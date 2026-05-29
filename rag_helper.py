"""
=============================================================================
A3 v2 RAG 助手 —— ChromaDB 文档检索增强生成
基于 Multi-Agent-Study-Assistant 二改
=============================================================================
"""
import os
from typing import List, Optional

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# chromadb 懒加载（Streamlit Cloud 上 protobuf/opentelemetry 版本冲突，延迟到实际使用时 import）
_chromadb = None
_embedding_functions = None

def _get_chromadb():
    global _chromadb
    if _chromadb is None:
        import chromadb as _c
        _chromadb = _c
    return _chromadb

def _get_embedding_functions():
    global _embedding_functions
    if _embedding_functions is None:
        from chromadb.utils import embedding_functions as _ef
        _embedding_functions = _ef
    return _embedding_functions


class RAGHelper:
    """RAG 文档管理：加载、嵌入、检索

    注意：SentenceTransformer 模型下载延迟到首次实际使用时（lazy init），
    避免在页面加载阶段因 Hugging Face 不可达导致整个应用卡死。
    """

    def __init__(self, collection_name: str = "study_materials",
                 persist_directory: str = "./chroma_db"):
        self.collection_name = collection_name
        self.persist_directory = persist_directory

        self._use_local_embed = None  # None = 尚未决定，延迟初始化
        self.embeddings = None
        self._embed_init_error = None

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200, length_function=len,
        )
        self.vectorstore = None
        self._init_store()

    def _ensure_embedding(self):
        """延迟加载嵌入模型（首次真正需要时才下载）"""
        if self.embeddings is not None:
            return
        self._use_local_embed = True
        try:
            # 设置短超时，避免在国内网络环境下长时间卡死
            import os as _os
            _os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "10")
            self.embeddings = _get_embedding_functions().SentenceTransformerEmbeddingFunction(
                model_name="paraphrase-multilingual-MiniLM-L12-v2"
            )
        except Exception as e:
            self._embed_init_error = str(e)
            self._use_local_embed = False
            self.embeddings = _get_embedding_functions().DefaultEmbeddingFunction()

    def _init_store(self):
        """初始化向量数据库（Chromadb 客户端本身不依赖嵌入模型，可提前初始化）"""
        try:
            os.makedirs(self.persist_directory, exist_ok=True)
            self._chroma_client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=chromadb.config.Settings(anonymized_telemetry=False),
            )
            # 暂不创建 collection（需要 embedding function，延迟到首次使用时）
            self._collection = None
        except Exception as e:
            print(f"向量数据库初始化失败: {e}")

    def _get_collection(self):
        """获取或创建 collection（延迟加载 embedding function）"""
        self._ensure_embedding()
        if self._collection is None:
            self._collection = self._chroma_client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embeddings,
            )
        return self._collection

    def load_pdf(self, file_path: str) -> bool:
        """加载 PDF 到知识库"""
        try:
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            chunks = self.text_splitter.split_documents(documents)

            col = self._get_collection()
            texts = [doc.page_content for doc in chunks]
            ids = [f"chunk_{col.count() + i}" for i in range(len(texts))]
            metadatas = [doc.metadata for doc in chunks]
            col.add(documents=texts, metadatas=metadatas, ids=ids)
            return True
        except Exception as e:
            print(f"PDF加载失败: {e}")
            return False

    def load_text(self, file_path: str) -> bool:
        """加载文本文件到知识库"""
        try:
            loader = TextLoader(file_path)
            documents = loader.load()
            chunks = self.text_splitter.split_documents(documents)

            col = self._get_collection()
            texts = [doc.page_content for doc in chunks]
            ids = [f"chunk_{col.count() + i}" for i in range(len(texts))]
            metadatas = [doc.metadata for doc in chunks]
            col.add(documents=texts, metadatas=metadatas, ids=ids)
            return True
        except Exception as e:
            print(f"文本加载失败: {e}")
            return False

    def load_text_content(self, text: str, metadata: dict = None) -> bool:
        """直接加载文本内容"""
        try:
            from langchain.schema import Document
            doc = Document(page_content=text, metadata=metadata or {})
            chunks = self.text_splitter.split_documents([doc])

            col = self._get_collection()
            texts = [c.page_content for c in chunks]
            ids = [f"chunk_{col.count() + i}" for i in range(len(texts))]
            metadatas = [c.metadata for c in chunks]
            col.add(documents=texts, metadatas=metadatas, ids=ids)
            return True
        except Exception as e:
            print(f"文本添加失败: {e}")
            return False

    def query(self, question: str, k: int = 4) -> List[str]:
        """检索相关文档"""
        try:
            col = self._get_collection()
            results = col.query(query_texts=[question], n_results=k)
            return results.get("documents", [[]])[0]
        except Exception as e:
            print(f"检索失败: {e}")
            return []

    def clear_db(self) -> bool:
        """清空知识库"""
        try:
            self._chroma_client.delete_collection(name=self.collection_name)
            self._collection = None  # 下次 _get_collection 会重新创建
            return True
        except Exception as e:
            print(f"清空失败: {e}")
            return False

    def get_doc_count(self) -> int:
        """获取文档数量（不触发模型下载）"""
        try:
            if self._collection is not None:
                return self._collection.count()
            # collection 尚未创建，直接查 chromadb 客户端
            try:
                col = self._chroma_client.get_collection(name=self.collection_name)
                return col.count()
            except Exception:
                return 0
        except Exception:
            return 0
