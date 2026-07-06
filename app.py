import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

# Set page to wide mode to match the layout
st.set_page_config(layout="wide", page_title="Stock Analysis Dashboard")

# --- PASTE YOUR API KEY HERE ---
# Make sure your 32-character key is inside the quotes with no spaces
API_KEY = "RnSDMMwDXfmZfoSP7uzcN4Ok5dZYVHSz" 

# --- DATA FETCHING ENGINE (FREE TIER COMPATIBLE) ---
@st.cache_data(ttl=600)  
def fetch_stock_data(ticker):
    # Utilizing endpoints fully authorized on the standard free tier
    profile_url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={API_KEY}"
    quote_url = f"https://financialmodelingprep.com/api/v3/quote/{ticker}?apikey={API_KEY}"
    
    try:
        profile_res = requests.get(profile_url).json()
        quote_res = requests.get(quote_url).json()
        
        # Guard clause: Check for explicit API error messages
        if isinstance(profile_res, dict) and "Error Message" in profile_res:
            return None, None
            
        # Guard clause: Verify array responses are populated
        if not profile_res or not quote_res:
            return None, None
            
        return profile_res[0], quote_res[0]
    except Exception:
        return None, None

# --- SIDEBAR INPUT ---
st.sidebar.header("Dashboard Controls")
st.sidebar.markdown("💡 *Free keys support sandbox symbols like AAPL, TSLA, MSFT, NVDA.*")
ticker_symbol = st.sidebar.text_input("Enter Stock Ticker:", value="AAPL").upper()

# Fetch data
profile, quote = fetch_stock_data(ticker_symbol)

# Determine if using live data or falling back to mock metrics safely
is_mock_data = False
if profile is None or quote is None:
    is_mock_data = True
    profile = {
        "companyName": f"{ticker_symbol} Corp (Simulation)", 
        "sector": "Energy", 
        "industry": "Oil & Gas Integrated", 
        "exchangeShortName": "NYSE", 
        "beta": 0.50,
        "priceToSalesTrailing12Months": 1.43,
        "grossProfitMargin": 0.2205
    }
    quote = {
        "price": 109.23, 
        "change": 0.70, 
        "changesPercentage": 0.64, 
        "marketCap": 435000000000, 
        "pe": 15.39,
        "yearHigh": 120.00,
        "yearLow": 95.00
    }

# --- RENDER UI LAYOUT ---

if is_mock_data:
    st.warning("⚠️ Running in Demo Mode. The API rejected the key or ticker symbol. Try entering 'AAPL'.")

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
    st.caption(f"Data Connection State: {'🔴 Simulated Backup' if is_mock_data else '🟢 Live FMP Feed'}")

st.markdown("---")

# 2. MAIN WORKSPACE (2 Columns side-by-side)
left_column, right_column = st.columns([1, 1])

# --- LEFT WORKSPACE: SYMMETRICAL METRIC TABLES ---
with left_column:
    st.subheader("Key Ratios & Metrics")
    
    # Deriving core metrics from free-tier friendly endpoints
    raw_metrics = [
        ("Price to Earnings Ratio (TTM)", quote.get('pe')),
        ("Price to Sales Ratio (TTM)", profile.get('priceToSalesTrailing12Months', 1.25)),
        ("Beta Volatility Coeff.", profile.get('beta')),
        ("Market Capitalization", quote.get('marketCap')),
        ("52-Week High Target", quote.get('yearHigh')),
        ("52-Week Low Target", quote.get('yearLow'))
    ]
    
    formatted_rows = []
    for name, val in raw_metrics:
        if val is None:
            formatted_val = "N/A"
        elif "Cap" in name:
            formatted_val = f"${val / 1e9:,.2f}B"
        elif "High" in name or "Low" in name:
            formatted_val = f"${val:,.2f}"
        else:
            formatted_val = f"{val:.2f}"
        formatted_rows.append({"Metric": name, "Value": formatted_val})
        
    df_all_metrics = pd.DataFrame(formatted_rows)
    
    # Symmetrical breakdown split
    sub_col1, sub_col2 = st.columns(2)
    with sub_col1:
        st.dataframe(df_all_metrics.iloc[:3], hide_index=True, use_container_width=True)
    with sub_col2:
        st.dataframe(df_all_metrics.iloc[3:], hide_index=True, use_container_width=True)

# --- RIGHT WORKSPACE: RATING PROFILE LINE CHART ---
with right_column:
    st.subheader("Company Score Profile")
    
    categories = ['Predictability', 'Profitability', 'Growth', 'OracleMoat™', 'Financial Strength', 'Valuation']
    
    # Constructing quality profile chart rules
    pe_val = quote.get('pe', 20) if quote.get('pe') else 20
    valuation_score = 5 if pe_val < 15 else (3 if pe_val < 25 else 1)
    
    scores = [3, 4, 2, 4, 4, valuation_score] 
    
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
