from typing import List, Dict, Any
from langchain_core.documents import Document

from agents.base_agent import BaseAgent, BaseRagState
from tools.search_tools import tools, health_search, web_search
from utils.user_data_parser import parse_apple_watch_data

class HealthAgent(BaseAgent):
    """
    건강 정보 전문 에이전트 클래스
    Apple Watch 데이터와 RAG 검색을 결합하여 개인화된 건강 조언 제공
    """
    
    def __init__(self):
        super().__init__(agent_type="health")
        self.tools = {tool.name: tool for tool in tools}
        self.apple_watch_file = "apple_watch_sample_30min.json"
    
    def retrieve_documents(self, state: BaseRagState) -> BaseRagState:
        """건강 관련 문서를 검색합니다."""
        query = state["question"]
        documents = []
        
        try:
            # 1. 건강 데이터베이스에서 검색
            health_docs = health_search.invoke(query)
            documents.extend(health_docs)
            
            # 2. 웹 검색 (필요시)
            if len(health_docs) == 0 or "관련 건강 정보를 찾을 수 없습니다" in health_docs[0].page_content:
                web_docs = web_search.invoke(query)
                documents.extend(web_docs)
                state["context_type"] = "web_search"
            else:
                state["context_type"] = "health_data"
                
        except Exception as e:
            print(f"문서 검색 중 오류: {e}")
            documents = [Document(page_content=f"문서 검색 중 오류가 발생했습니다: {str(e)}")]
            state["context_type"] = "error"
        
        state["documents"] = documents
        return state
    
    def load_apple_watch_data(self, state: BaseRagState) -> BaseRagState:
        """Apple Watch 데이터를 로드하고 파싱합니다."""
        try:
            apple_watch_data = parse_apple_watch_data(self.apple_watch_file)
            state["apple_watch_data"] = apple_watch_data
        except Exception as e:
            print(f"Apple Watch 데이터 로드 중 오류: {e}")
            state["apple_watch_data"] = f"Apple Watch 데이터를 로드할 수 없습니다: {str(e)}"
        
        return state
    
    def create_agent(self):
        """건강 전문 에이전트를 생성합니다."""
        from langgraph.graph import StateGraph, END
        
        workflow = StateGraph(BaseRagState)
        
        # 노드 추가
        workflow.add_node("load_watch_data", self.load_apple_watch_data)
        workflow.add_node("retrieve", self.retrieve_documents)
        workflow.add_node("extract", self.extract_info)
        workflow.add_node("rewrite", self.rewrite_query)
        workflow.add_node("generate_response", self.generate_answer)
        
        # 엣지 설정
        workflow.set_entry_point("load_watch_data")
        workflow.add_edge("load_watch_data", "retrieve")
        workflow.add_edge("retrieve", "extract")
        workflow.add_edge("extract", "rewrite")
        workflow.add_edge("rewrite", "generate_response")
        workflow.add_edge("generate_response", END)
        
        # 메모리 체크포인트 설정
        from langgraph.checkpoint.memory import MemorySaver
        memory = MemorySaver()
        app = workflow.compile(checkpointer=memory)
        
        return app
    
    def process_query(self, question: str, thread_id: str = "default") -> str:
        """질문을 처리하고 답변을 반환합니다."""
        agent = self.create_agent()
        
        initial_state = {
            "question": question,
            "messages": [],
            "documents": [],
            "extracted_info": "",
            "rewritten_query": "",
            "answer": "",
            "apple_watch_data": "",
            "context_type": ""
        }
        
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            result = agent.invoke(initial_state, config=config)
            return result.get("answer", "답변을 생성할 수 없습니다.")
        except Exception as e:
            return f"질문 처리 중 오류가 발생했습니다: {str(e)}"

def create_health_agent():
    """건강 에이전트 인스턴스를 생성하는 팩토리 함수"""
    return HealthAgent() 