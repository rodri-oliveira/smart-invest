"""API endpoints para autenticação."""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional

from aim.auth import get_auth_manager, JWT_SECRET
from aim.data_layer.database import Database

router = APIRouter(tags=["autenticação"])
security = HTTPBearer()

# Schemas Pydantic
class UserRegister(BaseModel):
    email: str
    password: str
    name: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    name: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class ChangePassword(BaseModel):
    old_password: str
    new_password: str


def get_db():
    """Dependency para obter conexão com banco."""
    db = Database()
    return db


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Database = Depends(get_db)):
    """Dependency para obter usuário atual do token JWT."""
    auth_manager = get_auth_manager(db)
    token = credentials.credentials
    
    user_data = auth_manager.verify_token(token)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_data


@router.post("/register", response_model=dict)
async def register(user_data: UserRegister, db: Database = Depends(get_db)):
    """
    Registra novo usuário no sistema.
    """
    auth_manager = get_auth_manager(db)
    
    result = auth_manager.create_user(
        email=user_data.email,
        password=user_data.password,
        name=user_data.name
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return {
        "message": "Usuário criado com sucesso",
        "email": user_data.email
    }


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Database = Depends(get_db)):
    """
    Autentica usuário e retorna token JWT.
    """
    auth_manager = get_auth_manager(db)
    
    result = auth_manager.authenticate(
        email=credentials.email,
        password=credentials.password
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result["error"],
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return TokenResponse(
        access_token=result["token"],
        user=UserResponse(**result["user"])
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Retorna informações do usuário logado.
    """
    return UserResponse(**current_user)


@router.post("/change-password")
async def change_password(
    passwords: ChangePassword,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Altera senha do usuário logado.
    """
    auth_manager = get_auth_manager(db)
    
    result = auth_manager.change_password(
        user_id=current_user["user_id"],
        old_password=passwords.old_password,
        new_password=passwords.new_password
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return {"message": result["message"]}


@router.post("/refresh")
async def refresh_token(current_user: dict = Depends(get_current_user), db: Database = Depends(get_db)):
    """
    Gera novo token JWT (refresh).
    """
    auth_manager = get_auth_manager(db)
    
    # Gerar novo token
    new_token = auth_manager._generate_token(
        current_user["user_id"],
        current_user["email"]
    )
    
    return {
        "access_token": new_token,
        "token_type": "bearer"
    }
