#!/usr/bin/env python3
"""Debug completo do sistema de autenticação."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aim.data_layer.database import Database
from aim.auth.manager import AuthManager
import bcrypt

print("DEBUG AUTENTICAÇÃO COMPLETO")
print("=" * 60)

db = Database()

# Verificar se tabela existe
tables = db.fetch_all("SELECT name FROM sqlite_master WHERE type='table'")
table_names = [t['name'] for t in tables]
print(f"Tabelas: {table_names}")

if 'users' not in table_names:
    print("Criando tabela users...")
    db.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            is_admin BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    print("Tabela criada!")

# Testar bcrypt
print("\nTestando bcrypt...")
password = "senha123"
salt = bcrypt.gensalt(rounds=12)
hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
print(f"Hash criado: {hashed.decode('utf-8')[:50]}...")

# Verificar
is_valid = bcrypt.checkpw(password.encode('utf-8'), hashed)
print(f"Verificação: {is_valid}")

# Inserir usuário manualmente
print("\nInserindo usuário manualmente...")
try:
    db.execute(
        "INSERT INTO users (email, password_hash, name, is_active) VALUES (?, ?, ?, ?)",
        ("teste@smartinvest.com", hashed.decode('utf-8'), "Usuario Teste", True)
    )
    print("Usuário inserido!")
except Exception as e:
    print(f"Erro: {e}")

# Verificar
users = db.fetch_all("SELECT id, email, name FROM users")
print(f"\nTotal usuários: {len(users)}")
for u in users:
    print(f"  - {u['email']} (ID: {u['id']})")

# Testar AuthManager
print("\nTestando AuthManager...")
auth = AuthManager(db)
login = auth.authenticate("teste@smartinvest.com", "senha123")
print(f"Resultado login: {login}")
