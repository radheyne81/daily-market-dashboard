import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Daily Market Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Theme / mobile-friendly layout ----------
st.markdown("""
<style>
.block-container {padding-top: 1rem; padding-bottom: 2rem; max-width: 1500px;}
[data-testid="stMetric"] {background: rgba(100,130,180,.08); padding: 12px; border-radius: 12px;}
h1, h2, h3 {letter-spacing: -.02em;}
.small-muted {font-size:.85rem; opacity:.75;}
</style>
""", unsafe_allow_html=True)

st.title("📈 Daily Market Dashboard")
st.caption("Market intelligence • Technical indicators • Screening • Correlations")
st.warning(
    "Educational market analytics only. Data from Yahoo Finance may be delayed, incomplete, "
    "or unavailable. This is not investment advice."
)

IST = ZoneInfo("Asia/Kolkata")
now_ist = datetime.now(IST)
st.caption(f"Portal time: {now_ist:%d %b %Y, %I:%M:%S %p} IST")

# Optional shared access code. Leave blank in secrets for an open portal.
access_code = ""
try:
    access_code = st.secrets.get("PORTAL_ACCESS_CODE", "")
except Exception:
    access_code = os.getenv("PORTAL_ACCESS_CODE", "")

if access_code:
    entered = st.sidebar.text_input("Portal access code", type="password")
    if entered != access_code:
        st.info("Enter the access code in the sidebar to view the dashboard.")
        st.stop()

st.sidebar.header("Dashboard")
page = st.sidebar.radio(
    "Choose a view",
    ["Overview", "Market Breadth", "HA Screener", "Index Technicals", "Correlation Matrix"],
)
period = st.sidebar.selectbox("History window", ["6mo", "1y", "2y"], index=1)
if st.sidebar.button("Refresh data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

@st.cache_data(ttl=300, show_spinner=False)
def get_history(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    df = yf.download(symbol, period=period, interval=interval, auto_adjust=False, progress=False, threads=False)
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna(how="all")

@st.cache_data(ttl=1800, show_spinner=False)
def get_nifty200_symbols():
    url = "https://archives.nseindia.com/content/indices/ind_nifty200list.csv"
    try:
        df = pd.read_csv(url, storage_options={"User-Agent": "Mozilla/5.0"})
        return [str(s).strip() + ".NS" for s in df["Symbol"].dropna().tolist()]
    except Exception:
        return []

def add_rsi(df, period=14):
    out = df.copy()
    delta = out["Close"].diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    roll_down = down.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = roll_up / roll_down.replace(0, float("nan"))
    out["RSI_14"] = 100 - (100 / (1 + rs))
    out["RSI_14"] = out["RSI_14"].fillna(50)
    return out

def add_heikin_ashi(df):
    out = df.copy()
    out["HA_Close"] = (out["Open"] + out["High"] + out["Low"] + out["Close"]) / 4
    ha_open = [((out["Open"].iloc[0] + out["Close"].iloc[0]) / 2)]
    for i in range(1, len(out)):
        ha_open.append((ha_open[i-1] + out["HA_Close"].iloc[i-1]) / 2)
    out["HA_Open"] = ha_open
    out["Green_HA"] = out["HA_Close"] > out["HA_Open"]
    return out

def pattern_tags(df):
    out = df.copy()
    o,h,l,c = out["Open"],out["High"],out["Low"],out["Close"]
    o1,c1,o2,c2 = o.shift(1),c.shift(1),o.shift(2),c.shift(2)
    engulf = (c1 < o1) & (c > o) & (o <= c1) & (c >= o1) & ((c-o) > (o1-c1))
    piercing = (c1 < o1) & (c > o) & (o < l.shift(1)) & (c > (o1+c1)/2) & (c < o1)
    star = (c2 < o2) & ((c1-o1).abs() < (c2-o2).abs()*0.3) & (c > o) & (c > (o2+c2)/2)
    out["Pattern"] = "None"
    out.loc[engulf, "Pattern"] = "Bullish Engulfing"
    out.loc[piercing, "Pattern"] = "Piercing Line"
    out.loc[star, "Pattern"] = "Morning Star"
    return out

def latest_price(symbol):
    d = get_history(symbol, "5d", "1d")
    if d.empty or len(d) < 2:
        return None
    current = float(d["Close"].iloc[-1])
    prev = float(d["Close"].iloc[-2])
    return {"price": current, "change": (current-prev)/prev*100 if prev else 0.0}

def macd_signal(df):
    close = df["Close"]
    if len(close) < 35:
        return "Insufficient data"
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    signal = macd.ewm(span=9, adjust=False).mean()
    return "Bullish ↗" if macd.iloc[-1] > signal.iloc[-1] else "Bearish ↘"

def ema_signal(df, span=20):
    if len(df) < span:
        return "Insufficient data"
    ema = df["Close"].ewm(span=span, adjust=False).mean()
    return "Bullish ↗" if df["Close"].iloc[-1] > ema.iloc[-1] else "Bearish ↘"

def styled_table(df):
    def color_cell(v):
        if isinstance(v, str) and "Bullish" in v:
            return "background-color:#d9f2df;color:#176b35;font-weight:600"
        if isinstance(v, str) and "Bearish" in v:
            return "background-color:#f9dddd;color:#9d2424;font-weight:600"
        return ""
    return df.style.map(color_cell)

if page == "Overview":
    st.subheader("Index Snapshot")
    symbols = [
        ("Nifty 50", "^NSEI"),
        ("Bank Nifty", "^NSEBANK"),
        ("India VIX", "^INDIAVIX"),
        ("Dow Jones", "^DJI"),
        ("Nasdaq", "^IXIC"),
    ]
    cols = st.columns(2 if st.session_state.get("_is_mobile", False) else 3)
    for i, (name, symbol) in enumerate(symbols):
        with cols[i % len(cols)]:
            try:
                info = latest_price(symbol)
                if info:
                    st.metric(name, f'{info["price"]:,.2f}', f'{info["change"]:+.2f}%')
                else:
                    st.metric(name, "Unavailable")
            except Exception:
                st.metric(name, "Unavailable")
    st.subheader("Quick technical view")
    rows = []
    for name, symbol in [("Nifty 50", "^NSEI"), ("Bank Nifty", "^NSEBANK")]:
        try:
            d = get_history(symbol, "6mo", "1d")
            if d.empty:
                continue
            d = add_rsi(d)
            rows.append({
                "Index": name,
                "Latest Close": round(float(d["Close"].iloc[-1]), 2),
                "MACD": macd_signal(d),
                "Price vs 20 EMA": ema_signal(d),
                "RSI (14)": round(float(d["RSI_14"].iloc[-1]), 1),
            })
        except Exception:
            pass
    if rows:
        st.dataframe(styled_table(pd.DataFrame(rows)), use_container_width=True, hide_index=True)
    st.info("Use the left menu to open each analysis module. Data refreshes automatically every 5 minutes while the app is active.")

elif page == "Market Breadth":
    st.subheader("Market Breadth")
    st.caption("Constituent-level breadth is calculated from available Yahoo Finance daily closes.")
    groups = {
        "Nifty 50": "https://archives.nseindia.com/content/indices/ind_nifty50list.csv",
        "Nifty 100": "https://archives.nseindia.com/content/indices/ind_nifty100list.csv",
        "Nifty 200": "https://archives.nseindia.com/content/indices/ind_nifty200list.csv",
        "Nifty Bank": "https://archives.nseindia.com/content/indices/ind_niftybanklist.csv",
    }
    rows = []
    with st.spinner("Downloading constituent lists and price history…"):
        for name, url in groups.items():
            try:
                listing = pd.read_csv(url, storage_options={"User-Agent": "Mozilla/5.0"})
                tickers = [str(x).strip()+".NS" for x in listing["Symbol"].dropna()]
                closes = yf.download(tickers, period="1y", interval="1d", progress=False, group_by="column", threads=True)["Close"]
                if isinstance(closes, pd.Series):
                    closes = closes.to_frame()
                closes = closes.dropna(axis=1, how="all")
                if closes.empty or len(closes) < 2:
                    continue
                curr, prev = closes.iloc[-1], closes.iloc[-2]
                adv, dec = int((curr > prev).sum()), int((curr < prev).sum())
                ema50 = closes.ewm(span=50, adjust=False).mean().iloc[-1]
                ema200 = closes.ewm(span=200, adjust=False).mean().iloc[-1]
                valid = curr.dropna().index
                n = len(valid)
                rows.append({
                    "Index": name,
                    "Advance": adv,
                    "Decline": dec,
                    "A/D Ratio": round(adv/dec, 2) if dec else None,
                    "% Above 50 EMA": round((curr.loc[valid] > ema50.loc[valid]).mean()*100, 1),
                    "% Above 200 EMA": round((curr.loc[valid] > ema200.loc[valid]).mean()*100, 1),
                })
            except Exception as e:
                st.caption(f"{name}: data unavailable ({type(e).__name__})")
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.markdown("#### Expert Logic & Interpretation")
    st.success("Bullish context: A/D ratio above 1 and a majority of constituents above their moving averages suggest broad participation.")
    st.error("Bearish context: A/D ratio below 1 and fewer than half of constituents above their moving averages suggest weak breadth.")
    st.caption("These are contextual signals, not standalone buy/sell instructions.")

elif page == "HA Screener":
    st.subheader("Nifty 200 Heikin Ashi Screener")
    timeframe = st.selectbox("Timeframe", ["1D", "1H", "1W"])
    max_stocks = st.slider("Maximum stocks to scan (limits data usage)", 20, 200, 50, 10)
    rsi_limit = st.slider("RSI threshold", 20, 45, 35)
    params = {"1D": ("1d", "6mo"), "1H": ("1h", "1mo"), "1W": ("1wk", "2y")}[timeframe]
    symbols = get_nifty200_symbols()
    if not symbols:
        st.error("Could not load the Nifty 200 constituent list. Please retry later.")
    else:
        symbols = symbols[:max_stocks]
        results = []
        progress = st.progress(0)
        with st.spinner(f"Scanning {len(symbols)} stocks…"):
            for i, symbol in enumerate(symbols):
                try:
                    d = get_history(symbol, params[1], params[0])
                    if len(d) >= 15:
                        d = pattern_tags(add_heikin_ashi(add_rsi(d)))
                        last = d.iloc[-1]
                        if bool(last["Green_HA"]) and float(last["RSI_14"]) < rsi_limit:
                            results.append({
                                "Stock": symbol.replace(".NS", ""),
                                "Timeframe": timeframe,
                                "Latest Close": round(float(last["Close"]), 2),
                                "RSI (14)": round(float(last["RSI_14"]), 2),
                                "Pattern": str(last["Pattern"]),
                            })
                except Exception:
                    pass
                progress.progress((i+1)/len(symbols))
        if results:
            result_df = pd.DataFrame(results).sort_values("RSI (14)")
            st.dataframe(result_df, use_container_width=True, hide_index=True)
            st.download_button("Download screener CSV", result_df.to_csv(index=False), "ha_screener.csv", "text/csv")
        else:
            st.info("No matching stocks found in this scan, or data was unavailable.")
    st.markdown("#### Expert Logic & Interpretation")
    st.write(f"Filter: green Heikin Ashi candle with RSI below {rsi_limit}. This can flag a possible rebound after weakness, but may also occur in a continuing downtrend.")
    st.caption("The default scan is capped at 50 stocks to reduce free-tier timeouts. Increase the limit if the app has enough runtime.")

elif page == "Index Technicals":
    st.subheader("Index Technicals")
    rows = []
    for name, symbol in [("NIFTY 50", "^NSEI"), ("NIFTY BANK", "^NSEBANK")]:
        with st.spinner(f"Loading {name}…"):
            d = get_history(symbol, period, "1d")
            h = get_history(symbol, "1mo", "1h")
        if not d.empty:
            d = add_rsi(d)
            rows.append({
                "Metric": name,
                "Close": round(float(d["Close"].iloc[-1]), 2),
                "MACD 1D": macd_signal(d),
                "EMA 1D (20)": ema_signal(d),
                "RSI 1D": round(float(d["RSI_14"].iloc[-1]), 1),
                "MACD 1H": macd_signal(h) if not h.empty else "Unavailable",
                "EMA 1H (20)": ema_signal(h) if not h.empty else "Unavailable",
            })
    if rows:
        st.dataframe(styled_table(pd.DataFrame(rows)), use_container_width=True, hide_index=True)
    vix = get_history("^INDIAVIX", "5d", "1d")
    if not vix.empty:
        latest_vix = float(vix["Close"].iloc[-1])
        st.metric("India VIX", f"{latest_vix:.2f}", help="Volatility index; interpret with its recent trend and market context.")
    st.markdown("#### Expert Logic & Interpretation")
    st.write("- **EMA:** Price above the 20 EMA suggests a positive short-term trend; below suggests weakness.")
    st.write("- **MACD:** MACD above its signal line suggests positive momentum; below suggests negative momentum.")
    st.write("- **RSI:** A momentum oscillator, not a prediction. Extreme values can persist in strong trends.")
    st.write("- **VIX:** Higher readings generally indicate higher expected volatility, not necessarily market direction.")

elif page == "Correlation Matrix":
    st.subheader("Cross-Asset Correlation Matrix")
    assets = {
        "Nifty 50": "^NSEI",
        "Gold": "GC=F",
        "USOIL": "CL=F",
        "USD/INR": "INR=X",
        "Bitcoin": "BTC-USD",
        "S&P 500": "^GSPC",
    }
    with st.spinner("Calculating correlations from daily returns…"):
        data = yf.download(list(assets.values()), period=period, interval="1d", progress=False, threads=True)
        if not data.empty and "Close" in data:
            close = data["Close"]
            if isinstance(close, pd.Series):
                close = close.to_frame()
            close = close.rename(columns={v:k for k,v in assets.items()})
            ordered = [name for name in assets if name in close.columns]
            returns = close[ordered].pct_change().dropna(how="all")
            corr = returns.corr().round(2)
            def corr_style(v):
                if pd.isna(v):
                    return ""
                if abs(v-1.0) < 1e-8:
                    return "background-color:#d9d3f5;color:#4b3294;font-weight:bold"
                if v > 0.1:
                    return "background-color:#d9f2df;color:#176b35"
                if v < -0.1:
                    return "background-color:#f9dddd;color:#9d2424"
                return ""
            st.dataframe(corr.style.map(corr_style).format("{:.2f}"), use_container_width=True)
            st.download_button("Download correlation CSV", corr.to_csv(), "correlation_matrix.csv", "text/csv")
        else:
            st.error("Correlation data is temporarily unavailable. Please retry.")
    st.markdown("#### Expert Logic & Interpretation")
    st.write("- **+1.00:** Assets moved together over the selected sample; it does not mean one causes the other.")
    st.write("- **Near 0:** Little linear relationship over the selected period.")
    st.write("- **Negative:** Assets tended to move in opposite directions over the selected period.")
    st.caption("Correlations change over time. Interpret them using the chosen history window and market context.")

st.divider()
st.caption("Daily Market Dashboard • Built with Streamlit and Python • Free-tier deployment subject to provider limits")
