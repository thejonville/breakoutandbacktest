#!/usr/bin/env python
# coding: utf-8

# In[4]:


import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def calculate_vwap(data):
    v = data['Volume'].values
    tp = (data['High'] + data['Low'] + data['Close']) / 3
    return np.cumsum(tp * v) / np.cumsum(v)

def calculate_anchored_vwap(data, anchor_date):
    anchor_index = data.index.get_loc(anchor_date, method='nearest')
    return calculate_vwap(data.iloc[anchor_index:])

st.title('Stock Analysis App')

# User inputs
tickers = st.text_input('Enter stock tickers (comma-separated)', 'AAPL,GOOGL,MSFT')
period = st.slider('Select period (in days)', 1, 365, 30)

end_date = datetime.now()
start_date = end_date - timedelta(days=period)

# Anchored VWAP date selection
min_date = start_date
max_date = end_date
default_anchor_date = start_date + timedelta(days=period // 2)
anchor_date = st.date_input('Select Anchored VWAP start date', 
                            min_value=min_date, 
                            max_value=max_date, 
                            value=default_anchor_date)

if st.button('Analyze'):
    tickers = [ticker.strip() for ticker in tickers.split(',')]

    results = []

    for ticker in tickers:
        try:
            data = yf.download(ticker, start=start_date, end=end_date)
            if len(data) > 0:
                data['VWAP'] = calculate_vwap(data)
                data['Anchored_VWAP'] = calculate_anchored_vwap(data, pd.Timestamp(anchor_date))

                vwap_decline = data['VWAP'].iloc[-1] < data['VWAP'].iloc[0]
                crossed_anchored_vwap = any(
                    (data['Close'].iloc[i] > data['Anchored_VWAP'].iloc[i] and 
                     data['Close'].iloc[i-1] <= data['Anchored_VWAP'].iloc[i-1])
                    for i in range(-5, 0)
                )

                results.append({
                    'Ticker': ticker,
                    'VWAP Decline': vwap_decline,
                    'Crossed Anchored VWAP': crossed_anchored_vwap
                })
            else:
                st.warning(f"No data available for {ticker}")
        except Exception as e:
            st.error(f"Error processing {ticker}: {str(e)}")

    if results:
        df_results = pd.DataFrame(results)
        st.subheader('Analysis Results')
        st.dataframe(df_results)

        filtered_results = df_results[df_results['VWAP Decline'] & df_results['Crossed Anchored VWAP']]
        if not filtered_results.empty:
            st.subheader('Stocks meeting both criteria:')
            st.dataframe(filtered_results)
        else:
            st.info('No stocks met both criteria.')
    else:
        st.warning('No results to display. Please check your inputs and try again.')

st.sidebar.markdown('''
## How to use this app:
1. Enter stock tickers separated by commas.
2. Select the period for analysis (up to 365 days).
3. Choose the Anchored VWAP start date.
4. Click 'Analyze' to process the data.
5. View the results in the main panel.
''')

