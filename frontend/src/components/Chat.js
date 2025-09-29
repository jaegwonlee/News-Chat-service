"use client";

import { useEffect, useRef, useState } from "react";
import { useAuth } from "../context/AuthContext";

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const { user } = useAuth();
  const ws = useRef(null);
  const messagesContainerRef = useRef(null);

  useEffect(() => {
    const container = messagesContainerRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    if (!user) return;

    ws.current = new WebSocket(`ws://localhost:8000/ws/${user.username}`);

    ws.current.onopen = () => console.log("메인 채팅 서버 연결 완료");
    ws.current.onclose = () => console.log("메인 채팅 서버 연결 종료");

    ws.current.onmessage = (event) => {
      // ★ 1. 서버로부터 받은 JSON 문자열을 객체로 파싱합니다.
      const newMessage = JSON.parse(event.data);
      setMessages((prev) => [...prev, newMessage]);
    };

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [user]);

  const sendMessage = (e) => {
    e.preventDefault();
    if (input.trim() && ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(input);
      setInput("");
    }
  };

  if (!user) {
    return (
      <div className="chat-login-prompt">
        <p>실시간 채팅에 참여하려면 로그인이 필요합니다.</p>
      </div>
    );
  }

  return (
    <div className="chat-container">
      <div className="chat-messages" ref={messagesContainerRef}>
        {/* ★ 2. 메시지 렌더링 로직을 토론방과 동일하게 변경합니다. */}
        {messages.map((msg, index) => {
          if (msg.username === "📢") {
            return (
              <div key={index} className="system-message-container">
                <p>{msg.message}</p>
              </div>
            );
          }

          const isMyMessage = msg.username === user.username;

          return (
            <div key={index} className={`message-container ${isMyMessage ? "my-message" : "other-message"}`}>
              <div className="message-content">
                {!isMyMessage && <p className="message-username">{msg.username}</p>}
                <p className="message-bubble">{msg.message}</p>
              </div>
            </div>
          );
        })}
      </div>
      <form onSubmit={sendMessage} className="chat-input-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="메시지를 입력하세요..."
        />
        <button type="submit">전송</button>
      </form>
    </div>
  );
}
