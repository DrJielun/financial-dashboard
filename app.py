import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Set page to wide mode to accommodate the side-by-side dashboard look
st.set_page_config(layout="wide", page_title="Stock Analysis Dashboard")

# --- SECURE API KEY HANDLING ---
if "FMP_API_KEY" in st.secrets:
    API_KEY = st.secrets["FMP_API_KEY"]
else:
    # Fallback placeholder for local machine testing
    API_KEY = "YOUR_FMP_API_KEY" 

# --- DATA FETCHING ENGINE (CACHED) ---
@st.cache_data(ttl=600)  # Caches data for 10 minutes to save your 250 free daily requests
def fetch_stock_data(ticker):
    # FMP Endpoints needed to match the dashboard metrics
    profile_url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={API_KEY}"
    quote_url = f"https://financialmodelingprep.com/api/v3/quote/{ticker}?apikey={API_KEY}"
    metrics_url = f"https://financialmodelingprep.com/api/v3/key-metrics-ttm/{ticker}?apikey={API_KEY}"
    
    try:
        profile_res = requests.get(profile_url).json()
        quote_res = requests.get(quote_url).json()
        metrics_res = requests.get(metrics_url).json()
        
        # Error check: Invalid API Key
        if isinstance(profile_res, dict) and "Error Message" in profile_res:
            st.error(f"FMP API Error: {profile_res['Error Message']}")
            return None, None, None
            
        # Error check: Empty array response (wrong ticker or daily limits hit)
        if not profile_res or not quote_res or not metrics_res:
            st.error(f"No data returned for '{ticker}'. You may have misspelled the ticker or reached your free daily request limit.")
            return None, None, None
            
        return profile_res[0], quote_res[0], metrics_res[0]
    except Exception as e:
        st.error(f"API Connection Failure: {e}")
        return None, None, None

# --- SIDEBAR INPUT ---
st.sidebar.header("Dashboard Controls")
ticker_symbol = st.sidebar.text_input("Enter Stock Ticker:", value="XOM").upper()

# Execute data fetch
profile, quote, metrics = fetch_stock_data(ticker_symbol)

# --- DASHBOARD LAYOUT RENDER ---
if profile and quote and metrics:
    
    # 1. HEADER SECTION
    st.caption(f"{profile.get('sector', 'N/A')}  •  {profile.get('industry', 'N/A')}")
    st.title(f"({ticker_symbol}) {profile.get('companyName', 'Company Name')}")
    st.caption(f"{profile.get('exchangeShortName', 'NYSE')}")
    
    col_h1, col_h2 = st.columns([2, 5])
    with col_h1:
        # Display current price and daily movement
        price = quote.get('price', 0.0)
        change = quote.get('change', 0.0)
        change_pct = quote.get('changesPercentage', 0.0)
        st.metric(
            label="Current Price (USD)", 
            value=f"${price:,.2f}", 
            delta=f"{change:+.2f} ({change_pct:+.2f}%)"
        )
    with col_h2:
        # Valuation approximation badges mimicking the original dashboard tags
        fair_value = price * 0.95  # Standard mockup calculation rule
        st.markdown(f"**Tag Overview:** `Narrow Moat` | `OracleValue™: {fair_value:.2f}`")
        
        # Formatted Earnings Date proxy
        earnings_timestamp = quote.get('earningsAnnouncement')
        if earnings_timestamp:
            try:
                date_obj = datetime.strptime(earnings_timestamp.split('T')[0], "%Y-%m-%d")
                earnings_date = date_obj.strftime("%d %b %Y")
            except:
                earnings_date = "Upcoming"
        else:
            earnings_date = "N/A"
        st.caption(f"Next Earnings Date: **{earnings_date}**")

    st.markdown("---")
    
    # 2. MAIN 2-COLUMN VIEW
    left_column, right_column = st.columns([1, 1])
    
    # --- LEFT COLUMN: FINANCIAL METRICS TABLES ---
    with left_column:
        st.subheader("Key Metrics (TTM)")
        
        # Formatting data points extracted from FMP fields into the UI layout
        raw_metrics = [
            ("Price to Earnings Ratio (TTM)", quote.get('pe')),
            ("Price to Sales Ratio (TTM)", metrics.get('priceToSalesRatioTTM')),
            ("Return on Equity (TTM)", metrics.get('returnOnEquityTTM')),
            ("Return on Invested Capital (TTM)", metrics.get('returnOnCapitalEmployedTTM')),
            ("PEG Ratio Value", metrics.get('pegRatioTTM')),
            ("Beta", profile.get('beta')),
            ("Market Cap", quote.get('marketCap')),
            ("Net Income Margin", metrics.get('netIncomePerEBTardisTTM')), # Proxy for margins
            ("Gross Profit Margin (TTM)", metrics.get('grossProfitMarginTTM')),
            ("Price to Book Ratio", metrics.get('priceToBookRatioTTM'))
        ]
        
        # Clean up formatting for display
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
        
        # Split metrics symmetrically into two side-by-side tables like the original image
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            st.dataframe(df_all_metrics.iloc[:5], hide_index=True, use_container_width=True)
        with sub_col2:
            st.dataframe(df_all_metrics.iloc[5:], hide_index=True, use_container_width=True)

    # --- RIGHT COLUMN: CHARTS & SCORE PROFILES ---
    with right_column:
        st.subheader("Performance Indicators")
        
        # Mock up visual score indicators based on financial health parameters
        categories = ['Predictability', 'Profitability', 'Growth', 'OracleMoat™', 'Financial Strength', 'Valuation']
        # Dynamically shifting values depending on real data traits (e.g. Higher margin = higher profile score)
        prof_score = 4 if (metrics.get('grossProfitMarginTTM', 0) > 0.20) else 2
        debt_score = 4 if (metrics.get('debtToEquityRatioTTM', 1) < 0.5) else 2
        
        scores = [3, prof_score, 3, 4, debt_score, 3] 
        
        fig_profile = go.Figure()
        fig_profile.add_trace(go.Scatter(
            x=categories, 
            y=scores, 
            mode='lines+markers',
            line=dict(color='#2E7D32', width=3),
            marker=dict(size=10, color='#FBC02D')
        ))
        fig_profile.update_layout(
            title="Company Quality Vector Profile",
            yaxis=dict(range=[0, 6], showgrid=True, tickvals=[1,2,3,4,5], ticktext=['Low','','Medium','','High']),
            height=320,
            margin=dict(l=40, r=40, t=40, b=40)
        )
        st.plotly_chart(fig_profile, use_container_width=True)
