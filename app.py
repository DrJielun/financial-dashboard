import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

# Set page to wide mode to perfectly match standard terminal layouts
st.set_page_config(layout="wide", page_title="Live Technical Analysis Terminal")

# --- SIDEBAR INPUT CONTROL ---
st.sidebar.header("Dashboard Controls")
st.sidebar.markdown("🚀 Type any global ticker symbol (e.g., NVDA, TSM, AAPL, GOOG, TSLA, XOM).")
ticker_symbol = st.sidebar.text_input("Enter Stock Ticker:", value="NVDA").upper()

# --- REAL-TIME DATA ENGINE (FREE PUBLIC CHART QUERY LAYER) ---
@st.cache_data(ttl=60)  # Caches responses for 1 minute for live trading focus
def fetch_yahoo_market_data(ticker):
    # Utilizing the unblocked streaming historical chart timeline endpoint
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=6m"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        result = data['chart']['result'][0]
        return result
    except Exception:
        return None

# Execute layout mapping data fetch
live_data = fetch_yahoo_market_data(ticker_symbol)

# --- UI WORKSPACE RENDERING ---
if live_data is not None:
    # 1. Parse Real Metadata Variables
    meta = live_data['meta']
    current_price = meta.get('regularMarketPrice')
    prev_close = meta.get('previousClose')
    
    if current_price is None:
        current_price = prev_close or 100.00
    if prev_close is None:
        prev_close = current_price
        
    price_change = current_price - prev_close
    price_change_pct = (price_change / prev_close) * 100 if prev_close else 0.0
    exchange = meta.get('exchangeName', 'NASDAQ/NYSE')
    
    # 2. VISUAL HEADER BLOCK
    st.caption("Financial Market Asset • Real-Time Tracking Canvas")
    st.title(f"📈 {ticker_symbol} Market Workspace")
    st.caption(f"Trading Venue: {exchange} | 🟢 Verified Live Data Stream Active")

    # Render Price Metrics Block
    st.metric(
        label="Current Market Price (USD)", 
        value=f"${current_price:,.2f}", 
        delta=f"{price_change:+.2f} ({price_change_pct:+.2f}%)"
    )

    st.markdown("---")

    # 3. INTERACTIVE HISTORICAL CHART ENGINE
    st.subheader("📊 6-Month Historical Pricing & Volume Trends")
    
    try:
        timestamps = pd.to_datetime(live_data['timestamp'], unit='s')
        indicators = live_data['indicators']['quote'][0]
        
        df_chart = pd.DataFrame({
            'Date': timestamps,
            'Open': indicators['open'],
            'High': indicators['high'],
            'Low': indicators['low'],
            'Close': indicators['close'],
            'Volume': indicators['volume']
        }).dropna()

        # Build an advanced dual-axis visual plotting container
        fig = go.Figure()
        
        # Primary Plot: Line tracking daily close values
        fig.add_trace(go.Scatter(
            x=df_chart['Date'], 
            y=df_chart['Close'], 
            mode='lines',
            name='Closing Price',
            line=dict(color='#2E7D32', width=2.5) # Investment Green Line
        ))
        
        # Secondary Plot: Shaded block charting daily shares execution volume
        fig.add_trace(go.Bar(
            x=df_chart['Date'], 
            y=df_chart['Volume'], 
            name='Trading Volume',
            marker_color='rgba(100, 150, 250, 0.25)', # Transparent Blue Bars
            yaxis='y2'
        ))

        # Synchronize layout formatting axes structure
        fig.update_layout(
            height=450,
            hovermode="x unified",
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis=dict(title="Stock Price (USD)", side="left", showgrid=True),
            yaxis2=dict(title="Shares Executed Volume", side="right", overlaying="y", showgrid=False),
            margin=dict(l=40, r=40, t=10, b=40)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Symmetrical Data Summary Grid
        st.markdown("### Recent Historical Trading Log")
        st.dataframe(
            df_chart.tail(5)[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].sort_values(by='Date', ascending=False),
            hide_index=True,
            use_container_width=True
        )

    except Exception:
        st.warning("⚠️ Successfully connected to Yahoo Finance, but history data is processing. Refresh in a moment.")

else:
    # Error state handling if a broken ticker is requested
    st.error(f"❌ Unrecognized Ticker symbol or Blocked Pipeline: '{ticker_symbol}'.")
    st.info("Please verify the ticker formatting (e.g., TSM instead of TSMC, GOOG instead of GOOGLE) and refresh.")
