"""
Notification Engine:
1. Audio Alert (Beep sound on PC so you don't miss trades)
2. Beautiful Console Box
3. Telegram Bot Notification (Automated when on personal Wi-Fi / Hotspot)
"""
import requests
import json
try:
    import winsound
except ImportError:
    winsound = None
from datetime import datetime

class AlertNotifier:
    def __init__(self, bot_token="9148002055:AAHp3ZmZR2uvwdyF_ri3jxJdpNc-5fCDHqc", chat_id="7827646925"):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.telegram_active = bool(bot_token and chat_id)

    def play_sound(self, alert_type="entry"):
        if not winsound:
            return
        try:
            if alert_type == "entry":
                # Double beep for entry
                winsound.Beep(1200, 200)
                winsound.Beep(1600, 300)
            else:
                # Single long beep for exit
                winsound.Beep(1000, 400)
        except Exception:
            pass

    def send_telegram_message(self, message: str):
        if not self.telegram_active:
            return False
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            res = requests.post(url, json=payload, timeout=3)
            return res.status_code == 200
        except Exception:
            return False

    def notify_entry_signal(self, symbol, option_type, strike, entry_price, sl_price, target_price, qty=25, reason=""):
        risk_per_lot = round((entry_price - sl_price) * qty, 2)
        reward_per_lot = round((target_price - entry_price) * qty, 2)
        now_str = datetime.now().strftime("%I:%M %p | %d-%b-%Y")

        # 1. Play Audio Alarm
        self.play_sound("entry")

        # 2. Terminal Visual Alert
        terminal_alert = f"""
╔══════════════════════════════════════════════════════════════════════╗
║                    🔔 NIFTY ALGO SIGNAL: {option_type} BUY ALERT                      ║
╠══════════════════════════════════════════════════════════════════════╣
║  ⏰ Time        : {now_str:<46} ║
║  📌 Action      : BUY {option_type:<41} ║
║  🎯 Strike      : {symbol} {strike} {option_type:<32} ║
║  📦 Quantity    : {qty} Qty (1 Lot Strictly)                           ║
║  💵 Entry Price : ₹{entry_price:<44.2f} ║
║  🛑 Stop-Loss   : ₹{sl_price:<7.2f} (Max Risk: ₹{risk_per_lot:<20.2f}) ║
║  🎯 Target 1:2  : ₹{target_price:<7.2f} (Potential Reward: ₹{reward_per_lot:<12.2f}) ║
║  ⏳ Time Stop   : 75 Mins (Theta Protection Exit)                    ║
║  📊 Setup Rule  : {reason:<46} ║
╚══════════════════════════════════════════════════════════════════════╝
"""
        print(terminal_alert)

        # 3. Telegram Message
        telegram_msg = (
            f"🔔 *NIFTY ALGO SIGNAL: BUY {option_type}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 *Action:* BUY `{option_type}`\n"
            f"🎯 *Strike:* `{symbol} {strike} {option_type}`\n"
            f"📦 *Quantity:* `{qty} (1 Lot)`\n"
            f"💵 *Entry:* `₹{entry_price:.2f}`\n"
            f"🛑 *Stop-Loss:* `₹{sl_price:.2f}` _(Risk: ₹{risk_per_lot:.0f})_\n"
            f"🎯 *Target (1:2):* `₹{target_price:.2f}` _(Reward: ₹{reward_per_lot:.0f})_\n"
            f"⏳ *Theta Limit:* 75 Mins\n"
            f"📊 *Reason:* {reason}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ _{now_str}_"
        )
        sent = self.send_telegram_message(telegram_msg)
        if sent:
            print("[Telegram] Alert delivered to your phone successfully.")

    def notify_exit_signal(self, symbol, option_type, strike, exit_price, pnl, exit_reason=""):
        now_str = datetime.now().strftime("%I:%M %p | %d-%b-%Y")
        emoji = "🎯 TARGET HIT!" if pnl > 0 else "🛑 STOP-LOSS EXIT"
        
        self.play_sound("exit")

        terminal_alert = f"""
╔══════════════════════════════════════════════════════════════════════╗
║                    {emoji:<49} ║
╠══════════════════════════════════════════════════════════════════════╣
║  ⏰ Time        : {now_str:<46} ║
║  🎯 Strike      : {symbol} {strike} {option_type:<32} ║
║  💵 Exit Price  : ₹{exit_price:<44.2f} ║
║  💰 Net P&L     : ₹{pnl:<44.2f} ║
║  📌 Exit Reason : {exit_reason:<46} ║
║  🛡️ Status      : 1-Trade Per Day Rule (Today Closed)                ║
╚══════════════════════════════════════════════════════════════════════╝
"""
        print(terminal_alert)

        telegram_msg = (
            f"*{emoji}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 *Contract:* `{symbol} {strike} {option_type}`\n"
            f"💵 *Exit Price:* `₹{exit_price:.2f}`\n"
            f"💰 *Net P&L:* `₹{pnl:+.2f}`\n"
            f"📌 *Reason:* {exit_reason}\n"
            f"🛡️ *Rule:* 1-Trade Per Day Done. System Resting.\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ _{now_str}_"
        )
        self.send_telegram_message(telegram_msg)
