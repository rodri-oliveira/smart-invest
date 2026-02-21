"""Sistema de Autenticacao e Gerenciamento de Usuarios."""

import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from dataclasses import dataclass

from aim.config.settings import get_settings
from aim.data_layer.database import Database

# Configuracao JWT
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
JWT_SECRET = get_settings().secret_key


@dataclass
class User:
    """Representacao de um usuario do sistema."""

    id: int
    email: str
    name: str
    tenant_id: int
    is_active: bool
    created_at: str
    last_login: Optional[str] = None


class AuthManager:
    """Gerenciador de autenticacao de usuarios."""

    def __init__(self, db: Database):
        self.db = db
        self._ensure_tenant_schema()

    def _ensure_tenant_schema(self) -> None:
        """Garante estrutura minima para isolamento logico por tenant."""
        try:
            self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS tenants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(255) NOT NULL,
                    slug VARCHAR(100) UNIQUE NOT NULL,
                    plan_code VARCHAR(50) DEFAULT 'free',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self.db.execute(
                """
                INSERT OR IGNORE INTO tenants (id, name, slug, is_active)
                VALUES (1, 'Default Tenant', 'default', 1)
                """
            )
            tenant_columns = self.db.fetch_all("PRAGMA table_info(tenants)")
            tenant_column_names = {col["name"] for col in tenant_columns} if tenant_columns else set()
            if "plan_code" not in tenant_column_names:
                self.db.execute("ALTER TABLE tenants ADD COLUMN plan_code VARCHAR(50) DEFAULT 'free'")
                self.db.execute("UPDATE tenants SET plan_code = 'free' WHERE plan_code IS NULL")

            self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS subscription_plans (
                    code VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(120) NOT NULL,
                    max_simulated_positions INTEGER NOT NULL,
                    allow_real_portfolio BOOLEAN DEFAULT FALSE,
                    allow_history BOOLEAN DEFAULT TRUE,
                    allow_daily_plan BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self.db.execute(
                """
                INSERT OR IGNORE INTO subscription_plans
                (code, name, max_simulated_positions, allow_real_portfolio, allow_history, allow_daily_plan)
                VALUES
                ('free', 'Plano Free', 10, 0, 1, 1),
                ('edu', 'Plano Educacional', 20, 0, 1, 1),
                ('pro', 'Plano Pro', 60, 1, 1, 1)
                """
            )
            self.db.execute("UPDATE tenants SET plan_code = COALESCE(plan_code, 'free')")

            columns = self.db.fetch_all("PRAGMA table_info(users)")
            column_names = {col["name"] for col in columns} if columns else set()
            if "tenant_id" not in column_names:
                self.db.execute("ALTER TABLE users ADD COLUMN tenant_id INTEGER")
                self.db.execute("UPDATE users SET tenant_id = 1 WHERE tenant_id IS NULL")

            self.db.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_tenant_email ON users(tenant_id, email)"
            )
        except Exception:
            # Nao bloqueia autenticacao em ambiente legado.
            pass

    def get_tenant_capabilities(self, tenant_id: int) -> Dict[str, Any]:
        """Retorna plano, limites e feature flags do tenant."""
        tenant = self.db.fetch_one(
            "SELECT id, name, slug, plan_code, is_active FROM tenants WHERE id = ?",
            (tenant_id,),
        )
        if not tenant:
            return {
                "tenant_id": tenant_id,
                "plan_code": "free",
                "plan_name": "Plano Free",
                "limits": {"max_simulated_positions": 10},
                "features": {
                    "allow_real_portfolio": False,
                    "allow_history": True,
                    "allow_daily_plan": True,
                },
            }

        plan_code = tenant.get("plan_code") or "free"
        plan = self.db.fetch_one(
            """
            SELECT code, name, max_simulated_positions, allow_real_portfolio, allow_history, allow_daily_plan
            FROM subscription_plans
            WHERE code = ?
            """,
            (plan_code,),
        )
        if not plan:
            plan = self.db.fetch_one(
                """
                SELECT code, name, max_simulated_positions, allow_real_portfolio, allow_history, allow_daily_plan
                FROM subscription_plans
                WHERE code = 'free'
                """
            ) or {
                "code": "free",
                "name": "Plano Free",
                "max_simulated_positions": 10,
                "allow_real_portfolio": 0,
                "allow_history": 1,
                "allow_daily_plan": 1,
            }

        return {
            "tenant_id": tenant["id"],
            "tenant_name": tenant.get("name"),
            "tenant_slug": tenant.get("slug"),
            "plan_code": plan.get("code", "free"),
            "plan_name": plan.get("name", "Plano Free"),
            "limits": {
                "max_simulated_positions": int(plan.get("max_simulated_positions") or 10),
            },
            "features": {
                "allow_real_portfolio": bool(plan.get("allow_real_portfolio")),
                "allow_history": bool(plan.get("allow_history")),
                "allow_daily_plan": bool(plan.get("allow_daily_plan")),
            },
        }

    def create_user(self, email: str, password: str, name: str, tenant_id: int = 1) -> Dict[str, Any]:
        """
        Cria novo usuario no sistema.

        Args:
            email: Email do usuario (unico)
            password: Senha em texto plano (sera hasheada)
            name: Nome completo
            tenant_id: Tenant logico

        Returns:
            Dict com status e mensagem
        """
        existing = self.db.fetch_one("SELECT id FROM users WHERE email = ?", (email,))

        if existing:
            return {"success": False, "error": "Email ja cadastrado"}

        password_hash = self._hash_password(password)

        try:
            with self.db.transaction() as conn:
                conn.execute(
                    """
                    INSERT INTO users (email, password_hash, name, tenant_id, is_active, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (email, password_hash, name, tenant_id, True, datetime.now().isoformat()),
                )

            return {
                "success": True,
                "message": "Usuario criado com sucesso",
                "email": email,
            }

        except Exception as e:
            return {"success": False, "error": f"Erro ao criar usuario: {e}"}

    def authenticate(self, email: str, password: str) -> Dict[str, Any]:
        """
        Autentica usuario e gera token JWT.

        Args:
            email: Email do usuario
            password: Senha em texto plano

        Returns:
            Dict com token ou erro
        """
        user = self.db.fetch_one(
            "SELECT id, email, name, tenant_id, password_hash, is_active FROM users WHERE email = ?",
            (email,),
        )

        if not user:
            return {"success": False, "error": "Credenciais invalidas"}

        if not user["is_active"]:
            return {"success": False, "error": "Usuario desativado"}

        if not self._verify_password(password, user["password_hash"]):
            return {"success": False, "error": "Credenciais invalidas"}

        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (datetime.now().isoformat(), user["id"]),
            )

        tenant_id = user.get("tenant_id") or 1
        token = self._generate_token(user["id"], user["email"], tenant_id)

        return {
            "success": True,
            "token": token,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "name": user["name"],
                "tenant_id": tenant_id,
            },
        }

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verifica validade do token JWT.

        Args:
            token: Token JWT

        Returns:
            Dict com dados do usuario ou None
        """
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

            user = self.db.fetch_one(
                "SELECT id, email, name, tenant_id, is_active FROM users WHERE id = ?",
                (payload["user_id"],),
            )

            if not user or not user["is_active"]:
                return None

            return {
                "user_id": user["id"],
                "email": user["email"],
                "name": user["name"],
                "tenant_id": user.get("tenant_id") or payload.get("tenant_id") or 1,
            }

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def change_password(self, user_id: int, old_password: str, new_password: str) -> Dict[str, Any]:
        """
        Altera senha do usuario.

        Args:
            user_id: ID do usuario
            old_password: Senha atual
            new_password: Nova senha

        Returns:
            Dict com status
        """
        user = self.db.fetch_one("SELECT password_hash FROM users WHERE id = ?", (user_id,))

        if not user:
            return {"success": False, "error": "Usuario nao encontrado"}

        if not self._verify_password(old_password, user["password_hash"]):
            return {"success": False, "error": "Senha atual incorreta"}

        new_hash = self._hash_password(new_password)

        with self.db.transaction() as conn:
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))

        return {"success": True, "message": "Senha alterada com sucesso"}

    def _hash_password(self, password: str) -> str:
        """Gera hash bcrypt da senha."""
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verifica senha contra hash."""
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

    def _generate_token(self, user_id: int, email: str, tenant_id: int = 1) -> str:
        """Gera token JWT."""
        payload = {
            "user_id": user_id,
            "email": email,
            "tenant_id": tenant_id,
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# Instancia global
_auth_manager = None


def get_auth_manager(db: Database = None) -> AuthManager:
    """Retorna instancia singleton do AuthManager."""
    global _auth_manager
    settings = get_settings()
    if settings.is_production and (not settings.secret_key or len(settings.secret_key) < 32):
        raise RuntimeError("SECRET_KEY invalida para producao. Use no minimo 32 caracteres.")
    if _auth_manager is None:
        if db is None:
            db = Database()
        _auth_manager = AuthManager(db)
    elif db is not None and getattr(_auth_manager, "db", None) is not db:
        # Permite trocar instancia em testes/dependencias com DB dedicado.
        _auth_manager = AuthManager(db)
    return _auth_manager
