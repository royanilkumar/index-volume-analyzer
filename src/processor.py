import duckdb
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

DB_PATH = "data/volume_data.duckdb"

class VolumeProcessor:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initializes tables in DuckDB if they do not exist."""
        conn = duckdb.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS index_volumes (
                date DATE,
                symbol VARCHAR,
                last_price DOUBLE,
                p_change DOUBLE,
                total_volume BIGINT,
                total_value DOUBLE
            );
        """)
        conn.close()

    def save_snapshot(self, df: pd.DataFrame):
        """Saves daily volume records into DuckDB."""
        if df.empty:
            return
        conn = duckdb.connect(self.db_path)
        # Avoid duplicate ingestion for the same date/symbol
        conn.execute("DELETE FROM index_volumes WHERE date = ?", [df['date'].iloc[0]])
        conn.register("df_view", df)
        conn.execute("INSERT INTO index_volumes SELECT * FROM df_view")
        conn.close()

    def generate_synthetic_history_if_empty(self):
        """Populates historical data if the database is brand new."""
        conn = duckdb.connect(self.db_path)
        count = conn.execute("SELECT COUNT(*) FROM index_volumes").fetchone()[0]
        
        if count == 0:
            dates = pd.date_range(end=datetime.today(), periods=90, freq='D')
            records = []
            np.random.seed(42)
            
            for d in dates:
                d_str = d.strftime('%Y-%m-%d')
                base_vol = np.random.randint(1_000_000, 5_000_000)
                records.append({
                    "date": d_str,
                    "symbol": "NIFTY_AGGREGATE",
                    "last_price": 22000 + np.random.randn() * 100,
                    "p_change": np.random.uniform(-1.5, 1.5),
                    "total_volume": base_vol,
                    "total_value": base_vol * 22000
                })
            df_hist = pd.DataFrame(records)
            conn.register("df_hist_view", df_hist)
            conn.execute("INSERT INTO index_volumes SELECT * FROM df_hist_view")
        conn.close()

    def get_aggregated_rollups(self):
        """Queries DuckDB and calculates Daily, Weekly (5D), and Monthly (20D) moving averages."""
        conn = duckdb.connect(self.db_path)
        df = conn.execute("SELECT date, sum(total_volume) as total_volume, avg(last_price) as close_price FROM index_volumes GROUP BY date ORDER BY date ASC").df()
        conn.close()

        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

        # Resampling & Rolling Computations
        df['Daily_Vol'] = df['total_volume']
        df['Weekly_Avg_Vol'] = df['total_volume'].rolling(window=5, min_periods=1).mean()
        df['Monthly_Avg_Vol'] = df['total_volume'].rolling(window=20, min_periods=1).mean()

        return df