import streamlit as st
import asyncio
import json
from typing import Dict, Any
import os
from azure_client import AzureClient

# MCP 서버 구성 파일을 로드하는 함수
def load_mcp_config():
    """현재 디렉토리의 MCP 설정 파일을 로드합니다."""
    try:
        with open("./mcp_config.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"설정 파일을 읽는 중 오류 발생: {str(e)}")
        return None

# MCP 서버 연결 구성을 생성하는 함수
def create_server_config():
    config = load_mcp_config()
    server_config = {}

    if config and "mcpServers" in config:
        for server_name, server_config_data in config["mcpServers"].items():
            # stdio 방식 서버 설정
            if "command" in server_config_data:
                server_config[server_name] = {
                    "command": server_config_data.get("command"),
                    "args": server_config_data.get("args", []),
                    "env": server_config_data.get("env", None),
                    "transport": "stdio",
                }
            # SSE 방식 서버 설정
            elif "url" in server_config_data:
                server_config[server_name] = {
                    "url": server_config_data.get("url"),
                    "transport": "sse",
                }

    return server_config

# 비동기 이벤트 루프 초기화
if 'event_loop' not in st.session_state:
    st.session_state.event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(st.session_state.event_loop)

# 클라이언트 상태 초기화
if 'mcp_client' not in st.session_state:
    st.session_state.mcp_client = None
    st.session_state.tools = None
    st.session_state.connected = False

# 대화 메시지 초기화
if 'messages' not in st.session_state:
    st.session_state.messages = []

# 비동기 함수를 동기적으로 실행하는 헬퍼 함수
def run_async(coro):
    return st.session_state.event_loop.run_until_complete(coro)

# MCP 서버에 연결하는 비동기 함수
async def connect_servers(server_config):
    # 기존 연결이 있으면 종료
    if st.session_state.mcp_client:
        await st.session_state.mcp_client.close_all()

    # 새 클라이언트 생성 및 서버 연결
    client = AzureClient(server_config)
    await client.connect_to_server()
    tools = await client.list_all_tools()
    return client, tools

# 응답 스트림을 처리하는 비동기 함수
async def process_response_stream(client, prompt):
    full_response = []
    # 응답 스트림의 각 청크 처리
    async for chunk in client.process_query_stream(prompt):
        # 텍스트 응답 처리
        if chunk["type"] == "text":
            # final이 True인 경우만 처리하거나, final이 False인 경우만 처리
            if not chunk.get("final", False):  # 초기 응답만 표시
                st.markdown(chunk["content"])
                full_response.append(chunk["content"])

        # 도구 호출 처리
        elif chunk["type"] == "tool_call":
            with st.expander(f"🔧 도구 호출: {chunk['name']}", expanded=False):
                st.code(json.dumps(chunk["args"], indent=2, ensure_ascii=False), language="json")
            # full_response.append(f"\n\n**도구 호출:** {chunk['name']}\n```json\n{json.dumps(chunk['args'], indent=2, ensure_ascii=False)}\n```")

        # 도구 실행 결과 처리
        elif chunk["type"] == "tool_result":
            with st.expander(f"🔧 도구 결과: {chunk['name']}", expanded=False):
                try:
                    result_json = json.loads(chunk["result"])
                    st.json(result_json)
                except:
                    st.markdown(chunk["result"])
            # full_response.append(f"\n\n**도구 결과:**\n```\n{chunk['result']}\n```")

        # 오류 메시지 처리
        elif chunk["type"] == "error":
            st.error(chunk["message"])
            # full_response.append(f"\n\n**오류:** {chunk['message']}")

    # 전체 응답 텍스트 반환
    return "".join(full_response)

# 사이드바 UI 설정 함수
def setup_sidebar():
    with st.sidebar:
        st.header("서버 연결 상태")
        server_config = create_server_config()

        # 연결 상태 확인 및 자동 연결
        if not st.session_state.connected and not st.session_state.mcp_client:
            try:
                with st.spinner("서버에 자동 연결 중..."):
                    client, tools = run_async(connect_servers(server_config))

                # 세션 상태 업데이트
                st.session_state.mcp_client = client
                st.session_state.tools = tools
                st.session_state.connected = True
                st.success(f"서버 연결 완료! {len(tools)}개의 도구 사용 가능")
            except Exception as e:
                st.error(f"서버 자동 연결 실패: {str(e)}")
                st.info("아래 연결 버튼을 눌러 수동으로 연결해보세요.")
        elif st.session_state.connected:
            st.success("서버에 연결되어 있습니다.")

        # 서버 정보 표시
        if server_config:
            st.write(f"연결 가능한 서버: {len(server_config)}개")
            for server_name in server_config:
                st.write(f"- {server_name}")
        else:
            st.error("서버 구성을 불러올 수 없습니다.")

        # 서버 재연결 버튼
        if st.button("서버 재연결"):
            with st.spinner("서버에 연결 중..."):
                try:
                    # 기존 연결 종료
                    if st.session_state.mcp_client:
                        run_async(st.session_state.mcp_client.close_all())
                        st.session_state.mcp_client = None
                        st.session_state.connected = False

                    # 새로운 연결 생성
                    client, tools = run_async(connect_servers(server_config))
                    st.session_state.mcp_client = client
                    st.session_state.tools = tools
                    st.session_state.connected = True
                    st.success(f"서버 재연결 완료! {len(tools)}개의 도구 사용 가능")
                except Exception as e:
                    st.error(f"서버 연결 실패: {str(e)}")
                    st.session_state.connected = False

        # 대화 관리 섹션
        st.markdown("---")
        st.header("대화 관리")

        # 대화 초기화 버튼
        if st.button("대화 초기화"):
            st.session_state.messages = []
            st.rerun()

# 메인 애플리케이션 함수
def main():
    st.title("멀티 MCP 클라이언트")
    setup_sidebar()
    st.subheader("대화")

    # 기존 메시지 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 사용자 입력 처리
    if prompt := st.chat_input("메시지를 입력하세요"):
        # 서버 연결 상태 확인
        if not st.session_state.mcp_client or not st.session_state.connected:
            st.error("서버에 연결되어 있지 않습니다. 사이드바에서 서버 연결을 확인하세요.")
            return

        # 사용자 메시지 표시
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 응답 생성 및 표시
        with st.chat_message("assistant"):
            try:
                # 응답 스트림 처리
                with st.spinner("응답 생성 중..."):
                    full_content = run_async(process_response_stream(st.session_state.mcp_client, prompt))
                # 응답 메시지 저장
                st.session_state.messages.append({"role": "assistant", "content": full_content})
            except Exception as e:
                # 오류 처리
                error_msg = f"오류 발생: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
                st.session_state.connected = False

# 애플리케이션 시작점
if __name__ == "__main__":
    main()