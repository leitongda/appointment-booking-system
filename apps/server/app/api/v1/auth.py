from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

router = APIRouter()

class LoginRequest(BaseModel):
    phone: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int

@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    """用户登录"""
    # TODO: 实现登录逻辑
    return {
        "access_token": "mock_access_token",
        "refresh_token": "mock_refresh_token",
        "token_type": "Bearer",
        "expires_in": 1800
    }

@router.post("/register")
async def register(data: LoginRequest):
    """用户注册"""
    return {"message": "注册成功"}

@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """刷新Token"""
    return {"access_token": "new_access_token", "token_type": "Bearer"}

