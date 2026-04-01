from __future__ import annotations

from collections import defaultdict
from collections.abc import Generator
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from .db import Base, engine, get_session
from .models import Trade
from .schemas import EquityPoint, Metric, OverviewResponse, SymbolHighlight, TradeOut
from .seed import seed_if_needed

app = FastAPI(title="Trade Dashboard API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


def get_db() -> Generator[Session, None, None]:
    db = get_session()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def startup_event() -> None:
    Base.metadata.create_all(bind=engine)
    with get_session() as session:
        seed_if_needed(session)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/trades", response_model=list[TradeOut])
def list_trades(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[Trade]:
    stmt = select(Trade).order_by(desc(Trade.executed_at)).limit(limit)
    return list(db.scalars(stmt).all())


@app.get("/api/overview", response_model=OverviewResponse)
def overview(db: Session = Depends(get_db)) -> OverviewResponse:
    trades = list(db.scalars(select(Trade).order_by(Trade.executed_at)).all())
    if not trades:
        return OverviewResponse(
            updated_at=datetime.now(timezone.utc),
            metrics=[],
            top_symbols=[],
            equity_curve=[],
        )

    total_pnl = sum((Decimal(str(trade.pnl)) for trade in trades), Decimal("0"))
    total_notional = sum(
        (Decimal(str(trade.quantity)) * Decimal(str(trade.price)) for trade in trades),
        Decimal("0"),
    )
    wins = sum(1 for trade in trades if Decimal(str(trade.pnl)) > 0)
    unique_symbols = {trade.symbol for trade in trades}

    by_symbol: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for trade in trades:
        by_symbol[trade.symbol] += Decimal(str(trade.pnl))

    sorted_symbols = sorted(by_symbol.items(), key=lambda item: item[1], reverse=True)
    top_symbols = [
        SymbolHighlight(
            symbol=symbol,
            value=format_compact_money(pnl),
            change="Net realized PnL",
        )
        for symbol, pnl in sorted_symbols[:4]
    ]

    equity = Decimal("100000")
    equity_curve: list[EquityPoint] = []
    for trade in trades:
        equity += Decimal(str(trade.pnl))
        equity_curve.append(
            EquityPoint(
                label=trade.executed_at.astimezone(timezone.utc).strftime("%H:%M"),
                value=float(equity),
            )
        )

    metrics = [
        Metric(
            label="Realized PnL",
            value=format_money(total_pnl),
            hint="Based on filled trades",
        ),
        Metric(
            label="Win Rate",
            value=f"{(wins / len(trades)) * 100:.1f}%",
            hint=f"{wins} winning trades",
        ),
        Metric(
            label="Notional Volume",
            value=format_compact_money(total_notional),
            hint="Absolute trade turnover",
        ),
        Metric(
            label="Active Symbols",
            value=str(len(unique_symbols)),
            hint="Unique pairs in the sample set",
        ),
    ]

    return OverviewResponse(
        updated_at=datetime.now(timezone.utc),
        metrics=metrics,
        top_symbols=top_symbols,
        equity_curve=equity_curve,
    )
