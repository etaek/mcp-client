export interface Message {
  type: "user" | "assistant";
  content: string;
}

export interface ChatInterfaceProps {
  messages: Message[];
  onSendMessage: (content: string) => void;
  isProcessing: boolean;
}
