from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class Metric(BaseModel):
    label: str
    value: str
    hint: str


class MarketSummary(BaseModel):
    market: str
    label: str
    currency: str
    trade_count: int
    active_symbols: int
    net_pnl: float
    turnover: float
    change_pct: float
    last_sync: datetime


class WatchlistItem(BaseModel):
    symbol: str
    market: str
    label: str
    venue: str
    last_price: float
    change_pct: float
    position_hint: str
    note: str


class RiskMetric(BaseModel):
    label: str
    value: str
    hint: str


class ExposureRow(BaseModel):
    label: str
    market: str
    gross_notional: float
    net_pnl: float
    share_pct: float
    risk: str


class InsightMetric(BaseModel):
    label: str
    value: str
    hint: str
    state: str


class PricePoint(BaseModel):
    timestamp: datetime
    price: float
    ma7: float
    ma21: float


class KeyLevel(BaseModel):
    label: str
    price: float
    note: str
    side: str


class BtcSnapshot(BaseModel):
    symbol: str
    current_price: float
    change_24h: float
    high_24h: float
    low_24h: float
    volume_24h: float
    regime: str
    sentiment: str
    price_series: list[PricePoint]
    onchain: list[InsightMetric]
    technicals: list[InsightMetric]
    levels: list[KeyLevel]


class TradeView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    market: str
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    pnl: Decimal
    venue: str
    status: str
    executed_at: datetime


class DashboardResponse(BaseModel):
    updated_at: datetime
    metrics: list[Metric]
    risk_metrics: list[RiskMetric]
    exposure: list[ExposureRow]
    btc: BtcSnapshot
    markets: list[MarketSummary]
    watchlist: list[WatchlistItem]
    recent_trades: list[TradeView]
    focus_market: str
