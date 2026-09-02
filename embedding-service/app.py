"""
Embedding 微服务
基于 bge-large-zh-v1.5 模型
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer
from typing import List
import torch
import os
from loguru import logger
import sys

# 配置日志
logger.remove()
logger.add(sys.stdout, level="INFO")

# 创建 FastAPI 应用
app = FastAPI(
    title="Embedding 服务",
    description="基于 bge-large-zh-v1.5 的文本向量化服务",
    version="1.0.0"
)

# 模型配置
MODEL_NAME = os.getenv("MODEL_NAME", "BAAI/bge-large-zh-v1.5")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "32"))
MAX_LENGTH = int(os.getenv("MAX_LENGTH", "512"))

# 全局模型实例
model = None

@app.on_event("startup")
async def load_model():
    """启动时加载模型"""
    global model
    logger.info(f"加载模型: {MODEL_NAME}")
    logger.info(f"设备: {DEVICE}")
    
    try:
        model = SentenceTransformer(MODEL_NAME, device=DEVICE)
        logger.info(f"模型加载成功，维度: {model.get_sentence_embedding_dimension()}")
    except Exception as e:
        logger.error(f"模型加载失败: {e}")
        raise

# ==================== 请求/响应模型 ====================

class EmbedRequest(BaseModel):
    """单文本 embedding 请求"""
    text: str = Field(..., description="输入文本", min_length=1, max_length=5000)

class EmbedResponse(BaseModel):
    """单文本 embedding 响应"""
    embedding: List[float] = Field(..., description="向量")
    dimension: int = Field(..., description="维度")

class EmbedBatchRequest(BaseModel):
    """批量 embedding 请求"""
    texts: List[str] = Field(..., description="文本列表", min_items=1, max_items=100)

class EmbedBatchResponse(BaseModel):
    """批量 embedding 响应"""
    embeddings: List[List[float]] = Field(..., description="向量列表")
    dimension: int = Field(..., description="维度")
    count: int = Field(..., description="处理数量")

# ==================== API 端点 ====================

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "model": MODEL_NAME,
        "device": DEVICE,
        "dimension": model.get_sentence_embedding_dimension() if model else None
    }

@app.post("/embed", response_model=EmbedResponse)
async def embed_text(request: EmbedRequest):
    """
    生成单个文本的 embedding
    
    对于检索任务，需要在查询文本前加上指令前缀（BGE 模型要求）
    """
    if model is None:
        raise HTTPException(status_code=503, detail="模型未加载")
    
    try:
        # BGE 模型：查询文本需要添加指令前缀
        query_text = f"为这个句子生成表示以用于检索相关文章：{request.text}"
        
        # 生成 embedding
        embedding = model.encode(
            query_text,
            normalize_embeddings=True,  # 归一化，便于计算余弦相似度
            show_progress_bar=False
        ).tolist()
        
        return EmbedResponse(
            embedding=embedding,
            dimension=len(embedding)
        )
    
    except Exception as e:
        logger.error(f"生成 embedding 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/embed_batch", response_model=EmbedBatchResponse)
async def embed_batch(request: EmbedBatchRequest):
    """
    批量生成 embedding
    
    用于文档索引时的批量处理
    """
    if model is None:
        raise HTTPException(status_code=503, detail="模型未加载")
    
    try:
        # 文档不需要添加指令前缀
        embeddings = model.encode(
            request.texts,
            batch_size=BATCH_SIZE,
            normalize_embeddings=True,
            show_progress_bar=False
        ).tolist()
        
        return EmbedBatchResponse(
            embeddings=embeddings,
            dimension=len(embeddings[0]) if embeddings else 0,
            count=len(embeddings)
        )
    
    except Exception as e:
        logger.error(f"批量生成 embedding 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "Embedding 服务",
        "model": MODEL_NAME,
        "device": DEVICE,
        "endpoints": ["/embed", "/embed_batch", "/health"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)