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

# --- INFRASTRUCTURE CACHING ---
@st.cache_data(ttl=86400, max_entries=100)
def fetch_ticker_info_blob(ticker_str):
    try:
        return yf.Ticker(ticker_str).info
    except Exception:
        return {}

@st.cache_data(ttl=3600)
def fetch_longlived_metadata(ticker_str):
    payload = {
        "longName": ticker_str, "pe_trailing": None, "pe_forward": None, 
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

@st.cache_data(ttl=60, max_entries=50)
def get_raw_market_data(ticker_str, benchmark_str, period_str):
    try:
        stock = yf.Ticker(ticker_str)
        history = stock.history(period=period_str, interval="1d")
        if history.empty: return None, None, None
            
        bench = yf.Ticker(benchmark_str)
        bench_hist = bench.history(period=period_str, interval="1d")
        
        fast_payload = {"prev_close": history['Close'].tail(2).iloc[0] if len(history) > 1 else history['Close'].iloc[-1]}
        return history, bench_hist, fast_payload
    except Exception:
        return None, None, None

@st.cache_data(ttl=30)
def compute_technical_indicators(df_history, df_bench):
    df = df_history.copy()
    df['SMA50'] = df['Close'].rolling(window=min(50, len(df))).mean()
    df['SMA200'] = df['Close'].rolling(window=min(200, len(df))).mean()
    df['MA20'] = df['Close'].rolling(window=min(20, len(df))).mean()
    df['Std20'] = df['Close'].rolling(window=min(20, len(df))).std()
    df['BB_Upper'] = df['MA20'] + (2 * df['Std20'])
    df['BB_Lower'] = df['MA20'] - (2 * df['Std20'])
    df['Vol_Bandwidth'] = np.where(df['MA20'] > 0, (df['BB_Upper'] - df['BB_Lower']) / df['MA20'], np.nan)
    
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
    tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
    df['ATR'] = tr.ewm(alpha=1/14, adjust=False).mean()
    
    plus_dm = np.where(((high - high.shift(1)) > (low.shift(1) - low)) & ((high - high.shift(1)) > 0), high - high.shift(1), 0.0)
    minus_dm = np.where(((low.shift(1) - low) > (high - high.shift(1))) & ((low.shift(1) - low) > 0), low.shift(1) - low, 0.0)
    df['PlusDI'] = 100 * (pd.Series(plus_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() / df['ATR'].replace(0, np.nan))
    df['MinusDI'] = 100 * (pd.Series(minus_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() / df['ATR'].replace(0, np.nan))
    df['ADX'] = ((abs(df['PlusDI'] - df['MinusDI']) / (df['PlusDI'] + df['MinusDI']).replace(0, np.nan)) * 100).ewm(alpha=1/14, adjust=False).mean()
    
    df['RVOL'] = df['Volume'] / df['Volume'].rolling(window=min(20, len(df))).mean().replace(0, np.nan)
    return df

# --- RENDERING ENGINE ---
with st.spinner("Processing algorithms..."):
    raw_history, bench_history, info_payload = get_raw_market_data(ticker_symbol, benchmark_sym, period_val)

if raw_history is not None and info_payload is not None:
    fnd = fetch_longlived_metadata(ticker_symbol)
    df_view = compute_technical_indicators(raw_history, bench_history)
    latest = df_view.iloc[-1]
    
    latest_close = latest['Close']
    prev_close = info_payload['prev_close']
    price_change = latest_close - prev_close
    pct_change = (price_change / prev_close) * 100
    
    atr_val = latest['ATR']
    suggested_stop = latest_close - (atr_val * 2)
    risk_pct = ((latest_close - suggested_stop) / latest_close) * 100

    main_layout, fundamental_sidebar = st.columns([2.3, 0.7])
    
    with main_layout:
        st.subheader(f"🏢 {fnd['longName']} ({ticker_symbol}) — Institutional Terminal")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Close", f"${latest_close:,.2f}", f"{pct_change:+.2f}%")
        c2.metric("ATR (14)", f"{atr_val:.2f}")
        c3.metric("Suggested Stop", f"${suggested_stop:.2f}")
        c4.metric("Risk Exposure", f"{risk_pct:.1f}%")

        fig = make_subplots(
            rows=5, cols=1, shared_xaxes=True, vertical_spacing=0.03, 
            row_heights=[0.40, 0.15, 0.15, 0.15, 0.15]
        )
        fig.add_trace(go.Candlestick(x=df_view.index, open=df_view['Open'], high=df_view['High'], low=df_view['Low'], close=df_view['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Bar(x=df_view.index, y=df_view['Volume'], name='Volume', marker_color='rgba(100, 100, 100, 0.5)'), row=2, col=1)
        
        colors = ['red' if val < 0 else 'green' for val in df_view['MACD_Hist']]
        fig.add_trace(go.Bar(x=df_view.index, y=df_view['MACD_Hist'], name='MACD Hist', marker_color=colors), row=3, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['MACD'], name='MACD', line=dict(color='#29B6F6', width=1.5)), row=3, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['MACD_Signal'], name='Signal', line=dict(color='#AB47BC', width=1.2)), row=3, col=1)
        
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['ADX'], name='ADX', line=dict(color='#FF9100', width=2)), row=4, col=1)
        
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['RSI'], name='RSI', line=dict(color='#E040FB', width=1.5)), row=5, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=5, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=5, col=1)

        fig.update_layout(height=900, template="plotly_dark", hovermode="x unified", showlegend=False, xaxis=dict(rangeslider=dict(visible=False)))
        st.plotly_chart(fig, use_container_width=True)

    with fundamental_sidebar:
        st.markdown("### 📋 Quant Fundamentals")
        def fmt(v, f="num"):
            if pd.isna(v): return "N/A"
            if f == "pct": return f"{v * 100:.2f}%"
            if f == "mcap": return f"${v / 1e12:.2f}T" if v >= 1e12 else f"${v / 1e9:.2f}B"
            return f"{v:.2f}"
            
        st.markdown(f"**Market Cap:** `{fmt(fnd['marketCap'], 'mcap')}`")
        st.markdown(f"**Trailing P/E:** `{fmt(fnd['pe_trailing'])}`")
        st.markdown(f"**ROE:** `{fmt(fnd['roe'], 'pct')}`")
        st.markdown(f"**Debt/Equity:** `{fmt(fnd['debt_equity'])}`")
        st.markdown(f"**Next Earnings:** `{fnd['next_earnings']}`")

    st.caption("Terminal analysis complete.")
else:
    st.error("❌ Data error.")
