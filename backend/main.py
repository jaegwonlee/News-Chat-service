import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import mysql.connector
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt
import feedparser
from apscheduler.schedulers.background import BackgroundScheduler
from typing import List, Dict
from collections import Counter, defaultdict
import json
from contextlib import asynccontextmanager

# --- AI 관련 라이브러리 import ---
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
import numpy as np
from konlpy.tag import Okt

# --- AI 모델 및 필요 객체 로드 ---
model = SentenceTransformer('jhgan/ko-sroberta-multitask')
okt = Okt()
load_dotenv()
scheduler = BackgroundScheduler()

# --- 서버 시작/종료 관리자 (lifespan) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("뉴스 자동 수집 및 AI 토픽 분석 스케줄러를 시작합니다.")
    scheduler.start()
    yield
    print("스케줄러를 종료합니다.")
    scheduler.shutdown()

# --- FastAPI 앱 생성 및 lifespan 연결 ---
app = FastAPI(lifespan=lifespan)

# --- 보안, CORS 설정 등 ---
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
origins = ["http://localhost:3000"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

class UserCreate(BaseModel):
    email: str
    username: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

def get_db_connection():
    try:
        return mysql.connector.connect(host=os.getenv("DB_HOST"), user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"), database=os.getenv("DB_DATABASE"))
    except Exception as e:
        print(f"DB 연결 오류: {e}"); return None

# --- 뉴스 수집 함수 ---
def fetch_and_save_articles():
    RSS_FEEDS = {
        "정치": [{"source": "JTBC", "url": "https://news-ex.jtbc.co.kr/v1/get/rss/section/politics"}, {"source": "SBS", "url": "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=01&plink=RSSREADER"}, {"source": "경향신문", "url": "https://www.khan.co.kr/rss/rssdata/politic_news.xml"}, {"source": "조선일보", "url": "https://www.chosun.com/arc/outboundfeeds/rss/category/politics/?outputType=xml"}, {"source": "동아일보", "url": "https://rss.donga.com/politics.xml"}, {"source": "한겨레", "url": "http://www.hani.co.kr/rss/politics/"}],
        "경제": [{"source": "JTBC", "url": "https://news-ex.jtbc.co.kr/v1/get/rss/section/economy"}, {"source": "SBS", "url": "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=02&plink=RSSREADER"}, {"source": "경향신문", "url": "https://www.khan.co.kr/rss/rssdata/economy_news.xml"}, {"source": "조선일보", "url": "https://www.chosun.com/arc/outboundfeeds/rss/category/economy/?outputType=xml"}, {"source": "동아일보", "url": "https://rss.donga.com/economy.xml"}, {"source": "한겨레", "url": "http://www.hani.co.kr/rss/economy/"}],
        "사회": [{"source": "JTBC", "url": "https://news-ex.jtbc.co.kr/v1/get/rss/section/society"}, {"source": "SBS", "url": "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=03&plink=RSSREADER"}, {"source": "경향신문", "url": "https://www.khan.co.kr/rss/rssdata/society_news.xml"}, {"source": "조선일보", "url": "https://www.chosun.com/arc/outboundfeeds/rss/category/national/?outputType=xml"}, {"source": "동아일보", "url": "https://rss.donga.com/national.xml"}, {"source": "한겨레", "url": "http://www.hani.co.kr/rss/society/"}],
        "스포츠": [{"source": "JTBC", "url": "https://news-ex.jtbc.co.kr/v1/get/rss/section/sports"}, {"source": "SBS", "url": "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=09&plink=RSSREADER"}, {"source": "경향신문", "url": "https://www.khan.co.kr/rss/rssdata/kh_sports.xml"}, {"source": "조선일보", "url": "https://www.chosun.com/arc/outboundfeeds/rss/category/sports/?outputType=xml"}, {"source": "동아일보", "url": "https://rss.donga.com/sports.xml"}, {"source": "한겨레", "url": "http://www.hani.co.kr/rss/sports/"}],
    }
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()
    total_count = 0
    for category, feed_list in RSS_FEEDS.items():
        for info in feed_list:
            feed = feedparser.parse(info["url"])
            for entry in feed.entries:
                cursor.execute("SELECT link FROM articles WHERE link = %s", (entry.link,))
                if not cursor.fetchone():
                    published_date = entry.get("published", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    cursor.execute("INSERT INTO articles (title, link, published_date, category, source_name) VALUES (%s, %s, %s, %s, %s)",(entry.title, entry.link, published_date, category, info["source"]))
                    total_count += 1
    conn.commit()
    conn.close()
    if total_count > 0: print(f"[{datetime.now()}] 자동 수집: {total_count}개의 새로운 기사를 수집했습니다.")

# --- AI 기반 토픽 분석 함수 (최종 안정화 버전) ---
def analyze_topics_and_update_rooms():
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor(dictionary=True, buffered=True)
    try:
        cursor.execute("SELECT id, title, view_count FROM articles WHERE created_at >= NOW() - INTERVAL 24 HOUR AND view_count > 0")
        articles = cursor.fetchall()
        if len(articles) < 3:
            cursor.execute("DELETE FROM chat_room_articles"); cursor.execute("DELETE FROM chat_messages"); cursor.execute("DELETE FROM chat_rooms"); conn.commit()
            return

        titles = [article['title'] for article in articles]
        embeddings = model.encode(titles)
        num_clusters = min(4, len(articles) // 2)
        if num_clusters < 1: return

        if num_clusters == 1:
            labels = [0] * len(articles)
        else:
            clustering_model = KMeans(n_clusters=num_clusters, random_state=42, n_init='auto')
            clustering_model.fit(embeddings)
            labels = clustering_model.labels_

        clusters = [[] for _ in range(max(1, num_clusters))]
        for i, label in enumerate(labels):
            clusters[label].append(articles[i])

        active_topics_keywords = []
        for cluster in clusters:
            if len(cluster) < 2: continue
            total_views = sum(article['view_count'] for article in cluster)
            if total_views < 2: continue
            
            all_keywords = []
            for article in cluster:
                nouns = {n for n in okt.nouns(article['title']) if len(n) > 1 and n not in ['기자', '뉴스', '종합', '사진']}
                if nouns:
                    all_keywords.extend(list(nouns))
            if not all_keywords: continue
            keyword_counts = Counter(all_keywords)
            total_unique_keywords = len(keyword_counts)
            shared_keywords_count = sum(1 for count in keyword_counts.values() if count > 1)
            coherence_score = shared_keywords_count / total_unique_keywords if total_unique_keywords > 0 else 0
            if coherence_score < 0.2: continue

            most_common_nouns = [noun for noun, count in keyword_counts.most_common(2)]
            topic_keyword = " ".join(most_common_nouns)
            active_topics_keywords.append(topic_keyword)
            
            room_id = None
            cursor.execute("SELECT id FROM chat_rooms WHERE topic_keyword = %s", (topic_keyword,))
            room = cursor.fetchone()
            if room:
                room_id = room['id']
                cursor.execute("UPDATE chat_rooms SET total_views = %s WHERE id = %s", (total_views, room_id))
            else:
                cursor.execute("INSERT INTO chat_rooms (topic_keyword, total_views) VALUES (%s, %s)", (topic_keyword, total_views))
                room_id = cursor.lastrowid
            
            if room_id:
                cursor.execute("DELETE FROM chat_room_articles WHERE room_id = %s", (room_id,))
                article_ids_in_cluster = [article['id'] for article in cluster]
                for article_id in article_ids_in_cluster:
                    cursor.execute("INSERT INTO chat_room_articles (room_id, article_id) VALUES (%s, %s)", (room_id, article_id))

        if active_topics_keywords:
            format_strings = ','.join(['%s'] * len(active_topics_keywords))
            cursor.execute(f"DELETE FROM chat_rooms WHERE topic_keyword NOT IN ({format_strings})", tuple(active_topics_keywords))
        else:
            cursor.execute("DELETE FROM chat_room_articles"); cursor.execute("DELETE FROM chat_messages"); cursor.execute("DELETE FROM chat_rooms")
        conn.commit()
        print(f"[{datetime.now()}] AI 토픽 분석(최종) 완료. 생성된 토론방: {len(active_topics_keywords)}개")
    except Exception as e:
        print(f"AI 토픽 분석 중 오류 발생: {e}")
    finally:
        conn.close()

# --- 스케줄러 작업 추가 ---
scheduler.add_job(fetch_and_save_articles, 'interval', minutes=1, next_run_time=datetime.now())
scheduler.add_job(analyze_topics_and_update_rooms, 'interval', minutes=1, next_run_time=datetime.now() + timedelta(seconds=10))

# --- 인증 관련 함수 ---
def get_user(db, email: str):
    cursor = db.cursor(dictionary=True); cursor.execute("SELECT * FROM users WHERE email = %s", (email,)); return cursor.fetchone()
def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]); email: str = payload.get("sub")
        if email is None: raise credentials_exception
    except JWTError: raise credentials_exception
    db = get_db_connection()
    if db is None: raise HTTPException(status_code=503, detail="데이터베이스 연결 실패")
    user = get_user(db, email=email)
    db.close()
    if user is None: raise credentials_exception
    return user
def verify_password(plain_password, hashed_password): return pwd_context.verify(plain_password, hashed_password)
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy(); expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15)); to_encode.update({"exp": expire}); return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# --- API 엔드포인트 ---
@app.post("/api/auth/signup", status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("SELECT email FROM users WHERE email = %s", (user.email,))
    if cursor.fetchone(): conn.close(); raise HTTPException(status_code=409, detail="이미 사용 중인 이메일입니다.")
    hashed_password = pwd_context.hash(user.password)
    cursor.execute("INSERT INTO users (email, username, hashed_password) VALUES (%s, %s, %s)", (user.email, user.username, hashed_password)); conn.commit(); conn.close()
    return {"message": f"'{user.username}'님, 회원가입이 완료되었습니다."}

@app.post("/api/auth/login")
def login_for_access_token(form_data: UserLogin):
    conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s", (form_data.email,))
    user = cursor.fetchone(); conn.close()
    if not user or not verify_password(form_data.password, user["hashed_password"]): raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="이메일 또는 비밀번호가 잘못되었습니다.")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user["email"]}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/users/me")
def read_users_me(current_user: dict = Depends(get_current_user)): return {"email": current_user["email"], "username": current_user["username"]}

# ★★★ 마이 페이지 API ★★★
@app.get("/api/users/me/profile")
def get_user_profile(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    if not conn: raise HTTPException(status_code=500, detail="DB 연결 실패")
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT cm.message, cm.created_at, cr.topic_keyword, cr.id as room_id
        FROM chat_messages cm
        JOIN chat_rooms cr ON cm.room_id = cr.id
        WHERE cm.username = %s
        ORDER BY cm.created_at DESC
        LIMIT 20
    """, (current_user['username'],))
    messages = cursor.fetchall()
    conn.close()
    return {"user_info": current_user, "messages": messages}

@app.post("/api/users/me/change-password")
def change_user_password(password_data: PasswordChange, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    if not conn: raise HTTPException(status_code=500, detail="DB 연결 실패")
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT hashed_password FROM users WHERE email = %s", (current_user['email'],))
    user_db_data = cursor.fetchone()
    if not verify_password(password_data.current_password, user_db_data['hashed_password']):
        conn.close()
        raise HTTPException(status_code=400, detail="현재 비밀번호가 일치하지 않습니다.")
    new_hashed_password = pwd_context.hash(password_data.new_password)
    cursor.execute("UPDATE users SET hashed_password = %s WHERE email = %s", (new_hashed_password, current_user['email']))
    conn.commit()
    conn.close()
    return {"message": "비밀번호가 성공적으로 변경되었습니다."}

@app.get("/api/chat/rooms")
def get_chat_rooms(limit: int = 0):
    conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
    query = "SELECT id, topic_keyword, total_views FROM chat_rooms ORDER BY total_views DESC"
    if limit > 0: query += f" LIMIT {limit}"
    cursor.execute(query); rooms = cursor.fetchall(); conn.close(); return rooms

@app.get("/api/chat/rooms/{room_id}")
def get_chat_room_details(room_id: int):
    conn = get_db_connection()
    if not conn: raise HTTPException(status_code=404, detail="DB 연결 실패")
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, topic_keyword FROM chat_rooms WHERE id = %s", (room_id,))
    room_details = cursor.fetchone()
    if not room_details: conn.close(); raise HTTPException(status_code=404, detail="Chat room not found")
    cursor.execute("SELECT username, message, created_at FROM chat_messages WHERE room_id = %s ORDER BY created_at ASC LIMIT 100", (room_id,))
    messages = cursor.fetchall()
    cursor.execute("SELECT a.id, a.title, a.link, a.published_date, a.source_name, a.view_count FROM articles a JOIN chat_room_articles cra ON a.id = cra.article_id WHERE cra.room_id = %s ORDER BY a.published_date DESC", (room_id,))
    related_articles = cursor.fetchall()
    conn.close()
    return {"details": room_details, "messages": messages, "related_articles": related_articles}

@app.get("/api/articles")
def get_articles_with_popular():
    conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, title, link, published_date, category, source_name, view_count FROM articles ORDER BY created_at DESC LIMIT 50"); latest_articles = cursor.fetchall()
    cursor.execute("SELECT id, title, link, published_date, category, source_name, view_count FROM articles ORDER BY view_count DESC, created_at DESC LIMIT 50"); popular_articles = cursor.fetchall()
    sources = ["JTBC", "SBS", "경향신문", "조선일보", "동아일보", "한겨레"]
    by_source = {source: [] for source in sources}
    for source in sources:
        cursor.execute("SELECT id, title, link, published_date, category, source_name, view_count FROM articles WHERE source_name = %s ORDER BY published_date DESC LIMIT 10", (source,)); by_source[source] = cursor.fetchall()
    conn.close()
    categorized_articles = defaultdict(list)
    for article in latest_articles:
        if article["category"] and article["category"] != "주요뉴스": categorized_articles[article["category"]].append(article)
    return {"latest": latest_articles, "popular": popular_articles, "categorized": categorized_articles, "by_source": by_source}

@app.get("/api/articles/category/{category_name}")
def get_articles_by_category(category_name: str):
    conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, title, link, published_date, category, source_name, view_count FROM articles WHERE category = %s ORDER BY published_date DESC LIMIT 50", (category_name,)); articles = cursor.fetchall(); conn.close(); return articles

@app.get("/api/articles/search")
def search_articles(q: str = ""):
    conn = get_db_connection(); cursor = conn.cursor(dictionary=True); search_term = f"%{q}%"
    cursor.execute("SELECT id, title, link, published_date, category, source_name, view_count FROM articles WHERE title LIKE %s ORDER BY published_date DESC LIMIT 50", (search_term,)); articles = cursor.fetchall(); conn.close(); return articles

@app.post("/api/articles/{article_id}/view")
def increment_view_count(article_id: int):
    conn = get_db_connection(); cursor = conn.cursor()
    try:
        cursor.execute("UPDATE articles SET view_count = view_count + 1 WHERE id = %s", (article_id,)); conn.commit()
        if cursor.rowcount == 0: raise HTTPException(status_code=404, detail="Article not found")
    except Exception as e: conn.rollback(); raise HTTPException(status_code=500, detail=f"조회수 업데이트 중 오류 발생: {e}")
    finally: conn.close()
    return {"message": "View count updated successfully"}

# --- WebSocket ---
class GlobalConnectionManager:
    def __init__(self): self.active_connections: List[WebSocket] = []
    async def connect(self, websocket: WebSocket): await websocket.accept(); self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket): self.active_connections.remove(websocket)
    async def broadcast(self, message: str):
        for connection in self.active_connections: await connection.send_text(message)

class RoomConnectionManager:
    def __init__(self): self.active_connections: Dict[int, List[WebSocket]] = {}
    async def connect(self, websocket: WebSocket, room_id: int):
        await websocket.accept()
        if room_id not in self.active_connections: self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)
    def disconnect(self, websocket: WebSocket, room_id: int):
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)
            if not self.active_connections[room_id]: del self.active_connections[room_id]
    async def broadcast(self, message: str, room_id: int):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]: await connection.send_text(message)

global_manager = GlobalConnectionManager(); room_manager = RoomConnectionManager()

@app.websocket("/ws/{username}")
async def global_websocket_endpoint(websocket: WebSocket, username: str):
    await global_manager.connect(websocket); await global_manager.broadcast(json.dumps({"username": "📢", "message": f"[{username}]님이 입장했습니다."}))
    try:
        while True: data = await websocket.receive_text(); await global_manager.broadcast(json.dumps({"username": username, "message": data}))
    except WebSocketDisconnect: global_manager.disconnect(websocket); await global_manager.broadcast(json.dumps({"username": "📢", "message": f"[{username}]님이 퇴장했습니다."}))

@app.websocket("/ws/chat/{room_id}/{username}")
async def room_websocket_endpoint(websocket: WebSocket, room_id: int, username: str):
    await room_manager.connect(websocket, room_id); await room_manager.broadcast(json.dumps({"username": "📢", "message": f"[{username}]님이 입장했습니다."}), room_id)
    try:
        while True:
            data = await websocket.receive_text(); conn = get_db_connection()
            if conn:
                cursor = conn.cursor(); cursor.execute("INSERT INTO chat_messages (room_id, username, message) VALUES (%s, %s, %s)", (room_id, username, data)); conn.commit()
                cursor.execute("UPDATE chat_rooms SET last_message_at = CURRENT_TIMESTAMP WHERE id = %s", (room_id,)); conn.commit(); conn.close()
            await room_manager.broadcast(json.dumps({"username": username, "message": data}), room_id)
    except WebSocketDisconnect: room_manager.disconnect(websocket, room_id); await room_manager.broadcast(json.dumps({"username": "📢", "message": f"[{username}]님이 퇴장했습니다."}), room_id)