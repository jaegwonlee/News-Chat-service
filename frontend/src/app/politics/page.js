"use client";

import { useEffect, useState } from "react";
import Header from "../../components/Header"; // Header 컴포넌트 import

export default function PoliticsPage() {
  const [articles, setArticles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchArticles = async () => {
      try {
        setIsLoading(true);
        const res = await fetch("http://localhost:8000/api/articles/category/정치");
        if (!res.ok) throw new Error("서버에서 데이터를 불러오는 데 실패했습니다.");
        const data = await res.json();
        setArticles(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };
    fetchArticles();
  }, []);

  const handleArticleClick = (articleId) => {
    fetch(`http://localhost:8000/api/articles/${articleId}/view`, {
      method: "POST",
    }).catch((err) => console.error("조회수 업데이트 실패:", err));
  };

  return (
    <div className="grid-container">
      {/* 기존 header를 Header 컴포넌트로 교체 */}
      <Header />

      <main className="grid-main" style={{ gridColumn: "2 / 3" }}>
        <h2>정치 뉴스</h2>
        {isLoading && <p>뉴스 목록을 불러오는 중...</p>}
        {error && <p>오류: {error}</p>}
        {!isLoading && !error && (
          <div className="news-list-scrollable" style={{ maxHeight: "calc(100vh - 200px)" }}>
            {articles.map((article) => (
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
        )}
      </main>
    </div>
  );
}
