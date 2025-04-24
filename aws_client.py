import asyncio
from typing import Optional, List, Dict, Any, Callable, AsyncGenerator
from contextlib import AsyncExitStack

import boto3
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class AwsClient:
    def __init__(self, servers_config: dict):
        # Initialize session and client objects
        self.server_configs = servers_config
        self.clients = {}
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.bedrock_client = boto3.client(service_name="bedrock-runtime")
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
                    "toolSpec": {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": {
                            "json": tool.inputSchema
                        }
                    }
                })
        return aggregated_tools


    async def call_tool(self, tool_name: str, arguments: dict):
        server_id = self.tool_mapping.get(tool_name)
        session = self.clients.get(server_id)
        result = await session.call_tool(tool_name, arguments=arguments)
        return result


    async def process_query_stream(self, query: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a query using Claude and available tools, streaming the results"""
        messages = [
            {
                "role": "user",
                "content": [
                    {"text": query}
                ],
            }
        ]

        tools = await self.list_all_tools()
        # System prompt for Bedrock
        system_prompt = """당신은 사용자의 요청을 분석하고 적절한 도구를 선택하여 실행하는 에이전트입니다.
사용 가능한 도구들의 정보가 제공될 것입니다. 각 도구의 기능을 이해하고 사용자의 요청에 가장 적합한 도구를 선택하여 사용해주세요.
도구 실행 결과를 바탕으로 사용자의 요청에 대한 최종 답변을 자연어로 제공해주세요."""

        # Initial Bedrock API call
        response = self.bedrock_client.converse(
            modelId="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            messages=messages,
            system=[{"text": system_prompt}],
            toolConfig={
                "tools": tools
            },
        )

        # 도구 호출이 여러 번 발생할 수 있으므로 반복문으로 처리
        while True:
            has_tool_use = False
            assistant_message_content = []

            # 응답 메시지 처리
            for content in response['output']['message']['content']:
                if 'text' in content:
                    # 텍스트 응답 스트리밍 (초기 응답)
                    yield {"type": "text", "content": content['text'], "final": False}
                    assistant_message_content.append(content)
                elif 'toolUse' in content:
                    has_tool_use = True
                    tool = content['toolUse']
                    tool_id = tool['toolUseId']
                    tool_name = tool['name']
                    tool_args = tool['input']

                    # 도구 호출 알림 스트리밍
                    yield {"type": "tool_call", "name": tool_name, "args": tool_args}

                    try:
                        # 도구 실행
                        result = await self.call_tool(tool_name, tool_args)
                        result_text = result.content[0].text if result.content and hasattr(result.content[0], 'text') else str(result)

                        # 도구 결과 스트리밍
                        yield {"type": "tool_result", "name": tool_name, "result": result_text}

                        assistant_message_content.append(content)

                        # 도구 결과 전달
                        messages.append({
                            "role": "assistant",
                            "content": assistant_message_content
                        })
                        messages.append({
                            "role": "user",
                            "content": [
                                {
                                    "toolResult": {
                                        "toolUseId": tool_id,
                                        "content": [{"text": result_text}]
                                    }
                                }
                            ]
                        })
                    except Exception as e:
                        error_msg = f"도구 실행 중 오류: {str(e)}"
                        # 오류 스트리밍
                        yield {"type": "error", "message": error_msg}

                        # 오류 정보 전달
                        messages.append({
                            "role": "assistant",
                            "content": assistant_message_content
                        })
                        messages.append({
                            "role": "user",
                            "content": [
                                {
                                    "toolResult": {
                                        "toolUseId": tool_id,
                                        "content": [{"text": error_msg}]
                                    }
                                }
                            ]
                        })

            # 도구 호출이 없으면 반복 종료
            if not has_tool_use or response['stopReason'] != 'tool_use':
                break

            # 다음 응답 가져오기
            response = self.bedrock_client.converse(
                modelId="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                messages=messages,
                system=[{"text": system_prompt}],
                toolConfig={
                    "tools": tools
                },
            )

            # 다음 응답의 텍스트 부분만 추출해서 전송
            for content in response['output']['message']['content']:
                if 'text' in content:
                    # 최종 텍스트 응답 (도구 호출 이후)
                    yield {"type": "text", "content": content['text'], "final": True}

        # 최종 완료 신호
        yield {"type": "done"}


    async def close_all(self):
        await self.exit_stack.aclose()

