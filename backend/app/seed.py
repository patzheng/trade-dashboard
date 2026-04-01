from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Trade


def seed_if_needed(session: Session) -> None:
    count = session.scalar(select(func.count()).select_from(Trade)) or 0
    if count:
        return

    base_time = datetime.now(timezone.utc) - timedelta(hours=23)
    records = []
    sample_data = [
        ("BTC/USDT", "BUY", "0.18", "70240.00", "640.00", "Binance"),
        ("ETH/USDT", "SELL", "2.40", "3550.00", "210.00", "Coinbase"),
        ("SOL/USDT", "BUY", "95.00", "171.20", "-85.00", "Bybit"),
        ("BTC/USDT", "SELL", "0.11", "70890.00", "410.00", "Binance"),
        ("ETH/USDT", "BUY", "1.75", "3485.00", "155.00", "Coinbase"),
        ("XRP/USDT", "SELL", "6400.00", "0.58", "48.00", "Kraken"),
        ("SOL/USDT", "SELL", "120.00", "169.80", "220.00", "Bybit"),
        ("BTC/USDT", "BUY", "0.09", "71580.00", "520.00", "Binance"),
        ("ETH/USDT", "SELL", "1.20", "3610.00", "-120.00", "Coinbase"),
        ("DOGE/USDT", "BUY", "18000.00", "0.17", "35.00", "OKX"),
        ("BTC/USDT", "SELL", "0.14", "71820.00", "690.00", "Binance"),
        ("ETH/USDT", "BUY", "2.10", "3595.00", "260.00", "Coinbase"),
        ("SOL/USDT", "BUY", "80.00", "173.60", "95.00", "Bybit"),
        ("ARB/USDT", "SELL", "2500.00", "1.42", "-24.00", "OKX"),
        ("BTC/USDT", "BUY", "0.07", "72110.00", "430.00", "Binance"),
        ("ETH/USDT", "SELL", "1.60", "3640.00", "180.00", "Coinbase"),
        ("SOL/USDT", "SELL", "110.00", "176.40", "140.00", "Bybit"),
        ("XRP/USDT", "BUY", "5800.00", "0.60", "30.00", "Kraken"),
        ("BTC/USDT", "SELL", "0.08", "72430.00", "560.00", "Binance"),
        ("ETH/USDT", "BUY", "1.30", "3660.00", "165.00", "Coinbase"),
        ("SOL/USDT", "BUY", "70.00", "178.20", "210.00", "Bybit"),
        ("DOGE/USDT", "SELL", "15000.00", "0.19", "40.00", "OKX"),
        ("BTC/USDT", "BUY", "0.10", "72840.00", "780.00", "Binance"),
        ("ETH/USDT", "SELL", "1.10", "3695.00", "195.00", "Coinbase"),
    ]

    for index, item in enumerate(sample_data):
        symbol, side, quantity, price, pnl, venue = item
        records.append(
            Trade(
                symbol=symbol,
                side=side,
                quantity=Decimal(quantity),
                price=Decimal(price),
                pnl=Decimal(pnl),
                venue=venue,
                status="FILLED",
                executed_at=base_time + timedelta(hours=index),
            )
        )

    session.add_all(records)
    session.commit()

