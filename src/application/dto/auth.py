from pydantic import BaseModel, ConfigDict

class TokenSchema(BaseModel):
    token: str

class UserSchema(BaseModel):
    id: str
    email: str
    role: str

class LoginDTO(BaseModel):
    email: str
    password: str

class RegisterDTO(BaseModel):
    email: str
    password: str
    role: str="user"

class DummyLoginDTO(BaseModel):
    role: str