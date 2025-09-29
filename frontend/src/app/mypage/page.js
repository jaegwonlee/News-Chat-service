"use client";

import Link from "next/link"; // ★ 1. Link 컴포넌트를 import 합니다.
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Header from "../../components/Header";
import { useAuth } from "../../context/AuthContext";

export default function MyPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  const [profileData, setProfileData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [passwordData, setPasswordData] = useState({ current: "", new: "", confirm: "" });
  const [message, setMessage] = useState({ type: "", text: "" });

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [user, loading, router]);

  useEffect(() => {
    if (user) {
      const token = localStorage.getItem("token");
      fetch("http://localhost:8000/api/users/me/profile", {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => (res.ok ? res.json() : Promise.reject(res)))
        .then((data) => {
          setProfileData(data);
          setIsLoading(false);
        })
        .catch(() => setIsLoading(false));
    }
  }, [user]);

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    setMessage({ type: "", text: "" });

    if (passwordData.new !== passwordData.confirm) {
      return setMessage({ type: "error", text: "새 비밀번호가 일치하지 않습니다." });
    }

    try {
      const token = localStorage.getItem("token");
      const res = await fetch("http://localhost:8000/api/users/me/change-password", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ current_password: passwordData.current, new_password: passwordData.new }),
      });

      const data = await res.json();
      if (res.ok) {
        setMessage({ type: "success", text: data.message });
        setPasswordData({ current: "", new: "", confirm: "" });
      } else {
        setMessage({ type: "error", text: data.detail || "비밀번호 변경 실패" });
      }
    } catch (err) {
      setMessage({ type: "error", text: "서버 오류 발생" });
    }
  };

  if (loading || isLoading || !profileData) {
    return <p style={{ textAlign: "center", marginTop: "5rem" }}>로딩 중...</p>;
  }

  return (
    <div className="grid-container">
      <Header />
      <main className="grid-main mypage-container" style={{ gridColumn: "2 / 3" }}>
        <h2>마이 페이지</h2>

        <section className="profile-section">
          <h3>내 정보</h3>
          <p>
            <strong>사용자 이름:</strong> {profileData.user_info.username}
          </p>
          <p>
            <strong>이메일:</strong> {profileData.user_info.email}
          </p>
        </section>

        <section className="profile-section">
          <h3>비밀번호 변경</h3>
          <form onSubmit={handlePasswordChange}>
            <input
              type="password"
              value={passwordData.current}
              onChange={(e) => setPasswordData({ ...passwordData, current: e.target.value })}
              placeholder="현재 비밀번호"
              required
            />
            <input
              type="password"
              value={passwordData.new}
              onChange={(e) => setPasswordData({ ...passwordData, new: e.target.value })}
              placeholder="새 비밀번호"
              required
            />
            <input
              type="password"
              value={passwordData.confirm}
              onChange={(e) => setPasswordData({ ...passwordData, confirm: e.target.value })}
              placeholder="새 비밀번호 확인"
              required
            />
            <button type="submit">변경하기</button>
            {message.text && <p className={`${message.type}-message`}>{message.text}</p>}
          </form>
        </section>

        <section className="profile-section">
          <h3>나의 활동 내역 (최근 메시지 20개)</h3>
          <div className="my-messages-list">
            {profileData.messages.length > 0 ? (
              profileData.messages.map((msg, index) => (
                <div key={index} className="my-message-item">
                  {/* ★ 2. 오류가 발생한 따옴표를 제거합니다. */}
                  <p>{msg.message}</p>
                  <small>
                    {/* ★ 3. a 태그를 Link 태그로 변경합니다. */}
                    <Link href={`/chat/${msg.room_id}`}>#{msg.topic_keyword}</Link> 토론방에서 |{" "}
                    {new Date(msg.created_at).toLocaleString()}
                  </small>
                </div>
              ))
            ) : (
              <p>최근 활동 내역이 없습니다.</p>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
