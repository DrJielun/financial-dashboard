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

# --- LONGLIVED RAW DATA & INFRASTRUCTURE CACHING ---
@st.cache_data(ttl=86400, max_entries=100)
def fetch_ticker_info_blob(ticker_str):
    try:
        return yf.Ticker(ticker_str).info
    except Exception:
        return {}

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
            payload["targetPrice"] = info.get("targetMeanPrice")
            payload["pe_trailing"] = info.get("trailingPE")
            payload["pe_forward"] = info.get("forwardPE")
            payload["peg"] = info.get("pegRatio")
            payload["pb"] = info.get("priceToBook")
            payload["roe"] = info.get("returnOnEquity")
            payload["net_margin"] = info.get("profitMargins")
            payload["op_margin"] = info.get("operatingMargins")
            payload["eps_growth"] = info.get("earningsGrowth")
            payload["rev_growth"] = info.get("revenueGrowth")
            payload["debt_equity"] = info.get("debtToEquity")
            payload["current_ratio"] = info.get("currentRatio")
            payload["marketCap"] = info.get("marketCap")
            payload["beta"] = info.get("beta")
            payload["avg_volume"] = info.get("averageVolume")
            payload["fiftyTwoWeekHigh"] = info.get("fiftyTwoWeekHigh")
            payload["fiftyTwoWeekLow"] = info.get("fiftyTwoWeekLow")
            payload["dividendYield"] = info.get("dividendYield")
            payload["sharesOutstanding"] = info.get("sharesOutstanding")
            payload["floatShares"] = info.get("floatShares")
            payload["shortInterest"] = info.get("shortPercentOfFloat")
            
        calendar = getattr(t, "calendar", None)
        if calendar is not None and not calendar.empty and "Earnings Date" in calendar.index:
            payload["next_earnings"] = str(calendar.loc["Earnings Date"].iloc[0].date())
    except Exception:
        pass
    return payload

# --- LAYER 1: DATA INGESTION ---
@st.cache_data(ttl=60, max_entries=50)
def get_raw_market_data(ticker_str, benchmark_str, period_str):
    try:
        stock = yf.Ticker(ticker_str)
        history = stock.history(period=period_str, interval="1d")
        if history.empty:
            return None, None, None
            
        bench = yf.Ticker(benchmark_str)
        bench_hist = bench.history(period=period_str, interval="1d")
        
        fast_payload = {
            "prev_close": history['Close'].tail(2).iloc[0] if len(history) > 1 else history['Close'].iloc[-1]
        }
        return history, bench_hist, fast_payload
    except Exception:
        return None, None, None

# --- LAYER 2: INSTITUTIONAL QUANT ENGINE ---
@st.cache_data(ttl=30)
def compute_technical_indicators(df_history, df_bench):
    df = df_history.copy()
    
    df['SMA50'] = df['Close'].rolling(window=min(50, len(df))).mean()
    df['SMA200'] = df['Close'].rolling(window=min(200, len(df))).mean()
    df['MA20'] = df['Close'].rolling(window=min(20, len(df))).mean()
    df['Std20'] = df['Close'].rolling(window=min(20, len(df))).std()
    
    delta = df['Close'].diff()
    gain, loss = delta.clip(lower=0), -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + (avg_gain / avg_loss.replace(0, np.nan))))
    
    df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    
    high, low, close = df['High'], df['Low'], df['Close']
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)

    df['ATR'] = tr.ewm(alpha=1/14, adjust=False).mean()
    df['PlusDI'] = 100 * (pd.Series(plus_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() / df['ATR'].replace(0, np.nan))
    df['MinusDI'] = 100 * (pd.Series(minus_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() / df['ATR'].replace(0, np.nan))
    df['ADX'] = ((abs(df['PlusDI'] - df['MinusDI']) / (df['PlusDI'] + df['MinusDI']).replace(0, np.nan)) * 100).ewm(alpha=1/14, adjust=False).mean()
    
    df['RVOL'] = df['Volume'] / df['Volume'].rolling(window=min(20, len(df))).mean().replace(0, np.nan)
    
    stock_ret = (1 + df['Close'].pct_change()).cumprod()
    bench_ret = (1 + df_bench['Close'].pct_change().reindex(df.index, method='ffill')).cumprod()
    df['Alpha_Strength'] = stock_ret - bench_ret
    
    return df

# --- LAYER 3: LAYOUT MATRIX RENDERING ENGINE ---
with st.spinner("Executing real-time pipeline algorithms..."):
    raw_history, bench_history, info_payload = get_raw_market_data(ticker_symbol, benchmark_sym, period_val)

if raw_history is not None and info_payload is not None:
    fnd = fetch_longlived_metadata(ticker_symbol)
    df_view = compute_technical_indicators(raw_history, bench_history)
    
    latest = df_view.iloc[-1]
    sma_available = pd.notna(latest["SMA50"]) and pd.notna(latest["SMA200"])
    
    latest_close = latest['Close']
    prev_close = info_payload['prev_close']
    price_change = latest_close - prev_close
    pct_change = (price_change / prev_close) * 100 if prev_close else 0.0
    
    high_52w = fnd["fiftyTwoWeekHigh"] or df_view["High"].max()
    low_52w = fnd["fiftyTwoWeekLow"] or df_view["Low"].min()
    price_position_pct = ((latest_close - low_52w) / (high_52w - low_52w)) * 100 if high_52w != low_52w else 50.0
    
    main_layout, fundamental_sidebar = st.columns([2.3, 0.7])
    
    with main_layout:
        st.subheader(f"🏢 {fnd['longName']} ({ticker_symbol}) — Terminal View")
        col_h1, col_h2, col_h3, col_h4 = st.columns(4)
        col_h1.metric("Closing Value (USD)", f"${latest_close:,.2f}", f"${price_change:+.2f} ({pct_change:+.2f}%)")
        col_h2.metric("Relative Volume (RVOL)", f"{latest['RVOL']:.2f}x" if pd.notna(latest['RVOL']) else "N/A", "vs 20-Day Mean")
        col_h3.metric("52-Week Range Position", f"{price_position_pct:.1f}%", f"Floor: ${low_52w:.1f}")
        col_h4.metric(f"Benchmark Alpha ({benchmark_sym})", f"{latest['Alpha_Strength']*100:+.2f}%", "Geometric Delta")

        st.markdown("---")
        
        # 1. New Grid Layout: 5 rows (Price, Vol, MACD, RSI, ADX)
        fig = make_subplots(
            rows=5, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.03, 
            row_heights=[0.40, 0.15, 0.15, 0.15, 0.15]
        )
        
        # Row 1: Price
        fig.add_trace(go.Candlestick(x=df_view.index, open=df_view['Open'], high=df_view['High'], low=df_view['Low'], close=df_view['Close'], name='Price'), row=1, col=1)
        if sma_available:
            fig.add_trace(go.Scatter(x=df_view.index, y=df_view['SMA50'], name='50 SMA', line=dict(color='#FBC02D', width=1)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_view.index, y=df_view['SMA200'], name='200 SMA', line=dict(color='#D32F2F', width=1)), row=1, col=1)
        
        # Row 2: Volume
        fig.add_trace(go.Bar(x=df_view.index, y=df_view['Volume'], name='Volume', marker_color='rgba(33, 150, 243, 0.5)'), row=2, col=1)
        
        # Row 3: MACD (Lines + Histogram)
        colors = ['red' if val < 0 else 'green' for val in df_view['MACD_Hist']]
        fig.add_trace(go.Bar(x=df_view.index, y=df_view['MACD_Hist'], name='MACD Hist', marker_color=colors), row=3, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['MACD'], name='MACD', line=dict(color='#29B6F6', width=1.5)), row=3, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['MACD_Signal'], name='Signal', line=dict(color='#AB47BC', width=1.2)), row=3, col=1)
        
        # Row 4: RSI
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['RSI'], name='RSI', line=dict(color='#FFCA28', width=1.5)), row=4, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=4, col=1)
        fig.add_hline(y=50, line_dash="dot", line_color="gray", row=4, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=4, col=1)
        
        # Row 5: ADX
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['ADX'], name='ADX', line=dict(color='#FF9100', width=2)), row=5, col=1)

        fig.update_layout(
            height=900, margin=dict(l=20, r=20, t=10, b=10), template="plotly_dark",
            hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

    with fundamental_sidebar:
        st.markdown("### 📋 Quant Fundamentals")
        def fmt_v(v, f="num"):
            if v is None or pd.isna(v): return "N/A"
            if f == "pct": return f"{v * 100:.2f}%"
            if f == "mcap": return f"${v / 1e12:.2f}T" if v >= 1e12 else f"${v / 1e9:.2f}B"
            if f == "vol": return f"{v / 1e6:.2f}M"
            return f"{v:.2f}"

        st.markdown("#### **Corporate Overview**")
        st.markdown(f"**Market Cap:** `{fmt_v(fnd['marketCap'], 'mcap')}`")
        st.markdown(f"**Beta Risk Value:** `{fmt_v(fnd['beta'])}`")
        st.markdown(f"**Average Volume:** `{fmt_v(fnd['avg_volume'], 'vol')}`")
        
        # 5. ATR Display
        st.markdown("---")
        st.markdown("#### **Volatility Metrics**")
        curr_atr = latest['ATR']
        st.markdown(f"**ATR (14):** `{curr_atr:.2f}`")
        st.markdown(f"**Suggested Stop:** `${latest_close - (curr_atr * 2):.2f}`")
        st.markdown(f"**Risk Profile:** `{(curr_atr/latest_close)*100:.2f}%`")
        
        st.markdown("---")
        st.markdown("#### **Valuation Matrix**")
        st.markdown(f"**Trailing P/E:** `{fmt_v(fnd['pe_trailing'])}`")
        st.markdown(f"**Forward P/E:** `{fmt_v(fnd['pe_forward'])}`")
        st.markdown(f"**Next Expected Earnings:** `{fnd['next_earnings']}`")

    st.markdown("---")
    st.caption("Terminal analysis complete. Data refreshed and cached locally.")

else:
    st.error(f"❌ Core Data Exception: Historical records for symbol '{ticker_symbol}' could not be safely parsed.")
