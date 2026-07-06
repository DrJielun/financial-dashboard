import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# --- 1. CONFIGURATION & APP INITIALIZATION ---
st.set_page_config(layout="wide", page_title="Institutional Quant Terminal")
st.title("⚡ Institutional Quant Terminal")

# --- WATCHLIST & TICKER MANAGEMENT ---
st.sidebar.header("Navigation & Watchlist")
watchlist = ["AAPL", "MSFT", "NVDA", "GOOG", "META", "AMZN"]
selected_watch = st.sidebar.selectbox("Quick Select Watchlist:", [""] + watchlist)

default_ticker = selected_watch if selected_watch else "AAPL"
ticker_symbol = st.sidebar.text_input("Manual Ticker Input:", value=default_ticker).upper().strip()

# --- TIMEFRAME SUPPORT CONTROLS ---
timeframe_opts = {
    "1 Month": {"period": "1mo"},
    "3 Months": {"period": "3mo"},
    "6 Months": {"period": "6mo"},
    "1 Year": {"period": "1y"},
    "2 Years": {"period": "2y"},
    "5 Years": {"period": "5y"}
}
selected_tf = st.sidebar.selectbox("Terminal Analysis Horizon:", list(timeframe_opts.keys()), index=3)
period_val = timeframe_opts[selected_tf]["period"]

benchmark_sym = st.sidebar.selectbox("Relative Strength Benchmark:", ["SPY", "QQQ", "XLK"], index=0)

# --- AUTO-REFRESH CONFIGURATION ---
refresh_rate = st.sidebar.slider("Live Data Auto-Refresh (Seconds):", min_value=10, max_value=60, value=15)
st.components.v1.html(
    f"""
    <script>
        window.setTimeout(function() {{
            window.location.reload();
        }}, {refresh_rate * 1000});
    </script>
    """,
    height=0,
)

if not ticker_symbol.isalnum():
    st.sidebar.warning("⚠️ Invalid ticker format detected.")
    st.stop()

# --- DATA INFRASTRUCTURE CACHING ---
@st.cache_data(ttl=86400, max_entries=100)
def fetch_ticker_info_blob(ticker_str):
    try: return yf.Ticker(ticker_str).info
    except Exception: return {}

@st.cache_data(ttl=3600)
def fetch_longlived_metadata(ticker_str):
    payload = {
        "longName": ticker_str, "targetPrice": None, "pe_trailing": None, "pe_forward": None, 
        "peg": None, "pb": None, "roe": None, "net_margin": None, "op_margin": None,
        "eps_growth": None, "rev_growth": None, "debt_equity": None, "current_ratio": None,
        "marketCap": None, "beta": None, "avg_volume": None, "fiftyTwoWeekHigh": None,
        "fiftyTwoWeekLow": None, "dividendYield": None, "sharesOutstanding": None,
        "floatShares": None, "shortInterest": None, "next_earnings": "N/A"
    }
    try:
        t = yf.Ticker(ticker_str)
        payload["longName"] = t.fast_info.get("shortName", ticker_str)
        info = fetch_ticker_info_blob(ticker_str)
        if info:
            payload.update({k: info.get(v) for k, v in [
                ("targetPrice", "targetMeanPrice"), ("pe_trailing", "trailingPE"), 
                ("pe_forward", "forwardPE"), ("peg", "pegRatio"), ("pb", "priceToBook"),
                ("roe", "returnOnEquity"), ("net_margin", "profitMargins"), 
                ("op_margin", "operatingMargins"), ("eps_growth", "earningsGrowth"), 
                ("rev_growth", "revenueGrowth"), ("debt_equity", "debtToEquity"), 
                ("current_ratio", "currentRatio"), ("marketCap", "marketCap"), 
                ("beta", "beta"), ("avg_volume", "averageVolume"), 
                ("fiftyTwoWeekHigh", "fiftyTwoWeekHigh"), ("fiftyTwoWeekLow", "fiftyTwoWeekLow"), 
                ("dividendYield", "dividendYield"), ("sharesOutstanding", "sharesOutstanding"), 
                ("floatShares", "floatShares"), ("shortInterest", "shortPercentOfFloat")
            ]})
        calendar = getattr(t, "calendar", None)
        if calendar is not None and not calendar.empty and "Earnings Date" in calendar.index:
            payload["next_earnings"] = str(calendar.loc["Earnings Date"].iloc[0].date())
    except Exception: pass
    return payload

@st.cache_data(ttl=60, max_entries=50)
def get_raw_market_data(ticker_str, benchmark_str, period_str):
    try:
        stock = yf.Ticker(ticker_str)
        history = stock.history(period=period_str, interval="1d")
        if history.empty: return None, None, None
        bench_hist = yf.Ticker(benchmark_str).history(period=period_str, interval="1d")
        fast_payload = {"prev_close": history['Close'].tail(2).iloc[0] if len(history) > 1 else history['Close'].iloc[-1]}
        return history, bench_hist, fast_payload
    except Exception: return None, None, None

@st.cache_data(ttl=30)
def compute_technical_indicators(df_history, df_bench):
    df = df_history.copy()
    df['MA20'] = df['Close'].rolling(window=min(20, len(df))).mean()
    df['Std20'] = df['Close'].rolling(window=min(20, len(df))).std()
    df['BB_Upper'], df['BB_Lower'] = df['MA20'] + (2 * df['Std20']), df['MA20'] - (2 * df['Std20'])
    df['Vol_Bandwidth'] = (df['BB_Upper'] - df['BB_Lower']) / df['MA20'].replace(0, np.nan)
    df['BB_Squeeze'] = df['Vol_Bandwidth'] < df['Vol_Bandwidth'].rolling(window=min(126, len(df)), min_periods=1).quantile(0.20)
    
    delta = df['Close'].diff()
    gain, loss = delta.clip(lower=0), -delta.clip(upper=0)
    avg_gain, avg_loss = gain.ewm(alpha=1/14, adjust=False).mean(), loss.ewm(alpha=1/14, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + (avg_gain / avg_loss.replace(0, np.nan))))
    
    df['MACD'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    tr = pd.concat([df['High'] - df['Low'], abs(df['High'] - df['Close'].shift(1)), abs(df['Low'] - df['Close'].shift(1))], axis=1).max(axis=1)
    df['ATR'] = tr.ewm(alpha=1/14, adjust=False).mean()
    df['PlusDI'] = 100 * (pd.Series(np.where((df['High'] - df['High'].shift(1) > df['Low'].shift(1) - df['Low']) & (df['High'] - df['High'].shift(1) > 0), df['High'] - df['High'].shift(1), 0.0), index=df.index).ewm(alpha=1/14, adjust=False).mean() / df['ATR'].replace(0, np.nan))
    df['MinusDI'] = 100 * (pd.Series(np.where((df['Low'].shift(1) - df['Low'] > df['High'] - df['High'].shift(1)) & (df['Low'].shift(1) - df['Low'] > 0), df['Low'].shift(1) - df['Low'], 0.0), index=df.index).ewm(alpha=1/14, adjust=False).mean() / df['ATR'].replace(0, np.nan))
    df['ADX'] = ((abs(df['PlusDI'] - df['MinusDI']) / (df['PlusDI'] + df['MinusDI']).replace(0, np.nan)) * 100).ewm(alpha=1/14, adjust=False).mean()
    df['RVOL'] = df['Volume'] / df['Volume'].rolling(window=min(20, len(df))).mean().replace(0, np.nan)
    df['Alpha_Strength'] = (1 + df['Close'].pct_change()).cumprod() - (1 + df_bench['Close'].pct_change().reindex(df.index, method='ffill')).cumprod()
    return df

# --- LAYOUT ENGINE ---
with st.spinner("Processing..."):
    raw_history, bench_history, info_payload = get_raw_market_data(ticker_symbol, benchmark_sym, period_val)

if raw_history is not None and info_payload is not None:
    fnd = fetch_longlived_metadata(ticker_symbol)
    df_view = compute_technical_indicators(raw_history, bench_history)
    latest = df_view.iloc[-1]
    
    main_col, side_col = st.columns([2.3, 0.7])
    with main_col:
        st.subheader(f"🏢 {fnd['longName']} ({ticker_symbol})")
        # Header Metrics
        h1, h2, h3, h4 = st.columns(4)
        h1.metric("Close", f"${latest['Close']:,.2f}", f"{((latest['Close'] - info_payload['prev_close']) / info_payload['prev_close'])*100:+.2f}%")
        h2.metric("RVOL", f"{latest['RVOL']:.2f}x")
        h3.metric("52W Pos", f"{((latest['Close'] - (fnd['fiftyTwoWeekLow'] or 0)) / ((fnd['fiftyTwoWeekHigh'] or 1) - (fnd['fiftyTwoWeekLow'] or 0)))*100:.1f}%")
        h4.metric("Alpha", f"{latest['Alpha_Strength']*100:+.2f}%")
        
        # Plotting
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.5, 0.25, 0.25])
        fig.add_trace(go.Candlestick(x=df_view.index, open=df_view['Open'], high=df_view['High'], low=df_view['Low'], close=df_view['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Bar(x=df_view.index, y=df_view['Volume'], name='Volume', marker_color='rgba(33, 150, 243, 0.3)'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['ADX'], name='ADX', line=dict(color='#FF9100')), row=3, col=1)
        fig.update_layout(height=650, template="plotly_dark", margin=dict(l=20, r=20, t=10, b=10), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with side_col:
        st.markdown("### 📋 Quant Fundamentals")
        def fmt(v, f=""): return "N/A" if pd.isna(v) else (f"${v/1e9:.2f}B" if f=="mcap" else (f"{v*100:.2f}%" if f=="pct" else f"{v:.2f}"))
        st.markdown(f"**Market Cap:** `{fmt(fnd['marketCap'], 'mcap')}`")
        st.markdown(f"**P/E (Trailing):** `{fmt(fnd['pe_trailing'])}`")
        st.markdown(f"**ROE:** `{fmt(fnd['roe'], 'pct')}`")
        st.markdown(f"**Debt/Equity:** `{fmt(fnd['debt_equity'])}`")
        st.markdown(f"**Next Earnings:** `{fnd['next_earnings']}`")
else:
    st.error("❌ Data parse error.")
