"""Provider multi-fonte com fallback e telemetria por ticker."""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from aim.data_layer.providers.base import BaseDataProvider, DataProviderError
from aim.data_layer.providers.brapi import BrapiProvider
from aim.data_layer.providers.stooq import StooqProvider

logger = logging.getLogger(__name__)


@dataclass
class TickerResult:
    ticker: str
    status: str  # "ok", "partial", "failed"
    source_used: str  # "brapi", "stooq", "none"
    prices_count: int = 0
    attempts: int = 0
    errors: List[str] = field(default_factory=list)
    duration_ms: int = 0


@dataclass
class UpdateReport:
    total: int = 0
    ok: int = 0
    partial: int = 0
    failed: int = 0
    results: List[TickerResult] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""

    @property
    def failed_tickers(self) -> List[str]:
        return [r.ticker for r in self.results if r.status == "failed"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "ok": self.ok,
            "partial": self.partial,
            "failed": self.failed,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "failed_tickers": self.failed_tickers,
            "results": [
                {
                    "ticker": r.ticker,
                    "status": r.status,
                    "source": r.source_used,
                    "prices": r.prices_count,
                    "attempts": r.attempts,
                    "errors": r.errors,
                    "duration_ms": r.duration_ms,
                }
                for r in self.results
            ],
        }


class MultiSourceProvider:
    """Orquestrador de fontes de dados com fallback automatico.

    Ordem de tentativa: brapi -> stooq.
    Registra telemetria por ticker para diagnostico.
    """

    def __init__(self, brapi_token: Optional[str] = None):
        self._providers: List[tuple[str, BaseDataProvider]] = []
        self._init_providers(brapi_token)

    def _init_providers(self, brapi_token: Optional[str]) -> None:
        try:
            self._providers.append(("brapi", BrapiProvider(token=brapi_token)))
        except Exception as e:
            logger.warning("BrapiProvider init failed: %s", e)

        try:
            self._providers.append(("stooq", StooqProvider()))
        except Exception as e:
            logger.warning("StooqProvider init failed: %s", e)

    def get_prices(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> TickerResult:
        """Tenta obter precos de cada provider em ordem, retorna resultado com telemetria."""
        result = TickerResult(ticker=ticker, status="failed", source_used="none")
        t0 = time.monotonic()

        for name, provider in self._providers:
            result.attempts += 1
            try:
                prices = provider.get_prices(ticker, start_date=start_date, end_date=end_date)
                if prices:
                    result.status = "ok"
                    result.source_used = name
                    result.prices_count = len(prices)
                    result._prices = prices  # attach for caller
                    break
                else:
                    result.errors.append(f"{name}: retornou lista vazia")
            except DataProviderError as e:
                result.errors.append(f"{name}: {e}")
            except Exception as e:
                result.errors.append(f"{name}: erro inesperado - {e}")

        result.duration_ms = int((time.monotonic() - t0) * 1000)
        return result

    def fetch_universe(
        self,
        tickers: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> UpdateReport:
        """Busca precos para lista completa de tickers com fallback e telemetria."""
        report = UpdateReport(
            total=len(tickers),
            started_at=datetime.now().isoformat(timespec="seconds"),
        )

        for i, ticker in enumerate(tickers, 1):
            logger.info("[%d/%d] %s", i, len(tickers), ticker)
            result = self.get_prices(ticker, start_date=start_date, end_date=end_date)
            report.results.append(result)

            if result.status == "ok":
                report.ok += 1
                logger.info(
                    "  OK via %s (%d precos, %dms)",
                    result.source_used,
                    result.prices_count,
                    result.duration_ms,
                )
            elif result.status == "partial":
                report.partial += 1
                logger.warning("  PARCIAL: %s", result.errors)
            else:
                report.failed += 1
                logger.error("  FALHA: %s", result.errors)

        report.finished_at = datetime.now().isoformat(timespec="seconds")
        return report

    def get_prices_data(self, result: TickerResult) -> List[Dict[str, Any]]:
        """Extrai lista de precos do resultado."""
        return getattr(result, "_prices", [])

    def close(self) -> None:
        for _, provider in self._providers:
            try:
                provider.close()
            except Exception:
                pass
