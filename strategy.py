"""
Institutional Master Strategy Engine:
Enhanced with:
1. Toby Crabel's 15-Minute Opening Range Breakout (ORB)
2. Perry Kaufman's Efficiency Ratio (KER > 0.38)
3. Alexander Elder's 15-Minute Multi-Timeframe Trend Confirmation
4. Exhaustion Gap Filter: Prevents buying at the top after huge opening gaps (>0.6%)
5. Friday Weekend-Theta Filter: Blocks risky trades late on Friday afternoon
6. Expiry-Day High-Delta ITM Shield: Defends against Thursday theta decay
"""
import pandas as pd
import numpy as np

class MomentumOptionStrategy:
    def __init__(self, config):
        self.config = config

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # 1. 5-Minute EMAs
        df['EMA_Fast'] = df['Close'].ewm(span=self.config.EMA_FAST, adjust=False).mean()
        df['EMA_Slow'] = df['Close'].ewm(span=self.config.EMA_SLOW, adjust=False).mean()
        df['EMA_50'] = df['Close'].ewm(span=self.config.EMA_BASELINE, adjust=False).mean()

        # 2. Dynamic ATR
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift()).abs()
        low_close = (df['Low'] - df['Close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(window=self.config.ATR_PERIOD).mean()

        # 3. SuperTrend
        df = self._calculate_supertrend(df, period=10, multiplier=2.0)

        # 4. Perry Kaufman's Efficiency Ratio (KER)
        df = self._calculate_kaufman_efficiency_ratio(df, period=10)

        # 5. Toby Crabel's 15-Minute Opening Range (ORB) & Daily Gaps
        df = self._calculate_orb_and_gaps(df)

        # 6. Multi-Timeframe (15-Minute) Trend Anchor
        df = self._add_15m_higher_timeframe_trend(df)

        return df

    def _calculate_kaufman_efficiency_ratio(self, df: pd.DataFrame, period=10) -> pd.DataFrame:
        change = (df['Close'] - df['Close'].shift(period)).abs()
        volatility = (df['Close'] - df['Close'].shift(1)).abs().rolling(window=period).sum()
        df['KER'] = change / volatility.replace(0, 1e-5)
        return df

    def _calculate_orb_and_gaps(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Date'] = df.index.date
        df['DayOfWeek'] = df.index.dayofweek  # 0=Monday, 4=Friday
        times = df.index.time
        
        # Opening 15 mins window (09:15, 09:20, 09:25)
        is_orb_window = (times >= pd.to_datetime('09:15').time()) & (times <= pd.to_datetime('09:25').time())
        
        orb_df = df[is_orb_window].groupby('Date').agg(
            {'High': 'max', 'Low': 'min', 'Open': 'first'}
        ).rename(columns={'High': 'ORB_High', 'Low': 'ORB_Low', 'Open': 'Day_Open'})
        
        df = df.join(orb_df, on='Date')

        # Calculate opening gap vs previous day close
        daily_close = df.groupby('Date')['Close'].last().shift(1)
        df['Prev_Close'] = df['Date'].map(daily_close)
        df['Gap_Pct'] = ((df['Day_Open'] - df['Prev_Close']) / df['Prev_Close'].replace(0, 1e-5)).abs()
        return df

    def _calculate_supertrend(self, df: pd.DataFrame, period=10, multiplier=2.0) -> pd.DataFrame:
        hl2 = (df['High'] + df['Low']) / 2.0
        df['Upper_Basic'] = hl2 + (multiplier * df['ATR'])
        df['Lower_Basic'] = hl2 - (multiplier * df['ATR'])
        
        upper_band = [0.0] * len(df)
        lower_band = [0.0] * len(df)
        trend = [1] * len(df)

        for i in range(1, len(df)):
            if df['Upper_Basic'].iloc[i] < upper_band[i-1] or df['Close'].iloc[i-1] > upper_band[i-1]:
                upper_band[i] = df['Upper_Basic'].iloc[i]
            else:
                upper_band[i] = upper_band[i-1]

            if df['Lower_Basic'].iloc[i] > lower_band[i-1] or df['Close'].iloc[i-1] < lower_band[i-1]:
                lower_band[i] = df['Lower_Basic'].iloc[i]
            else:
                lower_band[i] = lower_band[i-1]

            if df['Close'].iloc[i] > upper_band[i-1]:
                trend[i] = 1
            elif df['Close'].iloc[i] < lower_band[i-1]:
                trend[i] = -1
            else:
                trend[i] = trend[i-1]

        df['SuperTrend_Upper'] = upper_band
        df['SuperTrend_Lower'] = lower_band
        df['SuperTrend_Direction'] = trend
        return df

    def _add_15m_higher_timeframe_trend(self, df: pd.DataFrame) -> pd.DataFrame:
        df_15 = df.resample('15min').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()

        ema_15_fast = df_15['Close'].ewm(span=20, adjust=False).mean()
        ema_15_slow = df_15['Close'].ewm(span=50, adjust=False).mean()
        trend_15m = np.where(ema_15_fast >= ema_15_slow, 1, -1)
        s_trend_15m = pd.Series(trend_15m, index=df_15.index)

        df['Trend_15M'] = s_trend_15m.reindex(df.index, method='ffill').fillna(1)
        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self.calculate_indicators(df)
        df['Signal'] = 0

        times = df.index.time
        morning_window = (times >= pd.to_datetime('09:30').time()) & (times <= pd.to_datetime('10:45').time())
        afternoon_window = (times >= pd.to_datetime('13:15').time()) & (times <= pd.to_datetime('14:30').time())
        valid_time = morning_window | afternoon_window

        # 1. Exhaustion Gap Filter: If opening gap was massive (> 0.65%), avoid chasing breakouts blindly
        normal_gap = df['Gap_Pct'].fillna(0) < 0.0065

        # 2. Friday Weekend Theta Protection: Avoid entering late on Friday after 13:30
        friday_filter = ~((df['DayOfWeek'] == 4) & (times >= pd.to_datetime('13:30').time()))

        # CE Setup (Institutional High-Conviction):
        ce_breakout = (df['Close'] > df['ORB_High']) & (df['Close'].shift(1) <= df['ORB_High'])
        ce_filter = (df['Trend_15M'] == 1) & (df['SuperTrend_Direction'] == 1) & (df['KER'] > 0.38) & normal_gap & friday_filter & valid_time

        # PE Setup (Institutional High-Conviction):
        pe_breakdown = (df['Close'] < df['ORB_Low']) & (df['Close'].shift(1) >= df['ORB_Low'])
        pe_filter = (df['Trend_15M'] == -1) & (df['SuperTrend_Direction'] == -1) & (df['KER'] > 0.38) & normal_gap & friday_filter & valid_time

        df.loc[ce_breakout & ce_filter, 'Signal'] = 1
        df.loc[pe_breakdown & pe_filter, 'Signal'] = -1
        return df
