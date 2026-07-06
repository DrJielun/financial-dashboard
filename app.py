import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# --- 1. CONFIGURATION & ENGINE INITIALIZATION ---
st.set_page_config(layout="centered", page_title="Professional Session Terminal")
st.title("⏱️ Institutional Session Terminal")

# --- NATIVE STABLE AUTO-REFRESH INJECTION ---
refresh_rate = st.sidebar.slider("Live Data Auto-Refresh (Seconds):", min_value=10, max_value=60, value=15)

st.components.v1.html(
    f"""
    <meta http-equiv="refresh" content="{refresh_rate}">
    <script>
        window.setTimeout(function() {{
            window.location.reload();
        }}, {refresh_rate * 1000});
    </script>
    """,
    height=0,
)

# --- USER INPUT & FORMAT GUARD ---
ticker_symbol = st.text_input("Enter Equity Ticker Symbol:", value="AAPL").upper().strip()

if not ticker_symbol.isalnum():
    st.warning("⚠️ Invalid ticker format detected. Please use alphanumeric characters only.")
    st.stop()

# --- HARDENED PROFILE NAME CACHE (FIX #1 - REMOVED SLOW .INFO SCRAPER) ---
@st.cache_data(ttl=3600)
def get_company_name(ticker_str):
    try:
        t = yf.Ticker(ticker_str)
        # Bypasses the slow scraping mechanics of the main payload engine
        return t.fast_info.get("shortName", ticker_str)
    except Exception:
        return ticker_str

# --- LAYER 1: RAW DATA INGESTION ENGINE ---
@st.cache_data(ttl=60, max_entries=50)
def get_raw_market_data(ticker_str):
    try:
        stock = yf.Ticker(ticker_str)
        # Pull 2 years to cleanly seed rolling 200 SMA and ADX lookbacks without early drops
        history = stock.history(period="2y", interval="1d")
        if history.empty:
            return None, None
            
        fast_payload = {
            "prev_close": history['Close'].iloc[-2] if len(history) > 1 else history['Close'].iloc[-1]
        }
        return history, fast_payload
    except Exception:
        return None, None

# --- LAYER 2: CLOSED METRICS FEATURE ENGINEERING LAYER (FIX #2 - ADX INCORPORATED) ---
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
    df['Vol_Bandwidth'] = (df['BB_Upper'] - df['BB_Lower']) / df['MA20']
    
    # 3. Wilder's Exponential Smoothing RSI
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df['RSI'] = 100 - (100 / (1 + rs))
    df['RSI'] = df['RSI'].fillna(50)
    
    # 4. Math Correct ADX Trend Strength Component (FIX #2)
    high = df['High']
    low = df['Low']
    close = df['Close']

    plus_dm = high.diff()
    minus_dm = low.diff().abs()

    plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0.0)
    minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0.0)

    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Use Wilder's EMA smoothing technique to match real analytical outputs
    atr = tr.ewm(alpha=1/14, adjust=False).mean()

    plus_di = 100 * (pd.Series(plus_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() / atr.replace(0, np.nan))
    minus_di = 100 * (pd.Series(minus_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() / atr.replace(0, np.nan))

    dx = (abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)) * 100
    df['ADX'] = dx.ewm(alpha=1/14, adjust=False).mean()
    df['ADX'] = df['ADX'].fillna(0) # Ingest baseline placeholder for warmup items
    
    # Returns complete dataframe inside cache boundaries
    return df.tail(252)

# --- LAYER 3: LAYOUT MATRIX RENDERING ENGINE ---
with st.spinner("Fetching market data..."):
    raw_history, info_payload = get_raw_market_data(ticker_symbol)

if raw_history is not None and info_payload is not None:
    company_name = get_company_name(ticker_symbol)
    df_view = compute_technical_indicators(raw_history)
    
    # ALWAYS anchor structural signal processing cleanly to the latest row index
    latest = df_view.iloc[-1]
    sma_available = pd.notna(latest["SMA50"]) and pd.notna(latest["SMA200"])
    
    latest_close = latest['Close']
    prev_close = info_payload['prev_close']
    price_change = latest_close - prev_close
    pct_change = (price_change / prev_close) * 100 if prev_close else 0.0
    
    # Primary Metrics Presentation Header
    st.subheader(f"🏢 {company_name} ({ticker_symbol})")
    st.metric(
        label="Closing Price (USD)",
        value=f"${latest_close:,.2f}",
        delta=f"${price_change:+.2f} ({pct_change:+.2f}%)"
    )

    # --- REGIME ANALYTICAL VECTOR MATRIX (FIX #3 & #4) ---
    st.markdown("---")
    st.subheader("📊 Regime Matrix Evaluation")
    
    latest_rsi = latest['RSI']
    latest_upper_bb = latest['BB_Upper']
    latest_lower_bb = latest['BB_Lower']
    latest_bandwidth = latest['Vol_Bandwidth']
    latest_adx = latest['ADX']
    
    # Assign Trend Strength Classifications (FIX #3)
    if latest_adx < 20:
        trend_state = "⚪ Weak / Choppy Market"
        adx_score = -0.2  # Penalize raw scores if the stock is trending sideways
    elif latest_adx < 40:
        trend_state = "🟡 Trending (Moderate)"
        adx_score = 1.0   # Confirm trending environment
    else:
        trend_state = "🟢 Strong Trend"
        adx_score = 1.0
        
    signals = {}
    
    # A. Momentum (RSI)
    if latest_rsi > 70:
        signals['RSI'] = {"label": "🔴 Overbought Warning", "score": -1.0}
    elif latest_rsi < 30:
        signals['RSI'] = {"label": "🟢 Oversold Target", "score": 1.0}
    else:
        signals['RSI'] = {"label": "⚪ Neutral Drift", "score": 0.0}
        
    # B. Volatility (Bollinger Bands with Collapse Filter)
    if pd.isna(latest_bandwidth) or latest_bandwidth < 0.02:
        signals['BB'] = {"label": "⚪ Volatility Squeeze (Bands Inhibited)", "score": 0.0}
    elif latest_close >= latest_upper_bb:
        signals['BB'] = {"label": "🔴 Upper Extension Broken", "score": -1.0}
    elif latest_close <= latest_lower_bb:
        signals['BB'] = {"label": "🟢 Lower Deviation Broken", "score": 1.0}
    else:
        signals['BB'] = {"label": "⚪ Normal Value Band", "score": 0.0}
        
    # C. Macro Trend Structure (SMA)
    if sma_available:
        if latest['SMA50'] > latest['SMA200']:
            signals['SMA'] = {"label": "🟢 Golden Cross Trend", "score": 1.0}
        else:
            signals['SMA'] = {"label": "🔴 Death Cross Trend", "score": -1.0}
    else:
        signals['SMA'] = {"label": "⚪ Insufficient Trend Horizon", "score": 0.0}
        
    # D. Regime Strength Validation Vector (FIX #4)
    signals['ADX'] = {"label": trend_state, "score": adx_score}

    # Advanced Multi-Regime Weighted Scoring Breakdown Matrix (FIX #4)
    w_rsi, w_bb, w_sma, w_adx = 0.30, 0.15, 0.35, 0.20
    macro_score = (
        (signals['RSI']['score'] * w_rsi) + 
        (signals['BB']['score'] * w_bb) + 
        (signals['SMA']['score'] * w_sma) + 
        (signals['ADX']['score'] * w_adx)
    )
    
    # Symmetrical Consensus Scoring Intervals
    if macro_score >= 0.3:
        macro_signal, render_box = "🟢 STRONG BULLISH BIAS", st.success
    elif macro_score >= 0.1:
        macro_signal, render_box = "🟢 MODERATE BULLISH BIAS", st.success
    elif macro_score <= -0.3:
        macro_signal, render_box = "🔴 STRONG BEARISH BIAS", st.error
    elif macro_score <= -0.1:
        macro_signal, render_box = "🔴 MODERATE BEARISH BIAS", st.error
    else:
        macro_signal, render_box = "⚪ NEUTRAL CONVERGENCE / HOLD", st.info
        
    render_box(f"### **Weighted Quantitative Model Consensus: {macro_signal}**")

    # Display Component Metrics
    col_m1, col_m2 = st.columns(2)
    col_m1.metric("RSI Momentum (14)", f"{latest_rsi:.1f}", signals['RSI']['label'], delta_color="off")
    col_m2.metric("Bollinger Bounds Delta", f"${latest_close:,.2f}", signals['BB']['label'], delta_color="off")
    
    col_m3, col_m4 = st.columns(2)
    col_m3.metric("Structural Macro Trend", "200 SMA Active" if sma_available else "Awaiting Index Data", signals['SMA']['label'], delta_color="off")
    col_m4.metric("Trend Strength (ADX)", f"{latest_adx:.1f}", signals['ADX']['label'], delta_color="off")

    # --- TECHNICAL WORKSPACE PANEL GRAPHIC RENDERING ---
    st.markdown("---")
    st.caption("📈 Technical Studio: Bollinger Bands, Moving Averages, and RSI")
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.7, 0.3])
    
    # Semantic ordering: Bollinger Fills added first to establish background layers
    fig.add_trace(go.Scatter(x=df_view.index, y=df_view['BB_Upper'], mode='lines', name='BB Upper (20,2)', line=dict(color='rgba(0, 230, 118, 0.25)', width=1), showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_view.index, y=df_view['BB_Lower'], mode='lines', name='Bollinger Bands (20,2)', line=dict(color='rgba(0, 230, 118, 0.25)', width=1), fill='tonexty', fillcolor='rgba(0, 230, 118, 0.02)'), row=1, col=1)
    
    # Overlay individual closing price data lines over background bounds
    fig.add_trace(go.Scatter(x=df_view.index, y=df_view['Close'], mode='lines', name='Closing Price', line=dict(color='#1565C0', width=2.5)), row=1, col=1)
    
    if sma_available:
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['SMA50'], mode='lines', name='50-Day SMA', line=dict(color='#FBC02D', width=1.5, dash='dash')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['SMA200'], mode='lines', name='200-Day SMA', line=dict(color='#D32F2F', width=1.5, dash='dot')), row=1, col=1)
    
    # Row 2 Panel: RSI 14 Traces
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
