"""
Demo script to test how the Entry and Exit Alert looks on Terminal & Telegram.
"""
from telegram_notifier import AlertNotifier

def test_alerts():
    notifier = AlertNotifier()
    
    print("\n--- SAMPLE ENTRY ALERT ---")
    notifier.notify_entry_signal(
        symbol="NIFTY",
        option_type="CE",
        strike=25700,
        entry_price=115.0,
        sl_price=90.0,
        target_price=165.0,
        qty=25,
        reason="10-bar Donchian Breakout + SuperTrend Bullish + ADX 23"
    )

    print("\n--- SAMPLE TARGET HIT ALERT ---")
    notifier.notify_exit_signal(
        symbol="NIFTY",
        option_type="CE",
        strike=25700,
        exit_price=165.5,
        pnl=1210.0,
        exit_reason="Target 1:2 R:R Hit"
    )

if __name__ == "__main__":
    test_alerts()
