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
        data['All_Time_VWAP'] = calculate_anchored_vwap(data, data.index[0])
        data['AVWAP'] = calculate_anchored_vwap(data, anchor_date)
        recent_data = data.loc[start_date:end_date]
        recent_data['Above_All_Time_VWAP'] = recent_data['Close'] > recent_data['All_Time_VWAP']
        recent_data['Above_AVWAP'] = recent_data['Close'] > recent_data['AVWAP']
        all_time_vwap_crossings = recent_data['Above_All_Time_VWAP'].diff().abs()
        avwap_crossings = recent_data['Above_AVWAP'].diff().abs()
        if all_time_vwap_crossings.sum() > 0 and avwap_crossings.sum() > 0:
            last_all_time_crossing = recent_data.index[all_time_vwap_crossings.astype(bool)][-1]
            last_avwap_crossing = recent_data.index[avwap_crossings.astype(bool)][-1]
            days_since_all_time = (end_date.date() - last_all_time_crossing.date()).days
            days_since_avwap = (end_date.date() - last_avwap_crossing.date()).days
            if days_since_all_time <= 20 and days_since_avwap <= 2:
                last_close = recent_data['Close'].iloc[-1]
                last_all_time_vwap = recent_data['All_Time_VWAP'].iloc[-1]
                last_avwap = recent_data['AVWAP'].iloc[-1]
                if last_close > last_all_time_vwap and last_close > last_avwap:
                    recent_volume = recent_data['Volume'].iloc[-1]
                    avg_volume = recent_data['Volume'].mean()
                    last_3_days_volume = recent_data['Volume'].tail(3)
                    last_3_days_avg_volume = last_3_days_volume.mean()
                    volume_increase_3d = last_3_days_avg_volume / avg_volume
                    return {
                        'Symbol': symbol,
                        'Last All-Time VWAP Crossing': last_all_time_crossing.strftime('%Y-%m-%d'),
                        'Last AVWAP Crossing': last_avwap_crossing.strftime('%Y-%m-%d'),
                        'Close': last_close,
                        'All-Time VWAP': last_all_time_vwap,
                        'AVWAP': last_avwap,
                        'Volume Increase': recent_volume / avg_volume,
                        'Price/All-Time VWAP Ratio': last_close / last_all_time_vwap,
                        'Price/AVWAP Ratio': last_close / last_avwap,
                        'Volume Increase (3d)': volume_increase_3d
                    }
    except Exception as e:
        st.error(f"Error processing {symbol}: {e}")
    return None

def scan_for_breakout_candidates(symbols, anchor_date, volume_threshold=1.5):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=20)
    all_data, found_symbols = fetch_data_in_batches(symbols, start_date - timedelta(days=365), end_date)
    breakout_candidates = []
    for symbol in found_symbols:
        result = process_symbol(symbol, all_data[symbol], start_date, end_date, anchor_date)
        if result:
            breakout_candidates.append(result)
    if breakout_candidates:
        df = pd.DataFrame(breakout_candidates)
        df = df.sort_values('Volume Increase (3d)', ascending=False)
        return df
    else:
        return pd.DataFrame()

def backtest_breakout_strategy(symbol, start_date, end_date, anchor_date):
    data = yf.download(symbol, start=start_date, end=end_date)
    data['All_Time_VWAP'] = calculate_anchored_vwap(data, data.index[0])
    data['AVWAP'] = calculate_anchored_vwap(data, anchor_date)
    data['Above_All_Time_VWAP'] = data['Close'] > data['All_Time_VWAP']
    data['Above_AVWAP'] = data['Close'] > data['AVWAP']
    all_time_vwap_crossings = data['Above_All_Time_VWAP'].diff().abs()
    avwap_crossings = data['Above_AVWAP'].diff().abs()
    breakout_dates = data.index[(all_time_vwap_crossings.astype(bool)) | (avwap_crossings.astype(bool))].tolist()
    return data, breakout_dates

def plot_interactive_results(data, breakout_dates, symbol):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, 
                        subplot_titles=(f'{symbol} Price, All-Time VWAP, and AVWAP', 'Volume'), row_heights=[0.7, 0.3])
    fig.add_trace(go.Scatter(x=data.index, y=data['Close'], name='Close Price', line=dict(color='blue')), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['All_Time_VWAP'], name='All-Time VWAP', line=dict(color='green')), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['AVWAP'], name='AVWAP', line=dict(color='orange')), row=1, col=1)
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

st.title("Stock All-Time VWAP and Anchored VWAP Crossing Scanner and Backtester")

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

volume_threshold = st.slider("Volume increase threshold", 0.1, 3.0, 1.5, 0.1)
anchor_date = st.date_input("Anchor date for AVWAP", datetime(2023, 1, 1))

if st.button("Scan for VWAP Crossings"):
    with st.spinner("Scanning..."):
        candidates = scan_for_breakout_candidates(symbols, anchor_date, volume_threshold)
        if not candidates.empty:
            st.subheader("Stocks that crossed All-Time VWAP within the last 20 days and Anchored VWAP within the last 2 days:")
            st.dataframe(candidates)
        else:
            st.info("No stocks found that crossed All-Time VWAP within the last 20 days and Anchored VWAP within the last 2 days.")

st.subheader("Backtest VWAP Crossing Strategy")
backtest_symbol = st.selectbox("Select a stock symbol for backtesting:", symbols)
start_date = st.date_input("Start date", datetime(2023, 1, 1))
end_date = st.date_input("End date", datetime.now())

if st.button("Run Backtest"):
    with st.spinner("Backtesting..."):
        data, breakout_dates = backtest_breakout_strategy(backtest_symbol, start_date, end_date, anchor_date)
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

