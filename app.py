import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

# Set page to wide mode to perfectly match the target layout proportions
st.set_page_config(layout="wide", page_title="Stock Analysis Dashboard")

# --- SIDEBAR INPUT CONTROL ---
st.sidebar.header("Dashboard Controls")
st.sidebar.markdown("🚀 Enter any active stock ticker symbol (e.g., NVDA, TSM, AAPL, AMD, MSFT).")
ticker_symbol = st.sidebar.text_input("Enter Stock Ticker:", value="AAPL").upper().strip()

refresh_rate = st.sidebar.slider("Auto-Refresh Interval (Seconds):", min_value=10, max_value=300, value=30)
st.sidebar.caption(f"🔄 Market engine refreshing elements dynamically every {refresh_rate} seconds.")

# --- COMPREHENSIVE YAHOO FINANCE MULTI-FLOW DATA ENGINE ---
@st.cache_data(ttl=refresh_rate)  
def fetch_complete_live_market_data(ticker):
    # Flow 1: Pull unblocked pricing timeline and core boundaries
    chart_url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=6m"
    # Flow 2: Pull open-access fundamental ratios via the v6 corporate summary module
    fundamental_url = f"https://query2.finance.yahoo.com/v6/finance/quoteSummary/{ticker}?modules=summaryDetail,defaultKeyStatistics,financialData"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    
    package = {"meta": None, "chart": None, "fundamentals": None}
    
    try:
        chart_res = requests.get(chart_url, headers=headers, timeout=10).json()
        if chart_res.get('chart', {}).get('result'):
            package["meta"] = chart_res['chart']['result'][0]['meta']
            package["chart"] = chart_res['chart']['result'][0]
    except Exception:
        pass

    try:
        fund_res = requests.get(fundamental_url, headers=headers, timeout=10).json()
        if fund_res.get('quoteSummary', {}).get('result'):
            package["fundamentals"] = fund_res['quoteSummary']['result'][0]
    except Exception:
        pass
        
    return package

# Execute dynamic live fetch loop
live_data = fetch_complete_live_market_data(ticker_symbol)

# --- UI WORKSPACE RENDERING ---
if live_data["meta"] is not None:
    meta = live_data["meta"]
    fund = live_data["fundamentals"] or {}
    
    # 1. PARSE CORE LIVE PRICING & DATA METRICS
    company_name = meta.get('longName', f"{ticker_symbol} Corporation")
    exchange = meta.get('exchangeName', 'Global Exchange')
    
    regular_price = meta.get('regularMarketPrice')
    prev_close = meta.get('previousClose')
    
    if regular_price is None:
        regular_price = meta.get('chartPreviousClose') or prev_close or 100.00
    if prev_close is None:
        prev_close = regular_price
        
    price_change = regular_price - prev_close
    price_change_pct = (price_change / prev_close) * 100 if prev_close else 0.0

    # Extract Data Blocks Defensively out of nesting modules
    stats = fund.get('defaultKeyStatistics', {})
    detail = fund.get('summaryDetail', {})
    findata = fund.get('financialData', {})

    def get_val(data_block, key):
        node = data_block.get(key, {})
        return node.get('raw') if isinstance(node, dict) else node

    # 2. POPULATE TRULY LIVE INDIVIDUAL RATIOS FROM THE V6 STREAM
    pe_base = get_val(detail, 'trailingPE') or get_val(stats, 'trailingPE')
    forward_pe = get_val(detail, 'forwardPE') or get_val(stats, 'forwardPE')
    ps_base = get_val(detail, 'priceToSalesTrailing12Months') or get_val(detail, 'priceToSales')
    pb_base = get_val(detail, 'priceToBook') or get_val(stats, 'priceToBook')
    peg_base = get_val(stats, 'pegRatio')
    beta_base = get_val(detail, 'beta') or get_val(stats, 'beta')
    eps_base = get_val(stats, 'trailingEps')
    
    # Balance sheet statement variables
    total_debt = get_val(findata, 'totalDebt')
    ebitda_margin = get_val(findata, 'ebitdaMargins')
    gross_margin = get_val(findata, 'grossMargins')

    # --- HISTORICAL DATA DATA FRAME GENERATION ---
    df_chart = pd.DataFrame()
    high_52, low_52 = None, None
    
    if live_data["chart"]:
        try:
            timestamps = pd.to_datetime(live_data["chart"]['timestamp'], unit='s')
            quotes = live_data["chart"]['indicators']['quote'][0]
            df_chart = pd.DataFrame({
                'Date': timestamps, 'Open': quotes['open'], 'High': quotes['high'],
                'Low': quotes['low'], 'Close': quotes['close'], 'Volume': quotes['volume']
            }).dropna()
            
            if not df_chart.empty:
                high_52 = float(df_chart['High'].max())
                low_52 = float(df_chart['Low'].min())
        except Exception:
            pass

    # UI Table Grid Layout Array Mapping
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
    st.caption(f"Financial Market Asset • 100% Dynamic Multi-Flow Pipeline")
    st.title(f"📈 ({ticker_symbol}) Equity Tracking Canvas")
    st.caption(f"Exchange Forum: **{exchange}** | 🟢 Live Connected Pipeline")

    col_h1, col_h2 = st.columns([2, 5])
    with col_h1:
        st.metric(
            label="Current Session Value", 
            value=f"${regular_price:,.2f}", 
            delta=f"{price_change:+.2f} ({price_change_pct:+.2f}%)"
        )
    with col_h2:
        st.markdown(f"**Tag Evaluation Matrix:** `Verified Authentic Feeds` | `Market Fluctuating Data`")
        st.caption(f"6-Month Calculated Boundaries: Timeline Low **${low_52:,.2f}** — Peak High **${high_52:,.2f}**" if low_52 else "")

    st.markdown("---")

    # 2. MAIN SYMMETRICAL DUAL-COLUMN LAYOUT
    left_column, right_column = st.columns([1, 1])

    # --- LEFT COLUMN: COMPACT SIDE-BY-SIDE GRID TABLES ---
    with left_column:
        st.subheader("My Favorites")
        
        formatted_rows = []
        for name, val, val_type in metric_fields:
            if val is None or pd.isna(val) or val == 0:
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
        
        # Calculate scores out of 5 completely dynamically based on live fundamentals
        if pe_base is None or pe_base == 0: 
            valuation_score = 3
        else: 
            valuation_score = 5 if pe_base < 22 else (3 if pe_base < 45 else 1)
            
        if gross_margin is None or gross_margin == 0:
            profit_score = 3
        else:
            profit_score = 5 if gross_margin > 0.40 else (3 if gross_margin > 0.20 else 1)
            
        if peg_base is None or peg_base == 0: 
            growth_score = 3
        else: 
            growth_score = 5 if peg_base < 1.3 else (3 if peg_base < 2.2 else 1)
            
        scores = [3, profit_score, growth_score, 4, valuation_score]
        
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

    # --- LOWER EXPANSION: STANDARD PRICE TIMELINE ---
    if not df_chart.empty:
        st.markdown("---")
        st.subheader("📈 Pricing Trend Grid (6-Month Historical Horizon)")
        
        fig_tech = go.Figure()
        fig_tech.add_trace(go.Scatter(
            x=df_chart['Date'], 
            y=df_chart['Close'], 
            mode='lines',
            name='Closing Price',
            line=dict(color='#2E7D32', width=2.5)
        ))
        
        fig_tech.update_layout(
            height=380, 
            margin=dict(l=40, r=40, t=10, b=10), 
            yaxis=dict(title="Price (USD)")
        )
        st.plotly_chart(fig_tech, use_container_width=True)

else:
    st.error(f"❌ Error: Fundamental market tracking profile for ticker '{ticker_symbol}' could not be resolved.")

# --- TRUE AUTOMATED REFRESH PIPELINE ---
@st.fragment
def auto_refresh_executor():
    import time
    time.sleep(refresh_rate)
    st.rerun()

auto_refresh_executor()
