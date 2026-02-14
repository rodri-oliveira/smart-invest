#!/usr/bin/env python3
"""Debug do sistema de autenticação."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aim.data_layer.database import Database
from aim.auth import get_auth_manager
import bcrypt

db = Database()
auth = get_auth_manager(db)

print("DEBUG AUTENTICAÇÃO")
print("=" * 60)

# Verificar se usuário existe
user = db.fetch_one(
    "SELECT id, email, password_hash FROM users WHERE email = ?",
    ("teste@smartinvest.com",)
)

if user:
    print(f"Usuário encontrado: {user['email']}")
    print(f"Hash armazenado: {user['password_hash'][:60]}...")
    
    # Testar verificação manual
    password = "senha123"
    hash_stored = user['password_hash']
    
    # Verificar se é bytes
    if isinstance(hash_stored, str):
        hash_stored = hash_stored.encode('utf-8')
    
    result = bcrypt.checkpw(password.encode('utf-8'), hash_stored)
    print(f"Verificação manual: {result}")
    
    # Verificar usando AuthManager
    result_auth = auth._verify_password("senha123", user['password_hash'])
    print(f"Verificação AuthManager: {result_auth}")
else:
    print("Usuário não encontrado!")
