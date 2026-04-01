"use client";

import { useEffect, useMemo, useState } from "react";

import styles from "./Dashboard.module.css";

type Metric = {
  label: string;
  value: string;
  hint: string;
};

type SymbolHighlight = {
  symbol: string;
  value: string;
  change: string;
};

type EquityPoint = {
  label: string;
  value: number;
};

type Trade = {
  id: number;
  symbol: string;
  side: string;
  quantity: string;
  price: string;
  pnl: string;
  venue: string;
  status: string;
  executed_at: string;
};

type Overview = {
  updated_at: string;
  metrics: Metric[];
  top_symbols: SymbolHighlight[];
  equity_curve: EquityPoint[];
};

type Snapshot = {
  overview: Overview | null;
  trades: Trade[];
  loading: boolean;
  error: string | null;
  updatedLabel: string;
};

function formatMoney(input: string | number) {
  const value = typeof input === "string" ? Number(input) : input;
  const prefix = value >= 0 ? "+" : "-";
  return `${prefix}$${Math.abs(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function formatQuantity(input: string) {
  const value = Number(input);
  return value.toLocaleString("en-US", {
    minimumFractionDigits: value >= 1 ? 2 : 0,
    maximumFractionDigits: 4,
  });
}

function formatTime(value: string) {
  return new Date(value).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function scalePoints(points: EquityPoint[], width: number, height: number) {
  const padding = 14;
  const usableWidth = width - padding * 2;
  const usableHeight = height - padding * 2;
  const values = points.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;

  return points.map((point, index) => {
    const x =
      padding +
      (points.length === 1 ? usableWidth / 2 : (usableWidth * index) / (points.length - 1));
    const y = padding + usableHeight - ((point.value - min) / span) * usableHeight;
    return { x, y };
  });
}

function buildPath(points: EquityPoint[], width: number, height: number) {
  if (!points.length) return "";

  return scalePoints(points, width, height)
    .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(1)} ${point.y.toFixed(1)}`)
    .join(" ");
}

function buildAreaPath(points: EquityPoint[], width: number, height: number) {
  if (!points.length) return "";

  const padding = 14;
  const scaled = scalePoints(points, width, height);
  const lastPoint = scaled[scaled.length - 1];

  return [
    `M ${scaled[0].x.toFixed(1)} ${height - padding}`,
    `L ${scaled[0].x.toFixed(1)} ${scaled[0].y.toFixed(1)}`,
    ...scaled.slice(1).map((point) => `L ${point.x.toFixed(1)} ${point.y.toFixed(1)}`),
    `L ${lastPoint.x.toFixed(1)} ${height - padding}`,
    "Z",
  ].join(" ");
}

export default function Dashboard() {
  const [state, setState] = useState<Snapshot>({
    overview: null,
    trades: [],
    loading: true,
    error: null,
    updatedLabel: "",
  });

  const loadData = async () => {
    setState((current) => ({ ...current, loading: true, error: null }));
    try {
      const [overviewResponse, tradesResponse] = await Promise.all([
        fetch("/api/overview", { cache: "no-store" }),
        fetch("/api/trades?limit=12", { cache: "no-store" }),
      ]);

      if (!overviewResponse.ok || !tradesResponse.ok) {
        throw new Error("Failed to load dashboard data.");
      }

      const [overview, trades] = (await Promise.all([
        overviewResponse.json(),
        tradesResponse.json(),
      ])) as [Overview, Trade[]];

      setState({
        overview,
        trades,
        loading: false,
        error: null,
        updatedLabel: new Date(overview.updated_at).toLocaleString("en-US", {
          dateStyle: "medium",
          timeStyle: "short",
        }),
      });
    } catch (error) {
      setState((current) => ({
        ...current,
        loading: false,
        error: error instanceof Error ? error.message : "Unknown error",
      }));
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  const path = useMemo(() => {
    if (!state.overview?.equity_curve.length) return "";
    return buildPath(state.overview.equity_curve, 800, 280);
  }, [state.overview]);

  const chartArea = useMemo(() => {
    if (!state.overview?.equity_curve.length) return "";
    return buildAreaPath(state.overview.equity_curve, 800, 280);
  }, [state.overview]);

  const latest = state.trades[0];

  return (
    <main className={styles.shell}>
      <section className={styles.hero}>
        <div className={styles.heroCopy}>
          <div className={styles.badge}>Trade Intelligence Console</div>
          <h1>交易数据看板</h1>
          <p>
            一个面向交易记录、收益走势和持仓概览的展示首页。现在是演示数据，后续可以直接接入真实交易源。
          </p>
          <div className={styles.actions}>
            <button className={styles.primaryButton} onClick={() => void loadData()}>
              Refresh Data
            </button>
            <div className={styles.statusChip}>
              {state.loading ? "Syncing..." : `Updated ${state.updatedLabel || "just now"}`}
            </div>
          </div>
        </div>

        <div className={styles.heroPanel}>
          <div className={styles.panelHeader}>
            <span>Market Pulse</span>
            <span className={styles.liveDot}>Live</span>
          </div>
          {state.overview?.metrics.length ? (
            <div className={styles.metricGrid}>
              {state.overview.metrics.slice(0, 4).map((metric) => (
                <article key={metric.label} className={styles.metricCard}>
                  <span>{metric.label}</span>
                  <strong>{metric.value}</strong>
                  <em>{metric.hint}</em>
                </article>
              ))}
            </div>
          ) : (
            <div className={styles.loadingBox}>Loading metrics...</div>
          )}
        </div>
      </section>

      {state.error ? <div className={styles.errorBox}>{state.error}</div> : null}

      <section className={styles.layout}>
        <article className={styles.chartCard}>
          <div className={styles.cardHeader}>
            <div>
              <h2>Equity Curve</h2>
              <p>Sample realized PnL curve derived from recent executions</p>
            </div>
            <div className={styles.cardTag}>24h</div>
          </div>

          <div className={styles.chartFrame}>
            {state.overview?.equity_curve.length ? (
              <svg viewBox="0 0 800 280" role="img" aria-label="Equity curve">
                <defs>
                  <linearGradient id="lineGradient" x1="0" x2="1" y1="0" y2="0">
                    <stop offset="0%" stopColor="#59d5ff" />
                    <stop offset="100%" stopColor="#ffad5b" />
                  </linearGradient>
                  <linearGradient id="fillGradient" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="rgba(89, 213, 255, 0.32)" />
                    <stop offset="100%" stopColor="rgba(89, 213, 255, 0.02)" />
                  </linearGradient>
                </defs>
                <path d={chartArea} fill="url(#fillGradient)" />
                <path d={path} fill="none" stroke="url(#lineGradient)" strokeWidth="4" />
              </svg>
            ) : (
              <div className={styles.loadingBox}>Loading chart...</div>
            )}
          </div>
        </article>

        <aside className={styles.sideStack}>
          <article className={styles.sideCard}>
            <div className={styles.cardHeader}>
              <div>
                <h2>Top Symbols</h2>
                <p>Highest net realized PnL in the current sample set</p>
              </div>
            </div>
            <div className={styles.listStack}>
              {state.overview?.top_symbols.map((item) => (
                <div key={item.symbol} className={styles.symbolRow}>
                  <div>
                    <strong>{item.symbol}</strong>
                    <span>{item.change}</span>
                  </div>
                  <b>{item.value}</b>
                </div>
              ))}
            </div>
          </article>

          <article className={styles.sideCard}>
            <div className={styles.cardHeader}>
              <div>
                <h2>Latest Execution</h2>
                <p>Most recent filled order from the demo feed</p>
              </div>
            </div>
            {latest ? (
              <div className={styles.latestTrade}>
                <div className={styles.tradeSymbol}>{latest.symbol}</div>
                <div className={styles.tradeMeta}>
                  <span>{latest.side}</span>
                  <span>{formatQuantity(latest.quantity)} @ ${Number(latest.price).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
                <div className={styles.tradeFooter}>
                  <span>{latest.venue}</span>
                  <b className={Number(latest.pnl) >= 0 ? styles.good : styles.bad}>
                    {formatMoney(latest.pnl)}
                  </b>
                </div>
              </div>
            ) : (
              <div className={styles.loadingBox}>Loading trade...</div>
            )}
          </article>
        </aside>
      </section>

      <section className={styles.tableCard}>
        <div className={styles.cardHeader}>
          <div>
            <h2>Recent Trades</h2>
            <p>Sorted by newest execution time</p>
          </div>
          <div className={styles.cardTag}>{state.trades.length} rows</div>
        </div>

        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Time</th>
                <th>Symbol</th>
                <th>Side</th>
                <th>Quantity</th>
                <th>Price</th>
                <th>PnL</th>
                <th>Venue</th>
              </tr>
            </thead>
            <tbody>
              {state.trades.map((trade) => (
                <tr key={trade.id}>
                  <td>{formatTime(trade.executed_at)}</td>
                  <td>{trade.symbol}</td>
                  <td>
                    <span className={trade.side === "BUY" ? styles.buy : styles.sell}>
                      {trade.side}
                    </span>
                  </td>
                  <td>{formatQuantity(trade.quantity)}</td>
                  <td>
                    $
                    {Number(trade.price).toLocaleString("en-US", {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                  </td>
                  <td className={Number(trade.pnl) >= 0 ? styles.good : styles.bad}>
                    {formatMoney(trade.pnl)}
                  </td>
                  <td>{trade.venue}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
