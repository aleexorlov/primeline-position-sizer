#!/usr/bin/env python3
"""
Primeline Capital — Position Sizer Web App v2.1
AIFM-compliant | Methodology v1.1 | Aligned with AIFM Filing §4, §6.2, §7, §8, §9, §10
v2.2: composite stop-loss (vol-regime × quality × base ATR mult); discretionary −20% stop fix
"""

import math
import time
import requests
import pandas as pd
import streamlit as st

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Primeline Capital · Position Sizer",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CUSTOM CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
.pl-header {
    background: linear-gradient(135deg, #1A1D27 0%, #12141E 100%);
    border-bottom: 2px solid #E8B84B;
    padding: 1.2rem 2rem;
    margin: -1rem -1rem 2rem -1rem;
    display: flex; align-items: center; gap: 1rem;
}
.pl-logo { font-size: 1.7rem; }
.pl-title { font-size: 1.3rem; font-weight: 700; color: #E8B84B; letter-spacing: 0.04em; }
.pl-subtitle { font-size: 0.75rem; color: #888; letter-spacing: 0.1em; text-transform: uppercase; }

.section-label {
    font-size: 0.65rem; font-weight: 700; letter-spacing: 0.14em;
    text-transform: uppercase; color: #E8B84B; margin-bottom: 0.5rem;
    border-bottom: 1px solid #2A2D3A; padding-bottom: 0.3rem;
}

.metric-card {
    background: #1A1D27; border: 1px solid #2A2D3A; border-radius: 8px;
    padding: 0.9rem 1.1rem; margin-bottom: 0.5rem;
}
.metric-card .label { font-size: 0.68rem; color: #888; letter-spacing: 0.08em; text-transform: uppercase; }
.metric-card .value { font-size: 1.5rem; font-weight: 700; color: #E8E8E8; line-height: 1.2; }
.metric-card .sub { font-size: 0.78rem; color: #aaa; margin-top: 0.15rem; }
.metric-card.accent { border-color: #E8B84B33; background: linear-gradient(135deg, #1A1D27, #1E1B10); }
.metric-card.green { border-color: #2ECC7133; }
.metric-card.red { border-color: #E74C3C33; }
.metric-card.warn { border-color: #F39C1233; }
.metric-card.short-card { border-color: #A855F733; }

.stop-box {
    border-radius: 8px; padding: 1rem 1.2rem;
}
.stop-box-long { background: linear-gradient(135deg, #1E1015, #1A0D12); border: 1px solid #E74C3C55; }
.stop-box-short { background: linear-gradient(135deg, #0D1020, #0A0D1E); border: 1px solid #A855F755; }
.stop-box .price-long { font-size: 2rem; font-weight: 700; color: #E74C3C; }
.stop-box .price-short { font-size: 2rem; font-weight: 700; color: #A855F7; }
.stop-box .detail { font-size: 0.78rem; color: #aaa; margin-top: 0.3rem; }

.hard-stop-box {
    background: #1A0A0A; border: 1px dashed #E74C3C88; border-radius: 6px;
    padding: 0.5rem 0.8rem; margin-top: 0.4rem; font-size: 0.78rem; color: #E74C3C;
}

.tp-row { display: flex; gap: 0.5rem; margin-top: 0.4rem; }
.tp-chip {
    flex: 1; text-align: center; border-radius: 6px; padding: 0.5rem 0.3rem;
}
.tp-chip-long { background: #0D1E14; border: 1px solid #2ECC7155; }
.tp-chip-short { background: #150D20; border: 1px solid #A855F755; }
.tp-chip .r { font-size: 0.65rem; font-weight: 700; }
.tp-chip-long .r { color: #2ECC71; }
.tp-chip-short .r { color: #A855F7; }
.tp-chip .price { font-size: 1rem; font-weight: 700; color: #E8E8E8; }
.tp-chip .pct { font-size: 0.7rem; color: #aaa; }

.heat-bar-wrap { background: #1A1D27; border-radius: 6px; overflow: hidden; height: 8px; margin-top: 6px; }
.heat-bar { height: 8px; border-radius: 6px; }

.info-box {
    background: #1A1D27; border-left: 3px solid #E8B84B;
    padding: 0.7rem 1rem; border-radius: 0 6px 6px 0;
    font-size: 0.8rem; color: #ccc; margin: 0.5rem 0;
}

.cap-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.35rem 0.7rem; border-radius: 5px; margin-bottom: 0.3rem; font-size: 0.8rem;
}
.cap-pass { background: #0D1E14; border: 1px solid #2ECC7122; color: #2ECC71; }
.cap-warn { background: #1E1500; border: 1px solid #F39C1222; color: #F39C12; }
.cap-fail { background: #1E0808; border: 1px solid #E74C3C44; color: #E74C3C; }

.checklist-item {
    display: flex; gap: 0.5rem; align-items: flex-start;
    padding: 0.3rem 0; font-size: 0.8rem; color: #ccc; border-bottom: 1px solid #1A1D27;
}

.direction-badge {
    display: inline-block; padding: 0.15rem 0.6rem; border-radius: 4px;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.05em; margin-left: 0.4rem;
}
.badge-long { background: #0D2010; color: #2ECC71; border: 1px solid #2ECC71; }
.badge-short { background: #15082A; color: #A855F7; border: 1px solid #A855F7; }

.badge { display: inline-block; padding: 0.2rem 0.7rem; border-radius: 20px;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.05em; }
.badge-t1 { background: #0D3320; color: #2ECC71; border: 1px solid #2ECC71; }
.badge-t2 { background: #1A2A10; color: #A8E063; border: 1px solid #A8E063; }
.badge-t3 { background: #2A1A08; color: #E8A430; border: 1px solid #E8A430; }

.pl-divider { border: none; border-top: 1px solid #2A2D3A; margin: 1.2rem 0; }
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS (per Methodology v1.1) ─────────────────────────────────────────

AV_BASE = "https://www.alphavantage.co/query"

TIER1_EXCHANGES = {
    "NYSE", "NASDAQ", "LSE", "LONDON STOCK EXCHANGE",
    "EURONEXT", "EURONEXT AMSTERDAM", "AEB", "AMSTERDAM",
    "XETRA", "FRANKFURT", "SIX", "SWISS EXCHANGE",
}

# yfinance exchange codes → canonical names used by calc_tier()
YF_EXCHANGE_MAP = {
    # US
    "NMS": "NASDAQ",  "NGM": "NASDAQ",  "NCM": "NASDAQ",
    "NYQ": "NYSE",    "NYS": "NYSE",    "ASE": "NYSE",
    # UK
    "LSE": "LONDON STOCK EXCHANGE",   "LSI": "LONDON STOCK EXCHANGE",
    # EU
    "AMS": "EURONEXT AMSTERDAM",
    "PAR": "EURONEXT",  "EPA": "EURONEXT",
    "BRU": "EURONEXT",  "LIS": "EURONEXT",
    "GER": "XETRA",     "EXX": "XETRA",   "XETR": "XETRA",
    "FRA": "FRANKFURT",
    "EBS": "SWISS EXCHANGE",   "VTX": "SWISS EXCHANGE",
    # Asia-Pacific (not Tier 1 per AIFM §6.2 — will land Tier 2/3 via mkt-cap/ADV)
    "HKG": "HKEX",
    "TYO": "TOKYO STOCK EXCHANGE",
    "SHH": "SHANGHAI",   "SHZ": "SHENZHEN",
    "KRX": "KOREA STOCK EXCHANGE",
    "BSE": "BOMBAY STOCK EXCHANGE",
    "NSE": "NSE INDIA",
    # Other
    "TSX": "TORONTO STOCK EXCHANGE",
    "ASX": "ASX",
}

FX_PAIRS = {
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD",
    "USDCAD", "EURGBP", "EURJPY", "GBPJPY", "USDMXN", "USDZAR",
    "EUR/USD", "GBP/USD", "USD/JPY", "EUR/GBP", "GBP/JPY",
}

# §8.3 Conviction score → position-size multiplier (Methodology Step 2)
CONVICTION_TABLE = [(80, 1.50), (60, 1.25), (40, 1.00), (20, 0.75), (0, 0.50)]

# §9.1 Quality score → stop-width multiplier (Methodology Step 7, stop composite)
# High-quality businesses earn wider stops; low quality gets tighter risk control.
QUALITY_TABLE = [(80, 1.20), (60, 1.10), (40, 1.00), (20, 0.95), (0, 0.90)]

# §9.1 Vol regime → stop-width multiplier (AIFM §9.1: "time horizon and volatility regime")
# Elevated vol expands stop to avoid shakeout; compressed vol tightens it.
VOL_REGIME_STOP = {
    "very_elevated": 1.30,  # vol_regime ≥ 1.50
    "elevated":      1.15,  # vol_regime 1.20–1.49
    "normal":        1.00,  # vol_regime 0.80–1.19
    "compressed":    0.90,  # vol_regime < 0.80
}
MAX_COMPOSITE_ATR = 4.5   # absolute ceiling on composite ATR multiplier

# §6.2, §8.2 Tier → position-size multiplier (Methodology Step 3)
TIER_MULT = {"Tier 1": 1.25, "Tier 2": 1.00, "Tier 3": 1.00, "Discretionary": 0.67}

# §4.3 Time horizon → position-size multiplier (Methodology Step 4)
TIME_MULT = {
    "Extended-Hold": 1.20,
    "LT Strategic":  1.00,
    "Core":          0.85,
    "Tactical":      0.60,
}

# §9.1 Base ATR multiplier by position type (before vol-regime and quality adjustments)
ATR_MULT = {
    "Extended-Hold": 3.0,
    "LT Strategic":  3.0,
    "Core":          2.5,
    "Tactical":      2.0,
}

# §8.2 Hard caps by tier (% of NAV) at initiation
HARD_CAP_PCT = {
    "Tier 1":        5.0,   # requires IC approval
    "Tier 2":        3.0,
    "Tier 3":        3.0,
    "Discretionary": 2.0,
}

BASE_RISK_PCT = 0.5  # §8.1 — fixed at 0.5% NAV, not user-adjustable


# ── HELPERS ───────────────────────────────────────────────────────────────────

def score_to_mult(score: float, table: list) -> float:
    for threshold, mult in table:
        if score >= threshold:
            return mult
    return table[-1][1]


def vol_regime_stop_mult(ratio: float) -> float:
    """§9.1: expand stop in elevated vol, tighten in compressed vol."""
    if ratio >= 1.50: return VOL_REGIME_STOP["very_elevated"]
    if ratio >= 1.20: return VOL_REGIME_STOP["elevated"]
    if ratio < 0.80:  return VOL_REGIME_STOP["compressed"]
    return VOL_REGIME_STOP["normal"]


def vol_regime_label(ratio: float) -> str:
    if ratio >= 1.50: return "Very Elevated (≥1.50×)"
    if ratio >= 1.20: return "Elevated (1.20-1.49×)"
    if ratio < 0.80:  return "Compressed (<0.80×)"
    return "Normal (0.80-1.19×)"


def infer_position_type(conviction: float) -> str:
    if conviction >= 80: return "Extended-Hold"
    if conviction >= 60: return "LT Strategic"
    if conviction >= 40: return "Core"
    return "Tactical"


def calc_tier(mkt_cap: int, exchange: str, adv60_usd: float) -> str:
    exch_upper = exchange.upper()
    on_major = any(e in exch_upper for e in TIER1_EXCHANGES)
    if mkt_cap >= 10_000_000_000 and on_major and adv60_usd >= 50_000_000:
        return "Tier 1"
    if mkt_cap >= 2_000_000_000 or adv60_usd >= 10_000_000:
        return "Tier 2"
    return "Tier 3"


def is_fx(ticker: str) -> bool:
    t = ticker.upper().replace("/", "").replace("-", "").replace("_", "")
    return t in {p.replace("/","").replace("-","").replace("_","") for p in FX_PAIRS} or (
        len(t) == 6 and t.isalpha()
    )


# ── DATA FETCHING (yfinance primary · Alpha Vantage fallback) ─────────────────

@st.cache_data(ttl=120, show_spinner=False)
def fetch_data(ticker: str, api_key: str) -> dict:
    """
    Try yfinance first (no key, global coverage).
    Auto-probes exchange suffixes when the bare ticker returns nothing.
    Falls back to Alpha Vantage if all yfinance attempts fail and a key is provided.
    All prices/ATR values returned in USD regardless of listed currency.
    """
    ticker = ticker.upper().strip()

    # Build candidate ticker list: bare ticker first, then auto-suffixed variants
    candidates = _resolve_candidates(ticker)

    last_yf_err: Exception | None = None
    for candidate in candidates:
        try:
            return _fetch_yfinance(candidate)
        except Exception as e:
            last_yf_err = e

    # All yfinance candidates failed — try Alpha Vantage if key supplied
    if api_key:
        try:
            return _fetch_alphavantage(ticker, api_key)
        except Exception as av_err:
            raise ValueError(
                f"Both data sources failed for '{ticker}'.\n"
                f"yfinance (tried: {candidates}): {last_yf_err}\n"
                f"Alpha Vantage: {av_err}"
            )

    raise ValueError(
        f"No data found for '{ticker}'.\n\n"
        "Use the exchange suffix for non-US stocks:\n"
        "• HK Exchange  →  9880.HK  (UBTECH · UBTech Robotics)\n"
        "• Xetra        →  SAP.DE · RHM.DE\n"
        "• Swiss SIX    →  NESN.SW · UBSG.SW\n"
        "• London LSE   →  BP.L · LLOY.L\n"
        "• Tokyo        →  7203.T  (Toyota)\n"
        "• US stocks    →  AAPL · PLTR · MSFT  (no suffix)\n\n"
        "Tip: adding an Alpha Vantage key in the sidebar enables a US-stock fallback."
    )


def _resolve_candidates(ticker: str) -> list[str]:
    """
    Return an ordered list of ticker symbols to try on yfinance.
    Handles the most common 'user typed a bare code' cases:
      - Pure 4-digit number (e.g. '9880') → try 9880.HK first (HKEX convention)
      - Known exchange suffix already present → just that ticker
      - Otherwise: bare ticker only (works for US stocks)
    """
    # Already has a suffix (e.g. '9880.HK', 'SAP.DE', 'NESN.SW', 'BP.L')
    if "." in ticker:
        return [ticker]

    # FX pair — no suffix logic needed
    if is_fx(ticker):
        return [ticker]

    # Pure numeric ticker (1–5 digits) → almost certainly HKEX; probe a few
    if ticker.isdigit() and len(ticker) <= 5:
        padded = ticker.zfill(4)   # HKEX uses zero-padded 4-digit codes
        raw = [f"{padded}.HK", f"{ticker}.HK", f"{ticker}.T", ticker]
        return list(dict.fromkeys(raw))   # dedupe, keep order

    # Bare alphabetic ticker — US first, then major exchanges as fallback probes
    return [
        ticker,          # US (no suffix)
        f"{ticker}.L",   # London
        f"{ticker}.DE",  # Xetra
        f"{ticker}.SW",  # Swiss
    ]


def _fetch_yfinance(ticker: str) -> dict:
    """Fetch via yfinance — works for any exchange worldwide."""
    import yfinance as yf

    fx = is_fx(ticker)

    if fx:
        # FX via yfinance: EURUSD → EURUSD=X
        ticker_clean = ticker.replace("/", "").replace("-", "").replace("_", "")
        yf_symbol = ticker_clean + "=X"
        yft = yf.Ticker(yf_symbol)
        hist = yft.history(period="100d", interval="1d", auto_adjust=True)
        hist = hist.dropna(subset=["Close", "High", "Low"])   # yf can return partial NaN rows
        if hist.empty:
            raise ValueError(f"No FX data for '{ticker}' (tried {yf_symbol})")
        name     = f"{ticker_clean[:3]}/{ticker_clean[3:]} (FX)"
        currency = "USD"
        fx_rate  = 1.0
        mkt_cap  = 0
        exchange = ""
        sector   = ""
        adv5_shares = 0
    else:
        yft  = yf.Ticker(ticker)
        hist = yft.history(period="100d", interval="1d", auto_adjust=True)
        hist = hist.dropna(subset=["Close", "High", "Low"])   # yf can return partial NaN rows

        if hist.empty:
            raise ValueError(
                f"No price data returned for '{ticker}'.\n"
                "For non-US stocks add the exchange suffix:\n"
                "  HK: 9880.HK · Xetra: SAP.DE · Swiss: NESN.SW · London: BP.L · Tokyo: 7203.T"
            )

        # Enrich with company info (best-effort — yfinance may throttle .info)
        name     = ticker
        currency = "USD"
        mkt_cap  = 0
        exchange = ""
        sector   = ""
        try:
            fi       = yft.fast_info
            currency = getattr(fi, "currency", "USD") or "USD"
            mkt_cap  = int(getattr(fi, "market_cap", 0) or 0)
        except Exception:
            pass
        try:
            info     = yft.info
            name     = info.get("longName") or info.get("shortName") or ticker
            exchange = info.get("exchange") or ""
            sector   = info.get("sector") or ""
            if not mkt_cap:
                mkt_cap = int(info.get("marketCap") or 0)
        except Exception:
            pass

        exchange = YF_EXCHANGE_MAP.get(exchange, exchange)

        # FX conversion: convert local-currency metrics to USD
        fx_rate = 1.0
        if currency and currency != "USD":
            fx_rate = _fetch_fx_rate(currency)
            mkt_cap = int(mkt_cap * fx_rate)   # USD market cap for tier calc

        adv5_shares = float(hist["Volume"].tail(5).mean()) if "Volume" in hist.columns else 0

    # ── Shared OHLCV calculations ─────────────────────────────────────────────
    df    = hist.reset_index()
    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]

    if len(df) < 20:
        raise ValueError(f"Insufficient history for '{ticker}' (only {len(df)} bars returned).")

    price_local = float(close.iloc[-1])
    prev_local  = float(close.iloc[-2]) if len(close) >= 2 else price_local

    # yfinance daily bars can lag a session behind. Pull the live/most-recent
    # quote and use it whenever it's newer than the last daily bar.
    try:
        live = float(getattr(yft.fast_info, "last_price", 0) or 0)
    except Exception:
        live = 0.0
    if live > 0 and price_local > 0 and abs(live - price_local) / price_local > 0.0005:
        prev_local  = price_local   # last completed bar becomes the reference close
        price_local = live

    price_usd   = round(price_local * fx_rate, 4)
    prev_usd    = prev_local * fx_rate

    day_chg_usd = round(price_usd - prev_usd, 4)
    day_chg_pct = round((day_chg_usd / prev_usd) * 100, 2) if prev_usd else 0

    prev     = close.shift(1)
    tr       = (high - low).combine((high - prev).abs(), max).combine((low - prev).abs(), max)
    atr14_local = float(tr.rolling(14).mean().iloc[-1])
    atr14_usd   = round(atr14_local * fx_rate, 4)

    vol60 = float(close.pct_change().dropna().tail(60).std() * math.sqrt(252))

    vol_col   = (df["Volume"] if "Volume" in df.columns else pd.Series([0.0] * len(df))).fillna(0)
    adv5      = float(vol_col.tail(5).mean()) if not fx else 0
    adv60_usd = float(vol_col.tail(60).mean()) * price_usd if not fx else 0

    atr_pct       = tr.rolling(14).mean() / close
    avg90_atr_pct = float(atr_pct.dropna().tail(90).mean())
    cur_atr_pct   = atr14_local / price_local if price_local else 0
    vol_regime    = round(cur_atr_pct / avg90_atr_pct, 2) if avg90_atr_pct else 1.0

    # Final sanity guard — never hand NaN to the sizing engine or the UI
    if any(math.isnan(x) for x in (price_usd, atr14_usd, vol60)):
        raise ValueError(
            f"Incomplete data for '{ticker}' (NaN in price/ATR/vol). "
            "The source returned partial bars — try again in a moment."
        )
    if math.isnan(vol_regime):
        vol_regime = 1.0

    tier = calc_tier(mkt_cap, exchange, adv60_usd) if not fx else "N/A (FX)"

    return {
        "ticker":        ticker,
        "name":          name,
        "currency":      currency,
        "fx_rate":       round(fx_rate, 6),
        "price":         price_usd,          # USD — used by sizing engine
        "price_local":   round(price_local, 4),
        "day_chg":       day_chg_usd,
        "day_chg_pct":   day_chg_pct,
        "vol60":         round(vol60, 4),
        "atr14":         atr14_usd,          # USD — used by sizing engine
        "atr_pct":       round(cur_atr_pct * 100, 2),
        "adv5":          int(round(adv5)),
        "adv60_usd":     round(adv60_usd, 0),
        "mkt_cap":       mkt_cap,
        "vol_regime":    vol_regime,
        "exchange":      exchange,
        "sector":        sector,
        "tier":          tier,
        "is_fx":         fx,
        "data_source":   "yfinance",
    }


def _fetch_alphavantage(ticker: str, api_key: str) -> dict:
    """Alpha Vantage fallback — best for US stocks when yfinance is unavailable."""
    ticker_clean = ticker.replace("/", "").replace("-", "")
    fx = is_fx(ticker)

    if fx:
        from_cur = ticker_clean[:3]
        to_cur   = ticker_clean[3:]
        raw    = _av_get({"function": "FX_DAILY", "from_symbol": from_cur,
                          "to_symbol": to_cur, "outputsize": "compact", "apikey": api_key})
        ts_key = "Time Series FX (Daily)"
        name   = f"{from_cur}/{to_cur} (FX)"
    else:
        raw    = _av_get({"function": "TIME_SERIES_DAILY", "symbol": ticker,
                          "outputsize": "compact", "apikey": api_key})
        ts_key = "Time Series (Daily)"
        name   = ticker

    ts = raw.get(ts_key)
    if not ts:
        raise ValueError(f"No price data returned for '{ticker}'.")

    rows = [
        {
            "date":   d,
            "close":  float(v.get("4. close", v.get("4. Close", 0))),
            "high":   float(v.get("2. high",  v.get("2. High",  0))),
            "low":    float(v.get("3. low",   v.get("3. Low",   0))),
            "volume": float(v.get("5. volume", 0)),
        }
        for d, v in ts.items()
    ]
    df    = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    close = df["close"]
    high  = df["high"]
    low   = df["low"]

    if len(df) < 20:
        raise ValueError(f"Insufficient history for {ticker} (only {len(df)} bars).")

    price       = float(close.iloc[-1])
    prev_price  = float(close.iloc[-2]) if len(close) >= 2 else price
    day_chg     = round(price - prev_price, 4)
    day_chg_pct = round((day_chg / prev_price) * 100, 2) if prev_price else 0

    prev  = close.shift(1)
    tr    = (high - low).combine((high - prev).abs(), max).combine((low - prev).abs(), max)
    atr14 = float(tr.rolling(14).mean().iloc[-1])
    vol60 = float(close.pct_change().dropna().tail(60).std() * math.sqrt(252))

    adv5      = float(df["volume"].tail(5).mean()) if not fx else 0
    adv60_usd = float(df["volume"].tail(60).mean()) * price if not fx else 0

    atr_pct       = tr.rolling(14).mean() / close
    avg90_atr_pct = float(atr_pct.tail(90).mean())
    cur_atr_pct   = atr14 / price if price else 0
    vol_regime    = round(cur_atr_pct / avg90_atr_pct, 2) if avg90_atr_pct else 1.0

    exchange = ""
    sector   = ""
    mkt_cap  = 0
    if not fx:
        time.sleep(1)
        try:
            ov       = _av_get({"function": "OVERVIEW", "symbol": ticker, "apikey": api_key})
            name     = ov.get("Name") or ticker
            mkt_cap  = int(ov.get("MarketCapitalization") or 0)
            exchange = ov.get("Exchange") or ""
            sector   = ov.get("Sector") or ""
        except Exception:
            pass

    tier = calc_tier(mkt_cap, exchange, adv60_usd) if not fx else "N/A (FX)"

    return {
        "ticker":       ticker,
        "name":         name,
        "currency":     "USD",
        "fx_rate":      1.0,
        "price":        round(price, 4),
        "price_local":  round(price, 4),
        "day_chg":      day_chg,
        "day_chg_pct":  day_chg_pct,
        "vol60":        round(vol60, 4),
        "atr14":        round(atr14, 4),
        "atr_pct":      round(cur_atr_pct * 100, 2),
        "adv5":         int(round(adv5)),
        "adv60_usd":    round(adv60_usd, 0),
        "mkt_cap":      mkt_cap,
        "vol_regime":   vol_regime,
        "exchange":     exchange,
        "sector":       sector,
        "tier":         tier,
        "is_fx":        fx,
        "data_source":  "alphavantage",
    }


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_fx_rate(currency: str) -> float:
    """Fetch spot rate to USD via yfinance (cached 1 hour)."""
    import yfinance as yf
    if currency == "USD":
        return 1.0
    symbol = f"{currency}USD=X"
    try:
        hist = yf.Ticker(symbol).history(period="2d", interval="1d", auto_adjust=True)
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    # Last resort: try inverse
    try:
        inv_symbol = f"USD{currency}=X"
        hist = yf.Ticker(inv_symbol).history(period="2d", interval="1d", auto_adjust=True)
        if not hist.empty:
            rate = float(hist["Close"].iloc[-1])
            return round(1.0 / rate, 6) if rate else 1.0
    except Exception:
        pass
    return 1.0   # graceful fallback: prices treated as USD


def _av_get(params: dict) -> dict:
    resp = requests.get(AV_BASE, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    for bad_key in ("Error Message", "Note", "Information"):
        if bad_key in data:
            raise ValueError(f"Alpha Vantage: {data[bad_key][:200]}")
    return data


# ── POSITION SIZING ENGINE (Methodology v1.1, Steps 1–9) ─────────────────────

def size_position(
    nav:              float,
    vol60:            float,    # annualised 60-day realised vol
    entry_price:      float,
    atr14:            float,
    conviction:       float,    # 0-100  → position-size multiplier
    quality_score:    float,    # 0-100  → stop-width multiplier (§9.1 composite)
    vol_regime:       float,    # current ATR% ÷ 90d avg ATR% → stop-width multiplier
    pos_type:         str,
    tier:             str,
    direction:        str,      # "Long" or "Short"
    sector_pct_nav:   float,    # existing sector exposure % NAV
    country_pct_nav:  float,    # existing country exposure % NAV
    thesis_floor:     float,    # price level that invalidates thesis
    portfolio_heat:   float,    # existing open portfolio heat % NAV
    adv5:             int,      # 5-day avg daily volume (shares)
    stress_mode:      bool,
    tp_r_multiples:   list,
    discretionary:    bool = False,
) -> dict:
    """
    Nine-step AIFM position sizing (Methodology v1.1).
    Steps 1-5: Calculate size. Steps 6-9: Constraint checks.
    """

    # ── Step 1: Base Position (Vol-Targeted) §8.1 ────────────────────────────
    daily_vol     = vol60 / math.sqrt(252) if vol60 > 0 else 0.01
    risk_budget   = nav * (BASE_RISK_PCT / 100)
    base_pos_usd  = risk_budget / daily_vol if daily_vol > 0 else 0

    # ── Step 2: Conviction Multiplier §8.3 ───────────────────────────────────
    conv_mult = score_to_mult(conviction, CONVICTION_TABLE)

    # ── Step 3: Tier Multiplier §6.2, §8.2 ───────────────────────────────────
    tier_key  = "Discretionary" if discretionary else tier
    tier_mult = TIER_MULT.get(tier_key, 1.00)

    # ── Step 4: Time Horizon Multiplier §4.3 ─────────────────────────────────
    time_mult = TIME_MULT.get(pos_type, 0.85)

    # ── Step 5: Adjusted Position ─────────────────────────────────────────────
    adj_pos_usd = base_pos_usd * conv_mult * tier_mult * time_mult

    # ── Step 6: Hard Cap Enforcement §6.3, §8.2 ──────────────────────────────
    cap_pct       = HARD_CAP_PCT.get("Discretionary" if discretionary else tier, 3.0)
    hard_cap_usd  = nav * (cap_pct / 100)

    # Tier 1 requires IC approval above standard 3%
    tier1_ic_flag = (tier == "Tier 1" and cap_pct == 5.0)

    final_pos_usd = min(adj_pos_usd, hard_cap_usd)

    # Stress mode: 25% reduction across all positions (§7.3)
    if stress_mode:
        final_pos_usd *= 0.75

    shares = max(int(final_pos_usd / entry_price), 0) if entry_price > 0 else 0

    pos_value   = round(shares * entry_price, 2)
    pos_pct_nav = round(pos_value / nav * 100, 2) if nav else 0

    # ── Step 7: ATR Stop-Loss §9.1 + Composite Multiplier + Hard Stop §9.2 ──────
    # Composite ATR mult = Base (by position type)
    #                    × Vol Regime mult (AIFM §9.1: "time horizon and volatility regime")
    #                    × Quality mult   (fundamental quality earns wider stop breathing room)
    base_atr_mult    = ATR_MULT.get(pos_type, 2.5)
    vr_stop_mult     = vol_regime_stop_mult(vol_regime)
    qual_stop_mult   = score_to_mult(quality_score, QUALITY_TABLE)
    composite_atr_m  = round(min(base_atr_mult * vr_stop_mult * qual_stop_mult, MAX_COMPOSITE_ATR), 3)

    # Hard stop: §9.2 standard = −25%; §7.4 Discretionary = −20% (mandatory auto-exit)
    hard_stop_pct    = 0.80 if discretionary else 0.75   # 0.80 → −20%, 0.75 → −25%

    if direction == "Long":
        atr_stop_price  = round(entry_price - composite_atr_m * atr14, 4)
        hard_stop_price = round(entry_price * hard_stop_pct, 4)

        # Stop cannot be below thesis floor; hard stop is the absolute floor
        effective_stop = max(atr_stop_price, thesis_floor)
        effective_stop = max(effective_stop, hard_stop_price)
        effective_stop = round(effective_stop, 4)

        atr_stop_clamped = effective_stop > atr_stop_price
        floor_clamped    = effective_stop == thesis_floor and thesis_floor > atr_stop_price

        # Take-profit: above entry for long
        tp_levels = []
        stop_dist = entry_price - effective_stop
        for r in tp_r_multiples:
            tp_price = round(entry_price + r * stop_dist, 4)
            tp_pct   = round((tp_price - entry_price) / entry_price * 100, 2)
            tp_levels.append({"r": r, "price": tp_price, "pct": tp_pct})

    else:  # Short
        atr_stop_price  = round(entry_price + composite_atr_m * atr14, 4)
        hard_stop_price = round(entry_price * (2 - hard_stop_pct), 4)  # +25% or +20%

        # For shorts, thesis floor is a CEILING (cover if price drops below)
        effective_stop = min(atr_stop_price, thesis_floor) if thesis_floor > 0 else atr_stop_price
        effective_stop = min(effective_stop, hard_stop_price)
        effective_stop = round(effective_stop, 4)

        atr_stop_clamped = effective_stop < atr_stop_price
        floor_clamped    = False

        # Take-profit: below entry for short
        tp_levels = []
        stop_dist = effective_stop - entry_price
        for r in tp_r_multiples:
            tp_price = round(entry_price - r * stop_dist, 4)
            tp_pct   = round((entry_price - tp_price) / entry_price * 100, 2)
            tp_levels.append({"r": r, "price": tp_price, "pct": tp_pct})

    # ── Step 8: Portfolio Heat §10.2 ─────────────────────────────────────────
    risk_per_share  = abs(entry_price - effective_stop)
    position_risk   = round(shares * risk_per_share, 2)
    new_heat_pct    = round(position_risk / nav * 100, 4) if nav else 0
    total_heat_pct  = round(portfolio_heat + new_heat_pct, 2)

    heat_status = "green" if total_heat_pct < 6.0 else "amber" if total_heat_pct < 8.0 else "red"

    # Amber: automatically reduce by 25%
    if heat_status == "amber":
        shares        = int(shares * 0.75)
        pos_value     = round(shares * entry_price, 2)
        pos_pct_nav   = round(pos_value / nav * 100, 2)
        position_risk = round(shares * risk_per_share, 2)
        new_heat_pct  = round(position_risk / nav * 100, 4)
        total_heat_pct= round(portfolio_heat + new_heat_pct, 2)

    # Red: no new positions
    heat_blocked = (heat_status == "red")

    # ── Step 6 Continued: Concentration Checks ───────────────────────────────
    # Sector cap: warn at 15%, breach at 20% (§6.3)
    sector_after  = round(sector_pct_nav + pos_pct_nav, 2)
    sector_warn   = sector_after > 15.0
    sector_breach = sector_after > 20.0

    # Country cap: 25-30% developed, 15% EM
    country_after  = round(country_pct_nav + pos_pct_nav, 2)
    country_breach = country_after > 30.0  # conservative developed-market limit

    # Liquidity: shares ≤ 10% of 5-day ADV (§6.3)
    liquidity_ok = (shares <= adv5 * 0.10) if adv5 > 0 else True

    # Cash floor check (§6.3): post-trade cash ≥ 15% NAV (20% in stress)
    cash_floor_pct = 20.0 if stress_mode else 15.0
    cash_ok = pos_pct_nav <= (100.0 - cash_floor_pct)

    # ── Step 9: Client-Level 2σ Check §8.2 ───────────────────────────────────
    daily_vol_abs = daily_vol
    sigma2_loss   = round(shares * entry_price * 2 * daily_vol_abs, 2)

    # Sign-off authority (§7.3)
    signoff = "IC (2 of 3 principals required)" if pos_pct_nav > 2.0 else "GP (Kacper Zyskowski)"

    return {
        # Step 1-5
        "daily_vol":      round(daily_vol * 100, 3),
        "risk_budget":    round(risk_budget, 2),
        "base_pos_usd":   round(base_pos_usd, 2),
        "conv_mult":      conv_mult,
        "tier_mult":      tier_mult,
        "time_mult":      time_mult,
        "adj_pos_usd":    round(adj_pos_usd, 2),
        "hard_cap_pct":   cap_pct,
        "hard_cap_usd":   round(hard_cap_usd, 2),
        "tier1_ic_flag":  tier1_ic_flag,
        "final_pos_usd":  round(final_pos_usd, 2),
        "shares":         shares,
        "pos_value":      pos_value,
        "pos_pct_nav":    pos_pct_nav,
        # Step 7 — composite stop
        "base_atr_mult":  base_atr_mult,
        "vr_stop_mult":   vr_stop_mult,
        "qual_stop_mult": qual_stop_mult,
        "atr_mult":       composite_atr_m,   # composite (what was actually used)
        "atr_stop_price": atr_stop_price,
        "hard_stop_price":hard_stop_price,
        "hard_stop_pct":  round((1 - hard_stop_pct) * 100, 0),  # 20 or 25
        "effective_stop": effective_stop,
        "stop_dist":      round(abs(entry_price - effective_stop), 4),
        "atr_stop_clamped": atr_stop_clamped,
        "floor_clamped":  floor_clamped,
        "tp_levels":      tp_levels,
        # Step 8
        "risk_per_share": round(risk_per_share, 4),
        "position_risk":  position_risk,
        "new_heat_pct":   new_heat_pct,
        "total_heat_pct": total_heat_pct,
        "heat_status":    heat_status,
        "heat_blocked":   heat_blocked,
        # Step 6 continued
        "sector_after":   sector_after,
        "sector_warn":    sector_warn,
        "sector_breach":  sector_breach,
        "country_after":  country_after,
        "country_breach": country_breach,
        "liquidity_ok":   liquidity_ok,
        "cash_ok":        cash_ok,
        # Step 9
        "sigma2_loss":    sigma2_loss,
        "signoff":        signoff,
    }


# ── SIDEBAR ───────────────────────────────────────────────────────────────────

def sidebar():
    with st.sidebar:
        st.markdown('<div class="section-label">📡 Data Source</div>', unsafe_allow_html=True)
        st.markdown(
            "<div style='font-size:0.72rem;color:#888;margin-bottom:0.4rem'>"
            "Primary: <b style='color:#2ECC71'>yfinance</b> — no key needed, global coverage.<br>"
            "Supports any exchange: <code>9880.HK</code> · <code>SAP.DE</code> · <code>NESN.SW</code> · <code>BP.L</code><br>"
            "Alpha Vantage key is optional (US stocks fallback only)."
            "</div>", unsafe_allow_html=True
        )
        import os
        _default_key = st.session_state.get("av_api_key",
            st.secrets.get("AV_API_KEY", "") if hasattr(st, "secrets") else os.environ.get("AV_API_KEY", ""))
        api_key = st.text_input(
            "Alpha Vantage Key (optional fallback)",
            value=_default_key,
            type="password",
            help="Only used if yfinance fails. Free key: alphavantage.co/support/#api-key (25 req/day)",
        )
        if api_key:
            st.session_state["av_api_key"] = api_key

        st.markdown('<hr class="pl-divider">', unsafe_allow_html=True)
        st.markdown('<div class="section-label">📊 Fund Settings</div>', unsafe_allow_html=True)

        nav = st.number_input(
            "Fund NAV (USD)",
            min_value=10_000.0, max_value=1_000_000_000.0,
            value=st.session_state.get("nav", 1_000_000.0),
            step=10_000.0, format="%.0f",
        )
        st.session_state["nav"] = nav

        st.markdown(
            f"<div style='font-size:0.72rem;color:#888;margin-top:-0.3rem'>Risk budget per trade: "
            f"<b style='color:#E8B84B'>0.5% NAV = ${nav * 0.005:,.0f}</b> (fixed §8.1)</div>",
            unsafe_allow_html=True
        )

        portfolio_heat = st.slider(
            "Existing Portfolio Heat (% NAV)",
            min_value=0.0, max_value=10.0,
            value=st.session_state.get("portfolio_heat", 0.0),
            step=0.1, format="%.1f%%",
            help="Sum of (entry−stop)×shares for all open positions ÷ NAV. Green <6%, Amber 6-8%, Red >8% §10.2"
        )
        st.session_state["portfolio_heat"] = portfolio_heat

        heat_col = "#2ECC71" if portfolio_heat < 6.0 else "#F39C12" if portfolio_heat < 8.0 else "#E74C3C"
        heat_lbl = "🟢 Green — Normal" if portfolio_heat < 6.0 else "🟡 Amber — Warning" if portfolio_heat < 8.0 else "🔴 Red — Hard Stop"
        st.markdown(f"<div style='font-size:0.72rem;color:{heat_col};margin-top:-0.3rem'>{heat_lbl}</div>", unsafe_allow_html=True)

        st.markdown('<hr class="pl-divider">', unsafe_allow_html=True)
        st.markdown('<div class="section-label">⚠️ Market Conditions</div>', unsafe_allow_html=True)
        stress_mode = st.toggle("🔴 Market Stress Mode", value=False,
            help="VIX>25, S&P -8% from 60d high, credit spreads +50bps, NAV -4% from monthly high (2+ conditions, 3+ days). Triggers: 0.75× size, 20% cash floor.")
        st.session_state["stress_mode"] = stress_mode
        if stress_mode:
            st.warning("Positions reduced 25% · Cash floor 20% NAV (§7.3)")

        st.markdown('<hr class="pl-divider">', unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:0.7rem;color:#666;line-height:1.6">
        <b style="color:#888">Primeline Capital OÜ</b><br>
        AIFM Position Sizer v2.1<br>
        Methodology v1.1 · §4, §6.2, §7, §8, §9, §10<br><br>
        Data: Alpha Vantage (free tier)<br>
        Delay: ~15 min. Not for HFT.
        </div>
        """, unsafe_allow_html=True)

    return api_key, nav, portfolio_heat, stress_mode


# ── MAIN APP ──────────────────────────────────────────────────────────────────

def main():
    st.markdown("""
    <div class="pl-header">
        <div class="pl-logo">📐</div>
        <div>
            <div class="pl-title">PRIMELINE CAPITAL</div>
            <div class="pl-subtitle">AIFM Position Sizer · v2.2 · Methodology v1.1</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    api_key, nav, portfolio_heat, stress_mode = sidebar()

    # ── Ticker + Direction ────────────────────────────────────────────────────
    col_input, col_dir, col_btn = st.columns([4, 1, 1])
    with col_input:
        ticker = st.text_input(
            "Ticker / FX Pair",
            placeholder="US: PLTR · AAPL   |   HK: 9880.HK   |   EU: SAP.DE · NESN.SW · BP.L",
            value=st.session_state.get("ticker", ""),
            label_visibility="collapsed",
        )
    with col_dir:
        direction = st.selectbox(
            "Direction",
            ["Long", "Short"],
            index=0,
            label_visibility="collapsed",
        )
    with col_btn:
        fetch_btn = st.button("⚡ Fetch", use_container_width=True, type="primary")

    dir_color = "#2ECC71" if direction == "Long" else "#A855F7"
    dir_badge = f'<span class="direction-badge badge-{"long" if direction == "Long" else "short"}">{direction}</span>'

    if fetch_btn and ticker:
        st.session_state["ticker"]    = ticker.upper().strip()
        st.session_state["direction"] = direction
        with st.spinner(f"Fetching {ticker.upper()} market data…"):
            try:
                data = fetch_data(ticker, api_key)
                st.session_state["market_data"] = data
                st.session_state["entry_price"] = data["price"]  # USD
            except Exception as exc:
                st.error(f"⛔ {exc}")
                st.session_state.pop("market_data", None)

    if "market_data" not in st.session_state:
        _render_empty_state()
        return

    d         = st.session_state["market_data"]
    direction = st.session_state.get("direction", direction)

    # ── ① Market Data ─────────────────────────────────────────────────────────
    st.markdown(f'<div class="section-label">① Market Data {dir_badge}</div>', unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)
    chg_color = "#2ECC71" if d["day_chg"] >= 0 else "#E74C3C"
    chg_sign  = "+" if d["day_chg"] >= 0 else ""

    with c1:
        local_note = ""
        if d.get("currency", "USD") != "USD":
            local_note = f"<div class='sub' style='color:#888'>{d['currency']} {d['price_local']:,.4g} @ {d['fx_rate']:.4f}</div>"
        src_badge = (
            "<span style='font-size:0.6rem;color:#2ECC71;margin-left:4px'>yf</span>"
            if d.get("data_source") == "yfinance"
            else "<span style='font-size:0.6rem;color:#888;margin-left:4px'>av</span>"
        )
        st.markdown(f"""
        <div class="metric-card accent">
            <div class="label">{d['ticker']} · Last Price (USD){src_badge}</div>
            <div class="value">${d['price']:,.4g}</div>
            <div class="sub" style="color:{chg_color}">{chg_sign}{d['day_chg']:,.4g} ({chg_sign}{d['day_chg_pct']:.2f}%)</div>
            {local_note}
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">ATR (14)</div>
            <div class="value">${d['atr14']:,.4g}</div>
            <div class="sub">{d['atr_pct']:.1f}% of price</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">60d Realised Vol</div>
            <div class="value">{d['vol60']*100:.1f}%</div>
            <div class="sub">Daily: {d['vol60']/math.sqrt(252)*100:.2f}% · §8.1</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        vr = d['vol_regime']
        vr_col = "#E74C3C" if vr >= 1.5 else "#F39C12" if vr >= 1.2 else "#2ECC71" if vr < 0.8 else "#E8E8E8"
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Vol Regime Ratio</div>
            <div class="value" style="color:{vr_col}">{vr:.2f}×</div>
            <div class="sub">{vol_regime_label(vr).split(' (')[0]}</div>
        </div>""", unsafe_allow_html=True)
    with c5:
        if d["is_fx"]:
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">Instrument Type</div>
                <div class="value" style="font-size:1rem">FX Pair</div>
                <div class="sub">{d['ticker']}</div>
            </div>""", unsafe_allow_html=True)
        else:
            tier_auto = d['tier']
            badge_cls = "badge-t1" if tier_auto == "Tier 1" else "badge-t2" if tier_auto == "Tier 2" else "badge-t3"
            mc = f"${d['mkt_cap']/1e9:.1f}B" if d['mkt_cap'] >= 1e9 else (f"${d['mkt_cap']/1e6:.0f}M" if d['mkt_cap'] else "N/A")
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">Tier (§6.2) · Mkt Cap</div>
                <div class="value" style="font-size:1.1rem"><span class="badge {badge_cls}">{tier_auto}</span></div>
                <div class="sub">{mc} · {d['exchange'] or 'N/A'}</div>
            </div>""", unsafe_allow_html=True)

    if not d["is_fx"]:
        st.markdown(f"""
        <div class="info-box">
        📍 <b>{d['name']}</b> &nbsp;·&nbsp; {d['sector'] or 'Sector N/A'} &nbsp;·&nbsp;
        5-Day ADV: <b>{d['adv5']:,} shares</b> &nbsp;·&nbsp;
        60d ADV: <b>${d['adv60_usd']/1e6:.1f}M/day</b>
        </div>""", unsafe_allow_html=True)

    st.markdown('<hr class="pl-divider">', unsafe_allow_html=True)

    # ── ② Conviction Scoring & Quality Scoring & Parameters ──────────────────
    st.markdown('<div class="section-label">② Conviction Scoring (§8.3) · Quality Scoring (§9.1) · Position Parameters</div>', unsafe_allow_html=True)

    col_conv, col_param = st.columns([4, 5])

    with col_conv:
        # ── Conviction Score (→ position size) ───────────────────────────────
        st.markdown("**① Conviction Score** *(max 100 — §8.3 · scales position size)*")
        c1s = st.slider("1. Revenue Growth Quality (25)",     0, 25, 15, key="c1",
                        help="Accelerating >20% YoY: 25 | Stable 10-20%: 18 | 0-10%: 10 | Declining: 0")
        c2s = st.slider("2. Competitive Moat / Pricing Power (20)", 0, 20, 12, key="c2",
                        help="Strong moat (network, patent, brand): 20 | Moderate: 12 | Limited: 5 | None: 0")
        c3s = st.slider("3. Thematic Alignment (15)",         0, 15,  9, key="c3",
                        help="Core theme (AI, robotics, disruptive tech): 15 | Adjacent: 8 | None: 0")
        c4s = st.slider("4. Technical Confirmation (20)",     0, 20, 12, key="c4",
                        help="Stage 2 uptrend, above 50 & 200 MA, volume expansion: 20 | Mixed: 12 | Weak: 5 | Bearish: 0")
        c5s = st.slider("5. Catalyst Clarity & Valuation (20)", 0, 20, 12, key="c5",
                        help="Clear catalyst + reasonable valuation: 20 | One without other: 12 | No catalyst: 5 | Expensive/no catalyst: 0")
        conviction_score = c1s + c2s + c3s + c4s + c5s

        conv_mult = score_to_mult(conviction_score, CONVICTION_TABLE)
        conv_level = (
            "Maximum (1.50×)" if conviction_score >= 80 else
            "High (1.25×)"    if conviction_score >= 60 else
            "Standard (1.00×)"if conviction_score >= 40 else
            "Reduced (0.75×)" if conviction_score >= 20 else
            "Minimal (0.50×) ⚠️ Reconsider entry"
        )
        st.markdown(f"""
        <div class="metric-card" style="margin-top:0.5rem;border-color:#E8B84B33">
            <div class="label">Conviction Total · Multiplier → <b>Position Size</b></div>
            <div class="value">{conviction_score}/100</div>
            <div class="sub" style="color:#E8B84B">{conv_level}</div>
        </div>""", unsafe_allow_html=True)
        _progress_bar(conviction_score / 100, "#E8B84B")

        if conviction_score < 40:
            st.warning("⚠️ Score <40: IC discussion required before opening position (Methodology §8.3)")

        # ── Quality Score (→ stop width) ──────────────────────────────────────
        st.markdown('<hr class="pl-divider">', unsafe_allow_html=True)
        st.markdown("**② Quality Score** *(max 100 — §9.1 · widens / tightens stop)*")
        st.markdown(
            "<div style='font-size:0.72rem;color:#888;margin-bottom:0.4rem'>"
            "High-quality businesses earn wider stops — prospective names like CSG "
            "aren't stopped out on routine vol. Low quality gets tighter risk control."
            "</div>", unsafe_allow_html=True
        )
        q1s = st.slider("1. Balance Sheet Health (20)",        0, 20, 12, key="q1",
                        help="Net cash / low leverage, high interest coverage: 20 | Modest debt, manageable: 12 | Levered, fragile: 5 | Distressed: 0")
        q2s = st.slider("2. Earnings Consistency (20)",        0, 20, 12, key="q2",
                        help="Consistent beats, low earnings variability, FCF ≈ net income: 20 | Moderate consistency: 12 | Lumpy / miss-heavy: 5 | Unpredictable: 0")
        q3s = st.slider("3. Returns on Capital (20)",          0, 20, 12, key="q3",
                        help="ROIC/ROE well above sector median, improving trend: 20 | In line with sector: 12 | Below median: 5 | Capital destructive: 0")
        q4s = st.slider("4. Management & Governance (20)",     0, 20, 12, key="q4",
                        help="Strong capital allocation track record, meaningful insider ownership: 20 | Competent, neutral: 12 | Questionable decisions: 5 | Poor governance: 0")
        q5s = st.slider("5. Business Model Resilience (20)",   0, 20, 12, key="q5",
                        help="Recurring revenues, high switching costs, stable margins through cycles: 20 | Moderate resilience: 12 | Cyclical, margin-volatile: 5 | Highly fragile: 0")
        quality_score = q1s + q2s + q3s + q4s + q5s

        qual_mult = score_to_mult(quality_score, QUALITY_TABLE)
        qual_level = (
            "High Quality (1.20× stop)" if quality_score >= 80 else
            "Good Quality (1.10× stop)" if quality_score >= 60 else
            "Standard (1.00× stop)"     if quality_score >= 40 else
            "Below Avg (0.95× stop)"    if quality_score >= 20 else
            "Low Quality (0.90× stop)"
        )
        st.markdown(f"""
        <div class="metric-card" style="margin-top:0.5rem;border-color:#3B82F633">
            <div class="label">Quality Total · Multiplier → <b>Stop Width</b></div>
            <div class="value">{quality_score}/100</div>
            <div class="sub" style="color:#60A5FA">{qual_level}</div>
        </div>""", unsafe_allow_html=True)
        _progress_bar(quality_score / 100, "#3B82F6")

    with col_param:
        st.markdown("**Position Parameters**")

        pcol1, pcol2 = st.columns(2)
        with pcol1:
            entry_price = st.number_input(
                "Entry Price (USD)",
                min_value=0.0001, value=float(st.session_state.get("entry_price", d["price"])),
                format="%.4f",
                help="Default = last close. Override with your planned fill.",
            )
        with pcol2:
            pos_type_auto = infer_position_type(conviction_score)
            pos_type = st.selectbox(
                "Position Type / Horizon",
                ["Extended-Hold", "LT Strategic", "Core", "Tactical", "Discretionary"],
                index=["Extended-Hold", "LT Strategic", "Core", "Tactical"].index(pos_type_auto),
                help="Extended-Hold >12m (1.20×) | LT Strategic 6-12m (1.00×) | Core 1-6m (0.85×) | Tactical <1m (0.60×) · §4.3",
            )
        discretionary = (pos_type == "Discretionary")
        effective_pos_type = "Tactical" if discretionary else pos_type

        tier_options_base = ["Tier 1", "Tier 2", "Tier 3"]
        tier_default = "Tier 1" if d["is_fx"] else d["tier"]
        tier_idx = tier_options_base.index(tier_default) if tier_default in tier_options_base else 1
        tier = st.selectbox("Tier (§6.2)",
            tier_options_base, index=tier_idx,
            help="Auto-classified from mkt cap / exchange / 60d ADV. Tier 1: mktcap >$10B + major exchange + ADV >$50M/day")

        scol1, scol2 = st.columns(2)
        with scol1:
            sector_pct = st.number_input(
                "Existing Sector Exposure (% NAV)",
                min_value=0.0, max_value=100.0, value=0.0, step=0.5, format="%.1f",
                help="Current sector total before this trade. §6.3: warn at 15%, cap at 20%.",
            )
        with scol2:
            country_pct = st.number_input(
                "Existing Country Exposure (% NAV)",
                min_value=0.0, max_value=100.0, value=0.0, step=0.5, format="%.1f",
                help="Current country total before this trade. §6.3: developed 25-30%, EM 15%.",
            )

        if direction == "Long":
            thesis_floor_default = round(entry_price * 0.85, 2)
            thesis_label = "Thesis Invalidation Floor (Long)"
            thesis_help  = "Price below which your thesis is wrong. Stop cannot go below this. Also defines hard stop anchor."
        else:
            thesis_floor_default = round(entry_price * 1.15, 2)
            thesis_label = "Thesis Invalidation Ceiling (Short)"
            thesis_help  = "Price above which your short thesis is wrong. Stop cannot go above this level."

        thesis_floor = st.number_input(
            thesis_label,
            min_value=0.0001 if direction == "Long" else entry_price,
            max_value=entry_price if direction == "Long" else entry_price * 5,
            value=thesis_floor_default,
            step=0.01, format="%.2f",
            help=thesis_help,
        )

        tp_dir_word = "above" if direction == "Long" else "below"
        st.markdown(f"**Take-Profit Levels** *(R-multiples vs ATR stop — {tp_dir_word} entry)*")
        tp_r_cols = st.columns(4)
        tp_rs = []
        for i, (col, default) in enumerate(zip(tp_r_cols, [1.5, 2.5, 4.0, 6.0])):
            with col:
                tp_rs.append(st.number_input(f"TP{i+1}", value=float(default), min_value=0.1,
                    step=0.5, format="%.1f", key=f"tp{i}"))

    st.markdown('<hr class="pl-divider">', unsafe_allow_html=True)

    # ── ③ Calculate ───────────────────────────────────────────────────────────
    result = size_position(
        nav=nav,
        vol60=d["vol60"],
        entry_price=entry_price,
        atr14=d["atr14"],
        conviction=conviction_score,
        quality_score=quality_score,
        vol_regime=d["vol_regime"],
        pos_type=effective_pos_type,
        tier=tier,
        direction=direction,
        sector_pct_nav=sector_pct,
        country_pct_nav=country_pct,
        thesis_floor=thesis_floor,
        portfolio_heat=portfolio_heat,
        adv5=d["adv5"],
        stress_mode=stress_mode,
        tp_r_multiples=tp_rs,
        discretionary=discretionary,
    )

    shares    = result["shares"]
    pos_value = result["pos_value"]

    # ── ④ Output ──────────────────────────────────────────────────────────────
    st.markdown(f'<div class="section-label">③ Position Output — {direction} {d["ticker"]}</div>', unsafe_allow_html=True)

    # Heat blocked banner
    if result["heat_blocked"]:
        st.error("🔴 **HARD STOP — No new positions.** Portfolio heat exceeds 8% NAV (§10.2). Reduce existing positions before initiating new trades. Mandatory IC review.")
        shares = 0; pos_value = 0

    out_l, out_m, out_r = st.columns([2, 2, 3])

    with out_l:
        stop_price = result["effective_stop"]
        stop_color_class = "stop-box-long" if direction == "Long" else "stop-box-short"
        price_cls = "price-long" if direction == "Long" else "price-short"
        stop_dir  = "below" if direction == "Long" else "above"

        flags = []
        if result["floor_clamped"]:
            flags.append("⚠️ Clamped to thesis floor")
        if result["atr_stop_clamped"] and not result["floor_clamped"]:
            flags.append(f"⚠️ Hard stop ({result['hard_stop_pct']:.0f}%) tighter than ATR stop")

        vr_lbl  = vol_regime_label(d["vol_regime"]).split(" (")[0]
        comp_detail = (
            f"Base {result['base_atr_mult']}× "
            f"× vol-regime {result['vr_stop_mult']}× ({vr_lbl}) "
            f"× quality {result['qual_stop_mult']}× "
            f"= <b>{result['atr_mult']}× ATR</b>"
        )
        hard_stop_sign = "-" if direction == "Long" else "+"
        hard_stop_ref = f"{hard_stop_sign}{result['hard_stop_pct']:.0f}%"
        hard_stop_section = "§9.2" if not discretionary else "§7.4 Disc"

        st.markdown(f"""
        <div class="stop-box {stop_color_class}">
            <div class="label" style="font-size:0.68rem;color:#E74C3C;letter-spacing:0.1em;text-transform:uppercase;font-weight:700">
                {"Stop-Loss" if direction == "Long" else "Buy-to-Cover Stop"}
            </div>
            <div class="{price_cls}">${stop_price:,.4g}</div>
            <div class="detail">
                {stop_dir.capitalize()} entry by ${result['stop_dist']:,.4g} ({result['stop_dist']/entry_price*100:.1f}%)<br>
                ATR stop: Entry {"-" if direction == "Long" else "+"} {comp_detail} = ${result['atr_stop_price']:,.4g}<br>
                {"<br>".join(flags) if flags else ""}
            </div>
        </div>
        <div class="hard-stop-box">
            ⛔ {hard_stop_section} Hard stop: ${result['hard_stop_price']:,.4g} ({hard_stop_ref} from entry)
        </div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        pos_val_m   = pos_value / 1e6 if pos_value >= 1e6 else None
        pos_display = f"${pos_val_m:.2f}M" if pos_val_m else f"${pos_value:,.0f}"
        shares_label = "Shares to Buy (Long)" if direction == "Long" else "Shares to Sell Short"

        st.markdown(f"""
        <div class="metric-card {"green" if direction == "Long" else "short-card"}">
            <div class="label">{shares_label}</div>
            <div class="value" style="color:{"#2ECC71" if direction == "Long" else "#A855F7"}">{shares:,}</div>
            <div class="sub">Value: {pos_display} ({result['pos_pct_nav']:.1f}% NAV)</div>
        </div>""", unsafe_allow_html=True)

        risk_usd = result["position_risk"]
        st.markdown(f"""
        <div class="metric-card red">
            <div class="label">Position Risk (Entry→Stop)</div>
            <div class="value">${risk_usd:,.0f}</div>
            <div class="sub">{result['new_heat_pct']:.2f}% heat added · {result['signoff']}</div>
        </div>""", unsafe_allow_html=True)

        if result["heat_status"] == "amber" and not result["heat_blocked"]:
            st.warning("🟡 **Amber heat zone** — position size automatically reduced 25% (§10.2). Risk officer must be notified.")

    with out_m:
        # Take-profit
        tp_chip_cls = "tp-chip-long" if direction == "Long" else "tp-chip-short"
        pct_label   = "above" if direction == "Long" else "below"
        tp_html = f'<div style="font-size:0.8rem;font-weight:600;margin-bottom:0.4rem">Take-Profit Levels ({pct_label} entry)</div><div class="tp-row">'
        for tp in result["tp_levels"]:
            tp_html += f"""
            <div class="tp-chip {tp_chip_cls}">
                <div class="r">R{tp['r']:.0f}×</div>
                <div class="price">${tp['price']:,.4g}</div>
                <div class="pct">{("+" if direction == "Long" else "-")}{tp['pct']:.1f}%</div>
            </div>"""
        tp_html += "</div>"
        st.markdown(tp_html, unsafe_allow_html=True)

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        # Concentration checks
        st.markdown('<div style="font-size:0.8rem;font-weight:600;margin-bottom:0.4rem">Concentration Checks (§6.3)</div>', unsafe_allow_html=True)

        _cap_row(f"Sector after trade: {result['sector_after']:.1f}% NAV",
                 "⛔ Breach >20%" if result["sector_breach"] else ("⚠️ Warn >15%" if result["sector_warn"] else "✅ OK"),
                 "fail" if result["sector_breach"] else ("warn" if result["sector_warn"] else "pass"))
        _progress_bar(result["sector_after"] / 20, "#E74C3C" if result["sector_breach"] else "#F39C12" if result["sector_warn"] else "#2ECC71")

        _cap_row(f"Country after trade: {result['country_after']:.1f}% NAV",
                 "⛔ >30% (developed)" if result["country_breach"] else "✅ OK",
                 "fail" if result["country_breach"] else "pass")

        hard_cap_pct = result["hard_cap_pct"]
        cap_ok = result["pos_pct_nav"] <= hard_cap_pct
        _cap_row(f"Single-issuer: {result['pos_pct_nav']:.1f}% NAV (cap {hard_cap_pct:.0f}%)",
                 "✅ OK" + (" — IC approval required" if result["tier1_ic_flag"] else ""),
                 "pass" if cap_ok else "fail")

        if not d["is_fx"] and d["adv5"] > 0:
            liq_pct = (shares / d["adv5"] * 100) if d["adv5"] else 0
            _cap_row(f"Liquidity: {liq_pct:.1f}% of 5d ADV (cap 10%)",
                     "✅ OK" if result["liquidity_ok"] else "⚠️ Exceeds 10% ADV",
                     "pass" if result["liquidity_ok"] else "warn")

        _cap_row(f"Cash floor: {100 - result['pos_pct_nav']:.1f}% remaining (min {20 if stress_mode else 15}%)",
                 "✅ OK" if result["cash_ok"] else "⚠️ Below floor",
                 "pass" if result["cash_ok"] else "warn")

        # Portfolio heat gauge
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        total_h = result["total_heat_pct"]
        heat_col_map = {"green": "#2ECC71", "amber": "#F39C12", "red": "#E74C3C"}
        heat_col = heat_col_map[result["heat_status"]]
        st.markdown(f"""
        <div class="metric-card" style="border-color:{heat_col}33">
            <div class="label">Portfolio Heat After Trade (§10.2)</div>
            <div class="value" style="font-size:1.2rem;color:{heat_col}">{total_h:.2f}%</div>
            <div class="sub">Existing {portfolio_heat:.1f}% + New {result['new_heat_pct']:.2f}% · Cap: 8% hard stop</div>
        </div>""", unsafe_allow_html=True)
        _progress_bar(min(total_h / 8.0, 1.0), heat_col)

    with out_r:
        st.markdown("**Sizing Breakdown (Methodology Steps 1–9)**")
        breakdown_data = {
            "Step": [
                "§8.1 Base risk budget",
                "§8.1 60d Annualised Vol",
                "§8.1 Daily Vol",
                "§8.1 Base Position",
                "§8.3 Conviction Mult → SIZE",
                "§6.2 Tier Mult",
                "§4.3 Time Horizon Mult",
                "Step 5 Adjusted Position",
                "§8.2 Hard Cap",
                "Final Position (pre-stress)",
                "Stress adjustment" if stress_mode else "Market Stress",
                "§9.1 Base ATR Mult",
                "§9.1 Vol Regime Mult → STOP",
                "§9.1 Quality Mult → STOP",
                "§9.1 Composite ATR Mult",
                "§9.1 ATR Stop",
                f"§{'7.4' if discretionary else '9.2'} Hard Stop",
                "Effective Stop",
                "Risk / Share",
                "Position Risk (heat)",
            ],
            "Value": [
                f"${result['risk_budget']:,.0f} (0.5% NAV)",
                f"{d['vol60']*100:.1f}%",
                f"{result['daily_vol']:.3f}%",
                f"${result['base_pos_usd']:,.0f}",
                f"{result['conv_mult']}× (score {conviction_score}/100)",
                f"{result['tier_mult']}× ({tier})",
                f"{result['time_mult']}× ({effective_pos_type})",
                f"${result['adj_pos_usd']:,.0f}",
                f"{result['hard_cap_pct']:.0f}% NAV = ${result['hard_cap_usd']:,.0f}",
                f"${result['final_pos_usd']:,.0f} ({result['pos_pct_nav']:.1f}% NAV)",
                "0.75× applied" if stress_mode else "Normal (1.00×)",
                f"{result['base_atr_mult']}× ({effective_pos_type})",
                f"{result['vr_stop_mult']}× (regime: {vol_regime_label(d['vol_regime']).split(' (')[0]})",
                f"{result['qual_stop_mult']}× (quality score {quality_score}/100)",
                f"{result['atr_mult']}× (composite, cap {MAX_COMPOSITE_ATR}×)",
                f"${result['atr_stop_price']:,.4g}",
                f"${result['hard_stop_price']:,.4g} ({'-' if direction == 'Long' else '+'}{result['hard_stop_pct']:.0f}%)",
                f"${result['effective_stop']:,.4g}",
                f"${result['risk_per_share']:,.4g}",
                f"${result['position_risk']:,.0f} ({result['new_heat_pct']:.2f}% NAV)",
            ],
        }
        df_bd = pd.DataFrame(breakdown_data)
        st.dataframe(df_bd, use_container_width=True, hide_index=True,
                     column_config={
                         "Step":  st.column_config.TextColumn(width="medium"),
                         "Value": st.column_config.TextColumn(width="medium"),
                     })

        # §8.2 2σ client check
        st.markdown(f"""
        <div class="metric-card" style="margin-top:0.5rem;font-size:0.8rem">
            <div class="label">§8.2 Client 2σ Risk Check</div>
            <div class="sub" style="color:#ccc;margin-top:0.3rem">
            2σ loss = {shares:,} × ${entry_price:,.4g} × 2 × {result['daily_vol']:.3f}% = <b>${result['sigma2_loss']:,.0f}</b><br>
            Must be ≤ 1% of smallest client portfolio to proceed.
            </div>
        </div>""", unsafe_allow_html=True)

        if result["tier1_ic_flag"]:
            st.info("🔵 **Tier 1 IC Approval Required** — position >3% NAV in Tier 1 issuer requires 2-of-3 principal sign-off (§8.2)")

    # ── Pre-Trade Checklist ────────────────────────────────────────────────────
    with st.expander("☑️ Pre-Trade Checklist (§7.3 — complete before any order)"):
        checks = [
            ("Step 1", "Base position calculated using 60-day annualised vol",                           True),
            ("Step 2", f"Conviction score recorded in IM ({conviction_score}/100) · Quality score ({quality_score}/100)", conviction_score > 0),
            ("Step 3", f"Tier classification confirmed: {tier}",                                          True),
            ("Step 4", f"Time horizon: {effective_pos_type} ({result['time_mult']}×)",                   True),
            ("Step 5", f"Adjusted position: ${result['adj_pos_usd']:,.0f}",                              True),
            ("6a",     f"Single-issuer cap: {result['pos_pct_nav']:.1f}% ≤ {result['hard_cap_pct']:.0f}% NAV", result['pos_pct_nav'] <= result['hard_cap_pct']),
            ("6b",     f"Sector: {result['sector_after']:.1f}% NAV {'⚠️ WARN' if result['sector_warn'] else '✅'}",    not result["sector_breach"]),
            ("6c",     f"Country: {result['country_after']:.1f}% NAV {'✅' if not result['country_breach'] else '⚠️ BREACH'}",  not result["country_breach"]),
            ("6d",     f"Liquidity: ≤10% of 5d ADV {'✅' if result['liquidity_ok'] else '⚠️ VERIFY'}",  result["liquidity_ok"]),
            ("6e",     f"Cash floor: ≥{20 if stress_mode else 15}% NAV post-trade {'✅' if result['cash_ok'] else '⚠️ BREACH'}", result["cash_ok"]),
            ("Step 7", f"Composite ATR {result['atr_mult']}× stop ${result['atr_stop_price']:,.4g} + {result['hard_stop_pct']:.0f}% hard stop ${result['hard_stop_price']:,.4g} logged", True),
            ("Step 8", f"Portfolio heat: {result['total_heat_pct']:.2f}% — {result['heat_status'].upper()}",   not result["heat_blocked"]),
            ("Step 9", f"2σ client check: ${result['sigma2_loss']:,.0f} (verify ≤ 1% of smallest client portfolio)", True),
            ("Sign-off", result["signoff"],                                                              True),
            ("Sanctions", "Sanctions screening completed; no MNPI held",                                 None),
        ]
        for ref, label, ok in checks:
            icon = "✅" if ok is True else ("❌" if ok is False else "☐")
            color = "#2ECC71" if ok is True else ("#E74C3C" if ok is False else "#888")
            st.markdown(f"""
            <div class="checklist-item">
                <span style="color:{color};font-weight:700;min-width:2rem">{icon}</span>
                <span style="color:#888;min-width:3rem;font-size:0.72rem">{ref}</span>
                <span>{label}</span>
            </div>""", unsafe_allow_html=True)

    with st.expander("📖 How to use this tool"):
        st.markdown(f"""
**Workflow:**
1. Set **Fund NAV** and **existing portfolio heat** in the sidebar
2. Type a ticker + select **Long or Short** → click ⚡ Fetch
3. Score **Conviction** (5 factors, 0-100) — scales position **size** (§8.3)
4. Score **Quality** (5 factors, 0-100) — scales stop **width** (§9.1 composite)
5. Set **entry price**, **position type**, **tier**, **sector/country exposure**, **thesis floor**
6. Read the output — shares, composite stop, TP levels, all concentration checks

**Position sizing formula (§8.1):**
- Base = (0.5% × NAV) ÷ Daily Vol · Adjusted = Base × Conviction × Tier × Time
- Final = min(Adjusted, Hard Cap) · Caps: 3% standard / 5% Tier 1 IC / 2% Discretionary

**Composite stop-loss (§9.1 + Quality scoring):**
- Base ATR mult: Extended-Hold/LT Strategic = 3.0×, Core = 2.5×, Tactical = 2.0×
- × Vol Regime mult: Compressed 0.90× | Normal 1.00× | Elevated 1.15× | Very Elevated 1.30×
- × Quality mult: Low Quality 0.90× → High Quality 1.20×
- = Composite ATR Mult (capped at {MAX_COMPOSITE_ATR}×)
- Hard stop: −25% standard (§9.2) · −20% Discretionary (§7.4)

**Concentration limits:**
- Single issuer: 3% NAV (5% Tier 1 with IC) · 2% Discretionary §8.2/§7.4
- Sector: warn 15%, cap 20% §6.3 · Country: 25-30% developed, 15% EM §6.3
- Portfolio heat: Green <6%, Amber 6-8% (reduce 25%), Red >8% (no new positions) §10.2
        """)


# ── UI HELPERS ────────────────────────────────────────────────────────────────

def _progress_bar(fraction: float, color: str = "#E8B84B"):
    pct = min(max(fraction * 100, 0), 100)
    st.markdown(f"""
    <div class="heat-bar-wrap">
        <div class="heat-bar" style="width:{pct:.1f}%;background:{color}"></div>
    </div>""", unsafe_allow_html=True)


def _cap_row(label: str, status: str, level: str):
    cls = {"pass": "cap-pass", "warn": "cap-warn", "fail": "cap-fail"}.get(level, "cap-pass")
    st.markdown(f"""
    <div class="cap-row {cls}">
        <span>{label}</span><span><b>{status}</b></span>
    </div>""", unsafe_allow_html=True)


def _render_empty_state():
    st.markdown("""
    <div style="text-align:center;padding:4rem 2rem;color:#555">
        <div style="font-size:3rem;margin-bottom:1rem">📐</div>
        <div style="font-size:1.1rem;color:#888;margin-bottom:0.5rem">Enter a ticker and click <b style="color:#E8B84B">⚡ Fetch</b> to begin sizing</div>
        <div style="font-size:0.8rem;color:#555">
        US: AAPL · PLTR · MSFT · HD &nbsp;|&nbsp; HK: 9880.HK (UBTECH) · 0700.HK (Tencent)<br>
        EU: SAP.DE · RHM.DE · NESN.SW · BP.L &nbsp;|&nbsp; FX: EURUSD · GBPUSD · USDJPY<br>
        Non-USD prices auto-converted to USD for sizing
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── ENTRY ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
