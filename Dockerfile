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

# Create requirements.txt directly in Dockerfile to avoid copy issues
RUN echo 'fastapi>=0.100.0' > requirements.txt && \
    echo 'uvicorn[standard]>=0.20.0' >> requirements.txt && \
    echo 'sqlmodel>=0.0.20' >> requirements.txt && \
    echo 'python-dotenv>=1.0.0' >> requirements.txt && \
    echo 'PyJWT>=2.0.0' >> requirements.txt && \
    echo 'passlib>=1.7.0' >> requirements.txt && \
    echo 'bcrypt>=4.0.0' >> requirements.txt && \
    echo 'twilio>=8.0.0' >> requirements.txt && \
    echo 'httpx>=0.25.0' >> requirements.txt && \
    echo 'requests>=2.30.0' >> requirements.txt && \
    echo 'python-multipart>=0.0.6' >> requirements.txt && \
    echo 'jinja2>=3.1.0' >> requirements.txt && \
    echo 'aiofiles>=23.0.0' >> requirements.txt && \
    echo 'websockets>=10.0' >> requirements.txt && \
    echo 'redis>=4.0.0' >> requirements.txt && \
    echo 'pytz>=2022.1' >> requirements.txt && \
    echo 'sqlalchemy>=2.0.0' >> requirements.txt && \
    echo 'psycopg2-binary>=2.9.0' >> requirements.txt && \
    echo 'rasa-sdk>=3.6.0' >> requirements.txt && \
    echo 'requests-toolbelt>=1.0.0' >> requirements.txt

# Verify file integrity
RUN cat requirements.txt && echo "--- File check passed ---"

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY backend/ ./backend/
COPY static/ ./static/

# Expose port
EXPOSE 8000

# Start the application
CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}