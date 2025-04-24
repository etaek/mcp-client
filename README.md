# MCP Client

MCP(Model Context Protocol) 클라이언트 구현체로, Azure OpenAI 및 AWS Bedrock과 통합되어 다양한 MCP 서버들과 상호작용할 수 있는 클라이언트입니다.

## 주요 기능

- Azure OpenAI 통합
  - GPT-4 모델 지원
  - 스트리밍 응답 처리
  - 도구 호출 및 결과 처리
    
- AWS Bedrock 통합
  - Claude 3 Sonnet 모델 지원
  - 스트리밍 응답 처리
  - 도구 호출 및 결과 처리
    
- 다중 MCP 서버 연결 지원
  - 파일시스템 서버, PostgreSQL 서버 etc ..

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

### Azure OpenAI 설정

```env
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_ENDPOINT="your_azure_endpoint_here"
AZURE_OPENAI_API_VERSION="2024-12-01-preview"
AZURE_OPENAI_DEPLOYMENT="your_deployment_name_here"
```

### AWS Bedrock 설정

AWS CLI를 통해 자격 증명을 설정합니다:

```bash
aws configure
```

위 명령어 실행 후 AWS Access Key ID, Secret Access Key, 리전 등을 입력하면 됩니다.
boto3가 자동으로 이 설정을 사용합니다.

### MCP 서버 설정

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
    },
    ...
  }
}
```

### 실행

Azure OpenAI 클라이언트 실행:

```bash
streamlit run azure_app.py
```

AWS Bedrock 클라이언트 실행:

```bash
streamlit run aws_app.py
```

## 파일 구조

- `azure_client.py`: Azure OpenAI 클라이언트 구현
- `aws_client.py`: AWS Bedrock 클라이언트 구현
- `azure_app.py`: Azure OpenAI 애플리케이션
- `aws_app.py`: AWS Bedrock 애플리케이션
- `.env.example`: 환경 변수 예제
- `mcp_config.json`: MCP 서버 설정
- `requirements.txt`: 프로젝트 의존성

```
