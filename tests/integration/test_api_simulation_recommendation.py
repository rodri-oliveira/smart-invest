from __future__ import annotations

import tempfile
from datetime import date, timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from aim.data_layer.database import Database
from aim.security.audit import ensure_audit_schema
from api.routers import auth, recommendation, simulation


def _write(db: Database, query: str, parameters: tuple = ()) -> None:
    with db.transaction() as conn:
        conn.execute(query, parameters)


def _setup_base_schema(db: Database) -> None:
    _write(
        db,
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            email TEXT,
            tenant_id INTEGER
        )
        """,
    )
    _write(
        db,
        """
        CREATE TABLE IF NOT EXISTS assets (
            ticker TEXT PRIMARY KEY,
            name TEXT,
            sector TEXT,
            is_active INTEGER DEFAULT 1
        )
        """,
    )
    _write(
        db,
        """
        CREATE TABLE IF NOT EXISTS prices (
            ticker TEXT NOT NULL,
            date DATE NOT NULL,
            close REAL,
            volume REAL,
            PRIMARY KEY (ticker, date)
        )
        """,
    )
    _write(
        db,
        """
        CREATE TABLE IF NOT EXISTS signals (
            date DATE NOT NULL,
            ticker TEXT NOT NULL,
            score_final REAL,
            score_momentum REAL,
            score_quality REAL,
            score_value REAL,
            PRIMARY KEY (date, ticker)
        )
        """,
    )


def _seed_market_data(db: Database) -> None:
    _write(db, "INSERT OR REPLACE INTO users (id, email, tenant_id) VALUES (1, 'user@test.com', 1)")
    _write(db, "INSERT OR REPLACE INTO users (id, email, tenant_id) VALUES (2, 'other@test.com', 2)")

    _write(
        db,
        "INSERT OR REPLACE INTO assets (ticker, name, sector, is_active) VALUES (?, ?, ?, 1)",
        ("WEGE3", "WEG ON", "Industria"),
    )
    _write(
        db,
        "INSERT OR REPLACE INTO assets (ticker, name, sector, is_active) VALUES (?, ?, ?, 1)",
        ("SANB11", "Santander BR Unit", "Financeiro"),
    )

    today = date.today()
    for i, p in enumerate([80.0, 82.0, 81.0, 83.0, 84.0]):
        d = today - timedelta(days=i)
        _write(
            db,
            "INSERT OR REPLACE INTO prices (ticker, date, close, volume) VALUES (?, ?, ?, ?)",
            ("WEGE3", d.isoformat(), p, 1000000 + i),
        )

    for i, p in enumerate([36.0, 35.8, 35.6, 35.9, 36.2, 36.4, 36.3, 36.1]):
        d = today - timedelta(days=i)
        _write(
            db,
            "INSERT OR REPLACE INTO prices (ticker, date, close, volume) VALUES (?, ?, ?, ?)",
            ("SANB11", d.isoformat(), p, 1500000 + i),
        )

    _write(
        db,
        "INSERT OR REPLACE INTO signals (date, ticker, score_final, score_momentum, score_quality, score_value) VALUES (?, ?, ?, ?, ?, ?)",
        (today.isoformat(), "WEGE3", -0.2, 0.1, 0.0, -0.1),
    )


def _build_client(db: Database) -> TestClient:
    app = FastAPI()
    app.include_router(auth.router, prefix="/auth")
    app.include_router(simulation.router, prefix="/simulation")
    app.include_router(recommendation.router, prefix="/recommendation")

    def _simulation_db_override() -> Database:
        simulation._ensure_simulation_schema(db)
        return db

    app.dependency_overrides[simulation.get_db] = _simulation_db_override
    app.dependency_overrides[simulation.get_current_user] = lambda: {
        "user_id": 1,
        "email": "user@test.com",
        "name": "Test User",
        "tenant_id": 1,
    }
    app.dependency_overrides[auth.get_db] = lambda: (ensure_audit_schema(db) or db)
    app.dependency_overrides[auth.get_current_user] = lambda: {
        "user_id": 1,
        "email": "user@test.com",
        "name": "Test User",
        "tenant_id": 1,
    }
    app.dependency_overrides[recommendation.get_db] = lambda: db

    return TestClient(app)


def test_simulation_order_history_and_daily_plan_regression() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        simulation._SCHEMA_READY = False
        db_path = Path(tmp_dir) / "test.db"
        db = Database(db_path=db_path)
        _setup_base_schema(db)
        _seed_market_data(db)

        client = _build_client(db)

        create_resp = client.post(
            "/simulation/order",
            json={
                "ticker": "WEGE3",
                "order_type": "BUY",
                "quantity": 2,
                "price": 80.98,
                "is_real": False,
            },
        )
        assert create_resp.status_code == 200

        positions_resp = client.get("/simulation/positions", params={"is_real": False})
        assert positions_resp.status_code == 200
        positions = positions_resp.json()
        assert len(positions) == 1
        assert positions[0]["ticker"] == "WEGE3"
        assert positions[0]["quantity"] == 2

        orders_resp = client.get("/simulation/orders", params={"is_real": False})
        assert orders_resp.status_code == 200
        orders = orders_resp.json()
        assert len(orders) == 1
        assert isinstance(orders[0]["order_date"], str)
        assert orders[0]["order_date"]

        daily_plan_resp = client.get("/simulation/daily-plan", params={"is_real": False})
        assert daily_plan_resp.status_code == 200
        daily_plan = daily_plan_resp.json()
        assert daily_plan["profile"] == "leigo"
        assert len(daily_plan["guidance"]) == 1
        assert daily_plan["guidance"][0]["ticker"] == "WEGE3"


def test_simulation_positions_are_isolated_by_tenant() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        simulation._SCHEMA_READY = False
        db_path = Path(tmp_dir) / "test.db"
        db = Database(db_path=db_path)
        _setup_base_schema(db)
        _seed_market_data(db)
        simulation._ensure_simulation_schema(db)

        _write(
            db,
            """
            INSERT INTO simulated_positions (user_id, tenant_id, ticker, quantity, avg_price, total_cost)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (1, 1, "WEGE3", 3, 80.0, 240.0),
        )
        _write(
            db,
            """
            INSERT INTO simulated_positions (user_id, tenant_id, ticker, quantity, avg_price, total_cost)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (1, 2, "SANB11", 5, 36.0, 180.0),
        )

        client = _build_client(db)

        resp = client.get("/simulation/positions", params={"is_real": False})
        assert resp.status_code == 200
        tickers = {row["ticker"] for row in resp.json()}

        assert "WEGE3" in tickers
        assert "SANB11" not in tickers


def test_asset_insight_matches_company_name_without_hardcoded_ticker() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        simulation._SCHEMA_READY = False
        db_path = Path(tmp_dir) / "test.db"
        db = Database(db_path=db_path)
        _setup_base_schema(db)
        _seed_market_data(db)

        client = _build_client(db)

        resp = client.post(
            "/recommendation/asset-insight",
            json={"prompt": "me mostra a situacao do santander"},
        )

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["mode"] == "asset_query"
        assert payload["ticker"] == "SANB11"
        assert "didactic_summary" in payload


def test_asset_insight_not_found_returns_didactic_error_with_suggestions() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        simulation._SCHEMA_READY = False
        db_path = Path(tmp_dir) / "test.db"
        db = Database(db_path=db_path)
        _setup_base_schema(db)
        _seed_market_data(db)

        client = _build_client(db)

        resp = client.post(
            "/recommendation/asset-insight",
            json={"prompt": "fale da multilaser"},
        )

        assert resp.status_code == 404
        detail = resp.json()["detail"]
        assert detail["code"] == "ASSET_NOT_FOUND"
        assert "didactic_message" in detail
        assert isinstance(detail["suggestions"], list)


def test_asset_request_creates_and_deduplicates_recent_prompt() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        simulation._SCHEMA_READY = False
        db_path = Path(tmp_dir) / "test.db"
        db = Database(db_path=db_path)
        _setup_base_schema(db)
        _seed_market_data(db)

        client = _build_client(db)

        first = client.post("/recommendation/asset-request", json={"prompt": "fale da multilaser"})
        assert first.status_code == 200
        payload_first = first.json()
        assert payload_first["status"] == "created"
        assert payload_first["request_id"] is not None

        second = client.post("/recommendation/asset-request", json={"prompt": "Fale da Multilaser"})
        assert second.status_code == 200
        payload_second = second.json()
        assert payload_second["status"] == "already_requested"
        assert payload_second["request_id"] == payload_first["request_id"]


def test_end_to_end_asset_query_then_buy_and_alert() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        simulation._SCHEMA_READY = False
        db_path = Path(tmp_dir) / "test.db"
        db = Database(db_path=db_path)
        _setup_base_schema(db)
        _seed_market_data(db)

        client = _build_client(db)

        insight_resp = client.post(
            "/recommendation/asset-insight",
            json={"prompt": "como esta WEGE3 hoje?"},
        )
        assert insight_resp.status_code == 200
        ticker = insight_resp.json()["ticker"]
        assert ticker == "WEGE3"

        order_resp = client.post(
            "/simulation/order",
            json={
                "ticker": ticker,
                "order_type": "BUY",
                "quantity": 1,
                "price": 80.98,
                "is_real": False,
            },
        )
        assert order_resp.status_code == 200

        alerts_resp = client.get("/simulation/alerts")
        assert alerts_resp.status_code == 200
        alerts = alerts_resp.json()
        # WEGE3 tem score_final negativo no seed, então deve haver alerta de rebalance.
        assert any(a["ticker"] == "WEGE3" and a["type"] == "REBALANCE" for a in alerts)


def test_daily_plan_empty_portfolio_returns_didactic_message() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        simulation._SCHEMA_READY = False
        db_path = Path(tmp_dir) / "test.db"
        db = Database(db_path=db_path)
        _setup_base_schema(db)
        _seed_market_data(db)

        client = _build_client(db)

        resp = client.get("/simulation/daily-plan", params={"is_real": False})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["guidance"] == []
        assert "ainda nao tem ativos" in payload["summary"].lower()


def test_free_plan_blocks_real_portfolio_access() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        simulation._SCHEMA_READY = False
        db_path = Path(tmp_dir) / "test.db"
        db = Database(db_path=db_path)
        _setup_base_schema(db)
        _seed_market_data(db)

        client = _build_client(db)

        resp_positions = client.get("/simulation/positions", params={"is_real": True})
        assert resp_positions.status_code == 403
        assert "plano atual" in resp_positions.json().get("detail", "").lower()

        resp_order = client.post(
            "/simulation/order",
            json={
                "ticker": "WEGE3",
                "order_type": "BUY",
                "quantity": 1,
                "price": 80.98,
                "is_real": True,
            },
        )
        assert resp_order.status_code == 403


def test_free_plan_enforces_max_simulated_positions_limit() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        simulation._SCHEMA_READY = False
        db_path = Path(tmp_dir) / "test.db"
        db = Database(db_path=db_path)
        _setup_base_schema(db)
        _seed_market_data(db)
        simulation._ensure_simulation_schema(db)

        # Preencher 10 posicoes (limite default do plano free).
        for i in range(10):
            ticker = f"TST{i:02d}"
            _write(db, "INSERT OR REPLACE INTO assets (ticker, name, sector, is_active) VALUES (?, ?, ?, 1)", (ticker, ticker, "Teste"))
            _write(
                db,
                """
                INSERT INTO simulated_positions (user_id, tenant_id, ticker, quantity, avg_price, total_cost)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (1, 1, ticker, 1, 10.0, 10.0),
            )

        client = _build_client(db)

        # Novo ticker para tentar ultrapassar o limite.
        _write(
            db,
            "INSERT OR REPLACE INTO assets (ticker, name, sector, is_active) VALUES (?, ?, ?, 1)",
            ("EXTR1", "Extra 1", "Teste"),
        )
        _write(
            db,
            "INSERT OR REPLACE INTO prices (ticker, date, close, volume) VALUES (?, ?, ?, ?)",
            ("EXTR1", date.today().isoformat(), 12.34, 1000),
        )

        resp = client.post(
            "/simulation/order",
            json={
                "ticker": "EXTR1",
                "order_type": "BUY",
                "quantity": 1,
                "is_real": False,
            },
        )

        assert resp.status_code == 403
        assert "limite do plano" in resp.json().get("detail", "").lower()


def test_prompt_route_out_of_scope_returns_safe_response() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        simulation._SCHEMA_READY = False
        db_path = Path(tmp_dir) / "test.db"
        db = Database(db_path=db_path)
        _setup_base_schema(db)
        _seed_market_data(db)
        client = _build_client(db)

        resp = client.post("/recommendation/route", json={"prompt": "me conta uma piada de futebol"})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["route"] == "out_of_scope"
        assert payload["in_scope"] is False
        assert "investimentos" in payload["safe_response"].lower()


def test_prompt_route_asset_query_detected() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        simulation._SCHEMA_READY = False
        db_path = Path(tmp_dir) / "test.db"
        db = Database(db_path=db_path)
        _setup_base_schema(db)
        _seed_market_data(db)
        client = _build_client(db)

        resp = client.post("/recommendation/route", json={"prompt": "como esta WEGE3 hoje?"})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["route"] == "asset_query"
        assert payload["in_scope"] is True


def test_prompt_route_asset_query_detected_with_typo_term() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        simulation._SCHEMA_READY = False
        db_path = Path(tmp_dir) / "test.db"
        db = Database(db_path=db_path)
        _setup_base_schema(db)
        _seed_market_data(db)
        client = _build_client(db)

        resp = client.post("/recommendation/route", json={"prompt": "como esta o santande hoje?"})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["route"] == "asset_query"
        assert payload["in_scope"] is True


def test_daily_plan_supports_learning_profile_variations() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        simulation._SCHEMA_READY = False
        db_path = Path(tmp_dir) / "test.db"
        db = Database(db_path=db_path)
        _setup_base_schema(db)
        _seed_market_data(db)

        client = _build_client(db)

        order_resp = client.post(
            "/simulation/order",
            json={
                "ticker": "WEGE3",
                "order_type": "BUY",
                "quantity": 1,
                "price": 80.98,
                "is_real": False,
            },
        )
        assert order_resp.status_code == 200

        teen_resp = client.get("/simulation/daily-plan", params={"is_real": False, "profile": "adolescente"})
        assert teen_resp.status_code == 200
        teen_payload = teen_resp.json()
        assert teen_payload["profile"] == "adolescente"
        assert "impulso" in teen_payload["summary"].lower() or "disciplina" in teen_payload["summary"].lower()

        senior_resp = client.get("/simulation/daily-plan", params={"is_real": False, "profile": "idoso"})
        assert senior_resp.status_code == 200
        senior_payload = senior_resp.json()
        assert senior_payload["profile"] == "idoso"
        assert "cautela" in senior_payload["summary"].lower() or "tranquilidade" in senior_payload["next_step"].lower()


def test_audit_recent_returns_events_for_tenant() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        simulation._SCHEMA_READY = False
        db_path = Path(tmp_dir) / "test.db"
        db = Database(db_path=db_path)
        _setup_base_schema(db)
        _seed_market_data(db)
        client = _build_client(db)

        order_resp = client.post(
            "/simulation/order",
            json={
                "ticker": "WEGE3",
                "order_type": "BUY",
                "quantity": 1,
                "price": 80.98,
                "is_real": False,
            },
        )
        assert order_resp.status_code == 200

        audit_resp = client.get("/auth/audit/recent", params={"limit": 20})
        assert audit_resp.status_code == 200
        payload = audit_resp.json()
        events = payload["items"]
        assert isinstance(events, list)
        assert payload["total"] >= len(events)
        assert payload["offset"] == 0
        assert any(event["event_type"] == "simulation.order_success" for event in events)


def test_audit_recent_supports_severity_and_event_type_filters() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        simulation._SCHEMA_READY = False
        db_path = Path(tmp_dir) / "test.db"
        db = Database(db_path=db_path)
        _setup_base_schema(db)
        _seed_market_data(db)
        client = _build_client(db)

        # Gera evento WARN (bloqueio por plano para carteira real no free).
        denied_resp = client.post(
            "/simulation/order",
            json={
                "ticker": "WEGE3",
                "order_type": "BUY",
                "quantity": 1,
                "price": 80.98,
                "is_real": True,
            },
        )
        assert denied_resp.status_code == 403

        warn_resp = client.get(
            "/auth/audit/recent",
            params={"limit": 20, "severity": "WARN", "event_type": "simulation.order_denied_plan", "days": 1},
        )
        assert warn_resp.status_code == 200
        payload = warn_resp.json()
        events = payload["items"]
        assert len(events) >= 1
        assert all(event["severity"] == "WARN" for event in events)
        assert all(event["event_type"] == "simulation.order_denied_plan" for event in events)

def test_prompt_route_greeting_returns_helpful_out_of_scope() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        simulation._SCHEMA_READY = False
        db_path = Path(tmp_dir) / "test.db"
        db = Database(db_path=db_path)
        _setup_base_schema(db)
        _seed_market_data(db)
        client = _build_client(db)

        resp = client.post("/recommendation/route", json={"prompt": "oi, tudo bem?"})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["route"] == "out_of_scope"
        assert payload["in_scope"] is False
        assert "exemplos" in payload["safe_response"].lower() or "posso te guiar" in payload["safe_response"].lower()


def test_prompt_route_non_finance_long_text_is_not_portfolio() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        simulation._SCHEMA_READY = False
        db_path = Path(tmp_dir) / "test.db"
        db = Database(db_path=db_path)
        _setup_base_schema(db)
        _seed_market_data(db)
        client = _build_client(db)

        resp = client.post("/recommendation/route", json={"prompt": "quero uma receita de bolo de chocolate para hoje"})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["route"] == "out_of_scope"
        assert payload["in_scope"] is False
        assert "investimentos" in payload["safe_response"].lower() or "simulador" in payload["safe_response"].lower()


def test_prompt_route_ambiguous_prompt_returns_clarification() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        simulation._SCHEMA_READY = False
        db_path = Path(tmp_dir) / "test.db"
        db = Database(db_path=db_path)
        _setup_base_schema(db)
        _seed_market_data(db)
        client = _build_client(db)

        resp = client.post(
            "/recommendation/route",
            json={"prompt": "quero saber do santander e montar carteira com risco moderado"},
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["route"] == "out_of_scope"
        assert payload["in_scope"] is False
        assert "duas intencoes" in payload["safe_response"].lower()
        assert isinstance(payload.get("disambiguation_options"), list)
        ids = {opt["id"] for opt in payload["disambiguation_options"]}
        assert "asset_query" in ids
        assert "portfolio" in ids
