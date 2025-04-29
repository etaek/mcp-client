import asyncio
from typing import Optional, List, Dict, Any, Callable, AsyncGenerator
from contextlib import AsyncExitStack
import os
from openai import AzureOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class AzureClient:
    def __init__(self, servers_config: dict):
        # Initialize session and client objects
        self.server_configs = servers_config
        self.clients = {}
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

        # Azure OpenAI 클라이언트 초기화
        self.client = AzureOpenAI(
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
            api_key=os.getenv('AZURE_OPENAI_API_KEY'),
            api_version=os.getenv('AZURE_OPENAI_API_VERSION')
        )
        self.deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT')
        self.tool_mapping = {}

    # methods will go here
    async def __aenter__(self):
        await self.connect_to_server()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close_all()

    async def connect_to_server(self):
      """Connect to an MCP server"""

      for server_name, config in self.server_configs.items():
        server_params = StdioServerParameters(
            command=config["command"],
            args=config.get("args", []),
            env=config.get("env", None)
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()
        self.clients[server_name] =  self.session


    async def list_all_tools(self):
        aggregated_tools = []
        for server_name, session in self.clients.items():
            tools_response = await session.list_tools()
            for tool in tools_response.tools:
                self.tool_mapping[tool.name] = server_name
                aggregated_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema
                    }
                })
        return aggregated_tools


    async def call_tool(self, tool_name: str, arguments: dict):
        server_id = self.tool_mapping.get(tool_name)
        session = self.clients.get(server_id)
        result = await session.call_tool(tool_name, arguments=arguments)
        return result

    def _send_request(
        self,
        messages: list,
        tools: list,
        *,
        tool_choice: str = "auto",
        response_format: dict = None,
        max_tokens: int = 1000,
        temperature: float = 0.2,
    ) -> Any:
        """
        Azure OpenAI에 요청을 보내는 내부 메소드

        Args:
            messages (list): 대화 메시지 목록
            tools (list): 사용 가능한 도구 목록
            tool_choice (str, optional): 도구 선택 방식. Defaults to "auto".
            response_format (dict, optional): 응답 형식. Defaults to None.
            max_tokens (int, optional): 최대 토큰 수. Defaults to 1000.
            temperature (float, optional): 온도 파라미터. Defaults to 0.2.

        Returns:
            Any: Azure OpenAI 응답
        """
        params = {
            "model": self.deployment,
            "messages": messages,
            "tools": tools,
            "tool_choice": tool_choice,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if response_format:
            params["response_format"] = response_format

        return self.client.chat.completions.create(**params)

    async def process_query_stream(self, query: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a query using Azure OpenAI and available tools, streaming the results"""
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        tools = await self.list_all_tools()
        # System prompt for Azure OpenAI
        system_prompt = """당신은 사용자의 요청을 분석하고 적절한 도구를 선택하여 실행하는 에이전트입니다.
사용 가능한 도구들의 정보가 제공될 것입니다. 각 도구의 기능을 이해하고 사용자의 요청에 가장 적합한 도구를 선택하여 사용해주세요.
도구를 사용하기 전에는 사용자가 요청한 내용을 요약하고, 어떤 도구를 왜 사용할지 먼저 사용자에게 설명해줘야 합니다.
도구 실행 결과를 바탕으로 사용자의 요청에 대한 최종 답변을 자연어로 제공해주세요."""

        messages.insert(0, {"role": "system", "content": system_prompt})

        while True:
            # Azure OpenAI API 호출
            response = self._send_request(
                messages=messages,
                tools=tools
            )

            choice = response.choices[0]

            # 텍스트 응답이 있으면 먼저 처리
            if choice.message.content:
                yield {"type": "text", "content": choice.message.content, "final": False}

            # 도구 호출이 없으면 반복 종료
            if not choice.message.tool_calls:
                break

            # 도구 호출 처리
            for tool_call in choice.message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = tool_call.function.arguments

                yield {
                    "type": "tool_call",
                    "name": tool_name,
                    "args": tool_args
                }

                try:
                    # 도구 실행
                    result = await self.call_tool(tool_name, eval(tool_args))
                    result_text = result.content[0].text if result.content and hasattr(result.content[0], 'text') else str(result)

                    # 도구 결과 스트리밍
                    yield {
                        "type": "tool_result",
                        "name": tool_name,
                        "result": result_text
                    }

                    # 도구 결과를 메시지에 추가
                    messages.append({
                        "role": "assistant",
                        "content": choice.message.content,
                        "tool_calls": [{
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": tool_args
                            }
                        }]
                    })
                    messages.append({
                        "role": "tool",
                        "content": result_text,
                        "tool_call_id": tool_call.id
                    })

                except Exception as e:
                    error_msg = f"도구 실행 중 오류: {str(e)}"
                    yield {"type": "error", "message": error_msg}
                    messages.append({
                        "role": "tool",
                        "content": error_msg,
                        "tool_call_id": tool_call.id
                    })

        # 최종 응답 생성
        final_response = self._send_request(
            messages=messages,
            tools=tools,
            tool_choice="none",
            response_format={"type": "text"},
            max_tokens=4096,
            temperature=1.0
        )

        if final_response.choices[0].message.content:
            yield {
                "type": "text",
                "content": final_response.choices[0].message.content,
                "final": True
            }

        # 최종 완료 신호
        yield {"type": "done"}


    async def close_all(self):
        """Close all connections"""
        await self.exit_stack.aclose()

