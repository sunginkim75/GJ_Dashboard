import os
import json
import uuid
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import FastAPI, HTTPException, Header, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

import sys
# 임포트 경로 보완 (Vercel 및 로컬 환경 호환)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from google.oauth2 import id_token
from google.auth.transport import requests

try:
    from src.sheets_client import SheetsClient
except ModuleNotFoundError:
    from sheets_client import SheetsClient

app = FastAPI(title="경조사 관리 API")

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 설정 파일 로드
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(base_dir, "config", "config.json")

# 기본값 설정
GOOGLE_CLIENT_ID = ""
JWT_SECRET_KEY = os.environ.get("JWT_SECRET", "gj_dashboard_local_secret_key_1298471")

if os.path.exists(config_path):
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
            GOOGLE_CLIENT_ID = config_data.get("google_client_id", "")
            if not os.environ.get("JWT_SECRET"):
                JWT_SECRET_KEY = config_data.get("jwt_secret", JWT_SECRET_KEY)
    except Exception as e:
        print(f"[Warning] Failed to load config.json: {e}")

# 환경 변수에 CLIENT_ID가 있다면 환경 변수 우선
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", GOOGLE_CLIENT_ID)

# 스프레드시트 클라이언트 초기화
sheets_client = SheetsClient()

class LoginRequest(BaseModel):
    id_token: str

class EventAddRequest(BaseModel):
    날짜: str
    이름: str
    경조사명: str
    회사: str
    누구: str
    입출금: str
    축의금: str
    참석: str
    입출금방법: str
    Remark: Optional[str] = ""

# JWT 토큰 생성 함수
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=7) # 기본 7일 만료
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm="HS256")
    return encoded_jwt

# JWT 토큰 검증 함수 (인증 의존성)
def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 헤더가 누락되었습니다."
        )
    
    try:
        token_type, token = authorization.split(" ")
        if token_type.lower() != "bearer":
            raise ValueError()
    except ValueError:
        token = authorization  # Bearer가 없는 경우 토큰값 자체로 처리
        
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("email")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 토큰입니다."
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="만료된 세션입니다. 다시 로그인해 주세요."
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 세션입니다. 다시 로그인해 주세요."
        )

@app.get("/api/auth/config")
def get_auth_config():
    return {"google_client_id": GOOGLE_CLIENT_ID}

@app.post("/api/auth/login")
def login(req: LoginRequest):
    try:
        # 구글 ID 토큰 검증
        id_info = id_token.verify_oauth2_token(
            req.id_token,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )
        
        email = id_info.get("email", "").strip().lower()
        name = id_info.get("name", "")
        picture = id_info.get("picture", "")
        
        if not email:
            raise HTTPException(status_code=400, detail="구글 토큰에서 이메일 정보를 가져올 수 없습니다.")
            
        # 허가된 이메일 목록 확인
        allowed_emails = sheets_client.get_allowed_emails()
        
        # AllowedUsers 시트가 비어 있는 경우, 개발 및 관리 편의를 위해 로그인한 사용자 접근을 일단 허용
        # 시트에 이메일이 등록되어 있다면 엄격하게 체크
        if allowed_emails and email not in allowed_emails:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"접근 권한이 없는 구글 계정입니다. ({email})"
            )
            
        # JWT 토큰 생성
        user_data = {
            "email": email,
            "name": name,
            "picture": picture
        }
        access_token = create_access_token(user_data)
        
        return {
            "success": True,
            "token": access_token,
            "user": user_data
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"구글 토큰 검증 실패: {str(e)}")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

@app.post("/api/auth/logout")
def logout():
    # Stateless JWT 세션은 백엔드에서 로그아웃 처리를 할 필요 없이 프론트에서 토큰을 파기하면 됨.
    return {"success": True}

@app.get("/api/auth/me")
def get_me(user: dict = Depends(get_current_user)):
    return {"success": True, "user": user}

@app.get("/api/events/search")
def search_events(query: str = "", user: dict = Depends(get_current_user)):
    results = sheets_client.search_events(query)
    return {"success": True, "data": results}

@app.post("/api/events/add")
def add_event(event: EventAddRequest, user: dict = Depends(get_current_user)):
    event_dict = event.dict()
    res = sheets_client.add_event(event_dict)
    if res.get("success"):
        return {"success": True, "번호": res.get("번호")}
    else:
        raise HTTPException(status_code=500, detail=f"스프레드시트 추가 실패: {res.get('error')}")

# SPA 프론트엔드 정적 파일 서빙
# Vercel 환경에서는 Vercel CDN 자체에서 정적 파일을 서빙하므로 로컬 마운트를 건너뜁니다.
if not os.environ.get("VERCEL"):
    static_path = os.path.join(base_dir, "src", "static")
    if not os.path.exists(static_path):
        try:
            os.makedirs(static_path)
        except Exception:
            pass
    if os.path.exists(static_path):
        app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.get("/")
def read_index():
    static_path = os.path.join(base_dir, "src", "static")
    index_file = os.path.join(static_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Server is running. Static files are served by CDN."}
