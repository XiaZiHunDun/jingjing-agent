"""
配置管理模块

统一管理项目配置，包括：
- 环境变量加载
- 路径配置
- 代理配置
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config:
    """项目配置类"""
    
    # 项目根目录
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    
    # 数据目录
    DATA_DIR = PROJECT_ROOT / "data"
    DOCS_DIR = DATA_DIR / "docs"
    CHROMA_DIR = DATA_DIR / "chroma_db"
    DB_PATH = DATA_DIR / "chat_history.db"
    
    # Kimi API 配置
    KIMI_API_KEY = os.getenv("KIMI_API_KEY")
    KIMI_BASE_URL = os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1")
    KIMI_MODEL = os.getenv("KIMI_MODEL", "moonshot-v1-8k")
    
    # 代理配置
    HTTP_PROXY = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
    HTTPS_PROXY = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
    
    # Embedding 模型配置
    EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DEVICE = "cpu"
    
    # RAG 配置
    RAG_CHUNK_SIZE = 500
    RAG_CHUNK_OVERLAP = 50
    RAG_SEARCH_K = 3
    
    # 向量数据库配置
    CHROMA_COLLECTION_NAME = "knowledge_base"
    
    @classmethod
    def setup_proxy(cls):
        """设置系统代理"""
        if cls.HTTP_PROXY:
            os.environ["HTTP_PROXY"] = cls.HTTP_PROXY
            os.environ["HTTPS_PROXY"] = cls.HTTP_PROXY
    
    @classmethod
    def ensure_dirs(cls):
        """确保必要的目录存在"""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.DOCS_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def validate(cls):
        """验证配置是否有效"""
        errors = []
        
        if not cls.KIMI_API_KEY:
            errors.append("KIMI_API_KEY 未设置")
        
        return errors


# 初始化时设置代理
Config.setup_proxy()

# 导出配置实例
config = Config()
