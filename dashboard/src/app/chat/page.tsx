"use client";

import Header from "@/components/header";
import ChatInterface from "@/components/chat-interface";

export default function ChatPage() {
  return (
    <div className="flex flex-col h-full">
      <Header title="Chat" />
      <div className="flex-1 overflow-hidden">
        <ChatInterface />
      </div>
    </div>
  );
}
