import requests
import xml.etree.ElementTree as ET
import sqlite3
import time
import os
from dotenv import load_dotenv
from pathlib import Path
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# .env 파일 로드
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

API_KEY = os.getenv("MOUNTAIN_API_KEY_DECODED")
BASE_URL = "https://apis.data.go.kr/1400000/service/cultureInfoService2/mntInfoOpenAPI2"

class MountainDBInitializer:
    """전체 산 데이터 초기화 클래스"""
    
    def __init__(self, db_path="mountains.db"):
        self.db_path = db_path
        self.api_key = API_KEY
        self.base_url = BASE_URL
        
    def init_db(self):
        """데이터베이스 초기화"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # 기존 테이블 삭제하고 새로 생성
        c.execute('DROP TABLE IF EXISTS mountains')
        
        c.execute('''
            CREATE TABLE mountains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                height TEXT,
                location TEXT,
                details TEXT,
                is_100_mountain TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, location)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("데이터베이스 초기화 완료")
    
    def fetch_all_mountains(self):
        """모든 산 데이터 가져오기 (3,368개)"""
        if not self.api_key:
            logger.error("API 키가 설정되지 않았습니다.")
            return []
        
        all_mountains = []
        page = 1
        total_fetched = 0
        
        logger.info("전체 산 데이터 다운로드 시작...")
        
        while True:
            logger.info(f"페이지 {page} 다운로드 중... (현재까지 {total_fetched}개)")
            
            params = {
                "serviceKey": self.api_key,
                "pageNo": str(page),
                "numOfRows": "1000",  # 한 번에 1000개씩
                "searchWrd": "",  # 전체 검색 (빈 문자열)
                "resultType": "xml"
            }
            
            try:
                response = requests.get(self.base_url, params=params, timeout=30)
                response.raise_for_status()
                
                # 응답 내용 디버깅 (첫 번째 페이지만)
                if page == 1:
                    logger.info(f"API 응답 상태: {response.status_code}")
                    logger.info(f"응답 내용 (처음 500자): {response.text[:500]}")
                
                root = ET.fromstring(response.content)
                
                # 에러 체크
                result_code = root.find('.//resultCode')
                if result_code is not None:
                    code = result_code.text
                    if code == "00" or code == "0000":
                        # 성공 코드
                        pass
                    else:
                        logger.error(f"API 에러 코드: {code}")
                        result_msg = root.find('.//resultMsg')
                        if result_msg is not None:
                            logger.error(f"API 에러 메시지: {result_msg.text}")
                        break
                
                items = root.findall('.//item')
                
                if not items:
                    logger.info("더 이상 데이터가 없습니다.")
                    break
                
                page_mountains = []
                for item in items:
                    mountain_name = item.find('mntiname').text if item.find('mntiname') is not None else "정보 없음"
                    location = item.find('mntiadd').text if item.find('mntiadd') is not None else "정보 없음"
                    height = item.find('mntihigh').text if item.find('mntihigh') is not None else "정보 없음"
                    details = item.find('mntidetails').text if item.find('mntidetails') is not None else "상세 정보 없음"
                    is_100_mountain = item.find('mntiadmin').text if item.find('mntiadmin') is not None else "해당 없음"
                    
                    # 산 이름 정제
                    cleaned_name = self._clean_mountain_name(mountain_name)
                    
                    mountain = {
                        'name': cleaned_name,
                        'height': height,
                        'location': location,
                        'details': details,
                        'is_100_mountain': is_100_mountain
                    }
                    page_mountains.append(mountain)
                
                all_mountains.extend(page_mountains)
                total_fetched += len(page_mountains)
                
                logger.info(f"페이지 {page} 완료: {len(page_mountains)}개 추가 (총 {total_fetched}개)")
                
                # 다음 페이지로
                page += 1
                
                # API 부하 방지를 위한 딜레이
                time.sleep(0.5)
                
                # 페이지당 데이터가 1000개 미만이면 마지막 페이지
                if len(page_mountains) < 1000:
                    break
                    
            except Exception as e:
                logger.error(f"페이지 {page} 다운로드 중 오류: {e}")
                time.sleep(2)  # 에러 시 더 긴 딜레이
                continue
        
        logger.info(f"전체 다운로드 완료: {len(all_mountains)}개 산")
        return all_mountains
    
    def _clean_mountain_name(self, raw_name):
        """산 이름 정제"""
        if not raw_name:
            return "정보 없음"
            
        cleaned = raw_name.strip()
        
        # "_" 제거 (예: "청량산_의상봉" -> "청량산")
        if '_' in cleaned:
            cleaned = cleaned.split('_')[0]
        
        # 괄호 제거 (예: "청량산(의상봉)" -> "청량산")
        if '(' in cleaned:
            cleaned = cleaned.split('(')[0].strip()
        
        return cleaned
    
    def save_all_to_db(self, mountains):
        """모든 산을 DB에 저장"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        saved_count = 0
        duplicate_count = 0
        
        logger.info("DB 저장 시작...")
        
        for i, mountain in enumerate(mountains):
            try:
                c.execute('''
                    INSERT OR IGNORE INTO mountains (name, height, location, details, is_100_mountain)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    mountain['name'],
                    mountain['height'],
                    mountain['location'],
                    mountain['details'],
                    mountain['is_100_mountain']
                ))
                
                if c.rowcount > 0:
                    saved_count += 1
                else:
                    duplicate_count += 1
                
                # 진행상황 표시
                if (i + 1) % 500 == 0:
                    logger.info(f"저장 진행: {i + 1}/{len(mountains)} (저장: {saved_count}, 중복: {duplicate_count})")
                
            except Exception as e:
                logger.error(f"산 저장 중 오류 ({mountain['name']}): {e}")
                continue
        
        conn.commit()
        conn.close()
        
        logger.info(f"DB 저장 완료 - 저장: {saved_count}개, 중복 제외: {duplicate_count}개")
        return saved_count
    
    def get_db_stats(self):
        """DB 통계 조회"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # 총 산 개수
        c.execute('SELECT COUNT(*) FROM mountains')
        total_count = c.fetchone()[0]
        
        # 지역별 통계 (상위 10개)
        c.execute('''
            SELECT 
                CASE 
                    WHEN location LIKE '%서울%' THEN '서울'
                    WHEN location LIKE '%경기%' THEN '경기'
                    WHEN location LIKE '%인천%' THEN '인천'
                    WHEN location LIKE '%강원%' THEN '강원'
                    WHEN location LIKE '%충청북도%' OR location LIKE '%충북%' THEN '충북'
                    WHEN location LIKE '%충청남도%' OR location LIKE '%충남%' THEN '충남'
                    WHEN location LIKE '%전라북도%' OR location LIKE '%전북%' THEN '전북'
                    WHEN location LIKE '%전라남도%' OR location LIKE '%전남%' THEN '전남'
                    WHEN location LIKE '%경상북도%' OR location LIKE '%경북%' THEN '경북'
                    WHEN location LIKE '%경상남도%' OR location LIKE '%경남%' THEN '경남'
                    WHEN location LIKE '%제주%' THEN '제주'
                    ELSE '기타'
                END as region,
                COUNT(*) as count
            FROM mountains 
            GROUP BY region 
            ORDER BY count DESC
            LIMIT 10
        ''')
        
        region_stats = c.fetchall()
        
        conn.close()
        
        return total_count, region_stats

def main():
    """메인 실행 함수"""
    print("=" * 50)
    print("🏔️  전국 산 데이터베이스 초기화")
    print("=" * 50)
    
    initializer = MountainDBInitializer()
    
    # 1. DB 초기화
    print("\n1. 데이터베이스 초기화 중...")
    initializer.init_db()
    
    # 2. 전체 산 데이터 다운로드
    print("\n2. 전체 산 데이터 다운로드 중...")
    all_mountains = initializer.fetch_all_mountains()
    
    if not all_mountains:
        print("❌ 데이터 다운로드 실패")
        return
    
    # 3. DB에 저장
    print("\n3. 데이터베이스에 저장 중...")
    saved_count = initializer.save_all_to_db(all_mountains)
    
    # 4. 결과 통계
    print("\n4. 초기화 완료!")
    total_count, region_stats = initializer.get_db_stats()
    
    print(f"\n📊 초기화 결과:")
    print(f"   • 전체 산 개수: {total_count}개")
    print(f"   • 신규 저장: {saved_count}개")
    print(f"\n🗺️  지역별 산 분포:")
    for region, count in region_stats:
        print(f"   • {region}: {count}개")
    
    print(f"\n✅ 전국 산 데이터베이스 초기화 완료!")
    print(f"   이제 {total_count}개 산 정보를 빠르게 검색할 수 있습니다.")

if __name__ == "__main__":
    main() 