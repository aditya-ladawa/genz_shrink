from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional


class UserInDB(BaseModel):
    user_id: str
    firstName: str
    lastName: str
    age: int
    email: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None


class UserCreate(BaseModel):
    firstName: str
    lastName: str
    age: int
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class LabelChatRequest(BaseModel):
    message: str

class MemeTemplate(BaseModel):
    id: str
    name: str
    box_count: int

class GeneratedMeme(BaseModel):
    url: str
    template_name: str