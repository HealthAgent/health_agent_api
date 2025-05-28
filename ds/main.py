import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from sidebar import render_sidebar
from sql_mountain_service import SQLMountainService
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Streamlit 기본 설정
st.set_page_config(page_title="당신은 나의 등반자", page_icon="🏔️", layout="wide")
st.title("당신은 나의 등반자 🏔️")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

if "api_key_valid" not in st.session_state:
    st.session_state.api_key_valid = False

# 산 정보 서비스 초기화 (한 번만)
if "mountain_service" not in st.session_state:
    st.session_state.mountain_service = SQLMountainService()

# 세션 상태 초기화
if "last_mountain" not in st.session_state:
    st.session_state.last_mountain = None


# 사이드바 렌더링
render_sidebar()

# API 키 확인
if not st.session_state.api_key_valid:
    st.warning("OpenAI API 키가 필요합니다. 사이드바에서 API 키를 입력해주세요.")
    st.stop()

# LLM 설정
llm = ChatOpenAI(
    api_key=st.session_state.openai_api_key,
    model="gpt-4o-mini",
    temperature=0.7
)

# 대화 기록 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 사용자 입력
if user_input := st.chat_input("메시지를 입력하세요"):
    # 사용자 메시지 추가
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # 사용자 메시지 표시
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # AI 응답 생성
    with st.chat_message("assistant"):
        with st.spinner("생각 중..."):
            try:
                # 대화 기록을 텍스트 리스트로 변환 (산 정보 서비스용)
                conversation_history = [msg["content"] for msg in st.session_state.messages]
                
                # 1단계: 산 정보 서비스로 먼저 처리 시도
                mountain_response = st.session_state.mountain_service.process_query(
                    user_input, 
                    conversation_history[:-1]  # 현재 입력 제외한 이전 대화들
                )
                
                if mountain_response:
                    # 산 관련 질문이면 산 정보 서비스 응답 사용
                    response_content = mountain_response
                    logger.info("산 정보 서비스로 처리됨")
                    
                else:
                    # 산 관련이 아니면 일반 챗봇으로 처리
                    logger.info("일반 챗봇으로 처리됨")
                    
                    # 대화 기록을 LangChain 메시지 형식으로 변환
                    messages = []
                    for msg in st.session_state.messages:
                        if msg["role"] == "user":
                            messages.append(HumanMessage(content=msg["content"]))
                        else:
                            messages.append(AIMessage(content=msg["content"]))
                    
                    # AI 응답 생성
                    response = llm.invoke(messages)
                    response_content = response.content
                
                # 응답 표시
                st.markdown(response_content)
                
                # 응답을 대화 기록에 추가
                st.session_state.messages.append({"role": "assistant", "content": response_content})
                
            except Exception as e:
                error_message = f"오류가 발생했습니다: {str(e)}"
                st.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})
                logger.error(f"처리 중 오류: {e}")