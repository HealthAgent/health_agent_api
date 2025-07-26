import os
from config import Config
from utils.document_parser import load_health_documents
from database.vectordb_manager import VectorDBManager

def load_health_data_to_vectordb(collection_name="health_data"):
    """건강 관련 문서를 벡터 데이터베이스에 저장합니다.
    
    Args:
        collection_name (str): 생성할 컬렉션 이름
        
    Returns:
        bool: 성공 여부
    """
    print(f"건강 데이터 로딩 시작... (컬렉션: {collection_name})")
    
    # 문서 로드
    documents = load_health_documents()
    
    if not documents:
        print("로드할 문서가 없습니다.")
        return False
    
    print(f"총 {len(documents)}개 문서 로드 완료")
    
    # 벡터 데이터베이스 생성
    try:
        db_manager = VectorDBManager()
        
        # 컬렉션 존재 여부 확인
        collection_exists = db_manager.collection_exists(collection_name)
        
        # 컬렉션 생성 (기존에 있으면 덮어쓰기)
        collection = db_manager.create_collection(documents, collection_name)
        
        if collection_exists:
            print(f"기존 컬렉션 초기화 후 새로 생성 완료: {collection_name}")
        else:
            print(f"새 벡터 데이터베이스 생성 완료: {collection_name}")
        
        # 테스트 검색
        retriever = db_manager.get_retriever(collection_name)
        test_docs = retriever.invoke("혈당지수(GI)와 식이섬유")
        print(f"테스트 검색 결과: {len(test_docs)}개 문서")
        
        if test_docs:
            print(f"첫 번째 문서 미리보기: {test_docs[0].page_content[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"벡터 데이터베이스 생성 중 오류: {e}")
        return False

def main():
    """메인 실행 함수"""
    print("=" * 50)
    print("Health Agent 데이터 로딩 시스템")
    print("=" * 50)
    
    # 설정 검증
    if not Config.validate():
        print("설정을 확인해주세요.")
        return
    
    # 데이터 디렉토리 확인
    if not os.path.exists(Config.DATA_DIR):
        print(f"데이터 디렉토리를 찾을 수 없습니다: {Config.DATA_DIR}")
        return
    
    # 벡터 데이터베이스 생성
    success = load_health_data_to_vectordb()
    
    if success:
        print("\n모든 작업이 완료되었습니다.")
        print("이제 Health Agent를 사용할 수 있습니다.")
    else:
        print("\n작업 중 오류가 발생했습니다.")

if __name__ == "__main__":
    main() 