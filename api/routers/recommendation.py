"""Endpoints para recomendaÃ§Ã£o."""

import os
import re
import subprocess
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from aim.data_layer.database import Database
from aim.intent.parser import IntentParser
from aim.sentiment.scorer import SentimentScorer

router = APIRouter(tags=["RecomendaÃ§Ã£o"])

class IntentRequest(BaseModel):
    prompt: str

class RecommendationRequest(BaseModel):
    intent: Dict[str, Any]
    signals: List[Dict[str, Any]]


class AssetInsightRequest(BaseModel):
    prompt: str


class PromptRouteRequest(BaseModel):
    prompt: str


class PromptRouteResponse(BaseModel):
    route: str  # portfolio | asset_query | out_of_scope
    in_scope: bool
    reason: str
    safe_response: str
    confidence: float
    detected_ticker: Optional[str] = None
    disambiguation_options: Optional[List[Dict[str, str]]] = None


class AssetRequestCreate(BaseModel):
    prompt: str


class AssetRequestResponse(BaseModel):
    status: str
    message: str
    request_id: Optional[int] = None


class UpdateStatusResponse(BaseModel):
    status: str  # idle | running | finished | failed
    message: str
    pid: Optional[int] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    exit_code: Optional[int] = None


_manual_update_process: Optional[subprocess.Popen] = None
_manual_update_started_at: Optional[str] = None
_manual_update_finished_at: Optional[str] = None
_manual_update_exit_code: Optional[int] = None


def get_db():
    return Database()


def _find_asset_from_prompt(db: Database, prompt: str) -> Optional[Dict[str, Any]]:
    """Tenta identificar um ativo por ticker ou nome da empresa no prompt."""
    prompt_lower = prompt.lower()
    prompt_normalized = unicodedata.normalize("NFKD", prompt_lower)
    prompt_normalized = "".join(c for c in prompt_normalized if not unicodedata.combining(c))

    # 1) Buscar ticker explÃ­cito (ex.: WEGE3, PETR4, TAEE11)
    ticker_match = re.search(r"\b([a-zA-Z]{4}\d{1,2})\b", prompt)
    if ticker_match:
        ticker = ticker_match.group(1).upper()
        asset = db.fetch_one(
            "SELECT ticker, name, sector FROM assets WHERE ticker = ? LIMIT 1",
            (ticker,),
        )
        if asset:
            return asset

    # 2) Buscar por termos relevantes no nome do ativo
    stopwords = {
        "como",
        "estao",
        "estÃ£o",
        "acao",
        "acoes",
        "aÃ§Ãµes",
        "mostrar",
        "mostra",
        "me",
        "da",
        "das",
        "de",
        "do",
        "no",
        "na",
        "e",
        "as",
        "os",
    }
    terms = [
        t for t in re.findall(r"[a-zA-Z0-9]+", prompt_normalized)
        if len(t) >= 3 and t not in stopwords
    ]
    terms = _expand_asset_aliases(terms)

    all_assets = db.fetch_all(
        "SELECT ticker, name, sector, is_active FROM assets ORDER BY is_active DESC, ticker ASC"
    ) or []

    def normalize_text(text: str) -> str:
        n = unicodedata.normalize("NFKD", text.lower())
        return "".join(c for c in n if not unicodedata.combining(c))

    def similarity(a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio()

    candidates: List[Dict[str, Any]] = []
    for asset in all_assets:
        name_normalized = normalize_text(asset.get("name", ""))
        ticker_normalized = normalize_text(asset.get("ticker", ""))
        name_tokens = [tok for tok in re.findall(r"[a-zA-Z0-9]+", name_normalized) if len(tok) >= 3]
        score = 0
        for term in terms:
            if ticker_normalized == term:
                score += 8
            elif ticker_normalized.startswith(term):
                score += 6
            if term in name_normalized:
                score += 4
            for token in name_tokens:
                # Tolerar erros simples de digitacao em nomes de empresas.
                if similarity(term, token) >= 0.82:
                    score += 3
                    break
        if score > 0:
            candidates.append(
                {
                    "ticker": asset["ticker"],
                    "name": asset.get("name"),
                    "sector": asset.get("sector"),
                    "score": score,
                }
            )

    if not candidates:
        return None

    # Desempate por liquidez recente (sem hardcode de ticker preferido).
    def recent_volume(ticker: str) -> float:
        vol = db.fetch_one(
            "SELECT volume FROM prices WHERE ticker = ? ORDER BY date DESC LIMIT 1",
            (ticker,),
        )
        return float(vol["volume"]) if vol and vol.get("volume") is not None else 0.0

    candidates.sort(
        key=lambda c: (c["score"], recent_volume(c["ticker"]), c["ticker"]),
        reverse=True,
    )
    best = candidates[0]
    return {
        "ticker": best["ticker"],
        "name": best.get("name"),
        "sector": best.get("sector"),
    }


def _suggest_assets_from_prompt(db: Database, prompt: str, limit: int = 5) -> List[Dict[str, str]]:
    """Gera sugestÃµes de ativos prÃ³ximos quando nÃ£o houver match exato."""
    normalized_prompt = _normalize_prompt(prompt)
    terms = [t for t in re.findall(r"[a-z0-9]+", normalized_prompt) if len(t) >= 3]
    if not terms:
        return []

    all_assets = db.fetch_all(
        "SELECT ticker, name, sector, is_active FROM assets ORDER BY is_active DESC, ticker ASC"
    ) or []

    suggestions: List[Dict[str, Any]] = []
    for asset in all_assets:
        ticker = (asset.get("ticker") or "").strip()
        name = (asset.get("name") or "").strip()
        sector = (asset.get("sector") or "").strip()
        normalized_ticker = _normalize_prompt(ticker)
        normalized_name = _normalize_prompt(name)
        name_tokens = [tok for tok in re.findall(r"[a-z0-9]+", normalized_name) if len(tok) >= 3]

        score = 0.0
        for term in terms:
            if term in normalized_ticker:
                score += 3.0
            if term in normalized_name:
                score += 2.0
            score += max(SequenceMatcher(None, term, normalized_ticker).ratio() - 0.75, 0) * 2.0
            for token in name_tokens:
                score += max(SequenceMatcher(None, term, token).ratio() - 0.82, 0)

        if score > 0:
            suggestions.append(
                {
                    "ticker": ticker,
                    "name": name,
                    "sector": sector,
                    "score": score,
                }
            )

    suggestions.sort(key=lambda item: (item["score"], item["ticker"]), reverse=True)
    return [
        {
            "ticker": item["ticker"],
            "name": item["name"],
            "sector": item["sector"],
        }
        for item in suggestions[:limit]
    ]


def _normalize_prompt(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in normalized if not unicodedata.combining(c))


def _expand_asset_aliases(terms: List[str]) -> List[str]:
    """Expande apelidos comuns para melhorar deteccao por linguagem natural."""
    alias_map = {
        "santande": ["santander"],
        "santader": ["santander"],
        "magalu": ["magazine", "luiza"],
        "petrbras": ["petrobras"],
        "petro": ["petrobras"],
        "itau": ["itau", "itausa"],
        "bancodobrasil": ["banco", "brasil"],
    }
    expanded = list(terms)
    for term in terms:
        for alias in alias_map.get(term, []):
            if alias not in expanded:
                expanded.append(alias)
    return expanded


def _ensure_asset_request_schema(db: Database) -> None:
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS pending_asset_requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_prompt TEXT NOT NULL,
            normalized_prompt TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_pending_asset_requests_normalized ON pending_asset_requests(normalized_prompt, created_at DESC)"
    )


def _route_prompt(db: Database, prompt: str) -> PromptRouteResponse:
    normalized = _normalize_prompt(prompt)
    tokens = re.findall(r"[a-z0-9]+", normalized)
    expanded_tokens = _expand_asset_aliases(tokens)

    has_ticker_pattern = bool(re.search(r"\b[a-zA-Z]{4}\d{1,2}\b", prompt))
    asset = _find_asset_from_prompt(db, prompt)

    asset_query_terms = {
        "acao", "acoes", "ativo", "cotacao", "preco", "ticker", "mercado",
        "petrobras", "petro", "santander", "weg", "vale", "itau", "b3",
        "empresa", "papel", "bolsa",
    }
    portfolio_terms = {
        "carteira", "retorno", "risco", "dividendo", "renda", "proteger",
        "capital", "balanceado", "especular", "objetivo", "horizonte", "investir",
        "investimento", "prazo", "perfil", "ganhar", "perder",
    }
    out_of_scope_terms = {
        "futebol", "politica", "receita", "culinaria", "filme", "serie",
        "jogo", "namoro", "piada", "senha", "hack", "invadir",
    }
    greeting_terms = {"oi", "ola", "hello", "bom", "boa", "dia", "tarde", "noite", "tudo", "bem", "obrigado", "obrigada", "valeu"}
    unsafe_terms = {"hack", "invadir", "senha", "exploit", "burlar"}

    matched_asset_terms = [t for t in asset_query_terms if t in normalized]
    matched_portfolio_terms = [t for t in portfolio_terms if t in normalized]
    matched_out_terms = [t for t in out_of_scope_terms if t in normalized]

    has_finance_context = any(t in asset_query_terms or t in portfolio_terms for t in expanded_tokens)
    has_unsafe_intent = any(t in unsafe_terms for t in expanded_tokens)
    has_greeting_only = bool(tokens) and len(tokens) <= 4 and all(t in greeting_terms for t in tokens)

    asset_query_patterns = [
        r"\bcomo\s+(esta|estao|ficou)\b",
        r"\bme\s+mostra\b",
        r"\bqual\s+(o\s+)?preco\b",
        r"\bcomo\s+anda\b",
        r"\bsobre\s+[a-z0-9]{3,}\b",
    ]
    has_asset_question_pattern = any(re.search(pattern, normalized) for pattern in asset_query_patterns)

    if has_unsafe_intent:
        return PromptRouteResponse(
            route="out_of_scope",
            in_scope=False,
            reason="pedido inseguro fora do escopo",
            safe_response=(
                "Nao posso ajudar com esse tipo de pedido. "
                "Se quiser, te ajudo com carteira, risco, retorno e leitura de ativos da B3."
            ),
            confidence=0.95,
        )

    if has_greeting_only:
        return PromptRouteResponse(
            route="out_of_scope",
            in_scope=False,
            reason="saudacao sem objetivo financeiro",
            safe_response=(
                "Posso te guiar de forma simples em investimentos. "
                "Exemplos: 'quero proteger meu capital' ou 'como esta WEGE3 hoje?'."
            ),
            confidence=0.85,
        )

    if matched_out_terms and not (has_finance_context or has_ticker_pattern or asset):
        return PromptRouteResponse(
            route="out_of_scope",
            in_scope=False,
            reason="prompt fora do escopo financeiro",
            safe_response=(
                "Consigo ajudar com investimentos, simulador e consulta de ativos. "
                "Se quiser, comecamos por: 'quero retorno com risco moderado' ou 'como esta PETR4?'."
            ),
            confidence=0.9,
        )

    has_asset_signal = bool(asset or has_ticker_pattern or matched_asset_terms or has_asset_question_pattern)
    has_portfolio_goal_pattern = any(k in normalized for k in [
        "quero", "objetivo", "retorno", "risco", "carteira", "investir", "dividendo"
    ])
    has_portfolio_signal = bool(matched_portfolio_terms or (has_finance_context and has_portfolio_goal_pattern))

    if has_asset_signal and has_portfolio_signal:
        return PromptRouteResponse(
            route="out_of_scope",
            in_scope=False,
            reason="intencao ambigua entre ativo e carteira",
            safe_response=(
                "Entendi duas intencoes no mesmo texto. "
                "Voce quer: 1) consultar um ativo especifico, ou 2) montar uma carteira pelo seu objetivo? "
                "Se preferir, envie em duas mensagens e eu te guio passo a passo."
            ),
            confidence=0.7,
            detected_ticker=(asset or {}).get("ticker") if asset else None,
            disambiguation_options=[
                {"id": "asset_query", "label": "Consultar ativo"},
                {"id": "portfolio", "label": "Montar carteira"},
            ],
        )

    if has_asset_signal:
        return PromptRouteResponse(
            route="asset_query",
            in_scope=True,
            reason="consulta de ativo detectada",
            safe_response="Consulta de ativo identificada. Vou trazer resumo didatico e risco.",
            confidence=0.85 if asset else 0.7,
            detected_ticker=(asset or {}).get("ticker") if asset else None,
        )

    if has_portfolio_signal:
        return PromptRouteResponse(
            route="portfolio",
            in_scope=True,
            reason="objetivo de carteira detectado",
            safe_response="Objetivo de carteira identificado. Vou montar sugestao com foco em risco.",
            confidence=0.78,
        )

    return PromptRouteResponse(
        route="out_of_scope",
        in_scope=False,
        reason="intencao insuficiente para recomendacao segura",
        safe_response=(
            "Nao entendi seu pedido com seguranca. "
            "Tente em uma frase simples, por exemplo: "
            "'quero renda passiva com dividendos' ou 'como esta SANB11?'."
        ),
        confidence=0.62,
    )


@router.post("/intent")
async def parse_intent(request: IntentRequest, db: Database = Depends(get_db)):
    """Parse user intent from natural language."""
    try:
        parser = IntentParser()
        intent = parser.parse(request.prompt)
        return {
            "objective": intent.objective.value,
            "horizon": intent.horizon.value,
            "risk_tolerance": intent.risk_tolerance.value,
            "user_regime": intent.user_regime,
            "priority_factors": intent.priority_factors,
            "max_volatility": intent.max_volatility,
            "max_drawdown": intent.max_drawdown,
            "confidence": intent.confidence,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/route", response_model=PromptRouteResponse)
async def route_prompt(request: PromptRouteRequest, db: Database = Depends(get_db)):
    """Roteia prompt para fluxo seguro: carteira, consulta de ativo ou fora de escopo."""
    try:
        return _route_prompt(db, request.prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao rotear prompt: {str(e)}")

@router.get("/data-status")
async def get_data_status(db: Database = Depends(get_db)):
    """Verifica a data dos dados mais recentes no sistema."""
    try:
        prices = db.fetch_one("SELECT MAX(date) as max_date FROM prices")
        scores = db.fetch_one("SELECT MAX(date) as max_date FROM signals")
        today = db.fetch_one("SELECT date('now') as today")
        universe = db.fetch_one("SELECT COUNT(*) as count FROM assets WHERE is_active = 1")

        prices_date = prices["max_date"] if prices else None
        scores_date = scores["max_date"] if scores else None
        active_universe = int(universe["count"]) if universe and universe.get("count") is not None else 0

        prices_count_latest = 0
        scores_count_latest = 0
        if prices_date:
            prices_latest = db.fetch_one(
                "SELECT COUNT(DISTINCT ticker) as count FROM prices WHERE date = ?",
                (prices_date,),
            )
            prices_count_latest = int(prices_latest["count"]) if prices_latest else 0
        if scores_date:
            scores_latest = db.fetch_one(
                "SELECT COUNT(DISTINCT ticker) as count FROM signals WHERE date = ?",
                (scores_date,),
            )
            scores_count_latest = int(scores_latest["count"]) if scores_latest else 0

        prices_coverage = (prices_count_latest / active_universe) if active_universe > 0 else 0.0
        scores_coverage = (scores_count_latest / active_universe) if active_universe > 0 else 0.0

        # Fresh means recency + minimum coverage.
        # 3-day tolerance handles weekend/holiday gap in local environments.
        is_fresh = False
        days_diff = None
        if prices_date and scores_date:
            days_diff_row = db.fetch_one(
                "SELECT julianday('now') - julianday(?) as diff",
                (prices_date,),
            )
            days_diff = float(days_diff_row["diff"]) if days_diff_row else None
            is_recent = (days_diff is not None) and (days_diff <= 3.0)
            has_coverage = prices_coverage >= 0.70 and scores_coverage >= 0.70
            is_fresh = is_recent and has_coverage

        return {
            "status": "fresh" if is_fresh else "stale",
            "prices_date": prices_date,
            "scores_date": scores_date,
            "today": today["today"],
            "prices_count": prices_count_latest,
            "scores_count": scores_count_latest,
            "active_universe": active_universe,
            "prices_coverage": prices_coverage,
            "scores_coverage": scores_coverage,
            "days_since_prices": days_diff,
            "message": (
                "Dados atualizados"
                if is_fresh
                else "Dados parciais/desatualizados - atualizacao recomendada"
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao verificar status: {str(e)}")


@router.get("/sentiment")
async def get_market_sentiment(db: Database = Depends(get_db)):
    """Retorna o sentimento atual do mercado baseado em dados macro e tÃ©cnicos."""
    try:
        scorer = SentimentScorer(db)
        result = scorer.calculate_daily_sentiment()
        
        return {
            "date": result["date"],
            "score": result["score"],
            "label": result["sentiment"],
            "confidence": result["confidence"],
            "components": {
                "macro": result["components"]["macro"]["score"] if "macro" in result["components"] else 0,
                "technical": result["components"]["technical"]["score"] if "technical" in result["components"] else 0,
                "volatility": result["components"]["volatility"]["score"] if "volatility" in result["components"] else 0,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao calcular sentimento: {str(e)}")


@router.post("/update-data")
async def trigger_data_update(db: Database = Depends(get_db)):
    """Executa o pipeline de atualizaÃ§Ã£o de dados sob demanda."""
    import sys

    global _manual_update_process
    global _manual_update_started_at
    global _manual_update_finished_at
    global _manual_update_exit_code
    
    try:
        if _manual_update_process and _manual_update_process.poll() is None:
            return {
                "status": "running",
                "message": "Atualizacao ja esta em andamento",
                "pid": _manual_update_process.pid,
                "estimated_time": "2-5 minutos"
            }

        # Verificar se o script existe
        script_path = os.path.join(os.getcwd(), "scripts", "daily_update.py")
        if not os.path.exists(script_path):
            raise HTTPException(status_code=500, detail="Script de pipeline nÃ£o encontrado")
        
        # Executar pipeline em subprocesso (nao bloqueia a API).
        # Evita pipe sem consumo para nao travar em logs longos.
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=os.getcwd()
        )
        _manual_update_process = process
        _manual_update_started_at = datetime.now().isoformat(timespec="seconds")
        _manual_update_finished_at = None
        _manual_update_exit_code = None
        
        return {
            "status": "started",
            "message": "AtualizaÃ§Ã£o de dados iniciada em background",
            "pid": process.pid,
            "estimated_time": "2-5 minutos"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao iniciar atualizaÃ§Ã£o: {str(e)}")


@router.get("/update-status", response_model=UpdateStatusResponse)
async def get_update_status():
    """Retorna status real da atualizacao manual em background."""
    global _manual_update_process
    global _manual_update_started_at
    global _manual_update_finished_at
    global _manual_update_exit_code

    if _manual_update_process is None:
        return UpdateStatusResponse(
            status="idle",
            message="Nenhuma atualizacao manual em execucao.",
        )

    exit_code = _manual_update_process.poll()
    if exit_code is None:
        return UpdateStatusResponse(
            status="running",
            message="Atualizacao em andamento.",
            pid=_manual_update_process.pid,
            started_at=_manual_update_started_at,
        )

    _manual_update_exit_code = int(exit_code)
    _manual_update_finished_at = _manual_update_finished_at or datetime.now().isoformat(timespec="seconds")
    status = "finished" if _manual_update_exit_code == 0 else "failed"
    message = "Atualizacao concluida com sucesso." if status == "finished" else "Atualizacao finalizou com erro."
    return UpdateStatusResponse(
        status=status,
        message=message,
        pid=_manual_update_process.pid,
        started_at=_manual_update_started_at,
        finished_at=_manual_update_finished_at,
        exit_code=_manual_update_exit_code,
    )


@router.post("/asset-insight")
async def get_asset_insight(
    request: AssetInsightRequest,
    db: Database = Depends(get_db),
):
    """Retorna um resumo didÃ¡tico de um ativo mencionado em linguagem natural."""
    try:
        asset = _find_asset_from_prompt(db, request.prompt)
        if not asset:
            suggestions = _suggest_assets_from_prompt(db, request.prompt, limit=5)
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "ASSET_NOT_FOUND",
                    "message": "NÃ£o identifiquei um ativo especÃ­fico no prompt.",
                    "didactic_message": (
                        "NÃ£o consegui localizar esse ativo no universo atual. "
                        "Tente pelo ticker (ex.: PETR4, WEGE3, SANB11) ou escolha uma sugestÃ£o prÃ³xima."
                    ),
                    "suggestions": suggestions,
                },
            )

        ticker = asset["ticker"]
        prices = db.fetch_all(
            """
            SELECT date, close
            FROM prices
            WHERE ticker = ?
            ORDER BY date DESC
            LIMIT 31
            """,
            (ticker,),
        )
        if not prices:
            raise HTTPException(status_code=404, detail=f"Sem preÃ§os para {ticker}")

        latest_price = prices[0]["close"]
        latest_date = prices[0]["date"]
        prev_price = prices[1]["close"] if len(prices) > 1 else latest_price
        price_7d = prices[min(7, len(prices) - 1)]["close"] if len(prices) > 1 else latest_price
        price_30d = prices[min(30, len(prices) - 1)]["close"] if len(prices) > 1 else latest_price

        day_change = ((latest_price / prev_price) - 1) * 100 if prev_price else 0
        change_7d = ((latest_price / price_7d) - 1) * 100 if price_7d else 0
        change_30d = ((latest_price / price_30d) - 1) * 100 if price_30d else 0

        latest_signal = db.fetch_one(
            """
            SELECT score_final, score_momentum, score_quality, score_value
            FROM signals
            WHERE ticker = ?
            ORDER BY date DESC
            LIMIT 1
            """,
            (ticker,),
        )

        score_final = latest_signal["score_final"] if latest_signal else None

        # Fallback de risco sem score: usa tendÃªncia curta + volatilidade realizada.
        closes_desc = [float(row["close"]) for row in prices if row.get("close") is not None]
        returns_abs = []
        for i in range(len(closes_desc) - 1):
            base = closes_desc[i + 1]
            if base:
                returns_abs.append(abs((closes_desc[i] / base) - 1))
        realized_vol = (sum(returns_abs) / len(returns_abs)) if returns_abs else 0.0

        if score_final is None:
            if realized_vol >= 0.03 or day_change <= -4:
                risk_label = "ALTO"
                guidance = (
                    "Sem score recente e com oscilacao elevada. "
                    "Para leigo: evite entrada grande e priorize protecao de risco."
                )
            elif change_30d > 5 and day_change >= -2:
                risk_label = "MODERADO"
                guidance = (
                    "Sem score recente, mas tendencia curta ainda positiva. "
                    "Para leigo: se entrar, prefira fracionar a compra."
                )
            else:
                risk_label = "MODERADO"
                guidance = (
                    "Sem score recente no motor quantitativo. "
                    "Para leigo: observe mais alguns dias antes de decidir."
                )
        elif score_final >= 1.0:
            guidance = (
                "Momento favorÃ¡vel no modelo. Para leigo: pode observar entrada "
                "gradual, sempre com limite de risco."
            )
            risk_label = "MODERADO"
        elif score_final >= 0:
            guidance = (
                "Ativo neutro no modelo. Para leigo: melhor acompanhar e esperar "
                "confirmaÃ§Ã£o de tendÃªncia."
            )
            risk_label = "MODERADO"
        else:
            guidance = (
                "Sinal enfraquecido no modelo. Para leigo: evite aumentar posiÃ§Ã£o "
                "atÃ© melhora dos indicadores."
            )
            risk_label = "ALTO"

        return {
            "mode": "asset_query",
            "ticker": ticker,
            "name": asset.get("name"),
            "sector": asset.get("sector"),
            "latest_price": latest_price,
            "latest_date": latest_date,
            "change_1d_pct": day_change,
            "change_7d_pct": change_7d,
            "change_30d_pct": change_30d,
            "score_final": score_final,
            "risk_label": risk_label,
            "guidance": guidance,
            "didactic_summary": (
                f"{ticker} estÃ¡ em R$ {latest_price:.2f}. "
                f"VariaÃ§Ã£o: {day_change:.2f}% no dia, {change_7d:.2f}% em 7 dias "
                f"e {change_30d:.2f}% em 30 dias."
            ),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar ativo: {str(e)}")


@router.post("/asset-request", response_model=AssetRequestResponse)
async def create_asset_request(
    request: AssetRequestCreate,
    db: Database = Depends(get_db),
):
    """Registra solicitacao de inclusao de ativo no universo para avaliacao posterior."""
    try:
        _ensure_asset_request_schema(db)
        normalized_prompt = _normalize_prompt(request.prompt or "")
        if len(normalized_prompt.strip()) < 3:
            raise HTTPException(status_code=400, detail="Prompt muito curto para solicitar inclusÃ£o.")

        existing = db.fetch_one(
            """
            SELECT request_id
            FROM pending_asset_requests
            WHERE normalized_prompt = ?
              AND status IN ('PENDING', 'APPROVED')
              AND created_at >= datetime('now', '-7 day')
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (normalized_prompt,),
        )
        if existing:
            return AssetRequestResponse(
                status="already_requested",
                message="Essa solicitaÃ§Ã£o jÃ¡ estÃ¡ em anÃ¡lise. VocÃª serÃ¡ avisado quando houver atualizaÃ§Ã£o.",
                request_id=existing["request_id"],
            )

        with db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO pending_asset_requests (raw_prompt, normalized_prompt, status)
                VALUES (?, ?, 'PENDING')
                """,
                (request.prompt, normalized_prompt),
            )
            request_id = int(cursor.lastrowid)

        return AssetRequestResponse(
            status="created",
            message="SolicitaÃ§Ã£o registrada com sucesso. Vamos avaliar e incluir se os dados estiverem disponÃ­veis.",
            request_id=request_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao registrar solicitaÃ§Ã£o: {str(e)}")


@router.get("/data-status/per-ticker")
async def get_data_status_per_ticker(db: Database = Depends(get_db)):
    """Retorna status individual de cada ativo: atualizado, desatualizado ou falha."""
    import json
    from pathlib import Path

    report_path = Path("data/last_update_report.json")

    # Buscar ultimo preco por ativo no banco
    per_ticker_db = db.fetch_all(
        """
        SELECT p.ticker, MAX(p.date) as last_date, p.source
        FROM prices p
        JOIN assets a ON p.ticker = a.ticker
        WHERE a.is_active = 1
        GROUP BY p.ticker
        ORDER BY p.ticker
        """
    )

    universe = db.fetch_all("SELECT ticker FROM assets WHERE is_active = 1")
    all_tickers = {r["ticker"] for r in universe}
    db_map = {r["ticker"]: {"last_date": r["last_date"], "source": r.get("source")} for r in per_ticker_db}

    # Ler relatorio da ultima atualizacao (se existir)
    update_report = {}
    if report_path.exists():
        try:
            raw = json.loads(report_path.read_text(encoding="utf-8"))
            for item in raw.get("results", []):
                update_report[item["ticker"]] = item
        except Exception:
            pass

    today_row = db.fetch_one("SELECT date('now') as today")
    today = today_row["today"] if today_row else None

    results = []
    for ticker in sorted(all_tickers):
        db_info = db_map.get(ticker)
        report_info = update_report.get(ticker, {})

        if not db_info or not db_info["last_date"]:
            status = "sem_dados"
            days_stale = None
        else:
            days_diff_row = db.fetch_one(
                "SELECT julianday('now') - julianday(?) as diff",
                (db_info["last_date"],),
            )
            days_stale = round(float(days_diff_row["diff"]), 1) if days_diff_row else None
            if days_stale is not None and days_stale <= 3.0:
                status = "atualizado"
            else:
                status = "desatualizado"

        if report_info.get("status") == "failed":
            status = "falha"

        results.append({
            "ticker": ticker,
            "status": status,
            "last_date": db_info["last_date"] if db_info else None,
            "source": db_info.get("source") if db_info else None,
            "days_stale": days_stale,
            "last_update_source": report_info.get("source"),
            "last_update_errors": report_info.get("errors", []),
        })

    summary = {
        "total": len(results),
        "atualizado": sum(1 for r in results if r["status"] == "atualizado"),
        "desatualizado": sum(1 for r in results if r["status"] == "desatualizado"),
        "falha": sum(1 for r in results if r["status"] == "falha"),
        "sem_dados": sum(1 for r in results if r["status"] == "sem_dados"),
    }

    return {
        "today": today,
        "summary": summary,
        "tickers": results,
    }


@router.post("/retry-failed-tickers")
async def retry_failed_tickers():
    """Dispara atualizacao apenas dos tickers que falharam na ultima execucao."""
    import json
    import sys
    from pathlib import Path

    global _manual_update_process
    global _manual_update_started_at
    global _manual_update_finished_at
    global _manual_update_exit_code

    if _manual_update_process and _manual_update_process.poll() is None:
        return {
            "status": "running",
            "message": "Atualizacao ja esta em andamento",
            "pid": _manual_update_process.pid,
        }

    report_path = Path("data/last_update_report.json")
    if not report_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Nenhum relatorio de atualizacao encontrado. Execute uma atualizacao completa primeiro.",
        )

    try:
        raw = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(status_code=500, detail="Erro ao ler relatorio de atualizacao.")

    failed = raw.get("failed_tickers", [])
    if not failed:
        return {
            "status": "ok",
            "message": "Nenhum ticker com falha para reprocessar.",
            "failed_tickers": [],
        }

    # Salvar lista de tickers para retry em arquivo temp
    retry_path = Path("data/retry_tickers.json")
    retry_path.write_text(json.dumps(failed), encoding="utf-8")

    script_path = Path(os.getcwd()) / "scripts" / "retry_failed.py"
    if not script_path.exists():
        raise HTTPException(status_code=500, detail="Script de retry nao encontrado.")

    process = subprocess.Popen(
        [sys.executable, str(script_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=os.getcwd(),
    )
    _manual_update_process = process
    _manual_update_started_at = datetime.now().isoformat(timespec="seconds")
    _manual_update_finished_at = None
    _manual_update_exit_code = None

    return {
        "status": "started",
        "message": f"Retry iniciado para {len(failed)} ticker(s)",
        "failed_tickers": failed,
        "pid": process.pid,
    }
