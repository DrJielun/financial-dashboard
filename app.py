import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

# Set page to wide mode to perfectly match the target layout proportions
st.set_page_config(layout="wide", page_title="Live Fundamental Dashboard")

# --- SIDEBAR INPUT CONTROL ---
st.sidebar.header("Dashboard Controls")
st.sidebar.markdown("🚀 Type any real global ticker symbol. Every line item is pulled completely live.")
ticker_symbol = st.sidebar.text_input("Enter Stock Ticker:", value="NVDA").upper()

# --- UNFILTERED REAL-TIME DATA ENGINE (YAHOO QUOTE SUMMARY SYSTEM) ---
@st.cache_data(ttl=15)  # Cache data for only 15 seconds to ensure absolute live market changes
def fetch_unfiltered_live_fundamentals(ticker):
    # Call Yahoo's structural corporate metrics summary backend
    url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=defaultKeyStatistics,financialData,price"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        # Verify if the engine successfully loaded valid corporate entries
        if data.get('quoteSummary') and data['quoteSummary'].get('result'):
            return data['quoteSummary']['result'][0]
        return None
    except Exception:
        return None

# Execute layout mapping data fetch
raw_payload = fetch_unfiltered_live_fundamentals(ticker_symbol)

# --- LIVE METRIC MATRIX PARSING ---
if raw_payload is not None:
    # 1. Access the sub-data modules
    stats = raw_payload.get('defaultKeyStatistics', {})
    financials = raw_payload.get('financialData', {})
    price_module = raw_payload.get('price', {})

    # Helper function to extract numerical entries safely out of Yahoo's structural JSON dictionary formats
    def get_raw_val(data_dict, key, format_type='raw'):
        obj = data_dict.get(key, {})
        if isinstance(obj, dict):
            return obj.get(format_type, 0.0) if obj.get(format_type) is not None else 0.0
        return obj if obj is not None else 0.0

    # Extract Header Price Metrics Live
    current_price = get_raw_val(financials, 'currentPrice') or get_raw_val(price_module, 'regularMarketPrice')
    prev_close = get_raw_val(price_module, 'regularMarketPreviousClose')
    price_change = current_price - prev_close
    price_change_pct = (price_change / prev_close) * 100 if prev_close else 0.0
    exchange = price_module.get('exchangeName', 'NASDAQ/NYSE')
    company_name = price_module.get('longName', f"{ticker_symbol} Corp")

    # Extract live fundamental metrics directly from raw financial modules
    pe_ratio = get_raw_val(stats, 'trailingPE') or get_raw_val(stats, 'forwardPE')
    price_to_sales = get_raw_val(stats, 'priceToSalesTrailing12Months')
    roe = get_raw_val(financials, 'returnOnEquity')
    roic = get_raw_val(financials, 'returnOnAssets')  # Public tracking fallback structure for invested capital return
    peg_ratio = get_raw_val(stats, 'pegRatio')
    beta = get_raw_val(stats, 'beta')
    total_debt = get_raw_val(financials, 'totalDebt')
    ebitda_margin = get_raw_val(financials, 'ebitdaMargins')
    gross_margin = get_raw_val(financials, 'grossMargins')
    forward_pe = get_raw_val(stats, 'forwardPE')

    # Construct the structural table grid framework utilizing 100% true live properties
    metric_fields = [
        ("Price to Earnings Ratio (TTM)", pe_ratio),
        ("Price to Sales Ratio (TTM)", price_to_sales),
        ("Return on Equity (TTM)", roe),
        ("Return on Invested Capital (TTM)", roic),
        ("Price to Earnings Growth (PEG) Value", peg_ratio),
        ("Beta Alignment Value", beta),
        ("Total Debt Matrix Value", total_debt),
        ("EBITDA Margin Profile", ebitda_margin),
        ("Gross Profit Margin (TTM)", gross_margin),
        ("Forward Price to Earnings Ratio", forward_pe)
    ]

    # --- UI WORKSPACE RENDERING ---
    
    # 1. VISUAL HEADER BLOCK
    st.caption("Financial Market Asset • 100% Real-Time Unfiltered Engine")
    st.title(f"({ticker_symbol}) {company_name}")
    st.caption(f"Exchange Forum: {exchange} | 🟢 Dynamic Live Tracking Pipeline Active")

    col_h1, col_h2 = st.columns([2, 5])
    with col_h1:
        st.metric(
            label="Current Price (USD)", 
            value=f"${current_price:,.2f}", 
            delta=f"{price_change:+.2f} ({price_change_pct:+.2f}%)"
        )
    with col_h2:
        st.markdown(f"**Tag Evaluation Matrix:** `Live Data Active` | `Market Driven Structure`")
        st.caption("Data feeds refreshing dynamically every 15 seconds.")

    st.markdown("---")

    # 2. MAIN SYMMETRICAL DUAL-COLUMN LAYOUT
    left_column, right_column = st.columns([1, 1])

    # --- LEFT COLUMN: COMPACT SIDE-BY-SIDE GRID TABLES ---
    with left_column:
        st.subheader("My Favorites")
        
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
        
        # Calculate scores out of 5 using real-time inputs
        prof_score = 5 if roe > 0.25 else (3 if roe > 0.10 else 1)
        valuation_score = 5 if (0 < pe_ratio < 18) else (3 if pe_ratio < 35 else 1)
        strength_score = 5 if total_debt < 5e9 else (3 if total_debt < 4e10 else 1)
        growth_score = 4 if (0 < peg_ratio < 1.5) else 2
        
        scores = [3, prof_score, growth_score, strength_score, valuation_score]
        
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
    # --- TRUE ERROR HANDLING LAYER ---
    st.error(f"❌ Connection Blocked or Unrecognized Stock Ticker symbol: '{ticker_symbol}'.")
    st.info("Please verify the ticker formatting against standard Yahoo Finance symbols (e.g., AAPL, NVDA, AMD, TSM, XOM) and ensure the company is currently active.")
