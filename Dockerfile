FROM python:3.9-slim

# Instalar dependências do sistema ANTES de instalar os pacotes Python
RUN apt-get update && apt-get install -y \
    pkg-config \
    default-libmysqlclient-dev \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requirements primeiro
COPY requirements.txt .

# Agora instalar os pacotes Python (vai funcionar porque as dependências estão instaladas)
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o resto do código
COPY . .

# Configurar a porta
EXPOSE 8000

# Comando para iniciar
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]