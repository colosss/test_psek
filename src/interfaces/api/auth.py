from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from src.infrastructure.database.db_helper import db_helper
from src.application.dto.auth import (
    UserSchema,
    TokenSchema,
    LoginDTO,
    RegisterDTO,
    DummyLoginDTO
)
from src.infrastructure.database.repositories.user import UserRepository
from src.application.use_case.auth import (
    LoginUseCase,
    RegisterUseCase,
    DummyLoginUseCase,
    LogoutUseCase,
)
from src.interfaces.api.dependencies import get_current_user, bearer

router=APIRouter(tags=["Auth"])

@router.post("/dummylogin", response_model=TokenSchema)
async def dummy_login(
    body: DummyLoginDTO,
    session=Depends(db_helper.session_dependency)
):
    try:
        token=await DummyLoginUseCase(UserRepository(session)).execute(body.role)
    except ValueError as e:
        raise HTTPException(400, detail={"error": {"code": "INVALID_REQUEST", "message": str(e)}})
    return TokenSchema(token=token)

@router.post("/login", response_model=TokenSchema)
async def login(
    body: LoginDTO,
    session=Depends(db_helper.session_dependency)
):
    try:
        token=await LoginUseCase(UserRepository(session)).execute(
            body.email,
            body.password,
        )
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "UNAUTHORIZED", "message": "invalid credentials"}}
        )
    return TokenSchema(token=token)

@router.post("/register", response_model=UserSchema, status_code=201)
async def register(
    body: RegisterDTO,
    session=Depends(db_helper.session_dependency)
):
    try:
        user=await RegisterUseCase(UserRepository(session)).execute(
            body.email,
            body.password,
            body.role,
        )
    except ValueError as e:
        raise HTTPException(400, detail={"error": {"code": "INVALID_REQUEST", "message": str(e)}})
    return UserSchema(id=str(user.id), email=user.email, role=user.role)

@router.post("/logout")
async def logout(
    current_user: dict=Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials=Depends(bearer)
):
    token=credentials.credentials
    await LogoutUseCase().execute(token=token, user_id=current_user["user_id"])
    return {"message": "logged out"}