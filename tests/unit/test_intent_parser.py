"""Testes do parser de intenção."""

from aim.intent.parser import (
    InvestmentHorizon,
    ObjectiveType,
    RiskTolerance,
    parse_intent,
)


class TestIntentParser:
    """Valida extração de objetivo, risco e horizonte."""

    def test_speculative_phrase_should_not_fall_back_to_aggressive(self):
        """Expressão composta deve priorizar SPECULATIVE."""
        intent = parse_intent("Especular aceitando alto risco")

        assert intent.objective == ObjectiveType.SPECULATION
        assert intent.risk_tolerance == RiskTolerance.SPECULATIVE
        assert intent.user_regime == "RISK_ON_STRONG"

    def test_income_prompt_should_map_to_income_objective(self):
        """Prompt de renda deve manter objetivo INCOME."""
        intent = parse_intent("Renda passiva com dividendos")

        assert intent.objective == ObjectiveType.INCOME
        assert intent.user_regime in {"TRANSITION", "RISK_OFF", "RISK_OFF_STRONG"}

    def test_explicit_short_horizon_should_be_detected(self):
        """Horizonte explícito em dias deve virar SHORT_TERM."""
        intent = parse_intent("Quero alto retorno em 30 dias")

        assert intent.horizon == InvestmentHorizon.SHORT_TERM
