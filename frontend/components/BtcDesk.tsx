"use client";

import { useEffect, useMemo, useState } from "react";

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
  state: string;
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
    price: number;
    change_24h: number;
    market_cap: number;
    volume_24h: number;
    btc_dominance: number;
    fear_greed_value: number;
    fear_greed_label: string;
    fear_greed_updated_at: string | null;
    regime: string;
    price_vs_200wma: number;
  };
  chart: {
    series: ChartPoint[];
    min: number;
    max: number;
  };
  cycle: {
    hero_metrics: InsightMetric[];
    technical_cards: InsightMetric[];
    level_rows: KeyLevel[];
    network_cards: InsightMetric[];
    sentiment_cards: InsightMetric[];
  };
  raw: {
    blockchain?: BtcBlockchainStats;
    mempool?: MempoolStats;
    fear_greed?: {
      latest?: FearGreedEntry;
    };
    global?: Record<string, unknown>;
  };
  sources: { label: string; url: string }[];
};

type BtcBlockchainStats = {
  minutes_between_blocks?: number;
  hash_rate?: number;
  difficulty?: number;
  miners_revenue_usd?: number;
  estimated_transaction_volume_usd?: number;
};

type MempoolStats = {
  fastestFee?: number;
  halfHourFee?: number;
  hourFee?: number;
};

type FearGreedEntry = {
  value?: string;
  value_classification?: string;
  timestamp?: string;
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

function formatCompact(value: number) {
  const abs = Math.abs(value);
  const sign = value >= 0 ? "+" : "-";
  if (abs >= 1_000_000_000_000) return `${sign}$${(abs / 1_000_000_000_000).toFixed(2)}T`;
  if (abs >= 1_000_000_000) return `${sign}$${(abs / 1_000_000_000).toFixed(2)}B`;
  if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `${sign}$${(abs / 1_000).toFixed(2)}K`;
  return formatPrice(value);
}

function formatNumber(value: number, digits = 1) {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
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

function scaleChart(series: ChartPoint[], width: number, height: number) {
  const padding = 20;
  const values = series.flatMap((point) => [point.price, point.ma7, point.ma50, point.ma200, point.ma1400]).filter(Number.isFinite);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const usableWidth = width - padding * 2;
  const usableHeight = height - padding * 2;

  return series.map((point, index) => {
    const x = padding + (series.length === 1 ? usableWidth / 2 : (usableWidth * index) / (series.length - 1));
    const priceY = padding + usableHeight - ((point.price - min) / span) * usableHeight;
    const ma7Y = padding + usableHeight - ((point.ma7 - min) / span) * usableHeight;
    const ma50Y = padding + usableHeight - ((point.ma50 - min) / span) * usableHeight;
    const ma200Y = padding + usableHeight - ((point.ma200 - min) / span) * usableHeight;
    const ma1400Y = padding + usableHeight - ((point.ma1400 - min) / span) * usableHeight;
    return { x, priceY, ma7Y, ma50Y, ma200Y, ma1400Y };
  });
}

function pathFrom(points: { x: number; y: number }[]) {
  if (!points.length) return "";
  return points
    .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(1)} ${point.y.toFixed(1)}`)
    .join(" ");
}

function areaFrom(points: { x: number; y: number }[], height: number) {
  if (!points.length) return "";
  const padding = 20;
  const lastPoint = points[points.length - 1];
  return [
    `M ${points[0].x.toFixed(1)} ${height - padding}`,
    `L ${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`,
    ...points.slice(1).map((point) => `L ${point.x.toFixed(1)} ${point.y.toFixed(1)}`),
    `L ${lastPoint.x.toFixed(1)} ${height - padding}`,
    "Z",
  ].join(" ");
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
        loading: false,
        error: error instanceof Error ? error.message : "Unknown error",
      }));
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  const data = state.data;
  const series = data?.chart.series ?? [];
  const layout = useMemo(() => scaleChart(series, 1200, 440), [series]);
  const pricePath = useMemo(() => pathFrom(layout.map((point) => ({ x: point.x, y: point.priceY }))), [layout]);
  const areaPath = useMemo(() => areaFrom(layout.map((point) => ({ x: point.x, y: point.priceY })), 440), [layout]);
  const ma7Path = useMemo(() => pathFrom(layout.map((point) => ({ x: point.x, y: point.ma7Y }))), [layout]);
  const ma50Path = useMemo(() => pathFrom(layout.map((point) => ({ x: point.x, y: point.ma50Y }))), [layout]);
  const ma200Path = useMemo(() => pathFrom(layout.map((point) => ({ x: point.x, y: point.ma200Y }))), [layout]);
  const ma1400Path = useMemo(() => pathFrom(layout.map((point) => ({ x: point.x, y: point.ma1400Y }))), [layout]);

  const blockchain: BtcBlockchainStats = data?.raw.blockchain ?? {};
  const mempool: MempoolStats = data?.raw.mempool ?? {};
  const networkCards = data?.cycle.network_cards ?? [];
  const heroMetrics = data?.cycle.hero_metrics ?? [];
  const technicalCards = data?.cycle.technical_cards ?? [];
  const sentimentCards = data?.cycle.sentiment_cards ?? [];
  const levels = data?.cycle.level_rows ?? [];
  const sources = data?.sources ?? [];

  const latestPoint = series[series.length - 1];
  const earliestPoint = series[0];
  const priceRange = data ? data.chart.max - data.chart.min : 0;
  const mempoolFast = mempool.fastestFee ?? null;
  const mempoolHalf = mempool.halfHourFee ?? null;
  const mempoolHour = mempool.hourFee ?? null;
  const fearLatest: FearGreedEntry = data?.raw.fear_greed?.latest ?? {};
  const fearValue = fearLatest.value ?? String(data?.hero.fear_greed_value ?? "0");
  const fearClass = fearLatest.value_classification ?? data?.hero.fear_greed_label ?? "Neutral";
  const hashRateEh = Number(blockchain.hash_rate ?? 0) / 1_000_000_000_000_000_000;
  const blockTime = Number(blockchain.minutes_between_blocks ?? 0);
  const difficulty = Number(blockchain.difficulty ?? 0);
  const txVolume = Number(blockchain.estimated_transaction_volume_usd ?? 0);

  const chainRows = [
    {
      label: "Hash rate",
      value: `${formatNumber(hashRateEh, 0)} EH/s`,
      hint: "Network work rate",
    },
    {
      label: "Difficulty",
      value: formatNumber(difficulty, 0),
      hint: "Next retarget balances the chain",
    },
    {
      label: "Block time",
      value: `${formatNumber(blockTime, 1)} min`,
      hint: "Faster blocks usually mean fuller mempool",
    },
    {
      label: "Tx volume",
      value: formatCompact(txVolume),
      hint: "Estimated value settled on-chain",
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
      value: `${formatNumber(data?.hero.btc_dominance ?? 0, 1)}%`,
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
      value: `${formatNumber(data?.hero.price_vs_200wma ?? 0, 2)}x`,
      hint: "Cycle location",
    },
    {
      label: "MA stack",
      value: latestPoint ? `${formatPrice(latestPoint.price)} / ${formatPrice(latestPoint.ma7)} / ${formatPrice(latestPoint.ma50)}` : "—",
      hint: "Spot / short / medium trend",
    },
    {
      label: "Swing range",
      value: data ? `${formatPrice(data.chart.min)} → ${formatPrice(data.chart.max)}` : "—",
      hint: "Visible chart envelope",
    },
    {
      label: "Bias",
      value: data?.hero.regime ?? "—",
      hint: "Structure summary",
    },
  ];

  return (
    <main className={styles.shell}>
      <div className={styles.orb} />
      <div className={styles.gridGlow} />

      <header className={styles.header}>
        <div className={styles.headerText}>
          <div className={styles.kicker}>BTC live desk</div>
          <h1>链上、技术面、情绪面，一屏看 BTC</h1>
          <p>
            这版直接接实时 API，主图用真实价格序列、均线和市场结构。链上数据来自
            CoinGecko、Blockchain.com、mempool.space 和 Alternative.me，适合做日内和中周期判断。
          </p>
        </div>

        <div className={styles.headerMeta}>
          <div className={styles.metaTile}>
            <span>Updated</span>
            <strong>{state.refreshedAt || "—"}</strong>
          </div>
          <div className={styles.metaTile}>
            <span>Sources</span>
            <strong>{sources.length || 4}</strong>
          </div>
          <button className={styles.refreshButton} onClick={() => void loadData()} disabled={state.loading}>
            {state.loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </header>

      {state.error ? <div className={styles.errorBanner}>{state.error}</div> : null}

      <section className={styles.hero}>
        <article className={styles.stage}>
          <div className={styles.stageTop}>
            <div>
              <div className={styles.stageKicker}>{data?.hero.symbol ?? "BTC"}</div>
              <div className={styles.priceRow}>
                <h2>{formatPrice(data?.hero.price ?? 0)}</h2>
                <span className={(data?.hero.change_24h ?? 0) >= 0 ? styles.good : styles.bad}>
                  {formatChange(data?.hero.change_24h ?? 0)}
                </span>
              </div>
              <p className={styles.regimeLine}>
                {data?.hero.regime ?? "Waiting for live data"} · {data?.hero.fear_greed_label ?? "Neutral"} ·{" "}
                {formatNumber(data?.hero.btc_dominance ?? 0, 1)}% BTC dominance
              </p>
            </div>

            <div className={styles.heroStack}>
              <div>
                <span>Market cap</span>
                <strong>{formatCompact(data?.hero.market_cap ?? 0)}</strong>
              </div>
              <div>
                <span>24h volume</span>
                <strong>{formatCompact(data?.hero.volume_24h ?? 0)}</strong>
              </div>
              <div>
                <span>Fear & Greed</span>
                <strong>
                  {fearValue} / {fearClass}
                </strong>
              </div>
              <div>
                <span>200WMA ratio</span>
                <strong>{formatNumber(data?.hero.price_vs_200wma ?? 0, 2)}x</strong>
              </div>
            </div>
          </div>

          <div className={styles.chartCard}>
            <div className={styles.chartHeader}>
              <div>
                <span>Real-time BTC curve</span>
                <strong>
                  {latestPoint ? `${formatPrice(latestPoint.price)} / ${formatTime(latestPoint.timestamp)}` : "Loading chart..."}
                </strong>
              </div>
              <div className={styles.chartLegend}>
                <span>
                  <i className={styles.legendPrice} /> Price
                </span>
                <span>
                  <i className={styles.legendMa7} /> MA7
                </span>
                <span>
                  <i className={styles.legendMa50} /> MA50
                </span>
                <span>
                  <i className={styles.legendMa200} /> MA200
                </span>
                <span>
                  <i className={styles.legendMa1400} /> MA200W
                </span>
              </div>
            </div>

            <div className={styles.chartWrap}>
              {pricePath ? (
                <svg viewBox="0 0 1200 440" role="img" aria-label="BTC price chart">
                  <defs>
                    <linearGradient id="btcArea" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="0%" stopColor="rgba(89, 213, 255, 0.28)" />
                      <stop offset="100%" stopColor="rgba(89, 213, 255, 0.02)" />
                    </linearGradient>
                    <linearGradient id="btcPriceStroke" x1="0" x2="1" y1="0" y2="0">
                      <stop offset="0%" stopColor="#67dcff" />
                      <stop offset="100%" stopColor="#4fe19d" />
                    </linearGradient>
                  </defs>
                  <path d={areaPath} fill="url(#btcArea)" />
                  <path d={ma1400Path} className={styles.line200w} fill="none" />
                  <path d={ma200Path} className={styles.line200d} fill="none" />
                  <path d={ma50Path} className={styles.line50d} fill="none" />
                  <path d={ma7Path} className={styles.line7d} fill="none" />
                  <path d={pricePath} stroke="url(#btcPriceStroke)" className={styles.linePrice} fill="none" />
                </svg>
              ) : (
                <div className={styles.emptyState}>{state.loading ? "Loading live BTC data..." : "No live BTC data."}</div>
              )}
            </div>

            <div className={styles.chartFooter}>
              <div>
                <span>Range</span>
                <strong>{data ? `${formatPrice(data.chart.min)} → ${formatPrice(data.chart.max)}` : "—"}</strong>
              </div>
              <div>
                <span>Window</span>
                <strong>{series.length ? `${series.length} points` : "—"}</strong>
              </div>
              <div>
                <span>Price span</span>
                <strong>{data ? formatCompact(priceRange) : "—"}</strong>
              </div>
              <div>
                <span>Previous</span>
                <strong>{earliestPoint ? formatPrice(earliestPoint.price) : "—"}</strong>
              </div>
            </div>
          </div>

          <div className={styles.levelDeck}>
            {levels.map((level) => (
              <article key={level.label} className={styles.levelCard}>
                <div>
                  <span>{level.label}</span>
                  <strong>{formatPrice(level.price)}</strong>
                </div>
                <p>{level.note}</p>
                <em>{level.side}</em>
              </article>
            ))}
          </div>
        </article>

        <aside className={styles.rail}>
          <section className={styles.panel}>
            <div className={styles.panelHeader}>
              <div>
                <h3>链上脉冲</h3>
                <p>供给、算力、交易热度。</p>
              </div>
            </div>
            <div className={styles.metricGrid}>
              {networkCards.map((item) => (
                <article key={item.label} className={styles.metricCard}>
                  <span>{item.label}</span>
                  <strong className={item.state === "bullish" ? styles.good : item.state === "bearish" ? styles.bad : ""}>
                    {item.value}
                  </strong>
                  <em>{item.hint}</em>
                </article>
              ))}
            </div>
          </section>

          <section className={styles.panel}>
            <div className={styles.panelHeader}>
              <div>
                <h3>技术面</h3>
                <p>均线、动量、结构状态。</p>
              </div>
            </div>
            <div className={styles.metricGrid}>
              {technicalCards.map((item) => (
                <article key={item.label} className={styles.metricCard}>
                  <span>{item.label}</span>
                  <strong className={item.state === "bullish" ? styles.good : item.state === "bearish" ? styles.bad : ""}>
                    {item.value}
                  </strong>
                  <em>{item.hint}</em>
                </article>
              ))}
            </div>
          </section>

          <section className={styles.panel}>
            <div className={styles.panelHeader}>
              <div>
                <h3>情绪与流动性</h3>
                <p>情绪、dominance、mempool fee。</p>
              </div>
            </div>
            <div className={styles.metricGrid}>
              {sentimentCards.map((item) => (
                <article key={item.label} className={styles.metricCard}>
                  <span>{item.label}</span>
                  <strong className={item.state === "bullish" ? styles.good : item.state === "bearish" ? styles.bad : ""}>
                    {item.value}
                  </strong>
                  <em>{item.hint}</em>
                </article>
              ))}
              <article className={styles.metricCard}>
                <span>Mempool fee</span>
                <strong>{mempoolFast != null ? `${mempoolFast} sat/vB` : "—"}</strong>
                <em>
                  {mempoolHalf != null ? `30m ${mempoolHalf} · ` : ""}
                  {mempoolHour != null ? `1h ${mempoolHour}` : "fee ladder"}
                </em>
              </article>
            </div>
          </section>
        </aside>
      </section>

      <section className={styles.deepGrid}>
        <article className={styles.deepPanel}>
          <div className={styles.panelHeader}>
            <div>
              <h3>链上</h3>
              <p>看供给、算力和结算压力，判断链本身有没有发热。</p>
            </div>
            <span className={styles.panelTag}>On-chain</span>
          </div>
          <div className={styles.deepRows}>
            {chainRows.map((item) => (
              <div key={item.label} className={styles.deepRow}>
                <div>
                  <strong>{item.label}</strong>
                  <span>{item.hint}</span>
                </div>
                <b>{item.value}</b>
              </div>
            ))}
          </div>
        </article>

        <article className={styles.deepPanel}>
          <div className={styles.panelHeader}>
            <div>
              <h3>资金流</h3>
              <p>看人群温度、dominance 和 mempool fee，判断钱往哪边挤。</p>
            </div>
            <span className={styles.panelTag}>Flow</span>
          </div>
          <div className={styles.deepRows}>
            {flowRows.map((item) => (
              <div key={item.label} className={styles.deepRow}>
                <div>
                  <strong>{item.label}</strong>
                  <span>{item.hint}</span>
                </div>
                <b>{item.value}</b>
              </div>
            ))}
          </div>
        </article>

        <article className={styles.deepPanel}>
          <div className={styles.panelHeader}>
            <div>
              <h3>结构</h3>
              <p>把价格、均线和周期位置放到一起看，先分辨趋势还是震荡。</p>
            </div>
            <span className={styles.panelTag}>Structure</span>
          </div>
          <div className={styles.deepRows}>
            {structureRows.map((item) => (
              <div key={item.label} className={styles.deepRow}>
                <div>
                  <strong>{item.label}</strong>
                  <span>{item.hint}</span>
                </div>
                <b className={item.label === "Bias" ? (data?.hero.regime?.includes("Trend") ? styles.good : styles.bad) : ""}>
                  {item.value}
                </b>
              </div>
            ))}
          </div>
          <div className={styles.structureFoot}>
            {heroMetrics.slice(0, 3).map((item) => (
              <div key={item.label}>
                <span>{item.label}</span>
                <strong className={item.state === "bullish" ? styles.good : item.state === "bearish" ? styles.bad : ""}>
                  {item.value}
                </strong>
              </div>
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
