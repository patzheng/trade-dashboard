"use client";

import { useEffect, useMemo, useState } from "react";

import styles from "./Dashboard.module.css";

type Metric = {
  label: string;
  value: string;
  hint: string;
};

type MarketSummary = {
  market: string;
  label: string;
  currency: string;
  trade_count: number;
  active_symbols: number;
  net_pnl: number;
  turnover: number;
  change_pct: number;
  last_sync: string;
};

type WatchlistItem = {
  symbol: string;
  market: string;
  label: string;
  venue: string;
  last_price: number;
  change_pct: number;
  position_hint: string;
  note: string;
};

type TradeView = {
  id: number;
  market: string;
  symbol: string;
  side: string;
  quantity: string;
  price: string;
  pnl: string;
  venue: string;
  status: string;
  executed_at: string;
};

type DashboardResponse = {
  updated_at: string;
  metrics: Metric[];
  risk_metrics: Metric[];
  exposure: {
    label: string;
    market: string;
    gross_notional: number;
    net_pnl: number;
    share_pct: number;
    risk: string;
  }[];
  markets: MarketSummary[];
  watchlist: WatchlistItem[];
  recent_trades: TradeView[];
  focus_market: string;
};

const MARKET_TABS = [
  { key: "all", label: "全市场" },
  { key: "crypto", label: "BTC" },
  { key: "cn_stock", label: "A股" },
  { key: "hk_stock", label: "港股" },
  { key: "us_stock", label: "美股" },
  { key: "futures", label: "商品期货" },
];

function formatMoney(value: number | string) {
  const numeric = typeof value === "string" ? Number(value) : value;
  const sign = numeric >= 0 ? "+" : "-";
  return `${sign}$${Math.abs(numeric).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function formatCompact(value: number) {
  const abs = Math.abs(value);
  const sign = value >= 0 ? "+" : "-";
  if (abs >= 1_000_000_000) return `${sign}$${(abs / 1_000_000_000).toFixed(2)}B`;
  if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `${sign}$${(abs / 1_000).toFixed(2)}K`;
  return formatMoney(value);
}

function formatQuantity(value: string) {
  const numeric = Number(value);
  return numeric.toLocaleString("en-US", {
    minimumFractionDigits: numeric >= 1 ? 2 : 0,
    maximumFractionDigits: 4,
  });
}

function formatTime(value: string) {
  return new Date(value).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function marketLabel(market: string, fallback: string) {
  return MARKET_TABS.find((tab) => tab.key === market)?.label ?? fallback;
}

function buildCurve(trades: TradeView[]) {
  if (!trades.length) return "";

  const width = 900;
  const height = 260;
  const padding = 18;
  const values: number[] = [];
  let cumulative = 0;
  trades
    .slice()
    .reverse()
    .forEach((trade) => {
      cumulative += Number(trade.pnl);
      values.push(cumulative);
    });

  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const usableWidth = width - padding * 2;
  const usableHeight = height - padding * 2;

  return values
    .map((point, index) => {
      const x = padding + (values.length === 1 ? usableWidth / 2 : (usableWidth * index) / (values.length - 1));
      const y = padding + usableHeight - ((point - min) / span) * usableHeight;
      return `${index === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ");
}

export default function Dashboard() {
  const [selectedMarket, setSelectedMarket] = useState("all");
  const [state, setState] = useState<{
    data: DashboardResponse | null;
    loading: boolean;
    error: string | null;
    refreshedAt: string;
  }>({
    data: null,
    loading: true,
    error: null,
    refreshedAt: "",
  });

  const loadData = async (market = selectedMarket) => {
    setState((current) => ({ ...current, loading: true, error: null }));
    try {
      const response = await fetch(`/api/dashboard?market=${market}`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error("Failed to load dashboard data.");
      }
      const data = (await response.json()) as DashboardResponse;
      setSelectedMarket(data.focus_market);
      setState({
        data,
        loading: false,
        error: null,
        refreshedAt: new Date(data.updated_at).toLocaleString("zh-CN", {
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
    void loadData(selectedMarket);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedMarket]);

  const curvePath = useMemo(() => buildCurve(state.data?.recent_trades ?? []), [state.data]);
  const activeMarket = selectedMarket;

  const marketSummaries = state.data?.markets ?? [];
  const riskMetrics = state.data?.risk_metrics ?? [];
  const exposures = state.data?.exposure ?? [];
  const watchlist = state.data?.watchlist ?? [];
  const recentTrades = state.data?.recent_trades ?? [];

  return (
    <main className={styles.shell}>
      <header className={styles.header}>
        <div>
          <div className={styles.kicker}>Personal Trading Console</div>
          <h1>多市场交易总览</h1>
          <p>
            BTC、A股、港股、美股和商品期货统一在一个工作台里看，后面接真实数据时只需要替换后端来源。
          </p>
        </div>

        <div className={styles.headerMeta}>
          <div>
            <span>Last sync</span>
            <strong>{state.refreshedAt || "—"}</strong>
          </div>
          <button className={styles.refreshButton} onClick={() => void loadData(activeMarket)}>
            Refresh
          </button>
        </div>
      </header>

      {state.error ? <div className={styles.errorBanner}>{state.error}</div> : null}

      <section className={styles.metricRow}>
        {state.data?.metrics.map((metric, index) => (
          <article key={metric.label} className={styles.metricCard} style={{ animationDelay: `${index * 70}ms` }}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            <em>{metric.hint}</em>
          </article>
        ))}
      </section>

      <section className={styles.riskStrip}>
        <div className={styles.sectionHeader}>
          <div>
            <h2>Risk view</h2>
            <p>集中度、暴露和最近损失，给你一个快速风险快照。</p>
          </div>
        </div>

        <div className={styles.riskGrid}>
          {riskMetrics.map((item, index) => (
            <article key={item.label} className={styles.riskCard} style={{ animationDelay: `${index * 60}ms` }}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <em>{item.hint}</em>
            </article>
          ))}
        </div>

        <div className={styles.exposureGrid}>
          {exposures.map((row, index) => (
            <div key={row.market} className={styles.exposureRow} style={{ animationDelay: `${index * 45}ms` }}>
              <div>
                <strong>{row.label}</strong>
                <span>
                  {row.share_pct.toFixed(1)}% of gross exposure · {formatCompact(row.gross_notional)}
                </span>
              </div>
              <div className={styles.exposureMeta}>
                <b className={row.net_pnl >= 0 ? styles.good : styles.bad}>{formatMoney(row.net_pnl)}</b>
                <small>{row.risk} risk</small>
              </div>
            </div>
          ))}
        </div>
      </section>

      <nav className={styles.tabBar} aria-label="Market tabs">
        {MARKET_TABS.map((tab) => (
          <button
            key={tab.key}
            className={`${styles.tab} ${activeMarket === tab.key ? styles.tabActive : ""}`}
            onClick={() => setSelectedMarket(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <section className={styles.workspace}>
        <article className={styles.mainPanel}>
          <div className={styles.panelHeading}>
            <div>
              <h2>{marketLabel(activeMarket, "全市场")}</h2>
              <p>最近成交驱动的累计盈亏曲线，以及全市场摘要。</p>
            </div>
            <div className={styles.scopeChip}>
              {activeMarket === "all" ? "Scope: all markets" : `Scope: ${marketLabel(activeMarket, activeMarket)}`}
            </div>
          </div>

          <div className={styles.chartFrame}>
            {curvePath ? (
              <svg viewBox="0 0 900 260" role="img" aria-label="Cumulative PnL curve">
                <defs>
                  <linearGradient id="curveStroke" x1="0" x2="1" y1="0" y2="0">
                    <stop offset="0%" stopColor="#59d5ff" />
                    <stop offset="100%" stopColor="#ffad5b" />
                  </linearGradient>
                  <linearGradient id="curveFill" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="rgba(89, 213, 255, 0.30)" />
                    <stop offset="100%" stopColor="rgba(89, 213, 255, 0.02)" />
                  </linearGradient>
                </defs>
                <path d={curvePath} fill="url(#curveFill)" />
                <path d={curvePath} fill="none" stroke="url(#curveStroke)" strokeWidth="4" />
              </svg>
            ) : (
              <div className={styles.loadingBox}>No trades in this scope.</div>
            )}
          </div>

          <div className={styles.summaryGrid}>
            {marketSummaries.map((market) => (
              <div key={market.market} className={`${styles.summaryRow} ${activeMarket === market.market ? styles.summaryRowActive : ""}`}>
                <div>
                  <strong>{market.label}</strong>
                  <span>
                    {market.trade_count} trades · {market.active_symbols} symbols · {market.currency}
                  </span>
                </div>
                <div className={styles.summaryNumbers}>
                  <b className={market.net_pnl >= 0 ? styles.good : styles.bad}>{formatMoney(market.net_pnl)}</b>
                  <small>{formatCompact(market.turnover)}</small>
                </div>
              </div>
            ))}
          </div>
        </article>

        <aside className={styles.sideRail}>
          <section className={styles.sidePanel}>
            <div className={styles.panelHeading}>
              <div>
                <h2>Watchlist</h2>
                <p>按最新 PnL 绝对值排序，便于先看最活跃的票。</p>
              </div>
            </div>

            <div className={styles.listStack}>
              {watchlist.map((item, index) => (
                <article key={item.symbol} className={styles.watchRow} style={{ animationDelay: `${index * 50}ms` }}>
                  <div>
                    <strong>{item.label}</strong>
                    <span>
                      {item.note} · {item.venue}
                    </span>
                  </div>
                  <div className={styles.watchMeta}>
                    <b className={item.change_pct >= 0 ? styles.good : styles.bad}>
                      {item.change_pct >= 0 ? "+" : ""}
                      {item.change_pct.toFixed(2)}%
                    </b>
                    <small>{item.position_hint}</small>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className={styles.sidePanel}>
            <div className={styles.panelHeading}>
              <div>
                <h2>Recent trades</h2>
                <p>当前 scope 下的最新成交记录。</p>
              </div>
            </div>

            <div className={styles.tradeList}>
              {recentTrades.map((trade, index) => (
                <div key={trade.id} className={styles.tradeRow} style={{ animationDelay: `${index * 45}ms` }}>
                  <div>
                    <strong>{trade.symbol}</strong>
                    <span>
                      {marketLabel(trade.market, trade.market)} · {formatTime(trade.executed_at)}
                    </span>
                  </div>
                  <div className={styles.tradeMeta}>
                    <b className={trade.pnl >= 0 ? styles.good : styles.bad}>{formatMoney(trade.pnl)}</b>
                    <small>
                      {trade.side} · {formatQuantity(trade.quantity)} @ {Number(trade.price).toLocaleString("en-US", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </small>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </aside>
      </section>
    </main>
  );
}
