"""
Check database contents to debug chat interface
"""
import os
from sqlmodel import Session, create_engine, select
from backend.models import User, Conversation, Message
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chatapp.db")
print(f"Database: {DATABASE_URL}\n")

engine = create_engine(DATABASE_URL)

with Session(engine) as session:
    # Check conversations
    print("=" * 60)
    print("CONVERSATIONS:")
    print("=" * 60)
    conversations = session.exec(select(Conversation).order_by(Conversation.id.desc())).all()
    for conv in conversations:
        print(f"ID: {conv.id}")
        print(f"  Number: {conv.customer_number}")
        print(f"  Name: {conv.name}")
        print(f"  Status: {conv.status}")
        print(f"  Assigned to: {conv.assigned_to}")
        print(f"  Created: {conv.created_at}")
        print()

    print("=" * 60)
    print("MESSAGES:")
    print("=" * 60)
    messages = session.exec(select(Message).order_by(Message.id.desc()).limit(20)).all()
    for msg in messages:
        print(f"ID: {msg.id}, Conv: {msg.conversation_id}")
        print(f"  Sender: {msg.sender}")
        content = msg.content[:80] if msg.content else ""
        print(f"  Content: {content}...")
        print(f"  Type: {msg.message_type}")
        print(f"  Timestamp: {msg.timestamp}")
        print()

    # Count total
    total_convs = len(conversations)
    total_msgs = session.exec(select(Message)).all()
    print("=" * 60)
    print(f"TOTAL: {total_convs} conversations, {len(total_msgs)} messages")
    print("=" * 60)
