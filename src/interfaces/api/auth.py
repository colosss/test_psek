from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from src.infrastructure.database.db_helper import db_helper
from src.application.dto.auth import (
    UserSchema,
    TokenPairSchema,
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
    RefreshTokenUseCase,
)
from src.interfaces.api.dependencies import get_current_user, bearer

router=APIRouter(tags=["Auth"])

@router.post("/dummylogin", response_model=TokenPairSchema)
async def dummy_login(
    body: DummyLoginDTO,
    session=Depends(db_helper.session_dependency)
):
    try:
        tokens=await DummyLoginUseCase(UserRepository(session)).execute(
            body.role,
            body.device_id,
            )
    except ValueError as e:
        raise HTTPException(400, detail={"error": {"code": "INVALID_REQUEST", "message": str(e)}})
    return TokenPairSchema(**tokens)

@router.post("/login", response_model=TokenPairSchema)
async def login(
    body: LoginDTO,
    session=Depends(db_helper.session_dependency)
):
    try:
        tokens=await LoginUseCase(UserRepository(session)).execute(
            body.email,
            body.password,
            body.device_id,
        )
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "UNAUTHORIZED", "message": "invalid credentials"}}
        )
    return TokenPairSchema(**tokens)

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
    device_id: str,
    current_user: dict=Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials=Depends(bearer)
):
    await LogoutUseCase().execute(
        access_token=credentials.credentials, 
        user_id=current_user["user_id"], 
        device_id=device_id)
    return {"message": "logged out"}

@router.post("/refresh", response_model=TokenPairSchema)
async def refresh_token(
    device_id: str,
    credentials: HTTPAuthorizationCredentials=Depends(bearer),
    session=Depends(db_helper.session_dependency)
):
    
    try:
        tokens = await RefreshTokenUseCase(UserRepository(session)).execute(
            refresh_token=credentials.credentials,
            device_id=device_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "UNAUTHORIZED", "message": str(e)}},
        )
    return TokenPairSchema(**tokens)
