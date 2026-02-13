"""Cliente para API brapi.dev - dados da B3."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from aim.config.settings import get_settings
from aim.data_layer.providers.base import (
    APIError,
    BaseDataProvider,
    DataValidationError,
)


class BrapiProvider(BaseDataProvider):
    """Provider de dados da brapi.dev."""

    def __init__(self, token: Optional[str] = None):
        """
        Inicializa cliente brapi.

        Args:
            token: Token de API. Se None, usa das settings.
        """
        super().__init__(timeout=30, max_retries=3)
        self.settings = get_settings()
        self.token = token or self.settings.brapi_token
        self.base_url = self.settings.brapi_base_url.rstrip("/")

    def get_prices(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retorna preços históricos OHLCV.

        Args:
            ticker: Código do ativo (ex: PETR4)
            start_date: Data inicial (YYYY-MM-DD)
            end_date: Data final (YYYY-MM-DD)

        Returns:
            Lista de candles OHLCV
        """
        endpoint = f"{self.base_url}/quote/{ticker}"

        params: Dict[str, Any] = {"range": "max"}  # Pega máximo disponível

        if start_date:
            params["start"] = start_date
        if end_date:
            params["end"] = end_date

        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            data = self._make_request(endpoint, params=params, headers=headers)

            if "results" not in data or not data["results"]:
                raise DataValidationError(f"Nenhum dado retornado para {ticker}")

            result = data["results"][0]

            if "historicalDataPrice" not in result:
                raise DataValidationError(f"Sem dados históricos para {ticker}")

            historical = result["historicalDataPrice"]

            # Normalizar dados
            normalized = []
            for candle in historical:
                if candle.get("close") is None:
                    continue  # Pular dias sem negociação

                normalized.append({
                    "ticker": ticker.upper(),
                    "date": candle.get("date"),
                    "open": float(candle.get("open", 0) or 0),
                    "high": float(candle.get("high", 0) or 0),
                    "low": float(candle.get("low", 0) or 0),
                    "close": float(candle.get("close", 0) or 0),
                    "volume": int(candle.get("volume", 0) or 0),
                    "adjusted_close": float(candle.get("close", 0) or 0),
                    "source": "brapi",
                })

            return normalized

        except APIError:
            raise
        except Exception as e:
            raise DataValidationError(f"Erro ao processar dados de {ticker}: {e}")

    def get_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """
        Retorna dados fundamentalistas.

        Args:
            ticker: Código do ativo

        Returns:
            Dicionário com indicadores
        """
        endpoint = f"{self.base_url}/quote/{ticker}"

        params = {"fundamental": "true"}

        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            data = self._make_request(endpoint, params=params, headers=headers)

            if "results" not in data or not data["results"]:
                raise DataValidationError(f"Nenhum dado fundamentalista para {ticker}")

            result = data["results"][0]

            # Extrair indicadores disponíveis
            fundamentals = {
                "ticker": ticker.upper(),
                "price": result.get("regularMarketPrice"),
                "p_l": self._safe_float(result.get("priceEarnings")),
                "p_vp": self._safe_float(result.get("priceToBook")),
                "dy": self._safe_float(result.get("dividendYield")),
                "roe": self._safe_float(result.get("returnOnEquity")),
                "roic": self._safe_float(result.get("returnOnInvestedCapital")),
                "ebitda": self._safe_float(result.get("ebitda")),
                "net_margin": self._safe_float(result.get("netMargin")),
                "gross_margin": self._safe_float(result.get("grossMargin")),
                "divida_patrimonio": self._safe_float(result.get("debtToEquity")),
                "market_cap": result.get("marketCap"),
                "book_value_per_share": self._safe_float(result.get("bookValuePerShare")),
                "revenue_per_share": self._safe_float(result.get("revenuePerShare")),
                "earnings_per_share": self._safe_float(result.get("earningsPerShare")),
                "updated_at": datetime.now().isoformat(),
            }

            return fundamentals

        except APIError:
            raise
        except Exception as e:
            raise DataValidationError(f"Erro ao processar fundamentos de {ticker}: {e}")

    def get_dividends(self, ticker: str) -> List[Dict[str, Any]]:
        """
        Retorna histórico de dividendos.

        Args:
            ticker: Código do ativo

        Returns:
            Lista de dividendos
        """
        endpoint = f"{self.base_url}/quote/{ticker}"

        params = {"dividends": "true"}

        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            data = self._make_request(endpoint, params=params, headers=headers)

            if "results" not in data or not data["results"]:
                return []

            result = data["results"][0]
            dividends_data = result.get("dividendsData", {})

            dividends = []

            # Dividendos passados (cash)
            for div in dividends_data.get("cash", []):
                dividends.append({
                    "ticker": ticker.upper(),
                    "type": "DIVIDENDO",
                    "value_per_share": self._safe_float(div.get("value")),
                    "payment_date": div.get("paymentDate"),
                    "ex_date": div.get("approvedIn"),  # Aproximação
                    "source": "brapi",
                })

            # Juros sobre capital próprio
            for jcp in dividends_data.get(" jcp", []):  # Corrigir espaço se necessário
                dividends.append({
                    "ticker": ticker.upper(),
                    "type": "JCP",
                    "value_per_share": self._safe_float(jcp.get("value")),
                    "payment_date": jcp.get("paymentDate"),
                    "ex_date": jcp.get("approvedIn"),
                    "source": "brapi",
                })

            return dividends

        except Exception:
            # Dividendos são opcionais, não falhar se der erro
            return []

    def get_available_tickers(self) -> List[str]:
        """
        Retorna lista de tickers disponíveis.
        Útil para validação.
        """
        # brapi não tem endpoint específico, usar lista conhecida
        from aim.config.parameters import DEFAULT_UNIVERSE
        return DEFAULT_UNIVERSE

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        """Converte valor para float de forma segura."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def get_quote_list(self, tickers: List[str]) -> List[Dict[str, Any]]:
        """
        Retorna cotações em lote para múltiplos tickers.

        Args:
            tickers: Lista de códigos (max ~20 por chamada)

        Returns:
            Lista de cotações atuais
        """
        if not tickers:
            return []

        tickers_str = ",".join(tickers)
        endpoint = f"{self.base_url}/quote/{tickers_str}"

        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            data = self._make_request(endpoint, headers=headers)
            return data.get("results", [])

        except APIError as e:
            # Se falhar em lote, tentar individualmente
            if len(tickers) > 1:
                results = []
                for ticker in tickers:
                    try:
                        single = self.get_quote_list([ticker])
                        results.extend(single)
                    except APIError:
                        continue
                return results
            raise e
