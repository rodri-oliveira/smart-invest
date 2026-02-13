"""Camada de acesso ao banco de dados."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from aim.config.settings import get_settings


class Database:
    """Gerenciador de conexão com SQLite."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        """
        Inicializa conexão com banco.

        Args:
            db_path: Caminho do arquivo SQLite. Se None, usa settings.
        """
        if db_path is None:
            db_path = get_settings().db_path

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Cria conexão configurada."""
        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row  # Permite acesso por nome de coluna
        return conn

    @contextmanager
    def connection(self):
        """Context manager para conexões."""
        conn = self._get_connection()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self):
        """Context manager para transações (com commit/rollback)."""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute(
        self,
        query: str,
        parameters: Optional[tuple] = None,
        fetch: bool = False,
    ) -> Union[None, List[Dict[str, Any]]]:
        """
        Executa query SQL.

        Args:
            query: Query SQL
            parameters: Parâmetros da query (para prepared statements)
            fetch: Se True, retorna resultados

        Returns:
            Lista de dicionários se fetch=True, None caso contrário
        """
        with self.connection() as conn:
            cursor = conn.execute(query, parameters or ())
            if fetch:
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            return None

    def execute_many(self, query: str, parameters_list: List[tuple]) -> None:
        """Executa query múltiplas vezes (batch insert)."""
        with self.transaction() as conn:
            conn.executemany(query, parameters_list)

    def fetch_one(
        self,
        query: str,
        parameters: Optional[tuple] = None,
    ) -> Optional[Dict[str, Any]]:
        """Retorna primeira linha do resultado."""
        with self.connection() as conn:
            cursor = conn.execute(query, parameters or ())
            row = cursor.fetchone()
            return dict(row) if row else None

    def fetch_all(
        self,
        query: str,
        parameters: Optional[tuple] = None,
    ) -> List[Dict[str, Any]]:
        """Retorna todas as linhas do resultado."""
        with self.connection() as conn:
            cursor = conn.execute(query, parameters or ())
            return [dict(row) for row in cursor.fetchall()]

    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """
        Insert simples em uma tabela.

        Args:
            table: Nome da tabela
            data: Dicionário com colunas/valores

        Returns:
            ID da última linha inserida
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        with self.transaction() as conn:
            cursor = conn.execute(query, tuple(data.values()))
            return cursor.lastrowid

    def upsert(
        self,
        table: str,
        data: Dict[str, Any],
        conflict_columns: List[str],
    ) -> None:
        """
        Insert ou Update (UPSERT) para SQLite.

        Args:
            table: Nome da tabela
            data: Dicionário com colunas/valores
            conflict_columns: Colunas da PRIMARY KEY para detectar conflito
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        updates = ", ".join([f"{col} = excluded.{col}" for col in data.keys()])
        conflict = ", ".join(conflict_columns)

        query = f"""
            INSERT INTO {table} ({columns}) VALUES ({placeholders})
            ON CONFLICT({conflict}) DO UPDATE SET {updates}
        """

        with self.transaction() as conn:
            conn.execute(query, tuple(data.values()))

    def query_to_df(
        self,
        query: str,
        parameters: Optional[tuple] = None,
    ) -> pd.DataFrame:
        """Executa query e retorna DataFrame pandas."""
        with self.connection() as conn:
            return pd.read_sql_query(query, conn, params=parameters)

    def table_exists(self, table_name: str) -> bool:
        """Verifica se tabela existe."""
        query = """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name=?
        """
        result = self.fetch_one(query, (table_name,))
        return result is not None

    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Retorna informações das colunas da tabela."""
        return self.fetch_all(f"PRAGMA table_info({table_name})")

    def close(self) -> None:
        """Fecha conexão (placeholder, usamos context managers)."""
        pass


# Instância global
db = Database()


def get_db() -> Database:
    """Retorna instância do banco de dados."""
    return db


def init_database() -> None:
    """Inicializa banco com tabelas e dados iniciais."""
    from scripts.init_database import create_tables, seed_initial_data

    create_tables()
    seed_initial_data()
    print("✓ Banco de dados inicializado com sucesso!")
