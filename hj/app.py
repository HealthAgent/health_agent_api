from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
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
    conversation_id: Optional[int] = None  

class ChatResponse(BaseModel):
    answer: str
    conversation_id: int

class ConversationResponse(BaseModel):
    id: int
    title: str
    created_at: str
    updated_at: str

class MessageResponse(BaseModel):
    role: str
    content: str
    created_at: str

class ConversationDetailResponse(BaseModel):
    id: int
    title: str
    created_at: str
    updated_at: str
    messages: List[MessageResponse]

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
        "database_ready": chat_db is not None,
        "database_url": Config().DATABASE_URL.split('@')[0] + "@***" if '@' in Config().DATABASE_URL else "***"
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
        
        # 대화 세션 처리
        if request.conversation_id:
            # 기존 대화 세션에 추가
            conversation_id = request.conversation_id
            logger.info(f"기존 대화 세션 사용: conversation_id={conversation_id}")
        else:
            # 새로운 대화 세션 생성
            conversation_title = request.question[:20] + "..." if len(request.question) > 20 else request.question
            conversation_id = db.create_conversation(conversation_title)
            logger.info(f"새 대화 세션 생성: conversation_id={conversation_id}")
        
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
        
        return ChatResponse(answer=answer, conversation_id=conversation_id)
        
    except Exception as e:
        logger.error(f"채팅 처리 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"채팅 처리 중 오류가 발생했습니다: {str(e)}")

@app.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    db: ChatDBManager = Depends(get_chat_db)
):
    """모든 대화 세션 목록 조회"""
    try:
        conversations = db.get_conversations()
        return [
            ConversationResponse(
                id=conv[0],
                title=conv[1],
                created_at=conv[2].isoformat(),
                updated_at=conv[3].isoformat()
            )
            for conv in conversations
        ]
    except Exception as e:
        logger.error(f"대화 세션 목록 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail="대화 세션 목록 조회 중 오류가 발생했습니다")

@app.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation_detail(
    conversation_id: int,
    db: ChatDBManager = Depends(get_chat_db)
):
    """특정 대화 세션의 상세 정보 조회"""
    try:
        # 대화 세션 정보 조회
        conversations = db.get_conversations()
        conversation = None
        for conv in conversations:
            if conv[0] == conversation_id:
                conversation = conv
                break
        
        if not conversation:
            raise HTTPException(status_code=404, detail="대화 세션을 찾을 수 없습니다")
        
        # 메시지 목록 조회
        messages = db.get_messages(conversation_id)
        
        return ConversationDetailResponse(
            id=conversation[0],
            title=conversation[1],
            created_at=conversation[2].isoformat(),
            updated_at=conversation[3].isoformat(),
            messages=[
                MessageResponse(
                    role=msg[0],
                    content=msg[1],
                    created_at=msg[2].isoformat()
                )
                for msg in messages
            ]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"대화 세션 상세 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail="대화 세션 상세 조회 중 오류가 발생했습니다")

@app.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: ChatDBManager = Depends(get_chat_db)
):
    """대화 세션 삭제"""
    try:
        db.delete_conversation(conversation_id)
        return {"message": f"대화 세션 {conversation_id}가 삭제되었습니다"}
    except Exception as e:
        logger.error(f"대화 세션 삭제 중 오류: {e}")
        raise HTTPException(status_code=500, detail="대화 세션 삭제 중 오류가 발생했습니다")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 