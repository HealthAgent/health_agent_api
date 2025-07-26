import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class Config:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        
        self.DATA_DIR = os.path.join(self.BASE_DIR, 'data')
        self.DB_DIR = os.path.join(self.BASE_DIR, 'chroma_db')
        
        self.OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
        self.TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
        
        # Database configuration
        self.DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:password@localhost:5432/health_agent")
        
        self.EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
        self.LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")
        
        self.SEARCH_TOP_K = int(os.environ.get("SEARCH_TOP_K", "3"))
        self.RERANK_TOP_N = int(os.environ.get("RERANK_TOP_N", "2"))
        
        self._initialized = True
    
    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        instance = cls()
        return {k: v for k, v in instance.__dict__.items() 
                if not k.startswith('_') and not callable(getattr(instance, k))}
    
    @classmethod
    def validate(cls) -> bool:
        instance = cls()
        required_settings = ["OPENAI_API_KEY"]
        for setting in required_settings:
            if not getattr(instance, setting):
                print(f"경고: {setting}이(가) 설정되지 않았습니다.")
                return False
        return True 