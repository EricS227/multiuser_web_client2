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
COPY start.py ./

# Add current directory to Python path
ENV PYTHONPATH=/app

# Expose port (Railway will override with PORT env var)
EXPOSE $PORT
EXPOSE 8000

# Start the application
CMD ["python", "start.py"]