import json
import os
from langchain_core.documents import Document
from config import Config

def load_health_documents(data_files=None):
    """data 폴더의 JSON 파일을 로드하여 Document 객체로 변환합니다.
    
    Args:
        data_files (list, optional): 로드할 JSON 파일 목록. 기본값은 None으로 모든 파일 로드.
        
    Returns:
        list: Document 객체 리스트
    """
    documents = []
    
    # 기본 데이터 파일 목록
    if data_files is None:
        data_files = [
            'exercise.json',
            'nutrition.json', 
            'lifestyle.json',
            'hiking.json',
            'personalization.json'
        ]
    
    for filename in data_files:
        file_path = os.path.join(Config.DATA_DIR, filename)
        
        if not os.path.exists(file_path):
            print(f"파일을 찾을 수 없습니다: {file_path}")
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # JSON 데이터를 Document 객체로 변환
            category = filename.replace('.json', '')
            
            for item in data:
                doc = Document(
                    page_content=f"제목: {item.get('title', 'Unknown')}\n\n내용: {item.get('content', '')}",
                    metadata={
                        "source": filename,
                        "category": category,
                        "id": item.get('id', 'unknown'),
                        "title": item.get('title', 'Unknown')
                    }
                )
                documents.append(doc)
            
            print(f"{filename}: {len(data)}개 문서 로드 완료")
            
        except Exception as e:
            print(f"{filename} 로드 중 오류: {e}")
    
    return documents

def get_document_ids(documents):
    """문서 리스트에서 ID 목록을 추출합니다.
    
    Args:
        documents (list): Document 객체 리스트
        
    Returns:
        set: 문서 ID 집합
    """
    return {doc.metadata.get("id") for doc in documents if doc.metadata.get("id") != "unknown"} 