from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager
import os
import logging

from agents.health_agent import create_health_agent, HealthAgent
from database.chatdb_manager import ChatDBManager
from config import Config

# uvicorn app:app --host 127.0.0.1 --port 8000 --reload

# =============================================================================
# APP CONFIGURATION
# =============================================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# DEPENDENCIES
# =============================================================================
health_agent = None
chat_db = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 생명주기 관리"""
    global health_agent, chat_db
    
    try:
        # 설정 검증
        if not Config.validate():
            logger.error("설정 검증 실패")
            raise Exception("설정을 확인해주세요")
        
        # Health Agent 초기화
        logger.info("Health Agent 초기화 중...")
        health_agent = create_health_agent()
        
        # 데이터베이스 초기화
        logger.info("데이터베이스 초기화 중...")
        chat_db = ChatDBManager()
        
        logger.info("Health Agent API 시작 완료")
        
    except Exception as e:
        logger.error(f"초기화 중 오류: {e}")
        raise
    
    yield
    
    # 정리 작업 (필요시)
    logger.info("Health Agent API 종료")

app = FastAPI(
    title="Health Agent API",
    description="건강 정보 전문 AI 에이전트 API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# MODELS
# =============================================================================
class ChatRequest(BaseModel):
    user_id: str
    question: str

class ChatResponse(BaseModel):
    answer: str

def get_health_agent():
    """Health Agent 의존성 주입"""
    if health_agent is None:
        raise HTTPException(status_code=500, detail="Health Agent가 초기화되지 않았습니다")
    return health_agent

def get_chat_db():
    """Chat DB 의존성 주입"""
    if chat_db is None:
        raise HTTPException(status_code=500, detail="데이터베이스가 초기화되지 않았습니다")
    return chat_db

# =============================================================================
# ROUTES
# =============================================================================
@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {"message": "Health Agent API", "status": "running"}

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "health_agent_ready": health_agent is not None,
        "database_ready": chat_db is not None
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    agent: HealthAgent = Depends(get_health_agent),
    db: ChatDBManager = Depends(get_chat_db)
):
    """채팅 API 엔드포인트"""
    try:
        logger.info(f"채팅 요청 수신: user_id={request.user_id}, question={request.question[:50]}...")
        
        # 대화 세션 생성 또는 기존 세션 사용
        conversation_title = request.question[:20] + "..." if len(request.question) > 20 else request.question
        conversation_id = db.create_conversation(conversation_title)
        
        # 사용자 메시지 저장
        db.save_message(conversation_id, "user", request.question)
        
        # Health Agent로 질문 처리
        thread_id = f"health_session_{conversation_id}"
        answer = agent.process_query(
            question=request.question,
            thread_id=thread_id
        )
        
        # 응답 저장
        db.save_message(conversation_id, "assistant", answer)
        
        logger.info(f"채팅 응답 완료: conversation_id={conversation_id}")
        
        return ChatResponse(answer=answer)
        
    except Exception as e:
        logger.error(f"채팅 처리 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"채팅 처리 중 오류가 발생했습니다: {str(e)}")

@app.get("/conversations/{user_id}")
async def get_conversations(
    user_id: str,
    db: ChatDBManager = Depends(get_chat_db)
):
    """사용자의 대화 히스토리 조회"""
    try:
        conversations = db.get_conversations()
        return {"conversations": conversations}
    except Exception as e:
        logger.error(f"대화 히스토리 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail="대화 히스토리 조회 중 오류가 발생했습니다")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 