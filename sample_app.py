import streamlit as st
import asyncio
import json
from typing import Dict, Any
import os
import boto3

from client import MCPClient

# MCP 서버 구성 로드 함수
def load_mcp_config():
    try:
        with open("mcp_config.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("mcp_config.json 파일을 찾을 수 없습니다.")
        return None
    except json.JSONDecodeError:
        st.error("mcp_config.json 파일이 유효한 JSON 형식이 아닙니다.")
        return None

# 서버 구성 생성 함수
def create_server_config():
    config = load_mcp_config()
    server_config = {}

    if config and "mcpServers" in config:
        for server_name, server_config_data in config["mcpServers"].items():
            # command가 있으면 stdio 방식
            if "command" in server_config_data:
                server_config[server_name] = {
                    "command": server_config_data.get("command"),
                    "args": server_config_data.get("args", []),
                    "env": server_config_data.get("env", None),
                    "transport": "stdio",
                }
            # url이 있으면 sse 방식
            elif "url" in server_config_data:
                server_config[server_name] = {
                    "url": server_config_data.get("url"),
                    "transport": "sse",
                }

    return server_config

# 비동기 환경 초기화
if 'event_loop' not in st.session_state:
    st.session_state.event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(st.session_state.event_loop)

# 클라이언트 상태 관리
if 'mcp_client' not in st.session_state:
    st.session_state.mcp_client = None
    st.session_state.tools = None

# 비동기 작업을 실행하는 함수
def run_async(coro):
    return st.session_state.event_loop.run_until_complete(coro)

def main():
    st.title("멀티 MCP 클라이언트")

    # 사이드바: 서버 연결 상태
    with st.sidebar:
        st.header("서버 연결 상태")

        # 서버 구성 가져오기
        server_config = create_server_config()
        print(server_config)
        # 서버 상태 표시
        if server_config:
            st.write(f"연결 가능한 서버: {len(server_config)}개")
            for server_name in server_config:
                st.write(f"- {server_name}")
        else:
            st.error("서버 구성을 불러올 수 없습니다.")

        # 연결 버튼
        if st.button("서버 연결"):
            with st.spinner("서버에 연결 중..."):
                try:
                    # 비동기 연결 함수 정의
                    async def connect_servers():
                        # 이미 연결된 경우 닫기
                        if st.session_state.mcp_client:
                            await st.session_state.mcp_client.close_all()

                        # 새 클라이언트 생성 및 연결
                        client = MCPClient(server_config)
                        await client.connect_to_server()
                        tools = await client.list_all_tools()

                        return client, tools

                    # 비동기 연결 실행
                    client, tools = run_async(connect_servers())

                    # 세션 상태에 저장
                    st.session_state.mcp_client = client
                    st.session_state.tools = tools

                    st.success(f"서버 연결 완료! {len(tools)}개의 도구 사용 가능")
                except Exception as e:
                    st.error(f"서버 연결 실패: {str(e)}")

    # 메인 페이지: 메시지 입력 및 처리
    st.subheader("대화")

    # 메시지 기록
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # 메시지 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 사용자 입력
    if prompt := st.chat_input("메시지를 입력하세요"):
        # 서버 연결 확인
        if not st.session_state.mcp_client:
            st.error("먼저 서버에 연결해주세요!")
            return

        # 사용자 입력 표시
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 응답 생성
        with st.chat_message("assistant"):
            with st.spinner("실행 중.."):
                try:
                    # 비동기 응답 처리
                    async def process_prompt():
                        return await st.session_state.mcp_client.process_query(prompt)

                    # 비동기 함수 실행
                    response = run_async(process_prompt())

                    # 응답 표시
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    error_msg = f"오류 발생: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

# 앱 실행
if __name__ == "__main__":
    main()