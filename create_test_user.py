"""
Create a test user directly in the database
Run this to create an admin user for testing
"""
import os
from sqlmodel import Session, create_engine, select
from backend.models import User
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chatapp.db")
print(f"Connecting to: {DATABASE_URL}")

engine = create_engine(DATABASE_URL)

# Create test user
with Session(engine) as session:
    # Check if user exists
    existing = session.exec(select(User).where(User.email == "admin@test.com")).first()

    if existing:
        print("User admin@test.com already exists!")
        print(f"ID: {existing.id}, Name: {existing.name}, Role: {existing.role}")
    else:
        # Create new admin user
        admin = User(
            name="Admin",
            email="admin@test.com",
            password_hash=hash_password("admin123"),
            role="admin"
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)
        print(f"✅ Created admin user!")
        print(f"Email: admin@test.com")
        print(f"Password: admin123")
        print(f"Role: admin")
        print(f"ID: {admin.id}")
