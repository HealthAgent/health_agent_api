import streamlit as st
from langchain_openai import ChatOpenAI

def validate_api_key(api_key):
    """OpenAI API 키의 유효성을 검증합니다."""
    try:
        llm = ChatOpenAI(api_key=api_key)
        llm.invoke("test")
        return True
    except Exception as e:
        return False

def render_sidebar():
    """바닐라 챗봇용 간단한 사이드바 UI 렌더링"""
    with st.sidebar:
        st.markdown("### 🔑 API 설정")
        
        try:
            default_api_key = st.secrets.get("openai", {}).get("api_key", "")
        except Exception:
            default_api_key = ""
            
        api_key = st.text_input("OpenAI API Key", type="password", value=default_api_key)
        
        if api_key:
            if validate_api_key(api_key):
                st.success("✅ API 키 유효")
                st.session_state.openai_api_key = api_key
                st.session_state.api_key_valid = True
            else:
                st.error("❌ 유효하지 않은 API 키")
                st.session_state.api_key_valid = False
        else:
            st.warning("⚠️ API 키를 입력해주세요")
            st.session_state.api_key_valid = False
        
        st.divider()
        
        # 대화 초기화 버튼
        if st.button("🗑️ 대화 초기화", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        
        # 현재 대화 정보
        st.info(f"💬 총 {len(st.session_state.messages)}개 메시지")
        
        # 하단 정보
        st.divider()
        st.markdown("""
        <div style="text-align: center; opacity: 0.6; font-size: 0.8em;">
            🤖 Health Agent<br>
            기본 챗봇
        </div>
        """, unsafe_allow_html=True) 