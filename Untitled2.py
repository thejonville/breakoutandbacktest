#!/usr/bin/env python
# coding: utf-8

# In[4]:


import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

def calculate_vwap(data):
    v = data['Volume']
    tp = (data['High'] + data['Low'] + data['Close']) / 3
    return (tp * v).cumsum() / v.cumsum()

def scan_for_breakout_candidates(symbols, lookback_days=10, volume_threshold=1.5):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)
    
    breakout_candidates = []

    for symbol in symbols:
        try:
            # Fetch all historical data
            data = yf.download(symbol, period="max", interval="1d")
            
            if len(data) < 2:  # Need at least 2 days of data to check for crossing
                continue
            
            # Calculate VWAP
            data['VWAP'] = calculate_vwap(data)
            
            # Filter data for the lookback period
            recent_data = data.loc[start_date:end_date]
            
            # Check for VWAP crossings
            recent_data['Above_VWAP'] = recent_data['Close'] > recent_data['VWAP']
            vwap_crossings = recent_data['Above_VWAP'].diff().abs()
            
            if vwap_crossings.sum() > 0:
                last_crossing_date = recent_data.index[vwap_crossings.astype(bool)][-1]
                days_since_crossing = (end_date - last_crossing_date).days
                
                if days_since_crossing <= lookback_days:
                    last_close = recent_data['Close'].iloc[-1]
                    last_vwap = recent_data['VWAP'].iloc[-1]
                    recent_volume = recent_data['Volume'].iloc[-1]
                    avg_volume = recent_data['Volume'].mean()
                    
                    breakout_candidates.append({
                        'Symbol': symbol,
                        'Last Crossing Date': last_crossing_date.strftime('%Y-%m-%d'),
                        'Days Since Crossing': days_since_crossing,
                        'Close': last_close,
                        'VWAP': last_vwap,
                        'Volume Increase': recent_volume / avg_volume,
                        'Price/VWAP Ratio': last_close / last_vwap
                    })
        
        except Exception as e:
            st.error(f"Error processing {symbol}: {e}")
    
    return pd.DataFrame(breakout_candidates)

def backtest_breakout_strategy(symbol, start_date, end_date, lookback_days=10, volume_threshold=1.5):
    # Fetch all historical data
    data = yf.download(symbol, period="max", interval="1d")
    
    # Calculate VWAP
    data['VWAP'] = calculate_vwap(data)
    
    # Filter data for the backtest period
    backtest_data = data.loc[start_date:end_date]
    
    # Initialize results
    breakout_dates = []
    
    # Check for VWAP crossings
    backtest_data['Above_VWAP'] = backtest_data['Close'] > backtest_data['VWAP']
    vwap_crossings = backtest_data['Above_VWAP'].diff().abs()
    
    breakout_dates = backtest_data.index[vwap_crossings.astype(bool)].tolist()
    
    return backtest_data, breakout_dates

def plot_interactive_results(data, breakout_dates, symbol):
    # Create subplot with 2 rows
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.1, subplot_titles=(f'{symbol} Price and VWAP', 'Volume'),
                        row_heights=[0.7, 0.3])

    # Add price and VWAP traces
    fig.add_trace(go.Scatter(x=data.index, y=data['Close'], name='Close Price', line=dict(color='blue')), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'], name='VWAP', line=dict(color='orange')), row=1, col=1)

    # Add volume trace
    fig.add_trace(go.Bar(x=data.index, y=data['Volume'], name='Volume', marker_color='lightblue'), row=2, col=1)

    # Add breakout markers
    for date in breakout_dates:
        fig.add_trace(go.Scatter(x=[date, date], y=[data['Low'].min(), data['High'].max()], 
                                 mode='lines', name='VWAP Crossing', line=dict(color='red', width=1, dash='dash')), row=1, col=1)

    # Update layout
    fig.update_layout(height=800, title_text=f"{symbol} - Interactive Chart with VWAP Crossings", 
                      showlegend=True, hovermode="x unified")
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    return fig

# Streamlit app
st.title("Stock VWAP Crossing Scanner and Backtester")

# Input for stock symbols
default_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'VOO', 'TSLA', 'NVDA', 'JPM', 'V', 'JNJ']
symbols_input = st.text_area("Enter stock symbols (comma-separated):", ", ".join(default_symbols))
symbols = [symbol.strip() for symbol in symbols_input.split(',')]

# Search functionality
search_query = st.text_input("Search for a stock symbol:")
if search_query:
    matching_symbols = [symbol for symbol in symbols if search_query.upper() in symbol.upper()]
    if matching_symbols:
        st.write("Matching symbols:", ", ".join(matching_symbols))
    else:
        st.write("No matching symbols found.")

# Add new stock
new_symbol = st.text_input("Add a new stock symbol:")
if new_symbol:
    if new_symbol.upper() not in [symbol.upper() for symbol in symbols]:
        symbols.append(new_symbol.upper())
        st.success(f"Added {new_symbol.upper()} to the list of symbols.")
    else:
        st.warning(f"{new_symbol.upper()} is already in the list of symbols.")

# Update symbols input
st.text_area("Current list of stock symbols:", ", ".join(symbols), key="updated_symbols")

# Parameters
lookback_days = st.slider("Lookback period (days)", 5, 900, 10)
volume_threshold = st.slider("Volume increase threshold", 0.1, 3.0, 1.5, 0.1)

# Run the scanner
if st.button("Scan for VWAP Crossings"):
    with st.spinner("Scanning..."):
        candidates = scan_for_breakout_candidates(symbols, lookback_days, volume_threshold)
    
    if not candidates.empty:
        st.subheader(f"Stocks that crossed VWAP within the last {lookback_days} days:")
        st.dataframe(candidates)
    else:
        st.info(f"No stocks found that crossed VWAP within the last {lookback_days} days.")

# Backtesting section
st.subheader("Backtest VWAP Crossing Strategy")

# Input for backtesting
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
        
        # Plot the results
        fig = plot_interactive_results(data, breakout_dates, backtest_symbol)
        st.plotly_chart(fig)
    else:
        st.info("No VWAP crossings found during the backtest period.")

# Display the list of all symbols
st.subheader("All Stock Symbols:")
st.write(", ".join(symbols))
