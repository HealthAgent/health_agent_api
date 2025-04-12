import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import Tool
from langchain.memory import ConversationBufferMemory
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
from utils import render_with_latex
from sidebar import render_sidebar
from database import Database
import os
import json

# 세션 상태 초기화

# 메시지가 없으면 빈 리스트로 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 현재 대화 세션 ID가 없으면 None로 초기화
if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None

# API 키 유효성 검증 상태가 없으면 False로 초기화
if "api_key_valid" not in st.session_state:
    st.session_state.api_key_valid = False

# 데이터베이스 초기화
db = Database()

# Streamlit 기본 설정
st.set_page_config(page_title="HealthAgent", page_icon=":climbing:", layout="wide")
st.title("🏔️ Health Agent")

# 사이드바 렌더링
render_sidebar()

# API 키 유효성 검증 상태 확인
if not st.session_state.api_key_valid:
    st.warning("OpenAI API 키가 유효하지 않습니다. 사이드바에서 유효한 API 키를 입력해주세요.")
    st.stop()  # 여기서 실행을 중단하여 채팅 기능 제한

# LangChain 설정
try:
    api_key = st.session_state.get("openai_api_key", st.secrets.get("openai", {}).get("api_key", ""))
except Exception:
    api_key = st.session_state.get("openai_api_key", "")

if not api_key:
    st.warning("OpenAI API 키가 필요합니다. 사이드바에서 API 키를 입력해주세요.")
    st.stop()

# LLM 설정
llm = ChatOpenAI(
    api_key=api_key,
    model="gpt-4o-mini",
    temperature=0.7,
    streaming=True
)

# 임베딩 설정
embeddings = OpenAIEmbeddings(api_key=api_key)

# 메모리 설정
memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
)

# 프롬프트 템플릿 설정
prompt = ChatPromptTemplate.from_messages([
    ("system", """당신은 건강 관련 정보를 제공하는 전문 챗봇입니다. 
    사용자의 질문에 정확하고 전문적인 답변을 제공해주세요.
    가능한 한 자세하고 명확하게 설명해주세요.
    """),
    ("human", "{input}")
])

# 에이전트 프롬프트 템플릿
agent_prompt = ChatPromptTemplate.from_messages([
    ("system", """당신은 건강 관련 정보를 제공하는 전문 챗봇입니다.
    사용자의 질문에 정확하고 전문적인 답변을 제공해주세요.
    가능한 한 자세하고 명확하게 설명해주세요.
    
    사용 가능한 툴:
    {tools}
    
    사용 방법:
    1. 사용자의 질문을 이해합니다.
    2. 필요한 경우 적절한 툴을 사용합니다.
    3. 툴의 결과를 바탕으로 답변을 구성합니다.
    
    {agent_scratchpad}
    """),
    ("human", "{input}")
])

# 커스텀 툴 정의 예시
def search_health_info(query: str) -> str:
    """건강 정보를 검색하는 툴"""
    # 여기에 실제 검색 로직 구현
    return f"검색 결과: {query}"

# 툴 설정
tools = [
    Tool(
        name="health_search",
        func=search_health_info,
        description="건강 관련 정보를 검색하는 툴입니다."
    ),
    # 추가 툴을 여기에 정의할 수 있습니다
]

# 에이전트 설정
agent = create_openai_functions_agent(llm, tools, agent_prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# RAG 설정
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

# 벡터 스토어 설정 (실제 사용 시 주석 해제)
# vectorstore = FAISS.from_texts(
#     texts=["건강 정보 샘플 1", "건강 정보 샘플 2"],
#     embedding=embeddings
# )

# 체인 설정
chain = (
    {"input": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

# 이전 대화 히스토리 출력
if st.session_state.messages:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                st.markdown(render_with_latex(msg["content"]))
            else:
                st.markdown(msg["content"])

# 사용자 입력
user_input = st.chat_input("메시지를 입력하세요")

if user_input:
    
    # 현재 대화 세션 ID가 없으면 생성; 첫 쿼리의 10자만큼 제목으로 설정
    if not st.session_state.current_conversation_id:
        conversation_title = user_input[:10] + "..." if len(user_input) > 50 else user_input
        st.session_state.current_conversation_id = db.create_conversation(conversation_title)
        
        
    # 사용자의 첫 번째 질문을 메시지 히스토리에 추가
    st.chat_message("user").write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    db.save_message(st.session_state.current_conversation_id, "user", user_input)

    with st.chat_message("assistant"):
        stream_placeholder = st.empty()
        full_response = ""

        try:
            # 에이전트를 사용한 응답 생성 (주석 해제하여 사용)
            # response = agent_executor.invoke({"input": user_input})
            # full_response = response["output"]

            # 또는 기본 체인을 사용한 응답 생성
            for chunk in chain.stream(user_input):
                full_response += chunk
                stream_placeholder.markdown(render_with_latex(full_response + "▌"))

            # 최종 응답 표시
            stream_placeholder.empty()
            st.markdown(render_with_latex(full_response))

            # 응답 저장
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            db.save_message(st.session_state.current_conversation_id, "assistant", full_response)

        except Exception as e:
            st.error(f"응답 생성 중 오류가 발생했습니다: {str(e)}")
            st.info("잠시 후 다시 시도해주세요.")
            st.stop()