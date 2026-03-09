"""
知识库管理 API 路由

提供知识库文档的增删查接口。
"""

import os
import sys
import io
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.schemas import (
    DocumentInfo,
    DocumentListResponse,
    DocumentUploadResponse,
    DocumentDeleteResponse,
    ErrorResponse
)
from api.auth import verify_api_key
from src.utils.config import Config
from src.memory.vector_store import (
    get_all_documents,
    delete_document,
    add_documents_to_store
)

router = APIRouter(prefix="/api/knowledge", tags=["知识库"])


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """从 PDF 文件提取文本"""
    from pypdf import PdfReader
    
    try:
        pdf_file = io.BytesIO(file_bytes)
        reader = PdfReader(pdf_file)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n\n".join(text_parts)
    except Exception as e:
        raise ValueError(f"PDF 解析失败: {str(e)}")


def extract_text_from_docx(file_bytes: bytes) -> str:
    """从 Word 文件提取文本"""
    from docx import Document
    
    try:
        docx_file = io.BytesIO(file_bytes)
        doc = Document(docx_file)
        text_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        return "\n\n".join(text_parts)
    except Exception as e:
        raise ValueError(f"Word 文档解析失败: {str(e)}")


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="获取文档列表",
    description="返回知识库中所有文档的信息（需要认证）",
    responses={
        401: {"description": "缺少 API Key"},
        403: {"description": "无效的 API Key"}
    }
)
async def list_documents(
    api_key: Optional[str] = Depends(verify_api_key)
) -> DocumentListResponse:
    """获取知识库中的所有文档"""
    try:
        docs = get_all_documents()
        documents = [
            DocumentInfo(source=doc["source"], chunk_count=doc["chunk_count"])
            for doc in docs
        ]
        
        return DocumentListResponse(
            documents=documents,
            total=len(documents)
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取文档列表失败: {str(e)}"
        )


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    summary="上传文档",
    description="上传文档到知识库，支持 txt、md、pdf、docx 格式（需要认证）",
    responses={
        401: {"description": "缺少 API Key"},
        403: {"description": "无效的 API Key"}
    }
)
async def upload_document(
    file: UploadFile = File(..., description="要上传的文档文件"),
    api_key: Optional[str] = Depends(verify_api_key)
) -> DocumentUploadResponse:
    """
    上传文档到知识库
    
    支持的格式：
    - txt: 纯文本文件
    - md: Markdown 文件
    - pdf: PDF 文档
    - docx: Word 文档
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件名")
    
    allowed_extensions = ['txt', 'md', 'pdf', 'docx']
    file_ext = file.filename.lower().split('.')[-1]
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {file_ext}，支持: {', '.join(allowed_extensions)}"
        )
    
    try:
        file_bytes = await file.read()
        
        if file_ext == 'pdf':
            content = extract_text_from_pdf(file_bytes)
        elif file_ext == 'docx':
            content = extract_text_from_docx(file_bytes)
        else:
            content = file_bytes.decode('utf-8')
        
        if not content.strip():
            return DocumentUploadResponse(
                success=False,
                message="文件内容为空",
                source=file.filename
            )
        
        success, msg = add_documents_to_store(content, file.filename)
        
        if success:
            Config.ensure_dirs()
            save_path = Config.DOCS_DIR / file.filename
            with open(save_path, 'wb') as f:
                f.write(file_bytes)
            
            from .chat import refresh_agent
            refresh_agent()
            
            chunk_count = int(msg.split("添加了")[1].split("个")[0]) if "添加了" in msg else None
            
            return DocumentUploadResponse(
                success=True,
                message=msg,
                source=file.filename,
                chunk_count=chunk_count
            )
        else:
            return DocumentUploadResponse(
                success=False,
                message=msg,
                source=file.filename
            )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"上传文档失败: {str(e)}"
        )


@router.delete(
    "/{source}",
    response_model=DocumentDeleteResponse,
    summary="删除文档",
    description="从知识库中删除指定文档（需要认证）",
    responses={
        401: {"description": "缺少 API Key"},
        403: {"description": "无效的 API Key"}
    }
)
async def remove_document(
    source: str,
    api_key: Optional[str] = Depends(verify_api_key)
) -> DocumentDeleteResponse:
    """
    删除知识库中的文档
    
    - **source**: 文档名称/来源
    """
    try:
        success, msg = delete_document(source)
        
        if success:
            from .chat import refresh_agent
            refresh_agent()
        
        return DocumentDeleteResponse(
            success=success,
            message=msg
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"删除文档失败: {str(e)}"
        )
