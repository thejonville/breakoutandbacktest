#!/usr/bin/env python
# coding: utf-8

# In[4]:


import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import streamlit as st

@st.cache_data
def fetch_data_in_batches(symbols, start_date, end_date, batch_size=100):
    all_data = {}
    found_symbols = []
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        batch_data = yf.download(batch, start=start_date, end=end_date, group_by='ticker')
        if len(batch) == 1:
            if not batch_data.empty:
                all_data[batch[0]] = batch_data
                found_symbols.append(batch[0])
        else:
            for symbol in batch:
                if symbol in batch_data.columns.levels[0]:
                    all_data[symbol] = batch_data[symbol]
                    found_symbols.append(symbol)
    return all_data, found_symbols

def calculate_anchored_vwap(data, anchor_date):
    data = data.loc[anchor_date:]
    v = data['Volume'].values
    tp = (data['High'].values + data['Low'].values + data['Close'].values) / 3
    return pd.Series((tp * v).cumsum() / v.cumsum(), index=data.index)

def process_symbol(symbol, data, start_date, end_date, anchor_date):
    try:
        if len(data) < 2:
            return None

        data['AVWAP'] = calculate_anchored_vwap(data, anchor_date)
        data['All_Time_VWAP'] = calculate_anchored_vwap(data, data.index[0])

        recent_data = data.loc[start_date:end_date]
        recent_data['Above_AVWAP'] = recent_data['Close'] > recent_data['AVWAP']
        recent_data['Above_All_Time_VWAP'] = recent_data['Close'] > recent_data['All_Time_VWAP']

        avwap_crossings = recent_data['Above_AVWAP'].diff().abs()
        all_time_vwap_crossings = recent_data['Above_All_Time_VWAP'].diff().abs()

        if avwap_crossings.sum() > 0 and all_time_vwap_crossings.sum() > 0:
            last_avwap_crossing = recent_data.index[avwap_crossings.astype(bool)][-1]
            last_all_time_crossing = recent_data.index[all_time_vwap_crossings.astype(bool)][-1]
            
            days_since_avwap = (end_date.date() - last_avwap_crossing.date()).days
            days_since_all_time = (end_date.date() - last_all_time_crossing.date()).days

            if days_since_avwap <= 2 and days_since_all_time <= 2:
                last_close = recent_data['Close'].iloc[-1]
                last_avwap = recent_data['AVWAP'].iloc[-1]
                last_all_time_vwap = recent_data['All_Time_VWAP'].iloc[-1]

                if last_close > last_avwap and last_close > last_all_time_vwap:
                    recent_volume = recent_data['Volume'].iloc[-1]
                    avg_volume = recent_data['Volume'].mean()
                    last_3_days_volume = recent_data['Volume'].tail(3)
                    last_3_days_avg_volume = last_3_days_volume.mean()
                    volume_increase_3d = last_3_days_avg_volume / avg_volume

                    return {
                        'Symbol': symbol,
                        'Last AVWAP Crossing': last_avwap_crossing.strftime('%Y-%m-%d'),
                        'Last All-Time VWAP Crossing': last_all_time_crossing.strftime('%Y-%m-%d'),
                        'Close': last_close,
                        'AVWAP': last_avwap,
                        'All-Time VWAP': last_all_time_vwap,
                        'Volume Increase': recent_volume / avg_volume,
                        'Price/AVWAP Ratio': last_close / last_avwap,
                        'Price/All-Time VWAP Ratio': last_close / last_all_time_vwap,
                        'Volume Increase (3d)': volume_increase_3d
                    }
    except Exception as e:
        st.error(f"Error processing {symbol}: {e}")
    return None

def scan_for_breakout_candidates(symbols, anchor_date, volume_threshold=1.5):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*5)  # Fetch 5 years of data for all-time VWAP

    all_data, found_symbols = fetch_data_in_batches(symbols, start_date, end_date)

    st.subheader("Symbols Found:")
    st.write(", ".join(found_symbols))

    st.subheader("Symbols Not Found:")
    not_found_symbols = list(set(symbols) - set(found_symbols))
    st.write(", ".join(not_found_symbols))

    breakout_candidates = []

    for symbol in found_symbols:
        result = process_symbol(symbol, all_data[symbol], end_date - timedelta(days=2), end_date, anchor_date)
        if result:
            breakout_candidates.append(result)

    if breakout_candidates:
        df = pd.DataFrame(breakout_candidates)
        df = df.sort_values('Volume Increase (3d)', ascending=False)
        return df
    else:
        return pd.DataFrame()

# Streamlit app
st.title("Stock AVWAP and All-Time VWAP Crossing Scanner")

default_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'VOO', 'TSLA', 'NVDA', 'JPM', 'V', 'JNJ']
symbols_input = st.text_area("Enter stock symbols (comma-separated):", ", ".join(default_symbols))
symbols = [symbol.strip() for symbol in symbols_input.split(',')]

volume_threshold = st.slider("Volume increase threshold", 0.1, 3.0, 1.5, 0.1)
anchor_date = st.date_input("Anchor date for AVWAP", datetime(2023, 1, 1))

if st.button("Scan for VWAP Crossings"):
    with st.spinner("Scanning..."):
        candidates = scan_for_breakout_candidates(symbols, anchor_date, volume_threshold)
        if not candidates.empty:
            st.subheader(f"Stocks that crossed both AVWAP and All-Time VWAP within the last 2 days:")
            st.dataframe(candidates)
        else:
            st.info(f"No stocks found that crossed both AVWAP and All-Time VWAP within the last 2 days.")

st.subheader("All Stock Symbols:")
st.write(", ".join(symbols))

