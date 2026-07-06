import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# --- 1. CONFIGURATION & ENGINE INITIALIZATION ---
st.set_page_config(layout="wide", page_title="Institutional Quant Terminal")
st.title("⚡ Institutional Quant Terminal")

# --- NAVIGATION & WATCHLIST (FIX #11) ---
st.sidebar.header("Navigation & Watchlist")
watchlist = ["AAPL", "MSFT", "NVDA", "GOOG", "META", "AMZN"]
selected_watch = st.sidebar.selectbox("Quick Select Watchlist:", [""] + watchlist)
default_ticker = selected_watch if selected_watch else "AAPL"
ticker_symbol = st.sidebar.text_input("Manual Ticker Input:", value=default_ticker).upper().strip()

# --- HORIZON & BENCHMARK (FIX #6, #10) ---
timeframe_opts = {"1 Month": "1mo", "3 Months": "3mo", "6 Months": "6mo", "1 Year": "1y", "2 Years": "2y", "5 Years": "5y"}
selected_tf = st.sidebar.selectbox("Terminal Analysis Horizon:", list(timeframe_opts.keys()), index=3)
period_val = timeframe_opts[selected_tf]
benchmark_sym = st.sidebar.selectbox("Relative Strength Benchmark:", ["SPY", "QQQ", "XLK"], index=0)

# --- AUTO-REFRESH CONFIGURATION (FIX #8) ---
refresh_rate = st.sidebar.slider("Live Data Auto-Refresh (Seconds):", min_value=10, max_value=60, value=15)
st.components.v1.html(f"<script>window.setTimeout(function(){{window.location.reload();}}, {refresh_rate * 1000});</script>", height=0)

if not ticker_symbol.isalnum():
    st.sidebar.warning("⚠️ Invalid ticker format detected.")
    st.stop()

# --- DATA LAYER (FIX #1, #7) ---
@st.cache_data(ttl=86400, max_entries=100)
def fetch_ticker_info_blob(ticker_str):
    try: return yf.Ticker(ticker_str).info
    except Exception: return {}

@st.cache_data(ttl=3600)
def fetch_longlived_metadata(ticker_str):
    t = yf.Ticker(ticker_str)
    info = fetch_ticker_info_blob(ticker_str)
    payload = {
        "longName": t.fast_info.get("shortName", ticker_str),
        "targetPrice": info.get("targetMeanPrice"),
        "pe_trailing": info.get("trailingPE"),
        "pe_forward": info.get("forwardPE"),
        "peg": info.get("pegRatio"),
        "pb": info.get("priceToBook"),
        "roe": info.get("returnOnEquity"),
        "net_margin": info.get("profitMargins"),
        "op_margin": info.get("operatingMargins"),
        "eps_growth": info.get("earningsGrowth"),
        "rev_growth": info.get("revenueGrowth"),
        "debt_equity": info.get("debtToEquity"),
        "current_ratio": info.get("currentRatio"),
        "marketCap": info.get("marketCap"),
        "beta": info.get("beta"),
        "avg_volume": info.get("averageVolume"),
        "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
        "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
        "dividendYield": info.get("dividendYield"),
        "sharesOutstanding": info.get("sharesOutstanding"),
        "floatShares": info.get("floatShares"),
        "shortInterest": info.get("shortPercentOfFloat"),
        "next_earnings": "N/A"
    }
    cal = getattr(t, "calendar", None)
    if cal is not None and not cal.empty and "Earnings Date" in cal.index:
        payload["next_earnings"] = str(cal.loc["Earnings Date"].iloc[0].date())
    return payload

@st.cache_data(ttl=60, max_entries=50)
def get_raw_market_data(ticker_str, benchmark_str, period_str):
    stock = yf.Ticker(ticker_str)
    history = stock.history(period=period_str, interval="1d")
    if history.empty or len(history) < 2: return None, None, None
    bench = yf.Ticker(benchmark_str).history(period=period_str, interval="1d")
    return history, bench, {"prev_close": history['Close'].tail(2).iloc[0]}

def compute_wilder_smoothing(series, window=14):
    rma = series.copy()
    rma.iloc[window] = series.iloc[1:window+1].mean()
    for i in range(window + 1, len(series)):
        rma.iloc[i] = (series.iloc[i] * (1/window)) + (rma.iloc[i-1] * (1 - 1/window))
    return rma

@st.cache_data(ttl=30)
def compute_technical_indicators(df, df_bench):
    # Moving Averages
    df['SMA50'] = df['Close'].rolling(50, min_periods=1).mean()
    df['SMA200'] = df['Close'].rolling(200, min_periods=1).mean()
    
    # Bollinger
    ma20 = df['Close'].rolling(20).mean()
    std20 = df['Close'].rolling(20).std()
    df['BB_Upper'] = ma20 + (2 * std20)
    df['BB_Lower'] = ma20 - (2 * std20)
    df['Vol_Bandwidth'] = (df['BB_Upper'] - df['BB_Lower']) / ma20
    df['BB_Squeeze'] = df['Vol_Bandwidth'] < df['Vol_Bandwidth'].expanding().quantile(0.20)
    
    # RSI
    delta = df['Close'].diff()
    avg_gain = compute_wilder_smoothing(delta.clip(lower=0), 14)
    avg_loss = compute_wilder_smoothing(-delta.clip(upper=0), 14)
    df['RSI'] = 100 - (100 / (1 + (avg_gain / avg_loss.replace(0, np.nan))))
    
    # MACD
    df['MACD'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    
    # ADX & DMI
    tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift(1)), abs(df['Low']-df['Close'].shift(1))], axis=1).max(axis=1)
    df['ATR'] = compute_wilder_smoothing(tr, 14)
    up_move, down_move = df['High'].diff(), -df['Low'].diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    df['PlusDI'] = 100 * (compute_wilder_smoothing(pd.Series(plus_dm, index=df.index), 14) / df['ATR'].replace(0, np.nan))
    df['MinusDI'] = 100 * (compute_wilder_smoothing(pd.Series(minus_dm, index=df.index), 14) / df['ATR'].replace(0, np.nan))
    dx = (abs(df['PlusDI'] - df['MinusDI']) / (df['PlusDI'] + df['MinusDI']).replace(0, np.nan)) * 100
    df['ADX'] = compute_wilder_smoothing(dx, 14)
    
    # Alpha
    df['Alpha_Strength'] = (1 + df['Close'].pct_change()).cumprod() - (1 + df_bench['Close'].pct_change().reindex(df.index, method='ffill')).cumprod()
    return df

# --- LAYER 3: RENDER ---
raw_history, bench_history, info_payload = get_raw_market_data(ticker_symbol, benchmark_sym, period_val)

if raw_history is not None:
    fnd = fetch_longlived_metadata(ticker_symbol)
    df_view = compute_technical_indicators(raw_history, bench_history)
    latest = df_view.iloc[-1]
    
    main, side = st.columns([2.3, 0.7])
    with main:
        st.subheader(f"🏢 {fnd['longName']} ({ticker_symbol})")
        col_h = st.columns(4)
        col_h[0].metric("Price", f"${latest['Close']:.2f}", f"{((latest['Close']-info_payload['prev_close'])/info_payload['prev_close']*100):+.2f}%")
        col_h[1].metric("ATR 14", f"${latest['ATR']:.2f}")
        col_h[2].metric("52w Pos", f"{((latest['Close']-fnd['fiftyTwoWeekLow'])/(fnd['fiftyTwoWeekHigh']-fnd['fiftyTwoWeekLow'])*100):.1f}%")
        col_h[3].metric("Alpha", f"{latest['Alpha_Strength']*100:+.2f}%")

        # --- ORTHOGONAL SCORING ---
        trend = np.clip(((latest['SMA50'] - latest['SMA200']) / latest['SMA200']) * 10, -1.0, 1.0)
        mom = np.clip((0.6 * ((latest['RSI'] - 50) / 20)) + (0.4 * (1 if latest['MACD'] > latest['MACD_Signal'] else -1)), -1.0, 1.0)
        vol = np.clip(((latest['Close'] - latest['BB_Lower']) / (latest['BB_Upper'] - latest['BB_Lower']) - 0.5) * 2, -1.0, 1.0) * (latest['Vol_Bandwidth'] * 5)
        score = (trend + mom + vol) * (1.1 if latest['ADX'] > 25 else 0.7)
        st.success(f"### Consensus Score: {score:+.2f} | Regime: {'Bullish' if score > 0.1 else 'Bearish' if score < -0.1 else 'Neutral'}")

        # --- CHART ---
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.5, 0.25, 0.25])
        fig.add_trace(go.Candlestick(x=df_view.index, open=df_view['Open'], high=df_view['High'], low=df_view['Low'], close=df_view['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['SMA50'], name='SMA50', line=dict(color='yellow', width=1)), row=1, col=1)
        fig.add_trace(go.Bar(x=df_view.index, y=df_view['Volume'], name='Vol', marker_color='rgba(100,100,100,0.5)'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['ADX'], name='ADX', line=dict(color='orange', width=2)), row=3, col=1)
        fig.update_layout(height=650, template="plotly_dark", hovermode="x unified", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # --- JSON EXPORT ---
        st.code(f"""{{"ticker":"{ticker_symbol}", "price":{latest['Close']:.2f}, "rsi":{latest['RSI']:.1f}, "adx":{latest['ADX']:.1f}, "pe":{fnd['pe_trailing'] or 'null'}}}""", language="json")

    with side:
        st.markdown("### Fundamentals")
        st.write(f"Market Cap: {fnd['marketCap']/1e9:.1f}B")
        st.write(f"Debt/Equity: {fnd['debt_equity']:.2f}" if fnd['debt_equity'] else "")
else:
    st.error("Data unavailable.")
