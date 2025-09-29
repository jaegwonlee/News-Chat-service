"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import Header from "../../components/Header";

function SearchResults() {
  const [articles, setArticles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const searchParams = useSearchParams();
  const query = searchParams.get("q");

  useEffect(() => {
    if (query) {
      const fetchArticles = async () => {
        try {
          setIsLoading(true);
          const res = await fetch(`http://localhost:8000/api/articles/search?q=${encodeURIComponent(query)}`);
          if (!res.ok) throw new Error("검색 결과를 불러오는 데 실패했습니다.");
          const data = await res.json();
          setArticles(data);
        } catch (err) {
          setError(err.message);
        } finally {
          setIsLoading(false);
        }
      };
      fetchArticles();
    } else {
      setIsLoading(false);
      setArticles([]);
    }
  }, [query]);

  const handleArticleClick = (articleId) => {
    fetch(`http://localhost:8000/api/articles/${articleId}/view`, {
      method: "POST",
    }).catch((err) => console.error("조회수 업데이트 실패:", err));
  };

  return (
    <main className="grid-main" style={{ gridColumn: "2 / 3" }}>
      <h2>{`'${query}' 검색 결과`}</h2>
      {isLoading && <p>검색 중...</p>}
      {error && <p>오류: {error}</p>}
      {!isLoading && !error && articles.length > 0 && (
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
      {!isLoading && !error && articles.length === 0 && <p>{`'${query}'에 대한 검색 결과가 없습니다.`}</p>}
    </main>
  );
}

export default function SearchPage() {
  return (
    <div className="grid-container">
      <Header />
      <Suspense fallback={<p>로딩 중...</p>}>
        <SearchResults />
      </Suspense>
    </div>
  );
}
