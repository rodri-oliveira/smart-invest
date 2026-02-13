"""Classe base para providers de dados."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import httpx


class DataProviderError(Exception):
    """Exceção base para erros de providers."""
    pass


class APIError(DataProviderError):
    """Erro na chamada à API."""
    pass


class RateLimitError(DataProviderError):
    """Limite de requisições excedido."""
    pass


class DataValidationError(DataProviderError):
    """Dados retornados são inválidos."""
    pass


class BaseDataProvider(ABC):
    """Classe base para todos os providers de dados."""

    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        """Lazy loading do cliente HTTP."""
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def close(self) -> None:
        """Fecha conexão HTTP."""
        if self._client:
            self._client.close()
            self._client = None

    @abstractmethod
    def get_prices(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retorna preços históricos OHLCV.

        Args:
            ticker: Código do ativo
            start_date: Data inicial (YYYY-MM-DD)
            end_date: Data final (YYYY-MM-DD)

        Returns:
            Lista de dicionários com dados OHLCV
        """
        pass

    @abstractmethod
    def get_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """
        Retorna dados fundamentalistas.

        Args:
            ticker: Código do ativo

        Returns:
            Dicionário com indicadores fundamentalistas
        """
        pass

    def _make_request(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Faz requisição HTTP com retry.

        Args:
            url: URL da requisição
            params: Query parameters
            headers: Headers HTTP

        Returns:
            JSON da resposta

        Raises:
            APIError: Em caso de erro na API
            RateLimitError: Se atingir limite de requisições
        """
        for attempt in range(self.max_retries):
            try:
                response = self.client.get(url, params=params, headers=headers)

                if response.status_code == 429:
                    raise RateLimitError("Limite de requisições excedido")

                if response.status_code == 404:
                    raise APIError(f"Recurso não encontrado: {url}")

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                if attempt == self.max_retries - 1:
                    raise APIError(f"Erro HTTP {e.response.status_code}: {e}")
                continue

            except httpx.RequestError as e:
                if attempt == self.max_retries - 1:
                    raise APIError(f"Erro de conexão: {e}")
                continue

        raise APIError("Max retries exceeded")
