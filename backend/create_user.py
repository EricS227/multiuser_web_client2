from sqlmodel import Session, select
from main import engine, User, hash_password

with Session(engine) as session:
    user = User (
        email="admin@teste.com",
        name="Admin",
        password_hash=hash_password("123456"),
        role="admin"
    )
    session.add(user)
    session.commit()
    print("Usuário criado com sucesso")