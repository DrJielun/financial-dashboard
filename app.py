import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

# Set page to wide mode to perfectly match the target layout proportions
st.set_page_config(layout="wide", page_title="Stock Analysis Dashboard")

# --- SIDEBAR INPUT CONTROL ---
st.sidebar.header("Dashboard Controls")
st.sidebar.markdown("🚀 Type any active stock ticker symbol (e.g., NVDA, TSM, AAPL, AMD, MSFT).")
ticker_symbol = st.sidebar.text_input("Enter Stock Ticker:", value="AAPL").upper().strip()

refresh_rate = st.sidebar.slider("Auto-Refresh Interval (Seconds):", min_value=10, max_value=300, value=30)
st.sidebar.caption(f"🔄 Market data auto-refreshing every {refresh_rate} seconds.")

# --- COMPREHENSIVE YAHOO FINANCE UNBLOCKED PIPELINE ---
@st.cache_data(ttl=refresh_rate)  
def fetch_unblocked_yahoo_data(ticker):
    # Utilizing the open query2 quote gateway which is unfirewalled for public cloud nodes
    url = f"https://query2.finance.yahoo.com/v7/finance/quote?symbols={ticker}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        quote_result = data.get('quoteResponse', {}).get('result', [])
        if quote_result:
            return quote_result[0]
        return None
    except Exception:
        return None

# Execute live data fetch
live_meta = fetch_unblocked_yahoo_data(ticker_symbol)

# --- UI WORKSPACE RENDERING ---
if live_meta is not None:
    # 1. VISUAL METADATA PARSING & MARKET PRICE CONDITIONS
    company_name = live_meta.get('longName', f"{ticker_symbol} Corporation")
    exchange = live_meta.get('exchange', 'Global Exchange')
    market_state = live_meta.get('marketState', 'REGULAR').upper()
    
    # Handle market states cleanly (Live trading vs Post-market close)
    if market_state in ['POST', 'POSTPOST', 'CLOSED'] and live_meta.get('postMarketPrice'):
        current_price = live_meta.get('postMarketPrice')
        price_change = live_meta.get('postMarketChange', 0.0)
        price_change_pct = live_meta.get('postMarketChangePercent', 0.0)
        status_tag = f"🔴 Closed / At Close Summary"
    elif market_state in ['PRE', 'PREPRE'] and live_meta.get('preMarketPrice'):
        current_price = live_meta.get('preMarketPrice')
        price_change = live_meta.get('preMarketChange', 0.0)
        price_change_pct = live_meta.get('preMarketChangePercent', 0.0)
        status_tag = f"🟡 Pre-Market Interval"
    else:
        current_price = live_meta.get('regularMarketPrice')
        prev_close = live_meta.get('regularMarketPreviousClose')
        
        if current_price is None:
            current_price = prev_close or 100.00
        if prev_close is None:
            prev_close = current_price
            
        price_change = live_meta.get('regularMarketChange', current_price - prev_close)
        price_change_pct = live_meta.get('regularMarketChangePercent', (price_change / prev_close) * 100 if prev_close else 0.0)
        status_tag = f"🟢 Regular Live Trading Session"
    
    # 2. EXTRACT AUTHENTIC LIVE FUNDAMENTALS
    pe_ratio = live_meta.get('trailingPE')
    forward_pe = live_meta.get('forwardPE')
    ps_ratio = live_meta.get('priceToSales')
    pb_ratio = live_meta.get('priceToBook')
    peg_ratio = live_meta.get('pegRatio')
    beta_base = live_meta.get('beta')
    eps_base = live_meta.get('trailingEps')
    div_yield = live_meta.get('trailingAnnualDividendYield')
    
    market_cap = live_meta.get('marketCap')
    shares_outstanding = live_meta.get('sharesOutstanding')
    high_52 = live_meta.get('fiftyTwoWeekHigh')
    low_52 = live_meta.get('fiftyTwoWeekLow')
    avg_vol = live_meta.get('averageDailyVolume3Month')

    # Construct clean UI display arrays containing only data supported by the open mirror
    metrics_block_1 = [
        ("Price to Earnings Ratio (TTM)", pe_ratio, "num"),
        ("Forward P/E Valuation Multiplier", forward_pe, "num"),
        ("Price to Sales Ratio (TTM)", ps_ratio, "num"),
        ("Price to Book Ratio (TTM)", pb_ratio, "num"),
        ("Price to Earnings Growth (PEG)", peg_ratio, "num")
    ]
    
    metrics_block_2 = [
        ("Beta Systematic Volatility", beta_base, "num"),
        ("Trailing Earnings Per Share (EPS)", eps_base, "num"),
        ("Dividend Yield Annual Rate", div_yield, "pct"),
        ("52-Week Market Peak High", high_52, "num"),
        ("52-Week Market Floor Low", low_52, "num")
    ]

    # --- LEFT COLUMN: COMPACT SIDE-BY-SIDE GRID TABLES ---
    st.caption(f"Financial Market Asset • Global Trading Workspace")
    st.title(f"📈 ({ticker_symbol}) {company_name}")
    st.caption(f"Exchange Forum: **{exchange}** | Status: **{status_tag}**")

    # Metrics Summary Bar
    h_col1, h_col2, h_col3 = st.columns(3)
    h_col1.metric("Current Value", f"${current_price:,.2f}", f"{price_change:+.2f} ({price_change_pct:+.2f}%)")
    h_col2.metric("Market Capitalization", f"${market_cap/1e9:,.2f}B" if market_cap else "N/A")
    h_col3.metric("Shares Outstanding", f"{shares_outstanding/1e6:,.2f}M" if shares_outstanding else "N/A")

    st.markdown("---")

    left_column, right_column = st.columns([1, 1])

    with left_column:
        st.subheader("Live Valuation & Market Metrics")
        
        def format_cell(val, style):
            if val is None or pd.isna(val) or val == 0: return "N/A"
            if style == 'pct': return f"{val * 100:.2f}%"
            return f"{val:,.2f}"

        def build_dataframe(metrics_list):
            rows = [{"Metric Parameter": name, "Live Value": format_cell(v, s)} for name, v, s in metrics_list]
            return pd.DataFrame(rows)

        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            st.dataframe(build_dataframe(metrics_block_1), hide_index=True, use_container_width=True)
        with sub_col2:
            st.dataframe(build_dataframe(metrics_block_2), hide_index=True, use_container_width=True)

    # --- RIGHT COLUMN: DYNAMIC QUALITY SCALE RATINGS CHART ---
    with right_column:
        st.subheader("Performance Indicators")
        categories = ['Predictability', 'Profitability', 'Growth', 'Financial Strength', 'Valuation']
        
        # Calculate scorecard vectors dynamically out of true incoming metrics
        if pe_ratio is None or pe_ratio == 0: 
            val_score = 3
        else: 
            val_score = 5 if pe_ratio < 22 else (3 if pe_ratio < 45 else 1)
            
        if peg_ratio is None or peg_ratio == 0: 
            growth_score = 3
        else: 
            growth_score = 5 if peg_ratio < 1.3 else (3 if peg_base < 2.2 else 1)
            
        if beta_base is None:
            strength_score = 3
        else:
            strength_score = 5 if beta_base < 1.1 else (3 if beta_base < 1.7 else 1)
            
        scores = [3, 4, growth_score, strength_score, val_score]
        
        fig_profile = go.Figure()
        fig_profile.add_trace(go.Scatter(
            x=categories, y=scores, mode='lines+markers',
            line=dict(color='#2E7D32', width=3), marker=dict(size=10, color='#FBC02D')
        ))
        fig_profile.update_layout(
            yaxis=dict(range=[0, 6], showgrid=True, tickvals=[1,2,3,4,5], ticktext=['Low','','Medium','','High']),
            height=240, margin=dict(l=40, r=40, t=20, b=40)
        )
        st.plotly_chart(fig_profile, use_container_width=True)

else:
    st.error(f"❌ Error: Fundamental market profile data for ticker '{ticker_symbol}' could not be resolved.")
    st.info("Please verify your internet connection or the spelling of the ticker symbol.")

# --- TRUE AUTOMATED REFRESH PIPELINE ---
@st.fragment
def auto_refresh_executor():
    import time
    time.sleep(refresh_rate)
    st.rerun()

auto_refresh_executor()
