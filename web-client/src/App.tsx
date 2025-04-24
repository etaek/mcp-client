import { useState } from "react";
import { ThemeProvider, createTheme } from "@mui/material/styles";
import CssBaseline from "@mui/material/CssBaseline";
import { Container, Box } from "@mui/material";
import ChatInterface from "./components/ChatInterface";
import { Message } from "./types";

const darkTheme = createTheme({
  palette: {
    mode: "dark",
    background: {
      default: "#343541",
      paper: "#343541",
    },
    primary: {
      main: "#ECECF1",
    },
  },
});

const API_URL = "http://localhost:8501/process_request";

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleSendMessage = async (content: string) => {
    if (!content.trim() || isProcessing) return;

    setIsProcessing(true);
    setMessages((prev) => [...prev, { type: "user", content }]);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: content }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("Response body is not readable");
      }

      let currentMessage = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // 새로운 청크를 디코드
        const chunk = new TextDecoder().decode(value);
        try {
          const data = JSON.parse(chunk);

          if (data.type === "tool_start") {
            // 도구 실행 시작
            currentMessage += `\n실행 도구: ${data.tool}\n`;
          } else if (data.type === "tool_result") {
            // 도구 실행 결과
            currentMessage += `도구실행결과: ${data.result}\n`;
          } else if (data.type === "assistant_message") {
            // 일반 메시지
            currentMessage += data.content;
          }

          // 실시간으로 메시지 업데이트
          setMessages((prev) => {
            const newMessages = [...prev];
            const lastMessage = newMessages[newMessages.length - 1];

            if (lastMessage?.type === "assistant") {
              lastMessage.content = currentMessage;
              return [...newMessages];
            } else {
              return [
                ...newMessages,
                { type: "assistant", content: currentMessage },
              ];
            }
          });
        } catch (e) {
          console.error("Error parsing chunk:", e);
        }
      }
    } catch (error) {
      console.error("Error processing message:", error);
      setMessages((prev) => [
        ...prev,
        {
          type: "assistant",
          content: "죄송합니다. 요청을 처리하는 중에 오류가 발생했습니다.",
        },
      ]);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Container
        maxWidth={false}
        disableGutters
        sx={{ height: "100vh", display: "flex", flexDirection: "column" }}
      >
        <Box
          sx={{
            flexGrow: 1,
            display: "flex",
            flexDirection: "column",
            height: "100%",
          }}
        >
          <ChatInterface
            messages={messages}
            onSendMessage={handleSendMessage}
            isProcessing={isProcessing}
          />
        </Box>
      </Container>
    </ThemeProvider>
  );
}

export default App;
