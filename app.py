import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# --- 1. CONFIGURATION & APP INITIALIZATION ---
st.set_page_config(layout="wide", page_title="JL Quant")
st.title("JL Quant")

# --- TICKER INPUT ---
st.sidebar.header("Ticker")
ticker_symbol = st.sidebar.text_input("Ticker Symbol:", value="AAPL").upper().strip()

# --- TIMEFRAME SUPPORT CONTROLS ---
timeframe_opts = {
    "1 Month": {"period": "1mo"},
    "3 Months": {"period": "3mo"},
    "6 Months": {"period": "6mo"},
    "1 Year": {"period": "1y"},
    "2 Years": {"period": "2y"},
    "5 Years": {"period": "5y"}
}
selected_tf = st.sidebar.selectbox("Terminal Analysis Horizon:", list(timeframe_opts.keys()), index=3)
period_val = timeframe_opts[selected_tf]["period"]

benchmark_sym = st.sidebar.selectbox("Relative Strength Benchmark:", ["SPY", "QQQ", "XLK"], index=0)

# --- AUTO-REFRESH CONFIGURATION ---
refresh_rate = st.sidebar.slider("Live Data Auto-Refresh (Seconds):", min_value=10, max_value=60, value=15)
st.components.v1.html(
    f"""
    <script>
        window.setTimeout(function() {{
            window.location.reload();
        }}, {refresh_rate * 1000});
    </script>
    """,
    height=0,
)

if not ticker_symbol.isalnum():
    st.sidebar.warning("⚠️ Invalid ticker format detected.")
    st.stop()

# --- LONGLIVED RAW DATA & INFRASTRUCTURE CACHING ---
@st.cache_data(ttl=86400, max_entries=100)
def fetch_ticker_info_blob(ticker_str):
    try:
        return yf.Ticker(ticker_str).info
    except Exception:
        return {}

@st.cache_data(ttl=300)
def fetch_longlived_metadata(ticker_str):
    t=yf.Ticker(ticker_str)
    fast=getattr(t,"fast_info",{}) or {}
    try:
        info=t.info or {}
    except Exception:
        info={}
    payload={}
    payload["longName"]=info.get("longName") or info.get("shortName") or fast.get("shortName") or ticker_str
    price=fast.get("lastPrice") or info.get("currentPrice") or info.get("regularMarketPrice")
    shares=info.get("sharesOutstanding") or fast.get("shares")
    payload["marketCap"]=info.get("marketCap") or (price*shares if price and shares else None)
    for k in ["beta","averageVolume","trailingPE","forwardPE","pegRatio","priceToBook","dividendYield","returnOnEquity","profitMargins","operatingMargins","earningsGrowth","revenueGrowth","debtToEquity","currentRatio","fiftyTwoWeekHigh","fiftyTwoWeekLow","sharesOutstanding","floatShares","shortPercentOfFloat","targetMeanPrice"]:
        payload[k]=info.get(k)
    payload["avg_volume"]=payload.pop("averageVolume")
    payload["pe_trailing"]=payload.pop("trailingPE")
    payload["pe_forward"]=payload.pop("forwardPE")
    payload["peg"]=payload.pop("pegRatio")
    payload["pb"]=payload.pop("priceToBook")
    payload["roe"]=payload.pop("returnOnEquity")
    payload["net_margin"]=payload.pop("profitMargins")
    payload["op_margin"]=payload.pop("operatingMargins")
    payload["eps_growth"]=payload.pop("earningsGrowth")
    payload["rev_growth"]=payload.pop("revenueGrowth")
    payload["debt_equity"]=payload.pop("debtToEquity")
    payload["current_ratio"]=payload.pop("currentRatio")
    payload["shortInterest"]=payload.pop("shortPercentOfFloat")
    payload["targetPrice"]=payload.pop("targetMeanPrice")
    return payload

# --- LAYER 1: DATA INGESTION ---
@st.cache_data(ttl=60, max_entries=50)
def get_raw_market_data(ticker_str, benchmark_str, period_str):
    try:
        stock = yf.Ticker(ticker_str)
        history = stock.history(period=period_str, interval="1d")
        if history.empty:
            return None, None, None
            
        bench = yf.Ticker(benchmark_str)
        bench_hist = bench.history(period=period_str, interval="1d")
        
        fast_payload = {
            "prev_close": history['Close'].tail(2).iloc[0] if len(history) > 1 else history['Close'].iloc[-1]
        }
        return history, bench_hist, fast_payload
    except Exception:
        return None, None, None

# --- LAYER 2: INSTITUTIONAL QUANT ENGINE ---
@st.cache_data(ttl=30)
def compute_technical_indicators(df_history, df_bench):
    df = df_history.copy()
    
    df['SMA50'] = df['Close'].rolling(window=min(50, len(df))).mean()
    df['SMA200'] = df['Close'].rolling(window=min(200, len(df))).mean()
    df['MA20'] = df['Close'].rolling(window=min(20, len(df))).mean()
    df['Std20'] = df['Close'].rolling(window=min(20, len(df))).std()
    df['BB_Upper'] = df['MA20'] + (2 * df['Std20'])
    df['BB_Lower'] = df['MA20'] - (2 * df['Std20'])
    df['Vol_Bandwidth'] = np.where(df['MA20'] > 0, (df['BB_Upper'] - df['BB_Lower']) / df['MA20'], np.nan)
    
    df['BB_Squeeze'] = df['Vol_Bandwidth'] < df['Vol_Bandwidth'].rolling(window=min(126, len(df)), min_periods=1).quantile(0.20)
    
    delta = df['Close'].diff()
    gain, loss = delta.clip(lower=0), -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + (avg_gain / avg_loss.replace(0, np.nan))))
    
    df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    
    high, low, close = df['High'], df['Low'], df['Close']
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)

    df['ATR'] = tr.ewm(alpha=1/14, adjust=False).mean()
    df['PlusDI'] = 100 * (pd.Series(plus_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() / df['ATR'].replace(0, np.nan))
    df['MinusDI'] = 100 * (pd.Series(minus_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() / df['ATR'].replace(0, np.nan))
    df['ADX'] = ((abs(df['PlusDI'] - df['MinusDI']) / (df['PlusDI'] + df['MinusDI']).replace(0, np.nan)) * 100).ewm(alpha=1/14, adjust=False).mean()
    
    df['RVOL'] = df['Volume'] / df['Volume'].rolling(window=min(20, len(df))).mean().replace(0, np.nan)
    
    stock_ret = (1 + df['Close'].pct_change()).cumprod()
    bench_ret = (1 + df_bench['Close'].pct_change().reindex(df.index, method='ffill')).cumprod()
    df['Alpha_Strength'] = stock_ret - bench_ret
    
    return df



# ===== Added: Trading Signals & Support/Resistance =====
def generate_trading_signals(df):
    latest=df.iloc[-1]
    signals={}
    if pd.notna(latest["SMA50"]) and pd.notna(latest["SMA200"]):
        if latest["Close"]>latest["SMA50"]>latest["SMA200"]:
            signals["Trend"]=("Bullish",1)
        elif latest["Close"]<latest["SMA50"]<latest["SMA200"]:
            signals["Trend"]=("Bearish",-1)
        else:
            signals["Trend"]=("Neutral",0)
    signals["RSI"]=("Oversold",1) if latest["RSI"]<30 else ("Overbought",-1) if latest["RSI"]>70 else ("Neutral",0)
    signals["MACD"]=("Bullish",1) if latest["MACD"]>latest["MACD_Signal"] else ("Bearish",-1)
    signals["ADX"]=("Strong Trend",1) if latest["ADX"]>25 else ("Weak Trend",0)
    if latest["Close"]>latest["BB_Upper"]:
        signals["Bollinger"]=("Above Upper",-1)
    elif latest["Close"]<latest["BB_Lower"]:
        signals["Bollinger"]=("Below Lower",1)
    else:
        signals["Bollinger"]=("Inside Bands",0)
    signals["Volume"]=("High",1) if latest["RVOL"]>1.5 else ("Normal",0)
    score=sum(v[1] for v in signals.values())
    rating="🟢 Strong Buy" if score>=4 else "🟢 Buy" if score>=2 else "🟡 Hold" if score>=0 else "🟠 Weak Sell" if score>=-2 else "🔴 Strong Sell"
    confidence=round((score+6)/12*100)
    return signals,rating,confidence

def detect_support_resistance(df,window=10):
    highs=[];lows=[]
    for i in range(window,len(df)-window):
        if df["High"].iloc[i]==df["High"].iloc[i-window:i+window+1].max(): highs.append(df["High"].iloc[i])
        if df["Low"].iloc[i]==df["Low"].iloc[i-window:i+window+1].min(): lows.append(df["Low"].iloc[i])
    return sorted(set(lows))[:5],sorted(set(highs),reverse=True)[:5]

# --- LAYER 3: LAYOUT MATRIX RENDERING ENGINE ---
with st.spinner("Executing real-time pipeline algorithms..."):
    raw_history, bench_history, info_payload = get_raw_market_data(ticker_symbol, benchmark_sym, period_val)

if raw_history is not None and info_payload is not None:
    fnd = fetch_longlived_metadata(ticker_symbol)
    df_view = compute_technical_indicators(raw_history, bench_history)
    support_levels,resistance_levels=detect_support_resistance(df_view)
    signals,rating,confidence=generate_trading_signals(df_view)
    
    latest = df_view.iloc[-1]
    sma_available = pd.notna(latest["SMA50"]) and pd.notna(latest["SMA200"])
    latest_squeeze = latest['BB_Squeeze']
    
    latest_close = latest['Close']
    prev_close = info_payload['prev_close']
    price_change = latest_close - prev_close
    pct_change = (price_change / prev_close) * 100 if prev_close else 0.0
    
    high_52w = fnd["fiftyTwoWeekHigh"] or df_view["High"].max()
    low_52w = fnd["fiftyTwoWeekLow"] or df_view["Low"].min()
    price_position_pct = ((latest_close - low_52w) / (high_52w - low_52w)) * 100 if high_52w != low_52w else 50.0
    
    main_layout, fundamental_sidebar = st.columns([2.3, 0.7])
    
    with main_layout:
        st.subheader(f"🏢 {ticker_symbol} ({fnd['longName']}) — Terminal View")
        col_h1, col_h2, col_h3, col_h4 = st.columns(4)
        col_h1.metric("Closing Value (USD)", f"${latest_close:,.2f}", f"${price_change:+.2f} ({pct_change:+.2f}%)")
        col_h2.metric("Relative Volume (RVOL)", f"{latest['RVOL']:.2f}x" if pd.notna(latest['RVOL']) else "N/A", "vs 20-Day Mean")
        col_h3.metric("52-Week Range Position", f"{price_position_pct:.1f}%", f"Floor: ${low_52w:.1f}")
        col_h4.metric("Analyst Target", f"${fnd['targetPrice']:.2f}" if fnd.get("targetPrice") else "N/A")

        st.markdown("---")
        st.subheader("📊 Trading Signals")
        c1,c2=st.columns([1,2])
        with c1:
            st.metric("Overall Rating",rating)
            st.metric("Confidence",f"{confidence}%")
        with c2:
            st.dataframe(pd.DataFrame({"Indicator":list(signals.keys()),"Status":[v[0] for v in signals.values()]}),hide_index=True,use_container_width=True)
        latest_rsi = latest['RSI']
        latest_upper_bb = latest['BB_Upper']
        latest_lower_bb = latest['BB_Lower']
        latest_adx = latest['ADX']
        
        if sma_available:
            trend_factor = np.clip(((latest['SMA50'] - latest['SMA200']) / latest['SMA200']) * 10, -1.0, 1.0)
        else:
            trend_factor = 0.0

        norm_rsi = ((latest_rsi - 50) / 20) if pd.notna(latest_rsi) else 0.0
        norm_macd = 1.0 if latest['MACD'] > latest['MACD_Signal'] else -1.0
        momentum_factor = np.clip((0.6 * norm_rsi) + (0.4 * norm_macd), -1.0, 1.0)

        pct_b = (latest_close - latest_lower_bb) / (latest_upper_bb - latest_lower_bb) if latest_upper_bb != latest_lower_bb else 0.5
        volatility_factor = np.clip((pct_b - 0.5) * 2, -1.0, 1.0)
        if pd.notna(latest['Vol_Bandwidth']):
            volatility_factor *= (latest['Vol_Bandwidth'] * 5)
        volatility_factor = np.clip(volatility_factor, -1.0, 1.0)

        composite_score = trend_factor + momentum_factor + volatility_factor
        composite_score *= (1.10 if (pd.notna(latest_adx) and latest_adx > 25.0) else 0.70)
        
        if latest_squeeze: regime_label = "Compression / Volatility Squeeze"
        elif latest_adx >= 25.0 and trend_factor > 0.3: regime_label = "Strong Bullish Breakout Trend"
        elif latest_adx >= 25.0 and trend_factor < -0.3: regime_label = "Strong Bearish Distribution Trend"
        elif latest_rsi > 70.0: regime_label = "Momentum Extension / Mean Reversion Setup"
        elif latest_rsi < 30.0: regime_label = "Momentum Exhaustion / Mean Reversion Setup"
        else: regime_label = "Accumulation / Range Bound Drift"
            
        if composite_score >= 0.25: render_box = st.success
        elif composite_score <= -0.25: render_box = st.error
        else: render_box = st.info
        render_box(f"#### **Market Regime Classification: {regime_label}** (Composite Signal Score: {composite_score:+.2f})")

        trend_state = "Strong Bullish" if trend_factor > 0.4 else ("Moderate Bullish" if trend_factor > 0 else "Bearish Structure")
        mom_state = "Expanding Upside" if momentum_factor > 0.3 else ("Weakening / Cool Down" if momentum_factor < -0.3 else "Neutral Inactive")
        vol_state = "Expanding Bandwidth" if latest['Vol_Bandwidth'] > 0.15 else "Contracting Squeeze"
        alpha_state = "Outperforming Index" if latest['Alpha_Strength'] > 0 else "Underperforming Benchmark Index"
        risk_clause = "Overextended near upper Bollinger line boundaries." if pct_b > 0.85 else "Stable trading inside price distribution bands."
        
        st.info(f"📋 **Adaptive Regime Overview:**\n"
                f"* **Trend Vector:** `{trend_state}` | **Momentum Speed:** `{mom_state}`\n"
                f"* **Volatility Context:** `{vol_state}` | **Alpha Return profile:** `{alpha_state}`\n"
                f"* **Risk Vector Guard:** {risk_clause}")

        st.markdown("---")
        fig = make_subplots(
            rows=5,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.04,
            row_heights=[0.56,0.12,0.14,0.09,0.09])
        )
        
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['BB_Upper'], mode='lines', line=dict(color='rgba(0, 230, 118, 0.25)', width=1), showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['BB_Lower'], mode='lines', line=dict(color='rgba(0, 230, 118, 0.25)', width=1), fill='tonexty', fillcolor='rgba(0, 230, 118, 0.02)', name='Bollinger Bands (20,2)'), row=1, col=1)
        
        fig.add_trace(go.Candlestick(x=df_view.index, open=df_view['Open'], high=df_view['High'], low=df_view['Low'], close=df_view['Close'], name='Price Bars'), row=1, col=1)
        
        if sma_available:
            fig.add_trace(go.Scatter(x=df_view.index, y=df_view['SMA50'], mode='lines', name='50-Day SMA', line=dict(color='#FBC02D', width=1.5, dash='dash')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_view.index, y=df_view['SMA200'], mode='lines', name='200-Day SMA', line=dict(color='#D32F2F', width=1.5, dash='dot')), row=1, col=1)
            
        fig.add_trace(go.Bar(x=df_view.index, y=df_view['Volume'], name='Volume Traded', marker_color='rgba(33, 150, 243, 0.30)'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['MACD'], mode='lines', name='MACD Line', line=dict(color='#29B6F6', width=1.5)), row=3, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['MACD_Signal'], mode='lines', name='MACD Signal', line=dict(color='#AB47BC', width=1.2, dash='dot')), row=3, col=1)
        
        fig.add_trace(go.Bar(x=df_view.index,y=df_view['MACD_Hist'],name='MACD Histogram'), row=3,col=1)

        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['ADX'], mode='lines', name='ADX Strength Line', line=dict(color='#FF9100', width=2.5)), row=4, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['PlusDI'], mode='lines', name='+DI Channel', line=dict(color='#00E676', width=1.2, dash='dash')), row=5, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['MinusDI'], mode='lines', name='-DI Channel', line=dict(color='#FF5252', width=1.2, dash='dot')), row=5, col=1)

        for lvl in support_levels:
            fig.add_hline(y=lvl,line_dash="dot",line_color="green",annotation_text=f"S {lvl:.2f}", row=1,col=1)
        for lvl in resistance_levels:
            fig.add_hline(y=lvl,line_dash="dot",line_color="red",annotation_text=f"R {lvl:.2f}", row=1,col=1)
        fig.update_layout(
            height=1100, margin=dict(l=60, r=40, t=90, b=50), template="plotly_dark",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), 
            xaxis=dict(rangeslider=dict(visible=False)),
            yaxis=dict(title="Asset Price"), yaxis2=dict(title="Volume / MACD Matrix"), yaxis3=dict(title="DMI Core Tracking Matrix")
        )
        st.plotly_chart(fig, use_container_width=True)

    with fundamental_sidebar:
        st.markdown("### 📋 Quant Fundamentals")
        def fmt_v(v, f="num"):
            if v is None or pd.isna(v): return "N/A"
            if f == "pct": return f"{v * 100:.2f}%"
            if f == "mcap": return f"${v / 1e12:.2f}T" if v >= 1e12 else f"${v / 1e9:.2f}B"
            if f == "vol": return f"{v / 1e6:.2f}M"
            return f"{v:.2f}"

        st.markdown("#### **Corporate Overview**")
        st.markdown(f"**Market Cap:** `{fmt_v(fnd['marketCap'], 'mcap')}`")
        st.markdown(f"**Beta Risk Value:** `{fmt_v(fnd['beta'])}`")
        st.markdown(f"**Average Volume:** `{fmt_v(fnd['avg_volume'], 'vol')}`")
        st.markdown(f"**Shares Outstanding:** `{fmt_v(fnd['sharesOutstanding'], 'vol')}`")
        st.markdown(f"**Float Percentage:** `{fmt_v(fnd['floatShares'], 'vol')}`")
        st.markdown(f"**Short % of Float:** `{fmt_v(fnd['shortInterest'], 'pct')}`")
        
        st.markdown("---")
        st.markdown("#### **Valuation Matrix**")
        st.markdown(f"**Trailing P/E:** `{fmt_v(fnd['pe_trailing'])}`")
        st.markdown(f"**Forward P/E:** `{fmt_v(fnd['pe_forward'])}`")
        st.markdown(f"**PEG Ratio (Growth):** `{fmt_v(fnd['peg'])}`")
        st.markdown(f"**Price to Book:** `{fmt_v(fnd['pb'])}`")
        st.markdown(f"**Dividend Yield:** `{fmt_v(fnd['dividendYield'], 'pct')}`")
        
        st.markdown("---")
        st.markdown("#### **Operating Ledger Margins**")
        st.markdown(f"**Return on Equity (ROE):** `{fmt_v(fnd['roe'], 'pct')}`")
        st.markdown(f"**Net Profit Margin:** `{fmt_v(fnd['net_margin'], 'pct')}`")
        st.markdown(f"**Operating Margin:** `{fmt_v(fnd['op_margin'], 'pct')}`")
        st.markdown(f"**Earnings Growth (YoY):** `{fmt_v(fnd['eps_growth'], 'pct')}`")
        st.markdown(f"**Revenue Growth (YoY):** `{fmt_v(fnd['rev_growth'], 'pct')}`")
        
        st.markdown("---")
        st.markdown("#### **Balance Sheet Strength**")
        de_val = fnd['debt_equity']
        de_str = f"{de_val:.2f}%" if (pd.notna(de_val) and de_val > 5.0) else fmt_v(de_val, "pct")
        st.markdown(f"**Debt to Equity:** `{de_str}`")
        st.markdown(f"**Current Ratio:** `{fmt_v(fnd['current_ratio'])}`")

    st.markdown("---")
    st.caption("Terminal analysis complete. Data refreshed and cached locally.")

else:
    st.error(f"❌ Core Data Exception: Historical records for symbol '{ticker_symbol}' could not be safely parsed.")
