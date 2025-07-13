from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from sqlmodel import Field, SQLModel, Session, create_engine, select
from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from twilio.rest import Client
import os
import asyncio
import uvicorn


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
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

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

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)


manager = ConnectionManager()

# Cria as tabelas no banco
SQLModel.metadata.create_all(engine)


# Utils
def get_session():
    with Session(engine) as session:
        yield session

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
    return session.exec(select(Conversation)).all()


@app.post("/conversations/{conversation_id}/reply")
def reply(conversation_id: int, payload: dict, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    message = Message(
        conversation_id=conversation_id,
        sender="agent",
        content=payload["message"]
    )
    session.add(message)
    session.commit()

    # envia via WhatsApp (remova se não usar Twilio)
    send_whatsapp_message(conversation.customer_number, payload["message"])

    asyncio.create_task(manager.broadcast({
        "conversation_id": conversation_id,
        "sender": "agent",
        "message": message.content
    }))

    return {"msg": "Mensagem enviada"}


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
        "message": message
    })

    return {"status": "received"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Serve arquivos estáticos HTML/JS
app.mount("/", StaticFiles(directory="static", html=True), name="static")
