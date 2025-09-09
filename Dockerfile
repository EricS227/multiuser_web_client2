FROM python:3.9

# Install system dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    default-libmysqlclient-dev \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements.txt first for better Docker layer caching
COPY backend/requirements.txt ./

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY backend/ ./backend/
COPY static/ ./static/

# Add current directory to Python path
ENV PYTHONPATH=/app

# Railway sets PORT automatically
EXPOSE 8000
ENV PORT=8000

# Start the application (always respect Railway's $PORT)
CMD ["uvicorn", "--app-dir", "backend", "main:app", "--host", "0.0.0.0", "--port", "8000"]

