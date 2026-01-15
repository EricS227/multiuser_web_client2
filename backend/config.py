import os
from sqlmodel import create_engine
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Database - Railway compatible (PostgreSQL preferred for production)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chatapp.db")

# Handle Railway PostgreSQL URL format
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, echo=False)  # Disable echo in production

# Evolution API Configuration
EVOLUTION_ENABLED = os.getenv("EVOLUTION_ENABLED", "true").lower() == "true"
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")
EVOLUTION_INSTANCE_NAME = os.getenv("EVOLUTION_INSTANCE_NAME", "")
