FROM python:3.11-slim

WORKDIR /app

# 安装 onnxruntime 所需的系统库
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖（包含 rapidocr_onnxruntime）
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目所有必要文件
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/
COPY example/ /app/example/
COPY ui/ /app/ui/

# 创建 uploads 目录
RUN mkdir -p /app/uploads

# 工作目录设为 backend，确保 database.py 的相对路径正确
WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
