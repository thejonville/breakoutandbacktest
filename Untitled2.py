#!/usr/bin/env python
# coding: utf-8

# In[4]:


import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import pytz

def fetch_stock_data(ticker, start_date, end_date):
    stock = yf.Ticker(ticker)
    data = stock.history(start=start_date, end=end_date)
    return data

def calculate_avwap(data, date):
    date = pd.to_datetime(date).tz_localize(pytz.UTC)
    data_until_date = data.loc[:date]
    return (data_until_date['Close'] * data_until_date['Volume']).sum() / data_until_date['Volume'].sum()

st.title("Stock AVWAP Analysis")

# User inputs
tickers_input = st.text_input("Enter stock tickers (comma-separated):", "AAPL,GOOGL,MSFT")
avwap_date = st.date_input("Enter AVWAP calculation date:", datetime.now().date() - timedelta(days=7))

if st.button("Analyze Stocks"):
    tickers = [ticker.strip() for ticker in tickers_input.split(',')]
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)  # Fetch 30 days of data
    
    results = []
    
    for ticker in tickers:
        try:
            data = fetch_stock_data(ticker, start_date, end_date)
            if data.empty:
                st.warning(f"No data available for {ticker}")
                continue
            
            avwap = calculate_avwap(data, avwap_date)
            
            # Check if stock passed AVWAP in the last 3 days
            last_3_days = data.iloc[-3:]
            passed_avwap = (last_3_days['Close'] > avwap).any()
            
            # Check if the latest closing price is higher than AVWAP
            latest_close = data['Close'].iloc[-1]
            higher_than_avwap = latest_close > avwap
            
            if passed_avwap and higher_than_avwap:
                passed_date = last_3_days[last_3_days['Close'] > avwap].index[0].tz_convert(None).date()
                results.append({
                    'Ticker': ticker,
                    'AVWAP': avwap,
                    'Latest Close': latest_close,
                    'Passed AVWAP Date': passed_date
                })
        
        except Exception as e:
            st.error(f"Error fetching data for {ticker}: {str(e)}")
    
    if results:
        st.subheader("Stocks that passed AVWAP in the last 3 days and have a higher closing price:")
        df_results = pd.DataFrame(results)
        st.dataframe(df_results)
    else:
        st.info("No stocks found that meet the criteria.")

st.sidebar.markdown("## About")
st.sidebar.info("This app analyzes stocks based on their AVWAP and recent price movements.")
st.sidebar.markdown("### How to use:")
st.sidebar.markdown("1. Enter stock tickers separated by commas.")
st.sidebar.markdown("2. Select the AVWAP calculation date.")
st.sidebar.markdown("3. Click 'Analyze Stocks' to see the results.")

