from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor
from langchain_openai import ChatOpenAI
from config import Config

class VectorDBManager:
    def __init__(self):
        self.config = Config()
        self.embeddings_model = OpenAIEmbeddings(
            api_key=self.config.OPENAI_API_KEY,
            model=self.config.EMBEDDING_MODEL
        )
        
        # LLM 기반 압축기 사용 (CrossEncoder 대신)
        llm = ChatOpenAI(
            api_key=self.config.OPENAI_API_KEY,
            model=self.config.LLM_MODEL,
            temperature=0
        )
        self.compressor = LLMChainExtractor.from_llm(llm)
        
        self.collections = {}
    
    def create_collection(self, documents, collection_name):
        """문서 컬렉션을 생성하고 벡터화합니다."""
        db = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings_model,
            collection_name=collection_name,
            persist_directory=self.config.DB_DIR,
        )
        self.collections[collection_name] = db
        return db
    
    def update_collection(self, documents, collection_name):
        """기존 컬렉션에 문서를 추가하되, 중복 문서는 제외합니다."""
        # 기존 컬렉션 로드 시도
        try:
            db = Chroma(
                embedding_function=self.embeddings_model,
                collection_name=collection_name,
                persist_directory=self.config.DB_DIR,
            )
            self.collections[collection_name] = db
            
            # 기존 문서 ID 확인
            existing_docs = db.get()
            existing_ids = set()
            
            if existing_docs and 'metadatas' in existing_docs and existing_docs['metadatas']:
                for metadata in existing_docs['metadatas']:
                    if metadata and 'id' in metadata:
                        existing_ids.add(metadata['id'])
            
            # 중복되지 않은 문서만 필터링
            new_documents = [
                doc for doc in documents 
                if doc.metadata.get('id', 'unknown') not in existing_ids
            ]
            
            if new_documents:
                print(f"{collection_name}: {len(new_documents)}개 새 문서 추가 (중복 {len(documents) - len(new_documents)}개 제외)")
                db.add_documents(new_documents)
            else:
                print(f"{collection_name}: 모든 문서가 이미 존재함 (중복 {len(documents)}개)")
                
            return db
            
        except Exception as e:
            print(f"기존 컬렉션 로드 실패, 새로 생성합니다: {e}")
            return self.create_collection(documents, collection_name)
    
    def load_collection(self, collection_name):
        """기존 컬렉션을 로드하고 retriever를 반환합니다."""
        if collection_name in self.collections:
            return self.get_retriever(collection_name)
        
        db = Chroma(
            embedding_function=self.embeddings_model,
            collection_name=collection_name,
            persist_directory=self.config.DB_DIR,
        )
        self.collections[collection_name] = db
        return self.get_retriever(collection_name)
    
    def get_retriever(self, collection_name):
        """컬렉션에 대한 압축 retriever를 반환합니다."""
        if collection_name not in self.collections:
            self.load_collection(collection_name)
            
        retriever = ContextualCompressionRetriever(
            base_compressor=self.compressor,
            base_retriever=self.collections[collection_name].as_retriever(
                search_kwargs={"k": self.config.SEARCH_TOP_K}
            ),
        )
        return retriever
        
    def collection_exists(self, collection_name):
        """컬렉션이 존재하는지 확인합니다."""
        try:
            db = Chroma(
                embedding_function=self.embeddings_model,
                collection_name=collection_name,
                persist_directory=self.config.DB_DIR,
            )
            count = db.get()
            # 문서가 있으면 True 반환
            return count and len(count.get('ids', [])) > 0
        except Exception:
            return False 