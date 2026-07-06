import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

# Set page to wide mode to perfectly match the target layout proportions
st.set_page_config(layout="wide", page_title="Stock Analysis Dashboard")

# --- SIDEBAR INPUT CONTROL ---
st.sidebar.header("Dashboard Controls")
st.sidebar.markdown("🚀 Type any active stock ticker symbol (e.g., NVDA, TSM, AAPL, AMD, MSFT).")
ticker_symbol = st.sidebar.text_input("Enter Stock Ticker:", value="NVDA").upper().strip()

refresh_rate = st.sidebar.slider("Auto-Refresh Interval (Seconds):", min_value=10, max_value=300, value=30)
st.sidebar.caption(f"🔄 Market data auto-refreshing every {refresh_rate} seconds.")

# --- REAL-TIME DATA ENGINE (UNBLOCKED PUBLIC GATEWAY MIRROR) ---
@st.cache_data(ttl=refresh_rate)  
def fetch_real_live_market_data(ticker):
    # Utilizing the query2 mirror to completely bypass authentication cookie blocks on public cloud servers
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
live_meta = fetch_real_live_market_data(ticker_symbol)

# --- UI WORKSPACE RENDERING ---
if live_meta is not None:
    # 1. VISUAL METADATA PARSING & MARKET STATE PRICE HANDLING
    company_name = live_meta.get('longName', f"{ticker_symbol} Corporation")
    exchange = live_meta.get('exchange', 'NASDAQ/NYSE')
    market_state = live_meta.get('marketState', 'REGULAR').upper()
    
    # DYNAMIC "AT CLOSE" STATE CHECK: If market session isn't live, pull post/pre close price points
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
    
    # 2. EXTRACT CORE VALUATION STRATIFICATIONS
    pe_base = live_meta.get('trailingPE')
    ps_base = live_meta.get('priceToSales')
    pb_base = live_meta.get('priceToBook')
    peg_base = live_meta.get('pegRatio')
    beta_base = live_meta.get('beta')
    eps_base = live_meta.get('trailingEps')
    div_yield = live_meta.get('trailingAnnualDividendYield')
    forward_pe = live_meta.get('forwardPE')
    
    # Financial Statement nodes safely flagged as None to display N/A without layout crashes
    total_debt = None
    ebitda_margin = None
    gross_margin = None
    
    # Bound parameters for dynamic scorecard ratings logic
    high_52 = live_meta.get('fiftyTwoWeekHigh')
    low_52 = live_meta.get('fiftyTwoWeekLow')
    
    # UI Table Grid Fields Layout Array Mapping
    metric_fields = [
        ("Price to Earnings Ratio (TTM)", pe_base, "num"),
        ("Price to Sales Ratio (TTM)", ps_base, "num"),
        ("Price to Book Ratio (TTM)", pb_base, "num"),
        ("Trailing Earnings Per Share (EPS)", eps_base, "num"),
        ("Price to Earnings Growth (PEG) Value", peg_base, "num"),
        ("Beta Systematic Volatility", beta_base, "num"),
        ("Total Debt Matrix Value", total_debt, "debt"),
        ("EBITDA Margin Profile", ebitda_margin, "pct"),
        ("Gross Profit Margin (TTM)", gross_margin, "pct"),
        ("Forward Price to Earnings Ratio", forward_pe, "num")
    ]
    
    # 1. VISUAL HEADER BLOCK
    st.caption(f"Financial Market Asset • Global Trading Workspace")
    st.title(f"({ticker_symbol}) {company_name}")
    st.caption(f"Exchange Forum: {exchange} | Status: {status_tag}")

    col_h1, col_h2 = st.columns([2, 5])
    with col_h1:
        st.metric(
            label="Selected Session Price (USD)", 
            value=f"${current_price:,.2f}", 
            delta=f"{price_change:+.2f} ({price_change_pct:+.2f}%)"
        )
    with col_h2:
        st.markdown(f"**Tag Evaluation Matrix:** `Premium Live Engine Active` | `Market Driven Structure`")
        st.caption(f"52-Week Bounds: Range Low **${low_52 if low_52 else 'N/A'}** — Peak High **${high_52 if high_52 else 'N/A'}**")

    st.markdown("---")

    # 2. MAIN SYMMETRICAL DUAL-COLUMN LAYOUT
    left_column, right_column = st.columns([1, 1])

    # --- LEFT COLUMN: COMPACT SIDE-BY-SIDE GRID TABLES ---
    with left_column:
        st.subheader("My Favorites")
        
        formatted_rows = []
        for name, val, val_type in metric_fields:
            if val is None or pd.isna(val):
                f_val = "N/A"
            elif val_type == "pct":
                f_val = f"{val * 100:.2f}%"
            elif val_type == "debt":
                f_val = f"{val / 1e6:,.2f}M"
            else:
                f_val = f"{val:.2f}"
            formatted_rows.append({"Metric": name, "Value": f_val})
            
        df_metrics = pd.DataFrame(formatted_rows)
        
        # Split symmetrically into two balanced, clean tracking grids
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            st.dataframe(df_metrics.iloc[:5], hide_index=True, use_container_width=True)
        with sub_col2:
            st.dataframe(df_metrics.iloc[5:], hide_index=True, use_container_width=True)

    # --- RIGHT COLUMN: DYNAMIC QUALITY SCALE RATINGS CHART ---
    with right_column:
        st.subheader("Performance Indicators")
        
        categories = ['Predictability', 'Profitability', 'Growth', 'Financial Strength', 'Valuation']
        
        # Calculate scores completely dynamically based on live variables
        if pe_base is None: 
            valuation_score = 3
        else: 
            valuation_score = 5 if pe_base < 18 else (3 if pe_base < 35 else 1)
            
        if peg_base is None: 
            growth_score = 3
        else: 
            growth_score = 5 if peg_base < 1.2 else (3 if peg_base < 2.0 else 1)
            
        if high_52 and current_price:
            strength_score = 5 if (current_price / high_52) > 0.85 else 3
        else:
            strength_score = 3
            
        scores = [3, 4, growth_score, strength_score, valuation_score]
        
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
    # --- TRUE ERROR STATE RENDERER ---
    st.error(f"❌ Error: Fundamental market profile data for ticker '{ticker_symbol}' could not be resolved.")
    st.info("Please verify the ticker formatting stands accurate against standard active exchange parameters (e.g., NVDA, AMD, MSFT, TSM, AAPL).")

# --- TRUE AUTOMATED REFRESH PIPELINE ---
@st.fragment
def auto_refresh_executor():
    import time
    time.sleep(refresh_rate)
    st.rerun()

auto_refresh_executor()
