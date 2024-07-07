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

def calculate_avwap(data, date):
    date = pd.to_datetime(date).tz_localize(pytz.EST)
    data_until_date = data.loc[:date]
    return (data_until_date['Close'] * data_until_date['Volume']).sum() / data_until_date['Volume'].sum()

def estimate_buy_volume(data):
    last_day = data.iloc[-1]
    if last_day['Close'] > last_day['Open']:
        buy_volume = last_day['Volume']
    else:
        buy_volume = last_day['Volume'] * (last_day['Close'] - last_day['Low']) / (last_day['High'] - last_day['Low'])
    return buy_volume

st.title("Stock AVWAP Analysis")

# User inputs
tickers_input = st.text_input("Enter stock tickers (comma-separated):", "AAPL,GOOGL,MSFT")
period = st.selectbox("Select period", ['1d', '5d', '1mo'])
avwap_date = st.date_input("Enter AVWAP calculation date:", datetime.now().date() - timedelta(days=7))

if st.button("Analyze Stocks"):
    tickers = [ticker.strip() for ticker in tickers_input.split(',')]
    
    results = []
    
    for ticker in tickers:
        try:
            data = fetch_stock_data(ticker, period)
            if data.empty:
                st.warning(f"No data available for {ticker}")
                continue
            
            avwap = calculate_avwap(data, avwap_date)
            
            # Determine the number of days to check based on the period
            days_to_check = min(3, len(data))  # Check up to the last 3 days or the length of the data
            
            # Check if stock passed AVWAP in the last days_to_check days
            last_days = data.iloc[-days_to_check:]
            passed_avwap = (last_days['Close'] > avwap).any()
            
            # Check if the latest closing price is higher than AVWAP
            latest_close = data['Close'].iloc[-1]
            higher_than_avwap = latest_close > avwap
            
            # Estimate buy volume for the last day
            buy_volume = estimate_buy_volume(data)
            
            if passed_avwap and higher_than_avwap:
                passed_date = last_days[last_days['Close'] > avwap].index[0].tz_convert(None).date()
                results.append({
                    'Ticker': ticker,
                    'AVWAP': avwap,
                    'Latest Close': latest_close,
                    'Passed AVWAP Date': passed_date,
                    'Buy Volume': buy_volume
                })
        
        except Exception as e:
            st.error(f"Error fetching data for {ticker}: {str(e)}")
    
    if results:
        st.subheader(f"Stocks that passed AVWAP in the last {days_to_check} day(s) and have a higher closing price:")
        df_results = pd.DataFrame(results)
        
        # Sort results by Buy Volume
        sort_by_volume = st.checkbox("Sort by Buy Volume (Descending)")
        if sort_by_volume:
            df_results = df_results.sort_values('Buy Volume', ascending=False)
        
        st.dataframe(df_results)
    else:
        st.info("No stocks found that meet the criteria.")

st.sidebar.markdown("## About")
st.sidebar.info("This app analyzes stocks based on their AVWAP and recent price movements.")
st.sidebar.markdown("### How to use:")
st.sidebar.markdown("1. Enter stock tickers separated by commas.")
st.sidebar.markdown("2. Select the analysis period (1 day, 5 days, or 1 month).")
st.sidebar.markdown("3. Select the AVWAP calculation date.")
st.sidebar.markdown("4. Click 'Analyze Stocks' to see the results.")
st.sidebar.markdown("5. Optionally, sort results by Buy Volume.")

