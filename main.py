import streamlit as st
from openai import OpenAI
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

# OpenAI 클라이언트 설정
try:
    api_key = st.session_state.get("openai_api_key", st.secrets.get("openai", {}).get("api_key", ""))
except Exception:
    api_key = st.session_state.get("openai_api_key", "")

if not api_key:
    st.warning("OpenAI API 키가 필요합니다. 사이드바에서 API 키를 입력해주세요.")
    st.stop()

client = OpenAI(api_key=api_key)

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
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=st.session_state.messages,
                stream=True
            )

            # 스트리밍 응답 처리
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    stream_placeholder.markdown(render_with_latex(full_response + "▌"))

            # 스트리밍 도중에도 마크다운으로 계속 갱신 (수식 포함)
            stream_placeholder.empty()
            st.markdown(render_with_latex(full_response))

            # 최종 마크다운 저장 및 DB 저장
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            db.save_message(st.session_state.current_conversation_id, "assistant", full_response)

        except Exception as e:
            st.error(f"응답 생성 중 오류가 발생했습니다: {str(e)}")
            st.info("잠시 후 다시 시도해주세요.")
            st.stop()