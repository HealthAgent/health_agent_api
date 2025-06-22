from typing import TypedDict, List, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from config import Config

class BaseRagState(TypedDict):
    """RAG 시스템의 상태를 정의하는 TypedDict"""
    messages: List[BaseMessage]
    question: str
    documents: List[Document]
    extracted_info: str
    rewritten_query: str
    answer: str
    apple_watch_data: str
    context_type: str  # 'health_data', 'web_search', 'combined'

class BaseAgent:
    """Health Agent의 기본 클래스"""
    
    def __init__(self, agent_type: str = "health"):
        self.config = Config()
        self.agent_type = agent_type
        self.llm = ChatOpenAI(
            api_key=self.config.OPENAI_API_KEY,
            model=self.config.LLM_MODEL,
            temperature=0.7
        )
        
    def get_extraction_system_prompt(self) -> str:
        """정보 추출용 시스템 프롬프트 반환"""
        return """당신은 건강 전문가입니다. 주어진 문서에서 질문과 관련된 건강 정보를 3~5개 정도 추출하세요.
        각 추출된 정보에 대해 다음 두 가지 측면을 0에서 1 사이의 점수로 평가하세요:
        1. 질문과의 관련성
        2. 답변의 충실성 (질문에 대한 완전하고 정확한 답변을 제공할 수 있는 정도)
        
        추출 형식:
        1. [추출된 건강 정보]
        - 관련성 점수: [0-1 사이의 점수]
        - 충실성 점수: [0-1 사이의 점수]
        2. [추출된 건강 정보]
        - 관련성 점수: [0-1 사이의 점수]
        - 충실성 점수: [0-1 사이의 점수]
        ...
        
        마지막으로, 추출된 정보를 종합하여 질문에 대한 전반적인 답변 가능성을 0에서 1 사이의 점수로 평가하세요."""
    
    def get_rewrite_system_prompt(self) -> str:
        """쿼리 재작성용 시스템 프롬프트 반환"""
        return """당신은 건강 정보 검색 전문가입니다. 주어진 원래 질문과 추출된 정보를 바탕으로, 더 관련성 있고 충실한 건강 정보를 찾기 위해 검색 쿼리를 개선해주세요.

        다음 사항을 고려하여 검색 쿼리를 개선하세요:
        1. 원래 질문의 핵심 요소
        2. 추출된 정보의 관련성 점수
        3. 추출된 정보의 충실성 점수
        4. 부족한 건강 정보나 더 자세히 알아야 할 부분

        개선된 검색 쿼리 작성 단계:
        1. 2-3개의 검색 쿼리를 제안하세요.
        2. 각 쿼리는 구체적이고 간결해야 합니다(5-10 단어 사이).
        3. 건강 관련 전문 용어를 적절히 활용하세요.
        4. 각 쿼리 뒤에는 해당 쿼리를 제안한 이유를 간단히 설명하세요.

        출력 형식:
        1. [개선된 검색 쿼리 1]
        - 이유: [이 쿼리를 제안한 이유 설명]
        2. [개선된 검색 쿼리 2]
        - 이유: [이 쿼리를 제안한 이유 설명]
        3. [개선된 검색 쿼리 3]
        - 이유: [이 쿼리를 제안한 이유 설명]

        마지막으로, 제안된 쿼리 중 가장 효과적일 것 같은 쿼리를 선택하고 그 이유를 설명하세요."""
    
    def get_answer_system_prompt(self) -> str:
        """답변 생성용 시스템 프롬프트 반환"""
        return """당신은 건강 전문 상담사입니다. 주어진 질문과 추출된 건강 정보, Apple Watch 데이터를 바탕으로 개인화된 건강 조언을 제공해주세요.

        답변은 마크다운 형식으로 작성하며, 다음 구조를 따르세요:
        
        ## 🏥 건강 상태 분석
        - Apple Watch 데이터 기반 현재 상태 평가
        - 주요 건강 지표 해석
        
        ## 💡 개인화된 건강 조언
        - 구체적이고 실행 가능한 건강 개선 방안
        - 단계별 실천 계획
        
        ## 📚 관련 건강 정보
        - 검색된 전문 건강 정보 요약
        - 각 정보의 출처 명시 (출처: [문서명] 또는 [웹사이트])
        
        ## ⚠️ 주의사항
        - 의학적 진단이 아닌 일반적인 건강 정보임을 명시
        - 심각한 증상이 있을 경우 의료진 상담 권장
        
        답변은 친근하고 이해하기 쉽게 작성하되, 의학적으로 정확한 정보를 제공하세요."""

    def extract_info(self, state: BaseRagState) -> BaseRagState:
        """문서에서 관련 정보를 추출합니다."""
        if not state["documents"]:
            state["extracted_info"] = "검색된 문서가 없습니다."
            return state
        
        # 문서 내용 결합
        doc_content = "\n\n".join([doc.page_content for doc in state["documents"]])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.get_extraction_system_prompt()),
            ("human", f"질문: {state['question']}\n\n문서 내용:\n{doc_content}")
        ])
        
        try:
            response = self.llm.invoke(prompt.format_messages())
            state["extracted_info"] = response.content
        except Exception as e:
            state["extracted_info"] = f"정보 추출 중 오류가 발생했습니다: {str(e)}"
        
        return state
    
    def rewrite_query(self, state: BaseRagState) -> BaseRagState:
        """검색 쿼리를 재작성합니다."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.get_rewrite_system_prompt()),
            ("human", f"원래 질문: {state['question']}\n\n추출된 정보:\n{state['extracted_info']}")
        ])
        
        try:
            response = self.llm.invoke(prompt.format_messages())
            state["rewritten_query"] = response.content
        except Exception as e:
            state["rewritten_query"] = f"쿼리 재작성 중 오류가 발생했습니다: {str(e)}"
        
        return state
    
    def generate_answer(self, state: BaseRagState) -> BaseRagState:
        """최종 답변을 생성합니다."""
        # Apple Watch 데이터 포함
        apple_watch_info = state.get("apple_watch_data", "Apple Watch 데이터가 없습니다.")
        
        # 문서 정보 결합
        doc_info = "\n\n".join([doc.page_content for doc in state["documents"]]) if state["documents"] else "관련 문서가 없습니다."
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.get_answer_system_prompt()),
            ("human", f"""질문: {state['question']}

Apple Watch 데이터:
{apple_watch_info}

검색된 건강 정보:
{doc_info}

추출된 핵심 정보:
{state.get('extracted_info', '추출된 정보가 없습니다.')}""")
        ])
        
        try:
            response = self.llm.invoke(prompt.format_messages())
            state["answer"] = response.content
            
            # 메시지 히스토리에 추가
            if "messages" not in state:
                state["messages"] = []
            
            state["messages"].extend([
                HumanMessage(content=state["question"]),
                AIMessage(content=state["answer"])
            ])
            
        except Exception as e:
            state["answer"] = f"답변 생성 중 오류가 발생했습니다: {str(e)}"
        
        return state
    
    def create_agent(self) -> StateGraph:
        """LangGraph 기반 에이전트를 생성합니다."""
        workflow = StateGraph(BaseRagState)
        
        # 노드 추가
        workflow.add_node("extract", self.extract_info)
        workflow.add_node("rewrite", self.rewrite_query)
        workflow.add_node("generate_response", self.generate_answer)
        
        # 엣지 설정
        workflow.set_entry_point("extract")
        workflow.add_edge("extract", "rewrite")
        workflow.add_edge("rewrite", "generate_response")
        workflow.add_edge("generate_response", END)
        
        # 메모리 체크포인트 설정
        memory = MemorySaver()
        app = workflow.compile(checkpointer=memory)
        
        return app 