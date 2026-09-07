import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from fetcher import NSEFetcher
from processor import VolumeProcessor

st.set_page_config(page_title="Index Volume Analyzer", layout="wide")
st.title("📊 NSE Index Volume & Order Analyzer")

fetcher = NSEFetcher()
processor = VolumeProcessor()

# Auto-seed mock data if local database is empty
processor.generate_synthetic_history_if_empty()

# --- Sidebar Actions ---
st.sidebar.header("Data Actions")
if st.sidebar.button("Fetch Today's Live NSE Data"):
    with st.spinner("Connecting to NSE..."):
        raw_df = fetcher.fetch_index_snapshot("NIFTY 50")
        if not raw_df.empty:
            processor.save_snapshot(raw_df)
            st.sidebar.success("Successfully stored today's volume metrics!")
        else:
            st.sidebar.error("Could not fetch data from NSE API.")

timeframe = st.sidebar.radio("Volume View Window", ["Daily", "Weekly Average (5D)", "Monthly Average (20D)"])

# --- Processing & Data Retrieval ---
df = processor.get_aggregated_rollups()
latest = df.iloc[-1]

# --- Key Metric Cards ---
c1, c2, c3 = st.columns(3)
c1.metric("Latest Close", f"₹{latest['close_price']:,.2f}")
c2.metric("Selected Window Volume", f"{latest['Daily_Vol'] if timeframe == 'Daily' else (latest['Weekly_Avg_Vol'] if 'Weekly' in timeframe else latest['Monthly_Avg_Vol']):,.0f}")
c3.metric("20-Day Baseline Avg", f"{latest['Monthly_Avg_Vol']:,.0f}")

st.markdown("---")

# --- Volume Trend Chart ---
st.subheader("Traded Volume vs Moving Window Trend")

selected_col = 'Daily_Vol'
if "Weekly" in timeframe:
    selected_col = 'Weekly_Avg_Vol'
elif "Monthly" in timeframe:
    selected_col = 'Monthly_Avg_Vol'

fig = go.Figure()
fig.add_trace(go.Bar(
    x=df.index,
    y=df[selected_col],
    name=f"{timeframe} Volume",
    marker_color='royalblue'
))

fig.add_trace(go.Scatter(
    x=df.index,
    y=df['close_price'],
    name="Index Price",
    yaxis="y2",
    line=dict(color="orange", width=2)
))

fig.update_layout(
    xaxis_title="Date",
    yaxis_title="Volume",
    yaxis2=dict(title="Price (₹)", overlaying="y", side="right"),
    height=500,
    legend=dict(x=0, y=1.1, orientation="h")
)

st.plotly_chart(fig, use_container_width=True)