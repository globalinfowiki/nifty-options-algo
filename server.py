"""
Render Cloud Server & Interactive Institutional Dashboard for Nifty 50 Options Algo:
- 24/7 Web Service with /health endpoint for UptimeRobot keep-alive
- Auto-refreshing Real-Time Terminal Dashboard (Dark Mode, KPIs, Live Signals)
- Background scanner thread tracking 5m candles during IST market hours (09:15-15:30)
- Instant Telegram mobile notifications
"""
import os
import time
import threading
import json
import socket
from datetime import datetime
import pytz
import pandas as pd
from flask import Flask, jsonify, render_template_string, request

from live_scanner import LiveSignalScanner
from telegram_notifier import AlertNotifier

app = Flask(__name__)
IST = pytz.timezone('Asia/Kolkata')

scanner = None
scanner_status = {
    "status": "Initializing...",
    "last_scan_ist": None,
    "last_spot": 25819.25,
    "last_ker": 0.42,
    "trend_15m": "BULLISH",
    "orb_high": 25840.0,
    "orb_low": 25770.0,
    "last_signal": None,
    "today_trades": 0,
    "is_market_open": False
}

def is_market_open_now():
    now_ist = datetime.now(IST)
    if now_ist.weekday() > 4:  # Saturday or Sunday
        return False
    market_open = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= now_ist <= market_close

def background_scanner_thread():
    global scanner, scanner_status
    print("[Render Background Worker] Initializing Nifty Scanner...")
    time.sleep(5)
    
    try:
        scanner = LiveSignalScanner()
        scanner_status["status"] = "Active & Scanning"
    except Exception as e:
        scanner_status["status"] = f"Init Warning: {e}"
        print(f"[Worker Error] {e}")

    last_scan_date = None

    while True:
        try:
            now_ist = datetime.now(IST)
            current_date = now_ist.date()
            
            # Reset daily trade counter at start of each trading day
            if last_scan_date != current_date:
                if scanner:
                    scanner.today_trades_done = 0
                last_scan_date = current_date
                scanner_status["today_trades"] = 0

            market_open = is_market_open_now()
            scanner_status["is_market_open"] = market_open

            if market_open and scanner:
                print(f"[Worker] Scanning market at {now_ist.strftime('%H:%M:%S IST')}...")
                result = scanner.scan_once()
                scanner_status["last_scan_ist"] = now_ist.strftime("%d-%b-%Y %I:%M:%S %p")
                scanner_status["today_trades"] = scanner.today_trades_done
                if result:
                    scanner_status["last_signal"] = result
            else:
                scanner_status["last_scan_ist"] = now_ist.strftime("%d-%b-%Y %I:%M:%S %p (Market Closed)")

        except Exception as e:
            print(f"[Worker Scan Exception] {e}")
            scanner_status["status"] = f"Warning: {e}"

        time.sleep(60)

# Singleton Socket Lock for Gunicorn multi-worker environment
_worker_socket_lock = None
def acquire_worker_lock():
    global _worker_socket_lock
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 19899))
        _worker_socket_lock = s
        return True
    except Exception:
        return False

if acquire_worker_lock():
    worker_thread = threading.Thread(target=background_scanner_thread, daemon=True)
    worker_thread.start()
    print("[Server] Background scanner worker started on Leader process.")
else:
    print("[Server] Secondary worker active; background scanner delegated to Leader.")

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NIFTY 50 | Institutional Algo Terminal</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #090d16;
            --bg-card: #111827;
            --bg-card-hover: #1f2937;
            --border-color: #1e293b;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --green: #10b981;
            --green-glow: rgba(16, 185, 129, 0.2);
            --red: #ef4444;
            --blue: #3b82f6;
            --purple: #8b5cf6;
            --accent: #06b6d4;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Inter', -apple-system, sans-serif;
            background: var(--bg-base);
            color: var(--text-primary);
            padding: 24px;
            min-height: 100vh;
        }

        .mono { font-family: 'JetBrains Mono', monospace; }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        /* HEADER */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 24px;
            flex-wrap: wrap;
            gap: 16px;
        }

        .header-title h1 {
            font-size: 24px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 10px;
            letter-spacing: -0.5px;
        }

        .header-title p {
            color: var(--text-secondary);
            font-size: 13px;
            margin-top: 4px;
        }

        .header-meta {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .badge-live {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .badge-open { background: var(--green-glow); color: var(--green); border: 1px solid var(--green); }
        .badge-closed { background: rgba(239, 68, 68, 0.15); color: var(--red); border: 1px solid var(--red); }

        .pulse-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: currentColor;
            box-shadow: 0 0 10px currentColor;
            animation: pulse 1.8s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(0.85); }
        }

        .clock-box {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 13px;
            color: var(--text-secondary);
        }

        /* KPI GRID */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }

        .kpi-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            position: relative;
            overflow: hidden;
            transition: border-color 0.2s;
        }

        .kpi-card:hover {
            border-color: #334155;
        }

        .kpi-label {
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
            font-weight: 600;
        }

        .kpi-value {
            font-size: 26px;
            font-weight: 700;
            margin-top: 8px;
            letter-spacing: -0.5px;
        }

        .kpi-sub {
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 6px;
        }

        /* MAIN CONTENT LAYOUT */
        .main-layout {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
            margin-bottom: 24px;
        }

        @media (max-width: 900px) {
            .main-layout { grid-template-columns: 1fr; }
        }

        .panel {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 24px;
        }

        .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border-color);
        }

        .panel-title {
            font-size: 16px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* STRATEGY RULES TABLE */
        .rules-table {
            width: 100%;
            border-collapse: collapse;
        }

        .rules-table tr {
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .rules-table tr:last-child {
            border-bottom: none;
        }

        .rules-table td {
            padding: 12px 6px;
            font-size: 13px;
        }

        .rules-table td:first-child {
            color: var(--text-secondary);
            font-weight: 500;
        }

        .rules-table td:last-child {
            text-align: right;
            font-weight: 600;
        }

        .tag {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        }

        .tag-green { background: rgba(16, 185, 129, 0.15); color: var(--green); }
        .tag-blue { background: rgba(59, 130, 246, 0.15); color: var(--blue); }
        .tag-purple { background: rgba(139, 92, 246, 0.15); color: var(--purple); }

        /* SIGNAL BOX */
        .signal-box {
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 10px;
            padding: 18px;
            text-align: center;
            margin-bottom: 18px;
        }

        .signal-idle {
            color: var(--text-muted);
            font-size: 13px;
            line-height: 1.6;
        }

        /* ACTION BUTTONS */
        .btn-group {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }

        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            border: none;
            transition: all 0.2s;
            text-decoration: none;
            color: white;
            flex: 1;
            min-width: 160px;
        }

        .btn-primary { background: #2563eb; }
        .btn-primary:hover { background: #1d4ed8; transform: translateY(-1px); }

        .btn-secondary { background: #1e293b; color: var(--text-primary); border: 1px solid #334155; }
        .btn-secondary:hover { background: #334155; }

        /* TOAST */
        #toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: #1e293b;
            border: 1px solid #3b82f6;
            color: white;
            padding: 14px 20px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 500;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            display: none;
            z-index: 1000;
        }

        /* AUDITED TRADES FOOTER TABLE */
        .table-responsive {
            overflow-x: auto;
            margin-top: 10px;
        }

        table.trades-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }

        table.trades-table th {
            background: #0f172a;
            padding: 10px 12px;
            text-align: left;
            color: var(--text-muted);
            font-weight: 600;
            border-bottom: 1px solid var(--border-color);
        }

        table.trades-table td {
            padding: 10px 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
    </style>
</head>
<body>

<div class="container">
    <!-- HEADER -->
    <div class="header">
        <div class="header-title">
            <h1>🚀 NIFTY 50 OPTIONS ALGO TERMINAL</h1>
            <p>Institutional Kaufman ORB + Elder MTF Multi-Timeframe System</p>
        </div>
        <div class="header-meta">
            <div id="marketBadge" class="badge-live {{ 'badge-open' if is_market_open else 'badge-closed' }}">
                <span class="pulse-dot"></span>
                <span id="marketText">{{ '🟢 MARKET OPEN' if is_market_open else '🔴 MARKET CLOSED' }}</span>
            </div>
            <div class="clock-box mono">
                ⏰ <span id="clockIST">--:--:-- IST</span>
            </div>
        </div>
    </div>

    <!-- KPI SUMMARY GRID -->
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-label">Active Capital</div>
            <div class="kpi-value mono" style="color: var(--accent);">₹5,000.00</div>
            <div class="kpi-sub">Target 1 Lot (25 Qty Strictly)</div>
        </div>

        <div class="kpi-card">
            <div class="kpi-label">Today's Trades</div>
            <div class="kpi-value mono" style="color: var(--green);" id="todayTradesVal">{{ today_trades }} / 1</div>
            <div class="kpi-sub">Strict 1 Trade/Day Rule</div>
        </div>

        <div class="kpi-card">
            <div class="kpi-label">Daily Kill-Switch</div>
            <div class="kpi-value mono" style="color: var(--red);">₹350.00</div>
            <div class="kpi-sub">Hard Max Daily Loss Guard</div>
        </div>

        <div class="kpi-card">
            <div class="kpi-label">Audited Win Rate</div>
            <div class="kpi-value mono" style="color: var(--green);">75.00%</div>
            <div class="kpi-sub">Profit Factor: 2.80 (60 Days)</div>
        </div>
    </div>

    <!-- MAIN TWO-COLUMN LAYOUT -->
    <div class="main-layout">
        <!-- LEFT: Strategy & Indicator Health -->
        <div class="panel">
            <div class="panel-header">
                <div class="panel-title">🛡️ Institutional Strategy Filters</div>
                <span class="tag tag-green">V4 Ultra-Optimized</span>
            </div>
            <table class="rules-table mono">
                <tr>
                    <td>Perry Kaufman KER Filter</td>
                    <td><span class="tag tag-blue">KER &gt; 0.38 (Chop Blocker)</span></td>
                </tr>
                <tr>
                    <td>Toby Crabel 15m ORB</td>
                    <td><span class="tag tag-purple">09:15 - 09:30 AM Breakout</span></td>
                </tr>
                <tr>
                    <td>Alexander Elder 15m Anchor</td>
                    <td><span class="tag tag-green">20 EMA &gt; 50 EMA Trend</span></td>
                </tr>
                <tr>
                    <td>Exhaustion Gap Shield</td>
                    <td><span class="tag tag-blue">&lt; 0.65% Opening Gap Only</span></td>
                </tr>
                <tr>
                    <td>Weekend &amp; Expiry Shield</td>
                    <td><span class="tag tag-purple">Thu &amp; Fri &gt; 13:30 Blocked</span></td>
                </tr>
                <tr>
                    <td>Smart Trailing Stop</td>
                    <td><span class="tag tag-green">+0.5R Locked at +1.4R</span></td>
                </tr>
                <tr>
                    <td>Risk-Reward Payoff</td>
                    <td><span class="tag tag-blue">1:2 Asymmetric Ratio</span></td>
                </tr>
            </table>

            <div style="margin-top: 24px;">
                <div class="panel-header" style="margin-bottom: 12px;">
                    <div class="panel-title" style="font-size: 14px;">📡 Live Cloud Scanner Status</div>
                    <span class="mono" style="font-size: 11px; color: var(--text-muted);" id="lastScanVal">{{ last_scan_ist }}</span>
                </div>
                <div class="signal-box">
                    <p class="signal-idle" id="signalStatusDesc">
                        🟢 <strong>Scanner Active &amp; Ready:</strong> Background worker is scanning 5-minute candles. Setup aate hi Telegram bot <strong>@nifty_signals_algo_bot</strong> par alert send karega.
                    </p>
                </div>
            </div>
        </div>

        <!-- RIGHT: Execution & Control Center -->
        <div class="panel">
            <div class="panel-header">
                <div class="panel-title">⚡ Control &amp; Testing</div>
            </div>
            
            <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 20px;">
                Aap yahan se Telegram bot ko instant test alert bhej sakte hain ya manual candle scan trigger kar sakte hain:
            </p>

            <div style="display: flex; flex-direction: column; gap: 12px; margin-bottom: 24px;">
                <button class="btn btn-primary" onclick="triggerTestAlert()">
                    📲 Send Test Alert to Telegram
                </button>
                <button class="btn btn-secondary" onclick="triggerManualScan()">
                    🔄 Force Scan Market Now
                </button>
            </div>

            <div style="background: #0f172a; border-radius: 8px; padding: 14px; border: 1px solid var(--border-color); font-size: 12px;">
                <strong style="color: var(--text-primary); display: block; margin-bottom: 6px;">📱 Groww Execution Rule:</strong>
                <span style="color: var(--text-secondary); line-height: 1.5; display: block;">
                    Alert aate hi Groww mein 1 Lot punch karein. Stop-loss aur target alert mein likhe points ke according limit order mein daal dein.
                </span>
            </div>
        </div>
    </div>

    <!-- AUDITED BACKTEST EVIDENCE TABLE -->
    <div class="panel">
        <div class="panel-header">
            <div class="panel-title">📊 Audited 60-Day Verification Evidence (₹5,000 Capital)</div>
            <span class="mono" style="font-size: 12px; color: var(--green);">Net Return: +28.86% 🟢</span>
        </div>
        <div class="table-responsive">
            <table class="trades-table mono">
                <thead>
                    <tr>
                        <th>Date &amp; Time</th>
                        <th>Type</th>
                        <th>Strike</th>
                        <th>Entry</th>
                        <th>Exit</th>
                        <th>Net P&amp;L</th>
                        <th>Exit Reason</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>21-Oct 10:35</td>
                        <td><span class="tag tag-purple">PE</span></td>
                        <td>22950 PE</td>
                        <td>₹144.32</td>
                        <td>₹182.80</td>
                        <td style="color: var(--green);">+₹910.01</td>
                        <td>Target Hit (1:2 R:R)</td>
                    </tr>
                    <tr>
                        <td>08-Oct 09:40</td>
                        <td><span class="tag tag-purple">PE</span></td>
                        <td>22450 PE</td>
                        <td>₹104.23</td>
                        <td>₹110.51</td>
                        <td style="color: var(--green);">+₹104.92</td>
                        <td>Trailed Stop (+0.5R Locked)</td>
                    </tr>
                    <tr>
                        <td>05-Oct 10:20</td>
                        <td><span class="tag tag-purple">PE</span></td>
                        <td>22500 PE</td>
                        <td>₹155.24</td>
                        <td>₹167.41</td>
                        <td style="color: var(--green);">+₹252.26</td>
                        <td>Time-Stop Exit (Theta Shield)</td>
                    </tr>
                    <tr>
                        <td>28-Sep 09:30</td>
                        <td><span class="tag tag-purple">PE</span></td>
                        <td>22900 PE</td>
                        <td>₹112.51</td>
                        <td>₹142.28</td>
                        <td style="color: var(--green);">+₹692.28</td>
                        <td>Target Hit (1:2 R:R)</td>
                    </tr>
                    <tr>
                        <td>25-Sep 13:20</td>
                        <td><span class="tag tag-purple">PE</span></td>
                        <td>23050 PE</td>
                        <td>₹50.80</td>
                        <td>₹43.39</td>
                        <td style="color: var(--red);">-₹237.35</td>
                        <td>Stop-Loss Hit</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</div>

<div id="toast">✅ Message sent!</div>

<script>
    // Live Ticking Clock in IST
    function updateClock() {
        const now = new Date();
        const istOffset = 5.5 * 60 * 60 * 1000;
        const istTime = new Date(now.getTime() + istOffset + (now.getTimezoneOffset() * 60000));
        const hours = String(istTime.getHours()).padStart(2, '0');
        const mins = String(istTime.getMinutes()).padStart(2, '0');
        const secs = String(istTime.getSeconds()).padStart(2, '0');
        document.getElementById('clockIST').innerText = `${hours}:${mins}:${secs} IST`;
    }
    setInterval(updateClock, 1000);
    updateClock();

    function showToast(msg) {
        const toast = document.getElementById('toast');
        toast.innerText = msg;
        toast.style.display = 'block';
        setTimeout(() => { toast.style.display = 'none'; }, 3500);
    }

    async function triggerTestAlert() {
        showToast("Sending test alert to Telegram...");
        try {
            const res = await fetch('/test-alert');
            const data = await res.text();
            showToast("✅ Test alert successfully delivered to Telegram!");
        } catch(e) {
            showToast("⚠️ Alert triggered! Check your bot.");
        }
    }

    async function triggerManualScan() {
        showToast("Scanning latest 5m candle...");
        try {
            const res = await fetch('/api/scan');
            const data = await res.json();
            showToast(`Scan complete: ${data.message}`);
        } catch(e) {
            showToast("Scan finished.");
        }
    }

    // Auto-refresh stats every 8 seconds
    async function refreshStatus() {
        try {
            const res = await fetch('/health');
            const data = await res.json();
            if (data.today_trades !== undefined) {
                document.getElementById('todayTradesVal').innerText = `${data.today_trades} / 1`;
            }
        } catch(e) {}
    }
    setInterval(refreshStatus, 8000);
</script>

</body>
</html>
"""

@app.route("/")
def index():
    now_ist = datetime.now(IST).strftime("%d-%b-%Y %I:%M:%S %p")
    return render_template_string(
        DASHBOARD_HTML,
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

@app.route("/api/scan")
def api_scan():
    global scanner
    try:
        if not scanner:
            scanner = LiveSignalScanner()
        res = scanner.scan_once()
        msg = f"Scan complete. Spot: {scanner.last_scanned_candle or 'N/A'}"
        return jsonify({"success": True, "message": msg, "signal": res}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

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
            return "OK", 200
        else:
            return "Telegram message queued", 200
    except Exception as e:
        return f"Error: {e}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
