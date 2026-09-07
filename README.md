# index-volume-analyzer
This is to check Volume of the stocks 
# Index Volume Analyzer

A Python tool designed to pull NSE constituent volume metrics, store historical daily snapshots inside **DuckDB**, and compute **Daily, Weekly (5D), and Monthly (20D)** moving averages via a **Streamlit** dashboard.

## Folder Structure

```text
index-volume-analyzer/
│
├── data/                  # DuckDB persistent storage
├── src/
│   ├── fetcher.py         # NSE HTTP Scraping & Session Handler
│   ├── processor.py       # DuckDB Data Ingestion & Rolling Averages
│   └── dashboard.py       # Streamlit UI & Interactive Charts
├── requirements.txt       # Dependencies
└── README.md
