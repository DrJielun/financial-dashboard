
# ===== PRO SMART METRICS PANEL (FIXED LAYOUT) =====
import streamlit as st
import pandas as pd

st.markdown("---")
st.markdown("## Smart Metrics")

try:
    def get_ext(t):
        try:
            i = t.info
            return i.get("preMarketPrice"), i.get("postMarketPrice")
        except:
            return None, None

    pre, post = get_ext(ticker)

    sma50 = df['Close'].rolling(50).mean().iloc[-1]
    sma200 = df['Close'].rolling(200).mean().iloc[-1]

    # --- CROSS DETECTION ---
    cross_signal = "N/A"
    if not pd.isna(sma50) and not pd.isna(sma200):
        if sma50 > sma200:
            cross_signal = "🟢 Golden"
        else:
            cross_signal = "🔴 Death"

    # --- ADX TREND ---
    trend_signal = "N/A"
    if 'adx' in locals() and not adx.empty:
        val = adx.iloc[-1]
        if val < 20:
            trend_signal = "Weak"
        elif val < 40:
            trend_signal = "Strong"
        else:
            trend_signal = "Very Strong"

    # ===== ROW 1 =====
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("RSI", f"{rsi.iloc[-1]:.2f}" if 'rsi' in locals() else "N/A")
    col2.metric("ADX", f"{adx.iloc[-1]:.2f}" if 'adx' in locals() else "N/A")
    col3.metric("Trend", trend_signal)
    col4.metric("MACD", f"{macd.iloc[-1]:.2f}" if 'macd' in locals() else "N/A")

    # ===== ROW 2 =====
    col5, col6, col7, col8 = st.columns(4)
    col5.metric("SMA50", f"{sma50:.2f}")
    col6.metric("SMA200", f"{sma200:.2f}")
    col7.metric("Cross", cross_signal)
    col8.metric("Pre/Post", 
                f"{pre:.2f} / {post:.2f}" if pre and post else "N/A")

except Exception as e:
    st.error(f"Metrics error: {e}")
