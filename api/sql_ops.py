from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
import os
import uuid
from datetime import datetime, timedelta, date
from sqlalchemy.future import select
import re
import jwt
from dotenv import load_dotenv
from api.pydm import *

load_dotenv()

Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
ALGORITHM = os.environ.get('ALGORITHM')



class User(Base):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    firstName = Column(String, nullable=False)
    lastName = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)

DATABASE_URL = os.environ.get('SQL_DB_URL')
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def create_user(firstName: str, lastName: str, age: int, email: str, raw_password: str):
    async with async_session() as session:
        hashed_password = pwd_context.hash(raw_password)
        new_user = User(
            firstName=firstName,
            lastName=lastName,
            age=age,
            email=email,
            password=hashed_password
        )
        session.add(new_user)
        await session.commit()
        return new_user

async def get_user_by_email(email: str):
    async with async_session() as session:
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

async def get_user_by_id(user_id):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        return user

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def validate_password_strength(password: str) -> bool:
    pattern = r"^(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{8,}$"
    return bool(re.match(pattern, password))

def generate_jwt_token(user_id: str, email: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=12),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)
