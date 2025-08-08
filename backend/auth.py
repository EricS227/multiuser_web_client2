from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session, select
from backend.models import User
from backend.config import SECRET_KEY, ALGORITHM, engine

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def credentials_exception():
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )

def get_session():
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()

def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception()
    except JWTError:
        raise credentials_exception()

    user = session.exec(select(User).where(User.email == email)).first()
    if user is None:
        raise credentials_exception()
    return user