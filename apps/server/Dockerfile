FROM python:3.12-slim AS base

WORKDIR /app

# 安装系统依赖 + Python 依赖（这一层会被 Docker 缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Playwright Chromium 及其系统依赖（供定期 admin 网页截图任务使用）
# 国内服务器直连 Debian 官方源不稳定（apt 退出码 100）：apt 换阿里源。
# 浏览器二进制（167MB）在国内构建机上经常龟速/失败：默认跳过（INSTALL_CHROMIUM=false），
# 需要 screenshot 能力时用 --build-arg INSTALL_CHROMIUM=true 重建，
# 或在运行中的容器内手动 `playwright install chromium`。
ARG INSTALL_CHROMIUM=false
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g; s|security.debian.org|mirrors.aliyun.com|g' \
        /etc/apt/sources.list.d/debian.sources 2>/dev/null \
    || sed -i 's|deb.debian.org|mirrors.aliyun.com|g; s|security.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list \
    && playwright install-deps chromium \
    && if [ "$INSTALL_CHROMIUM" = "true" ]; then \
           playwright install chromium || echo "WARN: chromium 下载失败，admin 截图任务不可用"; \
       else \
           echo "SKIP: chromium 未安装（INSTALL_CHROMIUM=false），截图任务不可用"; \
       fi \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# 生产阶段：复制代码
FROM base AS production
COPY . .
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
