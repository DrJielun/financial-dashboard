
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

def detect_support_resistance(df, window=5, cluster_pct=0.015):
    lows = []
    highs = []

    for i in range(window, len(df) - window):
        if df["Low"].iloc[i] == df["Low"].iloc[i-window:i+window+1].min():
            lows.append(df["Low"].iloc[i])
        if df["High"].iloc[i] == df["High"].iloc[i-window:i+window+1].max():
            highs.append(df["High"].iloc[i])

    def cluster_levels(levels):
        clusters = []
        for lvl in sorted(levels):
            placed = False
            for cluster in clusters:
                if abs(lvl - np.mean(cluster)) / np.mean(cluster) < cluster_pct:
                    cluster.append(lvl)
                    placed = True
                    break
            if not placed:
                clusters.append([lvl])
        return sorted([np.mean(c) for c in clusters], key=lambda x: -len([v for v in levels if abs(v-x)/x < cluster_pct]))

    supports = cluster_levels(lows)[:3]
    resistances = cluster_levels(highs)[:3]

    return supports, resistances

st.title("Stock Analysis with Support Levels")

ticker = st.text_input("Enter Ticker", "AAPL")
df = yf.download(ticker, period="6mo", interval="1d")

if not df.empty:
    supports, resistances = detect_support_resistance(df)

    st.subheader("Support Levels")
    for i, lvl in enumerate(supports, 1):
        st.write(f"Support {i}: {lvl:.2f}")

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="Price"
    ))

    for lvl in supports:
        fig.add_hline(
            y=lvl,
            line_dash="dot",
            line_color="green",
            annotation_text=f"Support {lvl:.2f}",
            annotation_position="bottom right"
        )

    st.plotly_chart(fig)
