import sqlite3
import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os
from dotenv import load_dotenv
from pathlib import Path
import re

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# .env 파일 로드
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class SQLMountainService:
    """Text-to-SQL 기반 산 정보 서비스"""
    
    def __init__(self, db_path="mountains.db"):
        self.db_path = db_path
        self.llm = ChatOpenAI(api_key=OPENAI_API_KEY, model="gpt-4o-mini", temperature=0.1)
        
        # 스키마 정보
        self.schema_info = """
        테이블: mountains (총 4,686개 산 데이터)
        
        필드 구조:
        - name TEXT: 산 이름 (예: "북한산", "관악산", "청량산")
        - height TEXT: 높이 (예: "835.6", "632.2", "0") - 숫자+문자열 형태
        - location TEXT: 상세 위치 (예: "서울특별시 강북구 우이동", "경기도 광주시 남한산성면")
        - details TEXT: 산에 대한 상세 설명
        - is_100_mountain TEXT: 관리기관명 (예: "서울시청", "경기도청", "해당 없음")
        
        주요 지역: 서울, 경기, 인천, 강원, 경북, 경남, 전남, 전북, 충북, 충남, 제주
        
        샘플 데이터:
        - 북한산|835.6|서울특별시 강북구 우이동|서울의 진산...|서울시청
        - 관악산|632.2|서울특별시 관악구 신림동|관악산은 서울시...|서울시청
        - 청량산|497.1|경기도 광주시 남한산성면|성벽의 주봉...|광주시청
        - 청량산|869.7|경상북도 봉화군 명호면|아름다운 봉우리...|봉화군청
        """
    
    def process_query(self, user_query: str, conversation_history: list = None):
        """
        메인 처리 로직:
        1. 자연어 → SQL 변환 시도
        2. 성공하면 SQL 실행 → 자연어 답변
        3. 실패하면 None 반환 (일반 챗봇이 처리)
        """
        
        # 1. Text-to-SQL 변환 시도
        sql_query = self._generate_sql(user_query, conversation_history)
        
        if not sql_query or sql_query.upper().strip() == "NONE":
            logger.info(f"일반 질문으로 판단: {user_query}")
            return None  # 산 관련이 아님
        
        logger.info(f"생성된 SQL: {sql_query}")
        
        # 2. SQL 실행
        try:
            results = self._execute_sql(sql_query)
            logger.info(f"검색 결과: {len(results)}개")
        except Exception as e:
            logger.error(f"SQL 실행 오류: {e}")
            return "죄송합니다. 검색 중 오류가 발생했습니다."
        
        # 3. 자연어 답변 생성
        return self._generate_natural_response(user_query, results, conversation_history)
    
    def _generate_sql(self, user_query: str, conversation_history: list = None):
        """자연어 질문을 SQL 쿼리로 변환"""
        
        # 대화 맥락 구성
        context = ""
        if conversation_history:
            recent_context = conversation_history[-4:]  # 최근 4개만
            context = "\n".join([f"{'사용자' if i % 2 == 0 else '봇'}: {msg[:100]}..." for i, msg in enumerate(recent_context)])
        
        sql_prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 자연어 질문을 SQL 쿼리로 변환하는 전문가입니다.
            
            {schema_info}
            
            **변환 규칙**:
            1. 산 관련 질문이면 → 적절한 SQL 쿼리 생성
            2. 일반 질문이면 → "NONE" 반환
            3. height 비교 시 → CAST(height AS REAL) 사용 (0은 제외)
            4. 항상 LIMIT 20 추가 (결과 제한)
            5. LIKE 검색 시 → '%키워드%' 형태 사용
            6. 여러 조건 시 → AND/OR 적절히 사용
            
            **변환 예시**:
            
            ✅ 산 관련 질문들:
            "북한산 높이는?" 
            → SELECT name, height, location FROM mountains WHERE name LIKE '%북한산%' LIMIT 20;
            
            "서울에 있는 산들 알려줘"
            → SELECT name, height, location FROM mountains WHERE location LIKE '%서울%' ORDER BY CAST(height AS REAL) DESC LIMIT 20;
            
            "500m 이상인 산 중에서 경기도에 있는 곳"
            → SELECT name, height, location FROM mountains WHERE location LIKE '%경기%' AND CAST(height AS REAL) >= 500 AND height != '0' ORDER BY CAST(height AS REAL) DESC LIMIT 20;
            
            "청량산 어디에 있어?"
            → SELECT name, location, height FROM mountains WHERE name LIKE '%청량산%' LIMIT 20;
            
            "김해에 있는 백두산에 대해 설명해 줘"
            → SELECT name, height, location, details FROM mountains WHERE name LIKE '%백두산%' AND location LIKE '%김해%' LIMIT 20;
            
            "그래도 김해에 있는 백두산에 대해 설명해 줘"
            → SELECT name, height, location, details FROM mountains WHERE name LIKE '%백두산%' AND location LIKE '%김해%' LIMIT 20;
            
            "100대 명산 중에서 서울에 있는 산"
            → SELECT name, height, location, is_100_mountain FROM mountains WHERE location LIKE '%서울%' AND is_100_mountain != '해당 없음' LIMIT 20;
            
            "가장 높은 산 5개"
            → SELECT name, height, location FROM mountains WHERE height != '0' ORDER BY CAST(height AS REAL) DESC LIMIT 5;
            
            ❌ 일반 질문들:
            "안녕하세요" → NONE
            "오늘 날씨는?" → NONE  
            "점심 뭐 먹지?" → NONE
            "고마워" → NONE
            
            **중요**: SQL 쿼리 또는 "NONE"만 반환하세요. 다른 설명은 불필요합니다.
            
            대화 맥락:
            {context}
            
            현재 질문: {query}"""),
            ("human", "{query}")
        ])
        
        try:
            chain = sql_prompt | self.llm | StrOutputParser()
            result = chain.invoke({
                "query": user_query,
                "context": context,
                "schema_info": self.schema_info
            }).strip()
            
            # SQL 쿼리 정제
            if result.upper() == "NONE":
                return None
            
            # 혹시 markdown 코드 블록이 있으면 제거
            if "```sql" in result:
                result = result.split("```sql")[1].split("```")[0].strip()
            elif "```" in result:
                result = result.split("```")[1].split("```")[0].strip()
            
            return result
            
        except Exception as e:
            logger.error(f"SQL 생성 중 오류: {e}")
            return None
    
    def _execute_sql(self, sql_query: str):
        """SQL 쿼리 실행"""
        
        # 보안: 위험한 SQL 명령어 차단
        dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE"]
        sql_upper = sql_query.upper()
        
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                raise ValueError(f"위험한 SQL 명령어 감지: {keyword}")
        
        # SELECT 문만 허용
        if not sql_upper.strip().startswith("SELECT"):
            raise ValueError("SELECT 쿼리만 허용됩니다")
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute(sql_query)
            results = c.fetchall()
            
            # 컬럼 이름 가져오기
            column_names = [description[0] for description in c.description]
            
            # 딕셔너리 형태로 변환
            formatted_results = []
            for row in results:
                row_dict = {}
                for i, value in enumerate(row):
                    row_dict[column_names[i]] = value
                formatted_results.append(row_dict)
            
            return formatted_results
            
        finally:
            conn.close()
    
    def _generate_natural_response(self, user_query: str, results: list, conversation_history: list = None):
        """검색 결과를 자연어 답변으로 변환"""
        
        # 대화 맥락
        context = ""
        if conversation_history:
            context = "\n".join([f"{'사용자' if i % 2 == 0 else '봇'}: {msg}" for i, msg in enumerate(conversation_history[-4:])])
        
        # 결과 데이터 정리
        if not results:
            results_text = "검색 결과가 없습니다."
        else:
            results_text = f"검색된 산 정보 ({len(results)}개):\n\n"
            for i, result in enumerate(results[:10], 1):  # 최대 10개만 표시
                name = result.get('name', '정보없음')
                height = result.get('height', '정보없음')
                location = result.get('location', '정보없음')
                details = result.get('details', '')
                is_100_mountain = result.get('is_100_mountain', '')
                
                results_text += f"{i}. **{name}**\n"
                results_text += f"   • 높이: {height}m\n"
                results_text += f"   • 위치: {location}\n"
                
                if details and details != "( - )" and len(details) > 10:
                    results_text += f"   • 설명: {details[:100]}...\n"
                
                if is_100_mountain and is_100_mountain != "해당 없음":
                    results_text += f"   • 관리: {is_100_mountain}\n"
                
                results_text += "\n"
        
        response_prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 산 정보를 제공하는 친근한 가이드입니다.
            
            **중요**: 아래 검색 결과에 나와 있는 정확한 숫자와 정보만 사용하세요. 절대로 추측하거나 다른 숫자를 만들어내지 마세요.
            
            사용자의 질문과 검색 결과를 바탕으로 자연스럽고 도움이 되는 답변을 생성하세요.
            
            대화 맥락:
            {context}
            
            사용자 질문: {query}
            
            검색 결과 (이 정보만 사용하세요):
            {results}
            
            **반드시 지켜야 할 규칙**:
            1. 높이, 위치, 설명은 검색 결과에 있는 그대로만 사용
            2. 검색 결과에 "높이: 228m"라고 되어 있으면 → "228m"만 말하기
            3. 검색 결과에 "높이: 0"이거나 없으면 → "높이 정보가 없습니다"
            4. 절대로 215.5m, 430m 같은 다른 숫자 만들어내지 말기
            5. 검색 결과에 없는 추가 정보 절대 금지
            
            **답변 가이드라인**:
            - 검색 결과가 많으면 → 주요 산들을 간추려서 소개
            - 검색 결과가 적으면 → 각 산에 대해 상세히 설명  
            - 자연스럽고 친근한 말투 사용
            - 추가 궁금한 점이 있는지 물어보기"""),
            ("human", "{query}")
        ])
        
        try:
            chain = response_prompt | self.llm | StrOutputParser()
            response = chain.invoke({
                "query": user_query,
                "context": context,
                "results": results_text
            })
            
            return response
            
        except Exception as e:
            logger.error(f"응답 생성 중 오류: {e}")
            return f"검색 결과를 정리해드리면:\n\n{results_text}\n\n더 궁금한 점이 있으시면 말씀해 주세요!"

if __name__ == "__main__":
    # 테스트
    service = SQLMountainService()
    
    print("=== Text-to-SQL 산 정보 서비스 테스트 ===")
    
    test_queries = [
        "북한산 높이는?",
        "서울에 있는 산들 알려줘",
        "청량산 어디에 있어?",
        "500m 이상인 산 중에서 경기도에 있는 곳",
        "가장 높은 산 5개",
        "안녕하세요",  # 일반 질문
        "오늘 날씨는?"  # 일반 질문
    ]
    
    for query in test_queries:
        print(f"\n질문: {query}")
        result = service.process_query(query)
        if result:
            print(f"답변: {result[:300]}...")
        else:
            print("답변: [일반 챗봇이 처리]")
        print("-" * 80) 