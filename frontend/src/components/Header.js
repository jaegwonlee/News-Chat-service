"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "../context/AuthContext";

export default function Header() {
  const { user, loading, logout } = useAuth();
  const [searchTerm, setSearchTerm] = useState("");
  const router = useRouter();

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (searchTerm.trim()) {
      router.push(`/search?q=${encodeURIComponent(searchTerm.trim())}`);
    }
  };

  return (
    <header className="grid-header">
      <div className="site-name">
        <Link href="/">NewsRound1</Link>
      </div>

      <form className="search-bar-form" onSubmit={handleSearchSubmit}>
        <input
          type="text"
          className="search-bar-input"
          placeholder="검색어를 입력하세요..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
        <button type="submit" className="search-bar-button">
          검색
        </button>
      </form>

      <div className="auth-buttons">
        {loading ? null : user ? (
          <>
            <span className="welcome-message">{user.username}님 환영합니다!</span>
            {/* ★★★ 아래 Link 태그를 추가합니다. ★★★ */}
            <Link href="/mypage">
              <div className="login-button" style={{ backgroundColor: "#555", marginRight: "0.5rem" }}>
                마이 페이지
              </div>
            </Link>
            <div onClick={logout} className="signup-button" style={{ cursor: "pointer" }}>
              로그아웃
            </div>
          </>
        ) : (
          <>
            <Link href="/login">
              <div className="login-button">로그인</div>
            </Link>
            <Link href="/signup">
              <div className="signup-button">회원가입</div>
            </Link>
          </>
        )}
      </div>
    </header>
  );
}
