import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

# Set wide page layout to mimic the dashboard structure
st.set_page_config(layout="wide")

# 1. Fetch Data using yfinance
ticker_symbol = "XOM"
ticker = yf.Ticker(ticker_symbol)
info = ticker.info

# Extract current price and change details
history = ticker.history(period="1d")
current_price = info.get("currentPrice", 0.0)
previous_close = info.get("previousClose", 1.0)
price_change = current_price - previous_close
price_change_pct = (price_change / previous_close) * 100

# --- HEADER SECTION ---
st.caption(f"{info.get('sector', 'N/A')}  •  {info.get('industry', 'N/A')}")
st.title(f"({ticker_symbol}) {info.get('longName', 'Company Name')}")
st.caption(f"{info.get('exchange', 'NYSE')}")

# Price & Moat tags
col_header1, col_header2 = st.columns([1, 4])
with col_header1:
    st.metric(
        label="Current Price (USD)", 
        value=f"{current_price:.2f}", 
        delta=f"{price_change:.2f} ({price_change_pct:.2f}%)"
    )
with col_header2:
    st.markdown("`Narrow Moat` `OracleValue™: 101.07`")
    st.caption("Next Earnings Date: 24 Oct 2025") # Placeholder static date

st.markdown("---")

# --- MAIN CONTENT: 2 COLUMN LAYOUT ---
left_col, right_col = st.columns([1, 1])

# Left Column: Key Metrics Table
with left_col:
    st.subheader("My Favorites")
    
    # Safely extract metrics with default values if missing
    metrics_data = {
        "Metric": [
            "Price to Earnings Ratio (TTM)",
            "Price to Sales Ratio (TTM)",
            "Return on Equity (TTM)",
            "Return on Invested Capital (TTM)",
            "Price to Earnings Growth (PEG) Value",
            "Beta",
            "Total Debt",
            "EBITDA Margin",
            "Gross Profit Margin (TTM)",
            "Forward Price to Earnings Ratio"
        ],
        "Value": [
            f"{info.get('trailingPE', 0.0):.2f}",
            f"{info.get('priceToSalesTrailing12Months', 0.0):.2f}",
            f"{info.get('returnOnEquity', 0.0)*100:.2f}%",
            f"{info.get('returnOnAssets', 0.0)*100:.2f}%", # Using ROA as a proxy for ROIC
            f"{info.get('pegRatio', 0.0):.2f}",
            f"{info.get('beta', 0.0):.2f}",
            f"{info.get('totalDebt', 0.0)/1e6:.2f}M",
            f"{info.get('ebitdaMargins', 0.0)*100:.2f}%",
            f"{info.get('grossMargins', 0.0)*100:.2f}%",
            f"{info.get('forwardPE', 0.0):.2f}"
        ]
    }
    
    # Split into a clean 2-column table presentation
    df_metrics = pd.DataFrame(metrics_data)
    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(df_metrics.iloc[:5], hide_index=True, use_container_width=True)
    with col2:
        st.dataframe(df_metrics.iloc[5:], hide_index=True, use_container_width=True)

# Right Column: Visual Charts
with right_col:
    # Chart 1: Candlestick Stock Chart
    df_chart = ticker.history(period="3m") # Past 3 months
    fig_candle = go.Figure(data=[go.Candlestick(
        x=df_chart.index,
        open=df_chart['Open'],
        high=df_chart['High'],
        low=df_chart['Low'],
        close=df_chart['Close']
    )])
    fig_candle.update_layout(title="Stock Price Chart (Past 3 Months)", xaxis_rangeslider_visible=False, height=300)
    st.plotly_chart(fig_candle, use_container_width=True)
    
    # Chart 2: 6-Point Score Profile (Line chart)
    categories = ['Predictability', 'Profitability', 'Growth', 'OracleMoat™', 'Financial Strength', 'Valuation']
    # Example scores corresponding to the shape in the original image
    scores = [2, 4, 2, 2, 4, 2] 
    
    fig_scores = go.Figure()
    fig_scores.add_trace(go.Scatter(
        x=categories, 
        y=scores, 
        mode='lines+markers',
        line=dict(color='#32a852', width=3),
        marker=dict(size=10, color=['#e6b800', '#32a852', '#e6b800', '#e6b800', '#32a852', '#e6b800'])
    ))
    fig_scores.update_layout(
        title="Company Score Profile",
        yaxis=dict(range=[0, 5], showticklabels=False),
        height=250,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig_scores, use_container_width=True)