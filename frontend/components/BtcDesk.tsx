"use client";

import { useEffect, useState } from "react";

import styles from "./BtcDesk.module.css";

type ChartPoint = {
  timestamp: string;
  price: number;
  market_cap: number | null;
  volume: number | null;
  ma7: number;
  ma50: number;
  ma200: number;
  ma1400: number;
};

type InsightMetric = {
  label: string;
  value: string;
  hint: string;
  state?: string;
};

type KeyLevel = {
  label: string;
  price: number;
  note: string;
  side: string;
};

type BtcApiResponse = {
  updated_at: string;
  hero: {
    symbol: string;
    price: number | null;
    change_24h: number | null;
    market_cap: number | null;
    volume_24h: number | null;
    btc_dominance: number | null;
    fear_greed_value: number | null;
    fear_greed_label: string;
    fear_greed_updated_at: string | null;
    regime: string | null;
    price_vs_200wma: number | null;
  };
  chart: {
    series: ChartPoint[];
    min: number | null;
    max: number | null;
  };
  cycle: {
    hero_metrics: InsightMetric[];
    technical_cards: InsightMetric[];
    level_rows: KeyLevel[];
    network_cards: InsightMetric[];
    onchain_cards: InsightMetric[];
    derivatives_cards: InsightMetric[];
    cycle_signal: {
      label: string;
      hint: string;
      score: number;
      state: string;
      rsi14: number | null;
      price_vs_200wma: number | null;
    } | null;
    sentiment_cards: InsightMetric[];
  };
  raw: {
    blockchain?: BtcBlockchainStats;
    mempool?: MempoolStats;
    fear_greed?: {
      latest?: FearGreedEntry;
    };
    bitview?: BitViewStats;
    global?: Record<string, unknown>;
  };
  sources: { label: string; url: string }[];
};

type BtcBlockchainStats = {
  minutes_between_blocks?: number | null;
  hash_rate?: number | null;
  difficulty?: number | null;
  miners_revenue_usd?: number | null;
  estimated_transaction_volume_usd?: number | null;
};

type MempoolStats = {
  fastestFee?: number | null;
  halfHourFee?: number | null;
  hourFee?: number | null;
};

type FearGreedEntry = {
  value?: string;
  value_classification?: string;
  timestamp?: string;
};

type BitViewStats = {
  addr_count?: number | null;
  addr_count_source?: string | null;
  addr_count_change_7d?: number | null;
  addr_count_change_30d?: number | null;
  mvrv?: number | null;
  mvrv_source?: string | null;
  mvrv_change_7d?: number | null;
  mvrv_change_30d?: number | null;
  sopr?: number | null;
  sopr_source?: string | null;
  sopr_change_7d?: number | null;
  sopr_change_30d?: number | null;
  realized_cap?: number | null;
  realized_cap_source?: string | null;
  realized_cap_change_7d?: number | null;
  realized_cap_change_30d?: number | null;
  nupl?: number | null;
  nupl_source?: string | null;
  nupl_change_7d?: number | null;
  nupl_change_30d?: number | null;
};

function formatPrice(value: number, digits = 0) {
  return `$${value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}`;
}

function formatChange(value: number) {
  const prefix = value >= 0 ? "+" : "";
  return `${prefix}${value.toFixed(2)}%`;
}

function formatOptionalChange(value: number | null | undefined) {
  return value == null || Number.isNaN(value) ? "—" : formatChange(value);
}

function formatCompact(value: number) {
  const abs = Math.abs(value);
  const sign = value >= 0 ? "+" : "-";
  if (abs >= 1_000_000_000_000) return `${sign}$${(abs / 1_000_000_000_000).toFixed(2)}T`;
  if (abs >= 1_000_000_000) return `${sign}$${(abs / 1_000_000_000).toFixed(2)}B`;
  if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `${sign}$${(abs / 1_000).toFixed(2)}K`;
  return formatPrice(value);
}

function formatCompactCount(value: number) {
  const abs = Math.abs(value);
  const sign = value >= 0 ? "" : "-";
  if (abs >= 1_000_000_000_000) return `${sign}${(abs / 1_000_000_000_000).toFixed(2)}T`;
  if (abs >= 1_000_000_000) return `${sign}${(abs / 1_000_000_000).toFixed(2)}B`;
  if (abs >= 1_000_000) return `${sign}${(abs / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `${sign}${(abs / 1_000).toFixed(2)}K`;
  return `${sign}${abs.toLocaleString("en-US")}`;
}

function formatNumber(value: number, digits = 1) {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function formatOptionalNumber(value: number | null | undefined, digits = 1) {
  return value == null || Number.isNaN(value) ? "—" : formatNumber(value, digits);
}

function formatOptionalPrice(value: number | null | undefined, digits = 0) {
  return value == null || Number.isNaN(value) ? "—" : formatPrice(value, digits);
}

function formatOptionalCompact(value: number | null | undefined) {
  return value == null || Number.isNaN(value) ? "—" : formatCompact(value);
}

function formatOptionalCompactCount(value: number | null | undefined) {
  return value == null || Number.isNaN(value) ? "—" : formatCompactCount(value);
}

function formatDelta(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) {
    return "n/a";
  }
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${formatNumber(value, 1)}%`;
}


export default function BtcDesk() {
  const [state, setState] = useState<{
    data: BtcApiResponse | null;
    loading: boolean;
    error: string | null;
    refreshedAt: string;
  }>({
    data: null,
    loading: true,
    error: null,
    refreshedAt: "",
  });

  const loadData = async () => {
    setState((current) => ({ ...current, loading: true, error: null }));
    try {
      const response = await fetch("/api/btc", { cache: "no-store" });
      if (!response.ok) {
        throw new Error("Failed to load BTC desk data.");
      }
      const data = (await response.json()) as BtcApiResponse;
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
        data: null,
        loading: false,
        error: error instanceof Error ? error.message : "Unknown error",
      }));
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  const data = state.data;

  const blockchain: BtcBlockchainStats = data?.raw.blockchain ?? {};
  const sources = data?.sources ?? [];
  const bitview: BitViewStats = data?.raw.bitview ?? {};

  const addrCount = typeof bitview.addr_count === "number" ? bitview.addr_count : null;
  const mvrv = typeof bitview.mvrv === "number" ? bitview.mvrv : null;
  const nupl = typeof bitview.nupl === "number" ? bitview.nupl : null;

  const chainRows = [
    {
      label: "Addr count",
      value: addrCount != null ? formatCompactCount(addrCount) : "—",
      hint: bitview.addr_count_source || "Network participants",
    },
    {
      label: "MVRV",
      value: mvrv != null ? `${formatNumber(mvrv, 2)}x` : "—",
      hint: bitview.mvrv_source || "Network valuation multiple",
    },
    {
      label: "NUPL",
      value: nupl != null ? formatNumber(nupl, 2) : "—",
      hint: bitview.nupl_source || "Profit / loss balance",
    },
  ];

  return (
    <main className={styles.shell}>
      <div className={styles.orb} />
      <div className={styles.gridGlow} />

      <header className={styles.header}>
        <div className={styles.headerText}>
          <div className={styles.kicker}>BTC live desk</div>
          <h1>BTC 链上工作台</h1>
          <p>只保留链上一个区域。没有数据就空着，不再显示价格、资金、周期区块。</p>
        </div>

        <div className={styles.headerMeta}>
          <div className={styles.metaTile}>
            <span>Updated</span>
            <strong>{state.refreshedAt || "—"}</strong>
          </div>
          <button className={styles.refreshButton} onClick={() => void loadData()} disabled={state.loading}>
            {state.loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </header>

      {state.error ? <div className={styles.errorBanner}>{state.error}</div> : null}

      <section className={styles.workspace}>
        <article className={styles.workspaceSection}>
          <div className={styles.sectionHeader}>
            <div>
              <span className={styles.panelTag}>On-chain</span>
              <h3>链上</h3>
              <p>只看 BitView 已确认存在的核心 series：活动、估值、情绪。</p>
            </div>
            <div className={styles.sectionStatus}>
              <strong>{chainRows.filter((item) => item.value !== "—").length}</strong>
              <span>live</span>
            </div>
          </div>
          <div className={styles.sectionGrid}>
            {chainRows.map((item) => (
              <article key={item.label} className={styles.metricCard}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <em>{item.hint}</em>
              </article>
            ))}
          </div>
        </article>
      </section>

      <footer className={styles.footer}>
        <div>
          <span>Freshness</span>
          <strong>{state.refreshedAt || "—"}</strong>
        </div>
        <div>
          <span>Area</span>
          <strong>On-chain only</strong>
        </div>
        <div className={styles.sourceList}>
          {sources.map((source) => (
            <a key={source.label} href={source.url} target="_blank" rel="noreferrer">
              {source.label}
            </a>
          ))}
        </div>
      </footer>
    </main>
  );
}
