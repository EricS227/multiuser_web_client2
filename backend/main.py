# -*- coding: utf-8 -*-
import sys
import io
# Fix Windows console encoding issues
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request, Query, Form
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from sqlmodel import Field, SQLModel, Session, create_engine, select
from datetime import datetime, timedelta
from typing import Optional, List
import jwt
from jwt import InvalidTokenError, DecodeError
from passlib.context import CryptContext
# Twilio removed - using Evolution API only
from pydantic import BaseModel
from dotenv import load_dotenv
from datetime import timezone
from sqlalchemy import text, inspect
import asyncio
import random
from backend.enhanced_chatbot_service import EnhancedClaudeChatbotService
from backend.models import User, Conversation, Message, AuditLog, BotInteraction, BotContext, Usuario, brazilian_now
from backend.n8n_service import n8n_service
from backend.evolution_service import evolution_service

import httpx
import os
import asyncio
import requests
try:
    import anthropic
except ImportError:
    anthropic = None
import uvicorn

load_dotenv()

print("Starting FastAPI application...")

app = FastAPI()
print("FastAPI app initialized successfully")

# CORS - Configure for production
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Banco de dados - Railway compatible
print("Setting up database connection...")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chatapp.db")
print(f"Database URL: {DATABASE_URL}")

try:
    engine = create_engine(DATABASE_URL, echo=False)  # Disable echo in production
    print("Database engine created successfully")
except Exception as e:
    print(f"Error creating database engine: {e}")
    raise



# Get the absolute path to templates directory
from pathlib import Path

# Try multiple possible template directory locations
possible_template_dirs = [
    Path(__file__).parent.parent / "templates",  # ../templates (from backend/)
    Path("templates"),  # ./templates (from project root)
    Path(__file__).parent / "templates",  # ./backend/templates
]

templates_dir = None
for dir_path in possible_template_dirs:
    if dir_path.exists() and (dir_path / "cadastro.html").exists():
        templates_dir = dir_path
        break

if templates_dir:
    templates = Jinja2Templates(directory=str(templates_dir))
    print(f"Using templates directory: {templates_dir}")
else:
    print("Warning: No templates directory found!")
    templates = None

@app.get("/", response_class=HTMLResponse)
def form_html(request: Request):
    # Skip template loading due to encoding issues, use direct fallback
    print("Using inline HTML fallback for root route")
    
    # Direct inline HTML response
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Cadastro</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 400px; margin: 50px auto; padding: 20px; }
            form { background: #f5f5f5; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            input[type="text"], input[type="email"], input[type="password"] { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
            button { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
            button:hover { background: #0056b3; }
            .secondary-btn { background: #6c757d; margin-top: 10px; }
            .secondary-btn:hover { background: #545b62; }
        </style>
    </head>
    <body>
        <h2>Cadastro de Usuário</h2>
        <form id="cadastroForm">
            <input type="text" name="nome" placeholder="Nome" required><br>
            <input type="email" name="email" placeholder="Email" required><br>
            <input type="password" name="senha" placeholder="Senha" required><br>
            <button type="submit">Cadastrar</button>
        </form>
        <button class="secondary-btn" onclick="goToLogin()">Voltar para Login</button>
        <div id="mensagem"></div>
        <script>
            document.getElementById('cadastroForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                try {
                    const res = await fetch('/cadastrar', { method: 'POST', body: formData });
                    if (res.ok) {
                        const result = await res.json();
                        document.getElementById('mensagem').innerHTML = '<div style="color: green; padding: 10px; background: #d4edda; border: 1px solid #c3e6cb; border-radius: 4px; margin: 10px 0;">' + result.message + '</div>';
                        document.getElementById('cadastroForm').reset();
                        setTimeout(() => { window.location.href = 'index.html'; }, 2000);
                    } else {
                        const error = await res.json();
                        document.getElementById('mensagem').innerHTML = '<div style="color: red; padding: 10px; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px; margin: 10px 0;">Erro no cadastro</div>';
                    }
                } catch (error) {
                    document.getElementById('mensagem').innerHTML = '<div style="color: red; padding: 10px; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px; margin: 10px 0;">Erro de conexão</div>';
                }
            });
            
            function goToLogin() {
                // Clear any existing token to ensure we see the login form
                localStorage.removeItem("access_token");
                window.location.href = 'index.html';
            }
        </script>
    </body>
    </html>
    """)


# Autenticação
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    import secrets
    SECRET_KEY = secrets.token_urlsafe(32)
    print("WARNING: No SECRET_KEY found in environment. Generated temporary secret key.")
    print("For production, set SECRET_KEY environment variable in your deployment platform.")
    print(f"Generated SECRET_KEY: {SECRET_KEY}")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# WhatsApp integration via Evolution API (Twilio removed)
print("WhatsApp integration: Using Evolution API")


# Import models from models.py
# Models are now imported at the top of the file

class ConversationCreate(BaseModel):
    customer_number: str
    initial_message: str

class UsuarioCreate(BaseModel):
    nome: str
    email: str
    senha: str




# WebSocket Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: dict, recipient_number: str):
        for connection in self.active_connections:
            try:
                await connection.send_json({
                    "to": recipient_number,
                    **message
                })
            except Exception:
                self.disconnect(connection)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


class MessagePayload(BaseModel):
    message: str

# Cria as tabelas no banco
print("Creating database tables...")
try:
    SQLModel.metadata.create_all(engine)
    print("Database tables created successfully")
except Exception as e:
    print(f"Error creating database tables: {e}")
    raise



# Temporarily disabled - causing request hangs
# @app.on_event("startup")
def verificar_e_adicionar_colunas_disabled():
    with engine.connect() as conn:
        insp = inspect(conn)
        
        # Check conversation table
        conversation_columns = [col["name"] for col in insp.get_columns("conversation")]
        if "name" not in conversation_columns:
            print("Adicionando coluna 'name' à tabela conversation")
            conn.execute(text("ALTER TABLE conversation ADD COLUMN name VARCHAR"))
            conn.commit()
        
        # Check message table for new columns
        message_columns = [col["name"] for col in insp.get_columns("message")]
        
        if "message_type" not in message_columns:
            print("Adicionando coluna 'message_type' à tabela message")
            conn.execute(text("ALTER TABLE message ADD COLUMN message_type VARCHAR DEFAULT 'customer'"))
            conn.commit()
            
        if "bot_service" not in message_columns:
            print("Adicionando coluna 'bot_service' à tabela message")
            conn.execute(text("ALTER TABLE message ADD COLUMN bot_service VARCHAR"))
            conn.commit()
#with engine.connect() as conn:
   # conn.execute(text("ALTER TABLE conversation ADD COLUMN name VARCHAR"))
    #conn.commit()


# Utils
# Temporarily disabled - troubleshooting startup hangs
# @app.on_event("startup") 
def create_admin_user_disabled():
    with Session(engine) as session:
        # Cria admin se não existir
        admin = session.exec(select(User).where(User.email == "admin@test.com")).first()
        if not admin:
            admin_user = User(
                email="admin@test.com",
                name="Admin",
                password_hash=hash_password("senha123"),
                role="admin"
            )
            session.add(admin_user)

        # Cria user padrão se não existir
        standard = session.exec(select(User).where(User.email == "user@test.com")).first()
        if not standard:
            standard_user = User(
                email="user@test.com",
                name="User",
                password_hash=hash_password("senha1234"),
                role="user"
            )
            session.add(standard_user)

        # Cria usuário do sistema para conversas automáticas
        system_user = session.exec(select(User).where(User.email == "system@internal")).first()
        if not system_user:
            system_user = User(
                email="system@internal",
                name="System",
                password_hash=hash_password("system_internal_password"),
                role="system"
            )
            session.add(system_user)

        session.commit()
     
@app.post("/send_welcome_message/{to_number}")
async def enviar_mensagem(tipo: str, to_number: str, nome: str = ""):
    if tipo == "boas_vindas":
        mensagem = f"Olá {nome}, um operador entrará em contato com você em breve"
    elif tipo == "encerramento":
        mensagem = f"Olá {nome}, sua conversa foi finalizada. obrigado por entrar em contato"
    elif tipo == "atribuição":
        mensagem = f"Nova conversa atribuída a você, {nome}."
    else:
        mensagem = "Mensagem automática do sistema."

    return await send_whatsapp_message(to_number, mensagem)


def get_db():
    with Session(engine) as session:
        yield session


def get_session():
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()




def hash_password(password):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def create_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = brazilian_now() + (expires_delta or timedelta(minutes=30))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        user = session.exec(select(User).where(User.email == email)).first()
        if user is None:
            raise HTTPException(status_code=401, detail="Usuário não encontrado")
        return user
    except (InvalidTokenError, DecodeError):
        raise HTTPException(status_code=401, detail="Token inválido")



def safe_print(msg):
    """Safe print that handles encoding errors on Windows"""
    # Completely disabled to avoid any encoding issues
    pass
    # try:
    #     print(msg)


def is_within_business_hours() -> bool:
    """Check if current time is within configured business hours"""
    start_hour = os.getenv("BUSINESS_HOURS_START")
    end_hour = os.getenv("BUSINESS_HOURS_END")

    # If not configured, allow 24/7
    if not start_hour or not end_hour:
        return True

    try:
        current_hour = datetime.now().hour
        start = int(start_hour)
        end = int(end_hour)
        return start <= current_hour < end
    except:
        return True  # On error, allow sending


def check_message_limits(session: Session, phone_number: str) -> dict:
    """
    Check if we can send more messages to this number today
    Returns: {"can_send": bool, "reason": str}
    """
    max_per_day = int(os.getenv("MAX_MESSAGES_PER_DAY", "5"))
    max_per_conversation = int(os.getenv("MAX_MESSAGES_PER_CONVERSATION", "3"))

    # Check daily limit
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_interactions = session.exec(
        select(BotInteraction).where(
            BotInteraction.customer_phone == phone_number,
            BotInteraction.timestamp >= today_start
        )
    ).all()

    if len(today_interactions) >= max_per_day:
        return {"can_send": False, "reason": f"daily_limit_reached ({max_per_day})"}

    # Check conversation limit (messages in last hour)
    hour_ago = datetime.now() - timedelta(hours=1)
    recent_interactions = session.exec(
        select(BotInteraction).where(
            BotInteraction.customer_phone == phone_number,
            BotInteraction.timestamp >= hour_ago
        )
    ).all()

    if len(recent_interactions) >= max_per_conversation:
        return {"can_send": False, "reason": f"conversation_limit_reached ({max_per_conversation})"}

    return {"can_send": True, "reason": "ok"}


async def send_with_human_delay(phone_number: str, message: str):
    """Send message with random delay to appear more human"""
    min_delay = int(os.getenv("MIN_RESPONSE_DELAY", "3"))
    max_delay = int(os.getenv("MAX_RESPONSE_DELAY", "8"))

    # Random delay between min and max
    delay = random.uniform(min_delay, max_delay)
    safe_print(f"[DELAY] Waiting {delay:.1f}s before responding...")
    await asyncio.sleep(delay)

    # Send message
    await evolution_service.send_text_message(phone_number, message)
    # except UnicodeEncodeError:
    #     # Fallback: encode and decode to remove problematic characters
    #     safe_msg = str(msg).encode('ascii', 'ignore').decode('ascii')
    #     print(safe_msg)

# ngrok removed - using Evolution API webhook directly




# Send WhatsApp message using Evolution API
async def send_whatsapp_message(to_number: str, message: str):
    """
    Send WhatsApp message using Evolution API
    """

    # WARMUP MODE - Prevent auto-sending during warmup period
    warmup_mode = os.getenv("WARMUP_MODE", "false").lower() == "true"
    if warmup_mode:
        print(f"🛡️ WARMUP MODE: Skipping auto-send to {to_number} (warmup protection active)")
        return None

    # Use Evolution API
    if evolution_service.enabled:
        result = await evolution_service.send_text_message(to_number, message)
        if result:
            print(f"✅ Evolution API: Message sent to {to_number}")
            return result
        else:
            print(f"⚠️ Evolution API failed to send message")
            return None

    print("⚠️ Evolution API not enabled - WhatsApp features disabled")
    return None

def get_least_busy_agent(session: Session):
    agents = session.exec(select(User).where(User.role == "agent")).all()
    if not agents:
        return None
    
    agent_loads = {
        agent.id: session.exec(
            select(Conversation).where(
                Conversation.assigned_to == agent.id,
                Conversation.status == "pending"
            )
        ).count()
        for agent in agents
    }
    sorted_agents = sorted(agent_loads.items(), key=lambda item: item[1])
    return session.get(User, sorted_agents[0][0]) if sorted_agents else None

def chat_with_bot(message):
    try:
        response = requests.post('http://localhost:5005/webhooks/rest/webhook', json={"sender": "user", "message": message}, timeout=2)
        return response.json()
    except Exception as e:
        print(f"Bot not available: {e}")
        return None

# Test bot connection only if available
try:
    bot_response = chat_with_bot("Olá")
    if bot_response:
        print("Bot connected successfully")
except:
    print("Bot server not running - continuing without bot integration")

# Rotas

@app.get("/health")
async def health_check():
    try:
        # Test database connectivity
        with Session(engine) as session:
            session.exec(text("SELECT 1"))
        
        return {
            "status": "healthy", 
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "service": "chatapp"
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "timestamp": datetime.now().isoformat(),
            "database": "disconnected",
            "error": str(e)
        }

@app.post("/init-db")
async def init_database(db: Session = Depends(get_db)):
    """Initialize database with default admin user"""
    try:
        # Check if admin exists
        existing = db.exec(select(User).where(User.email == "admin@test.com")).first()

        if existing:
            return {
                "status": "exists",
                "message": "Admin user already exists",
                "email": "admin@test.com"
            }

        # Create default admin user
        admin = User(
            name="Admin",
            email="admin@test.com",
            password_hash=hash_password("admin123"),
            role="admin"
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        return {
            "status": "created",
            "message": "Admin user created successfully!",
            "email": "admin@test.com",
            "password": "admin123",
            "note": "Please change password after first login"
        }
    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "message": str(e)
        }

@app.post("/cadastrar")
async def cadastrar(
    nome: str = Form(...),
    email: str = Form(...),
    senha: str = Form(...),
    db: Session = Depends(get_db)
):
    print(f"=== CADASTRO REQUEST ===")
    print(f"Nome: {nome}, Email: {email}")
    try:
        # Verificar se usuário já existe
        existing_user = db.exec(select(User).where(User.email == email)).first()
        if existing_user:
            print(f"User already exists: {email}")
            raise HTTPException(status_code=400, detail="Usuário já existe com este email")

        # Criar novo usuário na tabela User (não Usuario)
        print("Creating new user...")
        novo_usuario = User(
            name=nome,
            email=email,
            password_hash=hash_password(senha),  # Hash da senha
            role="user"  # Role padrão
        )

        db.add(novo_usuario)
        db.commit()
        db.refresh(novo_usuario)
        print(f"User created successfully: ID {novo_usuario.id}")

        return {
            "message": f"Usuário {novo_usuario.name} cadastrado com sucesso!",
            "status": "success",
            "user_id": novo_usuario.id,
            "redirect": True
        }

    except HTTPException as he:
        print(f"HTTPException: {he.detail}")
        raise
    except Exception as e:
        print(f"Exception during cadastro: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")



@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    token = create_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/conversations")
def get_conversations(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    if user.role == "admin":
        conversations = session.exec(select(Conversation)).all()
    else:
        conversations = session.exec(select(Conversation).where(Conversation.assigned_to == user.id)).all()
    
    # Debug logging
    print(f"=== API CONVERSATIONS DEBUG ===")
    print(f"User role: {user.role}, User email: {user.email}")
    print(f"Returning {len(conversations)} conversations:")
    for conv in conversations:
        name_debug = f"'{conv.name}' (None: {conv.name is None}, Empty: {conv.name == ''}, Type: {type(conv.name)})"
        print(f"  Conv {conv.id}: number='{conv.customer_number}', name={name_debug}, status='{conv.status}'")
    print(f"=== END API CONVERSATIONS DEBUG ===")
    
    return conversations




@app.get("/agents/status")
def get_agents_status(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins podem acessar")
    
    agents = session.exec(select(User).where(User.role == "agent")).all()
    status = []

    for agent in agents:
        count = session.exec(
            select(Conversation).where(
                Conversation.assigned_to == agent.id,
                Conversation.status == "pending"
            )
        ).count()
        status.append({
            "agent_id": agent.id,
            "name": agent.name,
            "email": agent.email,
            "pending_conversations": count
        })
    return status

@app.post("/conversations/{conversation_id}/reply")
async def reply(conversation_id: int, payload: MessagePayload, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    conversation = session.get(Conversation, conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    
    # Allow admin, assigned agent, or conversation creator to reply
    if user.role == "admin":
        pass  # Admin can reply to any conversation
    elif conversation.assigned_to == user.id:
        pass  # Assigned agent can reply
    elif conversation.created_by == user.id:
        pass  # Creator can reply to their own conversation
    elif conversation.assigned_to is None:
        # If conversation is not assigned, allow any agent/admin to reply
        if user.role in ["admin", "agent"]:
            # Auto-assign conversation to this user
            conversation.assigned_to = user.id
            session.add(conversation)
            session.commit()
        else:
            raise HTTPException(status_code=403, detail="Você não tem permissão para responder")
    else:
        raise HTTPException(status_code=403, detail="Você não está atribuído a essa conversa")

    message = Message(
        conversation_id=conversation_id,
        sender="agent",
        message_type="agent",
        content=payload.message
    )
    session.add(message)
    session.commit()

    # Send via WhatsApp
    try:
        await send_whatsapp_message(conversation.customer_number, payload.message)
        print(f"WhatsApp message sent to {conversation.customer_number}")
    except Exception as e:
        print(f"Error sending WhatsApp message: {e}")

    # Broadcast to WebSocket clients
    try:
        await manager.broadcast({
            "id": message.id,
            "conversation_id": conversation_id,
            "sender": "agent",
            "message_type": "agent",
            "message": message.content,
            "timestamp": message.timestamp.isoformat()
        })
    except Exception as e:
        print(f"Error broadcasting message: {e}")
    
    return {"msg": "Message sent successfully"}


@app.post("/conversations/{conversation_id}/end")
async def end_conversation(conversation_id: int, db: Session = Depends(get_session), user=Depends(get_current_user)):
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="conversation not found")
    
    if user.role == "admin":
        pass
    elif conversation.assigned_to == user.id:
        pass
    else:
        raise HTTPException(status_code=403, detail="Você não está atribuído a essa conversa")
    
    if conversation.status == "closed":
        raise HTTPException(status_code=400, detail="Conversation already closed")
    
    try:
        conversation.status = "closed"
        db.commit()
        
        # Send closing message to customer
        closing_message = f"Obrigado pelo contato, {conversation.name}! Sua conversa foi finalizada. Se precisar de mais alguma coisa, estaremos aqui!"
        try:
            await send_whatsapp_message(conversation.customer_number, closing_message)
            print(f"Closing message sent to {conversation.customer_number}")
        except Exception as e:
            print(f"Error sending closing message: {e}")
        
        # Notify other agents via WebSocket
        await manager.broadcast({
            "type": "conversation_closed",
            "conversation_id": conversation_id,
            "customer_name": conversation.name,
            "closed_by": user.name
        })
        
        return {"detail": "Conversation closed successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error ending conversation")

@app.post("/conversations/{conversation_id}/status")
async def update_conversation_status(
    conversation_id: int, 
    status: str, 
    db: Session = Depends(get_session), 
    user=Depends(get_current_user)
):
    """Update conversation status (pending, active, closed)"""
    
    valid_statuses = ["pending", "active", "closed"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Permission check
    if user.role == "admin":
        pass
    elif conversation.assigned_to == user.id:
        pass
    else:
        raise HTTPException(status_code=403, detail="Access denied")
    
    old_status = conversation.status
    conversation.status = status
    db.commit()
    
    # Notify via WebSocket
    await manager.broadcast({
        "type": "status_updated",
        "conversation_id": conversation_id,
        "old_status": old_status,
        "new_status": status,
        "updated_by": user.name
    })
    
    return {"message": f"Status updated from {old_status} to {status}"}


# Legacy bot functions - now replaced by EnhancedChatbotService
# Keeping for backward compatibility if needed
async def query_rasa_bot(message: str, sender_id: str):
    try: 
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:5005/webhooks/rest/webhook",
                json={"sender": sender_id, "message": message}
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print("Erro ao consultar rasa:", e)
        return None

async def query_ollama_bot(message: str, model: str = "mistral"):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={"model": model, "prompt": message, "stream": False}
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
    except Exception as e:
        print("Erro ao consultar Ollama:", e)
        return None
  
@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """Legacy WhatsApp webhook (deprecated - use /webhook/evolution instead)"""
    return {"status": "deprecated", "message": "Use /webhook/evolution endpoint instead"}

@app.post("/webhook/whatsapp-legacy")
async def whatsapp_webhook_legacy(request: Request):
    """Legacy WhatsApp webhook for form data (deprecated)"""
    try:
        # Parse form data
        form_data = await request.form()
        from_number = form_data.get("From", "").replace("whatsapp:", "")
        message_body = form_data.get("Body", "")
        raw_profile_name = form_data.get("ProfileName")
        
        # Generate a better customer name
        if raw_profile_name and raw_profile_name.lower() not in ["none", "null", ""]:
            profile_name = raw_profile_name
        else:
            # Generate fallback name from phone number
            if from_number:
                # Extract last 4 digits for a friendly name
                last_digits = from_number[-4:] if len(from_number) >= 4 else from_number
                profile_name = f"Cliente {last_digits}"
            else:
                profile_name = "Cliente Desconhecido"

        print(f"WEBHOOK DEBUG - Received:")
        print(f"  From: {from_number}")
        print(f"  Raw ProfileName: '{raw_profile_name}'")
        print(f"  Final ProfileName: '{profile_name}'")
        print(f"  Message: {message_body}")

        if not from_number or not message_body:
            return {"status": "error", "message": "Missing data"}

        # Initialize enhanced chatbot service
        with Session(engine) as session:
            chatbot_service = EnhancedClaudeChatbotService(session)
            
            # Process message through enhanced chatbot
            result = await chatbot_service.process_message(from_number, message_body, profile_name)
            
            should_escalate = result['should_escalate']
            bot_response = result.get('bot_response')
            bot_service = result.get('bot_service', 'unknown')
            escalation_reason = result.get('escalation_reason')
            
            # Save bot interaction for analytics
            if bot_response:
                await _save_bot_interaction(
                    session, from_number, message_body, bot_response, 
                    profile_name, bot_service, should_escalate, escalation_reason
                )
                print(f"BOT ({bot_service}) responding: {bot_response}")
            
        # Handle escalation to human agent
        if should_escalate:
            print(f"ESCALATING conversation for {from_number} to human agent (reason: {escalation_reason})")
            
            # Get escalation message from chatbot service
            with Session(engine) as session:
                chatbot_service = EnhancedClaudeChatbotService(session)
                escalation_message = chatbot_service.get_escalation_message(escalation_reason, profile_name)
            
            # Create or find existing conversation with full history preservation
            with Session(engine) as session:
                # Check if conversation already exists (including any bot-only conversations)
                existing_conversation = session.exec(
                    select(Conversation).where(
                        Conversation.customer_number == from_number,
                        Conversation.status.in_(["pending", "active"])
                    )
                ).first()

                if existing_conversation:
                    # Use existing conversation and escalate it
                    conversation = existing_conversation
                    agent = get_least_busy_agent(session)
                    
                    # Update conversation for escalation
                    conversation.status = "active"  # Escalate to active status
                    if agent and not conversation.assigned_to:
                        conversation.assigned_to = agent.id
                        print(f"Escalating existing conversation {conversation.id} to agent {agent.name}")
                    else:
                        print(f"Escalating existing conversation {conversation.id} (already assigned)")
                        
                    session.add(conversation)
                    session.commit()
                else:
                    # Create new conversation for escalation
                    agent = get_least_busy_agent(session)
                    system_user = session.exec(select(User).where(User.email == "system@internal")).first()
                    if not system_user:
                        system_user = User(
                            email="system@internal",
                            name="System Bot",
                            password_hash=hash_password("system_internal_password"),
                            role="system"
                        )
                        session.add(system_user)
                        session.commit()
                        session.refresh(system_user)
                    
                    conversation = Conversation(
                        customer_number=from_number,
                        name=profile_name,
                        assigned_to=agent.id if agent else None,
                        created_by=agent.id if agent else system_user.id,
                        status="active",  # Start as active since it's escalated
                    )
                    session.add(conversation)
                    session.commit()
                    session.refresh(conversation)
                    
                    print(f"=== ESCALATION CONVERSATION DEBUG ===")
                    print(f"Created NEW escalated conversation {conversation.id}, assigned to agent {agent.name if agent else 'None'}")
                    print(f"Escalation input: number='{from_number}', name='{profile_name}'")
                    print(f"Stored in DB: id={conversation.id}, customer_number='{conversation.customer_number}', name='{conversation.name}'")
                    print(f"=== END ESCALATION CONVERSATION DEBUG ===")

                # Save current customer message (the escalation request)
                customer_msg = Message(
                    conversation_id=conversation.id,
                    sender="customer",
                    message_type="customer",
                    content=message_body
                )
                session.add(customer_msg)
                session.commit()

                # Save bot escalation message
                if escalation_message:
                    bot_msg = Message(
                        conversation_id=conversation.id,
                        sender="bot",
                        message_type="bot",
                        content=escalation_message,
                        bot_service="escalation"
                    )
                    session.add(bot_msg)
                    session.commit()

                    # Broadcast bot message to WebSocket clients
                    try:
                        asyncio.create_task(manager.broadcast({
                            "id": bot_msg.id,
                            "conversation_id": conversation.id,
                            "sender": "bot",
                            "message_type": "bot",
                            "message": escalation_message,
                            "content": escalation_message,
                            "bot_service": "escalation",
                            "timestamp": bot_msg.timestamp.isoformat()
                        }))
                    except Exception as e:
                        print(f"Error broadcasting bot message: {e}")

                # Notify agents via WebSocket with enhanced info
                try:
                    # Count previous messages in this conversation for context
                    message_count = session.exec(
                        select(Message).where(Message.conversation_id == conversation.id)
                    ).count()
                    
                    escalation_data = {
                        "type": "new_escalation",
                        "id": customer_msg.id,
                        "conversation_id": conversation.id,
                        "sender": "customer", 
                        "message_type": "customer",
                        "message": message_body,
                        "customer_name": profile_name,
                        "customer_number": from_number,
                        "timestamp": customer_msg.timestamp.isoformat(),
                        "escalation_reason": escalation_reason,
                        "bot_service": bot_service,
                        "message_history_count": message_count,
                        "conversation_status": conversation.status,
                        "assigned_agent": conversation.assigned_to
                    }
                    
                    asyncio.create_task(manager.broadcast(escalation_data))
                    print(f"Broadcasted escalation notification with {message_count} previous messages")
                    
                except Exception as e:
                    print(f"Error notifying agents: {e}")
            
            # Send escalation response
            try:
                await send_whatsapp_message(from_number, escalation_message)
            except Exception as e:
                print(f"WhatsApp send failed: {e}")
            
            return {"status": "escalated_to_agent", "response": escalation_message, "reason": escalation_reason}
        
        else:
            # Check if there's an existing conversation for this number
            with Session(engine) as session:
                existing_conversation = session.exec(
                    select(Conversation).where(Conversation.customer_number == from_number)
                    .where(Conversation.status.in_(["pending", "active"]))
                ).first()
                
                # Create conversation if none exists (for bot-only interactions)
                if not existing_conversation:
                    system_user = session.exec(select(User).where(User.email == "system@internal")).first()
                    if not system_user:
                        # Create system user if it doesn't exist
                        system_user = User(
                            email="system@internal",
                            name="System Bot",
                            password_hash=hash_password("system_internal_password"),
                            role="system"
                        )
                        session.add(system_user)
                        session.commit()
                        session.refresh(system_user)
                    
                    # Create new conversation for bot interaction
                    existing_conversation = Conversation(
                        customer_number=from_number,
                        name=profile_name,
                        created_by=system_user.id,
                        status="pending"  # Keep as pending so agents can see it
                    )
                    session.add(existing_conversation)
                    session.commit()
                    session.refresh(existing_conversation)
                    
                    print(f"=== CONVERSATION CREATION DEBUG ===")
                    print(f"Created new conversation {existing_conversation.id} for bot interaction")
                    print(f"Input values: number='{from_number}', name='{profile_name}'")
                    print(f"Stored in DB: id={existing_conversation.id}, customer_number='{existing_conversation.customer_number}', name='{existing_conversation.name}'")
                    print(f"Name is None: {existing_conversation.name is None}")
                    print(f"Name is empty: {existing_conversation.name == ''}")
                    print(f"=== END CONVERSATION DEBUG ===")
                else:
                    print(f"=== USING EXISTING CONVERSATION ===")
                    print(f"Found existing conversation {existing_conversation.id}")
                    print(f"Existing name: '{existing_conversation.name}', number: '{existing_conversation.customer_number}'")
                    print(f"=== END EXISTING CONVERSATION DEBUG ===")
                
                # Save customer message first
                customer_msg = Message(
                    conversation_id=existing_conversation.id,
                    sender="customer",
                    message_type="customer",
                    content=message_body
                )
                session.add(customer_msg)
                session.commit()
                
                # Save bot response to conversation
                bot_msg = Message(
                    conversation_id=existing_conversation.id,
                    sender="bot",
                    message_type="bot", 
                    content=bot_response,
                    bot_service=bot_service
                )
                session.add(bot_msg)
                session.commit()
                
                # Broadcast customer message to WebSocket clients
                try:
                    asyncio.create_task(manager.broadcast({
                        "id": customer_msg.id,
                        "conversation_id": existing_conversation.id,
                        "sender": "customer",
                        "message_type": "customer",
                        "message": message_body,
                        "content": message_body,
                        "customer_name": profile_name,
                        "customer_number": from_number,
                        "timestamp": customer_msg.timestamp.isoformat()
                    }))
                except Exception as e:
                    print(f"Error broadcasting customer message: {e}")
                
                # Broadcast bot message to WebSocket clients
                try:
                    asyncio.create_task(manager.broadcast({
                        "id": bot_msg.id,
                        "conversation_id": existing_conversation.id,
                        "sender": "bot",
                        "message_type": "bot",
                        "message": bot_response,
                        "content": bot_response,
                        "bot_service": bot_service,
                        "timestamp": bot_msg.timestamp.isoformat()
                    }))
                except Exception as e:
                    print(f"Error broadcasting bot message: {e}")
            
            # Send bot response
            try:
                await send_whatsapp_message(from_number, bot_response)
            except Exception as e:
                print(f"WhatsApp send failed: {e}")
            
            return {"status": "bot_response", "response": bot_response, "bot_service": bot_service}

    except Exception as e:
        print(f"ERROR in webhook: {e}")
        return {"status": "error", "message": str(e)}

# n8n Authentication Helper
def verify_n8n_webhook(request: Request) -> bool:
    """Verify n8n webhook authenticity"""
    # Check for n8n API key header
    n8n_api_key = request.headers.get("x-n8n-api-key") or request.headers.get("authorization")
    expected_key = os.getenv("N8N_API_KEY")
    
    if expected_key and n8n_api_key:
        # Remove 'Bearer ' prefix if present
        if n8n_api_key.startswith("Bearer "):
            n8n_api_key = n8n_api_key[7:]
        return n8n_api_key == expected_key
    
    # If no key configured, allow (for development)
    if not expected_key:
        print("N8N WARNING: No API key configured, allowing all requests")
        return True
        
    print("N8N ERROR: Missing or invalid API key")
    return False

# n8n Webhook Integration
@app.post("/webhook/n8n")
async def n8n_webhook(request: Request):
    """n8n webhook handler with enhanced message processing and security"""
    try:
        # Verify n8n authentication
        if not verify_n8n_webhook(request):
            print("N8N: Unauthorized webhook request")
            return {"status": "error", "message": "Unauthorized", "code": 401, "n8n_format": True}
        
        # Parse JSON payload from n8n
        data = await request.json()
        
        # Extract message data (n8n format)
        from_number = data.get("from", "").replace("whatsapp:", "")
        message_body = data.get("message", "")
        profile_name = data.get("profile_name", "Cliente")
        n8n_workflow_id = data.get("workflow_id", "unknown")
        n8n_execution_id = data.get("execution_id", "unknown")
        
        # Enhanced customer name processing
        if not profile_name or profile_name.lower() in ["none", "null", "", "cliente"]:
            if from_number:
                last_digits = from_number[-4:] if len(from_number) >= 4 else from_number
                profile_name = f"Cliente {last_digits}"
            else:
                profile_name = "Cliente n8n"
        
        print(f"N8N WEBHOOK DEBUG - Received:")
        print(f"  From: {from_number}")
        print(f"  ProfileName: '{profile_name}'")
        print(f"  Message: {message_body}")
        print(f"  Workflow ID: {n8n_workflow_id}")
        print(f"  Execution ID: {n8n_execution_id}")
        
        if not from_number or not message_body:
            return {"status": "error", "message": "Missing required data", "n8n_format": True}
        
        # Process through existing chatbot logic
        with Session(engine) as session:
            chatbot_service = EnhancedClaudeChatbotService(session)
            result = await chatbot_service.process_message(from_number, message_body, profile_name)
            
            should_escalate = result['should_escalate']
            bot_response = result.get('bot_response')
            bot_service = result.get('bot_service', 'n8n_enhanced')
            escalation_reason = result.get('escalation_reason')
            
            # Save bot interaction with n8n metadata
            if bot_response:
                await _save_bot_interaction(
                    session, from_number, message_body, bot_response, 
                    profile_name, f"{bot_service}_n8n", should_escalate, escalation_reason
                )
                print(f"N8N BOT ({bot_service}) responding: {bot_response}")
        
        # Handle escalation with n8n-specific formatting
        if should_escalate:
            print(f"N8N ESCALATING conversation for {from_number} to human agent (reason: {escalation_reason})")
            
            with Session(engine) as session:
                chatbot_service = EnhancedClaudeChatbotService(session)
                escalation_message = chatbot_service.get_escalation_message(escalation_reason, profile_name)
                
                # Create or find conversation (same logic as Twilio)
                existing_conversation = session.exec(
                    select(Conversation).where(
                        Conversation.customer_number == from_number,
                        Conversation.status.in_(["pending", "active"])
                    )
                ).first()

                if existing_conversation:
                    conversation = existing_conversation
                    agent = get_least_busy_agent(session)
                    conversation.status = "active"
                    if agent and not conversation.assigned_to:
                        conversation.assigned_to = agent.id
                        print(f"N8N: Escalating existing conversation {conversation.id} to agent {agent.name}")
                    session.add(conversation)
                    session.commit()
                else:
                    agent = get_least_busy_agent(session)
                    system_user = session.exec(select(User).where(User.email == "system@internal")).first()
                    if not system_user:
                        system_user = User(
                            email="system@internal",
                            name="System Bot",
                            password_hash=hash_password("system_internal_password"),
                            role="system"
                        )
                        session.add(system_user)
                        session.commit()
                        session.refresh(system_user)
                    
                    conversation = Conversation(
                        customer_number=from_number,
                        name=profile_name,
                        assigned_to=agent.id if agent else None,
                        created_by=agent.id if agent else system_user.id,
                        status="active"
                    )
                    session.add(conversation)
                    session.commit()
                    session.refresh(conversation)
                    
                    print(f"N8N: Created escalated conversation {conversation.id}, assigned to agent {agent.name if agent else 'None'}")

                # Save customer message
                customer_msg = Message(
                    conversation_id=conversation.id,
                    sender="customer",
                    message_type="customer",
                    content=message_body
                )
                session.add(customer_msg)
                session.commit()

                # Save escalation message
                if escalation_message:
                    bot_msg = Message(
                        conversation_id=conversation.id,
                        sender="bot",
                        message_type="bot",
                        content=escalation_message,
                        bot_service="n8n_escalation"
                    )
                    session.add(bot_msg)
                    session.commit()

                    # Broadcast to WebSocket clients
                    try:
                        asyncio.create_task(manager.broadcast({
                            "id": bot_msg.id,
                            "conversation_id": conversation.id,
                            "sender": "bot",
                            "message_type": "bot",
                            "message": escalation_message,
                            "content": escalation_message,
                            "bot_service": "n8n_escalation",
                            "timestamp": bot_msg.timestamp.isoformat()
                        }))
                    except Exception as e:
                        print(f"N8N: Error broadcasting bot message: {e}")

                # Notify agents with n8n metadata
                try:
                    message_count = session.exec(
                        select(Message).where(Message.conversation_id == conversation.id)
                    ).count()
                    
                    escalation_data = {
                        "type": "new_escalation",
                        "source": "n8n",
                        "n8n_workflow_id": n8n_workflow_id,
                        "n8n_execution_id": n8n_execution_id,
                        "id": customer_msg.id,
                        "conversation_id": conversation.id,
                        "sender": "customer",
                        "message_type": "customer", 
                        "message": message_body,
                        "customer_name": profile_name,
                        "customer_number": from_number,
                        "timestamp": customer_msg.timestamp.isoformat(),
                        "escalation_reason": escalation_reason,
                        "bot_service": bot_service,
                        "message_history_count": message_count,
                        "conversation_status": conversation.status,
                        "assigned_agent": conversation.assigned_to
                    }
                    
                    asyncio.create_task(manager.broadcast(escalation_data))
                    print(f"N8N: Broadcasted escalation notification")
                    
                except Exception as e:
                    print(f"N8N: Error notifying agents: {e}")
            
            # Return n8n-formatted escalation response
            return {
                "status": "escalated_to_agent",
                "response": escalation_message,
                "escalation_reason": escalation_reason,
                "conversation_id": conversation.id,
                "assigned_agent_id": conversation.assigned_to,
                "message_history_count": message_count,
                "n8n_format": True,
                "actions": {
                    "send_whatsapp": {
                        "to": from_number,
                        "message": escalation_message
                    },
                    "notify_agents": True,
                    "create_conversation": True
                }
            }
        
        else:
            # Handle bot-only response with n8n enhancements
            with Session(engine) as session:
                existing_conversation = session.exec(
                    select(Conversation).where(Conversation.customer_number == from_number)
                    .where(Conversation.status.in_(["pending", "active"]))
                ).first()
                
                # Create conversation for bot interactions (same as Twilio)
                if not existing_conversation:
                    system_user = session.exec(select(User).where(User.email == "system@internal")).first()
                    if not system_user:
                        system_user = User(
                            email="system@internal",
                            name="System Bot",
                            password_hash=hash_password("system_internal_password"),
                            role="system"
                        )
                        session.add(system_user)
                        session.commit()
                        session.refresh(system_user)
                    
                    existing_conversation = Conversation(
                        customer_number=from_number,
                        name=profile_name,
                        created_by=system_user.id,
                        status="pending"
                    )
                    session.add(existing_conversation)
                    session.commit()
                    session.refresh(existing_conversation)
                    
                    print(f"N8N: Created conversation {existing_conversation.id} for bot interaction")
                
                # Save customer message
                customer_msg = Message(
                    conversation_id=existing_conversation.id,
                    sender="customer",
                    message_type="customer",
                    content=message_body
                )
                session.add(customer_msg)
                session.commit()
                
                # Save bot response
                bot_msg = Message(
                    conversation_id=existing_conversation.id,
                    sender="bot",
                    message_type="bot",
                    content=bot_response,
                    bot_service=f"{bot_service}_n8n"
                )
                session.add(bot_msg)
                session.commit()
                
                # Broadcast to WebSocket clients
                try:
                    asyncio.create_task(manager.broadcast({
                        "id": customer_msg.id,
                        "conversation_id": existing_conversation.id,
                        "sender": "customer",
                        "message_type": "customer",
                        "message": message_body,
                        "content": message_body,
                        "customer_name": profile_name,
                        "customer_number": from_number,
                        "timestamp": customer_msg.timestamp.isoformat()
                    }))
                    
                    asyncio.create_task(manager.broadcast({
                        "id": bot_msg.id,
                        "conversation_id": existing_conversation.id,
                        "sender": "bot",
                        "message_type": "bot",
                        "message": bot_response,
                        "content": bot_response,
                        "bot_service": f"{bot_service}_n8n",
                        "timestamp": bot_msg.timestamp.isoformat()
                    }))
                except Exception as e:
                    print(f"N8N: Error broadcasting messages: {e}")
            
            # Return n8n-formatted bot response
            return {
                "status": "bot_response",
                "response": bot_response,
                "bot_service": f"{bot_service}_n8n",
                "conversation_id": existing_conversation.id,
                "n8n_format": True,
                "actions": {
                    "send_whatsapp": {
                        "to": from_number,
                        "message": bot_response
                    },
                    "save_conversation": True,
                    "continue_chat": True
                },
                "metadata": {
                    "workflow_id": n8n_workflow_id,
                    "execution_id": n8n_execution_id,
                    "profile_name": profile_name
                }
            }

    except Exception as e:
        print(f"N8N WEBHOOK ERROR: {e}")
        return {
            "status": "error", 
            "message": str(e),
            "n8n_format": True,
            "actions": {
                "retry": True,
                "fallback_to_twilio": True
            }
        }

# Evolution API Webhook
@app.post("/webhook/evolution")
async def evolution_webhook(request: Request):
    """
    Webhook to receive messages from Evolution API
    Evolution API will send messages to this endpoint
    """
    try:
        data = await request.json()

        # Debug log - log ALL events
        event_type = data.get("event", "unknown")
        data_keys = list(data.keys())
        print(f"[WEBHOOK] Event: {event_type}, Keys: {data_keys}")

        # Log full data for debugging (remove after fix)
        import json as json_mod
        print(f"[WEBHOOK] Full data: {json_mod.dumps(data, default=str)[:500]}")

        # Extract event type
        event = data.get("event")
        instance = data.get("instance")

        # Handle incoming messages
        if event == "messages.upsert":
            message_data = data.get("data", {})

            # Get message metadata
            key = message_data.get("key", {})
            message = message_data.get("message", {})
            pushName = message_data.get("pushName", "Cliente")

            # Ignore messages from us (TEMPORARILY DISABLED FOR TESTING)
            # from_me = key.get("fromMe", False)
            # if from_me:
            #     print("[Evolution] Ignoring message from us")
            #     return {"status": "ignored", "reason": "message from us"}

            # Extract phone number
            remote_jid = key.get("remoteJid", "")
            phone_number = remote_jid.replace("@s.whatsapp.net", "")

            # Check if number is authorized
            authorized_numbers = os.getenv("AUTHORIZED_NUMBERS", "").split(",")
            authorized_numbers = [n.strip() for n in authorized_numbers if n.strip()]

            if authorized_numbers and phone_number not in authorized_numbers:
                print(f"[WEBHOOK] Unauthorized: {phone_number}")
                return {"status": "ignored", "reason": "unauthorized number"}

            # Get message text
            conversation = message.get("conversation")
            extended_text = message.get("extendedTextMessage", {}).get("text")
            message_text = conversation or extended_text

            print(f"[WEBHOOK] From: {phone_number}, Text: {message_text[:30] if message_text else 'None'}...")

            if not message_text:
                print("[WEBHOOK] No text content")
                return {"status": "ignored", "reason": "no text content"}

            safe_print(f"[Evolution] Message from {phone_number} ({pushName}): {message_text}")

            # Process through chatbot (reuse existing logic from Twilio webhook)
            with Session(engine) as session:
                # Check business hours
                if not is_within_business_hours():
                    print("[WEBHOOK] Outside business hours")
                    return {"status": "ignored", "reason": "outside business hours"}

                # Check message limits
                limit_check = check_message_limits(session, phone_number)
                if not limit_check["can_send"]:
                    print(f"[WEBHOOK] Limit reached: {limit_check['reason']}")
                    return {"status": "ignored", "reason": limit_check["reason"]}

                print("[WEBHOOK] Processing with chatbot...")
                chatbot_service = EnhancedClaudeChatbotService(session)

                # Process message through enhanced chatbot
                result = await chatbot_service.process_message(phone_number, message_text, pushName)

                should_escalate = result['should_escalate']
                bot_response = result.get('bot_response')
                bot_service = result.get('bot_service', 'unknown')
                escalation_reason = result.get('escalation_reason')

                # Save bot interaction for analytics
                if bot_response:
                    await _save_bot_interaction(
                        session, phone_number, message_text, bot_response,
                        pushName, f"{bot_service}_evolution", should_escalate, escalation_reason
                    )
                    safe_print(f"[BOT] ({bot_service}) responding: {bot_response}")

            # Send response via Evolution API with human-like delay
            if bot_response:
                await send_with_human_delay(phone_number, bot_response)

            # Handle escalation to human agent
            if should_escalate:
                safe_print(f"[ESCALATION] Escalating conversation for {phone_number} to human agent")

                # Get escalation message
                with Session(engine) as session:
                    chatbot_service = EnhancedClaudeChatbotService(session)
                    escalation_message = chatbot_service.get_escalation_message(escalation_reason, pushName)

                    # Create or find existing conversation
                    existing_conversation = session.exec(
                        select(Conversation).where(
                            Conversation.customer_number == phone_number,
                            Conversation.status.in_(["pending", "active"])
                        )
                    ).first()

                    if existing_conversation:
                        conversation = existing_conversation
                        agent = get_least_busy_agent(session)
                        conversation.status = "active"
                        if agent and not conversation.assigned_to:
                            conversation.assigned_to = agent.id
                        session.add(conversation)
                        session.commit()
                    else:
                        # Create new conversation
                        agent = get_least_busy_agent(session)
                        system_user = session.exec(select(User).where(User.email == "system@internal")).first()

                        if not system_user:
                            system_user = User(
                                email="system@internal",
                                name="System Bot",
                                password_hash=hash_password("system_internal_password"),
                                role="system"
                            )
                            session.add(system_user)
                            session.commit()
                            session.refresh(system_user)

                        conversation = Conversation(
                            customer_number=phone_number,
                            name=pushName,
                            assigned_to=agent.id if agent else None,
                            created_by=agent.id if agent else system_user.id,
                            status="active"
                        )
                        session.add(conversation)
                        session.commit()
                        session.refresh(conversation)

                    # Save customer message
                    customer_msg = Message(
                        conversation_id=conversation.id,
                        sender="customer",
                        message_type="customer",
                        content=message_text
                    )
                    session.add(customer_msg)
                    session.commit()

                    # Save bot escalation message
                    if escalation_message:
                        bot_msg = Message(
                            conversation_id=conversation.id,
                            sender="bot",
                            message_type="bot",
                            content=escalation_message,
                            bot_service="evolution_escalation"
                        )
                        session.add(bot_msg)
                        session.commit()

                        # Broadcast to WebSocket clients
                        try:
                            asyncio.create_task(manager.broadcast({
                                "id": bot_msg.id,
                                "conversation_id": conversation.id,
                                "sender": "bot",
                                "message_type": "bot",
                                "message": escalation_message,
                                "timestamp": bot_msg.timestamp.isoformat()
                            }))
                        except Exception as e:
                            print(f"Error broadcasting: {e}")

                    # Notify agents via WebSocket
                    try:
                        escalation_data = {
                            "type": "new_escalation",
                            "source": "evolution_api",
                            "id": customer_msg.id,
                            "conversation_id": conversation.id,
                            "sender": "customer",
                            "message": message_text,
                            "customer_name": pushName,
                            "customer_number": phone_number,
                            "escalation_reason": escalation_reason,
                            "timestamp": customer_msg.timestamp.isoformat()
                        }
                        asyncio.create_task(manager.broadcast(escalation_data))
                    except Exception as e:
                        print(f"Error notifying agents: {e}")

                # Send escalation response
                if escalation_message:
                    await evolution_service.send_text_message(phone_number, escalation_message)

                return {
                    "status": "escalated_to_agent",
                    "response": escalation_message,
                    "reason": escalation_reason
                }
            else:
                # Bot handled the conversation
                with Session(engine) as session:
                    # Check if conversation exists
                    existing_conversation = session.exec(
                        select(Conversation).where(Conversation.customer_number == phone_number)
                        .where(Conversation.status.in_(["pending", "active"]))
                    ).first()

                    # Create conversation if none exists (for bot-only interactions)
                    if not existing_conversation:
                        system_user = session.exec(select(User).where(User.email == "system@internal")).first()
                        if not system_user:
                            system_user = User(
                                email="system@internal",
                                name="System Bot",
                                password_hash=hash_password("system_internal_password"),
                                role="system"
                            )
                            session.add(system_user)
                            session.commit()
                            session.refresh(system_user)

                        existing_conversation = Conversation(
                            customer_number=phone_number,
                            name=pushName,
                            created_by=system_user.id,
                            status="pending"
                        )
                        session.add(existing_conversation)
                        session.commit()
                        session.refresh(existing_conversation)

                    # Save customer message
                    customer_msg = Message(
                        conversation_id=existing_conversation.id,
                        sender="customer",
                        message_type="customer",
                        content=message_text
                    )
                    session.add(customer_msg)
                    session.commit()

                    # Save bot response
                    bot_msg = Message(
                        conversation_id=existing_conversation.id,
                        sender="bot",
                        message_type="bot",
                        content=bot_response,
                        bot_service=f"{bot_service}_evolution"
                    )
                    session.add(bot_msg)
                    session.commit()

                    # Broadcast to WebSocket clients
                    try:
                        asyncio.create_task(manager.broadcast({
                            "id": customer_msg.id,
                            "conversation_id": existing_conversation.id,
                            "sender": "customer",
                            "message_type": "customer",
                            "message": message_text,
                            "timestamp": customer_msg.timestamp.isoformat()
                        }))

                        asyncio.create_task(manager.broadcast({
                            "id": bot_msg.id,
                            "conversation_id": existing_conversation.id,
                            "sender": "bot",
                            "message_type": "bot",
                            "message": bot_response,
                            "timestamp": bot_msg.timestamp.isoformat()
                        }))
                    except Exception as e:
                        print(f"Error broadcasting messages: {e}")

                return {
                    "status": "bot_response",
                    "response": bot_response,
                    "bot_service": bot_service
                }

        # Handle connection updates
        elif event == "connection.update":
            connection_data = data.get("data", {})
            state = connection_data.get("state", "unknown")
            safe_print(f"[Evolution] Connection update - {state}")
            return {"status": "ok", "event": event}

        # Handle QR code updates
        elif event == "qrcode.updated":
            qr_data = data.get("data", {})
            safe_print("[Evolution] QR Code updated")
            return {"status": "ok", "event": event}

        return {"status": "ok", "event": event}

    except Exception as e:
        safe_print(f"[Evolution] Webhook error: {e}")
        # Don't print traceback to avoid encoding issues
        return {"status": "error", "message": str(e)}

# Test endpoint for bot without WhatsApp
@app.post("/test-bot")
async def test_bot_endpoint(request: Request):
    """Test the chatbot without WhatsApp - useful for development"""
    try:
        data = await request.json()
        from_number = data.get("phone_number", "+5511999999999")
        message_body = data.get("message", "")
        profile_name = data.get("profile_name", "Test User")
        
        if not message_body:
            return {"error": "Message is required"}
            
        print(f"TEST BOT - Message from {from_number}: {message_body}")
        
        # Use the same logic as WhatsApp webhook
        with Session(engine) as session:
            chatbot_service = EnhancedClaudeChatbotService(session)
            
            # Process message through enhanced chatbot
            result = await chatbot_service.process_message(from_number, message_body, profile_name)
            
            should_escalate = result['should_escalate']
            bot_response = result.get('bot_response')
            bot_service = result.get('bot_service', 'test')
            escalation_reason = result.get('escalation_reason')
            
            # Save bot interaction for analytics
            if bot_response:
                await _save_bot_interaction(
                    session, from_number, message_body, bot_response, 
                    profile_name, bot_service, should_escalate, escalation_reason
                )
        
        # Handle escalation (same as webhook but without WhatsApp sending)
        if should_escalate:
            print(f"TEST ESCALATION for {from_number} to human agent (reason: {escalation_reason})")
            
            with Session(engine) as session:
                chatbot_service = EnhancedClaudeChatbotService(session)
                escalation_message = chatbot_service.get_escalation_message(escalation_reason, profile_name)
                
                # Create conversation (same logic as webhook)
                conversation = session.exec(
                    select(Conversation).where(
                        Conversation.customer_number == from_number,
                        Conversation.status == "pending"
                    )
                ).first()

                if not conversation:
                    # Create new conversation
                    admin_user = session.exec(select(User).where(User.role == "admin")).first()
                    if admin_user:
                        conversation = Conversation(
                            customer_number=from_number,
                            name=profile_name,
                            created_by=admin_user.id,
                            status="pending"
                        )
                        session.add(conversation)
                        session.commit()
                        session.refresh(conversation)

                if conversation:
                    # Save customer message
                    customer_msg = Message(
                        conversation_id=conversation.id,
                        sender="customer",
                        message_type="customer",
                        content=message_body
                    )
                    session.add(customer_msg)
                    session.commit()

                    # Save bot escalation message
                    if escalation_message:
                        bot_msg = Message(
                            conversation_id=conversation.id,
                            sender="bot",
                            message_type="bot",
                            content=escalation_message,
                            bot_service="escalation"
                        )
                        session.add(bot_msg)
                        session.commit()

                        # Broadcast bot message to WebSocket clients
                        try:
                            asyncio.create_task(manager.broadcast({
                                "id": bot_msg.id,
                                "conversation_id": conversation.id,
                                "sender": "bot",
                                "message_type": "bot",
                                "message": escalation_message,
                                "content": escalation_message,
                                "bot_service": "escalation",
                                "timestamp": bot_msg.timestamp.isoformat()
                            }))
                        except Exception as e:
                            print(f"Error broadcasting bot message: {e}")

                    # Notify agents via WebSocket
                    try:
                        asyncio.create_task(manager.broadcast({
                            "type": "new_escalation",
                            "id": customer_msg.id,
                            "conversation_id": conversation.id,
                            "sender": "customer", 
                            "message_type": "customer",
                            "message": message_body,
                            "customer_name": profile_name,
                            "customer_number": from_number,
                            "timestamp": customer_msg.timestamp.isoformat(),
                            "escalation_reason": escalation_reason,
                            "bot_service": bot_service
                        }))
                    except Exception as e:
                        print(f"Error notifying agents: {e}")
            
            return {
                "status": "escalated_to_agent", 
                "bot_response": escalation_message, 
                "should_escalate": True,
                "escalation_reason": escalation_reason,
                "bot_service": bot_service,
                "conversation_created": True
            }
        else:
            return {
                "status": "bot_response", 
                "bot_response": bot_response, 
                "should_escalate": False,
                "bot_service": bot_service,
                "conversation_created": False
            }
            
    except Exception as e:
        print(f"ERROR in test bot endpoint: {e}")
        return {"status": "error", "message": str(e)}

async def _save_bot_interaction(session: Session, phone_number: str, user_message: str, bot_response: str, profile_name: str, bot_type: str = "enhanced", escalated: bool = False, escalation_reason: str = None):
    """Save bot interaction for analytics"""
    try:
        from backend.models import BotInteraction
        
        interaction = BotInteraction(
            phone_number=phone_number,
            customer_name=profile_name,
            user_message=user_message,
            bot_response=bot_response,
            bot_type=bot_type,
            escalated=escalated,
            escalation_reason=escalation_reason
        )
        
        session.add(interaction)
        session.commit()
        
        print(f"SAVED bot interaction: {phone_number} -> {user_message[:50]}... -> {bot_response[:50]}...")
    except Exception as e:
        print(f"ERROR saving bot interaction: {e}")

@app.post("/conversations/{conversation_id}/assign")
def assign_conversation(conversation_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    conversation.assigned_to = user.id
    session.add(conversation)
    session.commit()
    return {"msg": "Conversa atribuida ao operador"}

# Enhanced chatbot management endpoints
# n8n Integration Status and Helper Functions
def send_to_n8n(data: dict) -> bool:
    """Send data back to n8n workflow if configured"""
    n8n_url = os.getenv("N8N_WEBHOOK_URL")
    n8n_api_key = os.getenv("N8N_API_KEY")
    n8n_enabled = os.getenv("N8N_ENABLED", "false").lower() == "true"
    
    if not n8n_enabled or not n8n_url:
        return False
    
    try:
        headers = {"Content-Type": "application/json"}
        if n8n_api_key:
            headers["x-n8n-api-key"] = n8n_api_key
            
        response = requests.post(n8n_url, json=data, headers=headers, timeout=10)
        if response.status_code == 200:
            print(f"N8N: Successfully sent data to workflow")
            return True
        else:
            print(f"N8N: Failed to send data, status: {response.status_code}")
            return False
    except Exception as e:
        print(f"N8N: Error sending data to workflow: {e}")
        return False

@app.get("/n8n/status")
def get_n8n_status(user: User = Depends(get_current_user)):
    """Get n8n integration status"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins podem acessar")
    
    n8n_enabled = os.getenv("N8N_ENABLED", "false").lower() == "true"
    n8n_url = os.getenv("N8N_WEBHOOK_URL")
    n8n_api_key = os.getenv("N8N_API_KEY")
    
    # Test n8n connectivity if enabled
    n8n_connectivity = "disabled"
    if n8n_enabled and n8n_url:
        try:
            headers = {"Content-Type": "application/json"}
            if n8n_api_key:
                headers["x-n8n-api-key"] = n8n_api_key
                
            # Send a test ping
            response = requests.get(n8n_url.replace("/webhook", "/health"), headers=headers, timeout=5)
            if response.status_code == 200:
                n8n_connectivity = "online"
            else:
                n8n_connectivity = f"error_{response.status_code}"
        except Exception:
            n8n_connectivity = "offline"
    
    return {
        "n8n_integration": {
            "enabled": n8n_enabled,
            "webhook_url": n8n_url[:50] + "..." if n8n_url and len(n8n_url) > 50 else n8n_url,
            "api_key_configured": bool(n8n_api_key),
            "connectivity": n8n_connectivity,
            "webhook_endpoint": "/webhook/n8n"
        },
        "features": {
            "enhanced_routing": n8n_enabled,
            "workflow_automation": n8n_enabled,
            "parallel_processing": True,  # Both Twilio and n8n can work together
            "fallback_to_twilio": True
        }
    }

@app.post("/test-n8n")
async def test_n8n_webhook(request: Request, user: User = Depends(get_current_user)):
    """Test n8n webhook with sample data"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins podem acessar")
    
    try:
        # Get test data from request or use defaults
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        
        test_data = {
            "from": data.get("from", "+554196950370"),
            "message": data.get("message", "n8n test message"),
            "profile_name": data.get("profile_name", "n8n Test User"),
            "workflow_id": "test_workflow",
            "execution_id": "test_execution_123"
        }
        
        print(f"ADMIN TEST: Testing n8n webhook with data: {test_data}")
        
        # Call our own n8n webhook endpoint
        from fastapi.testclient import TestClient
        with TestClient(app) as client:
            # Add auth header for testing
            headers = {"Content-Type": "application/json"}
            n8n_api_key = os.getenv("N8N_API_KEY")
            if n8n_api_key:
                headers["x-n8n-api-key"] = n8n_api_key
            
            response = client.post("/webhook/n8n", json=test_data, headers=headers)
            
            return {
                "test_status": "completed",
                "webhook_response": response.json(),
                "status_code": response.status_code,
                "test_data": test_data
            }
            
    except Exception as e:
        return {"test_status": "error", "message": str(e)}

@app.get("/chatbot/status")
def get_chatbot_status(user: User = Depends(get_current_user)):
    """Get current chatbot service status and statistics"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins podem acessar")
    
    try:
        # Test bot services availability
        import asyncio
        async def check_services():
            claude_status = "offline"
            rasa_status = "offline"
            ollama_status = "offline"
            
            # Check Claude API
            claude_api_key = os.getenv("ANTHROPIC_API_KEY")
            if claude_api_key and anthropic:
                try:
                    claude_client = anthropic.Anthropic(api_key=claude_api_key)
                    # Simple test call
                    response = claude_client.messages.create(
                        model="claude-3-haiku-20240307",
                        max_tokens=10,
                        messages=[{"role": "user", "content": "Test"}]
                    )
                    if response:
                        claude_status = "online"
                except Exception as e:
                    print(f"Claude API test failed: {e}")
            
            # Check Rasa
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get("http://localhost:5005/webhooks/rest/webhook", timeout=2)
                    if response.status_code == 405:  # Method not allowed is expected for GET
                        rasa_status = "online"
            except:
                pass
            
            # Check Ollama
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get("http://localhost:11434/api/tags", timeout=2)
                    if response.status_code == 200:
                        ollama_status = "online"
            except:
                pass
            
            return claude_status, rasa_status, ollama_status
        
        claude_status, rasa_status, ollama_status = asyncio.run(check_services())
        
        return {
            "chatbot_service": "enhanced",
            "claude_api_status": claude_status,
            "rasa_status": rasa_status,
            "ollama_status": ollama_status,
            "fallback_bot": "always_available",
            "features": {
                "claude_integration": True,
                "multi_tier_fallback": True,
                "database_context": True,
                "smart_escalation": True,
                "permanent_fallback": True,
                "conversation_memory": True,
                "message_type_tracking": True
            }
        }
    except Exception as e:
        return {"chatbot_service": "error", "message": str(e)}

@app.post("/chatbot/clear-context/{phone_number}")
def clear_chatbot_context(phone_number: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Clear conversation context for a specific phone number"""
    if user.role not in ["admin", "agent"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    try:
        chatbot_service = EnhancedClaudeChatbotService(session)
        chatbot_service.context_manager.clear_context(phone_number)
        return {"message": f"Contexto limpo para {phone_number}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao limpar contexto: {str(e)}")

@app.post("/chatbot/cleanup-contexts")
def cleanup_expired_contexts(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Clean up expired conversation contexts"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins podem acessar")
    
    try:
        chatbot_service = EnhancedClaudeChatbotService(session)
        cleaned_count = chatbot_service.cleanup_expired_contexts()
        return {"message": f"Limpos {cleaned_count} contextos expirados com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na limpeza: {str(e)}")

@app.get("/chatbot/analytics")
def get_chatbot_analytics(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Get chatbot performance analytics"""
    if user.role not in ["admin", "agent"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    try:
        from backend.models import BotInteraction
        from sqlalchemy import func
        
        # Get basic statistics
        total_interactions = session.exec(select(func.count(BotInteraction.id))).first()
        escalated_interactions = session.exec(
            select(func.count(BotInteraction.id)).where(BotInteraction.escalated == True)
        ).first()
        
        # Bot type distribution
        bot_type_stats = session.exec(
            select(BotInteraction.bot_type, func.count(BotInteraction.id))
            .group_by(BotInteraction.bot_type)
        ).all()
        
        # Escalation reasons
        escalation_reasons = session.exec(
            select(BotInteraction.escalation_reason, func.count(BotInteraction.id))
            .where(BotInteraction.escalated == True)
            .group_by(BotInteraction.escalation_reason)
        ).all()
        
        # Recent interactions (last 24 hours)
        from datetime import datetime, timedelta
        yesterday = brazilian_now() - timedelta(days=1)
        recent_interactions = session.exec(
            select(func.count(BotInteraction.id))
            .where(BotInteraction.timestamp >= yesterday)
        ).first()
        
        success_rate = ((total_interactions - escalated_interactions) / total_interactions * 100) if total_interactions > 0 else 0
        
        return {
            "total_interactions": total_interactions,
            "escalated_interactions": escalated_interactions,
            "success_rate": round(success_rate, 2),
            "bot_type_distribution": dict(bot_type_stats),
            "escalation_reasons": dict(escalation_reasons),
            "interactions_last_24h": recent_interactions,
            "analytics_period": "all_time"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar analytics: {str(e)}")





@app.post("/fake-conversation")
def create_fake(session: Session = Depends(get_session)):
    test_name = "Test Customer Name"
    new = Conversation(
        customer_number="+554196950370", 
        name=test_name,
        status="pending",
        created_by=1  # Assume admin user exists
    )
    session.add(new)
    session.commit()
    session.refresh(new)
    
    print(f"=== FAKE CONVERSATION TEST ===")
    print(f"Created test conversation: id={new.id}")
    print(f"Input name: '{test_name}'")
    print(f"Stored name: '{new.name}' (None: {new.name is None})")
    print(f"=== END FAKE CONVERSATION TEST ===")
    
    return {"id": new.id, "name": new.name, "customer_number": new.customer_number}


@app.post("/conversations")
def create_conversation(data: ConversationCreate, user=Depends(get_current_user), session: Session = Depends(get_session)):
    #agent = get_least_busy_agent(session)


    conversation = Conversation(
        customer_number=data.customer_number,
        status="pending",
        #assigned_to=None,
        created_by=user.id
    )

    session.add(conversation)
    session.commit()
    session.refresh(conversation)

    message = Message(
        conversation_id=conversation.id,
        sender="customer",
        content=data.initial_message,
        timestamp=brazilian_now()
    )
    session.add(message)
    session.commit()

    return {"id": conversation.id, "message": "Conversa criada"}

@app.get("/conversations/{conversation_id}/messages")
def get_messages(conversation_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    
    if user.role != "admin" and conversation.assigned_to != user.id and conversation.created_by != user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    messages = session.exec(
        select(Message).where(Message.conversation_id == conversation_id)
    ).all()
    return messages

@app.get("/my-conversations")
def get_my_conversations(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    if user.role == "user":
        return session.exec(
            select(Conversation).where(Conversation.created_by == user.id)
        ).all()
    else:
        return session.exec(
            select(Conversation).where(Conversation.assigned_to == user.id)
        ).all()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            await websocket.close(code=1008)
            return
            #raise HTTPException(status_code=401, detail="Token inválido")

        with Session(engine) as session:
            user = session.exec(select(User).where(User.email == email)).first()
            if not user:
                #await websocket.send_json({"error": "Usuário inválido"})
                await websocket.close(code=1008)
                return
    except (InvalidTokenError, DecodeError):
       # await websocket.send_json({"error": "Token inválido"})
        await websocket.close(code=1008)
        return

   # await websocket.accept()
    await manager.connect(websocket)
    try:
        while True:
           # data = await websocket.receive_json()
            #await manager.broadcast(data)
            await asyncio.sleep(1000)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
       

#@app.websocket("/ws")
#async def websocket_endpoint(websocket: WebSocket):
   # await websocket.accept()
    #while True:
        #await websocket.receive_text()




# Serve arquivos estáticos HTML/JS
# Get the parent directory to access static files
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# n8n API Endpoints using new service
@app.post("/api/n8n/trigger")
async def trigger_n8n_workflow(request: Request, user: User = Depends(get_current_user)):
    """Trigger n8n workflow with custom data"""
    if user.role not in ["admin", "agent"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    try:
        data = await request.json()
        workflow_id = data.get("workflow_id", "chat")
        message_data = data.get("data", {})
        
        result = await n8n_service.send_to_workflow(workflow_id, message_data)
        return {"status": "success", "result": result}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/n8n/health")
async def get_n8n_health(user: User = Depends(get_current_user)):
    """Check n8n service health status"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins podem acessar")
    
    health_status = await n8n_service.health_check()
    return health_status

@app.post("/api/n8n/chat")
async def send_to_n8n_chat(request: Request, user: User = Depends(get_current_user)):
    """Send message to n8n chat workflow"""
    try:
        data = await request.json()
        message = data.get("message", "")
        phone_number = data.get("phone_number", "")
        customer_name = data.get("customer_name")
        conversation_id = data.get("conversation_id")
        
        if not message or not phone_number:
            return {"status": "error", "message": "Message and phone_number required"}
        
        result = await n8n_service.trigger_chat_workflow(
            message, phone_number, customer_name, conversation_id
        )
        return {"status": "success", "result": result}

    except Exception as e:
        return {"status": "error", "message": str(e)}

# ===== EVOLUTION API MANAGEMENT ENDPOINTS =====

@app.get("/api/evolution/status")
async def get_evolution_status(user: User = Depends(get_current_user)):
    """Check Evolution API instance status and connection"""
    if user.role not in ["admin", "agent"]:
        raise HTTPException(status_code=403, detail="Acesso negado")

    try:
        status = await evolution_service.get_instance_status()
        return {
            "enabled": evolution_service.enabled,
            "instance_name": evolution_service.instance_name,
            "base_url": evolution_service.base_url,
            "connection_status": status
        }
    except Exception as e:
        return {"error": str(e), "enabled": False}


@app.post("/api/evolution/create-instance")
async def create_evolution_instance(user: User = Depends(get_current_user)):
    """Create new WhatsApp instance"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins")

    try:
        result = await evolution_service.create_instance()
        if result:
            return {"status": "success", "data": result}
        else:
            return {"status": "error", "message": "Failed to create instance"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/evolution/qrcode")
async def get_evolution_qrcode(user: User = Depends(get_current_user)):
    """Get QR code for WhatsApp authentication"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins")

    try:
        qr_data = await evolution_service.get_qrcode()
        if qr_data:
            return {
                "status": "success",
                "qrcode": qr_data,
                "instruction": "Scan this QR code with WhatsApp on your phone"
            }
        else:
            return {"status": "error", "message": "Failed to get QR code"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/evolution/configure-webhook")
async def configure_evolution_webhook(user: User = Depends(get_current_user)):
    """Configure Evolution API webhook for receiving messages"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins")

    try:
        webhook_url = os.getenv("EVOLUTION_WEBHOOK_URL", "http://localhost:8000/webhook/evolution")
        result = await evolution_service.set_webhook(webhook_url)

        if result:
            return {
                "status": "success",
                "webhook_url": webhook_url,
                "data": result
            }
        else:
            return {"status": "error", "message": "Failed to configure webhook"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/evolution/logout")
async def evolution_logout(user: User = Depends(get_current_user)):
    """Logout from WhatsApp instance"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins")

    try:
        result = await evolution_service.logout()
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.delete("/api/evolution/delete-instance")
async def delete_evolution_instance(user: User = Depends(get_current_user)):
    """Delete WhatsApp instance"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins")

    try:
        result = await evolution_service.delete_instance()
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/dashboard/statistics")
async def get_dashboard_statistics(current_user: User = Depends(get_current_user)):
    """Get comprehensive statistics for dashboard"""
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import func, desc

        with Session(engine) as db_session:
            # Total conversations
            total_conversations = len(db_session.exec(select(Conversation)).all())

            # Active conversations (open status)
            active_conversations = len(db_session.exec(
                select(Conversation).where(Conversation.status == "open")
            ).all())

            # Total messages
            total_messages = len(db_session.exec(select(Message)).all())

            # Messages by type
            messages = db_session.exec(select(Message)).all()
            customer_msgs = len([m for m in messages if m.message_type == "customer"])
            agent_msgs = len([m for m in messages if m.message_type == "agent"])
            bot_msgs = len([m for m in messages if m.message_type == "bot"])

            # Bot service breakdown
            bot_messages = [m for m in messages if m.message_type == "bot"]
            claude_count = len([m for m in bot_messages if m.bot_service == "Claude"])
            ollama_count = len([m for m in bot_messages if m.bot_service == "Ollama"])
            fallback_count = len([m for m in bot_messages if m.bot_service == "Fallback"])

            # Conversations over last 7 days
            now = datetime.now()
            last_7_days = []
            for i in range(6, -1, -1):
                day = now - timedelta(days=i)
                day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)

                day_convs = len([c for c in db_session.exec(select(Conversation)).all()
                               if c.created_at and day_start <= c.created_at <= day_end])

                last_7_days.append({
                    "date": day.strftime("%Y-%m-%d"),
                    "count": day_convs
                })

            # Recent conversations (last 10)
            recent_conversations = db_session.exec(
                select(Conversation).order_by(Conversation.created_at.desc()).limit(10)
            ).all()

            recent_conv_data = []
            for conv in recent_conversations:
                last_msg = db_session.exec(
                    select(Message)
                    .where(Message.conversation_id == conv.id)
                    .order_by(Message.timestamp.desc())
                    .limit(1)
                ).first()

                recent_conv_data.append({
                    "id": conv.id,
                    "customer_number": conv.customer_number,
                    "name": conv.name,
                    "status": conv.status,
                    "created_at": conv.created_at.isoformat() if conv.created_at else None,
                    "last_message": last_msg.content[:50] + "..." if last_msg and last_msg.content else None,
                    "last_message_time": last_msg.timestamp.isoformat() if last_msg else None
                })

            # Bot response rate (percentage of conversations with bot messages)
            convs_with_bot = len(set([m.conversation_id for m in bot_messages]))
            bot_response_rate = (convs_with_bot / total_conversations * 100) if total_conversations > 0 else 0

            return {
                "overview": {
                    "total_conversations": total_conversations,
                    "active_conversations": active_conversations,
                    "total_messages": total_messages,
                    "bot_response_rate": round(bot_response_rate, 1)
                },
                "messages_by_type": {
                    "customer": customer_msgs,
                    "agent": agent_msgs,
                    "bot": bot_msgs
                },
                "bot_services": {
                    "claude": claude_count,
                    "ollama": ollama_count,
                    "fallback": fallback_count
                },
                "conversations_last_7_days": last_7_days,
                "recent_conversations": recent_conv_data
            }

    except Exception as e:
        print(f"Dashboard statistics error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

STATIC_DIR = os.path.join(BASE_DIR, "static")

# Only mount static files if directory exists
if os.path.exists(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    print(f"Static files mounted from: {STATIC_DIR}")
else:
    print(f"Static directory not found: {STATIC_DIR}")

print("FastAPI application startup completed successfully!")
print("All routes and endpoints are now available.")
print(f"n8n integration: {'enabled' if n8n_service.enabled else 'disabled'}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port)