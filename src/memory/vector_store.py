"""
向量存储模块

管理 ChromaDB 向量数据库，用于 RAG 知识库搜索。
"""

import os
from typing import Optional, List, Tuple
from functools import lru_cache

from langchain_core.documents import Document
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.utils.config import Config
from src.llm.kimi import get_llm


@lru_cache(maxsize=1)
def get_embeddings():
    """获取 Embedding 模型（带缓存）"""
    from langchain_huggingface import HuggingFaceEmbeddings
    
    return HuggingFaceEmbeddings(
        model_name=Config.EMBEDDING_MODEL,
        model_kwargs={'device': Config.EMBEDDING_DEVICE},
    )


def get_vector_store():
    """
    获取向量存储实例
    
    Returns:
        Chroma 向量存储实例，如果不存在则返回 None
    """
    if not os.path.exists(Config.CHROMA_DIR):
        return None
    
    try:
        from langchain_community.vectorstores import Chroma
        
        embeddings = get_embeddings()
        vector_store = Chroma(
            persist_directory=str(Config.CHROMA_DIR),
            embedding_function=embeddings,
            collection_name=Config.CHROMA_COLLECTION_NAME
        )
        return vector_store
    except Exception as e:
        print(f"向量存储加载失败: {e}")
        return None


def create_vector_store(documents: List[Document]):
    """
    创建新的向量存储
    
    Args:
        documents: 文档列表
        
    Returns:
        Chroma 向量存储实例
    """
    from langchain_community.vectorstores import Chroma
    
    Config.ensure_dirs()
    embeddings = get_embeddings()
    
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=str(Config.CHROMA_DIR),
        collection_name=Config.CHROMA_COLLECTION_NAME
    )
    
    return vector_store


def add_documents_to_store(content: str, filename: str) -> Tuple[bool, str]:
    """
    添加文档到向量存储
    
    Args:
        content: 文档内容
        filename: 文件名
        
    Returns:
        (是否成功, 消息)
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import Chroma
    
    try:
        embeddings = get_embeddings()
        
        # 分割文档
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=Config.RAG_CHUNK_SIZE,
            chunk_overlap=Config.RAG_CHUNK_OVERLAP,
        )
        
        doc = Document(page_content=content, metadata={"source": filename})
        chunks = text_splitter.split_documents([doc])
        
        # 添加到向量库
        if os.path.exists(Config.CHROMA_DIR):
            vector_store = Chroma(
                persist_directory=str(Config.CHROMA_DIR),
                embedding_function=embeddings,
                collection_name=Config.CHROMA_COLLECTION_NAME
            )
            vector_store.add_documents(chunks)
        else:
            Config.ensure_dirs()
            Chroma.from_documents(
                documents=chunks,
                embedding=embeddings,
                persist_directory=str(Config.CHROMA_DIR),
                collection_name=Config.CHROMA_COLLECTION_NAME
            )
        
        return True, f"成功添加 {len(chunks)} 个文档块"
        
    except Exception as e:
        return False, str(e)


def create_rag_tool(vector_store):
    """
    创建 RAG 知识库搜索工具
    
    Args:
        vector_store: 向量存储实例
        
    Returns:
        search_knowledge_base 工具
    """
    retriever = vector_store.as_retriever(
        search_kwargs={"k": Config.RAG_SEARCH_K}
    )
    
    rag_prompt = ChatPromptTemplate.from_template(
        """根据以下资料回答问题：

{context}

问题：{question}

请基于资料回答，如果资料中没有相关信息，请说明。回答完成后，请在末尾注明参考来源。"""
    )
    
    llm = get_llm()
    
    @tool
    def search_knowledge_base(query: str) -> str:
        """
        在本地知识库中搜索信息。知识库包含 Python、LangChain、Agent 等技术文档。
        当用户询问技术问题时，请使用此工具搜索相关信息。
        
        Args:
            query: 搜索问题或关键词
            
        Returns:
            从知识库检索到的相关信息，包含参考来源
        """
        try:
            docs = retriever.invoke(query)
            if not docs:
                return "未找到相关信息"
            
            sources = list(set(doc.metadata.get("source", "unknown") for doc in docs))
            
            context_parts = []
            for doc in docs:
                source = doc.metadata.get("source", "unknown")
                context_parts.append(f"[来源: {source}]\n{doc.page_content}")
            
            context = "\n\n---\n\n".join(context_parts)
            chain = rag_prompt | llm | StrOutputParser()
            answer = chain.invoke({"context": context, "question": query})
            
            source_note = "\n\n📚 **参考来源**: " + ", ".join(sources)
            
            return answer + source_note
            
        except Exception as e:
            return f"搜索错误: {str(e)}"
    
    return search_knowledge_base


def similarity_search(query: str, k: int = 3) -> List[Document]:
    """
    相似度搜索
    
    Args:
        query: 查询文本
        k: 返回结果数量
        
    Returns:
        相关文档列表
    """
    vector_store = get_vector_store()
    if vector_store is None:
        return []
    
    return vector_store.similarity_search(query, k=k)


def get_all_documents() -> List[dict]:
    """
    获取知识库中所有文档的信息
    
    Returns:
        文档信息列表，每个文档包含 source 和 chunk_count
    """
    from langchain_community.vectorstores import Chroma
    
    if not os.path.exists(Config.CHROMA_DIR):
        return []
    
    try:
        embeddings = get_embeddings()
        vector_store = Chroma(
            persist_directory=str(Config.CHROMA_DIR),
            embedding_function=embeddings,
            collection_name=Config.CHROMA_COLLECTION_NAME
        )
        
        collection = vector_store._collection
        results = collection.get(include=["metadatas"])
        
        if not results or not results.get("metadatas"):
            return []
        
        doc_counts = {}
        for metadata in results["metadatas"]:
            source = metadata.get("source", "unknown")
            doc_counts[source] = doc_counts.get(source, 0) + 1
        
        documents = [
            {"source": source, "chunk_count": count}
            for source, count in sorted(doc_counts.items())
        ]
        
        return documents
        
    except Exception as e:
        print(f"获取文档列表失败: {e}")
        return []


def delete_document(source: str) -> Tuple[bool, str]:
    """
    从知识库中删除指定文档
    
    Args:
        source: 文档来源名称（文件名）
        
    Returns:
        (是否成功, 消息)
    """
    from langchain_community.vectorstores import Chroma
    
    if not os.path.exists(Config.CHROMA_DIR):
        return False, "知识库不存在"
    
    try:
        embeddings = get_embeddings()
        vector_store = Chroma(
            persist_directory=str(Config.CHROMA_DIR),
            embedding_function=embeddings,
            collection_name=Config.CHROMA_COLLECTION_NAME
        )
        
        collection = vector_store._collection
        results = collection.get(
            where={"source": source},
            include=["metadatas"]
        )
        
        if not results or not results.get("ids"):
            return False, f"未找到文档: {source}"
        
        ids_to_delete = results["ids"]
        collection.delete(ids=ids_to_delete)
        
        doc_path = Config.DOCS_DIR / source
        if doc_path.exists():
            doc_path.unlink()
        
        return True, f"成功删除 {len(ids_to_delete)} 个文档块"
        
    except Exception as e:
        return False, f"删除失败: {str(e)}"


def similarity_search_with_source(query: str, k: int = 3) -> Tuple[List[Document], List[str]]:
    """
    相似度搜索并返回来源信息
    
    Args:
        query: 查询文本
        k: 返回结果数量
        
    Returns:
        (相关文档列表, 来源文件名列表)
    """
    vector_store = get_vector_store()
    if vector_store is None:
        return [], []
    
    docs = vector_store.similarity_search(query, k=k)
    sources = list(set(doc.metadata.get("source", "unknown") for doc in docs))
    
    return docs, sources
