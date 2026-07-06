import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
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
@st.cache_data(ttl=refresh_rate)  # Protects your IP from API rate-throttling
def fetch_terminal_market_data(ticker_str):
    try:
        stock = yf.Ticker(ticker_str)
        info = stock.info
        # Pull 5 days of 15-minute interval bars to keep response speeds fast
        history = stock.history(period="5d", interval="15m")
        
        if not info or history.empty:
            return None, None
        return info, history
    except Exception:
        return None, None

# Execute network fetch
if ticker_symbol:
    info_payload, df_history = fetch_terminal_market_data(ticker_symbol)
    
    if info_payload and df_history is not None:
        # 1. PARSE CORE FINANCIAL METADATA
        company_name = info_payload.get("longName", ticker_symbol)
        market_state = info_payload.get("marketState", "UNKNOWN")
        currency = info_payload.get("currency", "USD")
        
        regular_close = info_payload.get("regularMarketPrice") or df_history['Close'].iloc[-1]
        prev_close = info_payload.get("previousClose") or regular_close
        
        st.subheader(f"🏢 {company_name} ({ticker_symbol})")
        
        # 2. RUN REAL-TIME SESSION LOGIC COUPLING
        if market_state == "PRE":
            ext_price = info_payload.get("preMarketPrice") or regular_close
            change = ext_price - regular_close
            pct_change = (change / regular_close) * 100 if regular_close else 0.0
            
            st.warning(f"🌅 SESSION ACTIVE: PRE-MARKET")
            st.metric(
                label=f"Pre-Market Valuation ({currency})",
                value=f"${ext_price:,.2f}",
                delta=f"${change:+.2f} ({pct_change:+.2f}%) vs Regular Close"
            )
            
        elif market_state == "POST":
            ext_price = info_payload.get("postMarketPrice") or regular_close
            change = ext_price - regular_close
            pct_change = (change / regular_close) * 100 if regular_close else 0.0
            
            st.info(f"🌙 SESSION ACTIVE: POST-MARKET")
            st.metric(
                label=f"Post-Market Valuation ({currency})",
                value=f"${ext_price:,.2f}",
                delta=f"${change:+.2f} ({pct_change:+.2f}%) vs Regular Close"
            )
            
        elif market_state == "REGULAR":
            current_live = info_payload.get("currentPrice") or regular_close
            change = current_live - prev_close
            pct_change = (change / prev_close) * 100 if prev_close else 0.0
            
            st.success(f"🟢 SESSION ACTIVE: REGULAR MARKET (OPEN)")
            st.metric(
                label=f"Live Trading Price ({currency})",
                value=f"${current_live:,.2f}",
                delta=f"${change:+.2f} ({pct_change:+.2f}%) vs Yesterday Close"
            )
            
        else:  # Standard CLOSED or UNKNOWN Fallbacks
            final_price = info_payload.get("postMarketPrice") or regular_close
            change = final_price - prev_close
            pct_change = (change / prev_close) * 100 if prev_close else 0.0
            
            st.error(f"🛑 SESSION ACTIVE: MARKET CLOSED")
            st.metric(
                label=f"Final Closing Price ({currency})",
                value=f"${final_price:,.2f}",
                delta=f"${change:+.2f} ({pct_change:+.2f}%) Daily Session Net Change"
            )

        # 3. HIGH-PERFORMANCE INTERACTIVE GRAPH
        st.markdown("---")
        st.caption("📈 Historical Session Intraday Performance Trend")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_history.index, 
            y=df_history['Close'], 
            mode='lines',
            line=dict(color='#1565C0', width=2),
            fill='tozeroy',
            fillcolor='rgba(21, 101, 192, 0.1)'
        ))
        fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=10, b=10),
            template="plotly_dark",
            xaxis=dict(showgrid=False),
            yaxis=dict(title=f"Price ({currency})", showgrid=True)
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
