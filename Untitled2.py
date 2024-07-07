#!/usr/bin/env python
# coding: utf-8

# In[4]:


import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

def main():
    st.title("Stock Analysis App")

    tickers = st.text_input("Enter stock tickers (separated by commas, no spaces):")
    ticker_list = [ticker.strip() for ticker in tickers.split(",")]

    anchored_vwap_date = st.date_input("Select anchored VWAP date")

    period_options = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]
    selected_period = st.selectbox("Select data period", period_options)

    if st.button("Analyze Stocks"):
        results = analyze_stocks_in_batches(ticker_list, anchored_vwap_date, selected_period)
        if len(results) > 0:
            st.write("Stocks that meet the criteria:")
            st.dataframe(results)
        else:
            st.write("No stocks found that meet the criteria.")

def analyze_stocks_in_batches(tickers, anchored_vwap_date, period, batch_size=500):
    results = []
    total_tickers = len(tickers)
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i in range(0, total_tickers, batch_size):
        batch = tickers[i:i+batch_size]
        batch_results = analyze_batch(batch, anchored_vwap_date, period)
        results.extend(batch_results)
        
        progress = min((i + batch_size) / total_tickers, 1.0)
        progress_bar.progress(progress)
        status_text.text(f"Processed {min(i + batch_size, total_tickers)} out of {total_tickers} tickers")

    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(results)

def analyze_batch(batch, anchored_vwap_date, period):
    batch_results = []
    try:
        end_date = datetime.now().date()
        data = yf.download(" ".join(batch), start=anchored_vwap_date, end=end_date, period=period, group_by='ticker')
        
        for ticker in batch:
            if ticker in data.columns.levels[0]:
                ticker_data = data[ticker]
                result = analyze_stock_data(ticker, ticker_data, anchored_vwap_date)
                if result:
                    batch_results.append(result)
            else:
                st.warning(f"No data available for {ticker}")
    except Exception as e:
        st.error(f"Error processing batch: {str(e)}")
    
    return batch_results

def analyze_stock_data(ticker, data, anchored_vwap_date):
    if len(data) > 0:
        data['VWAP'] = (data['Close'] * data['Volume']).cumsum() / data['Volume'].cumsum()

        overall_decline = (data['Close'].iloc[-1] - data['Close'].iloc[0]) / data['Close'].iloc[0]

        vwap_cross = (data['Close'].iloc[-10:] > data['VWAP'].iloc[-10:]).any()

        high_close = (data['Close'].iloc[-5:] > data['VWAP'].iloc[-5:]).any()

        buy_volume = data['Volume'].iloc[-10:].mean() > data['Volume'].mean() * 1.1

        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        recent_trend = (data['Close'].iloc[-1] - data['Close'].iloc[-5]) / data['Close'].iloc[-5]

        if (overall_decline < 0 or recent_trend > 0) and (vwap_cross or high_close or buy_volume or rsi.iloc[-1] < 50):
            return {
                'Ticker': ticker,
                'Closing Price': f"${data['Close'].iloc[-1]:.2f}",
                'Overall Decline': f"{overall_decline*100:.2f}%",
                'Recent Trend (5d)': f"{recent_trend*100:.2f}%",
                'VWAP Cross (10d)': "Yes" if vwap_cross else "No",
                'Close > VWAP (5d)': "Yes" if high_close else "No",
                'High Buy Volume (10d)': "Yes" if buy_volume else "No",
                'RSI': f"{rsi.iloc[-1]:.2f}",
                'Average Volume (10d)': f"{data['Volume'].iloc[-10:].mean():.0f}",
                'Average Volume (All)': f"{data['Volume'].mean():.0f}"
            }
    return None

if __name__ == "__main__":
    main()

