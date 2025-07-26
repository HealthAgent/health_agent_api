from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Tuple, Optional
from datetime import datetime

from .db import get_db_session, ensure_tables_exist
from .models import Conversation, Message

class ChatDBManager:
    def __init__(self):
        """데이터베이스 매니저 초기화"""
        # 테이블 존재 여부 확인 및 생성
        ensure_tables_exist()

    def create_conversation(self, title: str) -> int:
        """새로운 대화 세션 생성"""
        with get_db_session() as db:
            conversation = Conversation(title=title)
            db.add(conversation)
            db.flush()  # ID 생성을 위해 flush
            conversation_id = conversation.id
            return conversation_id

    def save_message(self, conversation_id: int, role: str, content: str):
        """메시지 저장"""
        with get_db_session() as db:
            # 메시지 생성
            message = Message(
                conversation_id=conversation_id,
                role=role,
                content=content
            )
            db.add(message)
            
            # 대화 세션의 updated_at 자동 업데이트 (모델에서 처리됨)
            conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conversation:
                conversation.updated_at = datetime.now()

    def get_conversations(self) -> List[Tuple]:
        """모든 대화 세션 목록 조회"""
        with get_db_session() as db:
            conversations = db.query(Conversation).order_by(desc(Conversation.updated_at)).all()
            return [(conv.id, conv.title, conv.created_at, conv.updated_at) for conv in conversations]

    def get_messages(self, conversation_id: int) -> List[Tuple]:
        """특정 대화 세션의 모든 메시지 조회"""
        with get_db_session() as db:
            messages = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.created_at).all()
            return [(msg.role, msg.content, msg.created_at) for msg in messages]

    def delete_conversation(self, conversation_id: int):
        """대화 세션 삭제 (cascade로 메시지도 함께 삭제됨)"""
        with get_db_session() as db:
            conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conversation:
                db.delete(conversation)