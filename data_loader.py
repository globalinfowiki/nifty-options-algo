"""
Data Loader module: Downloads historical OHLCV data using yfinance or loads local CSVs.
"""
import os
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

class MarketDataLoader:
    def __init__(self, instrument="NIFTY", timeframe="5m"):
        self.instrument = instrument
        self.timeframe = timeframe
        self.symbol_map = {
            "NIFTY": "^NSEI",
            "BANKNIFTY": "^NSEBANK"
        }
        self.ticker_symbol = self.symbol_map.get(instrument, "^NSEI")

    def fetch_data(self, period="60d", interval="5m", cache_file=None):
        """
        Fetches intraday data. yfinance allows up to 60 days of 5m intraday data.
        For 1-year historical testing, daily or aggregated resampled data can also be evaluated.
        """
        if cache_file and os.path.exists(cache_file):
            print(f"[Data] Loading cached data from {cache_file}...")
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            return df

        print(f"[Data] Fetching {self.ticker_symbol} from Yahoo Finance (Period: {period}, Interval: {interval})...")
        try:
            df = yf.download(
                tickers=self.ticker_symbol,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=True
            )
            
            # Flatten multi-index columns if returned by yfinance
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df = df.dropna()
            
            # Format column names to standardized lowercase
            df.columns = [col.capitalize() for col in df.columns]
            
            # Ensure index has timezone handling or is converted to IST
            if df.index.tz is not None:
                df.index = df.index.tz_convert('Asia/Kolkata')
            else:
                df.index = df.index.tz_localize('UTC').tz_convert('Asia/Kolkata')

            if cache_file:
                os.makedirs(os.path.dirname(os.path.abspath(cache_file)), exist_ok=True)
                df.to_csv(cache_file)
                print(f"[Data] Saved cache to {cache_file}")

            return df
        except Exception as e:
            print(f"[Data Error] Failed to fetch data: {e}. Generating high-fidelity synthetic Nifty data for testing.")
            return self.generate_synthetic_intraday_data()

    def generate_synthetic_intraday_data(self, days=60):
        """
        Generates realistic synthetic 5-minute Nifty 50 data based on GBM and Intraday Volatility curve.
        Used as fallback or sandbox testing.
        """
        np.random.seed(42)
        start_date = datetime.now() - timedelta(days=days)
        timestamps = []
        current_date = start_date
        
        while current_date <= datetime.now():
            if current_date.weekday() < 5:  # Monday to Friday
                market_open = current_date.replace(hour=9, minute=15, second=0, microsecond=0)
                for i in range(75):  # 75 5-min bars between 9:15 and 15:30
                    timestamps.append(market_open + timedelta(minutes=5 * i))
            current_date += timedelta(days=1)

        n = len(timestamps)
        base_price = 24000.0
        # Drift and volatility
        returns = np.random.normal(0.00005, 0.0018, n)
        price_series = base_price * np.exp(np.cumsum(returns))
        
        high = price_series * (1 + np.abs(np.random.normal(0, 0.0008, n)))
        low = price_series * (1 - np.abs(np.random.normal(0, 0.0008, n)))
        open_p = price_series + np.random.normal(0, 10, n)
        close_p = price_series
        volume = np.random.randint(50000, 300000, n)

        df = pd.DataFrame({
            'Open': open_p,
            'High': high,
            'Low': low,
            'Close': close_p,
            'Volume': volume
        }, index=pd.to_datetime(timestamps))
        
        return df
