# Nifty 50 & Bank Nifty Options Algo Trading & Backtesting System

## 📌 Overview
Yeh system vishesh roop se **₹10,000 Target Capital (1 Lot Intraday)** ke liye banaya gaya hai jisme:
1. **Theta Decay Protection**: High-momentum time windows (09:25 - 10:45 AM & 13:15 - 14:30 PM) aur 60-minute time-stop logic.
2. **Strict Risk Management**: 
   - **Daily Max Loss Kill-Switch**: ₹500 (5% of capital) hit hote hi trading turant band ho jayegi.
   - **Overtrading Lock**: Maximum 1 trade per day (Brokerage drain se bachne ke liye).
   - **1:2 Risk-Reward Ratio**: Dynamic ATR-based Stop Loss aur Target.
3. **Realistic Friction Modeling**:
   - Zerodha/Groww ₹20/order brokerage + STT + GST (~₹52 per round-trip trade).
   - 0.8 points slippage per trade.
   - Real-time Black-Scholes Greeks aur Delta passthrough.

---

## 📂 Project Structure
```
nifty_options_algo/
│
├── config.py             # Capital, Lot size, Kill-Switch (₹500), R:R, Brokerage settings
├── data_loader.py        # Historical 5-min OHLCV data fetcher (yfinance & local cache)
├── option_engine.py      # Black-Scholes formula, Greeks (Delta, Theta, Vega) & Option Simulator
├── strategy.py           # SuperTrend (10, 2) + EMA (9/21/50) + ADX (>20) + Breakout engine
├── backtester.py         # Bar-by-bar execution loop with Kill-Switch & realistic slippage
├── analytics.py          # Win Rate, Profit Factor, Drawdown, Equity Curve generator
├── paper_trader.py       # Live tick virtual order book & paper trading engine
├── main.py               # Main CLI runner to run backtest & export reports
├── run_comparison.py     # Comparison between Naked Buying vs Hedged Spread
├── equity_curve.png      # Generated Equity Curve chart
└── trade_log.csv         # Complete trade-by-trade audit log
```

---

## 🚀 Step-by-Step Guide

### Step 1: Backtest Run Karein
```bash
python main.py
```
Yeh pichle historical data par backtest run karega, Win Rate, P&L, Max Drawdown calculate karega aur `equity_curve.png` generate karega.

### Step 2: Paper Trading Test Karein
```bash
python -c "from paper_trader import VirtualOrderBook; v = VirtualOrderBook(); v.place_order('NIFTY', 'CE', 24500, 'BUY', 25, 110.0, 90.0, 150.0); v.update_ticks(155.0)"
```

### Step 3: Broker API Integration (Live / Paper Feed)
Live trading ke liye `paper_trader.py` me apne broker (Zerodha KiteConnect / AngelOne SmartAPI) ka WebSocket tick feed connect karein.

---

## ⚠️ Important Capital Insights (₹10,000 Capital Reality)
Hamare backtesting audit se ek behad mahatvapurna cheez samne aayi hai:
- **Brokerage Drain**: Agar aap ₹10,000 capital par din ke 3-4 trades karte hain (mahine me 60 trades), toh **₹3,100 se ₹3,800 sirf brokerage aur taxes me chala jata hai** (Capital ka 35%+).
- **Solution**: Hamari system me **1 Trade Per Day rule** aur **₹500 Daily Kill-Switch** laga hai taaki aapka capital safe rahe aur aap sirf high-probability momentum setups trade karein.
