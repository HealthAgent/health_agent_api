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
from sidebar import render_gear_sidebar
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
st.set_page_config(page_title="등산 용품 관리 시스템", page_icon="⛰️", layout="wide")
st.title("⛰️ 등산 용품 관리 시스템")

# 사이드바 렌더링
render_gear_sidebar()

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
    model="gpt-4",
    temperature=0.7
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
    ("system", """당신은 등산 용품 관리를 도와주는 전문 어시스턴트입니다.
    사용자의 등산 용품을 관리하고 조언해주세요.
    
    가능한 작업:
    1. 새로운 등산 용품 등록
    2. 등산 용품 목록 조회
    3. 용품 상태 업데이트
    
    사용 가능한 툴:
    {tools}
    
    {agent_scratchpad}
    """),
    ("human", "{input}")
])

# 에이전트 프롬프트 템플릿
agent_prompt = ChatPromptTemplate.from_messages([
    ("system", """당신은 등산 용품 관리를 도와주는 전문 어시스턴트입니다.
    사용자의 등산 용품을 관리하고 조언해주세요.
    
    가능한 작업:
    1. 새로운 등산 용품 등록
    2. 등산 용품 목록 조회
    3. 용품 상태 업데이트
    
    사용 가능한 툴:
    {tools}
    
    {agent_scratchpad}
    """),
    ("human", "{input}")
])

# 등산 용품 관리 툴 정의
def add_gear_tool(input_str: str) -> str:
    """등산 용품 추가 툴"""
    try:
        data = json.loads(input_str)
        user = db.get_user(data['username'])
        if not user:
            return "사용자를 찾을 수 없습니다."
        
        gear_id = db.add_hiking_gear(user[0], data)
        if gear_id:
            return f"성공적으로 {data['item_name']}을(를) 추가했습니다."
        return "등산 용품 추가에 실패했습니다."
    except Exception as e:
        return f"오류 발생: {str(e)}"

def get_user_gear_tool(username: str) -> str:
    """사용자의 등산 용품 목록 조회 툴"""
    try:
        user = db.get_user(username)
        if not user:
            return "사용자를 찾을 수 없습니다."
        
        items = db.get_user_gear(user[0])
        if not items:
            return "등록된 등산 용품이 없습니다."
        
        result = "📋 등산 용품 목록:\n\n"
        current_category = None
        for item in items:
            if item[3] != current_category:
                current_category = item[3]
                result += f"\n【{current_category}】\n"
            result += f"• {item[2]}"
            if item[4]:  # brand
                result += f" ({item[4]})"
            result += f" - {item[9]}\n"  # condition
        return result
    except Exception as e:
        return f"오류 발생: {str(e)}"

def update_condition_tool(input_str: str) -> str:
    """등산 용품 상태 업데이트 툴"""
    try:
        data = json.loads(input_str)
        if db.update_gear_condition(data['gear_id'], data['condition'], data.get('last_used_date')):
            return "장비 상태가 업데이트되었습니다."
        return "상태 업데이트에 실패했습니다."
    except Exception as e:
        return f"오류 발생: {str(e)}"

# 툴 설정
tools = [
    Tool(
        name="add_hiking_gear",
        func=add_gear_tool,
        description="새로운 등산 용품을 추가합니다."
    ),
    Tool(
        name="get_user_gear",
        func=get_user_gear_tool,
        description="사용자의 등산 용품 목록을 조회합니다."
    ),
    Tool(
        name="update_gear_condition",
        func=update_condition_tool,
        description="등산 용품의 상태를 업데이트합니다."
    )
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
user_input = st.chat_input("무엇을 도와드릴까요?")

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
