"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

export default function RightSidebar() {
  const [rooms, setRooms] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchTopRooms = async () => {
      try {
        // isLoading을 true로 설정하지 않아도 괜찮습니다. 데이터가 오면 자연스럽게 업데이트 됩니다.
        const res = await fetch("http://localhost:8000/api/chat/rooms?limit=5");
        if (res.ok) {
          const data = await res.json();
          setRooms(data);
        }
      } catch (error) {
        console.error("Failed to fetch top rooms", error);
      } finally {
        setIsLoading(false); // 로딩 완료
      }
    };

    // 10초마다 자동으로 목록을 갱신합니다.
    const intervalId = setInterval(fetchTopRooms, 10000);
    fetchTopRooms(); // 처음 한 번 즉시 실행

    return () => clearInterval(intervalId); // 컴포넌트가 사라질 때 인터벌 정리
  }, []);

  return (
    <>
      <div className="other-features">
        <h3>R O U N D 2</h3>
        {isLoading ? (
          <p style={{ textAlign: "center", color: "#888" }}>불러오는 중...</p>
        ) : rooms.length > 0 ? (
          <>
            <ul className="room-list">
              {rooms.map((room) => (
                <li key={room.id}>
                  <Link href={`/chat/${room.id}`}>
                    {/* div로 감싸서 CSS 스타일이 정확히 적용되도록 합니다. */}
                    <div className="room-title">{room.topic_keyword}</div>
                    {/* 텍스트를 간결하게 수정했습니다. */}
                    <span className="room-views">(총 조회수 {room.total_views})</span>
                  </Link>
                </li>
              ))}
            </ul>
            <Link href="/chat" className="view-all-link">
              전체보기 →
            </Link>
          </>
        ) : (
          <p style={{ textAlign: "center", color: "#888" }}>현재 활성화된 토론방이 없습니다.</p>
        )}
      </div>
      <div className="ad-box-vertical small-ad">광고</div>
    </>
  );
}
