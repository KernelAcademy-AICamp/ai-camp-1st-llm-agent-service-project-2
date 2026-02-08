# Data Pipeline Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy libs (공통 라이브러리)
COPY libs/ ./libs/

# Install libs
RUN pip install --no-cache-dir -e libs/domain-model && \
    pip install --no-cache-dir -e libs/rag-core

# Copy data-pipeline code
COPY apps/data-pipeline/ ./apps/data-pipeline/

# Install data-pipeline dependencies
RUN pip install --no-cache-dir -r apps/data-pipeline/requirements.txt

# Set working directory
WORKDIR /app/apps/data-pipeline

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Default command (can be overridden)
CMD ["python", "main.py", "--help"]
