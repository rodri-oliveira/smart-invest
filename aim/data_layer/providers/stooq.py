"""Provider fallback via Stooq (sem chave) para precos diarios."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from aim.data_layer.providers.base import (
    APIError,
    BaseDataProvider,
    DataValidationError,
)


class StooqProvider(BaseDataProvider):
    """Provider de fallback para precos via Stooq CSV."""

    def __init__(self):
        super().__init__(timeout=20, max_retries=2)
        self.base_url = "https://stooq.com/q/d/l/"

    @staticmethod
    def _to_stooq_symbol(ticker: str) -> str:
        return f"{ticker.lower()}.br"

    @staticmethod
    def _parse_date(value: str) -> str:
        # Esperado: YYYY-MM-DD
        return value.strip()

    def get_prices(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        symbol = self._to_stooq_symbol(ticker)
        params = {"s": symbol, "i": "d"}

        try:
            response = self.client.get(self.base_url, params=params)
            if response.status_code == 404:
                raise APIError(f"Nenhum recurso para {ticker} em stooq")
            response.raise_for_status()

            content = response.text.strip()
            if not content or "No data" in content or "404 Not Found" in content:
                raise DataValidationError(f"Sem dados para {ticker} no stooq")

            lines = [line.strip() for line in content.splitlines() if line.strip()]
            if len(lines) <= 1:
                raise DataValidationError(f"CSV sem candles para {ticker}")

            # Header esperado: Date,Open,High,Low,Close,Volume
            parsed: List[Dict[str, Any]] = []
            for line in lines[1:]:
                parts = line.split(",")
                if len(parts) < 6:
                    continue

                date_str = self._parse_date(parts[0])
                if not date_str:
                    continue

                if start_date and date_str < start_date:
                    continue
                if end_date and date_str > end_date:
                    continue

                # Alguns dias podem vir com valores vazios
                try:
                    open_v = float(parts[1])
                    high_v = float(parts[2])
                    low_v = float(parts[3])
                    close_v = float(parts[4])
                    vol_v = int(float(parts[5]))
                except (TypeError, ValueError):
                    continue

                parsed.append(
                    {
                        "ticker": ticker.upper(),
                        "date": date_str,
                        "open": open_v,
                        "high": high_v,
                        "low": low_v,
                        "close": close_v,
                        "volume": vol_v,
                        "adjusted_close": close_v,
                        "source": "stooq",
                    }
                )

            if not parsed:
                raise DataValidationError(f"Sem candles validos para {ticker} no stooq")

            return parsed
        except APIError:
            raise
        except Exception as exc:
            raise DataValidationError(f"Erro processando {ticker} no stooq: {exc}")

    def get_fundamentals(self, ticker: str) -> Dict[str, Any]:
        # Stooq nao oferece fundamentos detalhados neste endpoint.
        raise DataValidationError(f"Fundamentos indisponiveis no stooq para {ticker}")
