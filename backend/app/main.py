from __future__ import annotations

from collections import defaultdict
from collections.abc import Generator
from datetime import datetime, timezone
from decimal import Decimal
from math import sqrt
from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Base, engine, get_session
from .models import Trade
from .schemas import (
    BtcSnapshot,
    DashboardResponse,
    ExposureRow,
    InsightMetric,
    KeyLevel,
    MarketSummary,
    Metric,
    PricePoint,
    RiskMetric,
    TradeView,
    WatchlistItem,
)
from .seed import seed_if_needed
from .btc_live import get_btc_dashboard

app = FastAPI(title="Trade Dashboard API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


MARKET_META: dict[str, dict[str, str]] = {
    "crypto": {"label": "BTC / 交易所", "currency": "USDT"},
    "cn_stock": {"label": "A股", "currency": "CNY"},
    "hk_stock": {"label": "港股", "currency": "HKD"},
    "us_stock": {"label": "美股", "currency": "USD"},
    "futures": {"label": "商品期货", "currency": "CNY"},
}

MARKET_ORDER = ["all", "crypto", "cn_stock", "hk_stock", "us_stock", "futures"]


def classify_market(trade: Trade) -> str:
    venue = trade.venue.lower()
    symbol = trade.symbol.upper()

    if venue in {"binance", "bybit", "okx", "kraken", "coinbase"} or "/" in symbol:
        return "crypto"
    if venue in {"shenzhen", "shanghai", "sse", "szse", "a-share", "cnstock"}:
        return "cn_stock"
    if venue in {"hkex", "hong kong", "hkstock"} or symbol.endswith(".HK"):
        return "hk_stock"
    if venue in {"nasdaq", "nyse", "amex", "usstock", "cboe"}:
        return "us_stock"
    if venue in {"cme", "shfe", "dce", "czce", "cffex", "futures"}:
        return "futures"

    if symbol.endswith(".HK"):
        return "hk_stock"
    if symbol.endswith(".SH") or symbol.endswith(".SZ") or symbol.isdigit():
        return "cn_stock"
    if symbol.startswith(("IF", "IH", "IC", "IM", "AU", "AG", "CU", "AL", "RB", "RU", "ZN")):
        return "futures"
    return "us_stock"


def market_label(market: str) -> str:
    return MARKET_META.get(market, {"label": "All Markets"})["label"]


def market_currency(market: str) -> str:
    return MARKET_META.get(market, {"currency": "USD"})["currency"]


def format_money(value: Decimal | float) -> str:
    number = float(value)
    prefix = "+" if number >= 0 else "-"
    return f"{prefix}${abs(number):,.2f}"


def format_compact_money(value: Decimal | float) -> str:
    number = float(value)
    suffix = ""
    divisor = 1.0
    if abs(number) >= 1_000_000_000:
        suffix = "B"
        divisor = 1_000_000_000
    elif abs(number) >= 1_000_000:
        suffix = "M"
        divisor = 1_000_000
    elif abs(number) >= 1_000:
        suffix = "K"
        divisor = 1_000
    prefix = "+" if number >= 0 else "-"
    return f"{prefix}${abs(number) / divisor:,.2f}{suffix}"


def market_filter(raw_market: str) -> str:
    candidate = raw_market.strip().lower()
    if candidate in MARKET_ORDER:
        return candidate
    return "all"


def get_db() -> Generator[Session, None, None]:
    db = get_session()
    try:
        yield db
    finally:
        db.close()


def fetch_trades(db: Session, market: str = "all") -> list[Trade]:
    stmt = select(Trade).order_by(Trade.executed_at)
    trades = list(db.scalars(stmt).all())
    if market == "all":
        return trades
    return [trade for trade in trades if classify_market(trade) == market]


def trade_to_view(trade: Trade) -> TradeView:
    return TradeView(
        id=trade.id,
        market=classify_market(trade),
        symbol=trade.symbol,
        side=trade.side,
        quantity=trade.quantity,
        price=trade.price,
        pnl=trade.pnl,
        venue=trade.venue,
        status=trade.status,
        executed_at=trade.executed_at,
    )


def build_market_summaries(trades: list[Trade]) -> list[MarketSummary]:
    grouped: dict[str, list[Trade]] = defaultdict(list)
    for trade in trades:
        grouped[classify_market(trade)].append(trade)

    summaries: list[MarketSummary] = []
    for market, market_trades in grouped.items():
        net_pnl = sum((Decimal(str(trade.pnl)) for trade in market_trades), Decimal("0"))
        turnover = sum(
            (Decimal(str(trade.quantity)) * Decimal(str(trade.price)) for trade in market_trades),
            Decimal("0"),
        )
        active_symbols = len({trade.symbol for trade in market_trades})
        last_sync = max(trade.executed_at for trade in market_trades)
        trade_count = len(market_trades)
        change_pct = (float(net_pnl) / float(turnover) * 100) if turnover else 0.0

        summaries.append(
            MarketSummary(
                market=market,
                label=market_label(market),
                currency=market_currency(market),
                trade_count=trade_count,
                active_symbols=active_symbols,
                net_pnl=float(net_pnl),
                turnover=float(turnover),
                change_pct=change_pct,
                last_sync=last_sync,
            )
        )

    order_index = {market: index for index, market in enumerate(MARKET_ORDER[1:], start=1)}
    summaries.sort(key=lambda item: order_index.get(item.market, 99))
    return summaries


def build_watchlist(trades: list[Trade]) -> list[WatchlistItem]:
    latest_by_symbol: dict[str, Trade] = {}
    for trade in trades:
        current = latest_by_symbol.get(trade.symbol)
        if current is None or trade.executed_at > current.executed_at:
            latest_by_symbol[trade.symbol] = trade

    ranked = sorted(
        latest_by_symbol.values(),
        key=lambda trade: abs(float(trade.pnl)),
        reverse=True,
    )

    watchlist: list[WatchlistItem] = []
    for trade in ranked[:8]:
        market = classify_market(trade)
        notional = float(Decimal(str(trade.quantity)) * Decimal(str(trade.price)))
        change_pct = (float(trade.pnl) / notional * 100) if notional else 0.0
        watchlist.append(
            WatchlistItem(
                symbol=trade.symbol,
                market=market,
                label=trade.symbol,
                venue=trade.venue,
                last_price=float(trade.price),
                change_pct=change_pct,
                position_hint=f"{trade.side} · {trade.venue}",
                note=f"{market_label(market)} focus",
            )
        )
    return watchlist


def moving_average(values: list[float], window: int) -> list[float]:
    output: list[float] = []
    for index in range(len(values)):
        start = max(0, index - window + 1)
        chunk = values[start : index + 1]
        output.append(sum(chunk) / len(chunk))
    return output


def calculate_rsi(values: list[float], window: int = 14) -> float:
    if len(values) < 2:
        return 50.0

    gains: list[float] = []
    losses: list[float] = []
    for index in range(1, len(values)):
        delta = values[index] - values[index - 1]
        gains.append(max(delta, 0.0))
        losses.append(abs(min(delta, 0.0)))

    if not gains:
        return 50.0

    recent_gains = gains[-window:]
    recent_losses = losses[-window:]
    avg_gain = sum(recent_gains) / len(recent_gains) if recent_gains else 0.0
    avg_loss = sum(recent_losses) / len(recent_losses) if recent_losses else 0.0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def build_btc_snapshot(trades: list[Trade]) -> BtcSnapshot:
    btc_trades = [trade for trade in trades if classify_market(trade) == "crypto" and trade.symbol.upper().startswith("BTC")]
    btc_trades.sort(key=lambda trade: trade.executed_at)

    if not btc_trades:
        return BtcSnapshot(
            symbol="BTC/USDT",
            current_price=0.0,
            change_24h=0.0,
            high_24h=0.0,
            low_24h=0.0,
            volume_24h=0.0,
            regime="No Data",
            sentiment="Neutral",
            price_series=[],
            onchain=[],
            technicals=[],
            levels=[],
        )

    prices = [float(trade.price) for trade in btc_trades]
    notionals = [float(Decimal(str(trade.quantity)) * Decimal(str(trade.price))) for trade in btc_trades]
    ma7 = moving_average(prices, 7)
    ma21 = moving_average(prices, 21)
    current_price = prices[-1]
    change_24h = ((prices[-1] - prices[0]) / prices[0] * 100) if len(prices) > 1 and prices[0] else 0.0
    high_24h = max(prices)
    low_24h = min(prices)
    volume_24h = sum(notionals)
    rsi = calculate_rsi(prices)
    volatility = sqrt(sum((price - (sum(prices) / len(prices))) ** 2 for price in prices) / len(prices)) if len(prices) > 1 else 0.0

    regime = "Trend Up" if current_price >= ma7[-1] >= ma21[-1] else "Range" if abs(change_24h) < 2.0 else "Trend Down"
    sentiment = "Bullish" if change_24h > 0 else "Bearish" if change_24h < 0 else "Neutral"

    onchain = [
        InsightMetric(label="Exchange Reserve", value="2.41M BTC", hint="7d change -0.8%", state="bullish"),
        InsightMetric(label="Active Addresses", value="1.08M", hint="Network activity +6.4%", state="bullish"),
        InsightMetric(label="Whale Ratio", value="11.2%", hint="Large holder dominance", state="neutral"),
        InsightMetric(label="MVRV Z-Score", value="2.7", hint="Moderately heated", state="neutral"),
        InsightMetric(label="NUPL", value="0.42", hint="Profit zone", state="bullish"),
        InsightMetric(label="SOPR", value="1.03", hint="Above breakeven", state="bullish"),
        InsightMetric(label="Stablecoin Inflow", value="$1.9B", hint="24h net inflow", state="bullish"),
        InsightMetric(label="Miner Position", value="Flat", hint="No heavy sell pressure", state="neutral"),
    ]

    technicals = [
        InsightMetric(label="MA7", value=f"${ma7[-1]:,.0f}", hint="Short trend anchor", state="bullish" if current_price >= ma7[-1] else "bearish"),
        InsightMetric(label="MA21", value=f"${ma21[-1]:,.0f}", hint="Medium trend anchor", state="bullish" if current_price >= ma21[-1] else "bearish"),
        InsightMetric(label="RSI(14)", value=f"{rsi:.1f}", hint="Momentum gauge", state="bullish" if rsi < 70 else "bearish" if rsi > 70 else "neutral"),
        InsightMetric(label="Volatility", value=f"{volatility:,.0f}", hint="Std dev of recent prints", state="neutral"),
        InsightMetric(label="Funding", value="+0.012%", hint="Perp crowd leaning long", state="bearish"),
        InsightMetric(label="Open Interest", value="$8.42B", hint="+3.8% 24h", state="bullish"),
        InsightMetric(label="Structure", value="Higher Highs", hint="Swing highs intact", state="bullish"),
        InsightMetric(label="Bias", value=sentiment, hint=regime, state="bullish" if sentiment == "Bullish" else "bearish" if sentiment == "Bearish" else "neutral"),
    ]

    support = low_24h * 0.985
    resistance = high_24h * 1.012
    levels = [
        KeyLevel(label="Immediate Support", price=support, note="Recent liquidity pocket", side="support"),
        KeyLevel(label="Local Pivot", price=ma7[-1], note="7-period mean", side="pivot"),
        KeyLevel(label="Trend Base", price=ma21[-1], note="21-period mean", side="support"),
        KeyLevel(label="Immediate Resistance", price=resistance, note="Recent local high", side="resistance"),
        KeyLevel(label="Breakout Trigger", price=high_24h * 1.03, note="Continuation level", side="resistance"),
    ]

    price_series = [
        PricePoint(
            timestamp=trade.executed_at,
            price=price,
            ma7=ma7[index],
            ma21=ma21[index],
        )
        for index, (trade, price) in enumerate(zip(btc_trades, prices))
    ]

    return BtcSnapshot(
        symbol="BTC/USDT",
        current_price=current_price,
        change_24h=change_24h,
        high_24h=high_24h,
        low_24h=low_24h,
        volume_24h=volume_24h,
        regime=regime,
        sentiment=sentiment,
        price_series=price_series,
        onchain=onchain,
        technicals=technicals,
        levels=levels,
    )


def build_metrics(trades: list[Trade], focus_market: str) -> list[Metric]:
    if not trades:
        return []

    total_pnl = sum((Decimal(str(trade.pnl)) for trade in trades), Decimal("0"))
    total_notional = sum(
        (Decimal(str(trade.quantity)) * Decimal(str(trade.price)) for trade in trades),
        Decimal("0"),
    )
    wins = sum(1 for trade in trades if Decimal(str(trade.pnl)) > 0)
    unique_symbols = len({trade.symbol for trade in trades})
    unique_markets = len({classify_market(trade) for trade in trades})

    market_summaries = build_market_summaries(trades)
    best_market = max(market_summaries, key=lambda item: item.net_pnl) if market_summaries else None

    metrics = [
        Metric(label="Net PnL", value=format_money(total_pnl), hint="Realized from filled trades"),
        Metric(label="Win Rate", value=f"{(wins / len(trades)) * 100:.1f}%", hint=f"{wins} winning trades"),
        Metric(label="Turnover", value=format_compact_money(total_notional), hint="Absolute traded notional"),
        Metric(label="Coverage", value=str(unique_markets), hint=f"{unique_symbols} symbols in scope"),
    ]
    if focus_market != "all":
        metrics.append(
            Metric(
                label="Scope",
                value=market_label(focus_market),
                hint="Filtered market view",
            )
        )
    if best_market:
        metrics.append(
            Metric(
                label="Best Market",
                value=best_market.label,
                hint=format_money(best_market.net_pnl),
            )
        )
    return metrics


def build_risk_metrics(trades: list[Trade]) -> list[RiskMetric]:
    if not trades:
        return []

    gross_notional = sum(
        (abs(Decimal(str(trade.quantity)) * Decimal(str(trade.price))) for trade in trades),
        Decimal("0"),
    )
    net_pnl = sum((Decimal(str(trade.pnl)) for trade in trades), Decimal("0"))
    max_trade = max(
        (abs(Decimal(str(trade.quantity)) * Decimal(str(trade.price))) for trade in trades),
        default=Decimal("0"),
    )
    symbol_notional: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for trade in trades:
        symbol_notional[trade.symbol] += abs(Decimal(str(trade.quantity)) * Decimal(str(trade.price)))

    top_symbol = max(symbol_notional.items(), key=lambda item: item[1]) if symbol_notional else None
    top_share = (float(top_symbol[1]) / float(gross_notional) * 100) if top_symbol and gross_notional else 0.0
    worst_trade = min((Decimal(str(trade.pnl)) for trade in trades), default=Decimal("0"))
    long_notional = sum(
        (Decimal(str(trade.quantity)) * Decimal(str(trade.price)) for trade in trades if trade.side.upper() == "BUY"),
        Decimal("0"),
    )
    short_notional = sum(
        (Decimal(str(trade.quantity)) * Decimal(str(trade.price)) for trade in trades if trade.side.upper() == "SELL"),
        Decimal("0"),
    )
    bias = "Long" if long_notional > short_notional else "Short" if short_notional > long_notional else "Balanced"

    return [
        RiskMetric(label="Gross Exposure", value=format_compact_money(gross_notional), hint="Absolute traded notional"),
        RiskMetric(label="Net PnL", value=format_money(net_pnl), hint="Realized performance"),
        RiskMetric(label="Top Symbol Share", value=f"{top_share:.1f}%", hint=f"{top_symbol[0] if top_symbol else 'N/A'} concentration"),
        RiskMetric(label="Trade Bias", value=bias, hint="Buy vs sell notional balance"),
        RiskMetric(label="Largest Loss", value=format_money(worst_trade), hint="Worst filled trade"),
        RiskMetric(label="Largest Ticket", value=format_compact_money(max_trade), hint="Single trade size"),
    ]


def build_exposure(trades: list[Trade]) -> list[ExposureRow]:
    if not trades:
        return []

    grouped: dict[str, list[Trade]] = defaultdict(list)
    gross_by_market: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    total_gross = Decimal("0")
    for trade in trades:
        market = classify_market(trade)
        grouped[market].append(trade)
        gross = abs(Decimal(str(trade.quantity)) * Decimal(str(trade.price)))
        gross_by_market[market] += gross
        total_gross += gross

    rows: list[ExposureRow] = []
    for market, market_trades in grouped.items():
        net_pnl = sum((Decimal(str(trade.pnl)) for trade in market_trades), Decimal("0"))
        gross = gross_by_market[market]
        share = (float(gross) / float(total_gross) * 100) if total_gross else 0.0
        if share >= 40:
            risk = "High"
        elif share >= 22:
            risk = "Medium"
        else:
            risk = "Low"
        rows.append(
            ExposureRow(
                label=market_label(market),
                market=market,
                gross_notional=float(gross),
                net_pnl=float(net_pnl),
                share_pct=share,
                risk=risk,
            )
        )

    order_index = {market: index for index, market in enumerate(MARKET_ORDER[1:], start=1)}
    rows.sort(key=lambda item: order_index.get(item.market, 99))
    return rows


def build_dashboard(db: Session, market: str = "all") -> DashboardResponse:
    focus_market = market_filter(market)
    all_trades = fetch_trades(db, "all")
    scoped_trades = fetch_trades(db, focus_market) if focus_market != "all" else all_trades

    recent_trades = list(reversed(scoped_trades[-12:]))
    metrics = build_metrics(scoped_trades, focus_market)
    risk_metrics = build_risk_metrics(scoped_trades)
    exposure = build_exposure(all_trades)
    markets = build_market_summaries(all_trades)
    watchlist = build_watchlist(all_trades)
    btc = build_btc_snapshot(all_trades)

    return DashboardResponse(
        updated_at=datetime.now(timezone.utc),
        metrics=metrics,
        risk_metrics=risk_metrics,
        exposure=exposure,
        btc=btc,
        markets=markets,
        watchlist=watchlist,
        recent_trades=[trade_to_view(trade) for trade in recent_trades],
        focus_market=focus_market,
    )


@app.on_event("startup")
def startup_event() -> None:
    Base.metadata.create_all(bind=engine)
    with get_session() as session:
        seed_if_needed(session)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/dashboard", response_model=DashboardResponse)
def dashboard(
    market: str = Query(default="all"),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    return build_dashboard(db, market)


@app.get("/api/overview", response_model=DashboardResponse)
def overview(
    market: str = Query(default="all"),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    return build_dashboard(db, market)


@app.get("/api/trades", response_model=list[TradeView])
def list_trades(
    market: str = Query(default="all"),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[TradeView]:
    scoped = fetch_trades(db, market_filter(market))
    return [trade_to_view(trade) for trade in list(reversed(scoped[-limit:]))]


@app.get("/api/btc")
def btc_dashboard() -> dict[str, object]:
    return get_btc_dashboard()
