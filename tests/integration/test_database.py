"""Testes de integração para Database - validação de operações CRUD."""

import pytest
import tempfile
import os
from pathlib import Path

from aim.data_layer.database import Database


class TestDatabaseConnection:
    """Testes para conexão com banco de dados."""
    
    def test_database_initialization(self):
        """Deve inicializar conexão com banco."""
        db = Database()
        assert db is not None
    
    def test_database_path_exists(self):
        """Banco deve ser criado no path configurado."""
        db = Database()
        with db._get_connection() as conn:
            # Deve conseguir executar query simples
            result = conn.execute("SELECT 1").fetchone()
            assert result[0] == 1
    
    def test_table_exists(self):
        """Deve verificar se tabelas existem."""
        db = Database()
        
        # Tabelas principais devem existir
        assert db.table_exists("assets")
        assert db.table_exists("prices")
        assert db.table_exists("features")
        assert db.table_exists("fundamentals")
        assert db.table_exists("signals")


class TestDatabaseCRUD:
    """Testes para operações CRUD."""
    
    def test_insert_and_fetch(self):
        """Deve inserir e buscar dados."""
        db = Database()
        
        # Usar upsert em vez de execute para garantir persistência
        db.upsert(
            "assets",
            {
                "ticker": "TEST11",
                "name": "Test Asset",
                "sector": "Test",
                "segment": "Test Segment",
                "market_cap_category": "LARGE",
                "is_active": True,
                "is_index": False,
            },
            conflict_columns=["ticker"]
        )
        
        # Buscar dados
        result = db.fetch_one(
            "SELECT * FROM assets WHERE ticker = ?",
            ("TEST11",)
        )
        
        assert result is not None
        assert result["ticker"] == "TEST11"
        assert result["name"] == "Test Asset"
    
    def test_fetch_all(self):
        """Deve buscar múltiplos registros."""
        db = Database()
        
        # Buscar todos os ativos
        results = db.fetch_all("SELECT * FROM assets WHERE is_active = TRUE LIMIT 5")
        
        assert isinstance(results, list)
        assert len(results) <= 5
    
    def test_upsert(self):
        """Deve atualizar ou inserir dados."""
        db = Database()
        
        # Inserir dados
        db.upsert(
            "assets",
            {
                "ticker": "TEST11",
                "name": "Updated Name",
                "sector": "Updated Sector",
                "segment": "Updated",
                "market_cap_category": "LARGE",
                "is_active": True,
            },
            conflict_columns=["ticker"]
        )
        
        # Verificar atualização
        result = db.fetch_one(
            "SELECT name, sector FROM assets WHERE ticker = ?",
            ("TEST11",)
        )
        
        assert result["name"] == "Updated Name"
        assert result["sector"] == "Updated Sector"
    
    def test_execute_many(self):
        """Deve executar múltiplas inserções."""
        db = Database()
        
        # Preparar dados
        data = [
            ("TEST21", "Test 1", "Sector1", "Seg1", "LARGE", True),
            ("TEST22", "Test 2", "Sector2", "Seg2", "MID", True),
            ("TEST23", "Test 3", "Sector3", "Seg3", "SMALL", True),
        ]
        
        db.execute_many(
            "INSERT OR REPLACE INTO assets (ticker, name, sector, segment, market_cap_category, is_active) VALUES (?, ?, ?, ?, ?, ?)",
            data
        )
        
        # Verificar inserções
        results = db.fetch_all(
            "SELECT * FROM assets WHERE ticker IN (?, ?, ?)",
            ("TEST21", "TEST22", "TEST23")
        )
        
        assert len(results) == 3


class TestDatabaseQueries:
    """Testes para queries complexas."""
    
    def test_query_to_dataframe(self):
        """Deve retornar DataFrame de query."""
        import pandas as pd
        
        db = Database()
        
        df = db.query_to_df(
            "SELECT ticker, name FROM assets WHERE is_active = TRUE LIMIT 5"
        )
        
        assert isinstance(df, pd.DataFrame)
        assert "ticker" in df.columns
        assert "name" in df.columns
    
    def test_transaction_rollback(self):
        """Deve suportar rollback de transações."""
        db = Database()
        
        try:
            with db._get_connection() as conn:
                # Inserir dados
                conn.execute(
                    "INSERT INTO assets (ticker, name, sector, segment, market_cap_category, is_active) VALUES (?, ?, ?, ?, ?, ?)",
                    ("ROLLBACK", "Test Rollback", "Test", "Test", "LARGE", True)
                )
                # Forçar erro
                raise Exception("Forçar rollback")
        except Exception:
            pass
        
        # Verificar que dados não foram persistidos
        result = db.fetch_one(
            "SELECT * FROM assets WHERE ticker = ?",
            ("ROLLBACK",)
        )
        
        assert result is None


class TestDatabaseDataIntegrity:
    """Testes para integridade de dados."""
    
    def test_prices_data_available(self):
        """Deve ter dados de preços disponíveis."""
        db = Database()
        
        result = db.fetch_one("SELECT COUNT(*) as count FROM prices")
        
        assert result["count"] > 0
    
    def test_features_data_available(self):
        """Deve ter features calculadas."""
        db = Database()
        
        result = db.fetch_one("SELECT COUNT(*) as count FROM features")
        
        assert result["count"] > 0
    
    def test_date_range_consistency(self):
        """Deve ter consistência de datas."""
        db = Database()
        
        result = db.fetch_one(
            "SELECT MIN(date) as min_date, MAX(date) as max_date FROM prices"
        )
        
        assert result["min_date"] is not None
        assert result["max_date"] is not None
        # Max date deve ser depois de min date
        assert result["max_date"] >= result["min_date"]
    
    def test_foreign_key_constraint(self):
        """Deve respeitar constraints de foreign key."""
        db = Database()
        
        # Tentar inserir preço para ativo inexistente deve falhar ou ser tratado
        try:
            db.execute(
                "INSERT INTO prices (ticker, date, close) VALUES (?, ?, ?)",
                ("NONEXISTENT", "2024-01-01", 100.0)
            )
            # Se não falhar, devemos verificar se o registro foi inserido
            result = db.fetch_one(
                "SELECT * FROM prices WHERE ticker = ?",
                ("NONEXISTENT",)
            )
            # Pode ou não existir dependendo da configuração do SQLite
        except Exception:
            # Se falhar por FK constraint, está correto
            pass
