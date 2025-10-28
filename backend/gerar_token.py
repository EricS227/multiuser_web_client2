from jose import jwt
from datetime import datetime, timedelta

SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"



def create_token(email: str):
    expire = datetime.utcnow() + timedelta(minutes=30)
    payload = {"sub": email, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)



email_do_usuario = "admin@teste.com"

token = create_token(email_do_usuario)
print("Token JWT:")
print(token)