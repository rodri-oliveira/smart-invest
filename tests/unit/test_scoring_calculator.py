"""Testes para scoring/calculator.py - Validação da lógica de scores."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from aim.scoring.calculator import (
    calculate_z_score,
    calculate_momentum_score,
    calculate_quality_score,
    calculate_value_score,
    calculate_volatility_score,
    calculate_composite_score,
    FACTOR_WEIGHTS,
)


class TestZScore:
    """Testes para normalização z-score."""
    
    def test_z_score_basic(self):
        """Z-score deve normalizar corretamente."""
        data = pd.Series([1, 2, 3, 4, 5])
        z = calculate_z_score(data)
        
        # Média deve ser ~0
        assert abs(z.mean()) < 0.01
        # Std deve ser ~1
        assert abs(z.std() - 1) < 0.01
    
    def test_z_score_with_nan(self):
        """Z-score deve lidar com NaN."""
        data = pd.Series([1, 2, np.nan, 4, 5])
        z = calculate_z_score(data)
        
        # NaN deve ser propagado
        assert pd.isna(z[2])
        # Valores não-NaN devem ser calculados
        assert not pd.isna(z[0])
    
    def test_z_score_constant(self):
        """Z-score de série constante deve retornar 0."""
        data = pd.Series([5, 5, 5, 5])
        z = calculate_z_score(data)
        
        # Todos devem ser 0 (ou NaN se std=0)
        assert (z == 0).all() or pd.isna(z).all()


class TestMomentumScore:
    """Testes para cálculo de momentum."""
    
    def test_momentum_composite_weights(self):
        """Momentum composto deve usar pesos corretos."""
        df = pd.DataFrame({
            'ticker': ['A', 'B', 'C'],
            'momentum_3m': [0.1, 0.05, -0.02],
            'momentum_6m': [0.15, 0.08, 0.01],
            'momentum_12m': [0.20, 0.10, -0.05],
        })
        
        score = calculate_momentum_score(df)
        
        # Deve retornar série do mesmo tamanho
        assert len(score) == len(df)
        # Deve ser numérico
        assert score.dtype in ['float64', 'float32']
    
    def test_momentum_with_missing_data(self):
        """Momentum deve funcionar com dados ausentes."""
        df = pd.DataFrame({
            'ticker': ['A', 'B'],
            'momentum_3m': [0.1, np.nan],
            'momentum_6m': [0.15, 0.08],
            'momentum_12m': [0.20, 0.10],
        })
        
        score = calculate_momentum_score(df)
        
        # Deve calcular para ambos (NaN tratado como 0)
        assert len(score) == 2
        assert not pd.isna(score[0])


class TestQualityScore:
    """Testes para score de qualidade (fundamentos)."""
    
    def test_quality_with_all_data(self):
        """Qualidade deve usar ROE, margem, ROIC quando disponíveis."""
        df = pd.DataFrame({
            'ticker': ['A', 'B', 'C'],
            'roe': [0.20, 0.15, 0.10],
            'net_margin': [0.25, 0.20, 0.15],
            'roic': [0.18, 0.12, 0.08],
        })
        
        score = calculate_quality_score(df)
        
        # Deve retornar score para todos
        assert len(score) == 3
        # Maior ROE deve ter score maior
        assert score[0] > score[2]
    
    def test_quality_with_partial_data(self):
        """Qualidade deve funcionar com dados parciais."""
        df = pd.DataFrame({
            'ticker': ['A', 'B'],
            'roe': [0.20, np.nan],
            'net_margin': [0.25, 0.20],
            'roic': [np.nan, np.nan],  # ROIC não disponível
        })
        
        score = calculate_quality_score(df)
        
        # Deve calcular mesmo com dados incompletos
        assert len(score) == 2
        assert not pd.isna(score[0])
    
    def test_quality_no_data(self):
        """Qualidade deve retornar 0 se nenhum dado disponível."""
        df = pd.DataFrame({
            'ticker': ['A', 'B'],
        })
        
        score = calculate_quality_score(df)
        
        # Deve retornar série de zeros
        assert len(score) == 2
        assert (score == 0).all()


class TestValueScore:
    """Testes para score de valor (P/L, P/VP, DY)."""
    
    def test_value_with_all_multiples(self):
        """Valor deve usar P/L, P/VP, DY quando disponíveis."""
        df = pd.DataFrame({
            'ticker': ['A', 'B', 'C'],
            'p_l': [10, 15, 20],      # Menor = mais barato
            'p_vp': [1.5, 2.0, 2.5],
            'dy': [0.05, 0.03, 0.02],  # Maior = melhor
        })
        
        score = calculate_value_score(df)
        
        # Deve retornar score para todos
        assert len(score) == 3
        # Menor P/L deve ter score maior (mais barato)
        assert score[0] > score[2]
    
    def test_value_with_partial_data(self):
        """Valor deve funcionar com múltiplos parciais."""
        df = pd.DataFrame({
            'ticker': ['A', 'B'],
            'p_l': [10, np.nan],
            'p_vp': [np.nan, 2.0],
            'dy': [0.05, 0.03],
        })
        
        score = calculate_value_score(df)
        
        # Deve calcular mesmo com dados parciais
        assert len(score) == 2
    
    def test_value_no_data(self):
        """Valor deve retornar 0 se nenhum múltiplo disponível."""
        df = pd.DataFrame({
            'ticker': ['A', 'B'],
        })
        
        score = calculate_value_score(df)
        
        # Deve retornar série de zeros
        assert len(score) == 2
        assert (score == 0).all()
    
    def test_value_handles_zero_pl(self):
        """Valor deve lidar com P/L = 0 (evitar divisão por zero)."""
        df = pd.DataFrame({
            'ticker': ['A', 'B'],
            'p_l': [0, 10],  # Zero deve ser tratado
            'p_vp': [1.5, 2.0],
            'dy': [0.05, 0.03],
        })
        
        score = calculate_value_score(df)
        
        # Não deve quebrar
        assert len(score) == 2
        assert not pd.isna(score).any()


class TestVolatilityScore:
    """Testes para score de volatilidade."""
    
    def test_volatility_inverse(self):
        """Volatilidade menor deve dar score maior."""
        df = pd.DataFrame({
            'ticker': ['A', 'B', 'C'],
            'vol_63d': [0.15, 0.25, 0.35],  # Anualizada
        })
        
        score = calculate_volatility_score(df)
        
        # Menor vol deve ter maior score
        assert score[0] > score[2]
    
    def test_volatility_with_missing(self):
        """Volatilidade deve lidar com dados ausentes."""
        df = pd.DataFrame({
            'ticker': ['A', 'B'],
            'vol_63d': [0.15, np.nan],
        })
        
        score = calculate_volatility_score(df)
        
        # Deve calcular para ambos
        assert len(score) == 2


class TestCompositeScore:
    """Testes para cálculo de score final."""
    
    def test_composite_with_all_factors(self):
        """Score final deve combinar todos os fatores."""
        features_df = pd.DataFrame({
            'ticker': ['A', 'B', 'C'],
            'date': ['2024-01-01'] * 3,
            'momentum_3m': [0.1, 0.05, -0.02],
            'momentum_6m': [0.15, 0.08, 0.01],
            'momentum_12m': [0.20, 0.10, -0.05],
            'vol_63d': [0.20, 0.25, 0.30],
            'liquidity_score': [0.8, 0.6, 0.4],
        })
        
        fundamentals_df = pd.DataFrame({
            'ticker': ['A', 'B', 'C'],
            'p_l': [10, 15, 20],
            'p_vp': [1.5, 2.0, 2.5],
            'dy': [0.05, 0.03, 0.02],
            'roe': [0.20, 0.15, 0.10],
            'net_margin': [0.25, 0.20, 0.15],
            'roic': [0.18, 0.12, 0.08],
        })
        
        result = calculate_composite_score(
            features_df=features_df,
            fundamentals_df=fundamentals_df,
            regime="BULL"
        )
        
        # Deve retornar DataFrame
        assert isinstance(result, pd.DataFrame)
        # Deve ter colunas de scores
        assert 'score_momentum' in result.columns
        assert 'score_quality' in result.columns
        assert 'score_value' in result.columns
        assert 'score_final' in result.columns
        assert 'rank_universe' in result.columns
        # Deve ter mesmo número de linhas
        assert len(result) == 3
    
    def test_composite_without_fundamentals(self):
        """Score deve funcionar sem dados fundamentalistas."""
        features_df = pd.DataFrame({
            'ticker': ['A', 'B'],
            'date': ['2024-01-01'] * 2,
            'momentum_3m': [0.1, 0.05],
            'momentum_6m': [0.15, 0.08],
            'momentum_12m': [0.20, 0.10],
            'vol_63d': [0.20, 0.25],
            'liquidity_score': [0.8, 0.6],
        })
        
        result = calculate_composite_score(
            features_df=features_df,
            fundamentals_df=None,
            regime="TRANSITION"
        )
        
        # Deve calcular mesmo sem fundamentos
        assert len(result) == 2
        # Qualidade e valor devem ser 0
        assert (result['score_quality'] == 0).all()
        assert (result['score_value'] == 0).all()
        # Momentum deve ser calculado
        assert (result['score_momentum'] != 0).any()
    
    def test_composite_weights_by_regime(self):
        """Pesos devem mudar conforme regime."""
        features_df = pd.DataFrame({
            'ticker': ['A'],
            'date': ['2024-01-01'],
            'momentum_3m': [0.1],
            'momentum_6m': [0.15],
            'momentum_12m': [0.20],
            'vol_63d': [0.20],
            'liquidity_score': [0.8],
        })
        
        fundamentals_df = pd.DataFrame({
            'ticker': ['A'],
            'p_l': [10],
            'p_vp': [1.5],
            'dy': [0.05],
            'roe': [0.20],
            'net_margin': [0.25],
            'roic': [0.18],
        })
        
        # Testar diferentes regimes
        for regime in ['BULL', 'BEAR', 'TRANSITION']:
            result = calculate_composite_score(
                features_df=features_df,
                fundamentals_df=fundamentals_df,
                regime=regime
            )
            
            assert len(result) == 1
            assert 'score_final' in result.columns
    
    def test_composite_ranking(self):
        """Ranking deve estar ordenado corretamente."""
        features_df = pd.DataFrame({
            'ticker': ['A', 'B', 'C', 'D', 'E'],
            'date': ['2024-01-01'] * 5,
            'momentum_3m': [0.2, 0.15, 0.1, 0.05, 0.0],
            'momentum_6m': [0.25, 0.2, 0.15, 0.1, 0.05],
            'momentum_12m': [0.3, 0.25, 0.2, 0.15, 0.1],
            'vol_63d': [0.15, 0.18, 0.20, 0.22, 0.25],
            'liquidity_score': [0.9, 0.8, 0.7, 0.6, 0.5],
        })
        
        result = calculate_composite_score(
            features_df=features_df,
            fundamentals_df=None,
            regime="TRANSITION"
        )
        
        # Verificar se ranking está correto
        # Maior score_final deve ter rank 1
        top_scorer = result.loc[result['score_final'].idxmax()]
        assert top_scorer['rank_universe'] == 1
        
        # Ranking deve ser sequencial
        ranks = sorted(result['rank_universe'].unique())
        assert ranks == list(range(1, len(result) + 1))
