# ==============================================================================
#                  PRODUCTION DOCKERFILE (CPU / CLOUD OPTIMIZED)
# ==============================================================================
FROM python:3.12-slim-bookworm AS base

# Ngăn chặn Python tạo file .pyc và bật chế độ unbuffered để hiển thị log ngay lập tức
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

# Cài đặt FFmpeg, SoX, Curl và các thư viện hệ thống cần thiết
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    sox \
    libsox-fmt-all \
    curl \
    ca-certificates \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Tạo người dùng không đặc quyền (non-root) để tăng cường bảo mật
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

WORKDIR /app

# Sao chép và cài đặt các dependencies Python
COPY requirements.txt .

# Cài đặt PyTorch CPU và các thư viện cần thiết
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn ứng dụng
COPY . .

# Phân quyền cho người dùng appuser
RUN chown -R appuser:appgroup /app /home/appuser

# Chuyển sang người dùng appuser
USER appuser

# Expose cổng Web Health Server cho Cloud PaaS (Railway, Render, Fly.io)
EXPOSE 8080

# Cấu hình kiểm tra sức khỏe Container (Docker Healthcheck)
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/health || exit 1

# Lệnh khởi chạy chính
CMD ["python", "main.py"]
