from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from sqlmodel import Field, SQLModel, Session, create_engine, select
from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from twilio.rest import Client
from pydantic import BaseModel
from dotenv import load_dotenv 

import os
import asyncio
import uvicorn

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

# Autenticação
SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Twilio (opcional, pode remover se não for usar)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID") or "SEU_ACCOUNT_SID"
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN") or "SEU_AUTH_TOKEN"
TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"
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
    assigned_to: Optional[int] = None
    status: str = "pending"


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int
    sender: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ConversationCreate(BaseModel):
    customer_number: str
    initial_message: str


# WebSocket Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        #await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

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





# Utils
@app.on_event("startup")
def create_admin_user():
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.email == "admin@test.com")).first()
        if not existing:
            user = User(email="admin@test.com", name="Admin", password_hash=hash_password("senha123"), role="admin")
            session.add(user)
            session.commit()

            
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


# Envia mensagem pelo WhatsApp (opcional)
def send_whatsapp_message(to_number: str, message: str):
    try:
        msg = twilio_client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_FROM,
            to=f"whatsapp:{to_number}"
        )
        return msg.sid
    except Exception as e:
        print(f"Erro ao enviar mensagem via WhatsApp: {e}")


# Rotas
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
        "conversation_id": conversation_id,
        "sender": "agent",
        "message": message.content
    })
    return {"msg": "Mensagem enviada"}


@app.post("/conversations/{conversation_id}/end")
def end_conversation(conversation_id: int, db: Session = Depends(get_session), user=Depends(get_current_user)):
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="conversation not found")
    if conversation.assigned_to != user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    conversation.status = "closed"
    db.commit()
    return {"detail": "Conversation ended"}
@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request, session: Session = Depends(get_session)):
    payload = await request.json()
    number = payload.get("from")
    message = payload.get("message")

    if not number or not message:
        raise HTTPException(status_code=400, detail="Dados incompletos")

    conversation = session.exec(select(Conversation).where(Conversation.customer_number == number)).first()
    if not conversation:
        conversation = Conversation(customer_number=number)
        session.add(conversation)
        session.commit()
        session.refresh(conversation)

    msg = Message(
        conversation_id=conversation.id,
        sender="customer",
        content=message
    )
    session.add(msg)
    session.commit()

    await manager.broadcast({
        "conversation_id": conversation.id,
        "sender": "customer",
        "message": message,
        "timestamp": msg.timestamp.isoformat()
    })

    return {"status": "received"}



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
    conversation = Conversation(
        customer_number=data.customer_number,
        status="pending",
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
    
    if conversation.assigned_to != user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    messages = session.exec(
        select(Message).where(Message.conversation_id == conversation_id)
    ).all()
    return messages

@app.get("/my-conversations")
def get_my_conversations(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    return session.exec(
        select(Conversation).where(Conversation.assigned_to == user.id)
    ).all()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Token inválido")

        with Session(engine) as session:
            user = session.exec(select(User).where(User.email == email)).first()
            if not user:
                await websocket.send_json({"error": "Usuário inválido"})
                await websocket.close(code=1008)
                return
    except JWTError:
        await websocket.send_json({"error": "Token inválido"})
        await websocket.close(code=1008)
        return

    await websocket.accept()
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
       

#@app.websocket("/ws")
#async def websocket_endpoint(websocket: WebSocket):
   # await websocket.accept()
    #while True:
        #await websocket.receive_text()



# Serve arquivos estáticos HTML/JS
app.mount("/", StaticFiles(directory="static", html=True), name="static")
