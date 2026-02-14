"""Auth module - Sistema de autenticação."""

from aim.auth.manager import (
    AuthManager,
    User,
    get_auth_manager,
    JWT_SECRET,
    JWT_EXPIRATION_HOURS,
)

__all__ = [
    "AuthManager",
    "User", 
    "get_auth_manager",
    "JWT_SECRET",
    "JWT_EXPIRATION_HOURS",
]
