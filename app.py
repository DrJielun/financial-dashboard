import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# --- 1. CONFIGURATION & APP INITIALIZATION ---
st.set_page_config(layout="wide", page_title="Institutional Quant Terminal")
st.title("⚡ Institutional Quant Terminal")

# --- WATCHLIST & TICKER MANAGEMENT (FIX #11) ---
st.sidebar.header("Navigation & Watchlist")
watchlist = ["AAPL", "MSFT", "NVDA", "GOOG", "META", "AMZN"]
selected_watch = st.sidebar.selectbox("Quick Select Watchlist:", [""] + watchlist)

# Manage active symbol definition
default_ticker = selected_watch if selected_watch else "AAPL"
ticker_symbol = st.sidebar.text_input("Manual Ticker Input:", value=default_ticker).upper().strip()

# --- TIMEFRAME SUPPORT CONTROLS (FIX #10) ---
timeframe_opts = {
    "1 Month": {"period": "1mo", "interval": "1d"},
    "3 Months": {"period": "3mo", "interval": "1d"},
    "6 Months": {"period": "6mo", "interval": "1d"},
    "1 Year": {"period": "1y", "interval": "1d"},
    "2 Years": {"period": "2y", "interval": "1d"},
    "5 Years": {"period": "5y", "interval": "1d"}
}
selected_tf = st.sidebar.selectbox("Terminal Analysis Horizon:", list(timeframe_opts.keys()), index=3)
period_val = timeframe_opts[selected_tf]["period"]
interval_val = timeframe_opts[selected_tf]["interval"]

# --- BENCHMARK SELECTION (FIX #6) ---
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
        "longName": ticker_str, "targetPrice": None,
        "pe_trailing": None, "pe_forward": None, "peg": None, "pb": None,
        "roe": None, "net_margin": None, "op_margin": None,
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
            payload["targetPrice"] = info.get("targetMeanPrice") or info.get("targetHighPrice")
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
            # Expanded panels (FIX #7)
            payload["marketCap"] = info.get("marketCap")
            payload["beta"] = info.get("beta")
            payload["avg_volume"] = info.get("averageVolume")
            payload["fiftyTwoWeekHigh"] = info.get("fiftyTwoWeekHigh")
            payload["fiftyTwoWeekLow"] = info.get("fiftyTwoWeekLow")
            payload["dividendYield"] = info.get("dividendYield")
            payload["sharesOutstanding"] = info.get("sharesOutstanding")
            payload["floatShares"] = info.get("floatShares")
            payload["shortInterest"] = info.get("shortPercentOfFloat")
            
        # Extract calendar dates cleanly (FIX #8)
        calendar = getattr(t, "calendar", None)
        if calendar is not None and not calendar.empty:
            if "Earnings Date" in calendar.index:
                payload["next_earnings"] = str(calendar.loc["Earnings Date"].iloc[0].date())
    except Exception:
        pass
    return payload

# --- LAYER 1: PIPELINE INGESTION WITH DYNAMIC BENCHMARKS ---
@st.cache_data(ttl=60, max_entries=50)
def get_raw_market_data(ticker_str, benchmark_str, period_str):
    try:
        stock = yf.Ticker(ticker_str)
        # Fetch data with sufficient window padding to support indicators on 5-year views
        history = stock.history(period="5y", interval="1d")
        if history.empty or len(history) < 200:
            return None, None, None
            
        bench = yf.Ticker(benchmark_str)
        bench_hist = bench.history(period="5y", interval="1d")
        
        fast_payload = {
            "prev_close": history['Close'].tail(2).iloc[0]
        }
        return history, bench_hist, fast_payload
    except Exception:
        return None, None, None

# --- LAYER 2: INSTITUTIONAL QUANT ENGINE (FIX #3, #4, #5) ---
@st.cache_data(ttl=30)
def compute_technical_indicators(df_history, df_bench, period_str):
    df = df_history.copy()
    
    # 1. Moving Averages
    df['SMA50'] = df['Close'].rolling(window=50).mean()
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    
    # 2. Bollinger Bands (20, 2)
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['Std20'] = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['MA20'] + (2 * df['Std20'])
    df['BB_Lower'] = df['MA20'] - (2 * df['Std20'])
    df['Vol_Bandwidth'] = np.where(df['MA20'] > 0, (df['BB_Upper'] - df['BB_Lower']) / df['MA20'], np.nan)
    df['BB_Squeeze'] = df['Vol_Bandwidth'] < df['Vol_Bandwidth'].expanding().quantile(0.20)
    
    # High-Speed Vectorized Exponential Moving Window Arrays (FIX #3 - O(n) loop dropped)
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    # Wilder's RMA exact approximation via standard fast alpha decay parameters
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # 3. MACD Layout
    df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    
    # 4. True Wilder Directional Movement Pipeline + ATR Integration (FIX #4 & #8)
    high, low, close = df['High'], df['Low'], df['Close']
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    df['ATR'] = tr.ewm(alpha=1/14, adjust=False).mean()
    plus_di = 100 * (pd.Series(plus_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() / df['ATR'].replace(0, np.nan))
    df['PlusDI'] = plus_di.bfill()
    minus_di = 100 * (pd.Series(minus_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() / df['ATR'].replace(0, np.nan))
    df['MinusDI'] = minus_di.bfill()

    dx = (abs(df['PlusDI'] - df['MinusDI']) / (df['PlusDI'] + df['MinusDI']).replace(0, np.nan)) * 100
    df['ADX'] = dx.ewm(alpha=1/14, adjust=False).mean()
    
    # 5. Relative Alpha Strength (FIX #6)
    df['Stock_Return_Cum'] = df['Close'].pct_change().cumsum()
    df_bench['Bench_Return_Cum'] = df_bench['Close'].pct_change().cumsum()
    df['Alpha_Strength'] = df['Stock_Return_Cum'] - df_bench['Bench_Return_Cum']
    df['Alpha_Strength'] = df['Alpha_Strength'].fillna(0)

    # Slice output matrix safely depending on the selected user timeframe
    tf_slice_map = {"1mo": 21, "3mo": 63, "6mo": 126, "1y": 252, "2y": 504, "5y": 1260}
    slice_window = tf_slice_map.get(period_str, 252)
    return df.tail(slice_window)

# --- LAYER 3: LAYOUT MATRIX RENDERING ENGINE ---
with st.spinner("Executing real-time pipeline algorithms..."):
    raw_history, bench_history, info_payload = get_raw_market_data(ticker_symbol, benchmark_sym, period_val)

if raw_history is not None and info_payload is not None:
    fnd = fetch_longlived_metadata(ticker_symbol)
    df_view = compute_technical_indicators(raw_history, bench_history, period_val)
    
    latest = df_view.iloc[-1]
    sma_available = pd.notna(latest["SMA50"]) and pd.notna(latest["SMA200"])
    
    latest_close = latest['Close']
    prev_close = info_payload['prev_close']
    price_change = latest_close - prev_close
    pct_change = (price_change / prev_close) * 100 if prev_close else 0.0
    
    # Calculate Price Position Parameters (FIX #9)
    high_52w = fnd["fiftyTwoWeekHigh"] or df_view["High"].max()
    low_52w = fnd["fiftyTwoWeekLow"] or df_view["Low"].min()
    price_position_pct = ((latest_close - low_52w) / (high_52w - low_52w)) * 100 if high_52w != low_52w else 50.0
    
    # --- UI GRID INTERFACE DEFINITIONS ---
    main_layout, fundamental_sidebar = st.columns([2.3, 0.7])
    
    with main_layout:
        st.subheader(f"🏢 {fnd['longName']} ({ticker_symbol}) — {selected_tf} Horizon Analysis")
        col_h1, col_h2, col_h3, col_h4 = st.columns(4)
        col_h1.metric("Closing Value (USD)", f"${latest_close:,.2f}", f"${price_change:+.2f} ({pct_change:+.2f}%)")
        col_h2.metric("Volatility Index (ATR 14)", f"${latest['ATR']:.2f}", "Position Stop Value")
        col_h3.metric("52-Week Allocation Position", f"{price_position_pct:.1f}%", f"Range: ${low_52w:.1f} - ${high_52w:.1f}")
        col_h4.metric("Benchmark Alpha vs " + benchmark_sym, f"{latest['Alpha_Strength'] * 100:+.2f}%", "Net Cumulative Delta")

        # --- ADVANCED ORTHOGONAL SCORING ENGINE ---
        st.markdown("---")
        latest_rsi = latest['RSI']
        latest_upper_bb = latest['BB_Upper']
        latest_lower_bb = latest['BB_Lower']
        latest_adx = latest['ADX']
        latest_plus_di = latest['PlusDI']
        latest_minus_di = latest['MinusDI']
        
        # Factor Vector 1: Trend Alignment [-1, 1]
        if sma_available:
            trend_factor = np.clip(((latest['SMA50'] - latest['SMA200']) / latest['SMA200']) * 10, -1.0, 1.0)
            trend_msg = "🟢 Golden Cross Expansion" if trend_factor > 0 else "🔴 Death Cross Compression"
        else:
            trend_factor, trend_msg = 0.0, "⚪ Awaiting Historical Lookback Baseline"

        # Factor Vector 2: Pure Momentum Optimization [-1, 1]
        norm_rsi = ((latest_rsi - 50) / 20) if pd.notna(latest_rsi) else 0.0
        norm_macd = 1.0 if latest['MACD'] > latest['MACD_Signal'] else -1.0
        momentum_factor = np.clip((0.6 * norm_rsi) + (0.4 * norm_macd), -1.0, 1.0)

        # Factor Vector 3: Bandwidth Volatility Scaling Matrix (FIX #5)
        pct_b = (latest_close - latest_lower_bb) / (latest_upper_bb - latest_lower_bb) if latest_upper_bb != latest_lower_bb else 0.5
        volatility_factor = np.clip((pct_b - 0.5) * 2, -1.0, 1.0)
        # Apply Bandwidth scaling multiplier to accurately track structural breakout expansions
        volatility_factor *= (latest['Vol_Bandwidth'] * 5 if pd.notna(latest['Vol_Bandwidth']) else 1.0)
        volatility_factor = np.clip(volatility_factor, -1.0, 1.0)

        # Structural Composite Formula
        composite_score = trend_factor + momentum_factor + volatility_factor
        composite_score *= (1.15 if latest_adx > 25.0 else 0.75)  # Regime isolation multiplier
        
        if composite_score >= 0.35: macro_msg, render_box = "🟢 STRONG BULLISH BIAS", st.success
        elif composite_score >= 0.10: macro_msg, render_box = "🟢 MODERATE BULLISH BIAS", st.success
        elif composite_score <= -0.35: macro_msg, render_box = "🔴 STRONG BEARISH BIAS", st.error
        elif composite_score <= -0.10: macro_msg, render_box = "🔴 MODERATE BEARISH BIAS", st.error
        else: macro_msg, render_box = "⚪ NEUTRAL MATRIX OVERLAY / RANGE BOUND", st.info
            
        render_box(f"#### **Quantitative Model Analysis: {macro_msg}**")

        # --- NARRATIVE COMPLIANT AI SUMMARY BLOCK (FIX #12) ---
        trend_clause = "above both the 50-day and 200-day moving averages, confirming an established structural uptrend" if (sma_available and latest['SMA50'] > latest['SMA200']) else "experiencing trend consolidation below key technical moving averages"
        mom_clause = "elevated with supportive bullish MACD crossovers" if momentum_factor > 0.1 else "cooling down alongside structural bearish histogram distributions"
        adx_clause = "is strengthening and accelerating" if latest_adx > 25 else "is weakening, indicating a highly range-bound/choppy market regime"
        
        st.info(f"🤖 **Automated Market Summary:** Price action for **{ticker_symbol}** is currently trading {trend_clause}. "
                f"Momentum parameters are {mom_clause} while the RSI rests near `{latest_rsi:.1f}`. "
                f"The true mathematical ADX value (`{latest_adx:.1f}`) suggests the underlying structural trend {adx_clause}. "
                f"Relative alpha tracking shows an outperformance variance of `{latest['Alpha_Strength']*100:+.2f}%` against its benchmark selection.")

        # --- MULTI-PANEL CHART VISUALIZATION TERMINAL (FIX #1 & #2 & #4) ---
        st.markdown("---")
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.50, 0.25, 0.25])
        
        # Plot 1: True Candlesticks + Bollinger Layers + SMA (FIX #1 & #2)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['BB_Upper'], mode='lines', line=dict(color='rgba(0, 230, 118, 0.25)', width=1), showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['BB_Lower'], mode='lines', line=dict(color='rgba(0, 230, 118, 0.25)', width=1), fill='tonexty', fillcolor='rgba(0, 230, 118, 0.02)', name='Bollinger Bands (20,2)'), row=1, col=1)
        
        # Native Interactive Candlestick Trace
        fig.add_trace(go.Candlestick(x=df_view.index, open=df_view['Open'], high=df_view['High'], low=df_view['Low'], close=df_view['Close'], name='Price Action'), row=1, col=1)
        
        if sma_available:
            fig.add_trace(go.Scatter(x=df_view.index, y=df_view['SMA50'], mode='lines', name='50-Day SMA', line=dict(color='#FBC02D', width=1.5, dash='dash')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_view.index, y=df_view['SMA200'], mode='lines', name='200-Day SMA', line=dict(color='#D32F2F', width=1.5, dash='dot')), row=1, col=1)
        if fnd["targetPrice"] and (abs(fnd["targetPrice"] - latest_close) / latest_close < 0.45):
            fig.add_trace(go.Scatter(x=df_view.index, y=[fnd["targetPrice"]] * len(df_view), mode='lines', name='Consensus Target', line=dict(color='#E65100', width=1.5, dash='longdashdot')), row=1, col=1)
            
        # Plot 2: Integrated Volume & MACD Histograms (FIX #2 & #7)
        fig.add_trace(go.Bar(x=df_view.index, y=df_view['Volume'], name='Volume traded', marker_color='rgba(33, 150, 243, 0.35)'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['MACD'], mode='lines', name='MACD', line=dict(color='#29B6F6', width=1.5)), row=2, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['MACD_Signal'], mode='lines', name='Signal', line=dict(color='#AB47BC', width=1.2, dash='dot')), row=2, col=1)
        
        # Plot 3: Complete ADX/DMI Directional Matrix Panel (FIX #4)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['ADX'], mode='lines', name='ADX (Trend Strength)', line=dict(color='#FF9100', width=2.5)), row=3, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['PlusDI'], mode='lines', name='+DI (Bullish)', line=dict(color='#00E676', width=1.2, dash='dash')), row=3, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['MinusDI'], mode='lines', name='-DI (Bearish)', line=dict(color='#FF5252', width=1.2, dash='dot')), row=3, col=1)

        fig.update_layout(height=650, margin=dict(l=20, r=20, t=10, b=10), template="plotly_dark", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), xaxis=dict(rangeslider=dict(visible=False)), yaxis=dict(title="Asset Price"), yaxis2=dict(title="Volume / MACD"), yaxis3=dict(title="DMI Core Vector Matrix"))
        st.plotly_chart(fig, use_container_width=True)

    # --- FUNDAMENTAL SIDEBAR MATRIX (FIX #7 & #8) ---
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
        st.markdown(f"**Beta (Risk Profile):** `{fmt_v(fnd['beta'])}`")
        st.markdown(f"**Average Volume:** `{fmt_v(fnd['avg_volume'], 'vol')}`")
        st.markdown(f"**Shares Outstanding:** `{fmt_v(fnd['sharesOutstanding'], 'vol')}`")
        st.markdown(f"**Float Percentage:** `{fmt_v(fnd['floatShares'], 'vol')}`")
        st.markdown(f"**Short Ratio (Float):** `{fmt_v(fnd['shortInterest'], 'pct')}`")
        
        st.markdown("---")
        st.markdown("#### **Corporate Valuation Matrix**")
        st.markdown(f"**Trailing P/E:** `{fmt_v(fnd['pe_trailing'])}`")
        st.markdown(f"**Forward P/E:** `{fmt_v(fnd['pe_forward'])}`")
        st.markdown(f"**PEG Ratio (Growth):** `{fmt_v(fnd['peg'])}`")
        st.markdown(f"**Price to Book:** `{fmt_v(fnd['pb'])}`")
        st.markdown(f"**Dividend Yield:** `{fmt_v(fnd['dividendYield'], 'pct')}`")
        
        st.markdown("---")
        st.markdown("#### **Operating Ledger Margins**")
        st.markdown(f"**Return on Equity (ROE):** `{fmt_v(fnd['roe'], 'pct')}`")
        st.markdown(f"**Net Margin Profile:** `{fmt_v(fnd['net_margin'], 'pct')}`")
        st.markdown(f"**Operating Margin:** `{fmt_v(fnd['op_margin'], 'pct')}`")
        st.markdown(f"**Earnings Growth (YoY):** `{fmt_v(fnd['eps_growth'], 'pct')}`")
        st.markdown(f"**Revenue Growth (YoY):** `{fmt_v(fnd['rev_growth'], 'pct')}`")
        
        st.markdown("---")
        st.markdown("#### **Balance Sheet Strength**")
        de_val = fnd['debt_equity']
        de_str = f"{de_val:.2f}%" if (pd.notna(de_val) and de_val > 5.0) else fmt_v(de_val, "pct")
        st.markdown(f"**Debt to Equity:** `{de_str}`")
        st.markdown(f"**Current Ratio:** `{fmt_v(fnd['current_ratio'])}`")
        
        st.markdown("---")
        st.markdown("#### **Macro Calendar Forecasts**")
        st.markdown(f"**Next Expected Earnings:** `{fnd['next_earnings']}`")
else:
    st.error(f"❌ Core Data Exception: The lookback frame history for symbol '{ticker_symbol}' is insufficient.")
