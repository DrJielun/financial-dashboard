import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# --- 1. CONFIGURATION & ENGINE INITIALIZATION ---
st.set_page_config(layout="wide", page_title="Professional Session Terminal")
st.title("⏱️ Institutional Session Terminal")

# --- NATIVE STABLE AUTO-REFRESH INJECTION ---
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

# --- USER INPUT & FORMAT GUARD ---
ticker_symbol = st.sidebar.text_input("Enter Equity Ticker Symbol:", value="AAPL").upper().strip()

if not ticker_symbol.isalnum():
    st.sidebar.warning("⚠️ Invalid ticker format detected.")
    st.stop()

# --- ISOLATED FUNDAMENTALS BLOB SCRAPER (24HR TTL CACHE PROTECTION) ---
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
        "eps_growth": None, "rev_growth": None,
        "debt_equity": None, "current_ratio": None
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
    except Exception:
        pass
    return payload

# --- LAYER 1: RAW HISTORICAL DATA INGESTION ENGINE ---
@st.cache_data(ttl=60, max_entries=50)
def get_raw_market_data(ticker_str):
    try:
        stock = yf.Ticker(ticker_str)
        history = stock.history(period="2y", interval="1d")
        if history.empty or len(history) < 200:
            return None, None
            
        fast_payload = {
            "prev_close": history['Close'].tail(2).iloc[0]
        }
        return history, fast_payload
    except Exception:
        return None, None

# --- LAYER 2: SYSTEM METRICS & TECH FEATURE ENGINEERING LAYER ---
@st.cache_data(ttl=30)
def compute_technical_indicators(df_history):
    df = df_history.copy()
    
    # 1. Moving Averages
    df['SMA50'] = df['Close'].rolling(window=50).mean()
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    
    # 2. Bollinger Bands (20, 2)
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['Std20'] = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['MA20'] + (2 * df['Std20'])
    df['BB_Lower'] = df['MA20'] - (2 * df['Std20'])
    
    df['Vol_Bandwidth'] = np.where(
        df['MA20'].notna() & (df['MA20'] > 0),
        (df['BB_Upper'] - df['BB_Lower']) / df['MA20'],
        np.nan
    )
    df['BB_Squeeze'] = df['Vol_Bandwidth'] < df['Vol_Bandwidth'].expanding().quantile(0.20)
    
    # Base Wilder Exponential Smoothing Engine (RMA)
    def compute_wilder_smoothing(series, window=14):
        if len(series) <= window:
            return pd.Series(np.nan, index=series.index)
        rma = series.copy()
        rma.iloc[window] = series.iloc[1:window+1].mean()
        rma.iloc[:window] = np.nan
        for i in range(window + 1, len(series)):
            rma.iloc[i] = (series.iloc[i] * (1/window)) + (rma.iloc[i-1] * (1 - 1/window))
        return rma

    # 3. Wilder's Exponential Smoothing RSI
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    avg_gain = compute_wilder_smoothing(gain, 14)
    avg_loss = compute_wilder_smoothing(loss, 14)
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df['RSI'] = 100 - (100 / (1 + rs))

    # 4. Institutional MACD Pipeline (FIX #7)
    df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    
    # 5. Math-Correct True Wilder ADX & ATR Pipeline (FIX #1 & #8)
    high = df['High']
    low = df['Low']
    close = df['Close']

    up_move = high - high.shift(1)
    down_move = low.shift(1) - low

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Expose True Wilder ATR (FIX #8)
    df['ATR'] = compute_wilder_smoothing(tr, 14)
    
    plus_dm_rma = compute_wilder_smoothing(pd.Series(plus_dm, index=df.index), 14)
    minus_dm_rma = compute_wilder_smoothing(pd.Series(minus_dm, index=df.index), 14)

    plus_di = 100 * (plus_dm_rma / df['ATR'].replace(0, np.nan))
    minus_di = 100 * (minus_dm_rma / df['ATR'].replace(0, np.nan))

    dx = (abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)) * 100
    df['ADX'] = compute_wilder_smoothing(dx, 14)
    
    return df.tail(252)

# --- LAYER 3: LAYOUT MATRIX RENDERING ENGINE ---
with st.spinner("Fetching market data..."):
    raw_history, info_payload = get_raw_market_data(ticker_symbol)

if raw_history is not None and info_payload is not None:
    fnd = fetch_longlived_metadata(ticker_symbol)
    df_view = compute_technical_indicators(raw_history)
    
    latest = df_view.iloc[-1]
    sma_available = pd.notna(latest["SMA50"]) and pd.notna(latest["SMA200"])
    
    latest_close = latest['Close']
    prev_close = info_payload['prev_close']
    price_change = latest_close - prev_close
    pct_change = (price_change / prev_close) * 100 if prev_close else 0.0
    
    main_layout, fundamental_sidebar = st.columns([2.2, 0.8])
    
    with main_layout:
        st.subheader(f"🏢 {fnd['longName']} ({ticker_symbol})")
        col_h1, col_h2, col_h3 = st.columns(3)
        col_h1.metric("Closing Price (USD)", f"${latest_close:,.2f}", f"${price_change:+.2f} ({pct_change:+.2f}%)")
        col_h2.metric("Average True Range (ATR 14)", f"${latest['ATR']:.2f}" if pd.notna(latest['ATR']) else "N/A", "Volatility Metric")
        
        if fnd["targetPrice"]:
            implied_return = ((fnd["targetPrice"] - latest_close) / latest_close) * 100
            col_h3.metric("Analyst Target (Mean)", f"${fnd['targetPrice']:,.2f}", f"{implied_return:+.2f}% Implied Return")
        else:
            col_h3.metric("Analyst Target (Mean)", "N/A")

        # --- NON-LINEAR UNBIASED MATRIX NORMALIZATION ENGINE (FIX #6) ---
        st.markdown("---")
        st.subheader("📊 Normalized Factor Regime Evaluation")
        
        latest_rsi = latest['RSI']
        latest_upper_bb = latest['BB_Upper']
        latest_lower_bb = latest['BB_Lower']
        latest_adx = latest['ADX']
        latest_macd = latest['MACD']
        latest_macd_signal = latest['MACD_Signal']
        
        # Axis 1: Normalized Trend Factor [-1, 1]
        if sma_available:
            raw_trend = (latest['SMA50'] - latest['SMA200']) / latest['SMA200']
            trend_factor = np.clip(raw_trend * 10, -1.0, 1.0)  # Center-scaled threshold limit
            trend_msg = "🟢 Golden Cross Expansion" if trend_factor > 0 else "🔴 Death Cross Compression"
        else:
            trend_factor, trend_msg = 0.0, "⚪ Awaiting Baseline Initialization"

        # Axis 2: Normalized Momentum Factor [-1, 1] (Blended RSI & MACD alignment)
        if pd.notna(latest_rsi) and pd.notna(latest_macd):
            norm_rsi = ((latest_rsi - 50) / 20)  # Scale standard deviation boundaries
            norm_macd = 1.0 if latest_macd > latest_macd_signal else -1.0
            momentum_factor = np.clip((0.6 * norm_rsi) + (0.4 * norm_macd), -1.0, 1.0)
            momentum_msg = "🟢 Bullish Momentum Divergence" if momentum_factor > 0.1 else ("🔴 Bearish Momentum Pressure" if momentum_factor < -0.1 else "⚪ Neutral Momentum Drift")
        else:
            momentum_factor, momentum_msg = 0.0, "⚪ Momentum Data Insufficient"

        # Axis 3: Normalized Volatility / Extreme Factor [-1, 1]
        if pd.notna(latest_upper_bb) and (latest_upper_bb != latest_lower_bb):
            # Map price placement accurately inside the width of the bands
            pct_b = (latest_close - latest_lower_bb) / (latest_upper_bb - latest_lower_bb)
            volatility_factor = np.clip((pct_b - 0.5) * 2, -1.0, 1.0)  # Map 0-1 range to clean [-1, 1] bounds
            vol_msg = "🔴 Overextended Upper Range" if volatility_factor > 0.7 else ("🟢 Underextended Lower Range" if volatility_factor < -0.7 else "⚪ Stable Inside Channels")
        else:
            volatility_factor, vol_msg = 0.0, "⚪ Volatility Squeeze Mode"

        # Orthogonal Composite Score Synthesis (Summed directly without scale corruption)
        composite_score = trend_factor + momentum_factor + volatility_factor
        
        # Apply volatility/trend regime dampener to scale score conviction in choppy markets
        vol_regime = 1.1 if pd.notna(latest_adx) and latest_adx > 25.0 else 0.7
        composite_score *= vol_regime
        
        if composite_score >= 0.75: macro_msg, render_box = "🟢 STRONG BULLISH REGIME", st.success
        elif composite_score >= 0.25: macro_msg, render_box = "🟢 MODERATE BULLISH REGIME", st.success
        elif composite_score <= -0.75: macro_msg, render_box = "🔴 STRONG BEARISH REGIME", st.error
        elif composite_score <= -0.25: macro_msg, render_box = "🔴 MODERATE BEARISH REGIME", st.error
        else: macro_msg, render_box = "⚪ NEUTRAL / CONVERGING MARKET RANGE", st.info
            
        render_box(f"#### **Composite Normalization Signal Consensus: {macro_msg}**")

        # Visual Structural Metrics Panels
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Trend Factor ([-1, 1])", f"{trend_factor:+.2f}", trend_msg, delta_color="off")
        col_m2.metric("Momentum Factor ([-1, 1])", f"{momentum_factor:+.2f}", momentum_msg, delta_color="off")
        col_m3.metric("Volatility Factor ([-1, 1])", f"{volatility_factor:+.2f}", vol_msg, delta_color="off")

        # --- TECHNICAL VISUALIZATION TERMINAL ---
        st.markdown("---")
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.55, 0.22, 0.23])
        
        # Row 1: Core Price Action & Overlays
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['BB_Upper'], mode='lines', line=dict(color='rgba(0, 230, 118, 0.25)', width=1), showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['BB_Lower'], mode='lines', line=dict(color='rgba(0, 230, 118, 0.25)', width=1), fill='tonexty', fillcolor='rgba(0, 230, 118, 0.02)', name='Bollinger Bands (20,2)'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['Close'], mode='lines', name='Closing Price', line=dict(color='#1565C0', width=2.5)), row=1, col=1)
        
        if sma_available:
            fig.add_trace(go.Scatter(x=df_view.index, y=df_view['SMA50'], mode='lines', name='50-Day SMA', line=dict(color='#FBC02D', width=1.5, dash='dash')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_view.index, y=df_view['SMA200'], mode='lines', name='200-Day SMA', line=dict(color='#D32F2F', width=1.5, dash='dot')), row=1, col=1)
        if fnd["targetPrice"] and (abs(fnd["targetPrice"] - latest_close) / latest_close < 0.45):
            fig.add_trace(go.Scatter(x=df_view.index, y=[fnd["targetPrice"]] * len(df_view), mode='lines', name='Consensus Target', line=dict(color='#E65100', width=1.5, dash='longdashdot')), row=1, col=1)
            
        # Row 2: RSI Panel
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['RSI'], mode='lines', name='RSI (14)', line=dict(color='#00E676', width=1.5)), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="rgba(211, 47, 47, 0.4)", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="rgba(76, 175, 80, 0.4)", row=2, col=1)
        
        # Row 3: Institutional MACD Subplot Layout (FIX #7)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['MACD'], mode='lines', name='MACD', line=dict(color='#29B6F6', width=1.5)), row=3, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['MACD_Signal'], mode='lines', name='Signal Line', line=dict(color='#AB47BC', width=1.2, dash='dot')), row=3, col=1)
        fig.add_trace(go.Bar(x=df_view.index, y=df_view['MACD_Hist'], name='Histogram', marker_color=np.where(df_view['MACD_Hist'] >= 0, 'rgba(0, 230, 118, 0.4)', 'rgba(211, 47, 47, 0.4)')), row=3, col=1)

        fig.update_layout(height=650, margin=dict(l=20, r=20, t=10, b=10), template="plotly_dark", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), yaxis=dict(title="Price (USD)"), yaxis2=dict(title="RSI", range=[10, 90]), yaxis3=dict(title="MACD Output"))
        st.plotly_chart(fig, use_container_width=True)

    # --- FUNDAMENTAL SIDEBAR MATRIX ---
    with fundamental_sidebar:
        st.markdown("### 📋 Company Fundamentals")
        
        def fmt_v(v, f="num"):
            if v is None or pd.isna(v): return "N/A"
            if f == "pct": return f"{v * 100:.2f}%"
            return f"{v:.2f}"

        st.markdown("#### **Valuation**")
        st.markdown(f"**Trailing P/E:** `{fmt_v(fnd['pe_trailing'])}`")
        st.markdown(f"**Forward P/E:** `{fmt_v(fnd['pe_forward'])}`")
        st.markdown(f"**PEG Ratio:** `{fmt_v(fnd['peg'])}`")
        st.markdown(f"**Price to Book:** `{fmt_v(fnd['pb'])}`")
        
        st.markdown("---")
        st.markdown("#### **Profitability**")
        st.markdown(f"**Return on Equity (ROE):** `{fmt_v(fnd['roe'], 'pct')}`")
        st.markdown(f"**Net Profit Margin:** `{fmt_v(fnd['net_margin'], 'pct')}`")
        st.markdown(f"**Operating Margin:** `{fmt_v(fnd['op_margin'], 'pct')}`")
        
        st.markdown("---")
        st.markdown("#### **Growth (YoY)**")
        st.markdown(f"**Earnings Growth:** `{fmt_v(fnd['eps_growth'], 'pct')}`")
        st.markdown(f"**Revenue Growth:** `{fmt_v(fnd['rev_growth'], 'pct')}`")
        
        st.markdown("---")
        st.markdown("#### **Financial Strength**")
        
        de_val = fnd['debt_equity']
        if pd.notna(de_val):
            de_str = f"{de_val:.2f}%" if de_val > 5.0 else f"{de_val * 100:.2f}%"
        else:
            de_str = "N/A"
            
        st.markdown(f"**Debt to Equity:** `{de_str}`")
        st.markdown(f"**Current Ratio:** `{fmt_v(fnd['current_ratio'])}`")
else:
    st.error(f"❌ Core Exception: Market historical parameters for symbol '{ticker_symbol}' are insufficient.")
