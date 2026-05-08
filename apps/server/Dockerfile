FROM python:3.12-slim AS base

WORKDIR /app

# 安装系统依赖 + Python 依赖（这一层会被 Docker 缓存）
COPY requirements.txt .
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 生产阶段：复制代码
FROM base AS production
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
