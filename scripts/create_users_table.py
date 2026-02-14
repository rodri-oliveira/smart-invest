#!/usr/bin/env python3
"""Criar tabela users manualmente."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aim.data_layer.database import Database

db = Database()

# Criar tabela users
db.execute('''
CREATE TABLE IF NOT EXISTS users (
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

print('Tabela users criada com sucesso!')

# Verificar
result = db.fetch_one("SELECT COUNT(*) as n FROM users")
print(f"Total de usuarios: {result['n']}")
