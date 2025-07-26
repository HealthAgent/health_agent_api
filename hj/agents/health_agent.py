from typing import List, Dict, Any
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from agents.base_agent import BaseAgent, BaseRagState
from tools.search_tools import health_search, web_search
from utils.user_data_parser import parse_apple_watch_data

class HealthAgent(BaseAgent):
    """건강 정보 전문 에이전트 - Apple Watch 데이터와 RAG 검색을 결합한 개인화된 건강 조언 제공"""
    
    def __init__(self):
        super().__init__(agent_type="health")
        self.apple_watch_file = "apple_watch_sample_30min.json"
        self.judgment_llm = ChatOpenAI(
            api_key=self.config.OPENAI_API_KEY,
            model=self.config.LLM_MODEL,
            temperature=0.1
        )
    
    def _needs_apple_watch_data(self, question: str) -> bool:
        """질문에 Apple Watch 데이터가 필요한지 판단"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 건강 상담 전문가입니다. 사용자의 질문을 분석하여 Apple Watch 데이터(심박수, 걸음 수, 활동량 등)가 답변에 도움이 될지 판단해주세요.

판단 기준:
1. 질문이 개인적인 건강 상태나 활동량에 관한 것인가?
2. 심박수, 걸음 수, 운동량, 활동 추적 등의 데이터가 답변에 유용할까?
3. 일반적인 건강 정보보다는 개인화된 데이터가 필요한 질문인가?

답변은 반드시 "YES" 또는 "NO"로만 해주세요."""),
            ("human", f"질문: {question}")
        ])
        
        try:
            response = self.judgment_llm.invoke(prompt.format_messages())
            return response.content.strip().upper() == "YES"
        except Exception as e:
            print(f"Apple Watch 데이터 필요성 판단 중 오류: {e}")
            return False
    
    def _search_documents(self, state: BaseRagState) -> BaseRagState:
        """건강 관련 문서 검색"""
        query = state["question"]
        documents = []
        
        try:
            health_docs = health_search.invoke(query)
            documents.extend(health_docs)
            
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
    
    def _load_watch_data(self, state: BaseRagState) -> BaseRagState:
        """Apple Watch 데이터 로드"""
        try:
            apple_watch_data = parse_apple_watch_data(self.apple_watch_file)
            state["apple_watch_data"] = apple_watch_data
        except Exception as e:
            print(f"Apple Watch 데이터 로드 중 오류: {e}")
            state["apple_watch_data"] = f"Apple Watch 데이터를 로드할 수 없습니다: {str(e)}"
        
        return state
    
    def _skip_watch_data(self, state: BaseRagState) -> BaseRagState:
        """Apple Watch 데이터 건너뛰기"""
        state["apple_watch_data"] = ""
        return state
    
    def _check_watch_need(self, state: BaseRagState) -> BaseRagState:
        """Apple Watch 데이터 필요성 확인"""
        return state
    
    def _route_watch_decision(self, state: BaseRagState) -> str:
        """Apple Watch 데이터 로드 여부 결정"""
        if self._needs_apple_watch_data(state["question"]):
            return "load_data"
        else:
            return "skip_data"
    
    def create_agent(self):
        """건강 전문 에이전트 생성"""
        from langgraph.graph import StateGraph, END
        
        workflow = StateGraph(BaseRagState)
        
        workflow.add_node("check_apple_watch_need", self._check_watch_need)
        workflow.add_node("load_watch_data", self._load_watch_data)
        workflow.add_node("skip_apple_watch_data", self._skip_watch_data)
        workflow.add_node("retrieve", self._search_documents)
        workflow.add_node("extract", self.extract_info)
        workflow.add_node("rewrite", self.rewrite_query)
        workflow.add_node("generate_response", self.generate_answer)
        
        workflow.set_entry_point("check_apple_watch_need")
        workflow.add_conditional_edges(
            "check_apple_watch_need",
            self._route_watch_decision,
            {
                "load_data": "load_watch_data",
                "skip_data": "skip_apple_watch_data"
            }
        )
        workflow.add_edge("load_watch_data", "retrieve")
        workflow.add_edge("skip_apple_watch_data", "retrieve")
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
        """질문 처리 및 답변 반환"""
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
    """건강 에이전트 인스턴스 생성"""
    return HealthAgent() 