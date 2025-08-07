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
from backend.chatbot_service import EnhancedChatbotService
from backend.models import User, Conversation, Message, AuditLog, BotInteraction, Usuario, brazilian_now

import httpx
import os
import asyncio
import requests

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
    raise ValueError("SECRET_KEY environment variable is required for production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Twilio (opcional, pode remover se não for usar)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID") or "SEU_ACCOUNT_SID"
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN") or "SEU_AUTH_TOKEN"
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM")
TO = 'whatsapp:+5531996950370'
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


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

    async def send_personal_message(self, message: dict, recipienet_number: str):
        for connection in self.active_connections:
            try:
                await connection.send_json({
                    "to": recipienet_number,
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



@app.on_event("startup")
def verificar_e_adicionar_coluna_name():
    with engine.connect() as conn:
        insp = inspect(conn)
        columns = [col["name"] for col in insp.get_columns("conversation")]

        if "name" not in columns:
            print("Adicionando coluna 'name' à tabela conversation")
            conn.execute(text("ALTER TABLE conversation ADD COLUMN name VARCHAR"))
            conn.commit()
#with engine.connect() as conn:
   # conn.execute(text("ALTER TABLE conversation ADD COLUMN name VARCHAR"))
    #conn.commit()


# Utils
@app.on_event("startup")
def create_admin_user():
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




# Envia mensagem pelo WhatsApp (opcional)
def send_whatsapp_message(to_number: str, message: str):
    try:
        msg = twilio_client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_FROM,
            to=f"whatsapp:{to_number}"
        )
        print(F"Mensagem enviaad para {to_number}: {msg.sid}")
        return msg.sid
    except Exception as e:
        print(f"Erro ao enviar mensagem via WhatsApp: {e}")
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
    if conversation.assigned_to != user.id:
        raise HTTPException(status_code=403, detail="Você não está atribuído a essa conversa")

    message = Message(
        conversation_id=conversation_id,
        sender="agent",
        content=payload.message
    )
    session.add(message)
    session.commit()

    # envia via WhatsApp (remova se não usar Twilio)
    try:
        send_whatsapp_message(conversation.customer_number, payload.message)
    except Exception as e:
        print(f"Erro ao enviar mensagem via WhatsApp: {e}")


    await manager.broadcast({
        "id": message.id,
        "conversation_id": conversation_id,
        "sender": "agent",
        "message": message.content,
        "timestamp": message.timestamp.isoformat()
    })
    return {"msg": "Mensagem enviada"}


@app.post("/conversations/{conversation_id}/end")
def end_conversation(conversation_id: int, db: Session = Depends(get_session), user=Depends(get_current_user)):
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="conversation not found")
    
    if user.role == "admin":
        pass
    else:
        if conversation.assigned_to != user.id:
            raise HTTPException(status_code=403, detail="Você não está atribuído a essa conversa")
    if conversation.status == "closed":
        raise HTTPException(status_code=400, detail="Conversation already closed")
    
    try:
        conversation.status = "closed"
        db.commit()
        return {"detail": "Conversation closed successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error ending conversation")


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
async def whatsapp_webhook(request: Request, session: Session = Depends(get_session)):
    """Enhanced WhatsApp webhook with intelligent chatbot routing and context management"""
    try:
        # Parse incoming message data
        try:
            payload = await request.json()
            from_number = payload.get("from", "").replace("whatsapp:", "")
            message_body = payload.get("message", "")
            profile_name = payload.get("name", "Cliente")
        except:
            # Fallback to form data (standard Twilio format)
            form_data = await request.form()
            from_number = form_data.get("From", "").replace("whatsapp:", "")
            message_body = form_data.get("Body", "")
            profile_name = form_data.get("ProfileName", "Cliente")

        print(f"📱 Mensagem recebida de {from_number}: {message_body}")

        if not from_number or not message_body:
            raise HTTPException(status_code=400, detail="Dados incompletos")

        # Initialize enhanced chatbot service
        chatbot_service = EnhancedChatbotService(session)
        
        # Process message through enhanced chatbot logic
        chatbot_result = await chatbot_service.process_message(from_number, message_body, profile_name)
        
        if not chatbot_result['should_escalate'] and chatbot_result['bot_response']:
            # Bot can handle this - send automated response
            bot_response = chatbot_result['bot_response']
            
            print(f"🤖 Bot respondendo: {bot_response}")
            
            # Send response via WhatsApp
            send_whatsapp_message(from_number, bot_response)
            
            # Save bot interaction to database (optional - for analytics)
            await _save_bot_interaction(session, from_number, message_body, bot_response, profile_name)
            
            # Notify interface for monitoring (optional)
            await manager.send_personal_message({
                "sender": "bot",
                "message": bot_response,
                "conversation_id": None,
                "customer_number": from_number,
                "customer_name": profile_name,
                "timestamp": brazilian_now().isoformat()
            }, from_number)
            
            return {"status": "bot_response", "response": bot_response}
        
        else:
            # Escalate to human agent
            escalation_reason = chatbot_result['escalation_reason']
            print(f"👥 Escalando para agente humano. Motivo: {escalation_reason}")
            
            # Get escalation message
            escalation_message = chatbot_service.get_escalation_message(escalation_reason, profile_name)
            
            # Check if conversation already exists
            conversation = session.exec(
                select(Conversation).where(
                    Conversation.customer_number == from_number,
                    Conversation.status == "pending"
                )
            ).first()

            # Create new conversation if doesn't exist
            if not conversation:
                agent = get_least_busy_agent(session)
                
                # Get system user for conversation creation when no agent available
                system_user = session.exec(select(User).where(User.email == "system@internal")).first()
                if not system_user:
                    raise HTTPException(status_code=500, detail="System user not found")
                
                conversation = Conversation(
                    customer_number=from_number,
                    name=profile_name,
                    assigned_to=agent.id if agent else None,
                    created_by=agent.id if agent else system_user.id,
                    status="pending",
                )
                session.add(conversation)
                session.commit()
                session.refresh(conversation)

                # Send escalation message for new conversations
                try:
                    send_whatsapp_message(from_number, escalation_message)
                except Exception as e:
                    print(f"❌ Erro ao enviar mensagem de escalação: {e}")

            # Save customer message to database
            msg = Message(
                conversation_id=conversation.id,
                sender="customer",
                content=message_body
            )
            session.add(msg)
            session.commit()

            # Notify agents via WebSocket with enhanced information
            await manager.broadcast({
                "id": msg.id,
                "conversation_id": conversation.id,
                "sender": "customer",
                "message": message_body,
                "timestamp": msg.timestamp.isoformat(),
                "customer_name": profile_name,
                "customer_number": from_number,
                "escalation_reason": escalation_reason,
                "bot_interaction_count": chatbot_result.get('bot_interaction_count', 0)
            })

            return {"status": "escalated_to_agent", "reason": escalation_reason}

    except Exception as e:
        print(f"❌ Erro no webhook WhatsApp: {e}")
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
        
        print(f"💾 Bot interaction saved: {phone_number} -> {user_message[:50]}... -> {bot_response[:50]}...")
    except Exception as e:
        print(f"❌ Erro ao salvar interação do bot: {e}")

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
            rasa_status = "offline"
            ollama_status = "offline"
            
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
            
            return rasa_status, ollama_status
        
        rasa_status, ollama_status = asyncio.run(check_services())
        
        return {
            "chatbot_service": "active",
            "rasa_status": rasa_status,
            "ollama_status": ollama_status,
            "features": {
                "context_management": True,
                "smart_escalation": True,
                "response_fallbacks": True,
                "conversation_memory": True
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
        chatbot_service = EnhancedChatbotService(session)
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
        chatbot_service = EnhancedChatbotService(session)
        chatbot_service.context_manager.cleanup_expired_contexts()
        return {"message": "Contextos expirados limpos com sucesso"}
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