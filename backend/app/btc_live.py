from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from math import sqrt
from statistics import mean
from typing import Any, Callable, TypeVar
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

BTC_ID = "bitcoin"
BTC_FUTURES_SYMBOL = "BTCUSDT"
BITVIEW_BASE_URL = os.getenv("BITVIEW_BASE_URL", "https://bitview.space/api")
BINANCE_BASE_URL = os.getenv("BINANCE_BASE_URL", "https://fapi.binance.com")
BINANCE_SPOT_BASE_URL = os.getenv("BINANCE_SPOT_BASE_URL", "https://api.binance.com")

T = TypeVar("T")


def fetch_payload(url: str, headers: dict[str, str] | None = None, timeout: int = 12) -> Any:
    request = Request(url, headers=headers or {})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310
        body = response.read().decode("utf-8")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return body


def fetch_json(url: str, headers: dict[str, str] | None = None, timeout: int = 12) -> dict[str, Any]:
    payload = fetch_payload(url, headers=headers, timeout=timeout)
    if isinstance(payload, dict):
        return payload
    raise ValueError(f"Expected JSON object from {url}")


def fetch_list(url: str, headers: dict[str, str] | None = None, timeout: int = 12) -> list[Any]:
    payload = fetch_payload(url, headers=headers, timeout=timeout)
    if isinstance(payload, list):
        return payload
    raise ValueError(f"Expected JSON list from {url}")


def safe_call(factory: Callable[[], T], default: T) -> T:
    try:
        return factory()
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, OSError):
        return default


def maybe_header() -> dict[str, str]:
    api_key = os.getenv("COINGECKO_API_KEY") or os.getenv("COINGECKO_DEMO_API_KEY")
    if api_key:
        return {"x-cg-demo-api-key": api_key}
    return {}


def coerce_number_list(payload: Any) -> list[float]:
    if payload is None:
        return []
    if isinstance(payload, (int, float)):
        return [float(payload)]
    if isinstance(payload, str):
        try:
            return [float(payload)]
        except ValueError:
            return []
    if isinstance(payload, list):
        numbers: list[float] = []
        for item in payload:
            if isinstance(item, (int, float)):
                numbers.append(float(item))
            elif isinstance(item, str):
                try:
                    numbers.append(float(item))
                except ValueError:
                    continue
            elif isinstance(item, list) and item:
                nested = coerce_number_list(item)
                if nested:
                    numbers.extend(nested)
        return numbers
    if isinstance(payload, dict):
        for key in ("data", "values", "result", "series", "rows", "payload", "items"):
            if key in payload:
                return coerce_number_list(payload[key])
        if len(payload) == 1:
            return coerce_number_list(next(iter(payload.values())))
    return []


def bitview_vector(index: str, vec_id: str, count: int = 420) -> list[float]:
    params = urlencode({"from": -count, "format": "json"})
    url = f"{BITVIEW_BASE_URL.rstrip('/')}/{index}-to-{vec_id}?{params}"
    try:
        payload = fetch_payload(url)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError):
        return []
    values = coerce_number_list(payload)
    return values


def extract_number(payload: Any) -> float | None:
    values = coerce_number_list(payload)
    return values[0] if values else None


def collect_strings(payload: Any) -> list[str]:
    if payload is None:
        return []
    if isinstance(payload, str):
        return [payload]
    if isinstance(payload, (int, float)):
        return [str(payload)]
    if isinstance(payload, list):
        items: list[str] = []
        for item in payload:
            items.extend(collect_strings(item))
        return items
    if isinstance(payload, dict):
        items: list[str] = []
        for key in ("id", "slug", "name", "series", "series_id", "series_name", "metric", "title"):
            value = payload.get(key)
            if isinstance(value, str):
                items.append(value)
        for key in ("results", "data", "items", "series"):
            if key in payload:
                items.extend(collect_strings(payload[key]))
        return items
    return []


def bitview_series_candidates(query: str) -> list[str]:
    params = urlencode({"q": query})
    url = f"{BITVIEW_BASE_URL.rstrip('/')}/series/search?{params}"
    try:
        payload = fetch_payload(url)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError):
        return []
    candidates = collect_strings(payload)
    normalized = []
    seen: set[str] = set()
    for item in candidates:
        candidate = item.strip()
        if not candidate:
            continue
        key = candidate.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(candidate)
    return normalized


def bitview_series_latest(series_query: str, index: str = "day1") -> tuple[float | None, str | None]:
    candidates = [series_query]
    candidates.extend(bitview_series_candidates(series_query))
    tried: set[tuple[str, str]] = set()
    for candidate in candidates:
        encoded_candidate = quote(candidate, safe="")
        for resolution in (index, "day1", "week1", "month1"):
            key = (candidate, resolution)
            if key in tried:
                continue
            tried.add(key)
            url = f"{BITVIEW_BASE_URL.rstrip('/')}/series/{encoded_candidate}/{resolution}/latest"
            try:
                payload = fetch_payload(url)
            except (HTTPError, URLError, TimeoutError, ValueError, OSError):
                continue
            value = extract_number(payload)
            if value is not None:
                return value, candidate
    return None, None


def bitview_series_history(series_query: str, index: str = "day1", count: int = 180) -> list[float]:
    candidates = [series_query]
    candidates.extend(bitview_series_candidates(series_query))
    tried: set[tuple[str, str]] = set()
    params = urlencode({"format": "json", "count": count})
    for candidate in candidates:
        encoded_candidate = quote(candidate, safe="")
        for resolution in (index, "day1", "week1", "month1"):
            key = (candidate, resolution)
            if key in tried:
                continue
            tried.add(key)
            url = f"{BITVIEW_BASE_URL.rstrip('/')}/series/{encoded_candidate}/{resolution}?{params}"
            try:
                payload = fetch_payload(url)
            except (HTTPError, URLError, TimeoutError, ValueError, OSError):
                continue
            values = coerce_number_list(payload)
            if values:
                return values[-count:]
    return []


def percent_change(series: list[float], period: int) -> float | None:
    if len(series) <= period:
        return None
    base = series[-period - 1]
    if not base:
        return None
    return (series[-1] - base) / base * 100


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


def bitview_price_history(count: int = 420) -> list[dict[str, Any]]:
    closes = bitview_vector("date", "close", count=count)
    opens = bitview_vector("date", "open", count=count)
    highs = bitview_vector("date", "high", count=count)
    lows = bitview_vector("date", "low", count=count)

    if not closes:
        return []

    values = closes
    ma7 = moving_average(values, 7)
    ma50 = moving_average(values, 50)
    ma200 = moving_average(values, 200)
    ma1400 = moving_average(values, 1400)

    now = datetime.now(timezone.utc)
    chart: list[dict[str, Any]] = []
    for index, close in enumerate(closes):
        timestamp = now - timedelta(days=len(closes) - 1 - index)
        chart.append(
            {
                "timestamp": timestamp.isoformat(),
                "price": float(close),
                "open": float(opens[index]) if index < len(opens) else None,
                "high": float(highs[index]) if index < len(highs) else None,
                "low": float(lows[index]) if index < len(lows) else None,
                "market_cap": None,
                "volume": None,
                "ma7": ma7[index],
                "ma50": ma50[index],
                "ma200": ma200[index],
                "ma1400": ma1400[index],
            }
        )
    return chart


def bitview_block_metrics(count: int = 180) -> dict[str, Any]:
    difficulty = bitview_vector("height", "difficulty", count=count)
    timestamps = bitview_vector("height", "timestamp", count=count)
    tx_count = bitview_vector("height", "tx_count", count=count)
    fee_sum = bitview_vector("height", "fee_sum", count=count)
    size = bitview_vector("height", "size", count=count)
    weight = bitview_vector("height", "weight", count=count)

    if not difficulty and not timestamps and not tx_count and not fee_sum:
        return {}

    intervals: list[float] = []
    for index in range(1, len(timestamps)):
        gap = timestamps[index] - timestamps[index - 1]
        if gap > 0:
            intervals.append(gap / 60.0)

    return {
        "difficulty": difficulty[-1] if difficulty else None,
        "difficulty_change_30d": ((difficulty[-1] - difficulty[-30]) / difficulty[-30] * 100) if len(difficulty) >= 30 and difficulty[-30] else None,
        "block_time_minutes": sum(intervals[-20:]) / len(intervals[-20:]) if intervals else None,
        "tx_count": tx_count[-1] if tx_count else None,
        "tx_count_avg_30d": sum(tx_count[-30:]) / len(tx_count[-30:]) if tx_count else None,
        "fee_sum": fee_sum[-1] if fee_sum else None,
        "fee_sum_avg_30d": sum(fee_sum[-30:]) / len(fee_sum[-30:]) if fee_sum else None,
        "size": size[-1] if size else None,
        "weight": weight[-1] if weight else None,
        "timestamps": timestamps,
    }


def bitview_onchain_snapshot(market_cap: float | None = None) -> dict[str, Any]:
    active_addresses, active_addresses_source = bitview_series_latest("active addresses")
    active_addresses_history = bitview_series_history("active addresses")
    exchange_reserves, exchange_reserves_source = bitview_series_latest("exchange reserves")
    exchange_reserves_history = bitview_series_history("exchange reserves")
    mvrv, mvrv_source = bitview_series_latest("mvrv")
    mvrv_history = bitview_series_history("mvrv")
    sopr, sopr_source = bitview_series_latest("sopr")
    sopr_history = bitview_series_history("sopr")
    realized_cap, realized_cap_source = bitview_series_latest("realized_cap")
    realized_cap_history = bitview_series_history("realized_cap")
    nupl, nupl_source = bitview_series_latest("nupl")
    nupl_history = bitview_series_history("nupl")

    computed_nupl = None
    computed_mvrv = None
    if realized_cap and market_cap:
        computed_mvrv = market_cap / realized_cap if realized_cap else None
        computed_nupl = (market_cap - realized_cap) / market_cap if market_cap else None

    latest_mvrv = mvrv if mvrv is not None else computed_mvrv
    latest_nupl = nupl if nupl is not None else computed_nupl
    latest_active_addresses = active_addresses
    latest_exchange_reserves = exchange_reserves

    return {
        "active_addresses": latest_active_addresses,
        "active_addresses_source": active_addresses_source,
        "active_addresses_change_7d": percent_change(active_addresses_history, 7),
        "active_addresses_change_30d": percent_change(active_addresses_history, 30),
        "exchange_reserves": latest_exchange_reserves,
        "exchange_reserves_source": exchange_reserves_source,
        "exchange_reserves_change_7d": percent_change(exchange_reserves_history, 7),
        "exchange_reserves_change_30d": percent_change(exchange_reserves_history, 30),
        "mvrv": latest_mvrv,
        "mvrv_source": mvrv_source or ("computed" if computed_mvrv is not None else None),
        "mvrv_change_7d": percent_change(mvrv_history, 7),
        "mvrv_change_30d": percent_change(mvrv_history, 30),
        "sopr": sopr,
        "sopr_source": sopr_source,
        "sopr_change_7d": percent_change(sopr_history, 7),
        "sopr_change_30d": percent_change(sopr_history, 30),
        "realized_cap": realized_cap,
        "realized_cap_source": realized_cap_source,
        "realized_cap_change_7d": percent_change(realized_cap_history, 7),
        "realized_cap_change_30d": percent_change(realized_cap_history, 30),
        "nupl": latest_nupl,
        "nupl_source": nupl_source or ("computed" if computed_nupl is not None else None),
        "nupl_change_7d": percent_change(nupl_history, 7),
        "nupl_change_30d": percent_change(nupl_history, 30),
        "has_realized_cap": realized_cap is not None,
    }


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


def fetch_binance_premium_index() -> dict[str, Any]:
    url = f"{BINANCE_BASE_URL.rstrip('/')}/fapi/v1/premiumIndex?symbol={BTC_FUTURES_SYMBOL}"
    return fetch_json(url)


def fetch_binance_open_interest() -> dict[str, Any]:
    url = f"{BINANCE_BASE_URL.rstrip('/')}/fapi/v1/openInterest?symbol={BTC_FUTURES_SYMBOL}"
    return fetch_json(url)


def fetch_binance_open_interest_history(limit: int = 30) -> list[dict[str, Any]]:
    url = f"{BINANCE_BASE_URL.rstrip('/')}/futures/data/openInterestHist?pair={BTC_FUTURES_SYMBOL}&contractType=PERPETUAL&period=1d&limit={limit}"
    return fetch_list(url)


def fetch_binance_funding_history(limit: int = 30) -> list[dict[str, Any]]:
    url = f"{BINANCE_BASE_URL.rstrip('/')}/fapi/v1/fundingRate?symbol={BTC_FUTURES_SYMBOL}&limit={limit}"
    return fetch_list(url)


def fetch_binance_spot_ticker() -> dict[str, Any]:
    url = f"{BINANCE_SPOT_BASE_URL.rstrip('/')}/api/v3/ticker/24hr?symbol={BTC_FUTURES_SYMBOL}"
    return fetch_json(url)


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
    history = safe_call(bitview_price_history, [])
    spot_ticker = safe_call(fetch_binance_spot_ticker, {})
    latest = history[-1] if history else {}
    prior_24h = history[-2]["price"] if len(history) >= 2 else (latest.get("price") if isinstance(latest, dict) else None)
    global_data = safe_call(global_snapshot, {})
    blockchain_legacy = safe_call(blockchain_stats, {})
    bitview_blocks = safe_call(bitview_block_metrics, {})
    mempool = safe_call(mempool_fees, {})
    fng = safe_call(fear_greed, {"latest": {}, "history": []})
    binance_premium = safe_call(fetch_binance_premium_index, {})
    binance_oi = safe_call(fetch_binance_open_interest, {})
    binance_oi_history = safe_call(fetch_binance_open_interest_history, [])
    binance_funding_history = safe_call(fetch_binance_funding_history, [])
    hero_metrics, technical_cards, level_rows = build_signals(history)

    current_price: float | None = None
    if isinstance(spot_ticker, dict):
        try:
            current_price = float(spot_ticker.get("lastPrice") or 0) or None
        except (TypeError, ValueError):
            current_price = None
    if current_price is None and isinstance(latest, dict):
        try:
            current_price = float(latest.get("price") or 0) or None
        except (TypeError, ValueError):
            current_price = None

    change_24h: float | None = None
    if isinstance(spot_ticker, dict):
        try:
            change_24h = float(spot_ticker.get("priceChangePercent") or 0) or None
        except (TypeError, ValueError):
            change_24h = None
    if change_24h is None and current_price is not None and prior_24h:
        change_24h = ((current_price - prior_24h) / prior_24h * 100) if prior_24h else None

    quote_volume_24h: float | None = None
    if isinstance(spot_ticker, dict):
        try:
            quote_volume_24h = float(spot_ticker.get("quoteVolume") or 0) or None
        except (TypeError, ValueError):
            quote_volume_24h = None

    circulating_supply_btc = float(blockchain_legacy.get("totalbc", 0) or 0) / 100_000_000
    market_cap = current_price * circulating_supply_btc if current_price is not None and circulating_supply_btc else None
    volume_24h = quote_volume_24h

    btc_dominance: float | None = None
    try:
        btc_dominance = float(global_data.get("market_cap_percentage", {}).get("btc", 0.0) or 0) or None
    except (TypeError, ValueError, AttributeError):
        btc_dominance = None

    total_market_cap: float | None = None
    try:
        total_market_cap = float(global_data.get("total_market_cap", {}).get("usd", 0.0) or 0) or None
    except (TypeError, ValueError, AttributeError):
        total_market_cap = None

    fear_greed_latest = fng.get("latest") or {}
    fear_greed_value = int(fear_greed_latest.get("value", "0") or 0) if fear_greed_latest.get("value") is not None else None
    fear_greed_label = fear_greed_latest.get("value_classification", "Neutral")
    fear_greed_updated = int(fear_greed_latest.get("timestamp", "0") or 0) if fear_greed_latest.get("timestamp") else None

    funding_rate: float | None = None
    mark_price: float | None = None
    estimated_settle_price: float | None = None
    try:
        funding_rate = float(binance_premium.get("lastFundingRate", 0) or 0) or None
        mark_price = float(binance_premium.get("markPrice", 0) or 0) or None
        estimated_settle_price = float(binance_premium.get("estimatedSettlePrice", 0) or 0) or None
    except (TypeError, ValueError, AttributeError):
        funding_rate = None
        mark_price = None
        estimated_settle_price = None

    try:
        open_interest_btc = float(binance_oi.get("openInterest", 0) or 0) or None
    except (TypeError, ValueError, AttributeError):
        open_interest_btc = None

    def parse_rate(item: dict[str, Any]) -> float:
        value = item.get("fundingRate") or 0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    funding_history_rates = [parse_rate(item) for item in binance_funding_history if isinstance(item, dict)]
    open_interest_history_values = [
        float(item.get("sumOpenInterest", item.get("openInterest", 0)) or 0)
        for item in binance_oi_history
        if isinstance(item, dict)
    ]
    funding_avg_7d = sum(funding_history_rates[-7:]) / len(funding_history_rates[-7:]) if funding_history_rates[-7:] else None
    funding_avg_30d = sum(funding_history_rates[-30:]) / len(funding_history_rates[-30:]) if funding_history_rates[-30:] else None
    oi_change_7d = percent_change(open_interest_history_values, 7)
    oi_change_30d = percent_change(open_interest_history_values, 30)

    blocks_total = int(blockchain_legacy.get("n_blocks_total", 0) or 0)
    blocks_to_halving = 210000 - (blocks_total % 210000) if blocks_total else 0
    if blocks_to_halving == 210000:
        blocks_to_halving = 0
    minutes_between_blocks = float(bitview_blocks.get("block_time_minutes", 0.0) or blockchain_legacy.get("minutes_between_blocks", 0.0) or 0.0)
    days_to_halving = (blocks_to_halving * minutes_between_blocks) / 60 / 24 if blocks_to_halving else 0.0
    current_subsidy = 50 / (2 ** (blocks_total // 210000)) if blocks_total else 3.125
    blocks_to_retarget = 2016
    hash_rate_ehs = float(blockchain_legacy.get("hash_rate", 0) or 0) / 1_000_000_000_000_000_000
    difficulty = float(bitview_blocks.get("difficulty", blockchain_legacy.get("difficulty", 0)) or 0)
    miners_revenue_usd = float(blockchain_legacy.get("miners_revenue_usd", 0) or 0)
    n_tx = int(bitview_blocks.get("tx_count", blockchain_legacy.get("n_tx", 0)) or 0)
    estimated_tx_volume = float(bitview_blocks.get("size", blockchain_legacy.get("estimated_transaction_volume_usd", 0)) or 0)
    bitview_onchain = safe_call(lambda: bitview_onchain_snapshot(market_cap=market_cap), {}) if market_cap is not None else safe_call(lambda: bitview_onchain_snapshot(market_cap=None), {})

    prices = [float(point["price"]) for point in history] if history else []
    rsi14 = calculate_rsi(prices) if prices else None
    price_vs_200wma = (
        current_price / latest["ma1400"]
        if current_price is not None and isinstance(latest, dict) and latest.get("ma1400")
        else None
    )

    cycle_score = 0
    if price_vs_200wma is not None:
        cycle_score += 1 if price_vs_200wma >= 1.0 else -1
    if bitview_onchain.get("mvrv") is not None:
        cycle_score += 1 if bitview_onchain["mvrv"] < 1.0 else -1 if bitview_onchain["mvrv"] > 3.0 else 0
    if bitview_onchain.get("nupl") is not None:
        cycle_score += 1 if bitview_onchain["nupl"] < 0.25 else -1 if bitview_onchain["nupl"] > 0.55 else 0
    if bitview_onchain.get("sopr") is not None:
        cycle_score += 1 if bitview_onchain["sopr"] <= 1.0 else -1
    if rsi14 is not None:
        cycle_score += 1 if rsi14 <= 45 else -1 if rsi14 >= 70 else 0
    if cycle_score >= 2:
        cycle_state = "bullish"
        cycle_label = "Low / Accumulation"
        cycle_hint = "Structure is below the heated zone"
    elif cycle_score <= -2:
        cycle_state = "bearish"
        cycle_label = "High / Distribution"
        cycle_hint = "Structure is stretched or overheated"
    else:
        cycle_state = "neutral"
        cycle_label = "Mid / Neutral"
        cycle_hint = "Cycle is balanced and waiting for expansion"

    network_cards = [
        {
            "label": "Hash Rate",
            "value": f"{hash_rate_ehs:,.0f} EH/s" if hash_rate_ehs else "—",
            "hint": "Derived from BitView block weight / activity",
            "state": "bullish" if hash_rate_ehs > 0 else "neutral",
        },
        {
            "label": "Difficulty",
            "value": f"{difficulty:,.0f}" if difficulty else "—",
            "hint": "BitView / Blockchain difficulty",
            "state": "neutral",
        },
        {
            "label": "Block Time",
            "value": f"{minutes_between_blocks:.1f} min" if minutes_between_blocks else "—",
            "hint": "Average block interval",
            "state": "bullish" if minutes_between_blocks and minutes_between_blocks <= 10 else "neutral",
        },
        {
            "label": "Miners Revenue",
            "value": f"${miners_revenue_usd:,.0f}" if miners_revenue_usd else "—",
            "hint": "Blockchain.com revenue estimate",
            "state": "bullish" if miners_revenue_usd > 0 else "neutral",
        },
        {
            "label": "Tx Count",
            "value": f"{n_tx:,}" if n_tx else "—",
            "hint": "Latest BitView block transactions",
            "state": "neutral",
        },
        {
            "label": "Estimated Tx Volume",
            "value": f"${estimated_tx_volume:,.0f}" if estimated_tx_volume else "—",
            "hint": "BitView block size proxy",
            "state": "neutral",
        },
        {
            "label": "Supply",
            "value": f"{circulating_supply_btc:,.2f} BTC" if circulating_supply_btc else "—",
            "hint": "Blockchain.com supply proxy",
            "state": "neutral",
        },
        {
            "label": "Halving",
            "value": f"{blocks_to_halving:,} blocks" if blocks_to_halving else "—",
            "hint": f"~{days_to_halving:.0f} days · reward {current_subsidy:.3f} BTC",
            "state": "neutral",
        },
    ]

    onchain_cards = [
        {
            "label": "MVRV",
            "value": f"{bitview_onchain['mvrv']:.2f}x" if bitview_onchain.get("mvrv") is not None else "—",
            "hint": bitview_onchain.get("mvrv_source") or "BitView / computed",
            "state": "bullish" if (bitview_onchain.get("mvrv") or 0) < 1.0 else "bearish" if (bitview_onchain.get("mvrv") or 0) > 3.0 else "neutral",
        },
        {
            "label": "NUPL",
            "value": f"{bitview_onchain['nupl']:.2f}" if bitview_onchain.get("nupl") is not None else "—",
            "hint": bitview_onchain.get("nupl_source") or "BitView / computed",
            "state": "bullish" if (bitview_onchain.get("nupl") or 0) < 0.25 else "bearish" if (bitview_onchain.get("nupl") or 0) > 0.55 else "neutral",
        },
        {
            "label": "SOPR",
            "value": f"{bitview_onchain['sopr']:.2f}" if bitview_onchain.get("sopr") is not None else "—",
            "hint": bitview_onchain.get("sopr_source") or "BitView",
            "state": "bullish" if (bitview_onchain.get("sopr") or 1.0) <= 1.0 else "bearish",
        },
        {
            "label": "Realized Cap",
            "value": format_compact_money(bitview_onchain["realized_cap"]) if bitview_onchain.get("realized_cap") is not None else "—",
            "hint": "Network cost basis",
            "state": "neutral",
        },
    ]

    derivatives_cards = [
        {
            "label": "Funding",
            "value": f"{funding_rate * 100:+.4f}%" if funding_rate is not None else "—",
            "hint": f"Avg 7d {funding_avg_7d * 100:+.4f}% · 30d {funding_avg_30d * 100:+.4f}%" if funding_avg_7d is not None and funding_avg_30d is not None else "Perp carry",
            "state": "bearish" if funding_rate is not None and funding_rate > 0 else "bullish" if funding_rate is not None and funding_rate < 0 else "neutral",
        },
        {
            "label": "Open Interest",
            "value": f"{open_interest_btc:,.0f} BTC" if open_interest_btc else "—",
            "hint": f"7d {oi_change_7d:+.1f}% · 30d {oi_change_30d:+.1f}%" if oi_change_7d is not None and oi_change_30d is not None else "Perp leverage",
            "state": "bullish" if open_interest_btc is not None and open_interest_btc > 0 else "neutral",
        },
        {
            "label": "Mark price",
            "value": f"${mark_price:,.0f}" if mark_price else "—",
            "hint": f"Est. settle ${estimated_settle_price:,.0f}" if estimated_settle_price else "Binance premium index",
            "state": "neutral",
        },
        {
            "label": "OI regime",
            "value": "Expanding" if (oi_change_7d or 0) > 5 else "Cooling" if (oi_change_7d or 0) < -5 else "Flat",
            "hint": "Leverage participation",
            "state": "bullish" if (oi_change_7d or 0) > 5 else "bearish" if (oi_change_7d or 0) < -5 else "neutral",
        },
    ]

    sentiment_cards = [
        {
            "label": "Fear & Greed",
            "value": f"{fear_greed_value}" if fear_greed_value is not None else "—",
            "hint": fear_greed_label,
            "state": "bearish" if fear_greed_value is not None and fear_greed_value <= 25 else "neutral" if fear_greed_value is not None and fear_greed_value <= 60 else "neutral",
        },
        {
            "label": "BTC Dominance",
            "value": f"{btc_dominance:.1f}%" if btc_dominance is not None else "—",
            "hint": "Share of total crypto market cap",
            "state": "bullish" if btc_dominance is not None and btc_dominance >= 50 else "neutral",
        },
        {
            "label": "Crypto Market Cap",
            "value": f"${total_market_cap / 1_000_000_000_000:.2f}T" if total_market_cap is not None else "—",
            "hint": "Global crypto market size",
            "state": "neutral",
        },
        {
            "label": "Retarget",
            "value": f"{blocks_to_retarget:,} blocks" if blocks_to_retarget else "—",
            "hint": "Next difficulty adjustment",
            "state": "neutral",
        },
    ]

    chart_series = pick_points(history, 420)
    chart_max = max(point["price"] for point in chart_series) if chart_series else None
    chart_min = min(point["price"] for point in chart_series) if chart_series else None

    sources = [
        {"label": "BitView", "url": "https://bitview.space/api"},
        {"label": "Binance", "url": "https://api.binance.com/"},
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
            "regime": "Bull trend" if current_price is not None and isinstance(latest, dict) and latest.get("ma200") and current_price > latest["ma200"] else "Cycle compression" if current_price is not None else None,
            "price_vs_200wma": price_vs_200wma,
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
            "onchain_cards": onchain_cards,
            "derivatives_cards": derivatives_cards,
            "cycle_signal": None if current_price is None and not history else {
                "label": cycle_label,
                "hint": cycle_hint,
                "score": cycle_score,
                "state": cycle_state,
                "rsi14": rsi14,
                "price_vs_200wma": price_vs_200wma,
            },
            "sentiment_cards": sentiment_cards,
        },
        "raw": {
            "blockchain": blockchain_legacy,
            "mempool": mempool,
            "fear_greed": fng,
            "binance": {
                "premium_index": binance_premium,
                "open_interest": binance_oi,
                "funding_history": binance_funding_history,
                "open_interest_history": binance_oi_history,
            },
            "global": global_data,
            "bitview": bitview_onchain,
        },
        "sources": sources,
    }

    return payload


def get_btc_dashboard() -> dict[str, Any]:
    return build_btc_dashboard()
