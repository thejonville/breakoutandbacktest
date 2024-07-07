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
                recent_volume = recent_data['Volume'].iloc[-1]
                avg_volume = recent_data['Volume'].mean()
                
                # Check for buy volume increase in last 3 days
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
    
    st.subheader("Symbols Found:")
    st.write(", ".join(found_symbols))
    
    st.subheader("Symbols Not Found:")
    not_found_symbols = list(set(symbols) - set(found_symbols))
    st.write(", ".join(not_found_symbols))
    
    breakout_candidates = []
    for symbol in found_symbols:
        result = process_symbol(symbol, all_data[symbol], start_date, end_date, lookback_days, volume_threshold)
        if result:
            breakout_candidates.append(result)
    
    df = pd.DataFrame(breakout_candidates)
    if not df.empty:
        df = df.sort_values('Volume Increase (3d)', ascending=False)
    return df

def backtest_breakout_strategy(symbol, start_date, end_date, lookback_days=10, volume_threshold=1.5):
    data = yf.download(symbol, start=start_date, end=end_date)
    data['VWAP'] = calculate_vwap(data)
    data['Above_VWAP'] = data['Close'] > data['VWAP']
    vwap_crossings = data['Above_VWAP'].diff().abs()
    breakout_dates = data.index[vwap_crossings.astype(bool)].tolist()
    return data, breakout_dates

def plot_interactive_results(data, breakout_dates, symbol):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.1, subplot_titles=(f'{symbol} Price and VWAP', 'Volume'),
                        row_heights=[0.7, 0.3])

    fig.add_trace(go.Scatter(x=data.index, y=data['Close'], name='Close Price', line=dict(color='blue')), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'], name='VWAP', line=dict(color='orange')), row=1, col=1)
    fig.add_trace(go.Bar(x=data.index, y=data['Volume'], name='Volume', marker_color='lightblue'), row=2, col=1)

    for date in breakout_dates:
        fig.add_trace(go.Scatter(x=[date, date], y=[data['Low'].min(), data['High'].max()], 
                                 mode='lines', name='VWAP Crossing', line=dict(color='red', width=1, dash='dash')), row=1, col=1)

    fig.update_layout(height=800, title_text=f"{symbol} - Interactive Chart with VWAP Crossings", 
                      showlegend=True, hovermode="x unified")
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    return fig

st.title("Stock VWAP Crossing Scanner and Backtester")

default_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'VOO', 'TSLA', 'NVDA', 'JPM', 'V', 'JNJ']
symbols_input = st.text_area("Enter stock symbols (comma-separated):", ", ".join(default_symbols))
symbols = [symbol.strip() for symbol in symbols_input.split(',')]

search_query = st.text_input("Search for a stock symbol:")
if search_query:
    matching_symbols = [symbol for symbol in symbols if search_query.upper() in symbol.upper()]
    if matching_symbols:
        st.write("Matching symbols:", ", ".join(matching_symbols))
    else:
        st.write("No matching symbols found.")

new_symbol = st.text_input("Add a new stock symbol:")
if new_symbol:
    if new_symbol.upper() not in [symbol.upper() for symbol in symbols]:
        symbols.append(new_symbol.upper())
        st.success(f"Added {new_symbol.upper()} to the list of symbols.")
    else:
        st.warning(f"{new_symbol.upper()} is already in the list of symbols.")

st.text_area("Current list of stock symbols:", ", ".join(symbols), key="updated_symbols")

lookback_days = st.slider("Lookback period (days)", 5, 900, 10)
volume_threshold = st.slider("Volume increase threshold", 0.1, 3.0, 1.5, 0.1)

if st.button("Scan for VWAP Crossings"):
    with st.spinner("Scanning..."):
        candidates = scan_for_breakout_candidates(symbols, lookback_days, volume_threshold)
    
    if not candidates.empty:
        st.subheader(f"Stocks that crossed VWAP within the last {lookback_days} days:")
        st.dataframe(candidates)
    else:
        st.info(f"No stocks found that crossed VWAP within the last {lookback_days} days.")

st.subheader("Backtest VWAP Crossing Strategy")

backtest_symbol = st.selectbox("Select a stock symbol for backtesting:", symbols)
start_date = st.date_input("Start date", datetime(2023, 1, 1))
end_date = st.date_input("End date", datetime.now())

if st.button("Run Backtest"):
    with st.spinner("Backtesting..."):
        data, breakout_dates = backtest_breakout_strategy(backtest_symbol, start_date, end_date, lookback_days, volume_threshold)
    
    if breakout_dates:
        st.subheader(f"Backtest Results for {backtest_symbol}")
        st.write(f"Number of VWAP crossings identified: {len(breakout_dates)}")
        st.write("VWAP crossing dates:")
        for date in breakout_dates:
            st.write(date.strftime('%Y-%m-%d'))
        
        fig = plot_interactive_results(data, breakout_dates, backtest_symbol)
        st.plotly_chart(fig)
    else:
        st.info("No VWAP crossings found during the backtest period.")

st.subheader("All Stock Symbols:")
st.write(", ".join(symbols))

