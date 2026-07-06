import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")

# IMPORTANT: Put your FMP API Key here
API_KEY = "TLPmlPmVfCtAJdV4mDDn3CrciCnxQtRd" 

@st.cache_data(ttl=600) # Cache responses for 10 minutes to save API requests
def fetch_fmp_data(ticker):
    # Endpoint 1: Company Profile (Contains margins, sector, etc.)
    profile_url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={API_KEY}"
    # Endpoint 2: Real-time Quote (Contains P/E, live price, changes)
    quote_url = f"https://financialmodelingprep.com/api/v3/quote/{ticker}?apikey={API_KEY}"
    
    profile_res = requests.get(profile_url).json()
    quote_res = requests.get(quote_url).json()
    
    # Check if we got valid data back
    if not profile_res or not quote_res:
        return None, None
        
    return profile_res[0], quote_res[0]

# Ticker to search
ticker_symbol = "XOM"

profile, quote = fetch_fmp_data(ticker_symbol)

if profile is None or quote is None:
    st.error("Could not fetch data. Check your API key or Ticker symbol.")
else:
    # --- HEADER SECTION ---
    st.caption(f"{profile.get('sector')}  •  {profile.get('industry')}")
    st.title(f"({ticker_symbol}) {profile.get('companyName')}")
    st.caption(f"{profile.get('exchangeShortName')}")

    # Price & Metrics
    col_header1, col_header2 = st.columns([1, 4])
    with col_header1:
        st.metric(
            label="Current Price (USD)", 
            value=f"{quote.get('price'):.2f}", 
            delta=f"{quote.get('change'):.2f} ({quote.get('changesPercentage'):.2f}%)"
        )
    with col_header2:
        st.markdown(f"`OracleValue™: {quote.get('yearHigh', 0) * 0.9:.2f}`") # Just an example calculation formula
        st.caption("Data source: Financial Modeling Prep API")

    st.markdown("---")

    # --- MAIN CONTENT ---
    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.subheader("Key Metrics Table")
        
        # Mapping FMP variables into our target dashboard format
        metrics_data = {
            "Metric": [
                "Price to Earnings Ratio",
                "Price to Sales Ratio",
                "Beta",
                "Market Cap",
                "Year High",
                "Year Low"
            ],
            "Value": [
                f"{quote.get('pe', 0):.2f}" if quote.get('pe') else "N/A",
                f"{profile.get('priceToSalesTrailing12Months', 0):.2f}" if profile.get('priceToSalesTrailing12Months') else "N/A",
                f"{profile.get('beta', 0):.2f}",
                f"${quote.get('marketCap', 0)/1e9:.2f}B",
                f"${quote.get('yearHigh', 0):.2f}",
                f"${quote.get('yearLow', 0):.2f}"
            ]
        }
        
        df_metrics = pd.DataFrame(metrics_data)
        st.dataframe(df_metrics, hide_index=True, use_container_width=True)

    with right_col:
        st.subheader("Visual Profile")
        # Dummy graph placeholder for the Score Profile 
        categories = ['Predictability', 'Profitability', 'Growth', 'Moat', 'Financial Strength', 'Valuation']
        scores = [3, 5, 2, 4, 4, 3] 
        
        fig_scores = go.Figure(data=go.Scatter(x=categories, y=scores, mode='lines+markers', line=dict(color='#32a852', width=3)))
        fig_scores.update_layout(yaxis=dict(range=[0, 5]), height=300)
        st.plotly_chart(fig_scores, use_container_width=True)
