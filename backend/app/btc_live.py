from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from math import sqrt
from statistics import mean
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BTC_ID = "bitcoin"
CACHE_TTL_SECONDS = 60

_CACHE: dict[str, Any] = {"ts": 0.0, "payload": None}


def fetch_json(url: str, headers: dict[str, str] | None = None, timeout: int = 12) -> dict[str, Any]:
    request = Request(url, headers=headers or {})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def maybe_header() -> dict[str, str]:
    api_key = os.getenv("COINGECKO_API_KEY") or os.getenv("COINGECKO_DEMO_API_KEY")
    if api_key:
        return {"x-cg-demo-api-key": api_key}
    return {}


def moving_average(values: list[float], window: int) -> list[float]:
    output: list[float] = []
    for index in range(len(values)):
        start = max(0, index - window + 1)
        window_values = values[start : index + 1]
        output.append(sum(window_values) / len(window_values))
    return output


def exponential_moving_average(values: list[float], window: int) -> list[float]:
    if not values:
        return []
    multiplier = 2 / (window + 1)
    ema_values = [values[0]]
    for value in values[1:]:
        ema_values.append((value - ema_values[-1]) * multiplier + ema_values[-1])
    return ema_values


def calculate_rsi(values: list[float], window: int = 14) -> float:
    if len(values) < 2:
        return 50.0

    gains: list[float] = []
    losses: list[float] = []
    for index in range(1, len(values)):
        delta = values[index] - values[index - 1]
        gains.append(max(delta, 0.0))
        losses.append(abs(min(delta, 0.0)))

    recent_gains = gains[-window:]
    recent_losses = losses[-window:]
    avg_gain = sum(recent_gains) / len(recent_gains) if recent_gains else 0.0
    avg_loss = sum(recent_losses) / len(recent_losses) if recent_losses else 0.0

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_macd(values: list[float]) -> tuple[float, float, float]:
    if len(values) < 35:
        return 0.0, 0.0, 0.0
    ema12 = exponential_moving_average(values, 12)
    ema26 = exponential_moving_average(values, 26)
    macd_line = [a - b for a, b in zip(ema12[-len(ema26) :], ema26)]
    signal_line = exponential_moving_average(macd_line, 9)
    histogram = macd_line[-1] - signal_line[-1]
    return macd_line[-1], signal_line[-1], histogram


def stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = mean(values)
    variance = sum((value - avg) ** 2 for value in values) / len(values)
    return sqrt(variance)


def btc_price_history(days_back: int = 2200) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days_back)
    params = urlencode(
        {
            "vs_currency": "usd",
            "from": int(start.timestamp()),
            "to": int(now.timestamp()),
        }
    )
    url = f"https://api.coingecko.com/api/v3/coins/{BTC_ID}/market_chart/range?{params}"
    data = fetch_json(url, headers=maybe_header())
    prices = data.get("prices", [])
    market_caps = data.get("market_caps", [])
    total_volumes = data.get("total_volumes", [])

    values = [float(point[1]) for point in prices]
    ma7 = moving_average(values, 7)
    ma50 = moving_average(values, 50)
    ma200 = moving_average(values, 200)
    ma1400 = moving_average(values, 1400)

    chart: list[dict[str, Any]] = []
    for index, point in enumerate(prices):
        chart.append(
            {
                "timestamp": datetime.fromtimestamp(point[0] / 1000, tz=timezone.utc).isoformat(),
                "price": float(point[1]),
                "market_cap": float(market_caps[index][1]) if index < len(market_caps) else None,
                "volume": float(total_volumes[index][1]) if index < len(total_volumes) else None,
                "ma7": ma7[index],
                "ma50": ma50[index],
                "ma200": ma200[index],
                "ma1400": ma1400[index],
            }
        )
    return chart


def global_snapshot() -> dict[str, Any]:
    url = "https://api.coingecko.com/api/v3/global"
    data = fetch_json(url, headers=maybe_header())
    return data.get("data", {})


def blockchain_stats() -> dict[str, Any]:
    return fetch_json("https://api.blockchain.info/stats")


def mempool_fees() -> dict[str, Any]:
    return fetch_json("https://mempool.space/api/v1/fees/recommended")


def fear_greed() -> dict[str, Any]:
    url = "https://api.alternative.me/fng/?limit=30&format=json"
    data = fetch_json(url)
    items = data.get("data", [])
    latest = items[0] if items else {}
    return {
        "latest": latest,
        "history": items,
    }


def pick_points(series: list[dict[str, Any]], count: int = 360) -> list[dict[str, Any]]:
    return series[-count:] if len(series) > count else series


def build_signals(history: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    prices = [float(point["price"]) for point in history]
    if not prices:
        return [], [], []

    current = prices[-1]
    high_90d = max(prices[-90:]) if len(prices) >= 90 else max(prices)
    low_90d = min(prices[-90:]) if len(prices) >= 90 else min(prices)
    ma7 = history[-1]["ma7"]
    ma50 = history[-1]["ma50"]
    ma200 = history[-1]["ma200"]
    ma1400 = history[-1]["ma1400"]

    rsi14 = calculate_rsi(prices)
    macd_line, signal_line, histogram = calculate_macd(prices)
    volatility_30d = stddev([(prices[index] / prices[index - 1]) - 1 for index in range(max(1, len(prices) - 30), len(prices))]) * 100
    momentum_30d = ((prices[-1] - prices[-30]) / prices[-30] * 100) if len(prices) >= 30 and prices[-30] else 0.0
    cycle_ratio = current / ma1400 if ma1400 else 0.0
    above_200d = current >= ma200
    above_50d = current >= ma50
    above_1400d = current >= ma1400

    hero_metrics = [
        {
            "label": "Price / 200WMA",
            "value": f"{cycle_ratio:.2f}x",
            "hint": "Cycle position vs 1400-day moving average",
            "state": "bullish" if cycle_ratio >= 1.0 else "bearish",
        },
        {
            "label": "90d Range Position",
            "value": f"{((current - low_90d) / (high_90d - low_90d) * 100 if high_90d > low_90d else 50):.1f}%",
            "hint": "Where price sits inside the 90-day range",
            "state": "neutral",
        },
        {
            "label": "RSI(14)",
            "value": f"{rsi14:.1f}",
            "hint": "Momentum gauge",
            "state": "bullish" if rsi14 < 70 else "bearish" if rsi14 > 72 else "neutral",
        },
        {
            "label": "MACD Histogram",
            "value": f"{histogram:+.2f}",
            "hint": "Trend acceleration",
            "state": "bullish" if histogram > 0 else "bearish",
        },
        {
            "label": "30d Momentum",
            "value": f"{momentum_30d:+.1f}%",
            "hint": "30-day price change",
            "state": "bullish" if momentum_30d > 0 else "bearish",
        },
        {
            "label": "30d Volatility",
            "value": f"{volatility_30d:.1f}%",
            "hint": "Std dev of daily returns",
            "state": "neutral",
        },
    ]

    technical_cards = [
        {
            "label": "MA7",
            "value": f"${ma7:,.0f}",
            "hint": "Short trend anchor",
            "state": "bullish" if current >= ma7 else "bearish",
        },
        {
            "label": "MA50",
            "value": f"${ma50:,.0f}",
            "hint": "Mid trend anchor",
            "state": "bullish" if above_50d else "bearish",
        },
        {
            "label": "MA200",
            "value": f"${ma200:,.0f}",
            "hint": "Long trend anchor",
            "state": "bullish" if above_200d else "bearish",
        },
        {
            "label": "MA1400",
            "value": f"${ma1400:,.0f}",
            "hint": "200-week equivalent",
            "state": "bullish" if above_1400d else "bearish",
        },
        {
            "label": "MACD",
            "value": f"{macd_line:+.2f}",
            "hint": f"Signal {signal_line:+.2f}",
            "state": "bullish" if macd_line > signal_line else "bearish",
        },
        {
            "label": "Cycle Bias",
            "value": "Above" if above_1400d else "Below",
            "hint": "200-week proxy",
            "state": "bullish" if above_1400d else "bearish",
        },
    ]

    level_rows = [
        {
            "label": "Local Support",
            "price": low_90d * 0.99,
            "note": "Recent swing low",
            "side": "support",
        },
        {
            "label": "200W Proxy",
            "price": ma1400,
            "note": "1400-day moving average",
            "side": "pivot",
        },
        {
            "label": "200D MA",
            "price": ma200,
            "note": "Long-cycle trend line",
            "side": "support",
        },
        {
            "label": "50D MA",
            "price": ma50,
            "note": "Swing trend line",
            "side": "pivot",
        },
        {
            "label": "Local Resistance",
            "price": high_90d * 1.01,
            "note": "Recent swing high",
            "side": "resistance",
        },
    ]

    return hero_metrics, technical_cards, level_rows


def build_btc_dashboard() -> dict[str, Any]:
    now = datetime.now(timezone.utc)

    try:
        history = btc_price_history()
        latest = history[-1]
        prior_24h = history[-2]["price"] if len(history) >= 2 else latest["price"]
        global_data = global_snapshot()
        blockchain = blockchain_stats()
        mempool = mempool_fees()
        fng = fear_greed()
        hero_metrics, technical_cards, level_rows = build_signals(history)

        current_price = float(latest["price"])
        change_24h = ((current_price - prior_24h) / prior_24h * 100) if prior_24h else 0.0
        market_cap = float(latest["market_cap"] or 0.0)
        volume_24h = float(latest["volume"] or 0.0)
        btc_dominance = float(global_data.get("market_cap_percentage", {}).get("btc", 0.0))
        total_market_cap = float(global_data.get("total_market_cap", {}).get("usd", 0.0))
        fear_greed_value = int(fng["latest"].get("value", "0") or 0)
        fear_greed_label = fng["latest"].get("value_classification", "Neutral")
        fear_greed_updated = int(fng["latest"].get("timestamp", "0") or 0)

        blocks_total = int(blockchain.get("n_blocks_total", 0) or 0)
        blocks_to_halving = 210000 - (blocks_total % 210000)
        if blocks_to_halving == 210000:
            blocks_to_halving = 0
        minutes_between_blocks = float(blockchain.get("minutes_between_blocks", 0.0) or 0.0)
        days_to_halving = (blocks_to_halving * minutes_between_blocks) / 60 / 24 if blocks_to_halving else 0.0
        current_subsidy = 50 / (2 ** (blocks_total // 210000)) if blocks_total else 3.125
        blocks_to_retarget = max(int(blockchain.get("nextretarget", 0) or 0) - blocks_total, 0)
        circulating_supply_btc = float(blockchain.get("totalbc", 0) or 0) / 100_000_000
        hash_rate_ehs = float(blockchain.get("hash_rate", 0) or 0) / 1_000_000_000_000_000_000
        difficulty = float(blockchain.get("difficulty", 0) or 0)
        miners_revenue_usd = float(blockchain.get("miners_revenue_usd", 0) or 0)
        n_tx = int(blockchain.get("n_tx", 0) or 0)
        n_blocks_mined = int(blockchain.get("n_blocks_mined", 0) or 0)
        estimated_tx_volume = float(blockchain.get("estimated_transaction_volume_usd", 0) or 0)

        network_cards = [
            {
                "label": "Hash Rate",
                "value": f"{hash_rate_ehs:,.0f} EH/s",
                "hint": "Estimated network power",
                "state": "bullish" if hash_rate_ehs > 0 else "neutral",
            },
            {
                "label": "Difficulty",
                "value": f"{difficulty:,.0f}",
                "hint": "Mining difficulty",
                "state": "neutral",
            },
            {
                "label": "Block Time",
                "value": f"{minutes_between_blocks:.1f} min",
                "hint": "Average block interval",
                "state": "bullish" if minutes_between_blocks <= 10 else "bearish",
            },
            {
                "label": "Miners Revenue",
                "value": f"${miners_revenue_usd:,.0f}",
                "hint": "Daily revenue estimate",
                "state": "bullish" if miners_revenue_usd > 0 else "neutral",
            },
            {
                "label": "Tx Count",
                "value": f"{n_tx:,}",
                "hint": "Transactions in latest stat snapshot",
                "state": "neutral",
            },
            {
                "label": "Estimated Tx Volume",
                "value": f"${estimated_tx_volume:,.0f}",
                "hint": "Network transfer volume",
                "state": "neutral",
            },
            {
                "label": "Supply",
                "value": f"{circulating_supply_btc:,.2f} BTC",
                "hint": "CoinGecko / Blockchain supply proxy",
                "state": "neutral",
            },
            {
                "label": "Halving",
                "value": f"{blocks_to_halving:,} blocks",
                "hint": f"~{days_to_halving:.0f} days · reward {current_subsidy:.3f} BTC",
                "state": "neutral",
            },
        ]

        sentiment_cards = [
            {
                "label": "Fear & Greed",
                "value": f"{fear_greed_value}",
                "hint": fear_greed_label,
                "state": "bearish" if fear_greed_value <= 25 else "neutral" if fear_greed_value <= 60 else "bullish",
            },
            {
                "label": "BTC Dominance",
                "value": f"{btc_dominance:.1f}%",
                "hint": "Share of total crypto market cap",
                "state": "bullish" if btc_dominance >= 50 else "neutral",
            },
            {
                "label": "Crypto Market Cap",
                "value": f"${total_market_cap / 1_000_000_000_000:.2f}T",
                "hint": "Global crypto market size",
                "state": "neutral",
            },
            {
                "label": "Retarget",
                "value": f"{blocks_to_retarget:,} blocks",
                "hint": "Next difficulty adjustment",
                "state": "neutral",
            },
        ]

        chart_series = pick_points(history, 420)
        chart_max = max(point["price"] for point in chart_series) if chart_series else current_price
        chart_min = min(point["price"] for point in chart_series) if chart_series else current_price

        sources = [
            {"label": "CoinGecko", "url": "https://docs.coingecko.com/"},
            {"label": "Blockchain.com", "url": "https://www.blockchain.com/en/api/charts_api"},
            {"label": "mempool.space", "url": "https://mempool.space/"},
            {"label": "Alternative.me", "url": "https://alternative.me/crypto/fear-and-greed-index/"},
        ]

        payload = {
            "updated_at": now.isoformat(),
            "hero": {
                "symbol": "BTC",
                "price": current_price,
                "change_24h": change_24h,
                "market_cap": market_cap,
                "volume_24h": volume_24h,
                "btc_dominance": btc_dominance,
                "fear_greed_value": fear_greed_value,
                "fear_greed_label": fear_greed_label,
                "fear_greed_updated_at": datetime.fromtimestamp(fear_greed_updated, tz=timezone.utc).isoformat() if fear_greed_updated else None,
                "regime": "Bull trend" if current_price > latest["ma200"] else "Cycle compression",
                "price_vs_200wma": current_price / latest["ma1400"] if latest["ma1400"] else 0.0,
            },
            "chart": {
                "series": chart_series,
                "min": chart_min,
                "max": chart_max,
            },
            "cycle": {
                "hero_metrics": hero_metrics,
                "technical_cards": technical_cards,
                "level_rows": level_rows,
                "network_cards": network_cards,
                "sentiment_cards": sentiment_cards,
            },
            "raw": {
                "blockchain": blockchain,
                "mempool": mempool,
                "fear_greed": fng,
                "global": global_data,
            },
            "sources": sources,
        }
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, OSError) as exc:
        payload = fallback_btc_dashboard(str(exc))

    _CACHE["ts"] = time.time()
    _CACHE["payload"] = payload
    return payload


def fallback_btc_dashboard(reason: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    base_price = 70000.0
    chart_series = []
    for index in range(420):
        t = now - timedelta(days=419 - index)
        swing = (index / 18.0)
        price = base_price + (index * 13.5) + (swing * 1200) - (swing % 7) * 300
        chart_series.append(
            {
                "timestamp": t.isoformat(),
                "price": price,
                "market_cap": price * 19_700_000,
                "volume": 35_000_000_000 + index * 2_000_000,
                "ma7": price * 0.98,
                "ma50": price * 0.95,
                "ma200": price * 0.90,
                "ma1400": price * 0.82,
            }
        )
    return {
        "updated_at": now.isoformat(),
        "hero": {
            "symbol": "BTC",
            "price": base_price,
            "change_24h": 0.0,
            "market_cap": base_price * 19_700_000,
            "volume_24h": 35_000_000_000,
            "btc_dominance": 58.0,
            "fear_greed_value": 50,
            "fear_greed_label": "Neutral",
            "fear_greed_updated_at": None,
            "regime": f"Fallback data ({reason})",
            "price_vs_200wma": 1.0,
        },
        "chart": {
            "series": chart_series,
            "min": min(point["price"] for point in chart_series),
            "max": max(point["price"] for point in chart_series),
        },
        "cycle": {
            "hero_metrics": [
                {"label": "Price / 200WMA", "value": "1.00x", "hint": "Fallback", "state": "neutral"},
                {"label": "90d Range Position", "value": "50.0%", "hint": "Fallback", "state": "neutral"},
                {"label": "RSI(14)", "value": "50.0", "hint": "Fallback", "state": "neutral"},
                {"label": "MACD Histogram", "value": "+0.00", "hint": "Fallback", "state": "neutral"},
                {"label": "30d Momentum", "value": "+0.0%", "hint": "Fallback", "state": "neutral"},
                {"label": "30d Volatility", "value": "0.0%", "hint": "Fallback", "state": "neutral"},
            ],
            "technical_cards": [
                {"label": "MA7", "value": "$68,600", "hint": "Fallback", "state": "neutral"},
                {"label": "MA50", "value": "$66,500", "hint": "Fallback", "state": "neutral"},
                {"label": "MA200", "value": "$63,000", "hint": "Fallback", "state": "neutral"},
                {"label": "MA1400", "value": "$57,400", "hint": "Fallback", "state": "neutral"},
                {"label": "MACD", "value": "+0.00", "hint": "Fallback", "state": "neutral"},
                {"label": "Cycle Bias", "value": "Above", "hint": "Fallback", "state": "neutral"},
            ],
            "level_rows": [
                {"label": "Local Support", "price": 67500.0, "note": "Fallback", "side": "support"},
                {"label": "200W Proxy", "price": 57400.0, "note": "Fallback", "side": "pivot"},
                {"label": "200D MA", "price": 63000.0, "note": "Fallback", "side": "support"},
                {"label": "50D MA", "price": 66500.0, "note": "Fallback", "side": "pivot"},
                {"label": "Local Resistance", "price": 74000.0, "note": "Fallback", "side": "resistance"},
            ],
            "network_cards": [
                {"label": "Hash Rate", "value": "—", "hint": "Fallback", "state": "neutral"},
                {"label": "Difficulty", "value": "—", "hint": "Fallback", "state": "neutral"},
                {"label": "Block Time", "value": "—", "hint": "Fallback", "state": "neutral"},
                {"label": "Miners Revenue", "value": "—", "hint": "Fallback", "state": "neutral"},
                {"label": "Tx Count", "value": "—", "hint": "Fallback", "state": "neutral"},
                {"label": "Estimated Tx Volume", "value": "—", "hint": "Fallback", "state": "neutral"},
                {"label": "Supply", "value": "—", "hint": "Fallback", "state": "neutral"},
                {"label": "Halving", "value": "—", "hint": "Fallback", "state": "neutral"},
            ],
            "sentiment_cards": [
                {"label": "Fear & Greed", "value": "50", "hint": "Neutral", "state": "neutral"},
                {"label": "BTC Dominance", "value": "58.0%", "hint": "Fallback", "state": "neutral"},
                {"label": "Crypto Market Cap", "value": "$2.50T", "hint": "Fallback", "state": "neutral"},
                {"label": "Retarget", "value": "—", "hint": "Fallback", "state": "neutral"},
            ],
        },
        "raw": {"reason": reason},
        "sources": [
            {"label": "CoinGecko", "url": "https://docs.coingecko.com/"},
            {"label": "Blockchain.com", "url": "https://www.blockchain.com/en/api/charts_api"},
            {"label": "mempool.space", "url": "https://mempool.space/"},
            {"label": "Alternative.me", "url": "https://alternative.me/crypto/fear-and-greed-index/"},
        ],
    }


def get_btc_dashboard() -> dict[str, Any]:
    cached_ts = float(_CACHE.get("ts", 0.0) or 0.0)
    cached_payload = _CACHE.get("payload")
    if cached_payload and (time.time() - cached_ts) < CACHE_TTL_SECONDS:
        return cached_payload
    return build_btc_dashboard()

