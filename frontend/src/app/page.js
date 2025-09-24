"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";

export default function Home() {
  const [latestArticles, setLatestArticles] = useState([]);
  const [popularArticles, setPopularArticles] = useState([]);
  const [categorizedArticles, setCategorizedArticles] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const { user, loading, logout } = useAuth();

  const categoryOrder = ["정치", "경제", "사회", "스포츠"];

  const fetchArticles = async () => {
    try {
      setIsLoading(true);
      const res = await fetch("http://localhost:8000/api/articles");
      if (!res.ok) throw new Error("서버 오류");

      const data = await res.json();
      setLatestArticles(data.latest);
      setPopularArticles(data.popular);
      setCategorizedArticles(data.categorized);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchArticles();
  }, []);

  const handleArticleClick = (articleId) => {
    fetch(`http://localhost:8000/api/articles/${articleId}/view`, {
      method: "POST",
    }).catch((err) => console.error("조회수 업데이트 실패:", err));
  };

  const ArticleList = ({ articles }) => (
    <div className="news-list-scrollable" style={{ maxHeight: "600px" }}>
      {articles.slice(0, 10).map((article) => (
        <div key={article.id} className="news-item">
          <a
            href={article.link}
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => handleArticleClick(article.id)}
          >
            <h3>{article.title}</h3>
            <p>
              {new Date(article.published_date).toLocaleString()} (조회수: {article.view_count})
            </p>
          </a>
        </div>
      ))}
    </div>
  );

  return (
    <div className="grid-container">
      <header className="grid-header">
        <div className="site-name">NewsRound1</div>
        <div className="search-bar">검색창</div>
        <div className="auth-buttons">
          {loading ? null : user ? (
            <>
              {/* span 태그에 새로운 className 추가 */}
              <span className="welcome-message">{user.username}님 환영합니다!</span>
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

      <nav className="grid-nav">
        <span>정치</span>
        <span>경제</span>
        <span>사회</span>
        <span>스포츠</span>
      </nav>

      <main className="grid-main">
        {isLoading ? (
          <p>뉴스 목록을 불러오는 중...</p>
        ) : error ? (
          <p>오류: {error}</p>
        ) : (
          <>
            <section className="content-section">
              <div className="column">
                <h2>최신 뉴스</h2>
                <ArticleList articles={latestArticles} />
              </div>
              <div className="column">
                <h2>실시간 채팅</h2>
                <div className="news-item-placeholder-large"></div>
              </div>
              <div className="column">
                <h2>인기 뉴스</h2>
                <ArticleList articles={popularArticles} />
              </div>
            </section>

            <section className="content-section">
              <div className="column">
                <h2>언론사 A</h2>
                <div className="news-item-placeholder"></div>
                <div className="news-item-placeholder"></div>
              </div>
              <div className="column">
                <h2>언론사 B</h2>
                <div className="news-item-placeholder"></div>
                <div className="news-item-placeholder"></div>
              </div>
            </section>
          </>
        )}
      </main>

      <aside className="grid-sidebar-left">
        <div className="ad-box-vertical">광고</div>
      </aside>

      <aside className="grid-sidebar-right">
        <div className="other-features">기타 기능</div>
        <div className="ad-box-vertical small-ad">광고</div>
      </aside>
    </div>
  );
}
