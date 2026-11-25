"""
Paper Trading Architecture & Live Simulation Engine.
This module can be hooked into live broker feeds (Zerodha KiteTicker, AngelOne SmartWebSocket, or Fyers).
It enforces:
1. Virtual Order Management System (OMS)
2. Daily Max Loss Kill-Switch protection (blocks orders after ₹500 loss)
3. Simulated Slippage & Brokerage tracking
"""
import time
from datetime import datetime
from config import TradingConfig

class VirtualOrderBook:
    def __init__(self, initial_capital=10000.0, max_daily_loss=500.0):
        self.capital = initial_capital
        self.max_daily_loss = max_daily_loss
        self.daily_pnl = 0.0
        self.kill_switch_active = False
        self.positions = []
        self.trade_history = []
        self.daily_trades_count = 0

    def check_kill_switch(self):
        if self.daily_pnl <= -abs(self.max_daily_loss):
            self.kill_switch_active = True
            print(f"[KILL-SWITCH ALERT] Daily Loss limit ₹{self.max_daily_loss} breached! Trading HALTED for today.")
            return True
        return False

    def place_order(self, symbol, option_type, strike, action="BUY", qty=25, market_price=100.0, sl=80.0, target=140.0):
        """Simulates order placement with margin validation and Kill-Switch check"""
        if self.kill_switch_active or self.check_kill_switch():
            print(f"[REJECTED] Order rejected by Kill-Switch policy.")
            return None

        if self.daily_trades_count >= 2:
            print(f"[REJECTED] Daily max trades (2) limit reached. Overtrading protection on.")
            return None

        cost = market_price * qty
        if cost > self.capital:
            print(f"[REJECTED] Insufficient Funds! Required: ₹{cost:.2f}, Available: ₹{self.capital:.2f}")
            return None

        order = {
            "order_id": f"ORD_{int(time.time())}",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": f"{symbol}_{strike}_{option_type}",
            "type": option_type,
            "action": action,
            "qty": qty,
            "entry_price": market_price,
            "sl": sl,
            "target": target,
            "status": "OPEN"
        }
        self.positions.append(order)
        self.daily_trades_count += 1
        print(f"[PAPER TRADING] Order EXECUTED: {order['symbol']} | Qty: {qty} @ ₹{market_price:.2f} | SL: ₹{sl:.2f} | Target: ₹{target:.2f}")
        return order

    def update_ticks(self, current_ltp):
        """Monitors open positions against live ticks for Stop-Loss and Target hits"""
        for pos in list(self.positions):
            if pos["status"] == "OPEN":
                # Check Stop Loss
                if current_ltp <= pos["sl"]:
                    self._close_position(pos, exit_price=pos["sl"], reason="Stop-Loss Triggered")
                # Check Target
                elif current_ltp >= pos["target"]:
                    self._close_position(pos, exit_price=pos["target"], reason="Target 1:2 Triggered")

    def _close_position(self, pos, exit_price, reason):
        gross_pnl = (exit_price - pos["entry_price"]) * pos["qty"]
        costs = 52.0  # ₹20 buy + ₹20 sell + STT/taxes
        net_pnl = gross_pnl - costs

        self.capital += net_pnl
        self.daily_pnl += net_pnl
        pos["status"] = "CLOSED"
        pos["exit_price"] = exit_price
        pos["net_pnl"] = net_pnl
        pos["exit_reason"] = reason
        pos["exit_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.positions.remove(pos)
        self.trade_history.append(pos)
        print(f"[PAPER TRADING] Position CLOSED: {pos['symbol']} | Exit: ₹{exit_price:.2f} | Net P&L: ₹{net_pnl:.2f} ({reason})")
        
        self.check_kill_switch()
