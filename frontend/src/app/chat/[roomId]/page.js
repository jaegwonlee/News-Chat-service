"use client";

import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import Header from "../../../components/Header";
import { useAuth } from "../../../context/AuthContext";

export default function ChatRoomPage() {
  const [roomDetails, setRoomDetails] = useState(null);
  const [messages, setMessages] = useState([]);
  const [relatedArticles, setRelatedArticles] = useState([]);
  const [input, setInput] = useState("");
  const { user } = useAuth(); // ★ 현재 로그인한 사용자 정보
  const ws = useRef(null);
  const messagesContainerRef = useRef(null);
  const params = useParams();
  const { roomId } = params;

  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    if (!roomId || !user) return;

    const fetchRoomInfo = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/chat/rooms/${roomId}`);
        if (res.ok) {
          const data = await res.json();
          setRoomDetails(data.details);
          setMessages(data.messages);
          setRelatedArticles(data.related_articles || []);
        }
      } catch (error) {
        console.error("Failed to fetch room info", error);
      }
    };
    fetchRoomInfo();

    const socket = new WebSocket(`ws://localhost:8000/ws/chat/${roomId}/${user.username}`);
    ws.current = socket;

    socket.onmessage = (event) => {
      // ★ 1. 서버로부터 받은 JSON 문자열을 객체로 파싱합니다.
      const newMessage = JSON.parse(event.data);
      setMessages((prev) => [...prev, newMessage]);
    };

    return () => socket.close();
  }, [roomId, user]);

  const sendMessage = (e) => {
    e.preventDefault();
    if (input.trim() && ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(input);
      setInput("");
    }
  };

  const handleArticleClick = (articleId) => {
    fetch(`http://localhost:8000/api/articles/${articleId}/view`, {
      method: "POST",
    }).catch((err) => console.error("조회수 업데이트 실패:", err));
  };

  return (
    <div className="grid-container">
      <Header />
      <main className="grid-main" style={{ gridColumn: "2 / 3" }}>
        <h2>토론방: #{roomDetails?.topic_keyword || "로딩 중..."}</h2>

        <div className="chatroom-layout-container">
          <div className="chat-area">
            <div className="chat-container" style={{ height: "70vh" }}>
              <div className="chat-messages" ref={messagesContainerRef}>
                {/* ★ 2. 메시지 렌더링 로직을 완전히 새로 구성합니다. */}
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
          </div>

          <div className="related-articles-area">
            <h3>관련 기사 목록</h3>
            <div className="news-list-scrollable" style={{ maxHeight: "calc(70vh - 40px)" }}>
              {relatedArticles.map((article) => (
                <div key={article.id} className="news-item">
                  <a
                    href={article.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={() => handleArticleClick(article.id)}
                  >
                    <h3>{article.title}</h3>
                    <p>
                      {article.source_name} - {new Date(article.published_date).toLocaleString()} (조회수:{" "}
                      {article.view_count})
                    </p>
                  </a>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
