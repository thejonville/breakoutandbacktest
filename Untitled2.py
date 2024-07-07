#!/usr/bin/env python
# coding: utf-8

# In[4]:


import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta
import pytz
import pandas as pd
import concurrent.futures

@st.cache_data(ttl=3600)  # Cache data for 1 hour
def get_stock_data(tickers):
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=1)
    
    data = yf.download(tickers, start=start_date, end=end_date, group_by='ticker')
    return data

def is_market_open():
    ny_tz = pytz.timezone('America/New_York')
    now = datetime.now(ny_tz)
    return now.weekday() < 5 and 9 <= now.hour < 16

@st.cache_data(ttl=60)  # Cache data for 1 minute
def get_current_prices(tickers):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(lambda ticker: yf.Ticker(ticker).info.get('regularMarketPrice'), tickers))
    return dict(zip(tickers, results))

st.title("Stock Buy Volume and Price Analyzer")

user_input = st.text_input("Enter stock tickers separated by commas (no spaces):", "AAPL,MSFT,GOOGL,AMZN")

if user_input:
    tickers = user_input.split(',')
    
    with st.spinner('Fetching stock data...'):
        stock_data = get_stock_data(tickers)
        
        if not stock_data.empty:
            buy_volumes = {ticker: stock_data[ticker]['Volume'].iloc[-1] for ticker in tickers}
            
            if is_market_open():
                current_prices = get_current_prices(tickers)
            else:
                current_prices = {ticker: stock_data[ticker]['Close'].iloc[-1] for ticker in tickers}
            
            sorted_stocks = sorted(buy_volumes.items(), key=lambda x: x[1], reverse=True)
            
            st.subheader("Stocks Ranked by Today's Buy Volume and Current Price:")
            for rank, (ticker, volume) in enumerate(sorted_stocks, 1):
                price = current_prices[ticker]
                st.write(f"{rank}. {ticker}: Volume: {volume:,.0f}, Current Price: ${price:.2f}")
            
            st.subheader("Buy Volume Comparison")
            st.bar_chart(pd.Series(buy_volumes))
            
            st.subheader("Current Prices")
            st.bar_chart(pd.Series(current_prices))
        else:
            st.warning("No valid stock data found for the given tickers.")
else:
    st.info("Please enter stock tickers to analyze.")

