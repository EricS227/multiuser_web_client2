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
from pydantic import BaseModel
from dotenv import load_dotenv
from datetime import timezone
from sqlalchemy import text, inspect
import asyncio
import random
from backend.enhanced_chatbot_service import EnhancedClaudeChatbotService
from backend.models import User, Conversation, Message, AuditLog, BotInteraction, BotContext, Usuario, brazilian_now
from backend.models.delivery_models import Customer, Product, Driver, Order, OrderItem, Delivery, OrderStatus, DriverStatus
from backend.services import CustomerService, OrderService, DeliveryService, DriverService, ProductService
from backend.waha_service import waha_service

import httpx
import os
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
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000,http://localhost:8001,http://127.0.0.1:8001").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
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
REFRESH_TOKEN_EXPIRE_DAYS = 7
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# WhatsApp integration via WAHA
print("WhatsApp integration: Using WAHA")


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
    expire = brazilian_now() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = brazilian_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
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
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Usuário desativado")
        return user
    except (InvalidTokenError, DecodeError):
        raise HTTPException(status_code=401, detail="Token inválido")

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Retorna usuário ativo"""
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="Usuário desativado")
    return current_user

def require_role(allowed_roles: list):
    """Dependency factory para verificar role do usuário"""
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Acesso negado. Requer role: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker

# Shortcuts para verificação de role
require_admin = require_role(["admin", "owner"])
require_owner = require_role(["owner"])
require_operador = require_role(["operador", "admin", "owner"])



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


async def send_whatsapp_message(to_number: str, message: str):
    """
    Send WhatsApp message via WAHA
    """
    warmup_mode = os.getenv("WARMUP_MODE", "false").lower() == "true"
    if warmup_mode:
        print(f"WARMUP MODE: Skipping auto-send to {to_number}")
        return None

    # Send via WAHA if enabled
    if waha_service.enabled:
        result = await waha_service.send_text_message(to_number, message)
        if result:
            print(f"WAHA: Message sent to {to_number}")
            return result

    print("WAHA not enabled - WhatsApp message not sent")
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
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Usuário desativado. Contate o administrador.")

    # Atualizar last_login
    user.last_login = brazilian_now()
    session.add(user)
    session.commit()

    access_token = create_token({"sub": user.email})
    refresh_token = create_refresh_token({"sub": user.email})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role
        }
    }

@app.post("/refresh-token")
def refresh_token(refresh_token: str = Form(...), session: Session = Depends(get_session)):
    """Gera novo access token usando refresh token"""
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Token inválido")
        email = payload.get("sub")
        user = session.exec(select(User).where(User.email == email)).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Usuário não encontrado ou desativado")
        new_access_token = create_token({"sub": user.email})
        return {"access_token": new_access_token, "token_type": "bearer"}
    except (InvalidTokenError, DecodeError):
        raise HTTPException(status_code=401, detail="Refresh token inválido ou expirado")

@app.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Retorna informações do usuário logado"""
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "last_login": current_user.last_login
    }

# ==================== ADMIN ENDPOINTS ====================

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str = "operador"

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

@app.get("/admin/users")
def list_users(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """Lista todos os usuários (admin/owner only)"""
    users = session.exec(select(User)).all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at,
            "last_login": u.last_login
        }
        for u in users
    ]

@app.post("/admin/users")
def create_user(
    user_data: UserCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """Cria novo usuário (admin/owner only)"""
    # Verificar se email já existe
    existing = session.exec(select(User).where(User.email == user_data.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    # Apenas owner pode criar admin/owner
    if user_data.role in ["admin", "owner"] and current_user.role != "owner":
        raise HTTPException(status_code=403, detail="Apenas owner pode criar usuários admin/owner")

    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=user_data.role,
        created_by=current_user.id
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    # Log de auditoria
    audit = AuditLog(
        action="user_created",
        user_id=current_user.id,
        details=f"Criou usuário {new_user.email} com role {new_user.role}"
    )
    session.add(audit)
    session.commit()

    return {"message": "Usuário criado com sucesso", "user_id": new_user.id}

@app.put("/admin/users/{user_id}")
def update_user(
    user_id: int,
    user_data: UserUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """Atualiza usuário (admin/owner only)"""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Proteções
    if user.role == "owner" and current_user.role != "owner":
        raise HTTPException(status_code=403, detail="Não é possível editar owner")

    if user_data.role in ["admin", "owner"] and current_user.role != "owner":
        raise HTTPException(status_code=403, detail="Apenas owner pode promover para admin/owner")

    # Atualizar campos
    if user_data.name is not None:
        user.name = user_data.name
    if user_data.email is not None:
        # Verificar se novo email já existe
        if user_data.email != user.email:
            existing = session.exec(select(User).where(User.email == user_data.email)).first()
            if existing:
                raise HTTPException(status_code=400, detail="Email já em uso")
        user.email = user_data.email
    if user_data.role is not None:
        user.role = user_data.role
    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    session.add(user)
    session.commit()

    # Log de auditoria
    audit = AuditLog(
        action="user_updated",
        user_id=current_user.id,
        details=f"Atualizou usuário {user.email}"
    )
    session.add(audit)
    session.commit()

    return {"message": "Usuário atualizado com sucesso"}

@app.delete("/admin/users/{user_id}")
def deactivate_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """Desativa usuário (admin/owner only) - não deleta, apenas desativa"""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Não é possível desativar a si mesmo")

    if user.role == "owner" and current_user.role != "owner":
        raise HTTPException(status_code=403, detail="Não é possível desativar owner")

    user.is_active = False
    session.add(user)
    session.commit()

    # Log de auditoria
    audit = AuditLog(
        action="user_deactivated",
        user_id=current_user.id,
        details=f"Desativou usuário {user.email}"
    )
    session.add(audit)
    session.commit()

    return {"message": "Usuário desativado com sucesso"}

@app.post("/admin/users/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    new_password: str = Form(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """Reseta senha de usuário (admin/owner only)"""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if user.role == "owner" and current_user.role != "owner":
        raise HTTPException(status_code=403, detail="Não é possível resetar senha de owner")

    user.password_hash = hash_password(new_password)
    session.add(user)
    session.commit()

    # Log de auditoria
    audit = AuditLog(
        action="password_reset",
        user_id=current_user.id,
        details=f"Resetou senha do usuário {user.email}"
    )
    session.add(audit)
    session.commit()

    return {"message": "Senha resetada com sucesso"}

@app.get("/admin/audit-logs")
def get_audit_logs(
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """Lista logs de auditoria (admin/owner only)"""
    logs = session.exec(
        select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
    ).all()
    return logs

@app.get("/admin/conversations")
def get_all_conversations_admin(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """Lista todas as conversas com detalhes (admin/owner only)"""
    conversations = session.exec(select(Conversation)).all()
    result = []
    for conv in conversations:
        assigned_user = session.get(User, conv.assigned_to) if conv.assigned_to else None
        messages_count = len(session.exec(select(Message).where(Message.conversation_id == conv.id)).all())
        result.append({
            "id": conv.id,
            "customer_number": conv.customer_number,
            "name": conv.name,
            "status": conv.status,
            "created_at": conv.created_at,
            "assigned_to": assigned_user.name if assigned_user else None,
            "assigned_to_id": conv.assigned_to,
            "messages_count": messages_count
        })
    return result

@app.get("/admin/stats")
def get_admin_stats(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """Estatísticas gerais do sistema (admin/owner only)"""
    total_users = len(session.exec(select(User)).all())
    active_users = len(session.exec(select(User).where(User.is_active == True)).all())
    total_conversations = len(session.exec(select(Conversation)).all())
    pending_conversations = len(session.exec(select(Conversation).where(Conversation.status == "pending")).all())
    total_messages = len(session.exec(select(Message)).all())

    # Mensagens hoje
    today_start = brazilian_now().replace(hour=0, minute=0, second=0, microsecond=0)
    messages_today = len(session.exec(select(Message).where(Message.timestamp >= today_start)).all())

    return {
        "users": {
            "total": total_users,
            "active": active_users
        },
        "conversations": {
            "total": total_conversations,
            "pending": pending_conversations
        },
        "messages": {
            "total": total_messages,
            "today": messages_today
        }
    }


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
    """Legacy WhatsApp webhook (deprecated - use /webhook/waha instead)"""
    return {"status": "deprecated", "message": "Use /webhook/waha endpoint instead"}


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



# ===== DELIVERY SYSTEM ENDPOINTS =====

# --- Products ---
@app.get("/api/products")
def list_products(session: Session = Depends(get_session)):
    """Lista todos os produtos"""
    service = ProductService(session)
    return service.list_all()

@app.get("/api/products/available")
def list_available_products(session: Session = Depends(get_session)):
    """Lista produtos disponíveis em estoque"""
    service = ProductService(session)
    return service.list_available()

@app.post("/api/products/init")
def init_products(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Cria produtos padrão (P13, P20, P45)"""
    service = ProductService(session)
    service.create_default_products()
    return {"msg": "Produtos criados com sucesso"}

# --- Customers ---
@app.get("/api/customers")
def list_customers(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Lista todos os clientes"""
    service = CustomerService(session)
    return service.list_all()

@app.get("/api/customers/{customer_id}")
def get_customer(customer_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Busca cliente por ID"""
    service = CustomerService(session)
    customer = service.get_by_id(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return customer

@app.get("/api/customers/phone/{telefone}")
def get_customer_by_phone(telefone: str, session: Session = Depends(get_session)):
    """Busca cliente por telefone"""
    service = CustomerService(session)
    customer = service.get_by_phone(telefone)
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return customer

class CustomerCreate(BaseModel):
    nome: str
    telefone: str
    endereco: str
    numero: str
    bairro: str
    complemento: Optional[str] = None
    cidade: str = "Curitiba"
    estado: str = "PR"
    cep: Optional[str] = None
    ponto_referencia: Optional[str] = None

@app.post("/api/customers")
def create_customer(data: CustomerCreate, session: Session = Depends(get_session)):
    """Cria novo cliente"""
    service = CustomerService(session)
    customer = service.create(**data.model_dump())
    return customer

# --- Drivers ---
@app.get("/api/drivers")
def list_drivers(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Lista todos os entregadores"""
    service = DriverService(session)
    return service.list_all()

@app.get("/api/drivers/available")
def list_available_drivers(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Lista entregadores disponíveis"""
    service = DriverService(session)
    return service.list_available()

class DriverCreate(BaseModel):
    nome: str
    telefone: str
    veiculo: Optional[str] = None
    placa: Optional[str] = None

@app.post("/api/drivers")
def create_driver(data: DriverCreate, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Cria novo entregador"""
    service = DriverService(session)
    driver = service.create(**data.model_dump())
    return driver

@app.post("/api/drivers/{driver_id}/online")
def driver_go_online(driver_id: int, session: Session = Depends(get_session)):
    """Coloca entregador online"""
    service = DriverService(session)
    driver = service.go_online(driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Entregador não encontrado")
    return driver

@app.post("/api/drivers/{driver_id}/offline")
def driver_go_offline(driver_id: int, session: Session = Depends(get_session)):
    """Coloca entregador offline"""
    service = DriverService(session)
    driver = service.go_offline(driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Entregador não encontrado")
    return driver

class LocationUpdate(BaseModel):
    latitude: float
    longitude: float

@app.post("/api/drivers/{driver_id}/location")
def update_driver_location(driver_id: int, data: LocationUpdate, session: Session = Depends(get_session)):
    """Atualiza localização do entregador"""
    service = DriverService(session)
    driver = service.update_location(driver_id, data.latitude, data.longitude)
    if not driver:
        raise HTTPException(status_code=404, detail="Entregador não encontrado")
    return driver

# --- Orders ---
@app.get("/api/orders/pending")
def list_pending_orders(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Lista pedidos pendentes"""
    service = OrderService(session)
    return service.list_pending()

@app.get("/api/orders/in-delivery")
def list_orders_in_delivery(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Lista pedidos em entrega"""
    service = OrderService(session)
    return service.list_in_delivery()

@app.get("/api/orders/{order_id}")
def get_order(order_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Busca pedido por ID"""
    service = OrderService(session)
    order = service.get_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return order

class OrderItemCreate(BaseModel):
    product_id: int
    quantidade: int = 1
    tem_troca: bool = True

class OrderCreate(BaseModel):
    customer_id: int
    items: List[OrderItemCreate]
    endereco_entrega: Optional[str] = None
    numero_entrega: Optional[str] = None
    bairro_entrega: Optional[str] = None
    observacoes: Optional[str] = None
    forma_pagamento: Optional[str] = None
    troco_para: Optional[float] = None

@app.post("/api/orders")
async def create_order(data: OrderCreate, session: Session = Depends(get_session)):
    """Cria novo pedido"""
    customer_service = CustomerService(session)
    customer = customer_service.get_by_id(data.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    order_service = OrderService(session)
    items = [item.model_dump() for item in data.items]
    order = order_service.create(
        customer=customer,
        items=items,
        endereco_entrega=data.endereco_entrega,
        numero_entrega=data.numero_entrega,
        bairro_entrega=data.bairro_entrega,
        observacoes=data.observacoes
    )

    # Broadcast para painéis
    await manager.broadcast({
        "type": "new_order",
        "order": {
            "id": order.id,
            "status": order.status.value if hasattr(order.status, 'value') else order.status,
            "customer_name": customer.nome,
            "customer_phone": customer.telefone,
            "endereco_entrega": order.endereco_entrega,
            "numero_entrega": order.numero_entrega,
            "bairro_entrega": order.bairro_entrega,
            "total": float(order.total) if order.total else 0,
            "created_at": order.created_at.isoformat() if order.created_at else None
        }
    })

    return order

@app.post("/api/orders/{order_id}/confirm")
async def confirm_order(order_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Confirma pedido"""
    service = OrderService(session)
    order = service.confirm(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    # Broadcast atualização
    await manager.broadcast({
        "type": "order_update",
        "order_id": order.id,
        "status": "confirmado",
        "action": "confirm"
    })

    return order

class CancelRequest(BaseModel):
    motivo: str = "Cancelado pelo cliente"

@app.post("/api/orders/{order_id}/cancel")
async def cancel_order(order_id: int, data: CancelRequest, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Cancela pedido"""
    service = OrderService(session)
    order = service.cancel(order_id, data.motivo)
    if not order:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    # Broadcast atualização
    await manager.broadcast({
        "type": "order_update",
        "order_id": order.id,
        "status": "cancelado",
        "action": "cancel",
        "motivo": data.motivo
    })

    return order

# --- Deliveries ---
@app.get("/api/deliveries/active")
def list_active_deliveries(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Lista entregas ativas"""
    service = DeliveryService(session)
    return service.list_active()

class AssignDriverRequest(BaseModel):
    driver_id: int

@app.post("/api/orders/{order_id}/assign-driver")
async def assign_driver_to_order(order_id: int, data: AssignDriverRequest, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Atribui entregador ao pedido"""
    delivery_service = DeliveryService(session)
    delivery = delivery_service.create_delivery(order_id, data.driver_id)
    if not delivery:
        raise HTTPException(status_code=400, detail="Erro ao criar entrega")

    # Broadcast
    await manager.broadcast({
        "type": "order_update",
        "order_id": order_id,
        "status": "em_preparo",
        "action": "assign_driver",
        "driver_id": data.driver_id,
        "driver_name": delivery.driver.nome if delivery.driver else None
    })

    return delivery

@app.post("/api/deliveries/{delivery_id}/start")
async def start_delivery(delivery_id: int, session: Session = Depends(get_session)):
    """Inicia entrega (saiu para entrega)"""
    service = DeliveryService(session)
    delivery = service.start_delivery(delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Entrega não encontrada")

    # Broadcast
    await manager.broadcast({
        "type": "order_update",
        "order_id": delivery.order_id,
        "status": "saiu_entrega",
        "action": "start_delivery",
        "delivery_id": delivery_id
    })

    return delivery

@app.post("/api/deliveries/{delivery_id}/complete")
async def complete_delivery(delivery_id: int, session: Session = Depends(get_session)):
    """Finaliza entrega"""
    service = DeliveryService(session)
    delivery = service.complete_delivery(delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Entrega não encontrada")

    # Broadcast
    await manager.broadcast({
        "type": "order_update",
        "order_id": delivery.order_id,
        "status": "entregue",
        "action": "complete_delivery",
        "delivery_id": delivery_id
    })

    return delivery

class FailDeliveryRequest(BaseModel):
    motivo: str

@app.post("/api/deliveries/{delivery_id}/fail")
async def fail_delivery(delivery_id: int, data: FailDeliveryRequest, session: Session = Depends(get_session)):
    """Marca entrega como falha"""
    service = DeliveryService(session)
    delivery = service.fail_delivery(delivery_id, data.motivo)
    if not delivery:
        raise HTTPException(status_code=404, detail="Entrega não encontrada")

    # Broadcast
    await manager.broadcast({
        "type": "order_update",
        "order_id": delivery.order_id,
        "status": "falha",
        "action": "fail_delivery",
        "delivery_id": delivery_id,
        "motivo": data.motivo
    })
    return delivery


# ===== WAHA WHATSAPP API ENDPOINTS =====

@app.get("/api/waha/status")
async def waha_status():
    """Get WAHA session status"""
    status = await waha_service.get_session_status()
    return {"enabled": waha_service.enabled, "status": status}

@app.post("/api/waha/start-session")
async def waha_start_session():
    """Start WAHA WhatsApp session"""
    if not waha_service.enabled:
        raise HTTPException(status_code=400, detail="WAHA not enabled")
    result = await waha_service.start_session()
    if result:
        return {"success": True, "result": result}
    raise HTTPException(status_code=500, detail="Failed to start session")

@app.post("/api/waha/stop-session")
async def waha_stop_session():
    """Stop WAHA WhatsApp session"""
    if not waha_service.enabled:
        raise HTTPException(status_code=400, detail="WAHA not enabled")
    result = await waha_service.stop_session()
    return {"success": True, "result": result}

@app.get("/api/waha/qrcode")
async def waha_qrcode():
    """Get WAHA QR code for authentication"""
    if not waha_service.enabled:
        raise HTTPException(status_code=400, detail="WAHA not enabled")
    result = await waha_service.get_qrcode()
    if result:
        return result
    raise HTTPException(status_code=404, detail="QR code not available")

@app.post("/api/waha/logout")
async def waha_logout():
    """Logout from WAHA WhatsApp"""
    if not waha_service.enabled:
        raise HTTPException(status_code=400, detail="WAHA not enabled")
    result = await waha_service.logout()
    return {"success": True, "result": result}

class WAHASendMessageRequest(BaseModel):
    to_number: str
    message: str

@app.post("/api/waha/send-message")
async def waha_send_message(data: WAHASendMessageRequest):
    """Send message via WAHA WhatsApp"""
    if not waha_service.enabled:
        raise HTTPException(status_code=400, detail="WAHA not enabled")
    result = await waha_service.send_text_message(data.to_number, data.message)
    if result:
        return {"success": True, "result": result}
    raise HTTPException(status_code=500, detail="Failed to send message")


# ===== WAHA WEBHOOK =====

@app.post("/webhook/waha")
async def waha_webhook(request: Request):
    """
    Webhook para receber mensagens do WAHA
    """
    try:
        data = await request.json()
        print(f"WAHA Webhook received: {data}")

        event_type = data.get("event")

        # Handle incoming message
        if event_type == "message":
            payload = data.get("payload", {})
            from_number = payload.get("from", "")
            message_body = payload.get("body", "")
            is_from_me = payload.get("fromMe", False)

            # Skip messages sent by us
            if is_from_me:
                return {"status": "ignored", "reason": "message from self"}

            # Clean phone number (remove @c.us)
            phone = from_number.replace("@c.us", "")

            print(f"WAHA Message from {phone}: {message_body}")

            # Process with chatbot
            with Session(engine) as session:
                # Find or create conversation
                statement = select(Conversation).where(Conversation.phone == phone)
                conversation = session.exec(statement).first()

                if not conversation:
                    conversation = Conversation(
                        phone=phone,
                        customer_name=f"WhatsApp {phone}",
                        source="waha",
                        status="new"
                    )
                    session.add(conversation)
                    session.commit()
                    session.refresh(conversation)

                # Save incoming message
                incoming_msg = Message(
                    conversation_id=conversation.id,
                    content=message_body,
                    sender="customer",
                    message_type="waha"
                )
                session.add(incoming_msg)
                session.commit()

                # Process with chatbot if bot is active
                if conversation.bot_enabled:
                    chatbot = EnhancedClaudeChatbotService()
                    bot_response = await chatbot.process_message(
                        message=message_body,
                        conversation_id=conversation.id,
                        phone=phone,
                        session=session
                    )

                    if bot_response and bot_response.get("response"):
                        response_text = bot_response["response"]

                        # Save bot response
                        bot_msg = Message(
                            conversation_id=conversation.id,
                            content=response_text,
                            sender="bot",
                            message_type="waha",
                            bot_service=bot_response.get("service", "chatbot")
                        )
                        session.add(bot_msg)
                        session.commit()

                        # Send via WAHA
                        await waha_service.send_text_message(phone, response_text)

                        # Check if should escalate
                        if bot_response.get("should_escalate"):
                            conversation.bot_enabled = False
                            conversation.status = "waiting"
                            session.commit()

                # Broadcast update
                await manager.broadcast({
                    "type": "new_message",
                    "conversation_id": conversation.id,
                    "phone": phone,
                    "message": message_body,
                    "source": "waha"
                })

            return {"status": "processed"}

        return {"status": "ignored", "reason": f"unhandled event: {event_type}"}

    except Exception as e:
        print(f"WAHA Webhook error: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


# ==================== REPORTS & OWNER ENDPOINTS ====================

@app.get("/api/reports/orders")
def get_orders_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """Relatório de pedidos (admin/owner)"""
    from sqlalchemy import func

    query = select(Order)

    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        query = query.where(Order.created_at >= start)
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        query = query.where(Order.created_at <= end)

    orders = session.exec(query).all()

    # Estatísticas
    total_orders = len(orders)
    total_revenue = sum(float(o.total or 0) for o in orders)
    status_counts = {}
    for o in orders:
        status = o.status.value if hasattr(o.status, 'value') else str(o.status)
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "period": {"start": start_date, "end": end_date},
        "summary": {
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "average_ticket": total_revenue / total_orders if total_orders > 0 else 0,
            "by_status": status_counts
        },
        "orders": [
            {
                "id": o.id,
                "status": o.status.value if hasattr(o.status, 'value') else str(o.status),
                "total": float(o.total or 0),
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "endereco": f"{o.endereco_entrega}, {o.numero_entrega}" if o.endereco_entrega else None
            }
            for o in orders
        ]
    }

@app.get("/api/reports/financial")
def get_financial_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_owner)
):
    """Relatório financeiro (owner only)"""
    query = select(Order)

    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        query = query.where(Order.created_at >= start)
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        query = query.where(Order.created_at <= end)

    orders = session.exec(query).all()

    # Agrupar por dia
    daily_revenue = {}
    for o in orders:
        if o.created_at:
            day = o.created_at.strftime("%Y-%m-%d")
            daily_revenue[day] = daily_revenue.get(day, 0) + float(o.total or 0)

    # Agrupar por status
    revenue_by_status = {}
    for o in orders:
        status = o.status.value if hasattr(o.status, 'value') else str(o.status)
        revenue_by_status[status] = revenue_by_status.get(status, 0) + float(o.total or 0)

    total_revenue = sum(float(o.total or 0) for o in orders)
    completed_orders = [o for o in orders if (o.status.value if hasattr(o.status, 'value') else str(o.status)) == 'entregue']
    completed_revenue = sum(float(o.total or 0) for o in completed_orders)

    return {
        "period": {"start": start_date, "end": end_date},
        "summary": {
            "total_revenue": total_revenue,
            "completed_revenue": completed_revenue,
            "pending_revenue": total_revenue - completed_revenue,
            "total_orders": len(orders),
            "completed_orders": len(completed_orders),
            "average_ticket": total_revenue / len(orders) if orders else 0
        },
        "daily_revenue": daily_revenue,
        "revenue_by_status": revenue_by_status
    }

@app.get("/api/reports/export/orders")
def export_orders_csv(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_owner)
):
    """Exporta pedidos em CSV (owner only)"""
    from fastapi.responses import Response

    query = select(Order)

    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        query = query.where(Order.created_at >= start)
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        query = query.where(Order.created_at <= end)

    orders = session.exec(query).all()

    # Gerar CSV
    csv_lines = ["ID,Status,Total,Endereco,Bairro,Data"]
    for o in orders:
        status = o.status.value if hasattr(o.status, 'value') else str(o.status)
        date_str = o.created_at.strftime("%Y-%m-%d %H:%M") if o.created_at else ""
        csv_lines.append(f"{o.id},{status},{o.total},{o.endereco_entrega},{o.bairro_entrega},{date_str}")

    csv_content = "\n".join(csv_lines)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=pedidos_{start_date or 'all'}_{end_date or 'all'}.csv"}
    )

@app.get("/api/reports/export/customers")
def export_customers_csv(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_owner)
):
    """Exporta clientes em CSV (owner only)"""
    from fastapi.responses import Response

    customers = session.exec(select(Customer)).all()

    csv_lines = ["ID,Nome,Telefone,Endereco,Bairro,Cidade"]
    for c in customers:
        csv_lines.append(f"{c.id},{c.nome},{c.telefone},{c.endereco},{c.bairro},{c.cidade}")

    csv_content = "\n".join(csv_lines)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=clientes.csv"}
    )

@app.get("/owner/stats")
def get_owner_stats(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_owner)
):
    """Estatísticas completas para o owner"""
    today = brazilian_now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # Pedidos
    all_orders = session.exec(select(Order)).all()
    today_orders = [o for o in all_orders if o.created_at and o.created_at >= today]
    week_orders = [o for o in all_orders if o.created_at and o.created_at >= week_ago]
    month_orders = [o for o in all_orders if o.created_at and o.created_at >= month_ago]

    # Faturamento
    today_revenue = sum(float(o.total or 0) for o in today_orders)
    week_revenue = sum(float(o.total or 0) for o in week_orders)
    month_revenue = sum(float(o.total or 0) for o in month_orders)

    # Clientes
    total_customers = len(session.exec(select(Customer)).all())

    # Entregadores
    all_drivers = session.exec(select(Driver)).all()
    online_drivers = [d for d in all_drivers if d.status and (d.status.value if hasattr(d.status, 'value') else str(d.status)) == 'disponivel']

    # Produtos
    total_products = len(session.exec(select(Product)).all())

    # Conversas
    total_conversations = len(session.exec(select(Conversation)).all())
    pending_conversations = len(session.exec(select(Conversation).where(Conversation.status == "pending")).all())

    return {
        "orders": {
            "today": len(today_orders),
            "week": len(week_orders),
            "month": len(month_orders),
            "total": len(all_orders)
        },
        "revenue": {
            "today": today_revenue,
            "week": week_revenue,
            "month": month_revenue
        },
        "customers": {
            "total": total_customers
        },
        "drivers": {
            "total": len(all_drivers),
            "online": len(online_drivers)
        },
        "products": {
            "total": total_products
        },
        "conversations": {
            "total": total_conversations,
            "pending": pending_conversations
        }
    }

# --- Products CRUD (Admin) ---
class ProductCreate(BaseModel):
    nome: str
    descricao: Optional[str] = None
    preco: float
    preco_sem_troca: Optional[float] = None
    categoria: str = "gas"
    ativo: bool = True

class ProductUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    preco: Optional[float] = None
    preco_sem_troca: Optional[float] = None
    categoria: Optional[str] = None
    ativo: Optional[bool] = None

@app.post("/api/products")
def create_product(
    data: ProductCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """Cria novo produto (admin/owner)"""
    product = Product(**data.model_dump())
    session.add(product)
    session.commit()
    session.refresh(product)
    return product

@app.put("/api/products/{product_id}")
def update_product(
    product_id: int,
    data: ProductUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """Atualiza produto (admin/owner)"""
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)

    session.add(product)
    session.commit()
    session.refresh(product)
    return product

@app.delete("/api/products/{product_id}")
def delete_product(
    product_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """Remove produto (admin/owner)"""
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    # Soft delete - apenas desativa
    product.ativo = False
    session.add(product)
    session.commit()
    return {"message": "Produto desativado com sucesso"}

# --- Drivers CRUD (Admin) ---
@app.put("/api/drivers/{driver_id}")
def update_driver(
    driver_id: int,
    data: DriverCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """Atualiza entregador (admin/owner)"""
    driver = session.get(Driver, driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Entregador não encontrado")

    for key, value in data.model_dump().items():
        setattr(driver, key, value)

    session.add(driver)
    session.commit()
    session.refresh(driver)
    return driver

@app.delete("/api/drivers/{driver_id}")
def delete_driver(
    driver_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """Remove entregador (admin/owner)"""
    driver = session.get(Driver, driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Entregador não encontrado")

    session.delete(driver)
    session.commit()
    return {"message": "Entregador removido com sucesso"}

# --- Customers CRUD (Admin) ---
class CustomerUpdate(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None

@app.put("/api/customers/{customer_id}")
def update_customer(
    customer_id: int,
    data: CustomerUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """Atualiza cliente (admin/owner)"""
    customer = session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(customer, key, value)

    session.add(customer)
    session.commit()
    session.refresh(customer)
    return customer

@app.delete("/api/customers/{customer_id}")
def delete_customer(
    customer_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """Remove cliente (admin/owner)"""
    customer = session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    session.delete(customer)
    session.commit()
    return {"message": "Cliente removido com sucesso"}


# ===== STATIC FILES =====

STATIC_DIR = os.path.join(BASE_DIR, "static")

# Only mount static files if directory exists
if os.path.exists(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    print(f"Static files mounted from: {STATIC_DIR}")
else:
    print(f"Static directory not found: {STATIC_DIR}")

print("FastAPI application startup completed successfully!")
print("All routes and endpoints are now available.")
print(f"WAHA integration: {'enabled' if waha_service.enabled else 'disabled'}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port)