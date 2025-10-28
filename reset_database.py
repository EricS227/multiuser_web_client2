#!/usr/bin/env python3
"""
Database Reset Script
Recreates the database with correct schema
"""

import os
from sqlmodel import SQLModel, create_engine, Session, select
from backend.models import User, Conversation, Message, AuditLog, BotInteraction, Usuario
from passlib.context import CryptContext

def reset_database():
    print("DATABASE RESET SCRIPT")
    print("=" * 30)
    
    # Database path
    db_path = "./chatapp.db"
    
    # Backup existing database
    if os.path.exists(db_path):
        backup_path = f"{db_path}.backup"
        try:
            os.rename(db_path, backup_path)
            print(f"✓ Backed up existing database to {backup_path}")
        except Exception as e:
            print(f"Warning: Could not backup database: {e}")
    
    # Create new database
    DATABASE_URL = "sqlite:///./chatapp.db"
    engine = create_engine(DATABASE_URL, echo=True)
    
    print("Creating new database tables...")
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    
    # Create default users
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    with Session(engine) as session:
        print("Creating default admin and user accounts...")
        
        # Admin user
        admin_user = User(
            email="admin@test.com",
            name="Admin",
            password_hash=pwd_context.hash("senha123"),
            role="admin"
        )
        session.add(admin_user)
        
        # Standard user
        standard_user = User(
            email="user@test.com",
            name="User", 
            password_hash=pwd_context.hash("senha1234"),
            role="user"
        )
        session.add(standard_user)
        
        session.commit()
        
        print("✓ Created admin user: admin@test.com / senha123")
        print("✓ Created standard user: user@test.com / senha1234")
    
    print("\n✅ Database reset complete!")
    print("Your application should now work without schema errors.")

if __name__ == "__main__":
    reset_database()