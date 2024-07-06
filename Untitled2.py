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
            # Fetch data
            data = yf.download(symbol, start=start_date, end=end_date, interval="1d")
            
            if len(data) < lookback_days:
                continue
            
            # Calculate VWAP
            data['VWAP'] = calculate_vwap(data)
            
            # Calculate average volume
            avg_volume = data['Volume'].mean()
            
            # Check if recent volume is above threshold
            recent_volume = data['Volume'].iloc[-1]
            volume_increase = recent_volume / avg_volume
            
            # Check if price is near or above VWAP
            last_close = data['Close'].iloc[-1]
            last_vwap = data['VWAP'].iloc[-1]
            price_to_vwap_ratio = last_close / last_vwap
            
            # Criteria for potential breakout
            if volume_increase > volume_threshold and price_to_vwap_ratio >= 0.98:
                breakout_candidates.append({
                    'Symbol': symbol,
                    'Close': last_close,
                    'VWAP': last_vwap,
                    'Volume Increase': volume_increase,
                    'Price/VWAP Ratio': price_to_vwap_ratio
                })
        
        except Exception as e:
            st.error(f"Error processing {symbol}: {e}")
    
    return pd.DataFrame(breakout_candidates)

def backtest_breakout_strategy(symbol, start_date, end_date, lookback_days=10, volume_threshold=1.5):
    # Fetch historical data
    data = yf.download(symbol, start=start_date, end=end_date, interval="1d")
    
    # Calculate VWAP
    data['VWAP'] = calculate_vwap(data)
    
    # Initialize results
    breakout_dates = []
    
    for i in range(lookback_days, len(data)):
        window = data.iloc[i-lookback_days:i]
        
        # Calculate average volume
        avg_volume = window['Volume'].mean()
        
        # Check if recent volume is above threshold
        recent_volume = window['Volume'].iloc[-1]
        volume_increase = recent_volume / avg_volume
        
        # Check if price is near or above VWAP
        last_close = window['Close'].iloc[-1]
        last_vwap = window['VWAP'].iloc[-1]
        price_to_vwap_ratio = last_close / last_vwap
        
        # Criteria for potential breakout
        if volume_increase > volume_threshold and price_to_vwap_ratio >= 0.98:
            breakout_dates.append(data.index[i])
    
    return data, breakout_dates

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
                                 mode='lines', name='Breakout', line=dict(color='red', width=1, dash='dash')), row=1, col=1)

    # Update layout
    fig.update_layout(height=800, title_text=f"{symbol} - Interactive Chart with Potential Breakouts", 
                      showlegend=True, hovermode="x unified")
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    return fig

# Streamlit app
st.title("Stock Breakout Scanner and Backtester")

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
lookback_days = st.slider("Lookback period (days)", 5, 30, 10)
volume_threshold = st.slider("Volume increase threshold", 1.0, 3.0, 1.5, 0.1)

# Run the scanner
if st.button("Scan for Breakout Candidates"):
    with st.spinner("Scanning..."):
        candidates = scan_for_breakout_candidates(symbols, lookback_days, volume_threshold)
    
    if not candidates.empty:
        st.subheader("Potential breakout candidates:")
        st.dataframe(candidates)
    else:
        st.info("No potential breakout candidates found.")

# Backtesting section
st.subheader("Backtest Breakout Strategy")

# Input for backtesting
backtest_symbol = st.selectbox("Select a stock symbol for backtesting:", symbols)
start_date = st.date_input("Start date", datetime(2023, 1, 1))
end_date = st.date_input("End date", datetime.now())

if st.button("Run Backtest"):
    with st.spinner("Backtesting..."):
        data, breakout_dates = backtest_breakout_strategy(backtest_symbol, start_date, end_date, lookback_days, volume_threshold)
    
    if breakout_dates:
        st.subheader(f"Backtest Results for {backtest_symbol}")
        st.write(f"Number of potential breakouts identified: {len(breakout_dates)}")
        st.write("Breakout dates:")
        for date in breakout_dates:
            st.write(date.strftime('%Y-%m-%d'))
        
        # Plot the results
        fig = plot_interactive_results(data, breakout_dates, backtest_symbol)
        st.plotly_chart(fig)
    else:
        st.info("No potential breakouts found during the backtest period.")

# Display the list of all symbols
st.subheader("All Stock Symbols:")
st.write(", ".join(symbols))


# In[ ]:





# In[ ]:




