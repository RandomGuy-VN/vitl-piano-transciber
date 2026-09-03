# ==============================================================================
#      PRODUCTION DOCKERFILE (NODE.JS BOT + PYTHON TRANSKUN AI CORE)
# ==============================================================================
FROM python:3.12-slim-bookworm AS base

# Ngăn chặn Python tạo file .pyc và hiển thị log ngay lập tức
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    NODE_ENV=production

# Cài đặt FFmpeg, SoX, Curl, Node.js và các công cụ hệ thống cần thiết
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    sox \
    libsox-fmt-all \
    curl \
    ca-certificates \
    gcc \
    g++ \
    python3-dev \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Tạo người dùng không đặc quyền (non-root) để tăng cường bảo mật
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

WORKDIR /app

# 1. Cài đặt các thư viện Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# 2. Cài đặt dependencies Node.js
COPY package.json package-lock.json* ./
RUN npm install --omit=dev

# 3. Sao chép toàn bộ mã nguồn ứng dụng
COPY . .

# Phân quyền cho script thực thi và người dùng appuser
RUN chmod +x start.sh && \
    chown -R appuser:appgroup /app /home/appuser

# Chuyển sang người dùng an toàn appuser
USER appuser

# Expose cổng Web Health Server cho Cloud PaaS (Railway, Render, Fly.io)
EXPOSE 8080

# Cấu hình kiểm tra sức khỏe Container
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/health || exit 1

# Lệnh khởi chạy đồng thời Python AI Core và Node.js Discord Bot
CMD ["bash", "start.sh"]
