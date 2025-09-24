import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import mysql.connector
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt
import feedparser
from apscheduler.schedulers.background import BackgroundScheduler

# .env 파일 로드
load_dotenv()

# --- 보안 및 설정 ---
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- FastAPI 앱 생성 및 CORS 설정 ---
app = FastAPI()
origins = ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# --- Pydantic 모델 ---
class UserCreate(BaseModel):
    email: str
    username: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

# --- 데이터베이스 ---
def get_db_connection():
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_DATABASE")
        )
    except Exception as e:
        print(f"DB 연결 오류: {e}")
        return None

# --- 뉴스 수집 함수 ---
def fetch_and_save_articles():
    RSS_FEEDS = {

        "정치": {"source": "JTBC", "url": "https://news-ex.jtbc.co.kr/v1/get/rss/section/politics"},
        "경제": {"source": "JTBC", "url": "https://news-ex.jtbc.co.kr/v1/get/rss/section/economy"},
        "사회": {"source": "JTBC", "url": "https://news-ex.jtbc.co.kr/v1/get/rss/section/society"},
        "스포츠": {"source": "JTBC", "url": "https://news-ex.jtbc.co.kr/v1/get/rss/section/sports"},
    }
    conn = get_db_connection()
    if not conn:
        print("자동 수집 실패: DB 연결 불가")
        return
    cursor = conn.cursor()
    total_count = 0
    for category, info in RSS_FEEDS.items():
        feed = feedparser.parse(info["url"])
        for entry in feed.entries:
            cursor.execute("SELECT link FROM articles WHERE link = %s", (entry.link,))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO articles (title, link, published_date, category, source_name) VALUES (%s, %s, %s, %s, %s)",
                    (entry.title, entry.link, entry.get("published", ""), category, info["source"])
                )
                total_count += 1
    conn.commit()
    conn.close()
    if total_count > 0:
        print(f"[{datetime.now()}] 자동 수집: {total_count}개의 새로운 기사를 수집했습니다.")

# --- 스케줄러 설정 ---
scheduler = BackgroundScheduler()
scheduler.add_job(fetch_and_save_articles, 'interval', minutes=1, next_run_time=datetime.now())
@app.on_event("startup")
def start_scheduler():
    scheduler.start()
    print("뉴스 자동 수집 스케줄러를 시작합니다 (1분 간격)")

# --- 인증 관련 함수 ---
def get_user(db, email: str):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    return cursor.fetchone()

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    db = get_db_connection()
    if db is None:
        raise HTTPException(status_code=503, detail="데이터베이스 연결 실패")
    
    user = get_user(db, email=email)
    db.close()
    if user is None:
        raise credentials_exception
    return user

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- API 엔드포인트 ---
@app.post("/api/auth/signup", status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate):
    conn = get_db_connection()
    if not conn: raise HTTPException(status_code=500, detail="DB 연결 실패")
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM users WHERE email = %s", (user.email,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=409, detail="이미 사용 중인 이메일입니다.")
    hashed_password = pwd_context.hash(user.password)
    try:
        cursor.execute("INSERT INTO users (email, username, hashed_password) VALUES (%s, %s, %s)", (user.email, user.username, hashed_password))
        conn.commit()
    finally:
        conn.close()
    return {"message": f"'{user.username}'님, 회원가입이 완료되었습니다."}

@app.post("/api/auth/login")
def login_for_access_token(form_data: UserLogin):
    conn = get_db_connection()
    if not conn: raise HTTPException(status_code=500, detail="DB 연결 실패")
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s", (form_data.email,))
    user = cursor.fetchone()
    conn.close()
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="이메일 또는 비밀번호가 잘못되었습니다.")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user["email"]}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/users/me")
def read_users_me(current_user: dict = Depends(get_current_user)):
    return {"email": current_user["email"], "username": current_user["username"]}

@app.get("/api/articles")
def get_articles_with_popular():
    conn = get_db_connection()
    if not conn: raise HTTPException(status_code=500, detail="DB 연결 실패")
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, title, link, published_date, category, source_name, view_count FROM articles ORDER BY created_at DESC LIMIT 50")
    latest_articles = cursor.fetchall()
    cursor.execute("SELECT id, title, link, published_date, category, source_name, view_count FROM articles ORDER BY view_count DESC, created_at DESC LIMIT 50")
    popular_articles = cursor.fetchall()
    conn.close()
    categorized_articles = {}
    for article in latest_articles:
        category = article["category"]
        if category and category != "주요뉴스":
            if category not in categorized_articles:
                categorized_articles[category] = []
            categorized_articles[category].append(article)
    return {"latest": latest_articles, "popular": popular_articles, "categorized": categorized_articles}

@app.post("/api/articles/{article_id}/view")
def increment_view_count(article_id: int):
    conn = get_db_connection()
    if not conn: raise HTTPException(status_code=500, detail="DB 연결 실패")
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE articles SET view_count = view_count + 1 WHERE id = %s", (article_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"조회수 업데이트 중 오류 발생: {e}")
    finally:
        conn.close()
    return {"message": "View count updated successfully"}