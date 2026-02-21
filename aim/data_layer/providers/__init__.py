"""Providers de dados externos."""

from aim.data_layer.providers.base import (
    APIError,
    BaseDataProvider,
    DataProviderError,
    DataValidationError,
    RateLimitError,
)
from aim.data_layer.providers.brapi import BrapiProvider
from aim.data_layer.providers.bcb import BCBProvider
from aim.data_layer.providers.stooq import StooqProvider
from aim.data_layer.providers.multi_source import MultiSourceProvider, UpdateReport, TickerResult

__all__ = [
    "BaseDataProvider",
    "BrapiProvider",
    "BCBProvider",
    "StooqProvider",
    "MultiSourceProvider",
    "UpdateReport",
    "TickerResult",
    "APIError",
    "DataProviderError",
    "DataValidationError",
    "RateLimitError",
]
