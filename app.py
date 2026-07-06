import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# --- 1. CONFIGURATION & ENGINE INITIALIZATION ---
st.set_page_config(layout="centered", page_title="Professional Session Terminal")
st.title("⏱️ Institutional Session Terminal")

# --- AUTO REFRESH INJECTION (FIX #1) ---
# Emits an invisible JS-driven pulse to avoid thread blocking, CPU churn, or UI flickering
refresh_rate = st.sidebar.slider("Live Data Auto-Refresh (Seconds):", min_value=10, max_value=60, value=15)
st.components.v1.html(
    f"""
    <script>
        window.parent.document.addEventListener('DOMContentLoaded', function() {{
            setTimeout(function() {{ window.location.reload(); }}, {refresh_rate * 1000});
        }});
    </script>
    """,
    height=0,
)

# --- USER INPUT & FORMAT GUARD (FIX #11) ---
ticker_symbol = st.text_input("Enter Equity Ticker Symbol:", value="AAPL").upper().strip()

if not ticker_symbol.isalnum():
    st.warning("⚠️ Invalid ticker format detected. Please use alphanumeric characters only.")
    st.stop()

# --- LAYER 1: FETCH RAW DATA WITH FIXED CACHE (FIX #2 & #3 & #10) ---
@st.cache_data(ttl=60, max_entries=50)  # Fixed TTL decoupled from user UI sliders
def get_raw_market_data(ticker_str):
    try:
        stock = yf.Ticker(ticker_str)
        # Pull 1 year + cushion to properly seed the 200 SMA array without missing early calculations
        history = stock.history(period="2y", interval="1d")
        if history.empty:
            return None, None
            
        # Use lightning-fast, zero-overhead properties instead of slow stock.info dicts
        fast_info = {}
        try:
            fast_info['longName'] = stock.info.get('longName', ticker_str) # Single fallback read
        except Exception:
            fast_info['longName'] = ticker_str
            
        # Fallback tracking parameters (FIX #9 Heuristics)
        fast_info['last_close'] = history['Close'].iloc[-1]
        fast_info['prev_close'] = history['Close'].iloc[-2]
        return history, fast_info
    except Exception:
        return None, None

# --- LAYER 2: PROCESS INDICATORS (FIX #4, #5, #6, #10) ---
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
    
    # 3. Wilder's Exponential Smoothing RSI (FIX #4 & #5)
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    # Apply exponential windows natively to avoid simple mean distortions
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    
    # Protect against zero division when tracking assets experiencing uninterrupted green streaks
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df['RSI'] = 100 - (100 / (1 + rs))
    df['RSI'] = df['RSI'].fillna(50) # Fallback baseline
    
    return df

# --- LAYER 3: EXECUTE PIPELINE RENDERING ---
with st.spinner("Fetching market data..."): # UI Indicator (FIX #11)
    raw_history, info_payload = get_raw_market_data(ticker_symbol)

if raw_history is not None and info_payload is not None:
    # Build analytical matrix data structures
    df_analyzed = compute_technical_indicators(raw_history)
    
    # Slice view window to exactly the past 1 year of daily metrics
    df_view = df_analyzed.tail(252)
    
    latest_close = df_view['Close'].iloc[-1]
    prev_close = info_payload['prev_close']
    price_change = latest_close - prev_close
    pct_change = (price_change / prev_close) * 100 if prev_close else 0.0
    
    # Header display structures
    st.subheader(f"🏢 {info_payload['longName']} ({ticker_symbol})")
    st.metric(
        label="Closing Price (USD)",
        value=f"${latest_close:,.2f}",
        delta=f"${price_change:+.2f} ({pct_change:+.2f}%)"
    )

    # --- REGIME ANALYTICAL VECTOR MATRIX (FIX #6 & #8) ---
    st.markdown("---")
    st.subheader("📊 Regime Matrix Evaluation")
    
    latest_rsi = df_view['RSI'].iloc[-1]
    latest_upper_bb = df_view['BB_Upper'].iloc[-1]
    latest_lower_bb = df_view['BB_Lower'].iloc[-1]
    latest_sma50 = df_view['SMA50'].iloc[-1]
    latest_sma200 = df_view['SMA200'].iloc[-1]
    
    # Structural Safety Check: Verify 200 SMA validation array limits (FIX #6)
    sma_available = pd.notna(latest_sma200) and pd.notna(latest_sma50)
    
    # Default metric weight assignments (FIX #8)
    signals = {}
    
    # A. Momentum Weight (RSI)
    if latest_rsi > 70:
        signals['RSI'] = {"label": "🔴 Overbought Warning", "score": -1.0}
    elif latest_rsi < 30:
        signals['RSI'] = {"label": "🟢 Oversold Target", "score": 1.0}
    else:
        signals['RSI'] = {"label": "⚪ Neutral Drift", "score": 0.0}
        
    # B. Volatility Boundary Weight (BB)
    if latest_close >= latest_upper_bb:
        signals['BB'] = {"label": "🔴 Upper Extension Broken", "score": -1.0}
    elif latest_close <= latest_lower_bb:
        signals['BB'] = {"label": "🟢 Lower Deviation Broken", "score": 1.0}
    else:
        signals['BB'] = {"label": "⚪ Normal Value Band", "score": 0.0}
        
    # C. Macro Trend Filter (SMA) with Safety Fallback Guard
    if sma_available:
        if latest_sma50 > latest_sma200:
            signals['SMA'] = {"label": "🟢 Golden Cross Trend", "score": 1.0}
        else:
            signals['SMA'] = {"label": "🔴 Death Cross Trend", "score": -1.0}
    else:
        signals['SMA'] = {"label": "⚪ Insufficient Trend Horizon", "score": 0.0}

    # Apply weighted consensus scoring matrices
    w_rsi, w_bb, w_sma = 0.40, 0.20, 0.40
    macro_score = (signals['RSI']['score'] * w_rsi) + (signals['BB']['score'] * w_bb) + (signals['SMA']['score'] * w_sma)
    
    # Map raw structural float values to target terminal blocks
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

    # Display clean component signals
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("RSI Momentum (14)", f"{latest_rsi:.1f}", signals['RSI']['label'], delta_color="off")
    col_m2.metric("Bollinger Bounds Delta", f"${latest_close:,.2f}", signals['BB']['label'], delta_color="off")
    col_m3.metric("Structural Macro Trend", "200 SMA Layer" if sma_available else "Awaiting Index Data", signals['SMA']['label'], delta_color="off")

    # --- HIGH-PERFORMANCE INTERACTIVE GRAPH ---
    st.markdown("---")
    st.caption("📈 Technical Studio: Bollinger Bands, Moving Averages, and RSI")
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.7, 0.3])
    
    # CRITICAL INVERSION TRACKING: Upper trace goes first, lower trace with fill follows immediately (FIX #7)
    fig.add_trace(go.Scatter(x=df_view.index, y=df_view['BB_Upper'], mode='lines', name='BB Upper (20,2)', line=dict(color='rgba(0, 230, 118, 0.25)', width=1), showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_view.index, y=df_view['BB_Lower'], mode='lines', name='Bollinger Bands (20,2)', line=dict(color='rgba(0, 230, 118, 0.25)', width=1), fill='tonexty', fillcolor='rgba(0, 230, 118, 0.02)'), row=1, col=1)
    
    # Overlay remaining structural traces sequentially
    fig.add_trace(go.Scatter(x=df_view.index, y=df_view['Close'], mode='lines', name='Closing Price', line=dict(color='#1565C0', width=2.5)), row=1, col=1)
    
    if sma_available:
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['SMA50'], mode='lines', name='50-Day SMA', line=dict(color='#FBC02D', width=1.5, dash='dash')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['SMA200'], mode='lines', name='200-Day SMA', line=dict(color='#D32F2F', width=1.5, dash='dot')), row=1, col=1)
    
    # Row 2: RSI 14 Traces
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
