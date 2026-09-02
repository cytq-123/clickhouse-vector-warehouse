FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app.py .

# 预下载模型（可选，首次运行会自动下载）
# RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-large-zh-v1.5')"

# 暴露端口
EXPOSE 8001

# 启动命令
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]