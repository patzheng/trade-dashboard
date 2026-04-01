from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class Metric(BaseModel):
    label: str
    value: str
    hint: str


class SymbolHighlight(BaseModel):
    symbol: str
    value: str
    change: str


class EquityPoint(BaseModel):
    label: str
    value: float


class TradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    pnl: Decimal
    venue: str
    status: str
    executed_at: datetime


class OverviewResponse(BaseModel):
    updated_at: datetime
    metrics: list[Metric]
    top_symbols: list[SymbolHighlight]
    equity_curve: list[EquityPoint]
