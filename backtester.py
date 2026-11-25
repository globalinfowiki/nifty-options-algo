"""
Optimized Options Backtester:
Smart Trailing Stop at 1.4R (gives room for 1:2 target without getting choked by 5m noise)
"""
import pandas as pd
import numpy as np
from datetime import time
from option_engine import OptionPricingEngine

class OptionsBacktester:
    def __init__(self, config, data: pd.DataFrame):
        self.config = config
        self.data = data
        self.pricing_engine = OptionPricingEngine(risk_free_rate=config.ANNUAL_RISK_FREE_RATE)
        self.trades = []
        self.equity_curve = []

    def run(self):
        df = self.data.copy()
        capital = self.config.INITIAL_CAPITAL
        current_trade = None
        
        current_day = None
        daily_loss_counter = 0.0
        daily_trade_count = 0
        kill_switch_activated = False

        start_time = time(9, 25)
        no_entry_time = time(14, 30)
        squareoff_time = time(15, 10)

        for i in range(1, len(df)):
            row = df.iloc[i]
            bar_time = row.name
            bar_date = bar_time.date()
            bar_time_of_day = bar_time.time()

            if current_day != bar_date:
                current_day = bar_date
                daily_loss_counter = 0.0
                daily_trade_count = 0
                kill_switch_activated = False

            if daily_loss_counter <= -abs(self.config.MAX_DAILY_LOSS):
                kill_switch_activated = True

            # If there is an active trade, evaluate SL & Target
            if current_trade is not None:
                trade = current_trade
                trade['bars_held'] += 1
                minutes_held = trade['bars_held'] * 5
                
                current_spot = row['Close']
                spot_high = row['High']
                spot_low = row['Low']

                exit_triggered = False
                exit_price = 0.0
                exit_reason = ""

                # Evaluate Trailing SL & Target
                if trade['type'] == 'CE':
                    # Trail to Breakeven+ when trade reaches 1.4R (leaves room to hit 1:2 target)
                    trail_trigger_level = trade['entry_spot'] + (trade['initial_risk_pts'] * 1.4)
                    if spot_high >= trail_trigger_level and not trade['trailed_to_be']:
                        trade['sl_spot'] = trade['entry_spot'] + (trade['initial_risk_pts'] * 0.5) # Lock +0.5R profit
                        trade['trailed_to_be'] = True

                    if spot_low <= trade['sl_spot']:
                        exit_triggered = True
                        if trade['trailed_to_be']:
                            gain_pts = (trade['sl_spot'] - trade['entry_spot']) * trade['delta']
                            exit_price = trade['entry_premium'] + gain_pts
                            exit_reason = "Trailed Stop (Profit Locked +0.5R)"
                        else:
                            loss_pts = (trade['entry_spot'] - trade['sl_spot']) * trade['delta']
                            exit_price = max(0.5, trade['entry_premium'] - loss_pts)
                            exit_reason = "Stop-Loss Hit"
                    elif spot_high >= trade['target_spot']:
                        exit_triggered = True
                        gain_pts = (trade['target_spot'] - trade['entry_spot']) * trade['delta']
                        exit_price = trade['entry_premium'] + gain_pts
                        exit_reason = "Target Hit (1:2 R:R)"
                else: # PE
                    trail_trigger_level = trade['entry_spot'] - (trade['initial_risk_pts'] * 1.4)
                    if spot_low <= trail_trigger_level and not trade['trailed_to_be']:
                        trade['sl_spot'] = trade['entry_spot'] - (trade['initial_risk_pts'] * 0.5)
                        trade['trailed_to_be'] = True

                    if spot_high >= trade['sl_spot']:
                        exit_triggered = True
                        if trade['trailed_to_be']:
                            gain_pts = (trade['entry_spot'] - trade['sl_spot']) * trade['delta']
                            exit_price = trade['entry_premium'] + gain_pts
                            exit_reason = "Trailed Stop (Profit Locked +0.5R)"
                        else:
                            loss_pts = (trade['sl_spot'] - trade['entry_spot']) * trade['delta']
                            exit_price = max(0.5, trade['entry_premium'] - loss_pts)
                            exit_reason = "Stop-Loss Hit"
                    elif spot_low <= trade['target_spot']:
                        exit_triggered = True
                        gain_pts = (trade['entry_spot'] - trade['target_spot']) * trade['delta']
                        exit_price = trade['entry_premium'] + gain_pts
                        exit_reason = "Target Hit (1:2 R:R)"

                # Time stop (75 mins) or Intraday Squareoff at 15:10
                if not exit_triggered:
                    if bar_time_of_day >= squareoff_time:
                        exit_triggered = True
                        exit_price = self.pricing_engine.simulate_option_trade_price(
                            trade['entry_spot'], current_spot, trade['entry_premium'],
                            option_type=trade['type'], delta=trade['delta'], minutes_in_trade=minutes_held
                        )
                        exit_reason = "Intraday Square-off (15:10)"
                    elif minutes_held >= self.config.MAX_TRADE_DURATION_MINS:
                        exit_triggered = True
                        exit_price = self.pricing_engine.simulate_option_trade_price(
                            trade['entry_spot'], current_spot, trade['entry_premium'],
                            option_type=trade['type'], delta=trade['delta'], minutes_in_trade=minutes_held
                        )
                        exit_reason = "Time-Stop Exit (Theta Protection)"

                if exit_triggered:
                    net_exit_premium = max(0.1, exit_price - self.config.SLIPPAGE_POINTS)
                    gross_pnl = (net_exit_premium - trade['entry_premium']) * trade['qty']
                    costs = (self.config.BROKERAGE_PER_ORDER * 2) + self.config.STT_AND_TAXES_PER_LOT
                    net_pnl = gross_pnl - costs

                    trade['exit_time'] = bar_time
                    trade['exit_spot'] = current_spot
                    trade['exit_premium'] = round(net_exit_premium, 2)
                    trade['gross_pnl'] = round(gross_pnl, 2)
                    trade['costs'] = round(costs, 2)
                    trade['net_pnl'] = round(net_pnl, 2)
                    trade['exit_reason'] = exit_reason

                    capital += net_pnl
                    daily_loss_counter += net_pnl
                    trade['capital_after'] = round(capital, 2)

                    self.trades.append(trade)
                    current_trade = None

                    if daily_loss_counter <= -abs(self.config.MAX_DAILY_LOSS):
                        kill_switch_activated = True

            # Entry Logic (1 Trade/Day, Multi-Timeframe Confirmed)
            if current_trade is None and not kill_switch_activated:
                if bar_time_of_day >= start_time and bar_time_of_day <= no_entry_time:
                    if daily_trade_count < self.config.MAX_TRADES_PER_DAY:
                        signal = row.get('Signal', 0)
                        atr = row.get('ATR', 25.0)
                        
                        if signal in [1, -1] and not pd.isna(atr) and atr > 0:
                            spot_price = row['Close']
                            strike = self.pricing_engine.get_atm_strike(spot_price, step=50)
                            
                            base_entry_premium = max(50.0, atr * 3.8)
                            entry_premium_with_slippage = base_entry_premium + self.config.SLIPPAGE_POINTS
                            
                            lot_qty = self.config.LOT_SIZE * self.config.MAX_LOTS
                            required_margin = entry_premium_with_slippage * lot_qty
                            
                            if capital >= required_margin:
                                sl_spot_dist = atr * 1.0
                                tp_spot_dist = sl_spot_dist * self.config.RISK_REWARD_RATIO

                                trade_type = 'CE' if signal == 1 else 'PE'
                                if trade_type == 'CE':
                                    sl_spot = spot_price - sl_spot_dist
                                    target_spot = spot_price + tp_spot_dist
                                else:
                                    sl_spot = spot_price + sl_spot_dist
                                    target_spot = spot_price - tp_spot_dist

                                current_trade = {
                                    'entry_time': bar_time,
                                    'type': trade_type,
                                    'strike': strike,
                                    'entry_spot': spot_price,
                                    'entry_premium': round(entry_premium_with_slippage, 2),
                                    'qty': lot_qty,
                                    'delta': self.config.ATM_DELTA,
                                    'sl_spot': round(sl_spot, 2),
                                    'target_spot': round(target_spot, 2),
                                    'initial_risk_pts': sl_spot_dist,
                                    'trailed_to_be': False,
                                    'bars_held': 0
                                }
                                daily_trade_count += 1

            self.equity_curve.append({
                'timestamp': bar_time,
                'capital': capital
            })

        return self.trades, pd.DataFrame(self.equity_curve)
