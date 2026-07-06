import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time

# --- DASHBOARD CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Institutional Stock Terminal")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Terminal Controls")
st.sidebar.markdown("💡 Input any globally active equity ticker symbol.")
ticker_symbol = st.sidebar.text_input("Stock Ticker:", value="AAPL").upper().strip()

refresh_rate = st.sidebar.slider("Data Refresh Interval (Seconds):", min_value=10, max_value=300, value=30)
st.sidebar.caption(f"🔄 UI engine auto-refreshing every {refresh_rate}s.")

# --- CORE DATA ENGINE (REAL-TIME DATA ONLY) ---
@st.cache_data(ttl=refresh_rate)
def fetch_real_market_data(ticker_str):
    try:
        ticker_obj = yf.Ticker(ticker_str)
        
        # Fetch 6 months of historical data
        hist = ticker_obj.history(period="6m")
        
        # Fetch operational fundamental metrics
        info = ticker_obj.info
        
        if hist.empty or not info:
            return None, None
            
        return hist, info
    except Exception:
        return None, None

# Execute data polling
df_chart, info_matrix = fetch_real_market_data(ticker_symbol)

# --- UI WORKSPACE RENDERING ---
if df_chart is not None and info_matrix is not None:
    
    # 1. VISUAL METADATA PARSING
    company_name = info_matrix.get('longName', ticker_symbol)
    exchange = info_matrix.get('exchange', 'Global Exchange')
    currency = info_matrix.get('currency', 'USD')
    
    regular_price = info_matrix.get('currentPrice') or info_matrix.get('regularMarketPrice') or df_chart['Close'].iloc[-1]
    prev_close = info_matrix.get('previousClose') or df_chart['Close'].iloc[-2]
    
    price_change = regular_price - prev_close
    price_change_pct = (price_change / prev_close) * 100 if prev_close else 0.0
    
    # 6-Month Range Calculation
    high_6m = float(df_chart['High'].max())
    low_6m = float(df_chart['Low'].min())

    # --- TOP MAIN HEADER ROW ---
    st.caption(f"Live Market Feed • {exchange} Connection Verified")
    st.title(f"🏢 {company_name} ({ticker_symbol}) Terminal Workspace")
    
    col_h1, col_h2, col_h3 = st.columns([2, 2, 3])
    with col_h1:
        st.metric(
            label=f"Current Price ({currency})", 
            value=f"${regular_price:,.2f}", 
            delta=f"{price_change:+.2f} ({price_change_pct:+.2f}%)"
        )
    with col_h2:
        st.metric(label="6-Month Horizon Peak", value=f"${high_6m:,.2f}")
    with col_h3:
        st.metric(label="6-Month Horizon Floor", value=f"${low_6m:,.2f}")

    st.markdown("---")

    # --- MAIN SYMMETRICAL DUAL-COLUMN LAYOUT ---
    left_column, right_column = st.columns([1, 1])

    # LEFT COLUMN: REAL FUNDAMENTALS DATAFRAME GRID
    with left_column:
        st.subheader("📋 Core Financial Fundamentals")
        
        # Safely parse real data points, falling back to "N/A" if unavailable
        def format_pct(val): return f"{val * 100:.2f}%" if val else "N/A"
        def format_num(val): return f"{val:.2f}" if val else "N/A"
        def format_mkt_cap(val):
            if not val: return "N/A"
            return f"${val / 1e12:,.2f}T" if val >= 1e12 else f"${val / 1e9:,.2f}B"

        real_metrics = [
            {"Metric": "Market Capitalization", "Value": format_mkt_cap(info_matrix.get('marketCap'))},
            {"Metric": "Trailing P/E Ratio", "Value": format_num(info_matrix.get('trailingPE'))},
            {"Metric": "Forward P/E Ratio", "Value": format_num(info_matrix.get('forwardPE'))},
            {"Metric": "Price to Sales Ratio (TTM)", "Value": format_num(info_matrix.get('priceToSalesTrailing12Months'))},
            {"Metric": "Trailing EPS", "Value": format_num(info_matrix.get('trailingEps'))},
            {"Metric": "Beta (Systematic Volatility)", "Value": format_num(info_matrix.get('beta'))},
            {"Metric": "Profit Margin", "Value": format_pct(info_matrix.get('profitMargins'))},
            {"Metric": "Gross Profit Margin", "Value": format_pct(info_matrix.get('grossMargins'))},
            {"Metric": "EBITDA Margin", "Value": format_pct(info_matrix.get('ebitdaMargins'))},
            {"Metric": "Return on Equity (ROE)", "Value": format_pct(info_matrix.get('returnOnEquity'))}
        ]
        
        df_metrics = pd.DataFrame(real_metrics)
        
        # Clean symmetrical grid split
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            st.dataframe(df_metrics.iloc[:5], hide_index=True, use_container_width=True)
        with sub_col2:
            st.dataframe(df_metrics.iloc[5:], hide_index=True, use_container_width=True)

    # RIGHT COLUMN: SYSTEM PERFORMANCE METRICS 
    with right_column:
        st.subheader("📊 Profitability & Valuation Profile")
        
        # Construct dynamically scaling visual indicators based on factual operating values
        gross_margin_val = info_matrix.get('grossMargins', 0.0) or 0.0
        pe_ratio_val = info_matrix.get('trailingPE', 30.0) or 30.0
        beta_val = info_matrix.get('beta', 1.0) or 1.0
        roe_val = info_matrix.get('returnOnEquity', 0.0) or 0.0
        
        categories = ['Gross Margin Scale', 'Valuation Safety', 'Volatility Control', 'Capital Efficiency (ROE)']
        
        # Real logic mapping to a 1-5 layout score
        score_margin = 5 if gross_margin_val > 0.50 else (3 if gross_margin_val > 0.25 else 1)
        score_val = 5 if pe_ratio_val < 15 else (3 if pe_ratio_val < 35 else 1.5)
        score_vol = 5 if beta_val < 0.9 else (3 if beta_val < 1.4 else 1.5)
        score_roe = 5 if roe_val > 0.20 else (3 if roe_val > 0.08 else 1)
        
        live_scores = [score_margin, score_val, score_vol, score_roe]
        
        fig_profile = go.Figure()
        fig_profile.add_trace(go.Bar(
            x=categories, 
            y=live_scores, 
            marker_color=['#2E7D32', '#1565C0', '#FBC02D', '#E65100'],
            width=0.4
        ))
        
        fig_profile.update_layout(
            yaxis=dict(range=[0, 5.5], showgrid=True, tickvals=[1, 3, 5], ticktext=['Low', 'Moderate', 'Exceptional']),
            height=280,
            margin=dict(l=40, r=40, t=10, b=10),
            template="plotly_dark"
        )
        st.plotly_chart(fig_profile, use_container_width=True)

    # --- LOWER EXPANSION: ADVANCED CANDLESTICK TERMINAL ---
    st.markdown("---")
    st.subheader("📈 Institutional Candle Graph & Volume Matrix")
    
    # Create unified dual-axis subplots
    fig_terminal = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                 vertical_spacing=0.03, row_width=[0.25, 0.75])
    
    # Plot Candlesticks
    fig_terminal.add_trace(go.Candlestick(
        x=df_chart.index,
        open=df_chart['Open'],
        high=df_chart['High'],
        low=df_chart['Low'],
        close=df_chart['Close'],
        name='Price Session'
    ), row=1, col=1)
    
    # Plot Volume
    fig_terminal.add_trace(go.Bar(
        x=df_chart.index,
        y=df_chart['Volume'],
        name='Volume',
        marker=dict(color='rgba(21, 101, 192, 0.6)')
    ), row=2, col=1)
    
    fig_terminal.update_layout(
        height=550, 
        margin=dict(l=40, r=40, t=10, b=10), 
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        showlegend=False
    )
    fig_terminal.update_yaxes(title_text=f"Price ({currency})", row=1, col=1)
    fig_terminal.update_yaxes(title_text="Volume Traded", row=2, col=1)
    
    st.plotly_chart(fig_terminal, use_container_width=True)

else:
    st.error(f"❌ Verification Failed: Fundamental assets for ticker '{ticker_symbol}' could not be safely resolved.")
    st.info("Check spelling definitions or connection statuses before trying again.")

# --- AUTO REFRESH LOOP EXECUTION ---
@st.fragment
def execution_timer_loop():
    time.sleep(refresh_rate)
    st.rerun()

execution_timer_loop()
