from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import Generator
from config import Config
from .models import Base
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Database engine configuration
engine = create_engine(
    Config().DATABASE_URL,
    poolclass=StaticPool,
    pool_pre_ping=True,
    echo=False  # Set to True for SQL query logging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """데이터베이스 세션을 반환하는 의존성 함수"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_session():
    """컨텍스트 매니저를 사용한 데이터베이스 세션 관리"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def table_exists(table_name: str) -> bool:
    """테이블 존재 여부 확인"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def create_tables():
    """데이터베이스 테이블 생성"""
    # 필요한 테이블 목록
    required_tables = ["conversations", "messages"]
    
    # 기존 테이블 확인
    existing_tables = []
    missing_tables = []
    
    for table in required_tables:
        if table_exists(table):
            existing_tables.append(table)
        else:
            missing_tables.append(table)
    
    if existing_tables:
        logger.info(f"기존 테이블 발견: {', '.join(existing_tables)}")
    
    if missing_tables:
        logger.info(f"생성할 테이블: {', '.join(missing_tables)}")
        Base.metadata.create_all(bind=engine)
        logger.info("테이블 생성 완료")
    else:
        logger.info("모든 필요한 테이블이 이미 존재합니다")

def drop_tables():
    """데이터베이스 테이블 삭제 (개발용)"""
    logger.warning("모든 테이블을 삭제합니다...")
    Base.metadata.drop_all(bind=engine)
    logger.info("테이블 삭제 완료")

def ensure_tables_exist():
    """테이블이 존재하는지 확인하고 없으면 생성"""
    required_tables = ["conversations", "messages"]
    missing_tables = [table for table in required_tables if not table_exists(table)]
    
    if missing_tables:
        logger.info(f"누락된 테이블 발견: {', '.join(missing_tables)}")
        create_tables()
    else:
        logger.debug("모든 테이블이 존재합니다") 