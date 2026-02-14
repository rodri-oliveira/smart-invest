from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from aim.data_layer.database import Database
from api.routers.auth import get_current_user

router = APIRouter(tags=["Carteira e Simulação"])

class OrderRequest(BaseModel):
    ticker: str
    order_type: str # 'BUY', 'SELL'
    quantity: int
    price: Optional[float] = None
    is_real: bool = False # Define se é Simulação ou Carteira Real

class PositionResponse(BaseModel):
    ticker: str
    quantity: int
    avg_price: float
    total_cost: float
    current_price: Optional[float] = None
    profit_loss: Optional[float] = None
    profit_loss_pct: Optional[float] = None

def get_db():
    return Database()

@router.post("/order")
async def create_order(
    order: OrderRequest, 
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Cria uma ordem de compra ou venda (simulada ou real)."""
    user_id = current_user["user_id"]
    table_orders = "real_orders" if order.is_real else "simulated_orders"
    table_positions = "real_positions" if order.is_real else "simulated_positions"
    
    price = order.price
    if price is None:
        price_data = db.fetch_one(
            "SELECT close FROM prices WHERE ticker = ? ORDER BY date DESC LIMIT 1",
            (order.ticker,)
        )
        if not price_data:
            raise HTTPException(status_code=400, detail=f"Preço não encontrado para {order.ticker}")
        price = price_data["close"]

    try:
        with db.transaction() as conn:
            # 1. Registrar a ordem
            conn.execute(
                f"""
                INSERT INTO {table_orders} (user_id, ticker, order_type, quantity, price_at_order)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, order.ticker, order.order_type, order.quantity, price)
            )
            
            # 2. Atualizar posição
            pos = db.fetch_one(
                f"SELECT * FROM {table_positions} WHERE user_id = ? AND ticker = ?",
                (user_id, order.ticker)
            )
            
            if order.order_type == 'BUY':
                if pos:
                    new_qty = pos["quantity"] + order.quantity
                    new_cost = pos["total_cost"] + (order.quantity * price)
                    new_avg = new_cost / new_qty
                    conn.execute(
                        f"UPDATE {table_positions} SET quantity = ?, avg_price = ?, total_cost = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ? AND ticker = ?",
                        (new_qty, new_avg, new_cost, user_id, order.ticker)
                    )
                else:
                    conn.execute(
                        f"INSERT INTO {table_positions} (user_id, ticker, quantity, avg_price, total_cost) VALUES (?, ?, ?, ?, ?)",
                        (user_id, order.ticker, order.quantity, price, order.quantity * price)
                    )
            elif order.order_type == 'SELL':
                if not pos or pos["quantity"] < order.quantity:
                    raise HTTPException(status_code=400, detail="Quantidade insuficiente para venda")
                
                new_qty = pos["quantity"] - order.quantity
                if new_qty == 0:
                    conn.execute(f"DELETE FROM {table_positions} WHERE user_id = ? AND ticker = ?", (user_id, order.ticker))
                else:
                    new_cost = new_qty * pos["avg_price"]
                    conn.execute(
                        f"UPDATE {table_positions} SET quantity = ?, total_cost = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ? AND ticker = ?",
                        (new_qty, new_cost, user_id, order.ticker)
                    )
                    
        return {"status": "success", "message": f"Ordem de {order.order_type} ({'Real' if order.is_real else 'Simulada'}) para {order.ticker} executada"}
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/positions", response_model=List[PositionResponse])
async def get_positions(
    is_real: bool = Query(False),
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Retorna as posições atuais (reais ou simuladas) com lucro/prejuízo."""
    user_id = current_user["user_id"]
    table_positions = "real_positions" if is_real else "simulated_positions"
    
    positions = db.fetch_all(f"SELECT * FROM {table_positions} WHERE user_id = ?", (user_id,))
    # Verificar se positions é None e retornar lista vazia
    if positions is None:
        positions = []
        
    result = []
    for pos in positions:
        price_data = db.fetch_one(
            "SELECT close FROM prices WHERE ticker = ? ORDER BY date DESC LIMIT 1",
            (pos["ticker"],)
        )
        
        current_price = price_data["close"] if price_data else pos["avg_price"]
        total_value = pos["quantity"] * current_price
        pl = total_value - pos["total_cost"]
        pl_pct = (pl / pos["total_cost"] * 100) if pos["total_cost"] > 0 else 0
        
        result.append(PositionResponse(
            ticker=pos["ticker"],
            quantity=pos["quantity"],
            avg_price=pos["avg_price"],
            total_cost=pos["total_cost"],
            current_price=current_price,
            profit_loss=pl,
            profit_loss_pct=pl_pct
        ))
    return result

@router.get("/alerts", response_model=List[dict])
async def get_simulation_alerts(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Gera alertas operacionais para as posições do usuário (simuladas e reais)."""
    user_id = current_user["user_id"]
    
    # 1. Buscar posições
    sim_positions = db.fetch_all("SELECT * FROM simulated_positions WHERE user_id = ?", (user_id,))
    real_positions = db.fetch_all("SELECT * FROM real_positions WHERE user_id = ?", (user_id,))
    
    all_alerts = []
    
    for pos_list, is_real in [(sim_positions, False), (real_positions, True)]:
        for pos in pos_list:
            ticker = pos["ticker"]
            
            # Buscar sinal mais recente
            signal = db.fetch_one(
                "SELECT score_final FROM signals WHERE ticker = ? ORDER BY date DESC LIMIT 1",
                (ticker,)
            )
            
            # Buscar preço atual
            price_data = db.fetch_one(
                "SELECT close FROM prices WHERE ticker = ? ORDER BY date DESC LIMIT 1",
                (ticker,)
            )
            
            if not signal or not price_data:
                continue
                
            current_price = price_data["close"]
            score = signal["score_final"]
            pl_pct = (current_price / pos["avg_price"] - 1) * 100
            
            # Regras de Alerta
            # 1. Stop Loss (simples 10%)
            if pl_pct <= -10:
                all_alerts.append({
                    "ticker": ticker,
                    "type": "STOP_LOSS",
                    "severity": "HIGH",
                    "message": f"Ativo em queda de {pl_pct:.1f}%. Considere reduzir exposição.",
                    "is_real": is_real
                })
            
            # 2. Score Deteriorado
            if score < 0:
                all_alerts.append({
                    "ticker": ticker,
                    "type": "REBALANCE",
                    "severity": "MEDIUM",
                    "message": f"Score atual ({score:.2f}) indica saída da estratégia.",
                    "is_real": is_real
                })
                
            # 3. Take Profit (simples 20%)
            if pl_pct >= 20:
                all_alerts.append({
                    "ticker": ticker,
                    "type": "TAKE_PROFIT",
                    "severity": "LOW",
                    "message": f"Lucro de {pl_pct:.1f}% atingido. Ótimo momento para rebalancear.",
                    "is_real": is_real
                })
                
    return all_alerts
