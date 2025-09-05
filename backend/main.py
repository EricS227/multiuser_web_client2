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
from twilio.rest import Client
from pydantic import BaseModel
from dotenv import load_dotenv 
from datetime import timezone
from sqlalchemy import text, inspect
from backend.enhanced_chatbot_service import EnhancedClaudeChatbotService
from backend.models import User, Conversation, Message, AuditLog, BotInteraction, BotContext, Usuario, brazilian_now

import httpx
import os
import asyncio
import requests
import anthropic
import uvicorn

load_dotenv()

app = FastAPI()

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
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chatwoot_clone.db")
engine = create_engine(DATABASE_URL, echo=False)  # Disable echo in production



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

# Import Twilio configuration from config.py
from backend.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM

# Initialize Twilio client if credentials are provided
twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    print("Twilio WhatsApp integration enabled")
else:
    print("Twilio credentials not configured - WhatsApp features disabled")


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
SQLModel.metadata.create_all(engine)



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
def enviar_mensagem(tipo: str, to_number: str, nome: str = ""):
    if tipo == "boas_vindas":
        mensagem = f"Olá {nome}, um operador entrará em contato com você em breve"
    elif tipo == "encerramento":
        mensagem = f"Olá {nome}, sua conversa foi finalizada. obrigado por entrar em contato"
    elif tipo == "atribuição":
        mensagem = f"Nova conversa atribuída a você, {nome}."
    else:
        mensagem = "Mensagem automática do sistema."

    return send_whatsapp_message(to_number, mensagem)


def get_db():
    with Session(engine) as session:
        yield session


def get_session():
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


@app.get("/health")
def health():
    return {"status": "ok"}




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



def get_ngrok_url():
    try:
        response = requests.get('http://localhost:4040/api/tunnels')
        tunnels = response.json()['tunnels']
        for t in tunnels:
            if t['proto'] == 'https':
                return t['public_url']
    except Exception as e:
        print("Erro ao obter URL do ngrok:", e)
        return None

url = get_ngrok_url()
if url:
    print(f"URL pública do ngrok: {url}/webhook/whatsapp")
else:
    print("Não foi possível obter a URL pública do ngrok")




# Send WhatsApp message (only if Twilio is configured)
def send_whatsapp_message(to_number: str, message: str):
    if not twilio_client or not TWILIO_WHATSAPP_FROM:
        print("Twilio not configured - cannot send WhatsApp message")
        return None
    
    try:
        msg = twilio_client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_FROM,
            to=f"whatsapp:{to_number}"
        )
        print(f"WhatsApp message sent to {to_number}: {msg.sid}")
        return msg.sid
    except Exception as e:
        print(f"Error sending WhatsApp message: {e}")
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
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/cadastrar")
async def cadastrar(
    nome: str = Form(...),
    email: str = Form(...),
    senha: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        # Verificar se usuário já existe
        existing_user = db.exec(select(User).where(User.email == email)).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Usuário já existe com este email")
        
        # Criar novo usuário na tabela User (não Usuario)
        novo_usuario = User(
            name=nome,
            email=email,
            password_hash=hash_password(senha),  # Hash da senha
            role="user"  # Role padrão
        )
        
        db.add(novo_usuario)
        db.commit()
        db.refresh(novo_usuario)
        
        return {
            "message": f"Usuário {novo_usuario.name} cadastrado com sucesso!",
            "status": "success",
            "user_id": novo_usuario.id,
            "redirect": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
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
        return session.exec(select(Conversation)).all()
    return session.exec(select(Conversation).where(Conversation.assigned_to == user.id)).all()




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
        send_whatsapp_message(conversation.customer_number, payload.message)
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
            send_whatsapp_message(conversation.customer_number, closing_message)
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
    """Enhanced WhatsApp webhook with Claude AI integration"""
    try:
        # Parse form data
        form_data = await request.form()
        from_number = form_data.get("From", "").replace("whatsapp:", "")
        message_body = form_data.get("Body", "")
        profile_name = form_data.get("ProfileName", "Cliente")

        print(f"MESSAGE received from {from_number}: {message_body}")

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
            
            # Create or find existing conversation
            with Session(engine) as session:
                # Check if conversation already exists
                conversation = session.exec(
                    select(Conversation).where(
                        Conversation.customer_number == from_number,
                        Conversation.status.in_(["pending", "active"])
                    )
                ).first()

                if not conversation:
                    # Create new conversation
                    agent = get_least_busy_agent(session)
                    system_user = session.exec(select(User).where(User.email == "system@internal")).first()
                    
                    conversation = Conversation(
                        customer_number=from_number,
                        name=profile_name,
                        assigned_to=agent.id if agent else None,
                        created_by=agent.id if agent else system_user.id,
                        status="active",  # Change from pending to active when escalated
                    )
                    session.add(conversation)
                    session.commit()
                    session.refresh(conversation)
                    
                    print(f"Created conversation {conversation.id}, assigned to agent {agent.name if agent else 'None'}")

                # Save customer message with proper message type
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
            
            # Send escalation response
            try:
                send_whatsapp_message(from_number, escalation_message)
            except Exception as e:
                print(f"WhatsApp send failed: {e}")
            
            return {"status": "escalated_to_agent", "response": escalation_message, "reason": escalation_reason}
        
        else:
            # Check if there's an existing conversation for this number
            with Session(engine) as session:
                existing_conversation = session.exec(
                    select(Conversation).where(Conversation.customer_number == from_number)
                    .where(Conversation.status == "pending")
                ).first()
                
                if existing_conversation:
                    # Save bot response to existing conversation
                    bot_msg = Message(
                        conversation_id=existing_conversation.id,
                        sender="bot",
                        message_type="bot", 
                        content=bot_response,
                        bot_service=bot_service
                    )
                    session.add(bot_msg)
                    session.commit()
                    
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
                send_whatsapp_message(from_number, bot_response)
            except Exception as e:
                print(f"WhatsApp send failed: {e}")
            
            return {"status": "bot_response", "response": bot_response, "bot_service": bot_service}

    except Exception as e:
        print(f"ERROR in webhook: {e}")
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
            if claude_api_key:
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
    new = Conversation(customer_number="+55119999999", status="pending")
    session.add(new)
    session.commit()
    session.refresh(new)
    return {"id": new.id}


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
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Only mount static files if directory exists
if os.path.exists(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)