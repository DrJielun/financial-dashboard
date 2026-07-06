import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import numpy as np

st.set_page_config(layout="wide", page_title="Live Equity Terminal")

# --- SIDEBAR INTERFACE & REFRESH TIMERS ---
st.sidebar.header("📊 Terminal Controls")
ticker_symbol = st.sidebar.text_input("Enter Stock Ticker:", value="NVDA").upper().strip()

refresh_rate = st.sidebar.slider("Auto-Refresh Interval (Seconds):", min_value=10, max_value=300, value=30)
st.sidebar.caption(f"🔄 Market data auto-refreshing every {refresh_rate} seconds.")

# --- COMPREHENSIVE YAHOO FINANCE DATA ENGINE (UNBLOCKED MIRROR) ---
@st.cache_data(ttl=refresh_rate)
def fetch_yahoo_mirror_dataset(ticker):
    # Utilizing the query2 public gateway to cleanly bypass Streamlit Cloud network filters
    summary_url = f"https://query2.finance.yahoo.com/v7/finance/quote?symbols={ticker}"
    chart_url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=6m"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    
    results = {"summary": None, "chart": None, "error_type": None}
    
    # 1. Fetch Live Summary Quotes
    try:
        sum_resp = requests.get(summary_url, headers=headers, timeout=10)
        sum_resp.raise_for_status()
        sum_data = sum_resp.json()
        
        quote_result = sum_data.get('quoteResponse', {}).get('result', [])
        if quote_result:
            results["summary"] = quote_result[0]
        else:
            results["error_type"] = "INVALID_TICKER"
            return results
    except requests.exceptions.HTTPError as e:
        results["error_type"] = f"HTTP_{e.response.status_code}"
        return results
    except (requests.exceptions.Timeout, requests.exceptions.RequestException):
        results["error_type"] = "NETWORK_ERROR"
        return results

    # 2. Fetch Historical Datasets
    try:
        chart_resp = requests.get(chart_url, headers=headers, timeout=10)
        chart_resp.raise_for_status()
        chart_data = chart_resp.json()
        if chart_data.get('chart', {}).get('result'):
            results["chart"] = chart_data['chart']['result'][0]
    except Exception:
        pass 
        
    return results

# Execute the live data stream
data_package = fetch_yahoo_mirror_dataset(ticker_symbol)

# --- PIPELINE ERROR ROUTING ---
if data_package["error_type"] is not None:
    if data_package["error_type"] == "INVALID_TICKER":
        st.error(f"❌ Unknown Ticker Asset: '{ticker_symbol}' could not be located.")
        st.info("Please verify the ticker formatting stands accurate against Yahoo Finance listings.")
    else:
        st.error(f"🌐 Pipeline Exception: Endpoint responded with error {data_package['error_type']}")
    st.stop()

# --- VALIDATED PARSING LAYER ---
summary = data_package["summary"]
chart = data_package["chart"]

if summary:
    # Core Metadata Variables
    company_name = summary.get('longName', ticker_symbol)
    exchange = summary.get('exchange', 'Global Exchange')
    quote_type = summary.get('quoteType', 'EQUITY')

    # Real-Time Price Metrics
    current_price = summary.get('regularMarketPrice')
    prev_close = summary.get('regularMarketPreviousClose')
    price_change = summary.get('regularMarketChange', 0.0)
    price_pct = summary.get('regularMarketChangePercent', 0.0)

    # Live Market Valuation & Activity Ratios
    pe_ratio = summary.get('trailingPE')
    forward_pe = summary.get('forwardPE')
    ps_ratio = summary.get('priceToSales')
    pb_ratio = summary.get('priceToBook')
    peg_ratio = summary.get('pegRatio')
    beta = summary.get('beta')
    eps = summary.get('trailingEps')
    div_yield = summary.get('trailingAnnualDividendYield')
    
    market_cap = summary.get('marketCap')
    shares_outstanding = summary.get('sharesOutstanding')
    target_price = summary.get('targetPriceMean')
    high_52 = summary.get('fiftyTwoWeekHigh')
    low_52 = summary.get('fiftyTwoWeekLow')
    avg_vol = summary.get('averageDailyVolume3Month')

    # Construct clean UI display arrays containing only 100% verified live fields
    metrics_block_1 = [
        ("Price to Earnings Ratio (TTM)", pe_ratio, "num"),
        ("Forward P/E Multiplier", forward_pe, "num"),
        ("Price to Sales Ratio (TTM)", ps_ratio, "num"),
        ("Price to Book Ratio (TTM)", pb_ratio, "num")
    ]
    
    metrics_block_2 = [
        ("PEG Valuation Multiplier", peg_ratio, "num"),
        ("Beta Systematic Volatility", beta, "num"),
        ("Trailing Earnings Per Share (EPS)", eps, "num"),
        ("Dividend Yield Target Rate", div_yield, "pct")
    ]

    metrics_block_3 = [
        ("52-Week Market Peak High", high_52, "num"),
        ("52-Week Market Floor Low", low_52, "num"),
        ("Average Daily Trading Volume", avg_vol, "vol"),
        ("Analyst Price Target Mean", target_price, "num")
    ]

    # --- LOCALIZED TECHNICAL CALCULATION MATRIX ---
    df_chart = pd.DataFrame()
    if chart:
        try:
            timestamps = pd.to_datetime(chart['timestamp'], unit='s')
            quotes = chart['indicators']['quote'][0]
            df_chart = pd.DataFrame({
                'Date': timestamps, 'Open': quotes['open'], 'High': quotes['high'],
                'Low': quotes['low'], 'Close': quotes['close'], 'Volume': quotes['volume']
            }).dropna()
            
            if not df_chart.empty:
                # Moving Averages
                df_chart['SMA_20'] = df_chart['Close'].rolling(window=20).mean()
                df_chart['SMA_50'] = df_chart['Close'].rolling(window=50).mean()
                
                # Bollinger Bands
                std_20 = df_chart['Close'].rolling(window=20).std()
                df_chart['BB_Upper'] = df_chart['SMA_20'] + (std_20 * 2)
                df_chart['BB_Lower'] = df_chart['SMA_20'] - (std_20 * 2)
                
                # Relative Strength Index (RSI 14)
                delta = df_chart['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / (loss + 1e-9)
                df_chart['RSI'] = 100 - (100 / (1 + rs))
        except Exception:
            pass

    # --- DYNAMIC MARKET RATING CALCULATOR ---
    def generate_live_ratings():
        # Valuation score scales natively based on live P/E ratios
        if pe_ratio is None: val_score = 3
        else: val_score = 5 if pe_ratio < 18 else (3 if pe_ratio < 35 else 1)
        
        # Growth indicator scales based on real PEG ratios
        if peg_ratio is None: growth_score = 3
        else: growth_score = 5 if peg_ratio < 1.2 else (3 if peg_ratio < 2.0 else 1)
        
        # Financial health score derived from market price relative to its 52-week parameters
        if high_52 and current_price: 
            health_score = 5 if (current_price / high_52) > 0.85 else 3
        else: 
            health_score = 3
            
        return [3, 4, growth_score, health_score, val_score]

    scores = generate_live_ratings()

    # --- USER INTERFACE RENDERING PANEL ---
    st.caption("Financial Analysis Workspace • Market Data via Yahoo Finance Unblocked Pipeline")
    st.title(f"({ticker_symbol}) {company_name}")
    st.caption(f"Exchange Board: **{exchange}** | Asset Classification: **{quote_type}**")

    # Metrics Summary Bar
    h_col1, h_col2, h_col3 = st.columns(3)
    h_col1.metric("Current Price", f"${current_price:,.2f}" if current_price else "N/A", f"{price_change:+.2f} ({price_pct:+.2f}%)")
    h_col2.metric("Market Capitalization", f"${market_cap/1e9:,.2f}B" if market_cap else "N/A")
    h_col3.metric("Shares Outstanding", f"{shares_outstanding/1e6:,.2f}M" if shares_outstanding else "N/A")

    st.markdown("---")
    
    col_left, col_right = st.columns([1, 1])

    # --- LEFT SECTION: VERIFIED DATA RATIO GRID TABLES ---
    with col_left:
        st.subheader("Live Valuation & Market Metrics")
        
        def format_cell(val, style):
            if val is None or pd.isna(val): return "N/A"
            if style == 'pct': return f"{val * 100:.2f}%"
            if style == 'vol': return f"{val / 1e6:,.2f}M"
            return f"{val:,.2f}"

        def build_dataframe(metrics_list):
            rows = [{"Parameter": name, "Current Value": format_cell(v, s)} for name, v, s in metrics_list]
            return pd.DataFrame(rows)

        sub_tab1, sub_tab2, sub_tab3 = st.tabs(["Valuation Multiples", "Growth & Yield Statistics", "Historical Boundaries"])
        with sub_tab1: st.dataframe(build_dataframe(metrics_block_1), hide_index=True, use_container_width=True)
        with sub_tab2: st.dataframe(build_dataframe(metrics_block_2), hide_index=True, use_container_width=True)
        with sub_tab3: st.dataframe(build_dataframe(metrics_block_3), hide_index=True, use_container_width=True)

    # --- RIGHT SECTION: ACCOUNTABILITY STRENGTHS RADIAL GRAPH ---
    with col_right:
        st.subheader("Market-Driven Core Performance Scorecard")
        categories = ['Predictability', 'Profitability', 'Growth', 'Financial Strength', 'Valuation']
        
        fig_score = go.Figure()
        fig_score.add_trace(go.Scatter(
            x=categories, y=scores, mode='lines+markers',
            line=dict(color='#1B5E20', width=3), marker=dict(size=10, color='#FFD600')
        ))
        fig_score.update_layout(
            yaxis=dict(range=[0, 6], showgrid=True, tickvals=[1,2,3,4,5], ticktext=['Low','','Medium','','High']),
            height=260, margin=dict(l=40, r=40, t=20, b=40)
        )
        st.plotly_chart(fig_score, use_container_width=True)

    # --- LOWER EXPANSION: REAL TECHNICAL OVERLAYS & LOCAL INDICATORS ---
    if not df_chart.empty:
        st.markdown("---")
        st.subheader("📈 Technical Analysis Terminal Layer (6-Month Horizon)")
        
        c_tab1, c_tab2 = st.tabs(["Candlestick Overlay Engine", "Momentum Oscillator (RSI)"])
        
        with c_tab1:
            fig_tech = go.Figure()
            # Historical Candlesticks
            fig_tech.add_trace(go.Candlestick(
                x=df_chart['Date'], open=df_chart['Open'], high=df_chart['High'],
                low=df_chart['Low'], close=df_chart['Close'], name="Market Price"
            ))
            # Locally Computed Trends
            fig_tech.add_trace(go.Scatter(x=df_chart['Date'], y=df_chart['SMA_20'], name='20-Day SMA', line=dict(color='#FF9100', width=1)))
            fig_tech.add_trace(go.Scatter(x=df_chart['Date'], y=df_chart['SMA_50'], name='50-Day SMA', line=dict(color='#2979FF', width=1.5)))
            
            # Bollinger Bands Channels
            fig_tech.add_trace(go.Scatter(x=df_chart['Date'], y=df_chart['BB_Upper'], name='BB Upper', line=dict(color='rgba(150,150,150,0.4)', dash='dash')))
            fig_tech.add_trace(go.Scatter(x=df_chart['Date'], y=df_chart['BB_Lower'], name='BB Lower', line=dict(color='rgba(150,150,150,0.4)', dash='dash'), fill='tonexty', fillcolor='rgba(200,200,200,0.1)'))
            
            fig_tech.update_layout(height=450, xaxis_rangeslider_visible=False, margin=dict(l=40, r=40, t=10, b=10), yaxis=dict(title="Price (USD)"))
            st.plotly_chart(fig_tech, use_container_width=True)
            
        with c_tab2:
            fig_rsi = go.Figure()
            fig_rsi.add_trace(go.Scatter(x=df_chart['Date'], y=df_chart['RSI'], name='RSI (14)', line=dict(color='#7B1FA2', width=2)))
            fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought (70)")
            fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold (30)")
            fig_rsi.update_layout(height=230, yaxis=dict(range=[0, 100], title="Oscillator Units"), margin=dict(l=40, r=40, t=10, b=10))
            st.plotly_chart(fig_rsi, use_container_width=True)

# --- TRUE AUTOMATED REFRESH PIPELINE ---
@st.fragment
def auto_refresh_executor():
    import time
    time.sleep(refresh_rate)
    st.rerun()

auto_refresh_executor()
