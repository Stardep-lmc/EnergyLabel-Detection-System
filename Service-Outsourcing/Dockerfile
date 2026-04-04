FROM python:3.9-slim

WORKDIR /app

# 系统依赖（OpenCV 需要 libgl）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY backend/requirements.txt backend/requirements-ml.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-ml.txt

# 后端代码
COPY backend/ ./backend/

# 前端构建产物（需要先 npm run build）
COPY frontend/web/dist/ ./frontend/web/dist/

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "backend"]