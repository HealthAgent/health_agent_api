import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    DB_DIR = os.path.join(BASE_DIR, 'chroma_db')
    
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
    
    EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
    LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    
    SEARCH_TOP_K = int(os.environ.get("SEARCH_TOP_K", "3"))
    RERANK_TOP_N = int(os.environ.get("RERANK_TOP_N", "2"))
    
    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        return {k: v for k, v in cls.__dict__.items() 
                if not k.startswith('__') and not callable(getattr(cls, k))}
    
    @classmethod
    def validate(cls) -> bool:
        required_settings = ["OPENAI_API_KEY"]
        for setting in required_settings:
            if not getattr(cls, setting):
                print(f"경고: {setting}이(가) 설정되지 않았습니다.")
                return False
        return True 