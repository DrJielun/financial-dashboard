import streamlit as st
import yfinance as yf

# --- PAGE SETUP ---
st.set_page_config(layout="centered", page_title="Market Session Monitor")
st.title("⏱️ Live Market Session Monitor")

# --- USER INPUT ---
ticker_symbol = st.text_input("Enter Stock Ticker Symbol:", value="AAPL").upper().strip()

if ticker_symbol:
    try:
        # Fetch real-time ticker payload
        with st.spinner(f"Polling Yahoo Finance API for {ticker_symbol}..."):
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
        
        if info and "marketState" in info:
            # Extract session parameters
            market_state = info.get("marketState", "UNKNOWN")
            regular_price = info.get("regularMarketPrice")
            current_price = info.get("currentPrice") or regular_price
            pre_price = info.get("preMarketPrice")
            post_price = info.get("postMarketPrice")
            
            company_name = info.get("longName", ticker_symbol)
            currency = info.get("currency", "USD")
            
            st.subheader(f"🏢 {company_name} ({ticker_symbol})")
            
            # --- EVALUATE EXTENDED HOURS CONDITIONS ---
            if market_state == "PRE" and pre_price:
                st.warning("🌅 MARKET STATE: PRE-MARKET")
                st.metric(
                    label=f"Pre-Market Price ({currency})", 
                    value=f"${pre_price:,.2f}", 
                    delta=f"Last Regular Close: ${regular_price:,.2f}"
                )
                
            elif market_state == "POST" and post_price:
                st.info("🌙 MARKET STATE: POST-MARKET")
                st.metric(
                    label=f"Post-Market Price ({currency})", 
                    value=f"${post_price:,.2f}", 
                    delta=f"Regular Close: ${regular_price:,.2f}"
                )
                
            elif market_state == "REGULAR":
                st.success("🟢 MARKET STATE: REGULAR SESSION (OPEN)")
                st.metric(
                    label=f"Current Live Price ({currency})", 
                    value=f"${current_price:,.2f}"
                )
                
            elif market_state == "CLOSED":
                st.error("🛑 MARKET STATE: CLOSED")
                final_price = post_price if post_price else regular_price
                st.metric(
                    label=f"Final Recorded Price ({currency})", 
                    value=f"${final_price:,.2f}",
                    delta=f"Regular Session Close: ${regular_price:,.2f}" if post_price else None
                )
                
            else:
                st.info(f"🔍 MARKET STATE: {market_state}")
                st.metric(label=f"Current Price ({currency})", value=f"${current_price:,.2f}")
                
        else:
            st.error(f"❌ No valid data returned for ticker '{ticker_symbol}'. Please verify the symbol.")
            
    except Exception as e:
        st.error(f"❌ Failed to fetch data: {e}")

st.caption("Data dynamically sourced from Yahoo Finance API via yfinance backend layer.")
