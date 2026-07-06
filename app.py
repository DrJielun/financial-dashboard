import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time

# Set page layout to wide mode for professional dashboard proportions
st.set_page_config(layout="wide", page_title="Institutional Stock Terminal")

# --- SIDEBAR INPUT CONTROL ---
st.sidebar.header("Terminal Controls")
st.sidebar.markdown("🚀 Enter any active equity ticker symbol.")
ticker_symbol = st.sidebar.text_input("Enter Stock Ticker:", value="AAPL").upper().strip()

refresh_rate = st.sidebar.slider("Auto-Refresh Interval (Seconds):", min_value=10, max_value=300, value=30)
st.sidebar.caption(f"🔄 Market data auto-refreshing every {refresh_rate} seconds.")

# --- CORE DATA ENGINE (100% REAL FUNDAMENTALS & HISTORY) ---
@st.cache_data(ttl=refresh_rate)  
def fetch_legitimate_market_data(ticker):
    try:
        stock_obj = yf.Ticker(ticker)
        # Fetch 6 months of daily historical charts
        hist_df = stock_obj.history(period="6m")
        # Fetch actual real-time corporate statistics profile
        info_dict = stock_obj.info
        
        if hist_df.empty or not info_dict:
            return None, None
        return hist_df, info_dict
    except Exception:
        return None, None

# Execute data polling
df_chart, info_matrix = fetch_legitimate_market_data(ticker_symbol)

# --- UI WORKSPACE RENDERING ---
if df_chart is not None and info_matrix is not None:
    
    # 1. LIVE PROFILE PARSING
    company_name = info_matrix.get('longName', ticker_symbol)
    exchange = info_matrix.get('exchange', 'Global Exchange')
    currency = info_matrix.get('currency', 'USD')
    
    regular_price = info_matrix.get('currentPrice') or info_matrix.get('regularMarketPrice') or df_chart['Close'].iloc[-1]
    prev_close = info_matrix.get('previousClose') or df_chart['Close'].iloc[-2]
    
    price_change = regular_price - prev_close
    price_change_pct = (price_change / prev_close) * 100 if prev_close else 0.0
    
    high_6m = float(df_chart['High'].max())
    low_6m = float(df_chart['Low'].min())

    # --- TOP METRIC DISPLAY BANNER ---
    st.caption("Financial Market Asset • Dynamic Terminal Workspace")
    st.title(f"🏢 {company_name} ({ticker_symbol}) Terminal Canvas")
    st.caption(f"Exchange: **{exchange}** | Currency: **{currency}** | Engine Status: 🟢 Connected")

    col_h1, col_h2, col_h3 = st.columns([2, 2, 3])
    with col_h1:
        st.metric(
            label="Current Market Value", 
            value=f"${regular_price:,.2f}", 
            delta=f"{price_change:+.2f} ({price_change_pct:+.2f}%)"
        )
    with col_h2:
        st.metric(label="6-Month Historical Peak", value=f"${high_6m:,.2f}")
    with col_h3:
        st.metric(label="6-Month Historical Floor", value=f"${low_6m:,.2f}")

    st.markdown("---")

    # --- MAIN SYMMETRICAL DUAL-COLUMN LAYOUT ---
    left_column, right_column = st.columns([1, 1])

    # LEFT COLUMN: COMPACT COMPREHENSIVE DATA GRID
    with left_column:
        st.subheader("📋 Core Financial Fundamentals")
        
        # Safe metric formatting functions
        def pct_fmt(v): return f"{v * 100:.2f}%" if v else "N/A"
        def num_fmt(v): return f"{v:.2f}" if v else "N/A"
        def cap_fmt(v):
            if not v: return "N/A"
            return f"${v / 1e12:,.2f}T" if v >= 1e12 else f"${v / 1e9:,.2f}B"

        real_metrics = [
            {"Metric": "Market Capitalization", "Value": cap_fmt(info_matrix.get('marketCap'))},
            {"Metric": "Trailing P/E Ratio", "Value": num_fmt(info_matrix.get('trailingPE'))},
            {"Metric": "Forward P/E Ratio", "Value": num_fmt(info_matrix.get('forwardPE'))},
            {"Metric": "Price to Sales Ratio (TTM)", "Value": num_fmt(info_matrix.get('priceToSalesTrailing12Months'))},
            {"Metric": "Trailing Earnings Per Share (EPS)", "Value": num_fmt(info_matrix.get('trailingEps'))},
            {"Metric": "Beta Systematic Volatility", "Value": num_fmt(info_matrix.get('beta'))},
            {"Metric": "Gross Profit Margin", "Value": pct_fmt(info_matrix.get('grossMargins'))},
            {"Metric": "EBITDA Margin Profile", "Value": pct_fmt(info_matrix.get('ebitdaMargins'))},
            {"Metric": "Return on Equity (ROE)", "Value": pct_fmt(info_matrix.get('returnOnEquity'))},
            {"Metric": "Dividend Yield", "Value": pct_fmt(info_matrix.get('dividendYield'))}
        ]
        
        df_metrics = pd.DataFrame(real_metrics)
        
        # Symmetrically divide data grid rows into two columns
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            st.dataframe(df_metrics.iloc[:5], hide_index=True, use_container_width=True)
        with sub_col2:
            st.dataframe(df_metrics.iloc[5:], hide_index=True, use_container_width=True)

    # RIGHT COLUMN: VISUAL PERFORMANCE MONITOR MATRIX
    with right_column:
        st.subheader("📊 Profitability & Risk Scale Profiles")
        
        # Gather live values for dynamic graphical distribution scaling
        gross_margin_val = info_matrix.get('grossMargins', 0.0) or 0.0
        pe_ratio_val = info_matrix.get('trailingPE', 30.0) or 30.0
        beta_val = info_matrix.get('beta', 1.0) or 1.0
        roe_val = info_matrix.get('returnOnEquity', 0.0) or 0.0
        
        categories = ['Gross Margin Profile', 'Valuation Safety', 'Volatility Control', 'Capital Efficiency (ROE)']
        
        # Map values to standard 1 to 5 quality scores
        score_margin = 5 if gross_margin_val > 0.45 else (3 if gross_margin_val > 0.20 else 1)
        score_val = 5 if pe_ratio_val < 18 else (3 if pe_ratio_val < 35 else 1.5)
        score_vol = 5 if beta_val < 0.9 else (3 if beta_val < 1.4 else 1)
        score_roe = 5 if roe_val > 0.25 else (3 if roe_val > 0.08 else 1)
        
        scores = [score_margin, score_val, score_vol, score_roe]
        
        fig_profile = go.Figure()
        fig_profile.add_trace(go.Bar(
            x=categories, 
            y=scores, 
            marker_color=['#2E7D32', '#1565C0', '#FBC02D', '#D32F2F'],
            width=0.4
        ))
        
        fig_profile.update_layout(
            yaxis=dict(range=[0, 5.5], showgrid=True, tickvals=[1, 3, 5], ticktext=['Low', 'Moderate', 'Strong']),
            height=280,
            margin=dict(l=40, r=40, t=10, b=10),
            template="plotly_dark"
        )
        st.plotly_chart(fig_profile, use_container_width=True)

    # --- LOWER EXPANSION: ADVANCED PERFORMANCE CANDLESTICK GRAPH ---
    st.markdown("---")
    st.subheader("📈 Institutional Candle Graph & Volume Matrix (6-Month Horizon)")
    
    # Generate integrated dual-axis layout rows
    fig_terminal = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                 vertical_spacing=0.03, row_width=[0.25, 0.75])
    
    # Setup Candlestick pricing markers
    fig_terminal.add_trace(go.Candlestick(
        x=df_chart.index,
        open=df_chart['Open'],
        high=df_chart['High'],
        low=df_chart['Low'],
        close=df_chart['Close'],
        name='Price Session'
    ), row=1, col=1)
    
    # Setup matching Volume bars
    fig_terminal.add_trace(go.Bar(
        x=df_chart.index,
        y=df_chart['Volume'],
        name='Volume Delta',
        marker=dict(color='rgba(21, 101, 192, 0.5)')
    ), row=2, col=1)
    
    fig_terminal.update_layout(
        height=500, 
        margin=dict(l=40, r=40, t=10, b=10), 
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        showlegend=False
    )
    fig_terminal.update_yaxes(title_text=f"Price ({currency})", row=1, col=1)
    fig_terminal.update_yaxes(title_text="Volume Traded", row=2, col=1)
    
    st.plotly_chart(fig_terminal, use_container_width=True)

else:
    st.error(f"❌ Error: Fundamental market assets for ticker '{ticker_symbol}' could not be resolved.")
    st.info("Verify your input matches globally indexed exchange symbols (e.g. NVDA, TSM, AAPL, AMD, MSFT).")

# --- AUTO REFRESH LOOP EXECUTION ---
@st.fragment
def execution_timer_loop():
    time.sleep(refresh_rate)
    st.rerun()

execution_timer_loop()
