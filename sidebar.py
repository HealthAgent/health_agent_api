import streamlit as st
from database import Database
from datetime import datetime
import openai
from openai import OpenAI

def validate_api_key(api_key):
    """OpenAI API 키의 유효성을 검증합니다."""
    try:
        client = OpenAI(api_key=api_key)
        # 간단한 API 호출로 키 유효성 검증
        client.models.list()
        return True
    except Exception as e:
        return False

def render_sidebar():
    """사이드바 UI 렌더링"""
    db = Database()
    
    with st.sidebar:
        # OpenAI API 키 입력
        st.markdown("### OpenAI API 설정")
        try:
            default_api_key = st.secrets.get("openai", {}).get("api_key", "")
        except Exception:
            default_api_key = ""
            
        api_key = st.text_input("API Key", type="password", value=default_api_key)
        
        if api_key:
            if validate_api_key(api_key):
                st.success("API 키가 유효합니다.")
                # API 키를 세션 상태에 저장
                st.session_state.openai_api_key = api_key
                st.session_state.api_key_valid = True
            else:
                st.error("유효하지 않은 API 키입니다.")
                st.session_state.api_key_valid = False
        else:
            st.warning("API 키를 입력해주세요.")
            st.session_state.api_key_valid = False
        
        st.divider()
        
        # API 키가 유효한 경우에만 세션 관리 및 히스토리 표시
        if st.session_state.api_key_valid:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown("### 세션 관리")
            with col2:
                if st.button("New", use_container_width=True):
                    st.session_state.messages = []
                    st.session_state.system_prompt_created = False
                    st.session_state.current_conversation_id = None
                    st.rerun()
            
            st.divider()
            st.markdown("### History")
            
            # 이전 대화 목록 표시
            conversations = db.get_conversations()
            for conv in conversations:
                conv_id, title, created_at, updated_at = conv
                formatted_date = datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    if st.button(f"{title}", key=f"conv_{conv_id}", use_container_width=True):
                        st.session_state.current_conversation_id = conv_id
                        st.session_state.messages = []
                        for role, content in db.get_messages(conv_id):
                            st.session_state.messages.append({"role": role, "content": content})
                        st.session_state.system_prompt_created = True
                        st.rerun()
                
                with col2:
                    if st.button("🗑️", key=f"delete_{conv_id}", use_container_width=True):
                        db.delete_conversation(conv_id)
                        st.rerun()
            
            st.divider()
            
            # 현재 대화 내보내기
            if st.session_state.get("current_conversation_id"):
                if st.button("현재 대화 내보내기", use_container_width=True):
                    messages = db.get_messages(st.session_state.current_conversation_id)
                    conversation = ""
                    for role, content in messages:
                        if role == "user":
                            conversation += f"사용자: {content}\n"
                        elif role == "assistant":
                            conversation += f"챗봇: {content}\n"
                    
                    st.download_button(
                        label="대화 내용 다운로드",
                        data=conversation,
                        file_name=f"conversation_{st.session_state.current_conversation_id}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
        else:
            st.warning("유효한 API 키를 입력하여 채팅 기능을 사용할 수 있습니다.") 