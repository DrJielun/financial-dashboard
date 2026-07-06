import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import time

# --- 1. CONFIGURATION & ENGINE INITIALIZATION ---
st.set_page_config(layout="centered", page_title="Professional Session Terminal")
st.title("⏱️ Institutional Session Terminal")

# --- NATIVE REFRESH PULSE (FIX #1) ---
refresh_rate = st.sidebar.slider("Live Data Auto-Refresh (Seconds):", min_value=10, max_value=60, value=15)

# Safe, native query parameter tick to force a framework rerun without breaking the thread
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > refresh_rate:
    st.session_state.last_refresh = time.time()
    st.rerun()

# --- USER INPUT & FORMAT GUARD ---
ticker_symbol = st.text_input("Enter Equity Ticker Symbol:", value="AAPL").upper().strip()

if not ticker_symbol.isalnum():
    st.warning("⚠️ Invalid ticker format detected. Please use alphanumeric characters only.")
    st.stop()

# --- LAYER 1: RAW DATA LAYER (FIX #2 - ELIMINATED STOCK.INFO) ---
@st.cache_data(ttl=60, max_entries=50)
def get_raw_market_data(ticker_str):
    try:
        stock = yf.Ticker(ticker_str)
        # Pull 2 years to cleanly buffer 200 SMA calculations on daily bars
        history = stock.history(period="2y", interval="1d")
        if history.empty:
            return None, None
            
        # Use fast_info properties exclusively to guarantee high-speed execution
        fast_info_obj = stock.fast_info
        fast_payload = {
            "longName": fast_info_obj.get("shortName", ticker_str),
            "prev_close": history['Close'].iloc[-2] if len(history) > 1 else history['Close'].iloc[-1]
        }
        return history, fast_payload
    except Exception:
        return None, None

# --- LAYER 2: FEATURE ENGINEERING & MATHEMATICAL CLEANING (FIX #4, #5) ---
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
    
    # 3. Wilder's Exponential Smoothing RSI with Zero-Division Guard
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Finance-correct interpolation fallback to protect signaling boundaries (FIX #4)
    df['RSI'] = df['RSI'].interpolate(limit_direction="both").fillna(50)
    
    return df

# --- LAYER 3: CORE RENDERING PIPELINE ---
with st.spinner("Fetching market data..."):
    raw_history, info_payload = get_raw_market_data(ticker_symbol)

if raw_history is not None and info_payload is not None:
    # Compute indicator matrices
    df_analyzed = compute_technical_indicators(raw_history)
    
    # Slice view safely to view window layout limits
    df_view = df_analyzed.tail(252)
    
    # Check for NaN risk safely across full arrays (FIX #3)
    sma_available = df_view[['SMA50', 'SMA200']].dropna().shape[0] > 0
    
    # Pull latest valid row as a unified object to optimize overhead (FIX #3 & #8)
    if sma_available:
        latest = df_view.dropna(subset=["SMA50", "SMA200"]).iloc[-1]
    else:
        latest = df_view.iloc[-1]
        
    latest_close = latest['Close']
    prev_close = info_payload['prev_close']
    price_change = latest_close - prev_close
    pct_change = (price_change / prev_close) * 100 if prev_close else 0.0
    
    # Top Metrics Banner Layout
    st.subheader(f"🏢 {info_payload['longName']} ({ticker_symbol})")
    st.metric(
        label="Closing Price (USD)",
        value=f"${latest_close:,.2f}",
        delta=f"${price_change:+.2f} ({pct_change:+.2f}%)"
    )

    # --- REGIME ANALYTICAL VECTOR MATRIX (FIX #6 & #8) ---
    st.markdown("---")
    st.subheader("📊 Regime Matrix Evaluation")
    
    latest_rsi = latest['RSI']
    latest_upper_bb = latest['BB_Upper']
    latest_lower_bb = latest['BB_Lower']
    
    signals = {}
    
    # Momentum Core (RSI)
    if latest_rsi > 70:
        signals['RSI'] = {"label": "🔴 Overbought Warning", "score": -1.0}
    elif latest_rsi < 30:
        signals['RSI'] = {"label": "🟢 Oversold Target", "score": 1.0}
    else:
        signals['RSI'] = {"label": "⚪ Neutral Drift", "score": 0.0}
        
    # Volatility Overextensions (Bollinger Bands)
    if latest_close >= latest_upper_bb:
        signals['BB'] = {"label": "🔴 Upper Extension Broken", "score": -1.0}
    elif latest_close <= latest_lower_bb:
        signals['BB'] = {"label": "🟢 Lower Deviation Broken", "score": 1.0}
    else:
        signals['BB'] = {"label": "⚪ Normal Value Band", "score": 0.0}
        
    # Structural Trend State Check (SMA Alignment with Guard)
    if sma_available:
        if latest['SMA50'] > latest['SMA200']:
            signals['SMA'] = {"label": "🟢 Golden Cross Trend", "score": 1.0}
        else:
            signals['SMA'] = {"label": "🔴 Death Cross Trend", "score": -1.0}
    else:
        signals['SMA'] = {"label": "⚪ Insufficient Trend Horizon", "score": 0.0}

    # Execute weighted calculation layers (0.4 / 0.2 / 0.4 consensus split)
    w_rsi, w_bb, w_sma = 0.40, 0.20, 0.40
    macro_score = (signals['RSI']['score'] * w_rsi) + (signals['BB']['score'] * w_bb) + (signals['SMA']['score'] * w_sma)
    
    if macro_score >= 0.4:
        macro_signal, render_box = "🟢 STRONG BULLISH BIAS", st.success
    elif macro_score > 0.1:
        macro_signal, render_box = "🟢 MODERATE BULLISH BIAS", st.success
    elif macro_score < -0.4:
        macro_signal, render_box = "🔴 STRONG BEARISH BIAS", st.error
    elif macro_score < -0.1:
        macro_signal, render_box = "🔴 MODERATE BEARISH BIAS", st.error
    else:
        macro_signal, render_box = "⚪ NEUTRAL CONVERGENCE / HOLD", st.info
        
    render_box(f"### **Weighted Quantitative Model Consensus: {macro_signal}**")

    # Display Breakdown Grid
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("RSI Momentum (14)", f"{latest_rsi:.1f}", signals['RSI']['label'], delta_color="off")
    col_m2.metric("Bollinger Bounds Delta", f"${latest_close:,.2f}", signals['BB']['label'], delta_color="off")
    col_m3.metric("Structural Macro Trend", "200 SMA Layer" if sma_available else "Awaiting Index Data", signals['SMA']['label'], delta_color="off")

    # --- TECHNICAL TIMELINE PLOTS ---
    st.markdown("---")
    st.caption("📈 Technical Studio: Bollinger Bands, Moving Averages, and RSI")
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.7, 0.3])
    
    # SEMANTIC TRACE ORDERING (FIX #5 & #7): Upper added first, lower follows with tonexty fill
    fig.add_trace(go.Scatter(x=df_view.index, y=df_view['BB_Upper'], mode='lines', name='BB Upper (20,2)', line=dict(color='rgba(0, 230, 118, 0.25)', width=1), showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_view.index, y=df_view['BB_Lower'], mode='lines', name='Bollinger Bands (20,2)', line=dict(color='rgba(0, 230, 118, 0.25)', width=1), fill='tonexty', fillcolor='rgba(0, 230, 118, 0.02)'), row=1, col=1)
    
    # Price Line and SMA Overlays drawn on top of the shaded band region
    fig.add_trace(go.Scatter(x=df_view.index, y=df_view['Close'], mode='lines', name='Closing Price', line=dict(color='#1565C0', width=2.5)), row=1, col=1)
    
    if sma_available:
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['SMA50'], mode='lines', name='50-Day SMA', line=dict(color='#FBC02D', width=1.5, dash='dash')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['SMA200'], mode='lines', name='200-Day SMA', line=dict(color='#D32F2F', width=1.5, dash='dot')), row=1, col=1)
    
    # Panel 2: RSI Oscillator Data
    fig.add_trace(go.Scatter(x=df_view.index, y=df_view['RSI'], mode='lines', name='RSI (14)', line=dict(color='#00E676', width=1.5)), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="rgba(211, 47, 47, 0.6)", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="rgba(76, 175, 80, 0.6)", row=2, col=1)

    fig.update_layout(
        height=550,
        margin=dict(l=20, r=20, t=10, b=10),
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=False),
        xaxis2=dict(showgrid=False),
        yaxis=dict(title="Price (USD)", showgrid=True),
        yaxis2=dict(title="RSI (14)", range=[10, 90], showgrid=True)
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error(f"❌ Core Exception: Could not pull market assets for ticker token '{ticker_symbol}'.")
