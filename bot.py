import time
import requests
import pandas as pd
from datetime import datetime
from flask import Flask
import threading, os

# ===== TELEGRAM SETTINGS =====
TOKEN = "8577248179:AAGUfZveD2pOD6SXGh3VO_MZ8ufcGf__ktg"
CHAT_ID = 5318907020

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, data=data)
    except:
        pass

# ===== SAFE BINANCE FUNCTIONS =====
def safe_get(url):
    """
    Prevent crashes from Binance rate limits / empty responses.
    """
    try:
        r = requests.get(url, timeout=5)
        return r.json()
    except:
        return None

def get_btc_price():
    data = safe_get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
    if data and "price" in data:
        return float(data["price"])
    return None

def get_klines(interval="5m", limit=200):
    url = f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval={interval}&limit={limit}"
    data = safe_get(url)

    # ❗ If data is not valid → return None
    if not isinstance(data, list) or len(data) == 0:
        return None

    try:
        closes = [float(i[4]) for i in data]
        return pd.Series(closes)
    except:
        return None

# ===== INDICATORS =====
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

# ===== SUMMARY FUNCTION (SAFE) =====
def compute_summary(interval_name, interval_code):

    price = get_btc_price()
    data = get_klines(interval_code)

    # ❗ If ANYTHING failed → skip interval silently
    if price is None or data is None:
        return

    rsi = RSI(data).iloc[-1]
    macd_val, signal_val = MACD(data)
    macd_val = macd_val.iloc[-1]
    signal_val = signal_val.iloc[-1]

    # Signal decision
    trend_up = macd_val > signal_val
    entry = round(price, 2)

    if trend_up:
        stop_loss = round(entry * 0.98, 2)
        take_profit = round(entry * 1.02, 2)
        signal_text = "BUY 📉"
    else:
        stop_loss = round(entry * 1.02, 2)
        take_profit = round(entry * 0.98, 2)
        signal_text = "SELL 📈"

    # Trend strength
    trend_strength = int(abs(macd_val - signal_val) / price * 1000)

    # Velocity
    velocity = "High ⬆️" if abs(data.pct_change().iloc[-1]) > 0.01 else "Medium ⚖️"

    # Next predicted ranges
    next_buy = (round(entry * 0.995, 2), round(entry * 1.015, 2))
    next_sell = (round(entry * 0.985, 2), round(entry * 1.005, 2))

    msg = f"⏱ {interval_name} SUMMARY — BTCUSDT📊\n" \
          f"💹 Signal: {signal_text}\n" \
          f"📧 Entry: {entry}\n" \
          f"⚠️ Stop-loss: {stop_loss}\n" \
          f"✅ Take-profit: {take_profit}\n" \
          f"⚕️ Trend strength: {trend_strength}%\n" \
          f"♻️ Velocity: {velocity}\n" \
          f"🚀 Next prediction:\n" \
          f"BUY: {next_buy[0]} → {next_buy[1]}\n" \
          f"SELL: {next_sell[0]} → {next_sell[1]}"

    send_telegram(msg)

# ===== MAIN BOT LOOP (BACKGROUND THREAD) =====
def start_bot():
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

        except Exception as e:
            send_telegram(f"⚠️ Bot internal error: {e}")

        time.sleep(60)

# ===== FLASK (FOR RENDER WEB SERVICE) =====
app = Flask(__name__)

@app.route("/")
def home():
    return "DicksonBTC Trend Bot is running! 🚀"

if __name__ == "__main__":
    threading.Thread(target=start_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
