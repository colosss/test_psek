from fastapi import APIRouter, Depends, HTTPException
from src.infrastructure.database.db_helper import db_helper
from src.interfaces.api.dependencies import require_role

router=APIRouter(tags=["Content"], prefix="/content")

@router.get("/common")
async def common_content(session=Depends(require_role("admin", "user"))):
    return{
        "content": "Общий контент для всех авторизованных",
        "avilable_for": ["admin", "user"]
    }

@router.get("/admin")
async def admin_content(session=Depends(require_role("admin"))):
    return{
        "content": "Контент только для admin",
        "avilable_for": ["admin"]
    }

@router.get("/user")
async def user_content(session=Depends(require_role("user"))):
    return{
        "content": "Контент только для user",
        "avilable_for": ["user"]
    }

@router.get("/all")
async def all_content():
    return{
        "content": "Контент доступный всем"
    }