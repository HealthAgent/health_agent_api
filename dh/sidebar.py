import streamlit as st
from database import Database
from datetime import datetime
from langchain_openai import ChatOpenAI

def validate_api_key(api_key):
    """OpenAI API 키의 유효성을 검증합니다."""
    try:
        llm = ChatOpenAI(api_key=api_key)
        # 간단한 API 호출로 키 유효성 검증
        llm.invoke("test")
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

def render_gear_sidebar():
    """등산 용품 관리 사이드바 렌더링"""
    db = Database()
    
    with st.sidebar:
        # OpenAI API 키 설정 섹션
        st.markdown("### 🔑 API 설정")
        
        # secrets.toml에서 API 키 읽기 시도
        try:
            default_api_key = st.secrets.get("openai", {}).get("api_key", "")
        except Exception:
            default_api_key = ""
            
        # API 키 입력 필드
        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            value=default_api_key,
            help="OpenAI API 키를 입력하세요."
        )
        
        # API 키 유효성 검증
        if api_key:
            if validate_api_key(api_key):
                st.success("✅ API 키가 유효합니다.")
                st.session_state.openai_api_key = api_key
                st.session_state.api_key_valid = True
            else:
                st.error("❌ 유효하지 않은 API 키입니다.")
                st.session_state.api_key_valid = False
        else:
            st.warning("⚠️ API 키를 입력해주세요.")
            st.session_state.api_key_valid = False
            
        st.divider()
        
        # API 키가 유효한 경우에만 나머지 기능 표시
        if not st.session_state.api_key_valid:
            st.warning("API 키를 입력하여 서비스를 이용해주세요.")
            return
        
        st.markdown("### ⛰️ 등산 용품 관리")
        
        # 사용자 선택/생성
        if "current_user" not in st.session_state:
            st.session_state.current_user = None
            
        username = st.text_input("사용자 이름")
        if username:
            user = db.get_user(username)
            if user:
                st.session_state.current_user = user
                st.success(f"환영합니다, {username}님!")
            else:
                if st.button("새 사용자 등록"):
                    user_id = db.create_user(username)
                    if user_id:
                        st.session_state.current_user = db.get_user(username)
                        st.success("사용자 등록이 완료되었습니다!")
                    else:
                        st.error("사용자 등록에 실패했습니다.")
        
        st.divider()
        
        # 등산 용품 관리 메뉴 (로그인된 사용자만)
        if st.session_state.current_user:
            menu = st.radio(
                "메뉴 선택",
                ["용품 목록", "새 용품 추가", "용품 상태 관리"]
            )
            
            if menu == "새 용품 추가":
                categories = db.get_categories()
                category_names = [cat[0] for cat in categories]
                
                with st.form("add_gear_form"):
                    item_name = st.text_input("용품명")
                    category = st.selectbox("카테고리", category_names)
                    brand = st.text_input("브랜드")
                    price = st.number_input("가격", min_value=0)
                    purchase_date = st.date_input("구매일")
                    notes = st.text_area("메모")
                    
                    if st.form_submit_button("추가"):
                        item_data = {
                            "item_name": item_name,
                            "category": category,
                            "brand": brand,
                            "price": price,
                            "purchase_date": purchase_date.strftime("%Y-%m-%d"),
                            "notes": notes
                        }
                        if db.add_hiking_gear(st.session_state.current_user[0], item_data):
                            st.success("용품이 추가되었습니다!")
                        else:
                            st.error("용품 추가에 실패했습니다.")
            
            elif menu == "용품 목록":
                if st.button("목록 새로고침"):
                    st.rerun()
                    
                items = db.get_user_gear(st.session_state.current_user[0])
                if items:
                    current_category = None
                    for item in items:
                        if item[3] != current_category:
                            current_category = item[3]
                            st.markdown(f"#### 📁 {current_category}")
                        
                        col1, col2, col3 = st.columns([3, 2, 1])
                        with col1:
                            st.write(f"**{item[2]}**")
                        with col2:
                            st.write(f"{item[4] or ''}")
                        with col3:
                            st.write(f"상태: {item[9]}")
                else:
                    st.info("등록된 용품이 없습니다.")
            
            elif menu == "용품 상태 관리":
                items = db.get_user_gear(st.session_state.current_user[0])
                if items:
                    for item in items:
                        with st.expander(f"{item[2]} ({item[4] or '브랜드 없음'})"):
                            new_condition = st.selectbox(
                                "상태",
                                ["최상", "좋음", "보통", "수리필요", "교체필요"],
                                key=f"condition_{item[0]}",
                                index=["최상", "좋음", "보통", "수리필요", "교체필요"].index(item[9]) if item[9] in ["최상", "좋음", "보통", "수리필요", "교체필요"] else 0
                            )
                            last_used = st.date_input(
                                "마지막 사용일",
                                value=None,
                                key=f"last_used_{item[0]}"
                            )
                            if st.button("업데이트", key=f"update_{item[0]}"):
                                if db.update_gear_condition(
                                    item[0],
                                    new_condition,
                                    last_used.strftime("%Y-%m-%d") if last_used else None
                                ):
                                    st.success("상태가 업데이트되었습니다.")
                                else:
                                    st.error("업데이트 실패")
                else:
                    st.info("등록된 용품이 없습니다.")

        # 로그아웃 버튼
        if st.session_state.current_user:
            st.divider()
            if st.button("로그아웃"):
                st.session_state.current_user = None
                st.rerun()
