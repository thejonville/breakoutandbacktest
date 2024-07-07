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

def calculate_vwap(data):
    v = data['Volume'].values
    tp = (data['High'].values + data['Low'].values + data['Close'].values) / 3
    return pd.Series((tp * v).cumsum() / v.cumsum(), index=data.index)

def process_symbol(symbol, data, start_date, end_date, lookback_days, volume_threshold):
    try:
        if len(data) < 2:
            return None
        data['VWAP'] = calculate_vwap(data)
        recent_data = data.loc[start_date:end_date]
        recent_data['Above_VWAP'] = recent_data['Close'] > recent_data['VWAP']
        vwap_crossings = recent_data['Above_VWAP'].diff().abs()
        if vwap_crossings.sum() > 0:
            last_crossing_date = recent_data.index[vwap_crossings.astype(bool)][-1]
            days_since_crossing = (end_date.date() - last_crossing_date.date()).days
            if days_since_crossing <= lookback_days:
                last_close = recent_data['Close'].iloc[-1]
                last_vwap = recent_data['VWAP'].iloc[-1]
                if last_close > last_vwap:  # Only return results if closing price is higher than VWAP
                    recent_volume = recent_data['Volume'].iloc[-1]
                    avg_volume = recent_data['Volume'].mean()
                    last_3_days_volume = recent_data['Volume'].tail(3)
                    last_3_days_avg_volume = last_3_days_volume.mean()
                    volume_increase_3d = last_3_days_avg_volume / avg_volume
                    return {
                        'Symbol': symbol,
                        'Last Crossing Date': last_crossing_date.strftime('%Y-%m-%d'),
                        'Days Since Crossing': days_since_crossing,
                        'Close': last_close,
                        'VWAP': last_vwap,
                        'Volume Increase': recent_volume / avg_volume,
                        'Price/VWAP Ratio': last_close / last_vwap,
                        'Volume Increase (3d)': volume_increase_3d
                    }
    except Exception as e:
        st.error(f"Error processing {symbol}: {e}")
    return None

def scan_for_breakout_candidates(symbols, lookback_days=10, volume_threshold=1.5):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)
    all_data, found_symbols = fetch_data_in_batches(symbols, start_date, end_date)
    
    breakout_candidates = []
    for symbol in found_symbols:
        result = process_symbol(symbol, all_data[symbol], start_date, end_date, lookback_days, volume_threshold)
        if result:
            breakout_candidates.append(result)
    
    df = pd.DataFrame(breakout_candidates)
    if not df.empty:
        df = df.sort_values('Volume Increase (3d)', ascending=False)
    return df

# Streamlit UI
st.title("Stock VWAP Crossing Scanner")

default_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'VOO', 'TSLA', 'NVDA', 'JPM', 'V', 'JNJ']
symbols_input = st.text_area("Enter stock symbols (comma-separated):", ", ".join(default_symbols))
symbols = [symbol.strip() for symbol in symbols_input.split(',')]

lookback_days = st.slider("Lookback period (days)", 5, 30, 10)
volume_threshold = st.slider("Volume increase threshold", 0.1, 3.0, 1.5, 0.1)

if st.button("Scan for VWAP Crossings"):
    with st.spinner("Scanning..."):
        candidates = scan_for_breakout_candidates(symbols, lookback_days, volume_threshold)
        if not candidates.empty:
            st.subheader(f"Stocks that crossed VWAP within the last {lookback_days} days and have a closing price higher than VWAP:")
            st.dataframe(candidates)
        else:
            st.info(f"No stocks found that crossed VWAP within the last {lookback_days} days and have a closing price higher than VWAP.")

