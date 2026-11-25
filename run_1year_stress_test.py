"""
1-Year Historical Multi-Cycle Stress Test:
Runs across 1 full year of Nifty 50 data (November 2025 to November 2026).
Evaluates all market regimes:
1. Bull market rallies
2. Bear market corrections
3. Election & Budget volatility
4. Range-bound choppy consolidation
Deducts ₹52 brokerage + realistic slippage on EVERY trade.
Enforces ₹350 Daily Max Loss Kill-Switch on ₹5,000 capital.
"""
import os
import pandas as pd
import numpy as np
import yfinance as yf
from config import TradingConfig
from strategy import MomentumOptionStrategy
from backtester import OptionsBacktester
from analytics import PerformanceAnalytics

def run_1year_stress_test():
    print("=" * 70)
    print("   1-YEAR HISTORICAL STRESS TEST (NIFTY 50 - 1 FULL YEAR)   ")
    print("=" * 70)
    
    config = TradingConfig()
    config.INITIAL_CAPITAL = 5000.0
    config.MAX_DAILY_LOSS = 350.0
    
    print(f"[Config] Starting Capital: ₹{config.INITIAL_CAPITAL:,.2f} | Lot Size: {config.LOT_SIZE}")
    print(f"[Config] Daily Kill-Switch: ₹{config.MAX_DAILY_LOSS:,.2f} | 1-Trade Per Day")
    print(f"[Config] Strategy: Kaufman KER (>0.38) + MTF Trend + 1:2 R:R Trailing Stop")
    
    # 1. Fetch 1-Year Historical Data from Yahoo Finance
    print("\n[Data] Fetching 1 full year of Nifty 50 data from Yahoo Finance...")
    cache_path = os.path.join(os.path.dirname(__file__), "data", "nifty_1year_hourly.csv")
    
    if os.path.exists(cache_path):
        df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
    else:
        df = yf.download('^NSEI', period='1y', interval='1h', progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna()
        df.columns = [col.capitalize() for col in df.columns]
        if df.index.tz is not None:
            df.index = df.index.tz_convert('Asia/Kolkata')
        else:
            df.index = df.index.tz_localize('UTC').tz_convert('Asia/Kolkata')
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        df.to_csv(cache_path)

    print(f"[Data] Loaded {len(df)} candles. Period: {df.index[0]} to {df.index[-1]}")

    # 2. Strategy Signal Generation
    strategy = MomentumOptionStrategy(config)
    print("\n[Strategy] Running Kaufman KER, SuperTrend, and Trend Filters across 1 Year...")
    df_signals = strategy.generate_signals(df)
    total_signals = (df_signals['Signal'] != 0).sum()
    print(f"[Strategy] Signals generated across 1 year: {total_signals} setups found.")

    # 3. Bar-by-bar Backtest
    print("\n[Backtest] Simulating bar-by-bar execution with ₹52 brokerage & ₹350 Kill-Switch...")
    backtester = OptionsBacktester(config, df_signals)
    trades, equity_df = backtester.run()

    # 4. Analytics
    analytics = PerformanceAnalytics(trades, equity_df, initial_capital=config.INITIAL_CAPITAL)
    metrics = analytics.compute_metrics()

    print("\n" + "=" * 55)
    print("        1-YEAR MULTI-CYCLE STRESS TEST REPORT        ")
    print("=" * 55)
    for key, value in metrics.items():
        if key == "Exit Breakdown":
            print("\n[Exit Reasons Breakdown]:")
            for reason, count in value.items():
                print(f"  • {reason}: {count} trades")
        else:
            print(f"{key:.<35} {value}")
    print("=" * 55)

    # Save 1-year trade log
    if trades:
        log_path = os.path.join(os.path.dirname(__file__), "trade_log_1year.csv")
        analytics.trades_df.to_csv(log_path, index=False)
        print(f"\n[Audit] Full 1-Year trade-by-trade log saved to: {log_path}")

    return metrics

if __name__ == "__main__":
    run_1year_stress_test()
