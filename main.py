"""
Main Execution Script with robust file saving & optimized reporting.
"""
import os
import sys
from config import TradingConfig
from data_loader import MarketDataLoader
from strategy import MomentumOptionStrategy
from backtester import OptionsBacktester
from analytics import PerformanceAnalytics

def main():
    print("=" * 70)
    print("   OPTIMIZED NIFTY 50 OPTIONS ALGO SYSTEM (MTF + TRAILING SL)   ")
    print("=" * 70)
    
    config = TradingConfig()
    print(f"[Config] Capital: ₹{config.INITIAL_CAPITAL:,.2f} | Instrument: {config.INSTRUMENT} (1 Lot: {config.LOT_SIZE} qty)")
    print(f"[Config] Max Daily Loss Kill-Switch: ₹{config.MAX_DAILY_LOSS:,.2f} | Max Trades/Day: {config.MAX_TRADES_PER_DAY}")
    print(f"[Config] Risk-Reward Ratio: 1:{config.RISK_REWARD_RATIO} | Strategy: MTF 15m Trend + 5m Breakout + ADX > {config.ADX_THRESHOLD}")
    
    # 1. Fetch Market Data
    loader = MarketDataLoader(instrument=config.INSTRUMENT, timeframe=config.TIMEFRAME)
    cache_path = os.path.join(os.path.dirname(__file__), "data", "nifty_5m_data.csv")
    df = loader.fetch_data(period="60d", interval="5m", cache_file=cache_path)
    print(f"[Data] Loaded {len(df)} 5-minute candles. Date range: {df.index[0]} to {df.index[-1]}")

    # 2. Strategy Signal Generation
    strategy = MomentumOptionStrategy(config)
    print("[Strategy] Calculating Multi-Timeframe (15m + 5m), SuperTrend, ATR, and ADX indicators...")
    df_signals = strategy.generate_signals(df)
    total_signals = (df_signals['Signal'] != 0).sum()
    print(f"[Strategy] High-conviction signals generated: {total_signals} setups found.")

    # 3. Run Backtest
    print("[Backtest] Running bar-by-bar simulation with slippage, brokerage, and Kill-Switch...")
    backtester = OptionsBacktester(config, df_signals)
    trades, equity_df = backtester.run()

    # 4. Analytics & Report
    analytics = PerformanceAnalytics(trades, equity_df, initial_capital=config.INITIAL_CAPITAL)
    metrics = analytics.compute_metrics()

    print("\n" + "=" * 50)
    print("             BACKTEST PERFORMANCE REPORT         ")
    print("=" * 50)
    for key, value in metrics.items():
        if key == "Exit Breakdown":
            print("\n[Exit Reasons Breakdown]:")
            for reason, count in value.items():
                print(f"  • {reason}: {count} trades")
        else:
            print(f"{key:.<32} {value}")
    print("=" * 50)

    # 5. Generate Chart
    chart_path = os.path.join(os.path.dirname(__file__), "equity_curve.png")
    try:
        analytics.generate_equity_plot(chart_path)
        print(f"\n[Chart] Equity Curve chart saved to: {chart_path}")
    except Exception as e:
        print(f"[Chart Warning] Could not save chart: {e}")

    # Save Trades log to CSV safely
    if trades:
        trades_csv_path = os.path.join(os.path.dirname(__file__), "trade_log_optimized.csv")
        try:
            analytics.trades_df.to_csv(trades_csv_path, index=False)
            print(f"[Trades] Detailed trade-by-trade log saved to: {trades_csv_path}")
        except Exception as e:
            print(f"[Trades Warning] Could not save trades log: {e}")

if __name__ == "__main__":
    main()
