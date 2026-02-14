"""Sistema de Autenticação e Gerenciamento de Usuários."""

import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from dataclasses import dataclass

from aim.data_layer.database import Database

# Configuração JWT
JWT_SECRET = "smart-invest-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


@dataclass
class User:
    """Representação de um usuário do sistema."""
    id: int
    email: str
    name: str
    is_active: bool
    created_at: str
    last_login: Optional[str] = None


class AuthManager:
    """Gerenciador de autenticação de usuários."""
    
    def __init__(self, db: Database):
        self.db = db
    
    def create_user(self, email: str, password: str, name: str) -> Dict[str, Any]:
        """
        Cria novo usuário no sistema.
        
        Args:
            email: Email do usuário (único)
            password: Senha em texto plano (será hasheada)
            name: Nome completo
            
        Returns:
            Dict com status e mensagem
        """
        # Verificar se email já existe
        existing = self.db.fetch_one(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        )
        
        if existing:
            return {"success": False, "error": "Email já cadastrado"}
        
        # Hash da senha
        password_hash = self._hash_password(password)
        
        # Inserir usuário
        try:
            # Usar transação para garantir commit
            with self.db.transaction() as conn:
                conn.execute(
                    """
                    INSERT INTO users (email, password_hash, name, is_active, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (email, password_hash, name, True, datetime.now().isoformat())
                )
            
            return {
                "success": True,
                "message": "Usuário criado com sucesso",
                "email": email
            }
            
        except Exception as e:
            return {"success": False, "error": f"Erro ao criar usuário: {e}"}
    
    def authenticate(self, email: str, password: str) -> Dict[str, Any]:
        """
        Autentica usuário e gera token JWT.
        
        Args:
            email: Email do usuário
            password: Senha em texto plano
            
        Returns:
            Dict com token ou erro
        """
        # Buscar usuário
        user = self.db.fetch_one(
            "SELECT id, email, name, password_hash, is_active FROM users WHERE email = ?",
            (email,)
        )
        
        if not user:
            return {"success": False, "error": "Credenciais inválidas"}
        
        if not user["is_active"]:
            return {"success": False, "error": "Usuário desativado"}
        
        # Verificar senha
        if not self._verify_password(password, user["password_hash"]):
            return {"success": False, "error": "Credenciais inválidas"}
        
        # Atualizar último login
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (datetime.now().isoformat(), user["id"])
            )
        
        # Gerar token JWT
        token = self._generate_token(user["id"], user["email"])
        
        return {
            "success": True,
            "token": token,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "name": user["name"]
            }
        }
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verifica validade do token JWT.
        
        Args:
            token: Token JWT
            
        Returns:
            Dict com dados do usuário ou None
        """
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            
            # Verificar se usuário ainda existe e está ativo
            user = self.db.fetch_one(
                "SELECT id, email, name, is_active FROM users WHERE id = ?",
                (payload["user_id"],)
            )
            
            if not user or not user["is_active"]:
                return None
            
            return {
                "user_id": user["id"],
                "email": user["email"],
                "name": user["name"]
            }
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> Dict[str, Any]:
        """
        Altera senha do usuário.
        
        Args:
            user_id: ID do usuário
            old_password: Senha atual
            new_password: Nova senha
            
        Returns:
            Dict com status
        """
        # Buscar usuário
        user = self.db.fetch_one(
            "SELECT password_hash FROM users WHERE id = ?",
            (user_id,)
        )
        
        if not user:
            return {"success": False, "error": "Usuário não encontrado"}
        
        # Verificar senha atual
        if not self._verify_password(old_password, user["password_hash"]):
            return {"success": False, "error": "Senha atual incorreta"}
        
        # Hash nova senha
        new_hash = self._hash_password(new_password)
        
        # Atualizar
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (new_hash, user_id)
            )
        
        return {"success": True, "message": "Senha alterada com sucesso"}
    
    def _hash_password(self, password: str) -> str:
        """Gera hash bcrypt da senha."""
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verifica senha contra hash."""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def _generate_token(self, user_id: int, email: str) -> str:
        """Gera token JWT."""
        payload = {
            "user_id": user_id,
            "email": email,
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# Instância global
_auth_manager = None

def get_auth_manager(db: Database = None) -> AuthManager:
    """Retorna instância singleton do AuthManager."""
    global _auth_manager
    if _auth_manager is None:
        if db is None:
            db = Database()
        _auth_manager = AuthManager(db)
    return _auth_manager
