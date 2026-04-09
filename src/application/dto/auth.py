from pydantic import BaseModel, ConfigDict
from typing import Optional

class UserSchema(BaseModel):
    id: str
    email: Optional[str] = None
    role: str

class LoginDTO(BaseModel):
    email: str
    password: str
    device_id: str

class RegisterDTO(BaseModel):
    email: str
    password: str
    role: str="user"

class DummyLoginDTO(BaseModel):
    role: str
    device_id: str

class TokenPairSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str="bearer"
