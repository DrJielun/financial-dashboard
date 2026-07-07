import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==============================
# CONFIG
# ==============================
ticker = "AAPL"   # change to your stock
period = "6mo"
interval = "1d"

# ==============================
# DOWNLOAD DATA
# ==============================
df = yf.download(ticker, period=period, interval=interval)

# ==============================
# RSI (WILDER - FIXED)
# ==============================
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

df["RSI"] = compute_rsi(df["Close"])

# ==============================
# FIX NaN ISSUE
# ==============================
df = df.dropna(subset=["RSI", "Open", "High", "Low", "Close"])

# ==============================
# PLOT (PRICE + RSI PANEL)
# ==============================
fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    row_heights=[0.7, 0.3],
    vertical_spacing=0.05
)

# PRICE (CANDLESTICK)
fig.add_trace(go.Candlestick(
    x=df.index,
    open=df["Open"],
    high=df["High"],
    low=df["Low"],
    close=df["Close"],
    name="Price"
), row=1, col=1)

# RSI PANEL
fig.add_trace(go.Scatter(
    x=df.index,
    y=df["RSI"],
    name="RSI"
), row=2, col=1)

# RSI LEVELS
fig.add_hline(y=70, line_dash="dash", row=2, col=1)
fig.add_hline(y=30, line_dash="dash", row=2, col=1)

# LAYOUT
fig.update_layout(
    title=f"{ticker} Price + RSI",
    xaxis_rangeslider_visible=False
)

fig.show()
