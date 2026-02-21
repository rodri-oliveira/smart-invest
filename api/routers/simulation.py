from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from aim.data_layer.database import Database
from aim.auth import get_auth_manager
from aim.security.audit import ensure_audit_schema, log_audit_event
from api.routers.auth import get_current_user

router = APIRouter(tags=["Carteira e Simulacao"])

_SCHEMA_READY = False


class OrderRequest(BaseModel):
    ticker: str
    order_type: str  # BUY, SELL
    quantity: int
    price: Optional[float] = None
    is_real: bool = False  # Define se e Simulacao ou Carteira Real


class PositionResponse(BaseModel):
    ticker: str
    quantity: int
    avg_price: float
    total_cost: float
    current_price: Optional[float] = None
    profit_loss: Optional[float] = None
    profit_loss_pct: Optional[float] = None


class OrderHistoryResponse(BaseModel):
    order_id: int
    ticker: str
    order_type: str
    quantity: int
    price_at_order: float
    order_date: str
    is_real: bool


class DailyGuidanceItem(BaseModel):
    ticker: str
    action: str
    reason: str
    risk_level: str
    signal_score: Optional[float] = None
    profit_loss_pct: Optional[float] = None


class DailyPlanResponse(BaseModel):
    generated_at: str
    is_real: bool
    profile: str
    summary: str
    next_step: str
    guidance: List[DailyGuidanceItem]


def _normalize_learning_profile(profile: Optional[str]) -> str:
    normalized = (profile or "leigo").strip().lower()
    aliases = {
        "iniciante": "leigo",
        "beginner": "leigo",
        "teen": "adolescente",
        "senior": "idoso",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in {"leigo", "adolescente", "idoso"}:
        return "leigo"
    return normalized


def _profile_reason(profile: str, key: str) -> str:
    messages = {
        "sem_preco": {
            "leigo": "Sem preco recente. Evite decidir ate atualizar os dados.",
            "adolescente": "Ainda sem dado novo de preco. Melhor esperar atualizar antes de agir.",
            "idoso": "Sem preco atualizado no momento. Recomendado aguardar novos dados para decidir com calma.",
        },
        "reduzir_risco": {
            "leigo": "Queda relevante ou sinal fraco. Para leigo: nao aumente a posicao agora.",
            "adolescente": "Sinal fraco ou queda forte. Evite empolgar e nao aumente a posicao hoje.",
            "idoso": "Houve enfraquecimento no ativo. Priorize preservacao de capital e evite aumentar exposicao agora.",
        },
        "realizar_parcial": {
            "leigo": "Lucro alto atingido. Pode vender uma parte para proteger ganho.",
            "adolescente": "Bateu lucro bom. Realizar parte ajuda a garantir o resultado.",
            "idoso": "Lucro relevante alcançado. Realizar parcialmente pode proteger o patrimonio.",
        },
        "manter": {
            "leigo": "Sinal quantitativo favoravel. Mantenha com disciplina e limite de risco.",
            "adolescente": "Cenario favoravel no momento. Mantenha disciplina e nao exagere no tamanho da aposta.",
            "idoso": "Sinal ainda positivo no modelo. Mantenha a posicao com acompanhamento e prudencia.",
        },
        "acompanhar": {
            "leigo": "Cenario neutro. Aguarde confirmacao antes de comprar mais.",
            "adolescente": "Mercado sem direcao clara. Melhor observar antes de aumentar a posicao.",
            "idoso": "Momento indefinido. Recomendado acompanhar e evitar novas entradas precipitadas.",
        },
        "summary_risk": {
            "leigo": "Plano do dia para {n} ativos: {r} pedem mais atencao de risco.",
            "adolescente": "Hoje voce acompanha {n} ativos: {r} exigem mais cuidado para evitar decisoes por impulso.",
            "idoso": "Plano diario para {n} ativos: {r} demandam maior cautela na gestao de risco.",
        },
        "summary_stable": {
            "leigo": "Plano do dia para {n} ativos: carteira em condicao estavel.",
            "adolescente": "Hoje a carteira com {n} ativos esta mais estavel. Siga com disciplina.",
            "idoso": "Plano diario para {n} ativos: carteira em condicao estavel no momento.",
        },
        "next_step_risk": {
            "leigo": "Priorize ativos com alerta de reduzir risco e revise tamanho das posicoes.",
            "adolescente": "Comece pelos ativos em alerta. Ajuste tamanho das posicoes antes de pensar em novas compras.",
            "idoso": "Priorize os ativos com alerta e reavalie o tamanho das posicoes com foco em seguranca.",
        },
        "next_step_stable": {
            "leigo": "Siga acompanhando e reavalie no proximo pregao.",
            "adolescente": "Continue acompanhando e reavalie no proximo pregao sem pressa.",
            "idoso": "Mantenha o acompanhamento e reavalie no proximo pregao com tranquilidade.",
        },
        "empty_summary": {
            "leigo": "Voce ainda nao tem ativos nesta carteira.",
            "adolescente": "Sua carteira ainda esta vazia. Vamos comecar pequeno para aprender com seguranca.",
            "idoso": "Ainda nao ha ativos nesta carteira. Podemos iniciar gradualmente e com baixo risco.",
        },
        "empty_next_step": {
            "leigo": "Escolha um ativo, compre pouco e acompanhe por alguns dias antes de aumentar.",
            "adolescente": "Escolha 1 ativo, monte uma posicao pequena e acompanhe alguns dias antes de aumentar.",
            "idoso": "Comece com 1 ativo e exposicao pequena. Acompanhe por alguns dias antes de ampliar a posicao.",
        },
    }
    return messages.get(key, {}).get(profile, messages.get(key, {}).get("leigo", ""))


def _table_has_column(db: Database, table_name: str, column_name: str) -> bool:
    cols = db.fetch_all(f"PRAGMA table_info({table_name})")
    return any(col["name"] == column_name for col in cols)


def _ensure_simulation_schema(db: Database) -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return

    # Cria tabelas caso ainda nao existam.
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS simulated_orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tenant_id INTEGER DEFAULT 1,
            ticker VARCHAR(10) NOT NULL,
            order_type VARCHAR(10) NOT NULL,
            quantity INTEGER NOT NULL,
            price_at_order DECIMAL(12,4) NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS real_orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tenant_id INTEGER DEFAULT 1,
            ticker VARCHAR(10) NOT NULL,
            order_type VARCHAR(10) NOT NULL,
            quantity INTEGER NOT NULL,
            price_at_order DECIMAL(12,4) NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS simulated_positions (
            position_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tenant_id INTEGER DEFAULT 1,
            ticker VARCHAR(10) NOT NULL,
            quantity INTEGER NOT NULL,
            avg_price DECIMAL(12,4) NOT NULL,
            total_cost DECIMAL(15,4) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, tenant_id, ticker),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS real_positions (
            position_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tenant_id INTEGER DEFAULT 1,
            ticker VARCHAR(10) NOT NULL,
            quantity INTEGER NOT NULL,
            avg_price DECIMAL(12,4) NOT NULL,
            total_cost DECIMAL(15,4) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, tenant_id, ticker),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )

    # Migra tabelas legadas para tenant_id sem quebrar ambientes antigos.
    for table in ["simulated_orders", "real_orders", "simulated_positions", "real_positions"]:
        if not _table_has_column(db, table, "tenant_id"):
            db.execute(f"ALTER TABLE {table} ADD COLUMN tenant_id INTEGER DEFAULT 1")

        db.execute(
            f"""
            UPDATE {table}
            SET tenant_id = COALESCE(
                (SELECT tenant_id FROM users WHERE users.id = {table}.user_id),
                1
            )
            WHERE tenant_id IS NULL
            """
        )

    # Indices para consultas por usuario + tenant.
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_sim_orders_tenant_user_date ON simulated_orders(tenant_id, user_id, order_date DESC)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_real_orders_tenant_user_date ON real_orders(tenant_id, user_id, order_date DESC)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_sim_positions_tenant_user_ticker ON simulated_positions(tenant_id, user_id, ticker)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_real_positions_tenant_user_ticker ON real_positions(tenant_id, user_id, ticker)"
    )

    _SCHEMA_READY = True


def get_db():
    db = Database()
    _ensure_simulation_schema(db)
    ensure_audit_schema(db)
    return db


def _get_tenant_capabilities(db: Database, tenant_id: int) -> dict:
    auth_manager = get_auth_manager(db)
    return auth_manager.get_tenant_capabilities(tenant_id)


@router.post("/order")
async def create_order(
    order: OrderRequest,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Cria uma ordem de compra ou venda (simulada ou real)."""
    user_id = current_user["user_id"]
    tenant_id = current_user.get("tenant_id", 1)
    table_orders = "real_orders" if order.is_real else "simulated_orders"
    table_positions = "real_positions" if order.is_real else "simulated_positions"
    capabilities = _get_tenant_capabilities(db, tenant_id)
    features = capabilities.get("features", {})
    limits = capabilities.get("limits", {})

    if order.is_real and not features.get("allow_real_portfolio", False):
        log_audit_event(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            event_type="simulation.order_denied_plan",
            severity="WARN",
            message="Tentativa de ordem em carteira real bloqueada pelo plano",
            metadata={"ticker": order.ticker, "is_real": order.is_real},
        )
        raise HTTPException(
            status_code=403,
            detail="Seu plano atual nao permite operacoes na carteira real.",
        )

    order_type = order.order_type.upper().strip()
    if order_type not in {"BUY", "SELL"}:
        raise HTTPException(status_code=400, detail="order_type deve ser BUY ou SELL")
    if order.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantidade deve ser maior que zero")

    price = order.price
    if price is None:
        price_data = db.fetch_one(
            "SELECT close FROM prices WHERE ticker = ? ORDER BY date DESC LIMIT 1",
            (order.ticker,),
        )
        if not price_data:
            raise HTTPException(status_code=400, detail=f"Preco nao encontrado para {order.ticker}")
        price = price_data["close"]

    try:
        with db.transaction() as conn:
            # 1. Registrar a ordem
            conn.execute(
                f"""
                INSERT INTO {table_orders} (user_id, tenant_id, ticker, order_type, quantity, price_at_order)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, tenant_id, order.ticker, order_type, order.quantity, price),
            )

            # 2. Atualizar posicao
            pos = db.fetch_one(
                f"SELECT * FROM {table_positions} WHERE user_id = ? AND tenant_id = ? AND ticker = ?",
                (user_id, tenant_id, order.ticker),
            )

            if order_type == "BUY":
                # Fallback para bases legadas onde tenant_id pode estar ausente em posições antigas.
                if not pos:
                    legacy_pos = db.fetch_one(
                        f"SELECT * FROM {table_positions} WHERE user_id = ? AND ticker = ? LIMIT 1",
                        (user_id, order.ticker),
                    )
                    if legacy_pos:
                        legacy_tenant = legacy_pos.get("tenant_id")
                        if legacy_tenant is None:
                            conn.execute(
                                f"""
                                UPDATE {table_positions}
                                SET tenant_id = ?
                                WHERE user_id = ? AND ticker = ?
                                """,
                                (tenant_id, user_id, order.ticker),
                            )
                        pos = legacy_pos

                if pos:
                    new_qty = pos["quantity"] + order.quantity
                    new_cost = pos["total_cost"] + (order.quantity * price)
                    new_avg = new_cost / new_qty
                    conn.execute(
                        f"""
                        UPDATE {table_positions}
                        SET tenant_id = COALESCE(tenant_id, ?), quantity = ?, avg_price = ?, total_cost = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ? AND ticker = ?
                        """,
                        (tenant_id, new_qty, new_avg, new_cost, user_id, order.ticker),
                    )
                else:
                    if not order.is_real:
                        current_positions_count = db.fetch_one(
                            """
                            SELECT COUNT(*) AS count
                            FROM simulated_positions
                            WHERE user_id = ? AND tenant_id = ?
                            """,
                            (user_id, tenant_id),
                        )
                        max_positions = int(limits.get("max_simulated_positions", 10))
                        if int(current_positions_count.get("count") or 0) >= max_positions:
                            log_audit_event(
                                db,
                                tenant_id=tenant_id,
                                user_id=user_id,
                                event_type="simulation.order_denied_limit",
                                severity="WARN",
                                message="Tentativa de exceder limite de posicoes simuladas",
                                metadata={"max_positions": max_positions, "ticker": order.ticker},
                            )
                            raise HTTPException(
                                status_code=403,
                                detail=(
                                    f"Limite do plano atingido: maximo de {max_positions} ativos "
                                    "simulados em carteira."
                                ),
                            )
                    try:
                        conn.execute(
                            f"""
                            INSERT INTO {table_positions} (user_id, tenant_id, ticker, quantity, avg_price, total_cost)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (user_id, tenant_id, order.ticker, order.quantity, price, order.quantity * price),
                        )
                    except Exception as insert_error:
                        # Recuperação defensiva para constraint legada em banco local.
                        if "UNIQUE constraint failed" not in str(insert_error):
                            raise
                        existing_pos = db.fetch_one(
                            f"SELECT * FROM {table_positions} WHERE user_id = ? AND ticker = ? LIMIT 1",
                            (user_id, order.ticker),
                        )
                        if not existing_pos:
                            raise
                        new_qty = existing_pos["quantity"] + order.quantity
                        new_cost = existing_pos["total_cost"] + (order.quantity * price)
                        new_avg = new_cost / new_qty
                        conn.execute(
                            f"""
                            UPDATE {table_positions}
                            SET tenant_id = COALESCE(tenant_id, ?), quantity = ?, avg_price = ?, total_cost = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE user_id = ? AND ticker = ?
                            """,
                            (tenant_id, new_qty, new_avg, new_cost, user_id, order.ticker),
                        )
            elif order_type == "SELL":
                if not pos or pos["quantity"] < order.quantity:
                    raise HTTPException(status_code=400, detail="Quantidade insuficiente para venda")

                new_qty = pos["quantity"] - order.quantity
                if new_qty == 0:
                    conn.execute(
                        f"DELETE FROM {table_positions} WHERE user_id = ? AND tenant_id = ? AND ticker = ?",
                        (user_id, tenant_id, order.ticker),
                    )
                else:
                    new_cost = new_qty * pos["avg_price"]
                    conn.execute(
                        f"""
                        UPDATE {table_positions}
                        SET quantity = ?, total_cost = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ? AND tenant_id = ? AND ticker = ?
                        """,
                        (new_qty, new_cost, user_id, tenant_id, order.ticker),
                    )

        carteira = "Real" if order.is_real else "Simulada"
        log_audit_event(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            event_type="simulation.order_success",
            severity="INFO",
            message=f"Ordem {order_type} executada para {order.ticker} ({carteira})",
            metadata={"ticker": order.ticker, "order_type": order_type, "quantity": order.quantity, "is_real": order.is_real},
        )
        return {
            "status": "success",
            "message": f"Ordem de {order_type} ({carteira}) para {order.ticker} executada",
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        log_audit_event(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            event_type="simulation.order_failed",
            severity="ERROR",
            message=f"Falha ao executar ordem: {str(e)}",
            metadata={"ticker": order.ticker, "order_type": order_type, "is_real": order.is_real},
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions", response_model=List[PositionResponse])
async def get_positions(
    is_real: bool = Query(False),
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Retorna as posicoes atuais (reais ou simuladas) com lucro/prejuizo."""
    user_id = current_user["user_id"]
    tenant_id = current_user.get("tenant_id", 1)
    table_positions = "real_positions" if is_real else "simulated_positions"
    capabilities = _get_tenant_capabilities(db, tenant_id)
    features = capabilities.get("features", {})

    if is_real and not features.get("allow_real_portfolio", False):
        raise HTTPException(
            status_code=403,
            detail="Seu plano atual nao permite visualizar carteira real.",
        )

    positions = db.fetch_all(
        f"SELECT * FROM {table_positions} WHERE user_id = ? AND tenant_id = ?",
        (user_id, tenant_id),
    ) or []

    result = []
    for pos in positions:
        price_data = db.fetch_one(
            "SELECT close FROM prices WHERE ticker = ? ORDER BY date DESC LIMIT 1",
            (pos["ticker"],),
        )

        current_price = price_data["close"] if price_data else pos["avg_price"]
        total_value = pos["quantity"] * current_price
        pl = total_value - pos["total_cost"]
        pl_pct = (pl / pos["total_cost"] * 100) if pos["total_cost"] > 0 else 0

        result.append(
            PositionResponse(
                ticker=pos["ticker"],
                quantity=pos["quantity"],
                avg_price=pos["avg_price"],
                total_cost=pos["total_cost"],
                current_price=current_price,
                profit_loss=pl,
                profit_loss_pct=pl_pct,
            )
        )
    return result


@router.get("/alerts", response_model=List[dict])
async def get_simulation_alerts(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Gera alertas operacionais para as posicoes do usuario (simuladas e reais)."""
    user_id = current_user["user_id"]
    tenant_id = current_user.get("tenant_id", 1)
    capabilities = _get_tenant_capabilities(db, tenant_id)
    features = capabilities.get("features", {})

    if not features.get("allow_history", True):
        raise HTTPException(
            status_code=403,
            detail="Seu plano atual nao permite acessar historico operacional.",
        )

    sim_positions = db.fetch_all(
        "SELECT * FROM simulated_positions WHERE user_id = ? AND tenant_id = ?",
        (user_id, tenant_id),
    ) or []
    real_positions = db.fetch_all(
        "SELECT * FROM real_positions WHERE user_id = ? AND tenant_id = ?",
        (user_id, tenant_id),
    ) or []

    raw_alerts = []

    for pos_list, is_real in [(sim_positions, False), (real_positions, True)]:
        for pos in pos_list:
            ticker = pos["ticker"]

            signal = db.fetch_one(
                "SELECT score_final FROM signals WHERE ticker = ? ORDER BY date DESC LIMIT 1",
                (ticker,),
            )

            price_data = db.fetch_one(
                "SELECT close FROM prices WHERE ticker = ? ORDER BY date DESC LIMIT 1",
                (ticker,),
            )

            if not signal or not price_data:
                continue

            current_price = price_data["close"]
            score = signal["score_final"]
            pl_pct = (current_price / pos["avg_price"] - 1) * 100

            if pl_pct <= -10:
                raw_alerts.append(
                    {
                        "ticker": ticker,
                        "type": "STOP_LOSS",
                        "severity": "HIGH",
                        "message": f"Ativo em queda de {pl_pct:.1f}%. Considere reduzir exposicao.",
                        "is_real": is_real,
                    }
                )

            if score < 0:
                raw_alerts.append(
                    {
                        "ticker": ticker,
                        "type": "REBALANCE",
                        "severity": "MEDIUM",
                        "message": f"Score atual ({score:.2f}) indica saida da estrategia.",
                        "is_real": is_real,
                    }
                )

            if pl_pct >= 20:
                raw_alerts.append(
                    {
                        "ticker": ticker,
                        "type": "TAKE_PROFIT",
                        "severity": "LOW",
                        "message": f"Lucro de {pl_pct:.1f}% atingido. Otimo momento para rebalancear.",
                        "is_real": is_real,
                    }
                )

    # Consolidar alertas por ativo para reduzir ruido (1 alerta principal por ticker).
    severity_rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    consolidated: dict[tuple[str, bool], dict] = {}
    for alert in raw_alerts:
        key = (alert["ticker"], bool(alert.get("is_real")))
        if key not in consolidated:
            consolidated[key] = {
                **alert,
                "reasons": [alert["message"]],
            }
            continue

        current = consolidated[key]
        current["reasons"].append(alert["message"])
        if severity_rank.get(alert["severity"], 0) > severity_rank.get(current["severity"], 0):
            current["type"] = alert["type"]
            current["severity"] = alert["severity"]
            current["message"] = alert["message"]

    results = list(consolidated.values())
    results.sort(key=lambda a: severity_rank.get(a.get("severity", "LOW"), 0), reverse=True)
    return results


@router.get("/orders", response_model=List[OrderHistoryResponse])
async def get_orders_history(
    is_real: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Retorna historico de ordens simuladas e/ou reais do usuario."""
    user_id = current_user["user_id"]
    tenant_id = current_user.get("tenant_id", 1)
    capabilities = _get_tenant_capabilities(db, tenant_id)
    features = capabilities.get("features", {})

    if is_real and not features.get("allow_real_portfolio", False):
        raise HTTPException(
            status_code=403,
            detail="Seu plano atual nao permite visualizar historico da carteira real.",
        )

    def fetch_table(table_name: str, real_flag: bool):
        rows = db.fetch_all(
            f"""
            SELECT order_id, ticker, order_type, quantity, price_at_order, order_date
            FROM {table_name}
            WHERE user_id = ? AND tenant_id = ?
            ORDER BY order_date DESC
            LIMIT ?
            """,
            (user_id, tenant_id, limit),
        ) or []
        return [
            OrderHistoryResponse(
                order_id=row["order_id"],
                ticker=row["ticker"],
                order_type=row["order_type"],
                quantity=row["quantity"],
                price_at_order=row["price_at_order"],
                order_date=(
                    row["order_date"].isoformat()
                    if hasattr(row["order_date"], "isoformat")
                    else str(row["order_date"])
                ),
                is_real=real_flag,
            )
            for row in rows
        ]

    if is_real is True:
        return fetch_table("real_orders", True)
    if is_real is False:
        return fetch_table("simulated_orders", False)

    merged = fetch_table("real_orders", True) + fetch_table("simulated_orders", False)
    merged.sort(key=lambda x: x.order_date, reverse=True)
    return merged[:limit]


@router.get("/daily-plan", response_model=DailyPlanResponse)
async def get_daily_plan(
    is_real: bool = Query(False),
    profile: str = Query("leigo"),
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Gera orientacao diaria didatica para carteira simulada ou real."""
    user_id = current_user["user_id"]
    tenant_id = current_user.get("tenant_id", 1)
    table_positions = "real_positions" if is_real else "simulated_positions"
    capabilities = _get_tenant_capabilities(db, tenant_id)
    features = capabilities.get("features", {})

    learning_profile = _normalize_learning_profile(profile)

    if not features.get("allow_daily_plan", True):
        raise HTTPException(
            status_code=403,
            detail="Seu plano atual nao permite plano diario automatizado.",
        )
    if is_real and not features.get("allow_real_portfolio", False):
        raise HTTPException(
            status_code=403,
            detail="Seu plano atual nao permite plano diario da carteira real.",
        )

    positions = db.fetch_all(
        f"SELECT ticker, quantity, avg_price, total_cost FROM {table_positions} WHERE user_id = ? AND tenant_id = ?",
        (user_id, tenant_id),
    ) or []

    if not positions:
        return DailyPlanResponse(
            generated_at=datetime.now().isoformat(timespec="seconds"),
            is_real=is_real,
            profile=learning_profile,
            summary=_profile_reason(learning_profile, "empty_summary"),
            next_step=_profile_reason(learning_profile, "empty_next_step"),
            guidance=[],
        )

    guidance_items: List[DailyGuidanceItem] = []
    for pos in positions:
        ticker = pos["ticker"]
        signal = db.fetch_one(
            "SELECT score_final FROM signals WHERE ticker = ? ORDER BY date DESC LIMIT 1",
            (ticker,),
        )
        price_data = db.fetch_one(
            "SELECT close FROM prices WHERE ticker = ? ORDER BY date DESC LIMIT 1",
            (ticker,),
        )

        if not price_data:
            guidance_items.append(
                DailyGuidanceItem(
                    ticker=ticker,
                    action="Acompanhar",
                    reason=_profile_reason(learning_profile, "sem_preco"),
                    risk_level="MEDIO",
                )
            )
            continue

        current_price = float(price_data["close"])
        avg_price = float(pos["avg_price"])
        pl_pct = ((current_price / avg_price) - 1) * 100 if avg_price else 0.0
        score = float(signal["score_final"]) if signal and signal.get("score_final") is not None else None

        if pl_pct <= -10 or (score is not None and score < 0):
            action = "Reduzir risco"
            reason = _profile_reason(learning_profile, "reduzir_risco")
            risk = "ALTO"
        elif pl_pct >= 20:
            action = "Realizar parcial"
            reason = _profile_reason(learning_profile, "realizar_parcial")
            risk = "MEDIO"
        elif score is not None and score >= 1.0:
            action = "Manter"
            reason = _profile_reason(learning_profile, "manter")
            risk = "BAIXO"
        else:
            action = "Acompanhar"
            reason = _profile_reason(learning_profile, "acompanhar")
            risk = "BAIXO"

        guidance_items.append(
            DailyGuidanceItem(
                ticker=ticker,
                action=action,
                reason=reason,
                risk_level=risk,
                signal_score=score,
                profit_loss_pct=pl_pct,
            )
        )

    high_risk = sum(1 for g in guidance_items if g.risk_level == "ALTO")
    summary_template = "summary_risk" if high_risk > 0 else "summary_stable"
    summary = _profile_reason(learning_profile, summary_template).format(
        n=len(guidance_items),
        r=high_risk,
    )

    next_step = _profile_reason(
        learning_profile,
        "next_step_risk" if high_risk > 0 else "next_step_stable",
    )

    return DailyPlanResponse(
        generated_at=datetime.now().isoformat(timespec="seconds"),
        is_real=is_real,
        profile=learning_profile,
        summary=summary,
        next_step=next_step,
        guidance=guidance_items,
    )
