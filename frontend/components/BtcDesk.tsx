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
  active_addresses?: number | null;
  active_addresses_source?: string | null;
  active_addresses_change_7d?: number | null;
  active_addresses_change_30d?: number | null;
  exchange_reserves?: number | null;
  exchange_reserves_source?: string | null;
  exchange_reserves_change_7d?: number | null;
  exchange_reserves_change_30d?: number | null;
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
  const mempool: MempoolStats = data?.raw.mempool ?? {};
  const cycleSignal = data?.cycle.cycle_signal;
  const derivativesCards = data?.cycle.derivatives_cards ?? [];
  const sources = data?.sources ?? [];
  const bitview: BitViewStats = data?.raw.bitview ?? {};

  const mempoolFast = mempool.fastestFee ?? null;
  const mempoolHalf = mempool.halfHourFee ?? null;
  const mempoolHour = mempool.hourFee ?? null;
  const fearLatest: FearGreedEntry = data?.raw.fear_greed?.latest ?? {};
  const fearValue = fearLatest.value ?? (data?.hero.fear_greed_value != null ? String(data.hero.fear_greed_value) : "—");
  const fearClass = fearLatest.value_classification ?? data?.hero.fear_greed_label ?? "Neutral";
  const hashRateEh = typeof blockchain.hash_rate === "number" ? blockchain.hash_rate / 1_000_000_000_000_000_000 : null;
  const blockTime = typeof blockchain.minutes_between_blocks === "number" ? blockchain.minutes_between_blocks : null;
  const difficulty = typeof blockchain.difficulty === "number" ? blockchain.difficulty : null;
  const txVolume = typeof blockchain.estimated_transaction_volume_usd === "number" ? blockchain.estimated_transaction_volume_usd : null;
  const activeAddresses = typeof bitview.active_addresses === "number" ? bitview.active_addresses : null;
  const exchangeReserves = typeof bitview.exchange_reserves === "number" ? bitview.exchange_reserves : null;
  const mvrv = typeof bitview.mvrv === "number" ? bitview.mvrv : null;
  const nupl = typeof bitview.nupl === "number" ? bitview.nupl : null;
  const sopr = typeof bitview.sopr === "number" ? bitview.sopr : null;
  const realizedCap = typeof bitview.realized_cap === "number" ? bitview.realized_cap : null;

  const chainRows = [
    {
      label: "Hash rate",
      value: hashRateEh != null ? `${formatNumber(hashRateEh, 0)} EH/s` : "—",
      hint: "Network work rate",
    },
    {
      label: "Difficulty",
      value: formatOptionalNumber(difficulty, 0),
      hint: "Next retarget balances the chain",
    },
    {
      label: "Block time",
      value: blockTime != null ? `${formatNumber(blockTime, 1)} min` : "—",
      hint: "Faster blocks usually mean fuller mempool",
    },
    {
      label: "Tx volume",
      value: formatOptionalCompact(txVolume),
      hint: "Estimated value settled on-chain",
    },
    {
      label: "Active addresses",
      value: activeAddresses != null ? formatCompactCount(activeAddresses) : "—",
      hint: bitview.active_addresses_source || "Network participants",
    },
    {
      label: "Exchange reserves",
      value: exchangeReserves != null ? formatCompactCount(exchangeReserves) : "—",
      hint: bitview.exchange_reserves_source || "Coins sitting on exchanges",
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
    {
      label: "SOPR",
      value: sopr != null ? formatNumber(sopr, 2) : "—",
      hint: bitview.sopr_source || "Spent output profit ratio",
    },
    {
      label: "Realized cap",
      value: realizedCap != null ? formatCompact(realizedCap) : "—",
      hint: bitview.realized_cap_source || "Network cost basis",
    },
  ];

  const flowRows = [
    {
      label: "Fear & Greed",
      value: `${fearValue} / ${fearClass}`,
      hint: "Crowd temperature",
    },
    {
      label: "BTC dominance",
      value: data?.hero.btc_dominance != null ? `${formatNumber(data.hero.btc_dominance, 1)}%` : "—",
      hint: "BTC share of total crypto cap",
    },
    {
      label: "Fast fee",
      value: mempoolFast != null ? `${mempoolFast} sat/vB` : "—",
      hint: "Immediate congestion",
    },
    {
      label: "30m / 1h fee",
      value: `${mempoolHalf != null ? `${mempoolHalf}` : "—"} / ${mempoolHour != null ? `${mempoolHour}` : "—"}`,
      hint: "Mempool heat ladder",
    },
  ];

  const structureRows = [
    {
      label: "Price vs 200WMA",
      value: data?.hero.price_vs_200wma != null ? `${formatNumber(data.hero.price_vs_200wma, 2)}x` : "—",
      hint: "Cycle location",
    },
    {
      label: "MA stack",
      value: data?.hero.regime ?? "—",
      hint: "Spot / short / medium trend",
    },
    {
      label: "Price",
      value: formatOptionalPrice(data?.hero.price),
      hint: "Top-line BTC state",
    },
    {
      label: "Bias",
      value: data?.hero.regime ?? "—",
      hint: "Structure summary",
    },
  ];

  const valuationRows = [
    {
      label: "MVRV",
      value: mvrv != null ? `${formatNumber(mvrv, 2)}x` : "—",
      hint: `7d ${formatDelta(bitview.mvrv_change_7d)} · 30d ${formatDelta(bitview.mvrv_change_30d)}`,
    },
    {
      label: "NUPL",
      value: nupl != null ? formatNumber(nupl, 2) : "—",
      hint: `7d ${formatDelta(bitview.nupl_change_7d)} · 30d ${formatDelta(bitview.nupl_change_30d)}`,
    },
    {
      label: "SOPR",
      value: sopr != null ? formatNumber(sopr, 2) : "—",
      hint: `7d ${formatDelta(bitview.sopr_change_7d)} · 30d ${formatDelta(bitview.sopr_change_30d)}`,
    },
    {
      label: "Realized cap",
      value: realizedCap != null ? formatCompact(realizedCap) : "—",
      hint: `7d ${formatDelta(bitview.realized_cap_change_7d)} · 30d ${formatDelta(bitview.realized_cap_change_30d)}`,
    },
  ];

  const cycleProgress = cycleSignal
    ? Math.max(0, Math.min(100, ((cycleSignal.score + 4) / 8) * 100))
    : 50;

  const onChainMetrics = [
    chainRows[0],
    chainRows[4],
    chainRows[5],
    valuationRows[0],
  ].filter((item): item is InsightMetric => Boolean(item));

  const flowMetrics = [
    flowRows[0],
    flowRows[1],
    derivativesCards[0],
    derivativesCards[1],
  ].filter((item): item is InsightMetric => Boolean(item));

  const cycleMetrics = [
    structureRows[0],
    structureRows[1],
    valuationRows[1],
    valuationRows[2],
  ].filter((item): item is InsightMetric => Boolean(item));

  return (
    <main className={styles.shell}>
      <div className={styles.orb} />
      <div className={styles.gridGlow} />

      <header className={styles.header}>
        <div className={styles.headerText}>
          <div className={styles.kicker}>BTC live desk</div>
          <h1>BTC 三区工作台</h1>
          <p>只看链上、资金、周期。价格只作为顶栏状态，不再占一个区块。</p>
        </div>

        <div className={styles.headerMeta}>
          <div className={styles.metaTile}>
            <span>Updated</span>
            <strong>{state.refreshedAt || "—"}</strong>
          </div>
          <div className={styles.metaTile}>
            <span>Live BTC</span>
            <strong className={data?.hero.change_24h != null ? (data.hero.change_24h >= 0 ? styles.good : styles.bad) : ""}>
              {formatOptionalPrice(data?.hero.price)} · {formatOptionalChange(data?.hero.change_24h)}
            </strong>
          </div>
          <div className={styles.metaTile}>
            <span>Cycle</span>
            <strong className={cycleSignal?.state === "bullish" ? styles.good : cycleSignal?.state === "bearish" ? styles.bad : ""}>
              {cycleSignal?.label ?? "—"}
            </strong>
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
              <p>把供给、活跃度和估值放在一起看。</p>
            </div>
          </div>
          <div className={styles.sectionGrid}>
            {onChainMetrics.map((item) => (
              <article key={item.label} className={styles.metricCard}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <em>{item.hint}</em>
              </article>
            ))}
          </div>
        </article>

        <article className={styles.workspaceSection}>
          <div className={styles.sectionHeader}>
            <div>
              <span className={styles.panelTag}>Flow</span>
              <h3>资金</h3>
              <p>只保留资金和衍生品相关的压力点。</p>
            </div>
          </div>
          <div className={styles.sectionGrid}>
            {flowMetrics.map((item) => (
              <article key={item.label} className={styles.metricCard}>
                <span>{item.label}</span>
                <strong className={item.state === "bullish" ? styles.good : item.state === "bearish" ? styles.bad : ""}>
                  {item.value}
                </strong>
                <em>{item.hint}</em>
              </article>
            ))}
          </div>
        </article>

        <article className={styles.workspaceSection}>
          <div className={styles.sectionHeader}>
            <div>
              <span className={styles.panelTag}>Cycle</span>
              <h3>周期</h3>
              <p>周期只回答一个问题：现在偏低、偏中还是偏高。</p>
            </div>
          </div>
          <div className={styles.cycleSignal}>
            <div>
              <span>Cycle signal</span>
              <strong className={cycleSignal?.state === "bullish" ? styles.good : cycleSignal?.state === "bearish" ? styles.bad : ""}>
                {cycleSignal?.label ?? "—"}
              </strong>
            </div>
            <p>{cycleSignal?.hint ?? "Waiting for live cycle data"}</p>
            <small>
              RSI {cycleSignal?.rsi14 != null ? formatNumber(cycleSignal.rsi14, 1) : "—"} · Price / 200WMA{" "}
              {cycleSignal?.price_vs_200wma != null ? formatNumber(cycleSignal.price_vs_200wma, 2) : "—"}x · Score {cycleSignal?.score ?? "—"}
            </small>
            <div className={styles.cycleBar}>
              <div className={styles.cycleBarScale}>
                <span>Low</span>
                <span>Neutral</span>
                <span>High</span>
              </div>
              <div className={styles.cycleBarTrack} aria-hidden="true">
                <div className={styles.cycleBarFill} style={{ width: `${cycleProgress}%` }} />
                <div className={styles.cycleBarMarker} style={{ left: `${cycleProgress}%` }} />
              </div>
            </div>
            <div className={styles.cycleLegend}>
              <span className={styles.cycleLegendLow}>Low</span>
              <span className={styles.cycleLegendMid}>Neutral</span>
              <span className={styles.cycleLegendHigh}>High</span>
            </div>
          </div>
          <div className={styles.sectionGrid}>
            {cycleMetrics.map((item) => (
              <article key={item.label} className={styles.metricCard}>
                <span>{item.label}</span>
                <strong className={item.state === "bullish" ? styles.good : item.state === "bearish" ? styles.bad : ""}>
                  {item.value}
                </strong>
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
