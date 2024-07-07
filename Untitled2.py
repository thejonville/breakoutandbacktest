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
default_anchor_date = start_date + timedelta(days=period // 1)
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

                close_price = data['Close'].iloc[-1]
                vwap = data['VWAP'].iloc[-1]
                anchored_vwap = data['Anchored_VWAP'].iloc[-1]

                # Check if the stock passed VWAP within the last 5 days
                passed_vwap_recently = any(
                    (data['Close'].iloc[i] > data['VWAP'].iloc[i] and 
                     data['Close'].iloc[i-1] <= data['VWAP'].iloc[i-1])
                    for i in range(-5, 0)
                )

                if passed_vwap_recently:
                    results.append({
                        'Ticker': ticker,
                        'VWAP Decline': vwap_decline,
                        'Crossed Anchored VWAP': crossed_anchored_vwap,
                        'Close': close_price,
                        'VWAP': vwap,
                        'Anchored VWAP': anchored_vwap,
                        'Buy Volume (2d)': buy_volume_2d,
                        'Close > VWAP': close_price > vwap,
                        'Close > Anchored VWAP': close_price > anchored_vwap
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
        
        # Filter results
        filtered_df = df_results[df_results['Close > VWAP'] & df_results['Close > Anchored VWAP']]
        
        if filtered_df.empty:
            st.warning("No stocks meet the criteria (Close > VWAP and Close > Anchored VWAP)")
        else:
            # Sort options
            sort_column = st.selectbox('Sort by:', ['Buy Volume (2d)', 'Close', 'VWAP', 'Anchored VWAP'])
            sort_order = st.radio('Sort order:', ['Descending', 'Ascending'])
            
            # Sort the dataframe
            ascending = sort_order == 'Ascending'
            filtered_df_sorted = filtered_df.sort_values(by=sort_column, ascending=ascending)
            
            st.dataframe(filtered_df_sorted)

            st.subheader('Stocks meeting all criteria:')
            final_filtered = filtered_df_sorted[filtered_df_sorted['VWAP Decline'] & filtered_df_sorted['Crossed Anchored VWAP']]
            if not final_filtered.empty:
                st.dataframe(final_filtered)
            else:
                st.info('No stocks met all criteria.')
    else:
        st.warning('No results to display. Please check your inputs and try again.')

st.sidebar.markdown('''
## How to use this app:
1. Enter stock tickers separated by commas.
2. Select the period for analysis (up to 365 days).
3. Choose the Anchored VWAP start date.
4. Click 'Analyze' to process the data.
5. View the filtered results (Close > VWAP and Close > Anchored VWAP).
6. Sort the results using the dropdown and radio buttons.
7. Check the final filtered results meeting all criteria.
''')

