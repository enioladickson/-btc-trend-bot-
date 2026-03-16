import time
import threading
import requests
import pandas as pd
from datetime import datetime
from flask import Flask

# ===== TELEGRAM SETTINGS =====
TOKEN = "8577248179:AAGUfZveD2pOD6SXGh3VO_MZ8ufcGf__ktg"
CHAT_ID = 5318907020

# ===== FLASK APP (required by Render Web Service) =====
app = Flask(__name__)

@app.route("/")
def home():
    return "Dickson BTC Trend Bot Running Successfully!"

# ===== TELEGRAM SEND =====
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, data=data)
    except:
        pass

# ===== Binance Mirror APIs (SAFE & NEVER BLOCKED) =====
def get_btc_price():
    urls = [
        "https://api.binance.us/api/v3/ticker/price?symbol=BTCUSDT",
        "https://data.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
    ]
    for u in urls:
        try:
            return float(requests.get(u, timeout=5).json()["price"])
        except:
            continue
    raise Exception("Price API failed")

def get_klines(interval="5m", limit=200):
    urls = [
        f"https://api.binance.us/api/v3/klines?symbol=BTCUSDT&interval={interval}&limit={limit}",
        f"https://data.binance.com/api/v3/klines?symbol=BTCUSDT&interval={interval}&limit={limit}",
    ]
    for u in urls:
        try:
            data = requests.get(u, timeout=5).json()
            if isinstance(data, list) and len(data) > 20:
                closes = [float(i[4]) for i in data]
                return pd.Series(closes)
        except:
            continue
    raise Exception("Invalid Binance data returned")

# ===== INDICATOR FUNCTIONS =====
def RSI(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def MACD(series):
    ema12 = series.ewm(span=12).mean()
    ema26 = series.ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    return macd, signal

# ===== SUMMARY BUILDER =====
def compute_summary(interval_name, interval_code):
    data = get_klines(interval=interval_code)
    price = get_btc_price()

    rsi = RSI(data).iloc[-1]
    macd_val, signal_val = MACD(data)
    macd_val = macd_val.iloc[-1]
    signal_val = signal_val.iloc[-1]

    trend_up = macd_val > signal_val
    trend_down = macd_val < signal_val

    entry = round(price, 2)

    # ===== STOP LOSS & TAKE PROFIT =====
    if trend_up:
        stop_loss = round(entry * 0.98, 2)
        take_profit = round(entry * 1.02, 2)
        signal_text = "BUY 📉"
    else:
        stop_loss = round(entry * 1.02, 2)
        take_profit = round(entry * 0.98, 2)
        signal_text = "SELL 📈"

    # ===== TREND STRENGTH =====
    trend_strength = int(abs(macd_val - signal_val) / price * 1000)

    # ===== VELOCITY =====
    pct = abs(data.pct_change().iloc[-1])
    if pct > 0.015:
        velocity = "High ⬆️"
    elif pct > 0.007:
        velocity = "Medium ⚖️"
    else:
        velocity = "Low ⬇️"

    # ===== NEXT PREDICTIONS =====
    next_buy = (round(entry * 0.995, 2), round(entry * 1.015, 2))
    next_sell = (round(entry * 0.985, 2), round(entry * 1.005, 2))

    # ===== BUILD MESSAGE =====
    msg = (
        f"⏱ {interval_name} SUMMARY — BTCUSDT📊\n"
        f"💹 Signal: {signal_text}\n"
        f"📧 Entry: {entry}\n"
        f"⚠️ Stop-loss: {stop_loss}\n"
        f"✅ Take-profit: {take_profit}\n"
        f"⚕️ Trend strength: {trend_strength}%\n"
        f"♻️ Velocity: {velocity}\n"
        f"🚀 Next prediction:\n"
        f"BUY: {next_buy[0]} → {next_buy[1]}\n"
        f"SELL: {next_sell[0]} → {next_sell[1]}"
    )

    send_telegram(msg)

# ===== BOT LOOP (RUNS IN BACKGROUND THREAD) =====
def run_bot():
    send_telegram("🚀 DicksonBTC Trend Bot Started! Watching BTCUSDT...")

    while True:
        try:
            now = datetime.utcnow()
            minute = now.minute

            if minute % 5 == 0:
                compute_summary("5M", "5m")

            if minute % 15 == 0:
                compute_summary("15M", "15m")

            if minute == 0:
                compute_summary("1H", "1h")

            time.sleep(60)

        except Exception as e:
            send_telegram(f"⚠️ Bot error: {e}")
            time.sleep(10)

# Start background bot thread
threading.Thread(target=run_bot, daemon=True).start()

# Run Flask
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
