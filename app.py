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

# --- LONGLIVED PROFILE NAME & FUNDAMENTALS SCRAPER (24HR CACHE BOTTLENECK GUARD) ---
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
        # Pull 2 years to cleanly seed rolling 200 SMA and ADX lookbacks without early drops
        history = stock.history(period="2y", interval="1d")
        if history.empty or len(history) < 2:
            return None, None
            
        # Precise operational session close extraction (FIX #5)
        fast_payload = {
            "prev_close": history['Close'].tail(2).iloc[0]
        }
        return history, fast_payload
    except Exception:
        return None, None

# --- LAYER 2: SYSTEM METRICS FEATURE ENGINEERING LAYER ---
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
    # Expanding Quantile tracking avoids lookahead/recalibration drift (FIX #3)
    df['BB_Squeeze'] = df['Vol_Bandwidth'] < df['Vol_Bandwidth'].expanding().quantile(0.20)
    
    # 3. Wilder's Exponential Smoothing RSI with Math Correct Base Init
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    # True Wilder Initialized Exponential Smoothing Algorithm (RMA)
    def compute_wilder_smoothing(series, window=14):
        rma = series.copy()
        # Seed first valid indicator cell with a simple rolling mean
        rma.iloc[window] = series.iloc[1:window+1].mean()
        rma.iloc[:window] = np.nan
        # Apply Wilder's alpha decay recursively
        for i in range(window + 1, len(series)):
            rma.iloc[i] = (series.iloc[i] * (1/window)) + (rma.iloc[i-1] * (1 - 1/window))
        return rma

    avg_gain = compute_wilder_smoothing(gain, 14)
    avg_loss = compute_wilder_smoothing(loss, 14)
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df['RSI'] = 100 - (100 / (1 + rs))
    # No synthetic ffill or bfill. Leave NaNs native; handled downstream by rendering guards (FIX #4)
    
    # 4. Math-Correct True Wilder ADX Framework (FIX #1)
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

    atr_wilder = compute_wilder_smoothing(tr, 14)
    
    plus_di = 100 * (compute_wilder_smoothing(pd.Series(plus_dm, index=df.index), 14) / atr_wilder.replace(0, np.nan))
    minus_di = 100 * (compute_wilder_smoothing(pd.Series(minus_dm, index=df.index), 14) / atr_wilder.replace(0, np.nan))

    dx = (abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)) * 100
    df['ADX'] = compute_wilder_smoothing(dx, 14)
    
    return df.tail(252)

# --- LAYER 3: LAYOUT MATRIX RENDERING ENGINE ---
with st.spinner("Fetching market data..."):
    raw_history, info_payload = get_raw_market_data(ticker_symbol)

if raw_history is not None and info_payload is not None:
    fnd = fetch_longlived_metadata(ticker_symbol)
    df_view = compute_technical_indicators(raw_history)
    
    # Anchor to the absolute latest row index
    latest = df_view.iloc[-1]
    sma_available = pd.notna(latest["SMA50"]) and pd.notna(latest["SMA200"])  # Hardened Gating Check (FIX #2)
    
    latest_close = latest['Close']
    prev_close = info_payload['prev_close']
    price_change = latest_close - prev_close
    pct_change = (price_change / prev_close) * 100 if prev_close else 0.0
    
    main_layout, fundamental_sidebar = st.columns([2.2, 0.8])
    
    with main_layout:
        st.subheader(f"🏢 {fnd['longName']} ({ticker_symbol})")
        col_h1, col_h2 = st.columns(2)
        col_h1.metric("Closing Price (USD)", f"${latest_close:,.2f}", f"${price_change:+.2f} ({pct_change:+.2f}%)")
        
        if fnd["targetPrice"]:
            implied_return = ((fnd["targetPrice"] - latest_close) / latest_close) * 100
            col_h2.metric("Analyst Target (12M Mean)", f"${fnd['targetPrice']:,.2f}", f"{implied_return:+.2f}% Implied Return")
        else:
            col_h2.metric("Analyst Target (12M Mean)", "N/A")

        # --- REGIME ANALYTICAL VECTOR MATRIX ---
        st.markdown("---")
        st.subheader("📊 Regime Matrix Evaluation")
        
        latest_rsi = latest['RSI']
        latest_upper_bb = latest['BB_Upper']
        latest_lower_bb = latest['BB_Lower']
        latest_squeeze = latest['BB_Squeeze']
        latest_adx = latest['ADX']
        
        # Guard momentum evaluation thresholds from NaN warm-up states (FIX #4)
        if pd.isna(latest_rsi):
            rsi_label, rsi_score = "⚪ Warmup Phase", 0.0
        elif latest_rsi > 70:
            rsi_label, rsi_score = "🔴 Overbought Warning", -1.0
        elif latest_rsi < 30:
            rsi_label, rsi_score = "🟢 Oversold Target", 1.0
        else:
            rsi_label, rsi_score = "⚪ Neutral Drift", 0.0
            
        if pd.isna(latest_adx) or latest_adx < 20:
            trend_state, adx_score = "⚪ Weak / Choppy Market", 0.0
        elif latest_adx < 25:
            trend_state, adx_score = "🟡 Emerging Trend Horizon", 0.5
        else:
            trend_state, adx_score = "🟢 Strong Active Trend Regime", 1.0
            
        signals = {
            "RSI": {"label": rsi_label, "score": rsi_score},
            "BB": {"label": "⚪ Volatility Squeeze (Adaptive Limit)" if latest_squeeze else ("🔴 Upper Bound Broken" if latest_close >= latest_upper_bb else ("🟢 Lower Bound Broken" if latest_close <= latest_lower_bb else "⚪ Normal Band")), "score": 0.0 if latest_squeeze else (-1.0 if latest_close >= latest_upper_bb else (1.0 if latest_close <= latest_lower_bb else 0.0))},
            "SMA": {"label": "🟢 Golden Cross" if latest['SMA50'] > latest['SMA200'] else "🔴 Death Cross", "score": 1.0 if latest['SMA50'] > latest['SMA200'] else -1.0} if sma_available else {"label": "⚪ Awaiting Lookback", "score": 0.0},
            "ADX": {"label": trend_state, "score": adx_score}
        }

        # NON-LINEAR REGIME SEPARATION ARCHITECTURE (FIX #6)
        # Prevents contradictory indicators from canceling out or inflating late-cycle scores
        trend_component = (signals["SMA"]["score"] * 0.65) + (signals["ADX"]["score"] * 0.35)
        meanrev_component = (signals["RSI"]["score"] * 0.60) + (signals["BB"]["score"] * 0.40)
        
        # Regime Gating Logic: If a strong trend is verified by ADX, trend signals dominate and mean-reversion fades
        if latest_adx >= 25.0:
            macro_score = trend_component + (0.15 * meanrev_component)
        else:
            # If market is choppy, trend signals fade and mean-reversion filters step in
            macro_score = (0.20 * trend_component) + meanrev_component
            
        # Volatility scale dampener
        vol_regime = 1.0 if latest_adx > 20.0 else 0.5
        macro_score *= vol_regime
        
        if macro_score >= 0.3: macro_msg, render_box = "🟢 STRONG BULLISH BIAS", st.success
        elif macro_score >= 0.1: macro_msg, render_box = "🟢 MODERATE BULLISH BIAS", st.success
        elif macro_score <= -0.3: macro_msg, render_box = "🔴 STRONG BEARISH BIAS", st.error
        elif macro_score <= -0.1: macro_msg, render_box = "🔴 MODERATE BEARISH BIAS", st.error
        else: macro_msg, render_box = "⚪ NEUTRAL CONVERGENCE / HOLD", st.info
            
        render_box(f"#### **Weighted Technical Signal Consensus: {macro_msg}**")

        col_m1, col_m2 = st.columns(2)
        col_m1.metric("RSI Momentum (14)", f"{latest_rsi:.1f}" if pd.notna(latest_rsi) else "N/A", signals['RSI']['label'], delta_color="off")
        col_m2.metric("Bollinger Bounds", f"${latest_close:,.2f}", signals['BB']['label'], delta_color="off")
        col_m3, col_m4 = st.columns(2)
        col_m3.metric("Macro Trend Alignment", "200 SMA Status", signals['SMA']['label'], delta_color="off")
        col_m4.metric("Trend Strength (ADX)", f"{latest_adx:.1f}" if pd.notna(latest_adx) else "N/A", signals['ADX']['label'], delta_color="off")

        # --- TECHNICAL VISUALIZATION PANELS ---
        st.markdown("---")
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.7, 0.3])
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['BB_Upper'], mode='lines', line=dict(color='rgba(0, 230, 118, 0.25)', width=1), showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['BB_Lower'], mode='lines', line=dict(color='rgba(0, 230, 118, 0.25)', width=1), fill='tonexty', fillcolor='rgba(0, 230, 118, 0.02)', name='Bollinger Bands (20,2)'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['Close'], mode='lines', name='Closing Price', line=dict(color='#1565C0', width=2.5)), row=1, col=1)
        
        if sma_available:
            fig.add_trace(go.Scatter(x=df_view.index, y=df_view['SMA50'], mode='lines', name='50-Day SMA', line=dict(color='#FBC02D', width=1.5, dash='dash')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_view.index, y=df_view['SMA200'], mode='lines', name='200-Day SMA', line=dict(color='#D32F2F', width=1.5, dash='dot')), row=1, col=1)
            
        # Add target line conditional guard to prevent layout clipping (FIX #5)
        if fnd["targetPrice"] and (abs(fnd["targetPrice"] - latest_close) / latest_close < 0.45):
            fig.add_trace(go.Scatter(x=df_view.index, y=[fnd["targetPrice"]] * len(df_view), mode='lines', name='Consensus Target', line=dict(color='#E65100', width=1.5, dash='longdashdot')), row=1, col=1)
            
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['RSI'], mode='lines', name='RSI (14)', line=dict(color='#00E676', width=1.5)), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="rgba(211, 47, 47, 0.6)", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="rgba(76, 175, 80, 0.6)", row=2, col=1)

        fig.update_layout(height=480, margin=dict(l=20, r=20, t=10, b=10), template="plotly_dark", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), yaxis=dict(title="Price (USD)"), yaxis2=dict(title="RSI (14)", range=[10, 90]))
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
    st.error(f"❌ Core Exception: Could not pull market assets for ticker token '{ticker_symbol}'.")
