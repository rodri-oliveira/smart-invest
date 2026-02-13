"""Cliente para API do Banco Central do Brasil (BCB)."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from aim.data_layer.providers.base import APIError, BaseDataProvider, DataValidationError


class BCBProvider(BaseDataProvider):
    """Provider de dados macroeconômicos do Banco Central."""

    # Códigos das séries no SGS (Sistema Gerenciador de Séries)
    SERIES = {
        # Taxas de juros
        "SELIC_META": 432,  # Taxa SELIC meta
        "SELIC_REAL": 4189,  # Taxa SELIC efetiva
        "CDI": 12,  # Taxa CDI
        "CDI_ACUMULADO_21": 4390,  # CDI acumulado 21 dias
        
        # Inflação
        "IPCA": 433,  # IPCA mensal
        "IPCA_12M": 433,  # IPCA acumulado 12 meses (usar endpoint diferente)
        "IGPM": 189,  # IGP-M mensal
        "IGPM_10D": 7448,  # IGP-M 10 dias
        
        # Câmbio
        "USD_PTAX": 1,  # Taxa de câmbio USD (compra)
        "USD_PTAX_VENDA": 10813,  # Taxa de câmbio USD (venda)
        "EUR_PTAX": 216,  # Taxa de câmbio EUR
        
        # Mercado de trabalho
        "DESEMPREGO": 24369,  # Taxa de desemprego
        
        # Atividade econômica
        "PIB_MENSAL": 4380,  # IBC-Br (proxy do PIB mensal)
        
        # Expectativas de mercado (Focus)
        # Nota: Usar endpoint diferente
    }

    BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs"

    def __init__(self):
        super().__init__(timeout=60, max_retries=3)  # BCB pode ser lento

    def get_series(
        self,
        series_code: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retorna série temporal do BCB.

        Args:
            series_code: Código da série no SGS
            start_date: Data inicial (DD/MM/YYYY)
            end_date: Data final (DD/MM/YYYY)

        Returns:
            Lista de {data, valor}
        """
        url = f"{self.BASE_URL}.{series_code}/dados"

        params = {}
        if start_date:
            params["dataInicial"] = start_date
        if end_date:
            params["dataFinal"] = end_date

        try:
            data = self._make_request(url, params=params)

            # Normalizar dados
            normalized = []
            for item in data:
                try:
                    # Converter data de DD/MM/YYYY para YYYY-MM-DD
                    date_str = item.get("data", "")
                    if date_str:
                        day, month, year = date_str.split("/")
                        normalized_date = f"{year}-{month}-{day}"
                    else:
                        continue

                    # Converter valor
                    value_str = item.get("valor", "0")
                    # Remover pontos de milhar e converter vírgula para ponto
                    value_str = value_str.replace(".", "").replace(",", ".")
                    value = float(value_str) if value_str else 0.0

                    normalized.append({
                        "date": normalized_date,
                        "value": value,
                        "series_code": series_code,
                    })

                except (ValueError, IndexError) as e:
                    continue  # Pular itens mal formatados

            return normalized

        except APIError:
            raise
        except Exception as e:
            raise DataValidationError(f"Erro ao processar série {series_code}: {e}")

    def get_indicator(
        self,
        indicator: str,
        days: int = 365,
    ) -> List[Dict[str, Any]]:
        """
        Retorna indicador por nome.

        Args:
            indicator: Nome do indicador (ex: "SELIC", "IPCA", "USD")
            days: Quantos dias de histórico

        Returns:
            Lista de {date, value}
        """
        # Mapear nome para código
        code = self.SERIES.get(f"{indicator}_META") or self.SERIES.get(indicator)
        
        if not code:
            raise DataValidationError(f"Indicador desconhecido: {indicator}")

        # Calcular datas
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Formato DD/MM/YYYY
        start_str = start_date.strftime("%d/%m/%Y")
        end_str = end_date.strftime("%d/%m/%Y")

        return self.get_series(code, start_str, end_str)

    def get_selic_meta(self, days: int = 90) -> List[Dict[str, Any]]:
        """Retorna série da taxa SELIC meta."""
        return self.get_indicator("SELIC_META", days)

    def get_cdi(self, days: int = 90) -> List[Dict[str, Any]]:
        """Retorna série do CDI."""
        return self.get_indicator("CDI", days)

    def get_ipca(self, months: int = 24) -> List[Dict[str, Any]]:
        """
        Retorna série do IPCA mensal.
        Nota: IPCA é mensal, então months = aprox. months * 30 dias
        """
        return self.get_indicator("IPCA", months * 30)

    def get_usd_exchange(self, days: int = 90) -> List[Dict[str, Any]]:
        """Retorna série da taxa de câmbio USD/BRL."""
        return self.get_indicator("USD_PTAX", days)

    def get_all_macro_indicators(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retorna todos os indicadores macro principais.
        Útil para popular o banco de dados.
        """
        indicators = {}

        try:
            indicators["SELIC"] = self.get_selic_meta(days=365)
        except Exception as e:
            indicators["SELIC"] = []
            print(f"Erro ao buscar SELIC: {e}")

        try:
            indicators["CDI"] = self.get_cdi(days=365)
        except Exception as e:
            indicators["CDI"] = []
            print(f"Erro ao buscar CDI: {e}")

        try:
            indicators["IPCA"] = self.get_ipca(months=24)
        except Exception as e:
            indicators["IPCA"] = []
            print(f"Erro ao buscar IPCA: {e}")

        try:
            indicators["USD_BRL"] = self.get_usd_exchange(days=365)
        except Exception as e:
            indicators["USD_BRL"] = []
            print(f"Erro ao buscar USD: {e}")

        try:
            indicators["IGPM"] = self.get_indicator("IGPM", days=365)
        except Exception as e:
            indicators["IGPM"] = []
            print(f"Erro ao buscar IGP-M: {e}")

        return indicators

    def get_prices(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """BCB não fornece preços de ações - usar brapi."""
        raise NotImplementedError("BCB não fornece preços de ações")

    def get_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """BCB não fornece fundamentos - usar brapi."""
        raise NotImplementedError("BCB não fornece dados fundamentalistas")
