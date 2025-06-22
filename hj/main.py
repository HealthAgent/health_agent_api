import streamlit as st
import os
from agents.health_agent import create_health_agent
from utils.ui_utils import render_with_latex
from utils.ui_components import render_sidebar
from database.chatdb_manager import ChatDBManager
from config import Config

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None

if "api_key_valid" not in st.session_state:
    st.session_state.api_key_valid = False

if "health_agent" not in st.session_state:
    st.session_state.health_agent = None

# 데이터베이스 초기화
db = ChatDBManager()

# Streamlit 기본 설정
st.set_page_config(page_title="HealthAgent", page_icon=":climbing:", layout="wide")
st.title("🏔️ Health Agent")

# 사이드바 렌더링
render_sidebar()

# API 키 유효성 검증
if not st.session_state.api_key_valid:
    st.warning("OpenAI API 키가 유효하지 않습니다. 사이드바에서 유효한 API 키를 입력해주세요.")
    st.stop()

# Health Agent 초기화
@st.cache_resource
def initialize_health_agent():
    """Health Agent를 초기화합니다."""
    try:
        # 환경 변수 설정
        if "openai_api_key" in st.session_state:
            os.environ["OPENAI_API_KEY"] = st.session_state.openai_api_key
        elif Config.OPENAI_API_KEY:
            os.environ["OPENAI_API_KEY"] = Config.OPENAI_API_KEY
        
        agent = create_health_agent()
        return agent
    except Exception as e:
        st.error(f"Health Agent 초기화 중 오류: {e}")
        return None

# Health Agent 초기화
if st.session_state.health_agent is None:
    with st.spinner("Health Agent 시스템을 초기화하는 중..."):
        st.session_state.health_agent = initialize_health_agent()

# 이전 대화 히스토리 출력
if st.session_state.messages:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                st.markdown(render_with_latex(msg["content"]))
            else:
                st.markdown(msg["content"])

# 사용자 입력
user_input = st.chat_input("건강에 관한 질문을 입력하세요...")

if user_input and st.session_state.health_agent:
    # 현재 대화 세션 ID가 없으면 생성
    if not st.session_state.current_conversation_id:
        conversation_title = user_input[:20] + "..." if len(user_input) > 20 else user_input
        st.session_state.current_conversation_id = db.create_conversation(conversation_title)

    # 사용자 메시지 표시 및 저장
    st.chat_message("user").write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    db.save_message(st.session_state.current_conversation_id, "user", user_input)

    # Health Agent 응답 생성
    with st.chat_message("assistant"):
        with st.spinner("건강 정보를 분석하고 있습니다..."):
            try:
                # 고유한 thread_id 생성
                thread_id = f"health_session_{st.session_state.current_conversation_id}"
                
                # Health Agent로 질문 처리
                response = st.session_state.health_agent.process_query(
                    question=user_input,
                    thread_id=thread_id
                )
                
                # 응답 표시
                st.markdown(render_with_latex(response))
                
                # 응답 저장
                st.session_state.messages.append({"role": "assistant", "content": response})
                db.save_message(st.session_state.current_conversation_id, "assistant", response)
                
            except Exception as e:
                error_message = f"응답 생성 중 오류가 발생했습니다: {str(e)}"
                st.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})

# 하단 정보
st.markdown("---")
st.markdown("""
**⚠️ 주의사항**: 이 시스템은 의학적 진단을 대체하지 않습니다. 심각한 건강 문제가 있다면 의료진과 상담하세요.
""")