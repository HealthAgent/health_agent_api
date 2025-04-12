# 🏔️ Health Agent

Health Agent는 건강 관련 정보를 제공하는 챗봇 애플리케이션입니다. 이 프로젝트는 Streamlit과 OpenAI API를 사용하여 구축되었습니다.

## 기능

-

## 환경 설정

### 필수 요구사항

- Python 3.8 이상 (ex. 3.9.6)
- OpenAI API Key

### 설치 방법

1. 저장소를 클론하기
   ```bash
   git clone https://github.com/HealthAgent/health_agent_api.git
   cd health_agent_api
   ```

2. 필요한 패키지 설치
   ```bash
   pip install -r requirements.txt
   ```

3. 각자 디렉터리로 이동
   ```bash
   cd ds #js, hj, dh
   ```

4. OpenAI API Key를 설정(생략 가능):
   - `.streamlit/secrets.toml` 파일을 생성하고 다음과 같이 API 키를 추가
   ```toml
   [openai]
   api_key = "your_api_key_here"
   ```

### 실행 방법

1. 터미널에서 다음 명령어를 실행
   ```bash
   streamlit run main.py
   ```

2. 자동 실행 or 웹 브라우저에서 `http://localhost:8501`로 접속

3. 연결 종료: `control + C`

### 사용 방법

- 사이드바에서 OpenAI API Key를 입력 (toml 파일 생성 시 자동 입력 됩니다)