from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request, Query, Form
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from sqlmodel import Field, SQLModel, Session, create_engine, select
from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from twilio.rest import Client
from pydantic import BaseModel
from fastapi.encoders import jsonable_encoder
from dotenv import load_dotenv 
from datetime import timezone
from sqlalchemy import text, inspect
from pytz import timezone as tz

import bcrypt
import httpx
import os
import asyncio
import uvicorn
import requests

load_dotenv()

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Banco de dados
DATABASE_URL = "sqlite:///./chatwoot_clone.db"
engine = create_engine(DATABASE_URL, echo=True)



@app.get("/", response_class=HTMLResponse)

def form_html():
    return """
     <html>
        <body>
            <h2>Cadastro de Usuário</h2>
            <form action="/cadastrar" method="post">
                Nome: <input type="text" name="nome"><br>
                Email: <input type="email" name="email"><br>
                Senha: <input type="password" name="senha"><br>
                <input type="submit" value="Cadastrar">
            </form>
        </body>
    </html>
    
    """

# Autenticação
SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret")
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


# Modelos
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str
    name: str
    password_hash: str
    role: str


class Conversation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_number: str
    name: Optional[str] = None
    assigned_to: str | None
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "pending"


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int
    sender: str
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ConversationCreate(BaseModel):
    customer_number: str
    initial_message: str

class Usuario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    email: str
    senha: str

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
            session.add(admin_user)  # deve estar dentro do if

        # Cria user padrão se não existir
        standard = session.exec(select(User).where(User.email == "user@test.com")).first()
        if not standard:
            standard_user = User(
                email="user@test.com",
                name="User",
                password_hash=hash_password("senha1234"),
                role="user"
            )
            session.add(standard_user)  # também dentro do if

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
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=30))
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
    except JWTError:
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

# Rotas

@app.post("/cadastrar")
async def cadastrar(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    novo_usuario = Usuario.from_orm(usuario)
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    return f"Usuário {novo_usuario.nome} cadastrado com sucesso!"


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
    if str(conversation.assigned_to) != str(user.id):
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
        try:
            assigned_to = int(conversation.assigned_to) if conversation.assigned_to else None
        except (ValueError, TypeError):
            assigned_to = None

        if assigned_to != user.id:
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
    try:
        # Tentar receber dados como JSON primeiro
        try:
            payload = await request.json()
            from_number = payload.get("from", "").replace("whatsapp:", "")
            message_body = payload.get("message", "")
            profile_name = payload.get("name", "Cliente")
        except:
            # Se falhar, tentar como form data (formato padrão do Twilio)
            form_data = await request.form()
            from_number = form_data.get("From", "").replace("whatsapp:", "")
            message_body = form_data.get("Body", "")
            profile_name = form_data.get("ProfileName", "Cliente")

        print(f"Mensagem recebida de {from_number}: {message_body}")

        if not from_number or not message_body:
            raise HTTPException(status_code=400, detail="Dados incompletos")

        # PRIMEIRA ETAPA: Tentar resposta automática com bots
        
        # Consultar Rasa
        rasa_responses = await query_rasa_bot(message_body, from_number)
        if rasa_responses:
            for rasa_resp in rasa_responses:
                text = rasa_resp.get("text")
                if text and "encaminhar_para_humano" not in text.lower():
                    # Resposta automática do Rasa - envia direto via WhatsApp
                    send_whatsapp_message(from_number, text)
                    
                    # Notifica interface (opcional, para histórico)
                    await manager.send_personal_message({
                        "sender": "bot",
                        "message": text,
                        "conversation_id": None,
                        "customer_number": from_number
                    }, from_number)
                    
                    return {"status": "respondido pelo Rasa"}

        # Consultar Ollama
        ollama_reply = await query_ollama_bot(message_body)
        if ollama_reply and "falar com atendente" not in ollama_reply.lower():
            # Resposta automática do Ollama - envia direto via WhatsApp
            send_whatsapp_message(from_number, ollama_reply)
            
            # Notifica interface (opcional, para histórico)
            await manager.send_personal_message({
                "sender": "bot",
                "message": ollama_reply,
                "conversation_id": None,
                "customer_number": from_number
            }, from_number)
            
            return {"status": "respondido pelo Ollama"}

        # SEGUNDA ETAPA: Se bots não responderam, encaminhar para agente
        
        # Verificar se já existe conversa ativa
        conversation = session.exec(
            select(Conversation).where(
                Conversation.customer_number == from_number,
                Conversation.status == "pending"
            )
        ).first()

        # Se não existe conversa ativa, criar uma nova
        if not conversation:
            agent = get_least_busy_agent(session)
            conversation = Conversation(
                customer_number=from_number,
                name=profile_name,
                assigned_to=agent.id if agent else None,
                created_by=agent.id if agent else None,
                status="pending",
            )
            session.add(conversation)
            session.commit()
            session.refresh(conversation)

            # Enviar mensagem de boas-vindas apenas para conversas novas
            try:
                send_whatsapp_message(from_number, f"Olá {profile_name}, um operador entrará em contato com você em breve.")
            except Exception as e:
                print(f"Erro ao enviar mensagem de boas-vindas: {e}")

        # Salvar mensagem do cliente no banco
        msg = Message(
            conversation_id=conversation.id,
            sender="customer",
            content=message_body
        )
        session.add(msg)
        session.commit()

        # Notificar agentes via WebSocket
        await manager.broadcast({
            "id": msg.id,
            "conversation_id": conversation.id,
            "sender": "customer",
            "message": message_body,
            "timestamp": msg.timestamp.isoformat(),
            "customer_name": profile_name,
            "customer_number": from_number
        })

        return {"status": "encaminhado para operador"}

    except Exception as e:
        print(f"Erro no webhook WhatsApp: {e}")
        return {"status": "erro", "message": str(e)}

@app.post("/conversations/{conversation_id}/assign")
def assign_conversation(conversation_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    conversation.assigned_to = user.id
    session.add(conversation)
    session.commit()
    return {"msg": "Conversa atribuida ao operador"}





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
        timestamp=datetime.utcnow()
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
    except JWTError:
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
app.mount("/", StaticFiles(directory="static", html=True), name="static")