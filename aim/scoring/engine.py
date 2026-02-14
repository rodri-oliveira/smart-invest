"""Engine principal de scoring para o universo de ativos."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from aim.config.parameters import DEFAULT_UNIVERSE
from aim.data_layer.database import Database
from aim.regime.engine import get_current_regime
from aim.scoring.calculator import calculate_composite_score

logger = logging.getLogger(__name__)


def load_features_for_scoring(
    db: Database,
    date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Carrega features calculadas para scoring.
    
    Args:
        db: Conexão com banco
        date: Data específica. Se None, usa a mais recente.
    
    Returns:
        DataFrame com features de todos os ativos
    """
    if date is None:
        # Pegar data mais recente
        result = db.fetch_one(
            "SELECT MAX(date) as max_date FROM features"
        )
        if result and result["max_date"]:
            date = result["max_date"]
        else:
            logger.warning("Sem dados de features disponíveis")
            return pd.DataFrame()
    
    query = """
        SELECT *
        FROM features
        WHERE date = ?
    """
    
    df = db.query_to_df(query, (date,))
    
    if df.empty:
        logger.warning(f"Sem features para data: {date}")
    else:
        logger.info(f"Carregadas features de {len(df)} ativos para {date}")
    
    return df


def load_fundamentals_for_scoring(
    db: Database,
    date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Carrega dados fundamentalistas mais recentes.
    
    Args:
        db: Conexão com banco
        date: Data de referência
    
    Returns:
        DataFrame com fundamentos
    """
    # Pegar os fundamentos mais recentes de cada ativo
    query = """
        SELECT 
            f.ticker, f.reference_date, f.report_type,
            f.p_l, f.p_vp, f.dy, f.roe, f.roic, 
            f.net_margin, f.gross_margin, f.ebitda,
            f.market_cap, f.divida_patrimonio
        FROM fundamentals f
        INNER JOIN (
            SELECT ticker, MAX(reference_date) as max_date
            FROM fundamentals
            GROUP BY ticker
        ) latest ON f.ticker = latest.ticker 
            AND f.reference_date = latest.max_date
    """
    
    df = db.query_to_df(query)
    
    if not df.empty:
        logger.info(f"Carregados fundamentos de {len(df)} ativos")
    
    return df


def calculate_daily_scores(
    db: Database,
    date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Calcula scores diários para todo o universo.
    
    Args:
        db: Conexão com banco
        date: Data específica. Se None, usa a mais recente.
    
    Returns:
        DataFrame com scores de todos os ativos
    """
    logger.info("Iniciando cálculo de scores...")
    
    # 1. Carregar features
    features_df = load_features_for_scoring(db, date)
    if features_df.empty:
        logger.error("Sem features disponíveis para scoring")
        return pd.DataFrame()
    
    # 2. Carregar fundamentos (se disponíveis)
    fundamentals_df = load_fundamentals_for_scoring(db, date)
    
    # 3. Obter regime atual
    regime_data = get_current_regime(db)
    if regime_data:
        regime = regime_data["regime"]
        logger.info(f"Regime atual: {regime}")
    else:
        regime = "TRANSITION"
        logger.warning("Sem dados de regime - usando TRANSITION")
    
    # 4. Calcular scores
    scores_df = calculate_composite_score(
        features_df=features_df,
        fundamentals_df=fundamentals_df if not fundamentals_df.empty else None,
        regime=regime,
    )
    
    return scores_df


def save_scores_to_database(
    db: Database,
    scores_df: pd.DataFrame,
) -> None:
    """
    Salva scores calculados no banco.
    
    Args:
        db: Conexão com banco
        scores_df: DataFrame com scores
    """
    logger.info(f"Salvando {len(scores_df)} scores no banco...")
    
    # Selecionar apenas colunas relevantes para a tabela signals
    columns_to_save = [
        "date", "ticker",
        "score_momentum", "score_quality", "score_value",
        "score_volatility", "score_liquidity", "score_final",
        "rank_universe", "regime_at_date"
    ]
    
    # Verificar se todas as colunas existem
    available_columns = [col for col in columns_to_save if col in scores_df.columns]
    
    for _, row in scores_df[available_columns].iterrows():
        record = row.to_dict()
        
        # Converter NaN para None
        for key, value in record.items():
            if pd.isna(value):
                record[key] = None
        
        db.upsert(
            "signals",
            record,
            conflict_columns=["date", "ticker"],
        )
    
    logger.info(f"✓ Scores salvos no banco")


def get_top_ranked_assets(
    db: Database,
    date: Optional[str] = None,
    top_n: int = 10,
    regime_filter: Optional[str] = None,
) -> pd.DataFrame:
    """
    Retorna top N ativos ranqueados.
    
    Args:
        db: Conexão com banco
        date: Data específica
        top_n: Quantos ativos retornar
        regime_filter: Filtrar por regime específico
    
    Returns:
        DataFrame com top ativos
    """
    if date is None:
        date_query = "SELECT MAX(date) as max_date FROM signals"
        result = db.fetch_one(date_query)
        date = result["max_date"] if result else None
    
    if not date:
        logger.error("Sem dados de signals disponíveis")
        return pd.DataFrame()
    
    query = """
        SELECT 
            s.ticker, 
            s.score_final,
            s.score_momentum,
            s.score_quality,
            s.score_value,
            s.score_volatility,
            s.score_liquidity,
            s.rank_universe,
            s.regime_at_date,
            a.sector,
            a.name
        FROM signals s
        JOIN assets a ON s.ticker = a.ticker
        WHERE s.date = ?
    """
    params = [date]
    
    if regime_filter:
        query += " AND s.regime_at_date = ?"
        params.append(regime_filter)
    
    query += """
        ORDER BY s.rank_universe ASC
        LIMIT ?
    """
    params.append(top_n)
    
    return db.query_to_df(query, tuple(params))


def generate_daily_signals(
    db: Database,
    date: Optional[str] = None,
) -> Dict:
    """
    Pipeline diário de geração de sinais.
    
    Args:
        db: Conexão com banco
        date: Data específica. Se None, usa a mais recente.
    
    Returns:
        Dict com estatísticas do processamento
    """
    logger.info("=" * 60)
    logger.info("Gerando sinais diários...")
    logger.info("=" * 60)
    
    try:
        # Calcular scores
        scores_df = calculate_daily_scores(db, date)
        
        if scores_df.empty:
            return {
                "signals_generated": 0,
                "status": "error",
                "message": "Sem dados para gerar sinais"
            }
        
        # Salvar no banco
        save_scores_to_database(db, scores_df)
        
        # Estatísticas
        stats = {
            "signals_generated": len(scores_df),
            "avg_score": float(scores_df["score_final"].mean()),
            "top_10": scores_df.nsmallest(10, "rank_universe")["ticker"].tolist(),
            "regime": scores_df["regime_at_date"].iloc[0] if "regime_at_date" in scores_df.columns else "UNKNOWN",
            "status": "success",
        }
        
        logger.info(f"✓ {stats['signals_generated']} sinais gerados")
        logger.info(f"✓ Top 10: {stats['top_10']}")
        
        return stats
        
    except Exception as e:
        logger.error(f"✗ Erro ao gerar sinais: {e}", exc_info=True)
        return {
            "signals_generated": 0,
            "status": "error",
            "message": str(e)
        }
