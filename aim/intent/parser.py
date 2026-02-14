"""Intent Parser - Converte intenção do usuário em parâmetros de investimento."""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class RiskTolerance(Enum):
    """Níveis de tolerância ao risco."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    SPECULATIVE = "speculative"


class InvestmentHorizon(Enum):
    """Horizontes de investimento."""
    SHORT_TERM = "short_term"      # Dias/semanas
    MEDIUM_TERM = "medium_term"    # Meses
    LONG_TERM = "long_term"        # Anos


class ObjectiveType(Enum):
    """Tipos de objetivo de investimento."""
    RETURN = "return"              # Alto retorno
    PROTECTION = "protection"        # Preservação de capital
    INCOME = "income"                # Renda/dividendos
    SPECULATION = "speculation"      # Especulação/alta volatilidade
    BALANCED = "balanced"          # Balanceado


@dataclass
class InvestmentIntent:
    """Representação estruturada da intenção do usuário."""
    
    # Extraído do prompt
    objective: ObjectiveType
    horizon: InvestmentHorizon
    risk_tolerance: RiskTolerance
    
    # Regime definido pelo usuário (override no regime de mercado)
    user_regime: str  # 'RISK_ON_STRONG', 'RISK_ON', 'TRANSITION', 'RISK_OFF', 'RISK_OFF_STRONG'
    
    # Parâmetros calculados
    max_volatility: float          # Volatilidade máxima aceitável (anualizada)
    max_drawdown: float           # Drawdown máximo aceitável
    target_return: Optional[float]  # Retorno alvo (se especificado)
    
    # Fatores prioritários (pesos serão ajustados)
    priority_factors: List[str]     # ['momentum', 'value', 'quality', etc.]
    
    # Constraints
    min_liquidity: float          # Score mínimo de liquidez
    max_concentration: float      # Máx concentração por ativo
    use_stop_loss: bool           # Usar stop loss?
    rebalance_frequency: str      # 'daily', 'weekly', 'monthly'
    
    # Metadados
    raw_prompt: str              # Prompt original
    confidence: float             # Confiança da interpretação (0-1)


class IntentParser:
    """Parser de intenção de investimento."""
    
    # Palavras-chave para cada categoria
    OBJECTIVE_KEYWORDS = {
        ObjectiveType.RETURN: [
            'retorno', 'return', 'crescer', 'crescimento', 'valorização',
            'alto retorno', 'alta performance', 'performance', 'lucro',
            'ganho', 'ganhar', 'multiplicar', 'appreciation', 'growth'
        ],
        ObjectiveType.PROTECTION: [
            'proteção', 'proteger', 'protecao', 'preservar', 'preservação',
            'segurança', 'seguro', 'defesa', 'defensivo', 'capital',
            'conservador', 'safe', 'protection', 'preserve', 'defensive'
        ],
        ObjectiveType.INCOME: [
            'renda', 'dividendo', 'dividendos', 'proventos', 'juros',
            'rendimento', 'yield', 'income', 'dividend', 'receita'
        ],
        ObjectiveType.SPECULATION: [
            'especulação', 'especular', 'especulacao', 'trade', 'trading',
            'curto prazo', 'curto', 'swing', 'daytrade', 'day trade',
            'alavancagem', 'alta volatilidade', 'speculation', 'speculative'
        ],
        ObjectiveType.BALANCED: [
            'balanceado', 'equilibrado', 'moderado', 'misto',
            'diversificado', 'balanced', 'moderate', 'mixed'
        ],
    }
    
    HORIZON_KEYWORDS = {
        InvestmentHorizon.SHORT_TERM: [
            'curto', 'curto prazo', 'dias', 'semanas', 'semana', 'dia',
            '30 dias', '60 dias', '90 dias', 'short', 'short term',
            'quick', 'fast', 'rapid', 'day', 'week'
        ],
        InvestmentHorizon.MEDIUM_TERM: [
            'médio', 'medio', 'médio prazo', 'medio prazo', 'meses', 'mes',
            '6 meses', '12 meses', '1 ano', 'medium', 'medium term',
            'months', 'semester'
        ],
        InvestmentHorizon.LONG_TERM: [
            'longo', 'longo prazo', 'anos', 'ano', 'longo prazo',
            '2 anos', '3 anos', '5 anos', '10 anos', 'long', 'long term',
            'years', 'buy and hold', 'buy & hold', 'hold'
        ],
    }
    
    RISK_KEYWORDS = {
        RiskTolerance.CONSERVATIVE: [
            'conservador', 'baixo risco', 'seguro', 'protegido',
            'conservative', 'low risk', 'safe', 'cautious'
        ],
        RiskTolerance.MODERATE: [
            'moderado', 'médio risco', 'equilibrado', 'balanceado',
            'moderate', 'medium risk', 'balanced'
        ],
        RiskTolerance.AGGRESSIVE: [
            'agressivo', 'alto risco', 'arriscado', 'ousado',
            'aggressive', 'high risk', 'risky', 'bold'
        ],
        RiskTolerance.SPECULATIVE: [
            'especulativo', 'especulação', 'muito arriscado', 'alavancado',
            'speculative', 'very risky', 'high leverage', 'extreme',
            'aceitando alto risco'
        ],
    }
    
    # Mapeamento de objetivo + horizonte → parâmetros
    PARAMETER_MAP = {
        # (objective, horizon) → config
        (ObjectiveType.RETURN, InvestmentHorizon.SHORT_TERM): {
            'max_volatility': 0.40,
            'max_drawdown': 0.25,
            'priority_factors': ['momentum', 'volatility'],
            'min_liquidity': 0.7,
            'max_concentration': 0.25,
            'use_stop_loss': True,
            'rebalance_frequency': 'weekly',
        },
        (ObjectiveType.RETURN, InvestmentHorizon.MEDIUM_TERM): {
            'max_volatility': 0.30,
            'max_drawdown': 0.20,
            'priority_factors': ['momentum', 'value', 'quality'],
            'min_liquidity': 0.6,
            'max_concentration': 0.20,
            'use_stop_loss': True,
            'rebalance_frequency': 'monthly',
        },
        (ObjectiveType.RETURN, InvestmentHorizon.LONG_TERM): {
            'max_volatility': 0.25,
            'max_drawdown': 0.15,
            'priority_factors': ['value', 'quality', 'momentum'],
            'min_liquidity': 0.5,
            'max_concentration': 0.15,
            'use_stop_loss': False,
            'rebalance_frequency': 'quarterly',
        },
        (ObjectiveType.PROTECTION, InvestmentHorizon.SHORT_TERM): {
            'max_volatility': 0.10,
            'max_drawdown': 0.05,
            'priority_factors': ['quality', 'liquidity'],
            'min_liquidity': 0.9,
            'max_concentration': 0.10,
            'use_stop_loss': True,
            'rebalance_frequency': 'weekly',
        },
        (ObjectiveType.PROTECTION, InvestmentHorizon.MEDIUM_TERM): {
            'max_volatility': 0.12,
            'max_drawdown': 0.08,
            'priority_factors': ['quality', 'value', 'liquidity'],
            'min_liquidity': 0.8,
            'max_concentration': 0.12,
            'use_stop_loss': True,
            'rebalance_frequency': 'monthly',
        },
        (ObjectiveType.PROTECTION, InvestmentHorizon.LONG_TERM): {
            'max_volatility': 0.15,
            'max_drawdown': 0.10,
            'priority_factors': ['quality', 'value'],
            'min_liquidity': 0.7,
            'max_concentration': 0.10,
            'use_stop_loss': False,
            'rebalance_frequency': 'quarterly',
        },
        (ObjectiveType.INCOME, InvestmentHorizon.MEDIUM_TERM): {
            'max_volatility': 0.15,
            'max_drawdown': 0.10,
            'priority_factors': ['value', 'quality'],
            'min_liquidity': 0.7,
            'max_concentration': 0.15,
            'use_stop_loss': True,
            'rebalance_frequency': 'monthly',
        },
        (ObjectiveType.INCOME, InvestmentHorizon.LONG_TERM): {
            'max_volatility': 0.18,
            'max_drawdown': 0.12,
            'priority_factors': ['value', 'quality'],
            'min_liquidity': 0.6,
            'max_concentration': 0.12,
            'use_stop_loss': False,
            'rebalance_frequency': 'quarterly',
        },
        (ObjectiveType.SPECULATION, InvestmentHorizon.SHORT_TERM): {
            'max_volatility': 0.50,
            'max_drawdown': 0.35,
            'priority_factors': ['momentum', 'volatility'],
            'min_liquidity': 0.6,
            'max_concentration': 0.30,
            'use_stop_loss': True,
            'rebalance_frequency': 'daily',
        },
        (ObjectiveType.BALANCED, InvestmentHorizon.MEDIUM_TERM): {
            'max_volatility': 0.20,
            'max_drawdown': 0.12,
            'priority_factors': ['momentum', 'value', 'quality'],
            'min_liquidity': 0.6,
            'max_concentration': 0.15,
            'use_stop_loss': True,
            'rebalance_frequency': 'monthly',
        },
    }
    
    def parse(self, prompt: str) -> InvestmentIntent:
        """
        Converte prompt do usuário em intenção estruturada.
        
        Args:
            prompt: Texto do usuário descrevendo objetivo
            
        Returns:
            InvestmentIntent com parâmetros calculados
        """
        prompt_lower = prompt.lower()
        
        # 1. Detectar objetivo
        objective = self._detect_objective(prompt_lower)
        
        # 2. Detectar horizonte
        horizon = self._detect_horizon(prompt_lower)
        
        # 3. Detectar tolerância ao risco (ou inferir do objetivo)
        risk_tolerance = self._detect_risk_tolerance(prompt_lower, objective)
        
        # 4. Extrair retorno alvo (se mencionado)
        target_return = self._extract_target_return(prompt_lower)
        
        # 5. Buscar parâmetros base
        params = self._get_parameters(objective, horizon, risk_tolerance)
        
        # 6. Ajustar por tolerância de risco
        params = self._adjust_by_risk_tolerance(params, risk_tolerance)
        
        # 7. Calcular confiança da interpretação
        confidence = self._calculate_confidence(
            prompt_lower, objective, horizon, risk_tolerance
        )
        
        # Mapear tolerância de risco para regime do usuário (override)
        regime_map = {
            RiskTolerance.CONSERVATIVE: 'RISK_OFF',
            RiskTolerance.MODERATE: 'TRANSITION',
            RiskTolerance.AGGRESSIVE: 'RISK_ON',
            RiskTolerance.SPECULATIVE: 'RISK_ON_STRONG',
        }
        user_regime = regime_map.get(risk_tolerance, 'TRANSITION')
        
        return InvestmentIntent(
            objective=objective,
            horizon=horizon,
            risk_tolerance=risk_tolerance,
            user_regime=user_regime,
            max_volatility=params['max_volatility'],
            max_drawdown=params['max_drawdown'],
            target_return=target_return,
            priority_factors=params['priority_factors'],
            min_liquidity=params['min_liquidity'],
            max_concentration=params['max_concentration'],
            use_stop_loss=params['use_stop_loss'],
            rebalance_frequency=params['rebalance_frequency'],
            raw_prompt=prompt,
            confidence=confidence,
        )
    
    def _detect_objective(self, prompt: str) -> ObjectiveType:
        """Detecta objetivo principal do prompt."""
        scores = {obj: 0 for obj in ObjectiveType}
        
        for obj, keywords in self.OBJECTIVE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in prompt:
                    scores[obj] += 1
        
        # Se nenhum detectado, usar RETURN como default
        if max(scores.values()) == 0:
            return ObjectiveType.RETURN
        
        return max(scores, key=scores.get)
    
    def _detect_horizon(self, prompt: str) -> InvestmentHorizon:
        """Detecta horizonte de investimento."""
        scores = {hor: 0 for hor in InvestmentHorizon}
        
        for hor, keywords in self.HORIZON_KEYWORDS.items():
            for keyword in keywords:
                if keyword in prompt:
                    scores[hor] += 1
        
        # Extrair números seguidos de "dias", "meses", "anos"
        # Regex para capturar padrões como "30 dias", "6 meses", "2 anos"
        patterns = [
            (r'(\d+)\s*dias?', InvestmentHorizon.SHORT_TERM),
            (r'(\d+)\s*semanas?', InvestmentHorizon.SHORT_TERM),
            (r'(\d+)\s*m[êe]s', InvestmentHorizon.MEDIUM_TERM),
            (r'(\d+)\s*anos?', InvestmentHorizon.LONG_TERM),
        ]
        
        for pattern, horizon in patterns:
            if re.search(pattern, prompt):
                scores[horizon] += 2  # Peso maior para números explícitos
        
        # Default: MEDIUM_TERM
        if max(scores.values()) == 0:
            return InvestmentHorizon.MEDIUM_TERM
        
        return max(scores, key=scores.get)
    
    def _detect_risk_tolerance(
        self,
        prompt: str,
        objective: ObjectiveType
    ) -> RiskTolerance:
        """Detecta tolerância ao risco."""
        scores = {risk: 0 for risk in RiskTolerance}
        
        for risk, keywords in self.RISK_KEYWORDS.items():
            for keyword in keywords:
                if keyword in prompt:
                    scores[risk] += 1
        
        # Se detectado explicitamente, usar
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        
        # Senão, inferir do objetivo
        risk_by_objective = {
            ObjectiveType.RETURN: RiskTolerance.AGGRESSIVE,
            ObjectiveType.PROTECTION: RiskTolerance.CONSERVATIVE,
            ObjectiveType.INCOME: RiskTolerance.MODERATE,
            ObjectiveType.SPECULATION: RiskTolerance.SPECULATIVE,
            ObjectiveType.BALANCED: RiskTolerance.MODERATE,
        }
        
        return risk_by_objective.get(objective, RiskTolerance.MODERATE)
    
    def _extract_target_return(self, prompt: str) -> Optional[float]:
        """Extrai retorno alvo se mencionado."""
        # Padrões: "10%", "10 por cento", "dez por cento", "10 ao ano"
        patterns = [
            r'(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*por\s*cento',
            r'(\d+(?:\.\d+)?)\s*(?:a|ao)\s*(?:ano|m[eê]s)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, prompt)
            if match:
                value = float(match.group(1))
                # Normalizar para decimal (10% → 0.10)
                if value > 1:  # Provavelmente percentual (10 ao invés de 0.10)
                    value = value / 100
                return value
        
        return None
    
    def _get_parameters(
        self,
        objective: ObjectiveType,
        horizon: InvestmentHorizon,
        risk_tolerance: RiskTolerance
    ) -> Dict[str, Any]:
        """Busca parâmetros base para a combinação."""
        key = (objective, horizon)
        
        # Usar default se combinação não existir
        if key not in self.PARAMETER_MAP:
            # Fallback para BALANCED/MEDIUM_TERM
            key = (ObjectiveType.BALANCED, InvestmentHorizon.MEDIUM_TERM)
        
        params = self.PARAMETER_MAP[key].copy()
        
        # Ajustar max_volatility pela tolerância de risco
        volatility_adjustments = {
            RiskTolerance.CONSERVATIVE: 0.7,
            RiskTolerance.MODERATE: 1.0,
            RiskTolerance.AGGRESSIVE: 1.3,
            RiskTolerance.SPECULATIVE: 1.6,
        }
        
        adjustment = volatility_adjustments.get(risk_tolerance, 1.0)
        params['max_volatility'] = min(0.50, params['max_volatility'] * adjustment)
        params['max_drawdown'] = min(0.40, params['max_drawdown'] * adjustment)
        
        return params
    
    def _adjust_by_risk_tolerance(
        self,
        params: Dict[str, Any],
        risk_tolerance: RiskTolerance
    ) -> Dict[str, Any]:
        """Ajusta parâmetros pela tolerância ao risco."""
        # Conservadores: mais qualidade, menos volatilidade
        # Agressivos: mais momentum, menos qualidade
        
        if risk_tolerance == RiskTolerance.CONSERVATIVE:
            # Adicionar qualidade se não estiver
            if 'quality' not in params['priority_factors']:
                params['priority_factors'].insert(0, 'quality')
        
        elif risk_tolerance == RiskTolerance.AGGRESSIVE:
            # Priorizar momentum
            if 'momentum' in params['priority_factors']:
                params['priority_factors'].remove('momentum')
            params['priority_factors'].insert(0, 'momentum')
        
        return params
    
    def _calculate_confidence(
        self,
        prompt: str,
        objective: ObjectiveType,
        horizon: InvestmentHorizon,
        risk_tolerance: RiskTolerance
    ) -> float:
        """Calcula confiança da interpretação."""
        confidence = 0.5  # Base
        
        # +0.2 se objetivo detectado explicitamente
        for keywords in self.OBJECTIVE_KEYWORDS[objective]:
            if keywords in prompt:
                confidence += 0.2
                break
        
        # +0.2 se horizonte detectado explicitamente
        for keywords in self.HORIZON_KEYWORDS[horizon]:
            if keywords in prompt:
                confidence += 0.2
                break
        
        # +0.1 se tolerância de risco explícita
        for keywords in self.RISK_KEYWORDS[risk_tolerance]:
            if keywords in prompt:
                confidence += 0.1
                break
        
        return min(1.0, confidence)


# Instância global
parser = IntentParser()


def parse_intent(prompt: str) -> InvestmentIntent:
    """Função conveniência para parsear intenção."""
    return parser.parse(prompt)


# Exemplos de uso para teste
if __name__ == "__main__":
    test_prompts = [
        "Quero alto retorno em 30 dias",
        "Proteger meu capital conservadoramente",
        "Renda passiva com dividendos por 2 anos",
        "Especular no curto prazo aceitando alto risco",
        "Crescimento balanceado para longo prazo",
    ]
    
    for prompt in test_prompts:
        intent = parse_intent(prompt)
        print(f"\nPrompt: '{prompt}'")
        print(f"  Objetivo: {intent.objective.value}")
        print(f"  Horizonte: {intent.horizon.value}")
        print(f"  Risco: {intent.risk_tolerance.value}")
        print(f"  Fatores: {intent.priority_factors}")
        print(f"  Max Vol: {intent.max_volatility:.1%}")
        print(f"  Max DD: {intent.max_drawdown:.1%}")
        print(f"  Confiança: {intent.confidence:.0%}")
