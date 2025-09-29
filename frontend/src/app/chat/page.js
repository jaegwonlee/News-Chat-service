"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Header from "../../components/Header";

export default function AllChatRoomsPage() {
  const [rooms, setRooms] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchAllRooms = async () => {
      try {
        setIsLoading(true);
        const res = await fetch("http://localhost:8000/api/chat/rooms");
        if (res.ok) {
          const data = await res.json();
          setRooms(data);
        }
      } catch (error) {
        console.error("Failed to fetch all rooms", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchAllRooms();
  }, []);

  return (
    <div className="grid-container">
      <Header />
      <main className="grid-main" style={{ gridColumn: "2 / 3" }}>
        <h2>전체 토론방 목록</h2>
        {isLoading ? (
          <p>목록을 불러오는 중...</p>
        ) : (
          <div className="full-room-list">
            {rooms.map((room) => (
              // 각 토론방을 news-item 스타일로 보기 좋게 표시
              <div key={room.id} className="news-item">
                <Link href={`/chat/${room.id}`}>
                  <h3># {room.topic_keyword}</h3>
                  <p>관련 기사 총 조회수: {room.total_views}회</p>
                </Link>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
