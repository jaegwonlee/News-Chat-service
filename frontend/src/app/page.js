"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Chat from "../components/Chat";
import Header from "../components/Header";
import RightSidebar from "../components/RightSidebar"; // ★★★ 1. RightSidebar 컴포넌트를 import 합니다.
import { useAuth } from "../context/AuthContext";

export default function Home() {
  const [latestArticles, setLatestArticles] = useState([]);
  const [popularArticles, setPopularArticles] = useState([]);
  const [articlesBySource, setArticlesBySource] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  // useAuth 훅과 관련된 변수들은 Header 컴포넌트가 사용하므로 그대로 둡니다.
  const { user, loading, logout } = useAuth();

  const fetchArticles = async () => {
    try {
      setIsLoading(true);
      const res = await fetch("http://localhost:8000/api/articles");
      if (!res.ok) throw new Error("서버 오류");

      const data = await res.json();
      setLatestArticles(data.latest);
      setPopularArticles(data.popular);
      setArticlesBySource(data.by_source || {});
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
      {(articles || []).slice(0, 10).map((article) => (
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
      <Header />

      <nav className="grid-nav">
        <Link href="/politics">
          <span>정치</span>
        </Link>
        <Link href="/economy">
          <span>경제</span>
        </Link>
        <Link href="/society">
          <span>사회</span>
        </Link>
        <Link href="/sports">
          <span>스포츠</span>
        </Link>
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
              <div className="column chat-column-container">
                <h2>뉴스톡</h2>
                <Chat />
              </div>
              <div className="column">
                <h2>인기 뉴스</h2>
                <ArticleList articles={popularArticles} />
              </div>
            </section>

            <section className="content-section">
              <div className="column">
                <h2>JTBC</h2>
                <ArticleList articles={articlesBySource.JTBC} />
              </div>
              <div className="column">
                <h2>SBS</h2>
                <ArticleList articles={articlesBySource.SBS} />
              </div>
              <div className="column">
                <h2>경향신문</h2>
                <ArticleList articles={articlesBySource.경향신문} />
              </div>
            </section>

            <div className="ad-banner-horizontal">광고</div>

            <section className="content-section">
              <div className="column">
                <h2>조선일보</h2>
                <ArticleList articles={articlesBySource.조선일보} />
              </div>
              <div className="column">
                <h2>동아일보</h2>
                <ArticleList articles={articlesBySource.동아일보} />
              </div>
              <div className="column">
                <h2>한겨레</h2>
                <ArticleList articles={articlesBySource.한겨레} />
              </div>
            </section>
          </>
        )}
      </main>

      <aside className="grid-sidebar-left">
        <div className="ad-box-vertical">광고</div>
      </aside>

      <aside className="grid-sidebar-right">
        <RightSidebar />
      </aside>
    </div>
  );
}
