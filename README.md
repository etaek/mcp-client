# MCP Client

MCP(Model Context Protocol) 클라이언트 구현체로, Azure OpenAI와 통합되어 다양한 MCP 서버들과 상호작용할 수 있는 클라이언트입니다.

## 주요 기능

- Azure OpenAI 통합
  - GPT-4 모델 지원
  - 스트리밍 응답 처리
  - 도구 호출 및 결과 처리
- 다중 MCP 서버 연결 지원
  - 파일시스템 서버
  - PostgreSQL 서버
  - GitHub 서버
  - YouTube 데이터 서버
- 비동기 통신 지원
- 환경 설정 관리

## 설치 방법

1. 저장소 클론:

```bash
git clone https://github.com/etaek/mcp-client.git
cd mcp-client
```

2. 의존성 설치:

```bash
pip install -r requirements.txt
```

3. 환경 설정:

- `.env.example` 파일을 `.env`로 복사하고 필요한 설정값 입력
- `mcp_config.json` 파일에서 사용할 MCP 서버 설정

## 사용 방법

1. Azure OpenAI 설정

```env
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_ENDPOINT="your_azure_endpoint_here"
AZURE_OPENAI_API_VERSION="2024-12-01-preview"
AZURE_OPENAI_DEPLOYMENT="your_deployment_name_here"
```

2. MCP 서버 설정

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/path/to/directory"
      ]
    }
  }
}
```

3. 실행

```bash
python aws_app.py  # AWS Bedrock 클라이언트 실행
python azure_app.py  # Azure OpenAI 클라이언트 실행
```

## 파일 구조

- `azure_client.py`: Azure OpenAI 클라이언트 구현
- `aws_client.py`: AWS Bedrock 클라이언트 구현
- `azure_app.py`: Azure OpenAI 애플리케이션
- `aws_app.py`: AWS Bedrock 애플리케이션
- `.env.example`: 환경 변수 예제
- `mcp_config.json`: MCP 서버 설정
- `requirements.txt`: 프로젝트 의존성

## 의존성

- openai>=1.12.0
- python-dotenv>=1.0.0
- mcp-core>=0.1.0

## 라이선스

MIT License

## 작성자

- etaek

### Before the run

1. In `client/main.py`, update the `boto3.client` section with your actual AWS credentials and region
2. In `client/main.py`, change the `mcp_file_path` to your path

### Run

```bash
PYTHONPATH=. uv run client/main.py
```
