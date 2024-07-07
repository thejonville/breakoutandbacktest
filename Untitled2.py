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
    anchor_date = pd.Timestamp(anchor_date)
    if anchor_date not in data.index:
        anchor_date = data.index[data.index >= anchor_date][0]
    return calculate_vwap(data.loc[anchor_date:])

def calculate_buy_volume(data):
    return data[data['Close'] > data['Open']]['Volume'].sum()

st.title('Stock Analysis App')

tickers = st.text_input('Enter stock tickers (comma-separated)', 'AAPL,GOOGL,MSFT')
period = st.slider('Select period (in days)', 1, 365, 30)

end_date = datetime.now()
start_date = end_date - timedelta(days=period)

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
                data['Anchored_VWAP'] = calculate_anchored_vwap(data, anchor_date)

                vwap_decline = data['VWAP'].iloc[-1] < data['VWAP'].iloc[0]
                crossed_anchored_vwap = any(
                    (data['Close'].iloc[i] > data['Anchored_VWAP'].iloc[i] and 
                     data['Close'].iloc[i-1] <= data['Anchored_VWAP'].iloc[i-1])
                    for i in range(-5, 0)
                )

                buy_volume_2d = calculate_buy_volume(data.iloc[-2:])

                results.append({
                    'Ticker': ticker,
                    'VWAP Decline': vwap_decline,
                    'Crossed Anchored VWAP': crossed_anchored_vwap,
                    'Close': data['Close'].iloc[-1],
                    'VWAP': data['VWAP'].iloc[-1],
                    'Anchored VWAP': data['Anchored_VWAP'].iloc[-1],
                    'Buy Volume (2d)': buy_volume_2d
                })
            else:
                st.warning(f"No data available for {ticker}")
        except Exception as e:
            st.error(f"Error processing {ticker}: {str(e)}")
            st.error(f"Error details: {type(e).__name__}")

    if results:
        df_results = pd.DataFrame(results)
        df_results['Close'] = df_results['Close'].round(2)
        df_results['VWAP'] = df_results['VWAP'].round(2)
        df_results['Anchored VWAP'] = df_results['Anchored VWAP'].round(2)
        df_results['Buy Volume (2d)'] = df_results['Buy Volume (2d)'].astype(int)
        
        st.subheader('Analysis Results')
        
        # Sort options
        sort_column = st.selectbox('Sort by:', ['Buy Volume (2d)', 'Close', 'VWAP', 'Anchored VWAP'])
        sort_order = st.radio('Sort order:', ['Descending', 'Ascending'])
        
        # Sort the dataframe
        ascending = sort_order == 'Ascending'
        df_results_sorted = df_results.sort_values(by=sort_column, ascending=ascending)
        
        st.dataframe(df_results_sorted)

        filtered_results = df_results_sorted[df_results_sorted['VWAP Decline'] & df_results_sorted['Crossed Anchored VWAP']]
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
5. Sort the results using the dropdown and radio buttons.
6. View the results in the main panel.
''')

