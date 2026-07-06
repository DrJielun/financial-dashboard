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
ticker_symbol = st.sidebar.text_input("Enter Equity Ticker Symbol:", value="AAPL").upper().strip()

if not ticker_symbol.isalnum():
    st.sidebar.warning("⚠️ Invalid ticker format detected.")
    st.stop()

# --- INSTANT LONG-LIVED COMPREHENSIVE FUNDAMENTALS ENGINE (ZERO RERUN LAG) ---
@st.cache_data(ttl=3600)  # Cached for 1 hour to prevent scraping bottlenecks
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
        
        # Pull analyst target safely
        targets = getattr(t, "analyst_price_targets", {})
        payload["targetPrice"] = targets.get("mean") if isinstance(targets, dict) else None
        
        # Scrape and map the requested operational stats safely
        info = t.info
        if info:
            payload["targetPrice"] = payload["targetPrice"] or info.get("targetMeanPrice")
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
        if history.empty:
            return None, None
            
        fast_payload = {
            "prev_close": history['Close'].iloc[-2] if len(history) > 1 else history['Close'].iloc[-1]
        }
        return history, fast_payload
    except Exception:
        return None, None

# --- LAYER 2: CLOSED METRICS FEATURE ENGINEERING LAYER ---
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
    
    # 4. Math Correct ADX Trend Strength Component
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

    atr = tr.ewm(alpha=1/14, adjust=False).mean()

    plus_di = 100 * (pd.Series(plus_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() / atr.replace(0, np.nan))
    minus_di = 100 * (pd.Series(minus_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() / atr.replace(0, np.nan))

    dx = (abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)) * 100
    df['ADX'] = dx.ewm(alpha=1/14, adjust=False).mean()
    df['ADX'] = df['ADX'].fillna(0)
    
    return df.tail(252)

# --- LAYER 3: LAYOUT MATRIX RENDERING ENGINE ---
with st.spinner("Fetching market data..."):
    raw_history, info_payload = get_raw_market_data(ticker_symbol)

if raw_history is not None and info_payload is not None:
    # Pull long-lived fundamentals without layout stutter
    fnd = fetch_longlived_metadata(ticker_symbol)
    df_view = compute_technical_indicators(raw_history)
    
    # ALWAYS anchor structural signal processing cleanly to the latest row index
    latest = df_view.iloc[-1]
    sma_available = pd.notna(latest["SMA50"]) and pd.notna(latest["SMA200"])
    
    latest_close = latest['Close']
    prev_close = info_payload['prev_close']
    price_change = latest_close - prev_close
    pct_change = (price_change / prev_close) * 100 if prev_close else 0.0
    
    # Divide the template workspace into a dual grid system (Main Chart vs Fundamental Sidebar)
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
        latest_rsi = latest['RSI']
        latest_upper_bb = latest['BB_Upper']
        latest_lower_bb = latest['BB_Lower']
        latest_bandwidth = latest['Vol_Bandwidth']
        latest_adx = latest['ADX']
        
        # Assign Trend Strength Classifications via ADX Regime Gating
        if latest_adx < 20:
            trend_state, adx_score = "⚪ Weak / Choppy Market", -0.2
        elif latest_adx < 40:
            trend_state, adx_score = "🟡 Trending (Moderate)", 1.0
        else:
            trend_state, adx_score = "🟢 Strong Trend", 1.0
            
        signals = {
            "RSI": {"label": "🔴 Overbought Warning" if latest_rsi > 70 else ("🟢 Oversold Target" if latest_rsi < 30 else "⚪ Neutral Drift"), "score": -1.0 if latest_rsi > 70 else (1.0 if latest_rsi < 30 else 0.0)},
            "BB": {"label": "⚪ Volatility Squeeze" if pd.isna(latest_bandwidth) or latest_bandwidth < 0.02 else ("🔴 Upper Bound Broken" if latest_close >= latest_upper_bb else ("🟢 Lower Bound Broken" if latest_close <= latest_lower_bb else "⚪ Normal Band")), "score": 0.0 if pd.isna(latest_bandwidth) or latest_bandwidth < 0.02 else (-1.0 if latest_close >= latest_upper_bb else (1.0 if latest_close <= latest_lower_bb else 0.0))},
            "SMA": {"label": "🟢 Golden Cross" if latest['SMA50'] > latest['SMA200'] else "🔴 Death Cross", "score": 1.0 if latest['SMA50'] > latest['SMA200'] else -1.0} if sma_available else {"label": "⚪ Awaiting Lookback", "score": 0.0},
            "ADX": {"label": trend_state, "score": adx_score}
        }

        # Advanced Multi-Regime Weighted Scoring Matrix
        w_rsi, w_bb, w_sma, w_adx = 0.30, 0.15, 0.35, 0.20
        macro_score = sum(signals[k]["score"] * w for k, w in zip(["RSI", "BB", "SMA", "ADX"], [w_rsi, w_bb, w_sma, w_adx]))
        
        if macro_score >= 0.3: macro_msg, render_box = "🟢 STRONG BULLISH BIAS", st.success
        elif macro_score >= 0.1: macro_msg, render_box = "🟢 MODERATE BULLISH BIAS", st.success
        elif macro_score <= -0.3: macro_msg, render_box = "🔴 STRONG BEARISH BIAS", st.error
        elif macro_score <= -0.1: macro_msg, render_box = "🔴 MODERATE BEARISH BIAS", st.error
        else: macro_msg, render_box = "⚪ NEUTRAL CONVERGENCE / HOLD", st.info
            
        render_box(f"#### **Weighted Technical Signal Consensus: {macro_msg}**")

        # Display Tech Signals
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("RSI Momentum (14)", f"{latest_rsi:.1f}", signals['RSI']['label'], delta_color="off")
        col_m2.metric("Bollinger Bounds", f"${latest_close:,.2f}", signals['BB']['label'], delta_color="off")
        col_m3, col_m4 = st.columns(2)
        col_m3.metric("Macro Trend Alignment", "200 SMA Status", signals['SMA']['label'], delta_color="off")
        col_m4.metric("Trend Strength (ADX)", f"{latest_adx:.1f}", signals['ADX']['label'], delta_color="off")

        # --- TECHNICAL VISUALIZATION PANELS ---
        st.markdown("---")
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.7, 0.3])
        
        # Upper trace added first, lower trace with tonexty fill added second to anchor boundaries cleanly
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['BB_Upper'], mode='lines', line=dict(color='rgba(0, 230, 118, 0.25)', width=1), showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['BB_Lower'], mode='lines', line=dict(color='rgba(0, 230, 118, 0.25)', width=1), fill='tonexty', fillcolor='rgba(0, 230, 118, 0.02)', name='Bollinger Bands (20,2)'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['Close'], mode='lines', name='Closing Price', line=dict(color='#1565C0', width=2.5)), row=1, col=1)
        
        if sma_available:
            fig.add_trace(go.Scatter(x=df_view.index, y=df_view['SMA50'], mode='lines', name='50-Day SMA', line=dict(color='#FBC02D', width=1.5, dash='dash')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_view.index, y=df_view['SMA200'], mode='lines', name='200-Day SMA', line=dict(color='#D32F2F', width=1.5, dash='dot')), row=1, col=1)
        if fnd["targetPrice"]:
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

        # 1. Valuation
        st.markdown("#### **Valuation**")
        st.markdown(f"**Trailing P/E:** `{fmt_v(fnd['pe_trailing'])}`")
        st.markdown(f"**Forward P/E:** `{fmt_v(fnd['pe_forward'])}`")
        st.markdown(f"**PEG Ratio:** `{fmt_v(fnd['peg'])}`")
        st.markdown(f"**Price to Book:** `{fmt_v(fnd['pb'])}`")
        
        # 2. Profitability
        st.markdown("---")
        st.markdown("#### **Profitability**")
        st.markdown(f"**Return on Equity (ROE):** `{fmt_v(fnd['roe'], 'pct')}`")
        st.markdown(f"**Net Profit Margin:** `{fmt_v(fnd['net_margin'], 'pct')}`")
        st.markdown(f"**Operating Margin:** `{fmt_v(fnd['op_margin'], 'pct')}`")
        
        # 3. Growth
        st.markdown("---")
        st.markdown("#### **Growth (YoY)**")
        st.markdown(f"**Earnings Growth:** `{fmt_v(fnd['eps_growth'], 'pct')}`")
        st.markdown(f"**Revenue Growth:** `{fmt_v(fnd['rev_growth'], 'pct')}`")
        
        # 4. Financial Strength (Harden Type-Safe Check)
        st.markdown("---")
        st.markdown("#### **Financial Strength**")
        
        de_val = fnd['debt_equity']
        if pd.notna(de_val):
            # Scale percentages safely depending on ledger presentation
            de_str = f"{de_val:.2f}%" if de_val > 5.0 else f"{de_val * 100:.2f}%"
        else:
            de_str = "N/A"
            
        st.markdown(f"**Debt to Equity:** `{de_str}`")
        st.markdown(f"**Current Ratio:** `{fmt_v(fnd['current_ratio'])}`")
else:
    st.error(f"❌ Core Exception: Could not pull market assets for ticker token '{ticker_symbol}'.")
