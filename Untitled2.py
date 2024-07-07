#!/usr/bin/env python
# coding: utf-8

# In[4]:


import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import concurrent.futures

def main():
    st.title("Stock Analysis App")

    # Get user input for stock tickers
    tickers = st.text_input("Enter stock tickers (separated by commas, no spaces):")
    ticker_list = [ticker.strip() for ticker in tickers.split(",")]

    # Get user input for anchored VWAP date
    anchored_vwap_date = st.date_input("Select anchored VWAP date")

    # Get user input for data period
    period_options = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]
    selected_period = st.selectbox("Select data period", period_options)

    if st.button("Analyze Stocks"):
        results = analyze_stocks_in_batches(ticker_list, anchored_vwap_date, selected_period)
        if len(results) > 0:
            st.write("Stocks that meet the criteria:")
            st.dataframe(results)
        else:
            st.write("No stocks found that meet the criteria.")

def analyze_stocks_in_batches(tickers, anchored_vwap_date, period, batch_size=100):
    results = []
    total_tickers = len(tickers)
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i in range(0, total_tickers, batch_size):
        batch = tickers[i:i+batch_size]
        batch_results = analyze_batch(batch, anchored_vwap_date, period)
        results.extend(batch_results)
        
        # Update progress
        progress = min((i + batch_size) / total_tickers, 1.0)
        progress_bar.progress(progress)
        status_text.text(f"Processed {min(i + batch_size, total_tickers)} out of {total_tickers} tickers")

    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(results)

def analyze_batch(batch, anchored_vwap_date, period):
    batch_results = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_ticker = {executor.submit(analyze_stock, ticker, anchored_vwap_date, period): ticker for ticker in batch}
        for future in concurrent.futures.as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                result = future.result()
                if result:
                    batch_results.append(result)
            except Exception as exc:
                st.warning(f"{ticker} generated an exception: {exc}")
    return batch_results

def analyze_stock(ticker, anchored_vwap_date, period):
    try:
        data = yf.download(ticker, start=anchored_vwap_date - timedelta(days=30), end=anchored_vwap_date + timedelta(days=2), period=period)
        if len(data) > 0:
            # Calculate VWAP
            data['VWAP'] = (data['Close'] * data['Volume']).cumsum() / data['Volume'].cumsum()

            # Check for strong decline in VWAP
            vwap_decline = data['VWAP'].iloc[-1] < data['VWAP'].iloc[0] * 0.95

            # Check for VWAP crossing within 2 days
            vwap_cross = (data['Close'] > data['VWAP']).rolling(2).sum().iloc[-1] == 2

            # Check for closing price higher than VWAP in the last 2 days
            high_close = data['Close'].iloc[-1] > data['VWAP'].iloc[-1]

            # Check for high buy volume in the last 2 days
            buy_volume = data['Volume'].iloc[-2:].sum() > data['Volume'].mean() * 2

            if vwap_decline and vwap_cross and high_close and buy_volume:
                return {
                    'Ticker': ticker,
                    'VWAP Decline': f"{(1 - data['VWAP'].iloc[-1] / data['VWAP'].iloc[0]) * 100:.2f}%",
                    'VWAP Cross': "Yes",
                    'Close > VWAP': "Yes",
                    'Buy Volume': f"{data['Volume'].iloc[-2:].sum():.0f}"
                }
    except Exception as e:
        st.warning(f"Error processing {ticker}: {str(e)}")
    return None

if __name__ == "__main__":
    main()

