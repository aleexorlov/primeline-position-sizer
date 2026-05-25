#!/usr/bin/env python3
"""
Primeline Capital — Position Sizer Web App
AIFM-compliant position sizing tool with composite dynamic stop-loss.
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
/* Header bar */
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

/* Section labels */
.section-label {
    font-size: 0.65rem; font-weight: 700; letter-spacing: 0.14em;
    text-transform: uppercase; color: #E8B84B; margin-bottom: 0.5rem;
    border-bottom: 1px solid #2A2D3A; padding-bottom: 0.3rem;
}

/* Metric cards */
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

/* Output panel */
.output-panel {
    background: #12141E; border: 1px solid #2A2D3A; border-radius: 10px;
    padding: 1.5rem; margin-top: 1rem;
}
.output-panel h3 { color: #E8B84B; font-size: 1rem; margin-bottom: 1rem; }

/* Tier badge */
.badge {
    display: inline-block; padding: 0.2rem 0.7rem; border-radius: 20px;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.05em;
}
.badge-t1 { background: #0D3320; color: #2ECC71; border: 1px solid #2ECC71; }
.badge-t2 { background: #1A2A10; color: #A8E063; border: 1px solid #A8E063; }
.badge-t3 { background: #2A1A08; color: #E8A430; border: 1px solid #E8A430; }

/* Stop display */
.stop-box {
    background: linear-gradient(135deg, #1E1015, #1A0D12);
    border: 1px solid #E74C3C55; border-radius: 8px;
    padding: 1rem 1.2rem;
}
.stop-box .price { font-size: 2rem; font-weight: 700; color: #E74C3C; }
.stop-box .detail { font-size: 0.78rem; color: #aaa; margin-top: 0.3rem; }

/* TP levels */
.tp-row { display: flex; gap: 0.5rem; margin-top: 0.4rem; }
.tp-chip {
    flex: 1; text-align: center; background: #0D1E14;
    border: 1px solid #2ECC7155; border-radius: 6px; padding: 0.5rem 0.3rem;
}
.tp-chip .r { font-size: 0.65rem; color: #2ECC71; font-weight: 700; }
.tp-chip .price { font-size: 1rem; font-weight: 700; color: #E8E8E8; }
.tp-chip .pct { font-size: 0.7rem; color: #aaa; }

/* Heat bar */
.heat-bar-wrap { background: #1A1D27; border-radius: 6px; overflow: hidden; height: 8px; margin-top: 6px; }
.heat-bar { height: 8px; border-radius: 6px; transition: width 0.5s; }

/* Info box */
.info-box {
    background: #1A1D27; border-left: 3px solid #E8B84B;
    padding: 0.7rem 1rem; border-radius: 0 6px 6px 0;
    font-size: 0.8rem; color: #ccc; margin: 0.5rem 0;
}

/* Divider */
.pl-divider { border: none; border-top: 1px solid #2A2D3A; margin: 1.2rem 0; }
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────

AV_BASE = "https://www.alphavantage.co/query"

TIER1_EXCHANGES = {
    "NYSE", "NASDAQ", "LSE", "LONDON STOCK EXCHANGE",
    "EURONEXT", "EURONEXT AMSTERDAM", "AEB", "AMSTERDAM",
    "XETRA", "FRANKFURT", "SIX", "SWISS EXCHANGE",
}

FX_PAIRS = {
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD",
    "USDCAD", "EURGBP", "EURJPY", "GBPJPY", "USDMXN", "USDZAR",
    "EUR/USD", "GBP/USD", "USD/JPY", "EUR/GBP", "GBP/JPY",
}

# Conviction score → multiplier
CONVICTION_TABLE = [(80, 1.25), (70, 1.10), (55, 1.00), (40, 0.90), (0, 0.80)]

# Quality score → multiplier
QUALITY_TABLE = [(75, 1.20), (60, 1.10), (40, 1.00), (0, 0.90)]

# Base stop multiplier by position type
BASE_MULT = {
    "Extended-Hold": 3.0,
    "LT Strategic":  2.75,
    "Core":          2.5,
    "Tactical":      2.0,
}

# Tier stop multiplier
TIER_MULT = {"Tier 1": 1.25, "Tier 2": 1.00, "Tier 3": 0.75}

# Max heat multiplier (vol regime cap: 5×)
VOL_REGIME_MULT = {
    "Very Elevated (≥1.50×)":  1.30,
    "Elevated (1.20-1.49×)":   1.15,
    "Normal (0.80-1.19×)":     1.00,
    "Compressed (<0.80×)":     0.90,
}


# ── HELPERS ───────────────────────────────────────────────────────────────────

def score_to_mult(score: float, table: list) -> float:
    for threshold, mult in table:
        if score >= threshold:
            return mult
    return table[-1][1]


def vol_regime_label(ratio: float) -> str:
    if ratio >= 1.50:
        return "Very Elevated (≥1.50×)"
    if ratio >= 1.20:
        return "Elevated (1.20-1.49×)"
    if ratio < 0.80:
        return "Compressed (<0.80×)"
    return "Normal (0.80-1.19×)"


def infer_position_type(conviction: float, quality: float) -> str:
    total = conviction + quality
    if conviction >= 80 and quality >= 80:
        return "Extended-Hold"
    if conviction >= 70 and quality >= 70:
        return "LT Strategic"
    if conviction >= 50 and quality >= 50:
        return "Core"
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


# ── ALPHA VANTAGE ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def fetch_data(ticker: str, api_key: str) -> dict:
    ticker = ticker.upper().strip()
    ticker_clean = ticker.replace("/", "").replace("-", "")
    fx = is_fx(ticker)

    # ── daily series ──────────────────────────────────────────────────────────
    if fx:
        from_cur = ticker_clean[:3]
        to_cur   = ticker_clean[3:]
        raw = _av_get({
            "function":    "FX_DAILY",
            "from_symbol": from_cur,
            "to_symbol":   to_cur,
            "outputsize":  "compact",
            "apikey":      api_key,
        })
        ts_key = "Time Series FX (Daily)"
        ts     = raw.get(ts_key)
        name   = f"{from_cur}/{to_cur} (FX)"
    else:
        raw = _av_get({
            "function":   "TIME_SERIES_DAILY",
            "symbol":     ticker,
            "outputsize": "compact",
            "apikey":     api_key,
        })
        ts_key = "Time Series (Daily)"
        ts     = raw.get(ts_key)
        name   = ticker

    if not ts:
        raise ValueError(f"No price data returned for '{ticker}'. Check the ticker symbol.")

    rows = []
    for d, v in ts.items():
        rows.append({
            "date":   d,
            "close":  float(v.get("4. close", v.get("4. Close", 0))),
            "high":   float(v.get("2. high",  v.get("2. High",  0))),
            "low":    float(v.get("3. low",   v.get("3. Low",   0))),
            "volume": float(v.get("5. volume", 0)),
        })

    df    = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    close = df["close"]
    high  = df["high"]
    low   = df["low"]

    if len(df) < 20:
        raise ValueError(f"Insufficient history for {ticker} (only {len(df)} bars).")

    price      = float(close.iloc[-1])
    prev_price = float(close.iloc[-2]) if len(close) >= 2 else price
    day_chg    = round(price - prev_price, 4)
    day_chg_pct = round((day_chg / prev_price) * 100, 2) if prev_price else 0

    # ATR(14)
    prev  = close.shift(1)
    tr    = (high - low).combine((high - prev).abs(), max).combine((low - prev).abs(), max)
    atr14 = float(tr.rolling(14).mean().iloc[-1])

    # 60d realised vol
    vol60 = float(close.pct_change().dropna().tail(60).std() * math.sqrt(252))

    # ADV
    adv5 = float(df["volume"].tail(5).mean()) if not fx else 0
    adv60_usd = float(df["volume"].tail(60).mean()) * price if not fx else 0

    # Vol regime ratio
    atr_pct       = tr.rolling(14).mean() / close
    avg90_atr_pct = float(atr_pct.tail(90).mean())
    cur_atr_pct   = atr14 / price if price else 0
    vol_regime    = round(cur_atr_pct / avg90_atr_pct, 2) if avg90_atr_pct else 1.0

    # Overview (equity only)
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
        "price":        round(price, 4),
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
    }


def _av_get(params: dict) -> dict:
    resp = requests.get(AV_BASE, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    for bad_key in ("Error Message", "Note", "Information"):
        if bad_key in data:
            raise ValueError(f"Alpha Vantage: {data[bad_key][:200]}")
    return data


# ── POSITION SIZING ENGINE ────────────────────────────────────────────────────

def size_position(
    nav:            float,
    price:          float,
    entry_price:    float,
    atr14:          float,
    vol_regime:     float,
    conviction:     float,
    quality:        float,
    pos_type:       str,
    tier:           str,
    sector_pct_nav: float,
    thesis_floor:   float,
    risk_pct_nav:   float,
    tp_r_multiples: list,
) -> dict:
    """Core position sizing calculation — AIFM composite dynamic stop-loss."""

    # ── multipliers ───────────────────────────────────────────────────────────
    conv_mult = score_to_mult(conviction, CONVICTION_TABLE)
    qual_mult = score_to_mult(quality,    QUALITY_TABLE)

    vr_label  = vol_regime_label(vol_regime)
    vr_mult   = VOL_REGIME_MULT[vr_label]

    base_mult = BASE_MULT.get(pos_type, 2.5)
    tier_mult = TIER_MULT.get(tier, 1.0) if "N/A" not in tier else 1.0

    # Composite stop distance (capped at 5× ATR)
    raw_dist   = base_mult * atr14 * vr_mult * conv_mult * qual_mult * tier_mult
    stop_dist  = min(raw_dist, 5.0 * atr14)
    stop_price = max(round(entry_price - stop_dist, 4), thesis_floor)

    # Effective stop distance after floor clamp
    eff_dist = entry_price - stop_price

    # Risk per share in USD
    risk_per_share = eff_dist  # already in USD for equities / base currency for FX

    # Risk budget
    risk_usd  = nav * (risk_pct_nav / 100)
    shares    = max(int(risk_usd / risk_per_share), 0) if risk_per_share > 0 else 0
    pos_value = round(shares * entry_price, 2)
    pos_pct_nav = round(pos_value / nav * 100, 2) if nav else 0

    # Heat (risk % of NAV this position adds)
    heat = round(risk_usd / nav * 100, 2) if nav else 0

    # Sector check (§7.2 max 25% per sector)
    sector_after = round(sector_pct_nav + pos_pct_nav, 2)
    sector_breach = sector_after > 25.0

    # TP levels
    tp_levels = []
    for r in tp_r_multiples:
        tp_price = round(entry_price + r * eff_dist, 4)
        tp_pct   = round((tp_price - entry_price) / entry_price * 100, 2)
        tp_levels.append({"r": r, "price": tp_price, "pct": tp_pct})

    return {
        "conv_mult":     conv_mult,
        "qual_mult":     qual_mult,
        "vr_mult":       vr_mult,
        "vr_label":      vr_label,
        "base_mult":     base_mult,
        "tier_mult":     tier_mult,
        "raw_dist":      round(raw_dist, 4),
        "stop_dist":     round(stop_dist, 4),
        "stop_price":    stop_price,
        "eff_dist":      round(eff_dist, 4),
        "risk_per_share": round(risk_per_share, 4),
        "risk_usd":      round(risk_usd, 2),
        "shares":        shares,
        "pos_value":     pos_value,
        "pos_pct_nav":   pos_pct_nav,
        "heat":          heat,
        "sector_after":  sector_after,
        "sector_breach": sector_breach,
        "tp_levels":     tp_levels,
    }


# ── SIDEBAR ───────────────────────────────────────────────────────────────────

def sidebar():
    with st.sidebar:
        st.markdown('<div class="section-label">🔑 API Configuration</div>', unsafe_allow_html=True)
        # Pre-fill from Streamlit Cloud secrets or env var if available
        import os
        _default_key = st.session_state.get("av_api_key",
            st.secrets.get("AV_API_KEY", "") if hasattr(st, "secrets") else os.environ.get("AV_API_KEY", ""))
        api_key = st.text_input(
            "Alpha Vantage API Key",
            value=_default_key,
            type="password",
            help="Free key: alphavantage.co/support/#api-key (25 req/day)",
        )
        if api_key:
            st.session_state["av_api_key"] = api_key

        st.markdown('<hr class="pl-divider">', unsafe_allow_html=True)
        st.markdown('<div class="section-label">📊 Fund Settings</div>', unsafe_allow_html=True)

        nav = st.number_input(
            "Fund NAV (USD)",
            min_value=10_000.0, max_value=1_000_000_000.0,
            value=st.session_state.get("nav", 2_500_000.0),
            step=10_000.0, format="%.0f",
        )
        st.session_state["nav"] = nav

        risk_pct = st.slider(
            "Risk per Trade (% NAV)",
            min_value=0.1, max_value=3.0,
            value=st.session_state.get("risk_pct", 1.0),
            step=0.05, format="%.2f%%",
        )
        st.session_state["risk_pct"] = risk_pct

        st.markdown('<hr class="pl-divider">', unsafe_allow_html=True)
        st.markdown('<div class="section-label">⚠️ Market Conditions</div>', unsafe_allow_html=True)
        stress_mode = st.toggle("🔴 Market Stress Mode", value=False,
            help="Applies additional 0.75× position size reduction across all trades (§7.3)")
        st.session_state["stress_mode"] = stress_mode
        if stress_mode:
            st.warning("All position sizes reduced 25% (§7.3 drawdown protocol)")

        st.markdown('<hr class="pl-divider">', unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:0.7rem;color:#666;line-height:1.6">
        <b style="color:#888">Primeline Capital OÜ</b><br>
        AIFM Position Sizer v2.0<br>
        Strategy §4, §6.2, §7, §9.1<br><br>
        Data: Alpha Vantage (free tier)<br>
        Delay: ~15 min. Not for HFT.
        </div>
        """, unsafe_allow_html=True)

    return api_key, nav, risk_pct, stress_mode


# ── MAIN APP ──────────────────────────────────────────────────────────────────

def main():
    # Header
    st.markdown("""
    <div class="pl-header">
        <div class="pl-logo">📐</div>
        <div>
            <div class="pl-title">PRIMELINE CAPITAL</div>
            <div class="pl-subtitle">AIFM Position Sizer · v2.0</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    api_key, nav, risk_pct, stress_mode = sidebar()

    # ── Ticker Input ──────────────────────────────────────────────────────────
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        ticker = st.text_input(
            "Ticker / FX Pair",
            placeholder="AAPL · MSFT · PLTR · EURUSD · HD …",
            value=st.session_state.get("ticker", ""),
            label_visibility="collapsed",
        )
    with col_btn:
        fetch_btn = st.button("⚡ Fetch", use_container_width=True, type="primary")

    # ── Fetch Data ────────────────────────────────────────────────────────────
    if fetch_btn and ticker:
        if not api_key:
            st.error("⛔ Enter your Alpha Vantage API key in the sidebar first.")
            st.stop()
        st.session_state["ticker"] = ticker.upper().strip()
        with st.spinner(f"Fetching {ticker.upper()} market data…"):
            try:
                data = fetch_data(ticker, api_key)
                st.session_state["market_data"] = data
                st.session_state["entry_price"] = data["price"]  # default to last close
            except Exception as exc:
                st.error(f"⛔ {exc}")
                st.session_state.pop("market_data", None)

    # ── Render only when we have data ─────────────────────────────────────────
    if "market_data" not in st.session_state:
        _render_empty_state()
        return

    d = st.session_state["market_data"]

    # ── ① Market Data Panel ───────────────────────────────────────────────────
    st.markdown('<div class="section-label">① Market Data</div>', unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)

    chg_color = "#2ECC71" if d["day_chg"] >= 0 else "#E74C3C"
    chg_sign  = "+" if d["day_chg"] >= 0 else ""

    with c1:
        st.markdown(f"""
        <div class="metric-card accent">
            <div class="label">{d['ticker']} · Last Close</div>
            <div class="value">${d['price']:,.4g}</div>
            <div class="sub" style="color:{chg_color}">{chg_sign}{d['day_chg']:,.4g} ({chg_sign}{d['day_chg_pct']:.2f}%)</div>
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
            <div class="sub">Annualised</div>
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
            tier = d['tier']
            badge_cls = "badge-t1" if tier == "Tier 1" else "badge-t2" if tier == "Tier 2" else "badge-t3"
            mc = f"${d['mkt_cap']/1e9:.1f}B" if d['mkt_cap'] >= 1e9 else (f"${d['mkt_cap']/1e6:.0f}M" if d['mkt_cap'] else "N/A")
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">Tier (§6.2) · Mkt Cap</div>
                <div class="value" style="font-size:1.1rem"><span class="badge {badge_cls}">{tier}</span></div>
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

    # ── ② Scoring & Parameters ────────────────────────────────────────────────
    st.markdown('<div class="section-label">② Conviction & Quality Scoring</div>', unsafe_allow_html=True)

    col_conv, col_qual, col_param = st.columns([3, 3, 4])

    with col_conv:
        st.markdown("**Conviction Score** *(max 100)*")
        c_thesis   = st.slider("Thesis strength (25)",       0, 25, 15, key="c1")
        c_catalyst = st.slider("Near-term catalyst (20)",    0, 20, 12, key="c2")
        c_macro    = st.slider("Macro alignment (15)",       0, 15,  9, key="c3")
        c_technical= st.slider("Technical setup (20)",       0, 20, 12, key="c4")
        c_risk     = st.slider("Risk/reward asymmetry (20)", 0, 20, 12, key="c5")
        conviction_score = c_thesis + c_catalyst + c_macro + c_technical + c_risk
        conv_pct = conviction_score / 100
        st.markdown(f"""
        <div class="metric-card" style="margin-top:0.5rem">
            <div class="label">Conviction Total</div>
            <div class="value">{conviction_score}/100</div>
        </div>""", unsafe_allow_html=True)
        _progress_bar(conv_pct, "#E8B84B")

    with col_qual:
        st.markdown("**Quality Score** *(max 100)*")
        q_moat     = st.slider("Competitive moat (25)",   0, 25, 15, key="q1")
        q_fin      = st.slider("Financial health (25)",   0, 25, 15, key="q2")
        q_mgmt     = st.slider("Management quality (25)", 0, 25, 15, key="q3")
        q_val      = st.slider("Valuation support (25)",  0, 25, 15, key="q4")
        quality_score = q_moat + q_fin + q_mgmt + q_val
        qual_pct = quality_score / 100
        st.markdown(f"""
        <div class="metric-card" style="margin-top:0.5rem">
            <div class="label">Quality Total</div>
            <div class="value">{quality_score}/100</div>
        </div>""", unsafe_allow_html=True)
        _progress_bar(qual_pct, "#A78BFA")

    with col_param:
        st.markdown("**Position Parameters**")

        entry_price = st.number_input(
            "Entry Price (USD)",
            min_value=0.0001, value=float(st.session_state.get("entry_price", d["price"])),
            format="%.4f",
            help="Default = last close. Override with your planned entry.",
        )

        pos_type_auto = infer_position_type(conviction_score, quality_score)
        pos_type = st.selectbox(
            "Position Type / Horizon",
            ["Extended-Hold", "LT Strategic", "Core", "Tactical"],
            index=["Extended-Hold", "LT Strategic", "Core", "Tactical"].index(pos_type_auto),
            help=f"Auto-suggested: {pos_type_auto} (from conviction + quality scores)",
        )

        tier_options = ["Tier 1", "Tier 2", "Tier 3"] if d["is_fx"] else [d["tier"], "Tier 1", "Tier 2", "Tier 3"]
        tier_default = "Tier 1" if d["is_fx"] else d["tier"]
        tier_idx     = tier_options.index(tier_default) if tier_default in tier_options else 0
        tier = st.selectbox("Tier (§6.2)", list(dict.fromkeys(tier_options)), index=tier_idx,
            help="Auto-classified from mkt cap / exchange / ADV. Override if needed.")

        sector_pct = st.number_input(
            "Current Sector Exposure (% NAV)",
            min_value=0.0, max_value=100.0, value=0.0, step=0.5, format="%.1f",
            help="Existing exposure to this sector. §7.2 cap = 25% NAV.",
        )

        thesis_floor = st.number_input(
            "Thesis Invalidation Floor",
            min_value=0.0,
            value=round(entry_price * 0.85, 2),
            step=0.01, format="%.2f",
            help="Price level that invalidates the thesis. Stop cannot be lower than this.",
        )

        st.markdown("**Take-Profit R-Multiples**")
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
        price=d["price"],
        entry_price=entry_price,
        atr14=d["atr14"],
        vol_regime=d["vol_regime"],
        conviction=conviction_score,
        quality=quality_score,
        pos_type=pos_type,
        tier=tier,
        sector_pct_nav=sector_pct,
        thesis_floor=thesis_floor,
        risk_pct_nav=risk_pct,
        tp_r_multiples=tp_rs,
    )

    # Apply stress mode
    shares = result["shares"]
    if stress_mode:
        shares = int(shares * 0.75)

    # ── ④ Output Panel ────────────────────────────────────────────────────────
    st.markdown('<div class="section-label">③ Position Output</div>', unsafe_allow_html=True)

    out_l, out_m, out_r = st.columns([2, 2, 3])

    with out_l:
        # Stop loss
        st.markdown(f"""
        <div class="stop-box">
            <div class="label" style="font-size:0.68rem;color:#E74C3C;letter-spacing:0.1em;text-transform:uppercase;font-weight:700">Dynamic Stop-Loss</div>
            <div class="price">${result['stop_price']:,.4g}</div>
            <div class="detail">
                Distance: ${result['stop_dist']:,.4g} ({result['stop_dist']/entry_price*100:.1f}% below entry)<br>
                Base {result['base_mult']}× ATR · Vol {result['vr_mult']}× · Conv {result['conv_mult']}× · Qual {result['qual_mult']}× · Tier {result['tier_mult']}×
                {"<br>⚠️ Floor-clamped (thesis invalidation)" if result['stop_price'] == thesis_floor else ""}
                {"<br>⚠️ Cap applied (5× ATR max)" if result['raw_dist'] > result['stop_dist'] + 0.001 else ""}
            </div>
        </div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

        # Sizing
        pos_val_m = result['pos_value'] / 1e6 if result['pos_value'] >= 1e6 else None
        pos_display = f"${pos_val_m:.2f}M" if pos_val_m else f"${result['pos_value']:,.0f}"

        st.markdown(f"""
        <div class="metric-card green">
            <div class="label">Shares to Buy</div>
            <div class="value">{shares:,}</div>
            <div class="sub">Position value: {pos_display} ({result['pos_pct_nav']:.1f}% NAV)</div>
        </div>""", unsafe_allow_html=True)

        st.markdown(f"""
        <div class="metric-card red">
            <div class="label">Risk Budget Used</div>
            <div class="value">${result['risk_usd']:,.0f}</div>
            <div class="sub">{risk_pct:.2f}% of ${nav/1e6:.2f}M NAV = {result['heat']:.2f}% heat added</div>
        </div>""", unsafe_allow_html=True)

    with out_m:
        st.markdown("**Take-Profit Levels**")
        tp_html = '<div class="tp-row">'
        for tp in result["tp_levels"]:
            tp_html += f"""
            <div class="tp-chip">
                <div class="r">R{tp['r']:.0f}×</div>
                <div class="price">${tp['price']:,.4g}</div>
                <div class="pct">+{tp['pct']:.1f}%</div>
            </div>"""
        tp_html += "</div>"
        st.markdown(tp_html, unsafe_allow_html=True)

        st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

        # Sector check
        if result["sector_breach"]:
            st.error(f"⛔ **Sector cap breach**: {result['sector_after']:.1f}% NAV after trade (§7.2 limit: 25%)")
        else:
            pct_of_cap = result['sector_after'] / 25 * 100
            st.markdown(f"""
            <div class="metric-card" style="border-color: {'#F39C1233' if pct_of_cap > 75 else '#2A2D3A'}">
                <div class="label">Sector Exposure After Trade</div>
                <div class="value" style="font-size:1.2rem">{result['sector_after']:.1f}%</div>
                <div class="sub">{pct_of_cap:.0f}% of §7.2 cap (25% NAV)</div>
            </div>""", unsafe_allow_html=True)
            _progress_bar(result['sector_after'] / 25, "#F39C12" if pct_of_cap > 75 else "#2ECC71")

        # Heat check vs portfolio
        st.markdown(f"""
        <div class="metric-card" style="margin-top:0.5rem">
            <div class="label">Position Heat (% NAV at risk)</div>
            <div class="value" style="font-size:1.2rem">{result['heat']:.2f}%</div>
            <div class="sub">§7.1: max 2% per position · {('✅ OK' if result['heat'] <= 2.0 else '⚠️ Exceeds 2% limit')}</div>
        </div>""", unsafe_allow_html=True)

    with out_r:
        st.markdown("**Sizing Breakdown**")
        breakdown_data = {
            "Factor": [
                "Entry Price", "Stop Distance (ATR-based)", "ATR(14)",
                "Base Multiplier", "Vol Regime", "Conviction Mult",
                "Quality Mult", "Tier Mult", "Risk / Share",
                "Risk Budget (USD)", "Shares", "Position Value",
            ],
            "Value": [
                f"${entry_price:,.4g}",
                f"${result['stop_dist']:,.4g} ({result['stop_dist']/entry_price*100:.1f}%)",
                f"${d['atr14']:,.4g} ({d['atr_pct']:.1f}% of price)",
                f"{result['base_mult']}× ({pos_type})",
                f"{result['vr_mult']}× — {result['vr_label'].split(' (')[0]}",
                f"{result['conv_mult']}× (score {conviction_score}/100)",
                f"{result['qual_mult']}× (score {quality_score}/100)",
                f"{result['tier_mult']}× ({tier})",
                f"${result['risk_per_share']:,.4g}",
                f"${result['risk_usd']:,.0f} ({risk_pct:.2f}% NAV)",
                f"{shares:,}" + (" ✦ stress-adjusted" if stress_mode else ""),
                f"${result['pos_value']:,.0f} ({result['pos_pct_nav']:.1f}% NAV)",
            ],
        }
        df_bd = pd.DataFrame(breakdown_data)
        st.dataframe(df_bd, use_container_width=True, hide_index=True,
                     column_config={"Factor": st.column_config.TextColumn(width="medium"),
                                    "Value":  st.column_config.TextColumn(width="medium")})

    # ── ⑤ How-To Quick Reference ──────────────────────────────────────────────
    with st.expander("📖 How to use this tool"):
        st.markdown("""
**Step-by-step workflow:**

1. **Enter API key** in the sidebar (alphavantage.co — free key, 25 req/day)
2. **Set Fund NAV** (your current AUM in USD)
3. **Type a ticker** and click ⚡ Fetch — market data fills in automatically
   - Equities: `AAPL`, `MSFT`, `HD`, `PLTR`, `CSG1`
   - FX pairs: `EURUSD`, `GBPUSD`, `USDJPY`
4. **Score conviction & quality** — sliders auto-suggest position type
5. **Set entry price** — defaults to last close, override with your planned fill
6. **Set thesis floor** — the price that invalidates your thesis (hard stop anchor)
7. **Read the output** — shares, stop price, TP levels, and sector/heat checks

**What's auto-calculated:**
- **Dynamic Stop-Loss** = Entry − (Base × ATR × Vol_Regime × Conviction × Quality × Tier) — §9.1
- **Tier** = auto-classified from mkt cap / exchange / 60d ADV — §6.2
- **Position Type** = inferred from conviction + quality scores — §4.3
- **Vol Regime** = current ATR% ÷ 90-day avg ATR% (detects expanded/compressed vol)

**Key limits (AIFM Strategy):**
- §7.1 Max 2% NAV at risk per position
- §7.2 Max 25% NAV per sector
- §9.1 Stop cap at 5× ATR
        """)


# ── UI HELPERS ────────────────────────────────────────────────────────────────

def _progress_bar(fraction: float, color: str = "#E8B84B"):
    pct = min(max(fraction * 100, 0), 100)
    st.markdown(f"""
    <div class="heat-bar-wrap">
        <div class="heat-bar" style="width:{pct:.1f}%;background:{color}"></div>
    </div>""", unsafe_allow_html=True)


def _render_empty_state():
    st.markdown("""
    <div style="text-align:center;padding:4rem 2rem;color:#555">
        <div style="font-size:3rem;margin-bottom:1rem">📐</div>
        <div style="font-size:1.1rem;color:#888;margin-bottom:0.5rem">Enter a ticker and click <b style="color:#E8B84B">⚡ Fetch</b> to begin sizing</div>
        <div style="font-size:0.8rem;color:#555">
        Equities: AAPL · MSFT · HD · PLTR · CSG1 &nbsp;|&nbsp; FX: EURUSD · GBPUSD · USDJPY
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── ENTRY ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
