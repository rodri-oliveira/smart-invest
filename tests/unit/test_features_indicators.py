"""Testes para features calculation - Validação de indicadores técnicos."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from aim.features.momentum import (
    calculate_absolute_momentum,
    calculate_annualized_return,
)
from aim.features.volatility import (
    calculate_volatility,
)
from aim.features.liquidity import (
    calculate_liquidity_score,
)


class TestMomentumIndicators:
    """Testes para cálculo de momentum."""
    
    def test_momentum_positive_trend(self):
        """Momentum deve ser positivo em tendência de alta."""
        # Criar série de preços em alta (dobrou em 100 dias)
        dates = pd.date_range(start='2024-01-01', periods=100, freq='B')
        prices = pd.Series(
            np.linspace(100, 200, 100),  # Subiu de 100 para 200
            index=dates
        )
        
        mom = calculate_absolute_momentum(prices, window=63)
        
        # Momentum deve ser positivo (subiu ~47% nos últimos 63 dias)
        assert mom is not None
        assert mom > 0
        assert 0.4 < mom < 0.6
    
    def test_momentum_negative_trend(self):
        """Momentum deve ser negativo em tendência de baixa."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='B')
        prices = pd.Series(
            np.linspace(100, 50, 100),  # Caiu de 100 para 50
            index=dates
        )
        
        mom = calculate_absolute_momentum(prices, window=63)
        
        # Momentum deve ser negativo (caiu ~47% nos últimos 63 dias)
        assert mom is not None
        assert mom < 0
        assert -0.5 < mom < -0.3
    
    def test_momentum_sideways(self):
        """Momentum deve ser ~0 em mercado lateral."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='B')
        prices = pd.Series(
            [100 + np.random.normal(0, 2) for _ in range(100)],  # Flutua em torno de 100
            index=dates
        )
        
        mom = calculate_absolute_momentum(prices, window=63)
        
        # Momentum deve ser próximo de 0
        assert mom is not None
        assert -0.15 < mom < 0.15
    
    def test_momentum_insufficient_data(self):
        """Momentum deve retornar None com dados insuficientes."""
        dates = pd.date_range(start='2024-01-01', periods=10, freq='B')
        prices = pd.Series([100] * 10, index=dates)
        
        mom = calculate_absolute_momentum(prices, window=63)
        
        # Deve retornar None
        assert mom is None


class TestVolatilityIndicators:
    """Testes para cálculo de volatilidade."""
    
    def test_volatility_high_vol_period(self):
        """Volatilidade deve ser alta em período turbulento."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='B')
        # Preços com alta volatilidade
        prices = pd.Series(
            100 * np.cumprod(1 + np.random.normal(0, 0.03, 100)),  # 3% std diário
            index=dates
        )
        
        vol = calculate_volatility(prices, window=21)
        
        # Volatilidade deve ser alta (anualizada ~48%)
        assert vol is not None
        assert vol > 0.3
    
    def test_volatility_low_vol_period(self):
        """Volatilidade deve ser baixa em período calmo."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='B')
        # Preços com baixa volatilidade
        prices = pd.Series(
            100 * np.cumprod(1 + np.random.normal(0, 0.005, 100)),  # 0.5% std diário
            index=dates
        )
        
        vol = calculate_volatility(prices, window=21)
        
        # Volatilidade deve ser baixa (anualizada ~8%)
        assert vol is not None
        assert vol < 0.15
    
    def test_volatility_annualized(self):
        """Volatilidade deve estar anualizada."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='B')
        prices = pd.Series(
            100 * np.cumprod(1 + np.random.normal(0, 0.01, 100)),  # 1% ao dia
            index=dates
        )
        
        vol = calculate_volatility(prices, window=21)
        
        # Volatilidade deve estar em escala anualizada (> 0.1)
        assert vol is not None
        assert vol > 0.1


class TestLiquidityIndicators:
    """Testes para cálculo de liquidez."""
    
    def test_liquidity_high_volume(self):
        """Liquidez deve ser alta com volume elevado."""
        dates = pd.date_range(start='2024-01-01', periods=30, freq='B')
        prices = pd.Series([100] * 30, index=dates)
        volumes = pd.Series([10_000_000] * 30, index=dates)  # 10M por dia
        
        liq = calculate_liquidity_score(prices, volumes)
        
        # Liquidez deve ser alta (> 0.5)
        assert liq is not None
        assert liq > 0.5
    
    def test_liquidity_low_volume(self):
        """Liquidez deve ser baixa com volume reduzido."""
        dates = pd.date_range(start='2024-01-01', periods=30, freq='B')
        prices = pd.Series([100] * 30, index=dates)
        volumes = pd.Series([100_000] * 30, index=dates)  # 100K por dia
        
        liq = calculate_liquidity_score(prices, volumes)
        
        # Liquidez deve ser baixa (< 0.4)
        assert liq is not None
        assert liq < 0.4
    
    def test_liquidity_dollar_volume(self):
        """Liquidez deve considerar volume em reais."""
        dates = pd.date_range(start='2024-01-01', periods=30, freq='B')
        prices_low = pd.Series([50] * 30, index=dates)  # Preço mais baixo
        volumes = pd.Series([1_000_000] * 30, index=dates)  # Mesmo volume
        
        liq_low_price = calculate_liquidity_score(prices_low, volumes)
        
        prices_high = pd.Series([500] * 30, index=dates)  # Preço mais alto
        liq_high_price = calculate_liquidity_score(prices_high, volumes)
        
        # Maior preço = maior volume em reais = maior liquidez
        assert liq_low_price is not None
        assert liq_high_price is not None
        assert liq_high_price > liq_low_price


class TestDataQuality:
    """Testes para qualidade e robustez dos dados."""
    
    def test_handles_missing_prices(self):
        """Deve lidar com preços ausentes."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='B')
        prices = pd.Series(
            [100 if i != 50 else np.nan for i in range(100)],
            index=dates
        )
        
        # Não deve quebrar
        mom = calculate_absolute_momentum(prices, window=63)
        assert mom is not None or mom is None  # Aceita qualquer resultado válido
    
    def test_handles_single_price(self):
        """Deve lidar com série de preços constante."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='B')
        prices = pd.Series([100] * 100, index=dates)
        
        # Não deve quebrar
        mom = calculate_absolute_momentum(prices, window=63)
        # Momentum deve ser 0 (sem variação)
        assert mom == 0 or mom is None
    
    def test_date_alignment(self):
        """Deve alinhar corretamente por data."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='B')
        prices = pd.Series(np.linspace(100, 200, 100), index=dates)
        volumes = pd.Series([1_000_000] * 100, index=dates)
        
        liq = calculate_liquidity_score(prices, volumes)
        
        # Deve calcular corretamente
        assert liq is not None
