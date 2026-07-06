import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import time

# --- INITIAL APP ENVIRONMENT SETUP ---
st.set_page_config(layout="centered", page_title="Professional Session Terminal")
st.title("⏱️ Institutional Session Terminal")

# --- SIDEBAR INTERFACE CONTROL PANEL ---
st.sidebar.header("Terminal Configurations")
refresh_rate = st.sidebar.slider("Live Data Auto-Refresh (Seconds):", min_value=5, max_value=60, value=15)
st.sidebar.caption(f"🔄 Data fetching pipeline cycles every {refresh_rate}s automatically.")

# --- USER TICKER INPUT ENGINE ---
ticker_symbol = st.text_input("Enter Equity Ticker Symbol:", value="AAPL").upper().strip()

# --- SERVER-SAFE MARKET DATA ENGINE ---
@st.cache_data(ttl=refresh_rate)
def fetch_terminal_market_data(ticker_str):
    try:
        stock = yf.Ticker(ticker_str)
        info = stock.info
        
        # Pull 1 year of daily historical bars to build rolling calculations
        history = stock.history(period="1y", interval="1d")
        
        if not info or history.empty:
            return None, None
            
        # 1. Moving Averages
        history['SMA50'] = history['Close'].rolling(window=50).mean()
        history['SMA200'] = history['Close'].rolling(window=200).mean()
        
        # 2. Bollinger Bands (20, 2)
        history['MA20'] = history['Close'].rolling(window=20).mean()
        history['Std20'] = history['Close'].rolling(window=20).std()
        history['BB_Upper'] = history['MA20'] + (2 * history['Std20'])
        history['BB_Lower'] = history['MA20'] - (2 * history['Std20'])
        
        # 3. Relative Strength Index (RSI 14)
        delta = history['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        history['RSI'] = 100 - (100 / (1 + rs))
        
        return info, history
    except Exception:
        return None, None

# Execute network fetch
if ticker_symbol:
    info_payload, df_history = fetch_terminal_market_data(ticker_symbol)
    
    if info_payload and df_history is not None:
        # --- PARSE CORE FINANCIAL METADATA ---
        company_name = info_payload.get("longName", ticker_symbol)
        market_state = info_payload.get("marketState", "UNKNOWN")
        currency = info_payload.get("currency", "USD")
        
        regular_close = info_payload.get("regularMarketPrice") or df_history['Close'].iloc[-1]
        prev_close = info_payload.get("previousClose") or regular_close
        
        st.subheader(f"🏢 {company_name} ({ticker_symbol})")
        
        # --- RUN REAL-TIME SESSION LOGIC COUPLING ---
        if market_state == "PRE":
            ext_price = info_payload.get("preMarketPrice") or regular_close
            change = ext_price - regular_close
            pct_change = (change / regular_close) * 100 if regular_close else 0.0
            
            st.warning(f"🌅 SESSION ACTIVE: PRE-MARKET")
            st.metric(label=f"Pre-Market Valuation ({currency})", value=f"${ext_price:,.2f}", delta=f"${change:+.2f} ({pct_change:+.2f}%) vs Regular Close")
            
        elif market_state == "POST":
            ext_price = info_payload.get("postMarketPrice") or regular_close
            change = ext_price - regular_close
            pct_change = (change / regular_close) * 100 if regular_close else 0.0
            
            st.info(f"🌙 SESSION ACTIVE: POST-MARKET")
            st.metric(label=f"Post-Market Valuation ({currency})", value=f"${ext_price:,.2f}", delta=f"${change:+.2f} ({pct_change:+.2f}%) vs Regular Close")
            
        elif market_state == "REGULAR":
            current_live = info_payload.get("currentPrice") or regular_close
            change = current_live - prev_close
            pct_change = (change / prev_close) * 100 if prev_close else 0.0
            
            st.success(f"🟢 SESSION ACTIVE: REGULAR MARKET (OPEN)")
            st.metric(label=f"Live Trading Price ({currency})", value=f"${current_live:,.2f}", delta=f"${change:+.2f} ({pct_change:+.2f}%) vs Yesterday Close")
            
        else:
            final_price = info_payload.get("postMarketPrice") or regular_close
            change = final_price - prev_close
            pct_change = (change / prev_close) * 100 if prev_close else 0.0
            
            st.error(f"🛑 SESSION ACTIVE: MARKET CLOSED")
            st.metric(label=f"Final Closing Price ({currency})", value=f"${final_price:,.2f}", delta=f"${change:+.2f} ({pct_change:+.2f}%) Daily Session Net Change")

        # --- HIGH-PERFORMANCE INTERACTIVE GRAPH ---
        st.markdown("---")
        st.caption("📈 Technical Studio: Bollinger Bands, Moving Averages, and RSI")
        
        # Build 2-row subplot setup (Row 1: Price Actions + Overlays, Row 2: RSI Oscillator)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.7, 0.3])
        
        # --- ROW 1: CORE PRICE ACTION + OVERLAYS ---
        # Closing Price
        fig.add_trace(go.Scatter(x=df_history.index, y=df_history['Close'], mode='lines', name='Closing Price', line=dict(color='#1565C0', width=2)), row=1, col=1)
        # SMA 50
        fig.add_trace(go.Scatter(x=df_history.index, y=df_history['SMA50'], mode='lines', name='50-Day SMA', line=dict(color='#FBC02D', width=1.5, dash='dash')), row=1, col=1)
        # SMA 200
        fig.add_trace(go.Scatter(x=df_history.index, y=df_history['SMA200'], mode='lines', name='200-Day SMA', line=dict(color='#D32F2F', width=1.5, dash='dot')), row=1, col=1)
        # Bollinger Upper Band
        fig.add_trace(go.Scatter(x=df_history.index, y=df_history['BB_Upper'], mode='lines', name='BB Upper (20,2)', line=dict(color='rgba(255, 255, 255, 0.3)', width=1)), row=1, col=1)
        # Bollinger Lower Band
        fig.add_trace(go.Scatter(x=df_history.index, y=df_history['BB_Lower'], mode='lines', name='BB Lower (20,2)', line=dict(color='rgba(255, 255, 255, 0.3)', width=1), fill='tonexty', fillcolor='rgba(255, 255, 255, 0.02)'), row=1, col=1)
        
        # --- ROW 2: RSI 14 OSCILLATOR ---
        # RSI Trace
        fig.add_trace(go.Scatter(x=df_history.index, y=df_history['RSI'], mode='lines', name='RSI (14)', line=dict(color='#00E676', width=1.5)), row=2, col=1)
        # Technical Indicator Boundary Markers (30/70 thresholds)
        fig.add_hline(y=70, line_dash="dash", line_color="rgba(211, 47, 47, 0.6)", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="rgba(76, 175, 80, 0.6)", row=2, col=1)

        # Style layout environments
        fig.update_layout(
            height=550,
            margin=dict(l=20, r=20, t=10, b=10),
            template="plotly_dark",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(showgrid=False),
            xaxis2=dict(showgrid=False),
            yaxis=dict(title=f"Price ({currency})", showgrid=True),
            yaxis2=dict(title="RSI (14)", range=[10, 90], showgrid=True)
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.error(f"❌ Could not map assets for symbol '{ticker_symbol}'. Please verify spelling constructs.")

# --- ASYNC REFRESH LOOP EXECUTION ---
@st.fragment
def loop_refresh_anchor():
    time.sleep(refresh_rate)
    st.rerun()

loop_refresh_anchor()
