"""API endpoints para autenticacao."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from aim.auth import get_auth_manager
from aim.config.settings import get_settings
from aim.data_layer.database import Database
from aim.security.audit import ensure_audit_schema, log_audit_event, purge_old_audit_events

router = APIRouter(tags=["autenticacao"])
security = HTTPBearer(auto_error=False)

_LOGIN_ATTEMPTS: dict[str, list[datetime]] = {}
_LOGIN_WINDOW = timedelta(minutes=10)
_LOGIN_MAX_ATTEMPTS = 8


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
    tenant_id: Optional[int] = 1


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ChangePassword(BaseModel):
    old_password: str
    new_password: str


class TenantFeaturesResponse(BaseModel):
    allow_real_portfolio: bool
    allow_history: bool
    allow_daily_plan: bool


class TenantLimitsResponse(BaseModel):
    max_simulated_positions: int


class TenantProfileResponse(BaseModel):
    tenant_id: int
    tenant_name: Optional[str] = None
    tenant_slug: Optional[str] = None
    plan_code: str
    plan_name: str
    limits: TenantLimitsResponse
    features: TenantFeaturesResponse


class AuditEventResponse(BaseModel):
    id: int
    tenant_id: int
    user_id: Optional[int] = None
    event_type: str
    severity: str
    message: str
    ip_address: Optional[str] = None
    metadata: Optional[str] = None
    created_at: str


class AuditEventListResponse(BaseModel):
    items: list[AuditEventResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


def get_db() -> Database:
    """Dependency para obter conexao com banco."""
    db = Database()
    ensure_audit_schema(db)
    purge_old_audit_events(db)
    return db


def _set_auth_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        secure=settings.auth_cookie_secure or settings.is_production,
        samesite=settings.auth_cookie_samesite,
        max_age=60 * 60 * 24,
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/",
    )


def _login_key(email: str, request: Request) -> str:
    ip = request.client.host if request.client else "unknown"
    return f"{ip}:{email.strip().lower()}"


def _prune_attempts(attempts: list[datetime]) -> list[datetime]:
    now = datetime.utcnow()
    return [ts for ts in attempts if now - ts <= _LOGIN_WINDOW]


def _check_login_limit(email: str, request: Request) -> None:
    key = _login_key(email, request)
    attempts = _prune_attempts(_LOGIN_ATTEMPTS.get(key, []))
    _LOGIN_ATTEMPTS[key] = attempts
    if len(attempts) >= _LOGIN_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Tente novamente em alguns minutos.",
        )


def _register_login_failure(email: str, request: Request) -> None:
    key = _login_key(email, request)
    attempts = _prune_attempts(_LOGIN_ATTEMPTS.get(key, []))
    attempts.append(datetime.utcnow())
    _LOGIN_ATTEMPTS[key] = attempts


def _clear_login_attempts(email: str, request: Request) -> None:
    key = _login_key(email, request)
    _LOGIN_ATTEMPTS.pop(key, None)


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Database = Depends(get_db),
):
    """Dependency para obter usuario atual do token JWT."""
    auth_manager = get_auth_manager(db)
    settings = get_settings()
    token = credentials.credentials if credentials else request.cookies.get(settings.auth_cookie_name)

    user_data = auth_manager.verify_token(token) if token else None
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_data


@router.post("/register", response_model=dict)
async def register(user_data: UserRegister, db: Database = Depends(get_db)):
    """Registra novo usuario no sistema."""
    auth_manager = get_auth_manager(db)

    result = auth_manager.create_user(
        email=user_data.email,
        password=user_data.password,
        name=user_data.name,
    )

    if not result["success"]:
        log_audit_event(
            db,
            tenant_id=1,
            user_id=None,
            event_type="auth.register_failed",
            severity="WARN",
            message=f"Falha de registro para email {user_data.email}",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"],
        )

    log_audit_event(
        db,
        tenant_id=1,
        user_id=None,
        event_type="auth.register_success",
        severity="INFO",
        message=f"Registro criado para email {user_data.email}",
    )
    return {
        "message": "Usuario criado com sucesso",
        "email": user_data.email,
    }


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    request: Request,
    response: Response,
    db: Database = Depends(get_db),
):
    """Autentica usuario e retorna token JWT."""
    auth_manager = get_auth_manager(db)
    _check_login_limit(credentials.email, request)

    result = auth_manager.authenticate(
        email=credentials.email,
        password=credentials.password,
    )

    if not result["success"]:
        _register_login_failure(credentials.email, request)
        log_audit_event(
            db,
            tenant_id=1,
            user_id=None,
            event_type="auth.login_failed",
            severity="WARN",
            message=f"Falha de login para email {credentials.email}",
            ip_address=request.client.host if request.client else None,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result["error"],
            headers={"WWW-Authenticate": "Bearer"},
        )

    _clear_login_attempts(credentials.email, request)
    user_data = result.get("user", {})
    _set_auth_cookie(response, result["token"])
    log_audit_event(
        db,
        tenant_id=user_data.get("tenant_id", 1),
        user_id=user_data.get("id"),
        event_type="auth.login_success",
        severity="INFO",
        message=f"Login realizado para {credentials.email}",
        ip_address=request.client.host if request.client else None,
    )
    return TokenResponse(
        access_token=result["token"],
        user=UserResponse(**user_data),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Retorna informacoes do usuario logado."""
    return UserResponse(
        id=current_user.get("id") or current_user.get("user_id"),
        email=current_user.get("email"),
        name=current_user.get("name"),
        tenant_id=current_user.get("tenant_id", 1),
    )


@router.post("/change-password")
async def change_password(
    passwords: ChangePassword,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Altera senha do usuario logado."""
    auth_manager = get_auth_manager(db)

    result = auth_manager.change_password(
        user_id=current_user["user_id"],
        old_password=passwords.old_password,
        new_password=passwords.new_password,
    )

    if not result["success"]:
        log_audit_event(
            db,
            tenant_id=current_user.get("tenant_id", 1),
            user_id=current_user["user_id"],
            event_type="auth.change_password_failed",
            severity="WARN",
            message=f"Falha na troca de senha para user_id={current_user['user_id']}",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"],
        )

    log_audit_event(
        db,
        tenant_id=current_user.get("tenant_id", 1),
        user_id=current_user["user_id"],
        event_type="auth.change_password_success",
        severity="INFO",
        message=f"Senha alterada para user_id={current_user['user_id']}",
    )
    return {"message": result["message"]}


@router.post("/refresh")
async def refresh_token(
    response: Response,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Gera novo token JWT (refresh)."""
    auth_manager = get_auth_manager(db)

    new_token = auth_manager._generate_token(
        current_user["user_id"],
        current_user["email"],
        current_user.get("tenant_id", 1),
    )
    _set_auth_cookie(response, new_token)

    return {
        "access_token": new_token,
        "token_type": "bearer",
    }


@router.post("/logout")
async def logout(response: Response):
    """Encerra sessão limpando cookie HttpOnly."""
    _clear_auth_cookie(response)
    return {"message": "Logout efetuado com sucesso"}


@router.get("/tenant-profile", response_model=TenantProfileResponse)
async def get_tenant_profile(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Retorna capacidades do tenant (plano, limites e features)."""
    auth_manager = get_auth_manager(db)
    profile = auth_manager.get_tenant_capabilities(current_user.get("tenant_id", 1))
    return TenantProfileResponse(**profile)


@router.get("/audit/recent", response_model=AuditEventListResponse)
async def get_recent_audit_events(
    limit: int = 50,
    offset: int = 0,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    days: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Retorna eventos recentes de auditoria do tenant atual."""
    safe_limit = max(1, min(limit, 200))
    safe_offset = max(0, offset)
    where = ["WHERE tenant_id = ?"]
    params: list[object] = [current_user.get("tenant_id", 1)]

    if event_type:
        where.append("AND event_type = ?")
        params.append(event_type.strip())

    if severity:
        normalized_severity = severity.strip().upper()
        if normalized_severity not in {"INFO", "WARN", "ERROR"}:
            raise HTTPException(status_code=400, detail="severity deve ser INFO, WARN ou ERROR")
        where.append("AND severity = ?")
        params.append(normalized_severity)

    if days is not None:
        safe_days = max(1, min(int(days), 3650))
        where.append("AND datetime(created_at) >= datetime('now', ?)")
        params.append(f"-{safe_days} day")

    where_sql = "\n".join(where)
    total_row = db.fetch_one(
        "\n".join(
            [
                "SELECT COUNT(*) AS total",
                "FROM audit_events",
                where_sql,
            ]
        ),
        tuple(params),
    ) or {"total": 0}
    total = int(total_row.get("total") or 0)

    query = [
        "SELECT id, tenant_id, user_id, event_type, severity, message, ip_address, metadata, created_at",
        "FROM audit_events",
        where_sql,
        "ORDER BY created_at DESC",
        "LIMIT ? OFFSET ?",
    ]
    rows = db.fetch_all("\n".join(query), tuple([*params, safe_limit, safe_offset])) or []
    items = [
        AuditEventResponse(
            id=row["id"],
            tenant_id=row["tenant_id"],
            user_id=row.get("user_id"),
            event_type=row["event_type"],
            severity=row.get("severity") or "INFO",
            message=row["message"],
            ip_address=row.get("ip_address"),
            metadata=row.get("metadata"),
            created_at=(
                row["created_at"].isoformat()
                if hasattr(row["created_at"], "isoformat")
                else str(row["created_at"])
            ),
        )
        for row in rows
    ]
    return AuditEventListResponse(
        items=items,
        total=total,
        limit=safe_limit,
        offset=safe_offset,
        has_more=(safe_offset + len(items)) < total,
    )
