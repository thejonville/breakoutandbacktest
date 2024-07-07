#!/usr/bin/env python
# coding: utf-8

# In[4]:


import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import pytz

def fetch_stock_data(ticker, period):
    stock = yf.Ticker(ticker)
    data = stock.history(period=period)
    return data

def calculate_avwap(data):
    return (data['Close'] * data['Volume']).sum() / data['Volume'].sum()

st.title("Stock AVWAP Analysis")

# User inputs
tickers_input = st.text_input("Enter stock tickers (comma-separated):", "AAPL,GOOGL,MSFT")
period = st.selectbox("Select period", ['1d', '5d'])

if st.button("Analyze Stocks"):
    tickers = [ticker.strip() for ticker in tickers_input.split(',')]
    
    results = []
    
    for ticker in tickers:
        try:
            data = fetch_stock_data(ticker, period)
            if data.empty:
                st.warning(f"No data available for {ticker}")
                continue
            
            avwap = calculate_avwap(data)
            
            # Determine the number of days to check based on the period
            days_to_check = 1 if period == '1d' else 3
            
            # Check if stock passed AVWAP in the last days_to_check days
            last_days = data.iloc[-days_to_check:]
            passed_avwap = (last_days['Close'] > avwap).any()
            
            # Check if the latest closing price is higher than AVWAP
            latest_close = data['Close'].iloc[-1]
            higher_than_avwap = latest_close > avwap
            
            if passed_avwap and higher_than_avwap:
                passed_date = last_days[last_days['Close'] > avwap].index[0].tz_convert(None).date()
                results.append({
                    'Ticker': ticker,
                    'AVWAP': avwap,
                    'Latest Close': latest_close,
                    'Passed AVWAP Date': passed_date
                })
        
        except Exception as e:
            st.error(f"Error fetching data for {ticker}: {str(e)}")
    
    if results:
        st.subheader(f"Stocks that passed AVWAP in the last {days_to_check} day(s) and have a higher closing price:")
        df_results = pd.DataFrame(results)
        st.dataframe(df_results)
    else:
        st.info("No stocks found that meet the criteria.")

st.sidebar.markdown("## About")
st.sidebar.info("This app analyzes stocks based on their AVWAP and recent price movements.")
st.sidebar.markdown("### How to use:")
st.sidebar.markdown("1. Enter stock tickers separated by commas.")
st.sidebar.markdown("2. Select the analysis period (1 day or 5 days).")
st.sidebar.markdown("3. Click 'Analyze Stocks' to see the results.")

