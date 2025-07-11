# Use Python 3.11 runtime (stable and widely supported)
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies step by step for debugging
RUN pip install --no-cache-dir flask>=2.0.0 requests>=2.25.0 gunicorn>=20.1.0
RUN pip install --no-cache-dir --verbose -r requirements.txt

# Copy application code (essential files first)
COPY main.py .
COPY aibot.py .
COPY atlassian_mcp_integration.py .

# Expose port
EXPOSE 8080

# Health check with extended timing
HEALTHCHECK --interval=60s --timeout=30s --start-period=120s --retries=5 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the application with Gunicorn for production
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app