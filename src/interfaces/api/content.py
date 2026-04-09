from fastapi import APIRouter, Depends
from src.interfaces.api.dependencies import require_role

router=APIRouter(tags=["Content"], prefix="/content")

@router.get("/common")
async def common_content(current_user: dict=Depends(require_role("admin", "user"))):
    return{
        "content": "Общий контент для всех авторизованных",
        "available_for": ["admin", "user"]
    }

@router.get("/admin")
async def admin_content(current_user: dict=Depends(require_role("admin"))):
    return{
        "content": "Контент только для admin",
        "available_for": ["admin"]
    }

@router.get("/user")
async def user_content(current_user: dict=Depends(require_role("user"))):
    return{
        "content": "Контент только для user",
        "available_for": ["user"]
    }

@router.get("/all")
async def all_content():
    return{
        "content": "Контент доступный всем"
    }