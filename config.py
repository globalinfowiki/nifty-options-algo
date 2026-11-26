"""
Configuration settings for Nifty/Bank Nifty Algo Trading & Backtesting System.
DYNAMIC CAPITAL CONFIGURATION:
Supports ₹5,000 Starting Capital (1 Lot Nifty)
"""
from dataclasses import dataclass

@dataclass
class TradingConfig:
    # Capital & Sizing
    INITIAL_CAPITAL: float = 5000.0   # ₹5,000 Starting Capital
    INSTRUMENT: str = "NIFTY"         # 'NIFTY' or 'BANKNIFTY'
    LOT_SIZE: int = 25                # Nifty 50 Lot Size (25)
    MAX_LOTS: int = 1                 # 1 Lot execution strictly
    MAX_PREMIUM_PRICE: float = 160.0  # Cap on option premium to ensure margin fits ₹5k (Leaves cash buffer)
    
    # Strategy Parameters (Multi-Timeframe + Volatility)
    TIMEFRAME: str = "5m"             # Execution Timeframe: 5m
    HIGHER_TIMEFRAME: str = "15m"     # Trend Filter Timeframe: 15m
    EMA_FAST: int = 9
    EMA_SLOW: int = 21
    EMA_BASELINE: int = 50
    SUPERTREND_PERIOD: int = 10
    SUPERTREND_MULTIPLIER: float = 2.0
    ADX_PERIOD: int = 14
    ADX_THRESHOLD: float = 22.0
    ATR_PERIOD: int = 14
    TRADING_MODE: str = "balanced"    # 'balanced' (Active Momentum) or 'sniper' (Strict Breakout)
    KER_THRESHOLD: float = 0.22       # 0.22 for balanced, 0.38 for sniper
    
    # Risk Management & Kill-Switch for ₹5,000 Capital
    RISK_REWARD_RATIO: float = 2.0    # 1:2 R:R strictly
    TRAIL_TO_BREAKEVEN_AT_1R: bool = True
    MAX_DAILY_LOSS: float = 350.0     # ₹350 Daily Max Loss Kill-Switch (strictly adapted for ₹5,000)
    MAX_TRADES_PER_DAY: int = 1       # 1 high-probability trade per day
    MAX_TRADE_DURATION_MINS: int = 75 # Theta protection exit
    
    # Intraday Timing Constraints (IST)
    MARKET_START_TIME: str = "09:25"  
    NO_NEW_ENTRY_AFTER: str = "14:30" 
    INTRADAY_SQUAREOFF: str = "15:10" 
    
    # Realistic Slippage & F&O Charges
    SLIPPAGE_POINTS: float = 0.8
    BROKERAGE_PER_ORDER: float = 20.0
    STT_AND_TAXES_PER_LOT: float = 12.0
    
    # Option Greeks & Pricing
    OPTION_SELECTION: str = "ATM"
    ATM_DELTA: float = 0.52
    ANNUAL_RISK_FREE_RATE: float = 0.07 
    DEFAULT_IV: float = 0.14

    # Telegram Notification Credentials
    TELEGRAM_BOT_TOKEN: str = "9148002055:AAHp3ZmZR2uvwdyF_ri3jxJdpNc-5fCDHqc"
    TELEGRAM_CHAT_ID: str = "7827646925"
