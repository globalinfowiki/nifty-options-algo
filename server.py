"""
Render Cloud Server for Nifty 50 Options Algo:
- 24/7 Web Service with /health endpoint for keep-alive ping
- Background worker thread that scans Nifty 5-minute candles during IST market hours (09:15-15:30)
- Instant Telegram mobile notifications on signal trigger
"""
import os
import time
import threading
from datetime import datetime
import pytz
from flask import Flask, jsonify, render_template_string

from live_scanner import LiveSignalScanner
from telegram_notifier import AlertNotifier

app = Flask(__name__)
IST = pytz.timezone('Asia/Kolkata')

scanner = None
scanner_status = {
    "status": "Starting",
    "last_scan_ist": None,
    "last_spot": None,
    "last_signal": None,
    "today_trades": 0,
    "is_market_open": False
}

def is_market_open_now():
    now_ist = datetime.now(IST)
    # Monday = 0, Friday = 4
    if now_ist.weekday() > 4:
        return False
    market_open = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= now_ist <= market_close

def background_scanner_thread():
    global scanner, scanner_status
    print("[Render Background Worker] Initializing Nifty Scanner...")
    time.sleep(5)  # Initial grace period
    
    try:
        scanner = LiveSignalScanner()
        scanner_status["status"] = "Active & Running"
    except Exception as e:
        scanner_status["status"] = f"Init Error: {e}"
        print(f"[Worker Error] {e}")

    last_scan_date = None

    while True:
        try:
            now_ist = datetime.now(IST)
            current_date = now_ist.date()
            
            # Reset daily trade counter at start of new day
            if last_scan_date != current_date:
                if scanner:
                    scanner.today_trades_done = 0
                last_scan_date = current_date
                scanner_status["today_trades"] = 0

            market_open = is_market_open_now()
            scanner_status["is_market_open"] = market_open

            if market_open and scanner:
                print(f"[Worker] Running market scan at {now_ist.strftime('%H:%M:%S IST')}...")
                result = scanner.scan_once()
                scanner_status["last_scan_ist"] = now_ist.strftime("%d-%b-%Y %I:%M:%S %p")
                scanner_status["today_trades"] = scanner.today_trades_done
                if result:
                    scanner_status["last_signal"] = result
            else:
                scanner_status["last_scan_ist"] = now_ist.strftime("%d-%b-%Y %I:%M:%S %p (Market Closed)")

        except Exception as e:
            print(f"[Worker Scan Exception] {e}")
            scanner_status["status"] = f"Runtime warning: {e}"

        # Sleep for 60 seconds before next check
        time.sleep(60)

# Start background scanner thread on startup
worker_thread = threading.Thread(target=background_scanner_thread, daemon=True)
worker_thread.start()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Nifty Options Algo | Cloud Scanner</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; padding: 20px; text-align: center; }
        .card { max-width: 500px; margin: 30px auto; background: #1e293b; border-radius: 12px; padding: 25px; box-shadow: 0 4px 20px rgba(0,0,0,0.4); border: 1px solid #334155; }
        .badge { display: inline-block; padding: 6px 14px; border-radius: 20px; font-weight: bold; font-size: 14px; }
        .badge-green { background: #166534; color: #4ade80; }
        .badge-red { background: #991b1b; color: #f87171; }
        .stat-row { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #334155; text-align: left; }
        .btn { display: inline-block; margin-top: 20px; padding: 12px 24px; background: #2563eb; color: white; text-decoration: none; border-radius: 8px; font-weight: bold; }
        .btn:hover { background: #1d4ed8; }
    </style>
</head>
<body>
    <div class="card">
        <h2>🚀 Nifty 50 Options Cloud Algo</h2>
        <p>
            <span class="badge {{ 'badge-green' if is_market_open else 'badge-red' }}">
                {{ '🟢 MARKET OPEN' if is_market_open else '🔴 MARKET CLOSED' }}
            </span>
        </p>
        <div class="stat-row"><span>Scanner Status:</span><strong>{{ status }}</strong></div>
        <div class="stat-row"><span>Time (IST):</span><strong>{{ current_ist }}</strong></div>
        <div class="stat-row"><span>Last Scan:</span><strong>{{ last_scan_ist }}</strong></div>
        <div class="stat-row"><span>Today Trades Done:</span><strong>{{ today_trades }} / 1</strong></div>
        <div class="stat-row"><span>Telegram Bot:</span><strong>Active (@nifty_signals_algo_bot)</strong></div>
        
        <a href="/test-alert" class="btn" target="_blank">📲 Send Test Alert to Telegram</a>
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    now_ist = datetime.now(IST).strftime("%d-%b-%Y %I:%M:%S %p")
    return render_template_string(
        HTML_TEMPLATE,
        status=scanner_status["status"],
        current_ist=now_ist,
        last_scan_ist=scanner_status["last_scan_ist"] or "Waiting for first scan...",
        today_trades=scanner_status["today_trades"],
        is_market_open=scanner_status["is_market_open"]
    )

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "service": "nifty_options_algo",
        "timestamp_ist": datetime.now(IST).isoformat(),
        "today_trades": scanner_status["today_trades"]
    }), 200

@app.route("/test-alert")
def test_alert():
    try:
        notifier = AlertNotifier()
        success = notifier.send_telegram_message(
            "🔔 *RENDER CLOUD SERVER ACTIVE!*\n\n"
            "Nifty Options Algo Scanner is running 24/7 on Render.\n"
            "Live market scans will execute automatically from 09:15 to 15:30 IST.\n\n"
            "Target Capital: ₹5,000 (1 Lot Nifty Strictly)"
        )
        if success:
            return "<h3>✅ Test message successfully sent to your Telegram! Check your phone!</h3>"
        else:
            return "<h3>⚠️ Telegram API call triggered. Check your bot @nifty_signals_algo_bot</h3>"
    except Exception as e:
        return f"<h3>Error: {e}</h3>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
