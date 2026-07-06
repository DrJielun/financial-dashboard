import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Set page to wide mode to match the original dashboard image layout
st.set_page_config(layout="wide", page_title="Stock Analysis Dashboard")

# --- PASTE YOUR API KEY HERE ---
# Replace the text inside the quotes with your actual 32-character FMP API key
API_KEY = "RnSDMMwDXfmZfoSP7uzcN4Ok5dZYVHSz"

# --- SAFE DATA FETCHING ENGINE (CACHED) ---
@st.cache_data(ttl=600)  
def fetch_stock_data(ticker):
    profile_url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={API_KEY}"
    quote_url = f"https://financialmodelingprep.com/api/v3/quote/{ticker}?apikey={API_KEY}"
    metrics_url = f"https://financialmodelingprep.com/api/v3/key-metrics-ttm/{ticker}?apikey={API_KEY}"
    
    try:
        profile_res = requests.get(profile_url).json()
        quote_res = requests.get(quote_url).json()
        metrics_res = requests.get(metrics_url).json()
        
        # If API rejects the key or the symbol is restricted on the free tier:
        if isinstance(profile_res, dict) and "Error Message" in profile_res:
            return None, None, None
            
        if not profile_res or not quote_res or not metrics_res:
            return None, None, None
            
        return profile_res[0], quote_res[0], metrics_res[0]
    except Exception:
        return None, None, None

# --- SIDEBAR INPUT ---
st.sidebar.header("Dashboard Controls")
st.sidebar.markdown("💡 *Free FMP keys only allow symbols like AAPL, TSLA, MSFT, NVDA.*")
ticker_symbol = st.sidebar.text_input("Enter Stock Ticker:", value="AAPL").upper()

# Fetch data
profile, quote, metrics = fetch_stock_data(ticker_symbol)

# Determine if we are using live data or mock data fallback
is_mock_data = False
if profile is None or quote is None or metrics is None:
    is_mock_data = True
    # Generate mock fallback data matching the XOM picture metrics
    profile = {"companyName": f"{ticker_symbol} Corp (Demo Mode)", "sector": "Energy", "industry": "Oil & Gas Integrated", "exchangeShortName": "NYSE", "beta": 0.50}
    quote = {"price": 109.23, "change": 0.70, "changesPercentage": 0.64, "marketCap": 435000000000, "pe": 15.39}
    metrics = {"priceToSalesRatioTTM": 1.43, "returnOnEquityTTM": 0.1168, "returnOnCapitalEmployedTTM": 0.1032, "pegRatioTTM": 1.21, "grossProfitMarginTTM": 0.2205, "priceToBookRatioTTM": 1.80}

# --- RENDER UI LAYOUT ---

# Warning banner if the app is in demo mode
if is_mock_data:
    st.warning("⚠️ Running in Demo Mode. The API rejected the key or ticker. Make sure you replaced 'YOUR_ACTUAL_FMP_API_KEY_HERE' in the code, or try entering 'AAPL'.")

# 1. HEADER BLOCK
st.caption(f"{profile.get('sector', 'N/A')}  •  {profile.get('industry', 'N/A')}")
st.title(f"({ticker_symbol}) {profile.get('companyName')}")
st.caption(f"{profile.get('exchangeShortName')}")

col_h1, col_h2 = st.columns([2, 5])
with col_h1:
    price = quote.get('price', 0.0)
    change = quote.get('change', 0.0)
    change_pct = quote.get('changesPercentage', 0.0)
    st.metric(
        label="Current Price (USD)", 
        value=f"${price:,.2f}", 
        delta=f"{change:+.2f} ({change_pct:+.2f}%)"
    )
with col_h2:
    fair_value = price * 0.92
    st.markdown(f"**Tag Evaluation:** `Narrow Moat` | `OracleValue™: {fair_value:.2f}`")
    st.caption(f"Data Mode: {'🔴 Simulating Data' if is_mock_data else '🟢 Live FMP Feed'}")

st.markdown("---")

# 2. MAIN WORKSPACE (2 Columns side-by-side)
left_column, right_column = st.columns([1, 1])

# --- LEFT WORKSPACE: SYMMETRICAL METRIC TABLES ---
with left_column:
    st.subheader("Key Ratios & Metrics")
    
    raw_metrics = [
        ("Price to Earnings Ratio (TTM)", quote.get('pe')),
        ("Price to Sales Ratio (TTM)", metrics.get('priceToSalesRatioTTM')),
        ("Return on Equity (TTM)", metrics.get('returnOnEquityTTM')),
        ("Return on Invested Capital (TTM)", metrics.get('returnOnCapitalEmployedTTM')),
        ("PEG Ratio Value", metrics.get('pegRatioTTM')),
        ("Beta Alignment Value", profile.get('beta')),
        ("Market Cap", quote.get('marketCap')),
        ("Enterprise Margin Proxy", metrics.get('grossProfitMarginTTM') * 0.85 if metrics.get('grossProfitMarginTTM') else 0.18), 
        ("Gross Profit Margin (TTM)", metrics.get('grossProfitMarginTTM')),
        ("Price to Book Ratio", metrics.get('priceToBookRatioTTM'))
    ]
    
    formatted_rows = []
    for name, val in raw_metrics:
        if val is None:
            formatted_val = "N/A"
        elif "Margin" in name or "Return" in name:
            formatted_val = f"{val * 100:.2f}%"
        elif "Cap" in name:
            formatted_val = f"${val / 1e9:,.2f}B"
        else:
            formatted_val = f"{val:.2f}"
        formatted_rows.append({"Metric": name, "Value": formatted_val})
        
    df_all_metrics = pd.DataFrame(formatted_rows)
    
    # Render two side-by-side mini dataframes to recreate the image layout
    sub_col1, sub_col2 = st.columns(2)
    with sub_col1:
        st.dataframe(df_all_metrics.iloc[:5], hide_index=True, use_container_width=True)
    with sub_col2:
        st.dataframe(df_all_metrics.iloc[5:], hide_index=True, use_container_width=True)

# --- RIGHT WORKSPACE: RATING PROFILE LINE CHART ---
with right_column:
    st.subheader("Company Score Profile")
    
    categories = ['Predictability', 'Profitability', 'Growth', 'OracleMoat™', 'Financial Strength', 'Valuation']
    
    # Symmetrically calculate quality metrics out of 5 to feed the rating chart
    prof_score = 5 if (metrics.get('grossProfitMarginTTM', 0) > 0.20) else 3
    valuation_score = 4 if (quote.get('pe', 20) < 18) else 2
    
    scores = [3, prof_score, 2, 4, 4, valuation_score] 
    
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
