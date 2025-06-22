from typing import List
from langchain_core.tools import tool
from langchain_core.documents import Document
from langchain_community.retrievers import TavilySearchAPIRetriever

from database.vectordb_manager import VectorDBManager
from config import Config

config = Config()
db_manager = VectorDBManager()

@tool
def health_search(query: str) -> List[Document]:
    """건강 관련 문서를 검색합니다."""
    try:
        retriever = db_manager.load_collection("health_data")
        docs = retriever.invoke(query)
        
        if len(docs) > 0:
            return docs
        
        return [Document(page_content="관련 건강 정보를 찾을 수 없습니다.")]
    except Exception as e:
        print(f"건강 데이터 검색 중 오류: {e}")
        return [Document(page_content="건강 데이터 검색 중 오류가 발생했습니다.")]

# 웹 검색 설정
try:
    web_retriever = TavilySearchAPIRetriever(k=5, api_key=config.TAVILY_API_KEY)
except Exception as e:
    print(f"웹 검색 설정 오류: {e}")
    web_retriever = None

@tool
def web_search(query: str) -> List[Document]:
    """데이터베이스에 없는 정보 또는 최신 건강 정보를 웹에서 검색합니다."""
    if not web_retriever:
        return [Document(page_content="웹 검색 기능을 사용할 수 없습니다. TAVILY_API_KEY를 확인하세요.")]
    
    try:
        docs = web_retriever.invoke(query)
        
        formatted_docs = []
        for doc in docs:
            formatted_docs.append(
                Document(
                    page_content=f'<Document href="{doc.metadata.get("source", "Unknown")}"/>\n{doc.page_content}\n</Document>',
                    metadata={"source": "web search", "url": doc.metadata.get("source", "Unknown")}
                )
            )
        
        if len(formatted_docs) > 0:
            return formatted_docs
        
        return [Document(page_content="관련 정보를 웹에서 찾을 수 없습니다.")]
    except Exception as e:
        print(f"웹 검색 중 오류: {e}")
        return [Document(page_content="웹 검색 중 오류가 발생했습니다.")]

# 현재 활성화된 도구 목록
tools = [health_search, web_search] 