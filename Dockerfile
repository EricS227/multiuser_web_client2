FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    build-essential \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend and static directories explicitly
COPY backend/ ./backend/
COPY static/ ./static/
# Copy templates if exists (optional)
COPY template[s]/ ./templates/

# Create __init__.py to make backend a proper Python package
RUN touch /app/backend/__init__.py

# Create data directory for SQLite database
RUN mkdir -p /app/data

# Verify files are copied
RUN ls -la /app && ls -la /app/backend/

# Add current directory to Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the application with uvicorn
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

