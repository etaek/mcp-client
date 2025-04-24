import { useState, useRef, useEffect } from "react";
import {
  Box,
  TextField,
  IconButton,
  CircularProgress,
  Typography,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import ReactMarkdown from "react-markdown";
import { Message } from "../types";

interface Props {
  messages: Message[];
  onSendMessage: (message: string) => void;
  isProcessing: boolean;
}

const ChatInterface: React.FC<Props> = ({
  messages,
  onSendMessage,
  isProcessing,
}) => {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isProcessing) {
      onSendMessage(input);
      setInput("");
    }
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        width: "100%",
        position: "fixed",
        top: 0,
        left: 0,
      }}
    >
      <Box
        sx={{
          flexGrow: 1,
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 2,
          pb: "80px",
        }}
      >
        <Box
          sx={{
            maxWidth: "1200px",
            width: "100%",
            margin: "0 auto",
            p: 2,
          }}
        >
          {messages.map((message, index) => (
            <Box
              key={index}
              sx={{
                backgroundColor:
                  message.type === "user" ? "transparent" : "#444654",
                p: 2,
                borderRadius: 1,
                maxWidth: "100%",
                wordBreak: "break-word",
                mb: 2,
              }}
            >
              <Typography
                component="div"
                sx={{
                  "& pre": {
                    backgroundColor: "#2A2B32",
                    p: 2,
                    borderRadius: 1,
                    overflowX: "auto",
                  },
                  "& code": {
                    backgroundColor: "#2A2B32",
                    p: 0.5,
                    borderRadius: 0.5,
                  },
                }}
              >
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </Typography>
            </Box>
          ))}
          <div ref={messagesEndRef} />
        </Box>
      </Box>
      <Box
        component="form"
        onSubmit={handleSubmit}
        sx={{
          p: 2,
          backgroundColor: "#343541",
          borderTop: "1px solid #4E4F60",
          position: "fixed",
          bottom: 0,
          left: 0,
          right: 0,
          width: "100%",
          zIndex: 1000,
        }}
      >
        <Box
          sx={{
            maxWidth: "1200px",
            margin: "0 auto",
          }}
        >
          <TextField
            fullWidth
            variant="outlined"
            placeholder="메시지를 입력하세요..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isProcessing}
            sx={{
              "& .MuiOutlinedInput-root": {
                backgroundColor: "#40414F",
                color: "white",
                "& fieldset": {
                  borderColor: "#4E4F60",
                },
                "&:hover fieldset": {
                  borderColor: "#4E4F60",
                },
                "&.Mui-focused fieldset": {
                  borderColor: "#4E4F60",
                },
              },
            }}
            InputProps={{
              endAdornment: (
                <IconButton
                  type="submit"
                  disabled={!input.trim() || isProcessing}
                  sx={{ color: "white" }}
                >
                  {isProcessing ? (
                    <CircularProgress size={24} color="inherit" />
                  ) : (
                    <SendIcon />
                  )}
                </IconButton>
              ),
            }}
          />
        </Box>
      </Box>
    </Box>
  );
};

export default ChatInterface;
