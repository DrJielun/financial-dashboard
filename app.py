import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

# =========================
# SETTINGS
# =========================
ticker = "AAPL"   # change to any ticker
start = "2024-01-01"
end = None

# =========================
# FETCH DATA
# =========================
df = yf.download(ticker, start=start, end=end)

# =========================
# INDICATORS
# =========================
# Moving averages
df["MA20"] = df["Close"].rolling(20).mean()
df["MA50"] = df["Close"].rolling(50).mean()

# MACD
exp1 = df["Close"].ewm(span=12, adjust=False).mean()
exp2 = df["Close"].ewm(span=26, adjust=False).mean()
df["MACD"] = exp1 - exp2
df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

# DMI (simplified)
high = df["High"]
low = df["Low"]
close = df["Close"]

plus_dm = high.diff()
minus_dm = low.diff() * -1

plus_dm[plus_dm < 0] = 0
minus_dm[minus_dm < 0] = 0

tr1 = high - low
tr2 = abs(high - close.shift())
tr3 = abs(low - close.shift())
tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

atr = tr.rolling(14).mean()
df["+DI"] = 100 * (plus_dm.rolling(14).mean() / atr)
df["-DI"] = 100 * (minus_dm.rolling(14).mean() / atr)

# =========================
# PLOT
# =========================
fig, axes = plt.subplots(4, 1, figsize=(12, 10), sharex=True)

# --- PRICE ---
axes[0].plot(df["Close"], label="Price")
axes[0].plot(df["MA20"], linestyle="--", label="MA20")
axes[0].plot(df["MA50"], linestyle=":", label="MA50")
axes[0].set_title(f"{ticker} Price")
axes[0].legend()

# --- MACD ---
axes[1].plot(df["MACD"], linestyle="--", label="MACD")
axes[1].plot(df["Signal"], linestyle=":", label="Signal")
axes[1].axhline(0)
axes[1].set_title("MACD")
axes[1].legend()

# --- DMI ---
axes[2].plot(df["+DI"], linestyle="--", label="+DI")
axes[2].plot(df["-DI"], linestyle=":", label="-DI")
axes[2].set_title("Directional Movement Index (DMI)")
axes[2].legend()

# --- VOLUME ---
axes[3].bar(df.index, df["Volume"])
axes[3].set_title("Volume")

plt.tight_layout()
plt.savefig("fixed_chart.png")
plt.close()

print("Done. Chart saved as fixed_chart.png")
