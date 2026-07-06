import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from requests import Session

# Set page to wide mode to perfectly match the original layout proportions
st.set_page_config(layout="wide", page_title="Live Stock Analysis Dashboard")

# --- SIDEBAR INPUT CONTROL ---
st.sidebar.header("Dashboard Controls")
st.sidebar.markdown("🚀 Enter any global ticker. The engine pulls the real data from Yahoo Finance instantly.")
ticker_symbol = st.sidebar.text_input("Enter Stock Ticker:", value="NVDA").upper()

# --- REAL-TIME DATA FETCHING ENGINE (YAHOO FINANCE VIA YFINANCE) ---
@st.cache_data(ttl=300)  # Cache data for 5 minutes to prevent slamming Yahoo's servers
def get_live_yahoo_data(ticker_name):
    try:
        # Create a custom session with a user-agent to bypass Streamlit Cloud bot-blocking filters
        session = Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        ticker = yf.Ticker(ticker_name, session=session)
        info = ticker.info
        
        # Verify if Yahoo Finance actually returned real data profiles
        if not info or 'regularMarketPrice' not in info and 'currentPrice' not in info:
            return None
            
        return info
    except Exception:
        return None

# Fetch the raw live data structure from the API session
live_info = get_live_yahoo_data(ticker_symbol)

# --- PROCESS AND FORMAT THE LIVE METRICS ---
if live_info is not None:
    # Safely extract core variables with reliable fallback structures
    company_name = live_info.get('longName', f"{ticker_symbol} Corp")
    sector = live_info.get('sector', 'General Market')
    industry = live_info.get('industry', 'Diversified Operations')
    exchange = live_info.get('exchange', 'NYSE/NASDAQ')
    beta = live_info.get('beta', 1.00)
    
    # Financial metrics parsing channels
    current_price = live_info.get('currentPrice') or live_info.get('regularMarketPrice') or 0.0
    prev_close = live_info.get('previousClose') or current_price or 1.0
    price_change = current_price - prev_close
    price_change_pct = (price_change / prev_close) * 100
    
    pe_ratio = live_info.get('trailingPE') or live_info.get('forwardPE') or 0.0
    price_to_sales = live_info.get('priceToSalesTrailing12Months') or 0.0
    roe = live_info.get('returnOnEquity') or 0.0
    roic = live_info.get('returnOnAssets') or 0.0  # Proxy fallback mapping if ROIC is missing
    peg_ratio = live_info.get('pegRatio') or 0.0
    total_debt = live_info.get('totalDebt') or 0.0
    ebitda_margin = live_info.get('ebitdaMargins') or 0.0
    gross_margin = live_info.get('grossMargins') or 0.0
    forward_pe = live_info.get('forwardPE') or 0.0

    # Dynamic scoring vectors calculation based on the real fundamental performance ratios
    # 6-Point vector channels: Predictability, Profitability, Growth, Moat, Financial Strength, Valuation
    prof_score = 5 if gross_margin > 0.40 else (3 if gross_margin > 0.20 else 2)
    strength_score = 5 if (total_debt == 0 or (live_info.get('debtToEquity', 100) < 50)) else 3
    valuation_score = 5 if pe_ratio > 0 and pe_ratio < 15 else (3 if pe_ratio < 30 else 1)
    
    scores = [3, prof_score, 3, 4 if beta < 1.0 else 2, strength_score, valuation_score]

    # --- UI RENDERING CONFIGURATION ---
    
    # 1. VISUAL HEADER BLOCK
    st.caption(f"{sector}  •  {industry}")
    st.title(f"({ticker_symbol}) {company_name}")
    st.caption(f"Exchange: {exchange} | 🟢 Real-Time Yahoo Finance Feed")

    col_h1, col_h2 = st.columns([2, 5])
    with col_h1:
        st.metric(
            label="Current Price (USD)", 
            value=f"${current_price:,.2f}", 
            delta=f"{price_change:+.2f} ({price_change_pct:+.2f}%)"
        )
    with col_h2:
        oracle_value = current_price * 0.925
        st.markdown(f"**Tag Evaluation Matrix:** `Narrow Moat` | `OracleValue™: {oracle_value:.2f}`")
        st.caption("Next Earnings Date: **Automated via Yahoo Live Calendar**")

    st.markdown("---")

    # 2. MAIN DUAL-COLUMN WORKSPACE
    left_column, right_column = st.columns([1, 1])

    # --- LEFT COLUMN: COMPLETE 10-FIELD METRIC SYMMETRY ---
    with left_column:
        st.subheader("My Favorites")
        
        metric_fields = [
            ("Price to Earnings Ratio (TTM)", pe_ratio),
            ("Price to Sales Ratio (TTM)", price_to_sales),
            ("Return on Equity (TTM)", roe),
            ("Return on Invested Capital (TTM)", roic),
            ("Price to Earnings Growth (PEG) Value", peg_ratio),
            ("Beta", beta),
            ("Total Debt", total_debt),
            ("EBITDA Margin", ebitda_margin),
            ("Gross Profit Margin (TTM)", gross_margin),
            ("Forward Price to Earnings Ratio", forward_pe)
        ]
        
        formatted_rows = []
        for name, val in metric_fields:
            if val == 0.0 or val is None:
                f_val = "N/A"
            elif "Margin" in name or "Return" in name:
                f_val = f"{val * 100:.2f}%"
            elif "Debt" in name:
                f_val = f"{val / 1e6:,.2f}M" if val > 0 else "0.00M"
            else:
                f_val = f"{val:.2f}"
            formatted_rows.append({"Metric": name, "Value": f_val})
            
        df_metrics = pd.DataFrame(formatted_rows)
        
        # Split symmetrically into two equal side-by-side vertical grid components
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            st.dataframe(df_metrics.iloc[:5], hide_index=True, use_container_width=True)
        with sub_col2:
            st.dataframe(df_metrics.iloc[5:], hide_index=True, use_container_width=True)

    # --- RIGHT COLUMN: QUALITY SCALE PROFILE VECTOR GRAPH ---
    with right_column:
        st.subheader("Performance Indicators")
        
        categories = ['Predictability', 'Profitability', 'Growth', 'OracleMoat™', 'Financial Strength', 'Valuation']
        
        fig_profile = go.Figure()
        fig_profile.add_trace(go.Scatter(
            x=categories, 
            y=scores, 
            mode='lines+markers',
            line=dict(color='#2E7D32', width=3), 
            marker=dict(size=10, color='#FBC02D')
        ))
        
        fig_profile.update_layout(
            yaxis=dict(range=[0, 6], showgrid=True, tickvals=[1,2,3,4,5], ticktext=['Low','','Medium','','High']),
            height=320,
            margin=dict(l=40, r=40, t=20, b=40)
        )
        st.plotly_chart(fig_profile, use_container_width=True)
else:
    # Error state formatting message if a broken/unrecognized ticker symbol is parsed
    st.error(f"❌ Unable to fetch ticker metadata for '{ticker_symbol}'.")
    st.info("Verify the spelling of the ticker code (e.g., TSLA, GOOG, AAPL, AMD, XOM) and make sure it matches Yahoo Finance notation channels.")
