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
import chromadb
from chromadb.utils import embedding_functions


class RAGHelper:
    """RAG 文档管理：加载、嵌入、检索"""

    def __init__(self, collection_name: str = "study_materials",
                 persist_directory: str = "./chroma_db"):
        self.collection_name = collection_name
        self.persist_directory = persist_directory

        # 使用本地嵌入模型，不依赖 OpenAI API
        self._use_local_embed = True
        try:
            self.embeddings = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="paraphrase-multilingual-MiniLM-L12-v2"
            )
        except Exception:
            # 降级到默认嵌入模型
            self.embeddings = embedding_functions.DefaultEmbeddingFunction()

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200, length_function=len,
        )
        self.vectorstore = None
        self._init_store()

    def _init_store(self):
        """初始化向量数据库"""
        try:
            os.makedirs(self.persist_directory, exist_ok=True)

            if self._use_local_embed:
                # 使用 ChromaDB 原生客户端 + 本地嵌入
                self._chroma_client = chromadb.PersistentClient(
                    path=self.persist_directory,
                    settings=chromadb.config.Settings(anonymized_telemetry=False),
                )
                self._collection = self._chroma_client.get_or_create_collection(
                    name=self.collection_name,
                    embedding_function=self.embeddings,
                )
            else:
                # 降级：使用 LangChain Chroma wrapper
                self.vectorstore = Chroma(
                    collection_name=self.collection_name,
                    embedding_function=self.embeddings,
                    persist_directory=self.persist_directory,
                )
        except Exception as e:
            print(f"向量数据库初始化失败: {e}")

    def load_pdf(self, file_path: str) -> bool:
        """加载 PDF 到知识库"""
        try:
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            chunks = self.text_splitter.split_documents(documents)

            if self._use_local_embed:
                texts = [doc.page_content for doc in chunks]
                ids = [f"chunk_{self._collection.count() + i}" for i in range(len(texts))]
                metadatas = [doc.metadata for doc in chunks]
                self._collection.add(documents=texts, metadatas=metadatas, ids=ids)
            elif self.vectorstore:
                self.vectorstore.add_documents(chunks)
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

            if self._use_local_embed:
                texts = [doc.page_content for doc in chunks]
                ids = [f"chunk_{self._collection.count() + i}" for i in range(len(texts))]
                metadatas = [doc.metadata for doc in chunks]
                self._collection.add(documents=texts, metadatas=metadatas, ids=ids)
            elif self.vectorstore:
                self.vectorstore.add_documents(chunks)
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

            if self._use_local_embed:
                texts = [c.page_content for c in chunks]
                ids = [f"chunk_{self._collection.count() + i}" for i in range(len(texts))]
                metadatas = [c.metadata for c in chunks]
                self._collection.add(documents=texts, metadatas=metadatas, ids=ids)
            elif self.vectorstore:
                self.vectorstore.add_documents(chunks)
            return True
        except Exception as e:
            print(f"文本添加失败: {e}")
            return False

    def query(self, question: str, k: int = 4) -> List[str]:
        """检索相关文档"""
        try:
            if self._use_local_embed:
                results = self._collection.query(query_texts=[question], n_results=k)
                return results.get("documents", [[]])[0]
            elif self.vectorstore:
                docs = self.vectorstore.similarity_search(question, k=k)
                return [doc.page_content for doc in docs]
            return []
        except Exception as e:
            print(f"检索失败: {e}")
            return []

    def clear_db(self) -> bool:
        """清空知识库"""
        try:
            if self._use_local_embed:
                self._chroma_client.delete_collection(name=self.collection_name)
                self._collection = self._chroma_client.get_or_create_collection(
                    name=self.collection_name,
                    embedding_function=self.embeddings,
                )
            elif self.vectorstore:
                client = chromadb.PersistentClient(path=self.persist_directory)
                client.delete_collection(name=self.collection_name)
                self._init_store()
            return True
        except Exception as e:
            print(f"清空失败: {e}")
            return False

    def get_doc_count(self) -> int:
        """获取文档数量"""
        try:
            if self._use_local_embed:
                return self._collection.count()
            elif self.vectorstore:
                return self.vectorstore._collection.count()
            return 0
        except Exception:
            return 0
