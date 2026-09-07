import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from fetcher import NSEFetcher
from processor import VolumeProcessor

st.set_page_config(page_title="NSE Stock & Index Volume Analyzer", layout="wide")
st.title("📊 NSE Stock-Level Volume & Breakout Analyzer")

fetcher = NSEFetcher()
processor = VolumeProcessor()

# Seed database if empty
processor.generate_synthetic_history_if_empty()

# --- Sidebar Controls ---
st.sidebar.header("Data Sync & Filters")

if st.sidebar.button("Fetch Live NSE Snapshot"):
    with st.spinner("Fetching latest stock volumes..."):
        df_live = fetcher.fetch_index_snapshot("NIFTY 50")
        if not df_live.empty:
            processor.save_snapshot(df_live)
            st.sidebar.success("Saved live snapshot to DuckDB!")
        else:
            st.sidebar.error("Failed to fetch live data from NSE.")

# Fetch raw stock records from DB
conn = processor._init_db()  # Ensures tables exist
conn_db = processor.get_connection() if hasattr(processor, 'get_connection') else None

import duckdb
conn_db = duckdb.connect(processor.db_path)
raw_df = conn_db.execute("SELECT * FROM index_volumes").df()
conn_db.close()

if raw_df.empty:
    st.warning("No data found in database.")
    st.stop()

# Convert dates
raw_df['date'] = pd.to_datetime(raw_df['date'])

# Get unique stock symbols
symbols = sorted(raw_df['symbol'].unique())

view_mode = st.sidebar.radio(
    "Select View Mode",
    ["Stock-Level Analysis", "🔥 Breakout Watch: Vol > Weekly Avg"]
)

# --- View Mode 1: Individual Stock Filtering ---
if view_mode == "Stock-Level Analysis":
    selected_stock = st.sidebar.selectbox("Select Stock Symbol", symbols)
    
    # Filter data for selected stock
    stock_df = raw_df[raw_df['symbol'] == selected_stock].sort_values('date').copy()
    
    # Compute 5-Day (Weekly) and 20-Day (Monthly) Rolling Averages
    stock_df['Weekly_Avg_Vol'] = stock_df['total_volume'].rolling(window=5, min_periods=1).mean()
    stock_df['Monthly_Avg_Vol'] = stock_df['total_volume'].rolling(window=20, min_periods=1).mean()
    
    latest_row = stock_df.iloc[-1]
    vol_vs_weekly = ((latest_row['total_volume'] - latest_row['Weekly_Avg_Vol']) / latest_row['Weekly_Avg_Vol']) * 100
    
    # Metric Summary
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Selected Symbol", selected_stock)
    c2.metric("Latest Price", f"₹{latest_row['last_price']:,.2f}", f"{latest_row['p_change']:.2f}%")
    c3.metric("Daily Volume", f"{latest_row['total_volume']:,}")
    c4.metric("Vs 5-Day Weekly Avg", f"{vol_vs_weekly:+.2f}%", delta_color="normal")
    
    st.markdown("---")
    
    # Stock Chart
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=stock_df['date'],
        y=stock_df['total_volume'],
        name="Daily Volume",
        marker_color='lightslategrey'
    ))
    fig.add_trace(go.Scatter(
        x=stock_df['date'],
        y=stock_df['Weekly_Avg_Vol'],
        name="5-Day (Weekly) Avg Vol",
        line=dict(color='limegreen', width=2)
    ))
    fig.add_trace(go.Scatter(
        x=stock_df['date'],
        y=stock_df['Monthly_Avg_Vol'],
        name="20-Day (Monthly) Avg Vol",
        line=dict(color='crimson', width=2, dash='dot')
    ))
    fig.add_trace(go.Scatter(
        x=stock_df['date'],
        y=stock_df['last_price'],
        name="Close Price",
        yaxis="y2",
        line=dict(color='orange', width=2)
    ))
    
    fig.update_layout(
        title=f"{selected_stock} Volume Moving Averages vs. Price",
        xaxis_title="Date",
        yaxis_title="Volume (Shares)",
        yaxis2=dict(title="Price (₹)", overlaying="y", side="right"),
        height=500,
        legend=dict(x=0, y=1.1, orientation="h")
    )
    st.plotly_chart(fig, use_container_width=True)

# --- View Mode 2: Volume > Weekly Average Breakouts ---
elif view_mode == "🔥 Breakout Watch: Vol > Weekly Avg":
    st.subheader("🚀 Stocks Where Daily Volume > 5-Day (Weekly) Average")
    
    # Calculate rolling weekly average for every stock independently
    raw_df['Weekly_Avg_Vol'] = raw_df.groupby('symbol')['total_volume'].transform(
        lambda x: x.rolling(window=5, min_periods=1).mean()
    )
    
    # Get latest date in dataset
    latest_date = raw_df['date'].max()
    latest_df = raw_df[raw_df['date'] == latest_date].copy()
    
    # Filter for volume exceeding weekly average
    breakout_df = latest_df[latest_df['total_volume'] > latest_df['Weekly_Avg_Vol']].copy()
    
    # Calculate percentage volume surge
    breakout_df['Vol_Surge_Pct'] = (
        (breakout_df['total_volume'] - breakout_df['Weekly_Avg_Vol']) / breakout_df['Weekly_Avg_Vol']
    ) * 100
    
    # Sort by highest surge percentage and pick top 10
    top_10 = breakout_df.sort_values(by='Vol_Surge_Pct', ascending=False).head(10)
    
    if top_10.empty:
        st.info("No stocks currently exceeding their 5-day weekly volume average.")
    else:
        st.markdown(f"Displaying top stocks on **{latest_date.strftime('%Y-%m-%d')}** exceeding their 5-day rolling average:")
        
        # Display Bar Chart of Top Surges
        fig_top = go.Figure()
        fig_top.add_trace(go.Bar(
            x=top_10['symbol'],
            y=top_10['total_volume'],
            name="Daily Volume",
            marker_color='dodgerblue'
        ))
        fig_top.add_trace(go.Bar(
            x=top_10['symbol'],
            y=top_10['Weekly_Avg_Vol'],
            name="5-Day (Weekly) Avg",
            marker_color='orange'
        ))
        
        fig_top.update_layout(
            barmode='group',
            xaxis_title="Stock Symbol",
            yaxis_title="Volume",
            height=400,
            legend=dict(x=0, y=1.1, orientation="h")
        )
        st.plotly_chart(fig_top, use_container_width=True)
        
        # Display Data Table
        display_cols = ['symbol', 'last_price', 'p_change', 'total_volume', 'Weekly_Avg_Vol', 'Vol_Surge_Pct']
        formatted_df = top_10[display_cols].copy()
        formatted_df.columns = ['Symbol', 'Price (₹)', 'Change (%)', 'Daily Volume', 'Weekly Avg Vol', 'Surge vs Weekly (%)']
        
        st.dataframe(
            formatted_df.style.format({
                'Price (₹)': '₹{:.2f}',
                'Change (%)': '{:+.2f}%',
                'Daily Volume': '{:,.0f}',
                'Weekly Avg Vol': '{:,.0f}',
                'Surge vs Weekly (%)': '+{:.2f}%'
            }),
            use_container_width=True
        )