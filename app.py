import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")

# Use Streamlit's built-in caching (caches for 1 hour / 3600 seconds)
@st.cache_data(ttl=3600)
def fetch_stock_data(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    # Fetching the info dictionary
    info = ticker.info
    # Fetching historical data
    history = ticker.history(period="3m")
    return info, history

ticker_symbol = "XOM"

try:
    # Call the cached function
    info, df_chart = fetch_stock_data(ticker_symbol)
    
    # ... Rest of your dashboard rendering code goes here ...
    st.write(f"Successfully loaded {info.get('longName')}")

except Exception as e:
    st.error("Yahoo Finance is currently rate-limiting this server. Try again shortly.")
    st.caption(f"Error Details: {e}")
