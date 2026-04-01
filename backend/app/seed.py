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
        ("AAPL", "BUY", "120.00", "189.20", "480.00", "NASDAQ"),
        ("MSFT", "SELL", "85.00", "402.40", "160.00", "NASDAQ"),
        ("0700.HK", "BUY", "300.00", "342.60", "920.00", "HKEX"),
        ("9988.HK", "SELL", "210.00", "78.40", "-140.00", "HKEX"),
        ("600519.SH", "BUY", "12.00", "1698.00", "620.00", "SSE"),
        ("510300.SH", "SELL", "4200.00", "3.62", "55.00", "SSE"),
        ("IF2506", "BUY", "8.00", "5162.00", "320.00", "CFFEX"),
        ("AU2506", "SELL", "55.00", "618.50", "180.00", "SHFE"),
        ("BTC/USDT", "SELL", "0.11", "70890.00", "410.00", "Binance"),
        ("ETH/USDT", "BUY", "1.75", "3485.00", "155.00", "Coinbase"),
        ("AAPL", "SELL", "95.00", "191.60", "-35.00", "NASDAQ"),
        ("TSLA", "BUY", "36.00", "175.20", "240.00", "NYSE"),
        ("0700.HK", "SELL", "240.00", "346.20", "140.00", "HKEX"),
        ("9988.HK", "BUY", "180.00", "76.80", "260.00", "HKEX"),
        ("600519.SH", "SELL", "10.00", "1718.00", "-45.00", "SSE"),
        ("IF2506", "SELL", "6.00", "5192.00", "210.00", "CFFEX"),
        ("CU2506", "BUY", "18.00", "75120.00", "590.00", "SHFE"),
        ("BTC/USDT", "BUY", "0.09", "71580.00", "520.00", "Binance"),
        ("ETH/USDT", "SELL", "1.20", "3610.00", "-120.00", "Coinbase"),
        ("MSFT", "BUY", "70.00", "405.80", "130.00", "NASDAQ"),
        ("TSLA", "SELL", "22.00", "178.50", "-80.00", "NYSE"),
        ("510300.SH", "BUY", "5000.00", "3.58", "34.00", "SSE"),
        ("IC2506", "SELL", "7.00", "5640.00", "95.00", "CFFEX"),
        ("BTC/USDT", "SELL", "0.14", "71820.00", "690.00", "Binance"),
        ("ETH/USDT", "BUY", "2.10", "3595.00", "260.00", "Coinbase"),
        ("0700.HK", "BUY", "180.00", "344.10", "-65.00", "HKEX"),
        ("9988.HK", "SELL", "260.00", "79.60", "190.00", "HKEX"),
        ("AU2506", "BUY", "42.00", "621.80", "88.00", "SHFE"),
        ("IF2506", "BUY", "4.00", "5176.00", "130.00", "CFFEX"),
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
