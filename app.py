import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import numpy as np

st.set_page_config(layout="wide", page_title="Institutional Equity Terminal")

# --- SIDEBAR INTERFACE & REFRESH TIMERS ---
st.sidebar.header("📊 Terminal Controls")
ticker_symbol = st.sidebar.text_input("Enter Stock Ticker:", value="NVDA").upper().strip()

refresh_rate = st.sidebar.slider("Auto-Refresh Interval (Seconds):", min_value=10, max_value=300, value=30)
st.sidebar.caption(f"🔄 App auto-refreshes execution loop every {refresh_rate} seconds.")

# --- COMPREHENSIVE LIVE RETRIEVAL ENGINE ---
@st.cache_data(ttl=refresh_rate)
def fetch_complete_equity_dataset(ticker):
    # Consolidates live quotes, multi-period history, and underlying balance modules
    summary_url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=defaultKeyStatistics,financialData,price,summaryDetail"
    chart_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=6m"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    results = {"summary": None, "chart": None, "error_type": None}
    
    # 1. Gather Fundamental Blocks
    try:
        sum_resp = requests.get(summary_url, headers=headers, timeout=7)
        sum_resp.raise_for_status()
        sum_data = sum_resp.json()
        
        if sum_data.get('quoteSummary', {}).get('result'):
            results["summary"] = sum_data['quoteSummary']['result'][0]
        else:
            results["error_type"] = "INVALID_TICKER"
            return results
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            results["error_type"] = "INVALID_TICKER"
        else:
            results["error_type"] = f"HTTP_{e.response.status_code}"
        return results
    except requests.exceptions.Timeout:
        results["error_type"] = "TIMEOUT"
        return results
    except requests.exceptions.RequestException:
        results["error_type"] = "NETWORK_ERROR"
        return results

    # 2. Gather Historical Technical Arrays
    try:
        chart_resp = requests.get(chart_url, headers=headers, timeout=7)
        chart_resp.raise_for_status()
        chart_data = chart_resp.json()
        if chart_data.get('chart', {}).get('result'):
            results["chart"] = chart_data['chart']['result'][0]
    except Exception:
        pass # Graceful fallback if only history fails but core metrics loaded
        
    return results

# Run Network Calls
data_package = fetch_complete_equity_dataset(ticker_symbol)

# --- STRICT EXCEPTION ROUTING ---
if data_package["error_type"] is not None:
    if data_package["error_type"] == "INVALID_TICKER":
        st.error(f"❌ Unknown Ticker Asset: '{ticker_symbol}' could not be located on global exchanges.")
        st.info("Verify the suffix conventions for global entries (e.g. TSM for US ADR, or 2330.TW for local market boards).")
    elif data_package["error_type"] == "TIMEOUT":
        st.error("⏰ Network Pipeline Timeout: Yahoo Finance servers took too long to respond.")
    else:
        st.error(f"🌐 Data Pipeline Interrupted: {data_package['error_type']}")
    st.stop()

# --- DEFENSIVE STRUCTURAL PARSING LAYER ---
summary = data_package["summary"]
chart = data_package["chart"]

if summary:
    stats = summary.get('defaultKeyStatistics', {})
    financials = summary.get('financialData', {})
    price = summary.get('price', {})
    detail = summary.get('summaryDetail', {})

    # Helper function preserves None natively until string layout formatting rules trigger
    def extract_node_value(nested_dict, key, target='raw'):
        node = nested_dict.get(key)
        if isinstance(node, dict):
            return node.get(target)
        return node

    # Core Meta Parsing
    company_name = price.get('longName', ticker_symbol)
    exchange = price.get('exchangeName', 'Global Venue')
    sector = lookup_sector = financials.get('sector', stats.get('sector', 'Technology')) 

    # Live Core Metrics Cross-Referencing Alternate Sub-structures Defensively
    current_price = extract_node_value(financials, 'currentPrice') or extract_node_value(price, 'regularMarketPrice')
    prev_close = extract_node_value(price, 'regularMarketPreviousClose') or extract_node_value(detail, 'previousClose')
    
    price_change = current_price - prev_close if current_price and prev_close else 0.0
    price_pct = (price_change / prev_close) * 100 if prev_close else 0.0

    # Valuation & Multiples
    pe_ratio = extract_node_value(stats, 'trailingPE') or extract_node_value(detail, 'trailingPE')
    forward_pe = extract_node_value(stats, 'forwardPE') or extract_node_value(detail, 'forwardPE')
    ps_ratio = extract_node_value(stats, 'priceToSalesTrailing12Months') or extract_node_value(detail, 'priceToSales')
    pb_ratio = extract_node_value(stats, 'priceToBook') or extract_node_value(detail, 'priceToBook')
    peg_ratio = extract_node_value(stats, 'pegRatio')
    beta = extract_node_value(stats, 'beta') or extract_node_value(detail, 'beta')

    # Income Statement & Scale
    revenue = extract_node_value(financials, 'totalRevenue')
    ebitda = extract_node_value(financials, 'ebitda')
    eps = extract_node_value(stats, 'trailingEps')
    gross_margin = extract_node_value(financials, 'grossMargins')
    ebitda_margin = extract_node_value(financials, 'ebitdaMargins')
    profit_margin = extract_node_value(financials, 'profitMargins')
    operating_margin = extract_node_value(financials, 'operatingMargins')

    # Balance Sheet & Efficiency
    total_debt = extract_node_value(financials, 'totalDebt')
    fcf = extract_node_value(financials, 'freeCashflow')
    shares_outstanding = extract_node_value(stats, 'sharesOutstanding')
    current_ratio = extract_node_value(financials, 'currentRatio')
    quick_ratio = extract_node_value(financials, 'quickRatio')
    roe = extract_node_value(financials, 'returnOnEquity')
    roa = extract_node_value(financials, 'returnOnAssets')

    # Market Activity Context
    market_cap = extract_node_value(price, 'marketCap') or extract_node_value(detail, 'marketCap')
    ev = extract_node_value(stats, 'enterpriseValue')
    div_yield = extract_node_value(detail, 'dividendYield')
    target_price = extract_node_value(financials, 'targetMeanPrice')
    rec_mean = extract_node_value(financials, 'recommendationMean')
    high_52 = extract_node_value(detail, 'fiftyTwoWeekHigh')
    low_52 = extract_node_value(detail, 'fiftyTwoWeekLow')
    avg_vol = extract_node_value(detail, 'averageVolume')

    # --- LOCALIZED TECHNICAL INDICATORS COMPUTATION ENGINE ---
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
                
                # Relative Strength Index (RSI) Calculation
                delta = df_chart['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / (loss + 1e-9)
                df_chart['RSI'] = 100 - (100 / (1 + rs))
        except Exception:
            pass

    # --- SECTOR-AWARE VALUATION GRID ENGINE ---
    def calculate_sector_adjusted_scores():
        is_growth_sector = any(s in str(sector) for s in ["Technology", "Communication", "Consumer Cyclical"])
        
        # Valuation Grading Mapping Vector
        if pe_ratio is None: val_score = 3
        elif is_growth_sector: val_score = 5 if pe_ratio < 28 else (3 if pe_ratio < 50 else 1)
        else: val_score = 5 if pe_ratio < 16 else (3 if pe_ratio < 28 else 1)
        
        # Profitability Grading Mapping Vector
        if roe is None: prof_score = 3
        else: prof_score = 5 if roe > 0.22 else (3 if roe > 0.10 else 1)
        
        # Financial Health Vector
        if current_ratio is None: health_score = 3
        else: health_score = 5 if current_ratio > 1.4 else (3 if current_ratio > 0.9 else 1)
        
        # Performance Indicators Matrix Array Summary
        return [4 if is_growth_sector else 3, prof_score, 4 if is_growth_sector else 2, health_score, val_score]

    scores = calculate_sector_adjusted_scores()

    # --- UI DISPLAY FRAMEWORK RENDERING ---
    st.caption("Financial Analysis Workspace • Near Real-Time Quotes via Yahoo Finance")
    st.title(f"({ticker_symbol}) {company_name}")
    st.caption(f"Primary Listing Venue: **{exchange}**")

    # Header Row Data Block
    h_col1, h_col2, h_col3, h_col4 = st.columns(4)
    h_col1.metric("Current Market Price", f"${current_price:,.2f}" if current_price else "N/A", f"{price_change:+.2f} ({price_pct:+.2f}%)")
    h_col2.metric("Market Capitalization", f"${market_cap/1e9:,.2f}B" if market_cap else "N/A")
    h_col3.metric("Enterprise Value (EV)", f"${ev/1e9:,.2f}B" if ev else "N/A")
    h_col4.metric("Analyst Consensus Target", f"${target_price:,.2f}" if target_price else "N/A")

    st.markdown("---")
    
    col_left, col_right = st.columns([1, 1])

    # --- LEFT COLUMN: CORE FUNDAMENTAL TABLES ---
    with col_left:
        st.subheader("Key Valuation & Operations Matrix")
        
        def format_cell(val, style='num'):
            if val is None or pd.isna(val): return "N/A"
            if style == 'pct': return f"{val * 100:.2f}%"
            if style == 'curr': return f"{val / 1e6:,.2f}M"
            return f"{val:,.2f}"

        metrics_block_1 = [
            ("Price to Earnings Ratio (TTM)", format_cell(pe_ratio)),
            ("Forward P/E Ratio", format_cell(forward_pe)),
            ("Price to Sales Ratio (TTM)", format_cell(ps_ratio)),
            ("Price to Book Ratio (TTM)", format_cell(pb_ratio)),
            ("PEG Valuation Multiplier", format_cell(peg_ratio)),
            ("Beta Systematic Volatility", format_cell(beta)),
            ("Trailing Earnings Per Share (EPS)", format_cell(eps)),
            ("Dividend Yield Target Rate", format_cell(div_yield, 'pct'))
        ]
        
        metrics_block_2 = [
            ("Gross Profit Margin (TTM)", format_cell(gross_margin, 'pct')),
            ("EBITDA Operations Margin", format_cell(ebitda_margin, 'pct')),
            ("Net Profit Margin (TTM)", format_cell(profit_margin, 'pct')),
            ("Operating Margin (TTM)", format_cell(operating_margin, 'pct')),
            ("Return on Equity (ROE)", format_cell(roe, 'pct')),
            ("Return on Assets (ROA)", format_cell(roa, 'pct')),
            ("Current Liquidity Ratio", format_cell(current_ratio)),
            ("Quick Assets Acid Test", format_cell(quick_ratio))
        ]

        metrics_block_3 = [
            ("Total Revenue Turnover", format_cell(revenue, 'curr')),
            ("EBITDA Financial Performance", format_cell(ebitda, 'curr')),
            ("Free Cash Flow Allocation", format_cell(fcf, 'curr')),
            ("Total Outstanding Capital Shares", format_cell(shares_outstanding, 'curr')),
            ("Total Capital Debt Load", format_cell(total_debt, 'curr')),
            ("52-Week Market Peak High", format_cell(high_52)),
            ("52-Week Market Floor Low", format_cell(low_52)),
            ("Average Trading Session Volume", format_cell(avg_vol))
        ]

        sub_tab1, sub_tab2, sub_tab3 = st.tabs(["Multiples & Ratios", "Margins & Returns", "Volume & Scale Balance"])
        with sub_tab1: st.dataframe(pd.DataFrame(metrics_block_1, columns=["Metric Parameters", "Current Value"]), hide_index=True, use_container_width=True)
        with sub_tab2: st.dataframe(pd.DataFrame(metrics_block_2, columns=["Metric Parameters", "Current Value"]), hide_index=True, use_container_width=True)
        with sub_tab3: st.dataframe(pd.DataFrame(metrics_block_3, columns=["Metric Parameters", "Current Value"]), hide_index=True, use_container_width=True)

    # --- RIGHT COLUMN: PERFORMANCE GRAPH RATING CHANNEL ---
    with col_right:
        st.subheader("Contextual Core Strengths Scorecard")
        categories = ['Predictability', 'Profitability', 'Growth', 'Financial Strength', 'Valuation']
        
        fig_score = go.Figure()
        fig_score.add_trace(go.Scatter(
            x=categories, y=scores, mode='lines+markers',
            line=dict(color='#1B5E20', width=3), marker=dict(size=10, color='#FFD600')
        ))
        fig_score.update_layout(
            yaxis=dict(range=[0, 6], showgrid=True, tickvals=[1,2,3,4,5], ticktext=['Low','','Medium','','High']),
            height=280, margin=dict(l=40, r=40, t=20, b=40)
        )
        st.plotly_chart(fig_score, use_container_width=True)

    # --- LOWER EXPANSION: LIVE TECHNICAL OVERLAYS & LOCAL CALCULATIONS ---
    if not df_chart.empty:
        st.markdown("---")
        st.subheader("📈 Live Technical Analysis Terminal Layer (6-Month Horizon)")
        
        c_tab1, c_tab2 = st.tabs(["Candlestick Overlay Engine", "Momentum Oscillator (RSI)"])
        
        with c_tab1:
            fig_tech = go.Figure()
            # Candlestick Array
            fig_tech.add_trace(go.Candlestick(
                x=df_chart['Date'], open=df_chart['Open'], high=df_chart['High'],
                low=df_chart['Low'], close=df_chart['Close'], name="Market Price"
            ))
            # Locally Computed Moving Averages
            fig_tech.add_trace(go.Scatter(x=df_chart['Date'], y=df_chart['SMA_20'], name='20-Day SMA', line=dict(color='#FF9100', width=1)))
            fig_tech.add_trace(go.Scatter(x=df_chart['Date'], y=df_chart['SMA_50'], name='50-Day SMA', line=dict(color='#2979FF', width=1.5)))
            # Bollinger Bands
            fig_tech.add_trace(go.Scatter(x=df_chart['Date'], y=df_chart['BB_Upper'], name='BB Upper', line=dict(color='rgba(150,150,150,0.4)', dash='dash')))
            fig_tech.add_trace(go.Scatter(x=df_chart['Date'], y=df_chart['BB_Lower'], name='BB Lower', line=dict(color='rgba(150,150,150,0.4)', dash='dash'), fill='tonexty', fillcolor='rgba(200,200,200,0.1)'))
            
            fig_tech.update_layout(height=450, xaxis_rangeslider_visible=False, margin=dict(l=40, r=40, t=10, b=10), yaxis=dict(title="Price (USD)"))
            st.plotly_chart(fig_tech, use_container_width=True)
            
        with c_tab2:
            fig_rsi = go.Figure()
            fig_rsi.add_trace(go.Scatter(x=df_chart['Date'], y=df_chart['RSI'], name='RSI (14)', line=dict(color='#7B1FA2', width=2)))
            # Standard Overbought / Oversold Support/Resistance Channels
            fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought (70)")
            fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold (30)")
            fig_rsi.update_layout(height=250, yaxis=dict(range=[0, 100], title="Oscillator Units"), margin=dict(l=40, r=40, t=10, b=10))
            st.plotly_chart(fig_rsi, use_container_width=True)

# --- TRUE PERIODIC AUTO-REFRESH TRIGGER (FRAGMENT LOOP) ---
@st.fragment
def auto_refresh_executor():
    import time
    time.sleep(refresh_rate)
    st.rerun()

auto_refresh_executor()
