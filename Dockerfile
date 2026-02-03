# Bunq Financial Dashboard - Production Dockerfile
FROM python:3.11-slim

LABEL maintainer="Bunq Dashboard"
LABEL description="Bunq Financial Dashboard with Vaultwarden integration"

WORKDIR /app

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements_web.txt .
RUN pip install --no-cache-dir -r requirements_web.txt

# Copy application files
COPY api_proxy.py .
COPY index.html .
COPY styles.css .
COPY app.js .

# Create directories
RUN mkdir -p /app/config /app/logs

# Volumes for persistent data
VOLUME ["/app/config", "/app/logs"]

# Expose single port for API + Frontend
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Run application
CMD ["python", "api_proxy.py"]
