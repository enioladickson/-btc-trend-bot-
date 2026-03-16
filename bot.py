import time
import requests
import pandas as pd
from datetime import datetime
from flask import Flask
import threading
import os

# ===== TELEGRAM SETTINGS =====
TOKEN = "8577248179:AAGUfZveD2pOD6SXGh3VO_MZ8ufcGf__ktg"
CHAT_ID = "5318907020"

# ===== FLASK APP =====
app = Flask(__name__)

@app.route("/")
def home():
    return "Dickson BTC Trend Bot Running!"

# ===== TELEGRAM SEND =====
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except:
        pass

# ===== GET BTC PRICE FROM BYBIT =====
def get_btc_price():
    try:
        url = "https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT"
        data = requests.get(url, timeout=5).json()
        price = float(data["result"]["list"][0]["lastPrice"])
        return price
    except:
        return None

# ===== GET KLINES FROM BYBIT =====
def get_klines(interval="5", limit=200):

    interval_map = {
        "5m": "5",
        "15m": "15",
        "1h": "60"
    }

    try:
        url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol=BTCUSDT&interval={interval_map[interval]}&limit={limit}"
        data = requests.get(url, timeout=5).json()

        candles = data["result"]["list"]

        closes = [float(c[4]) for c in candles]
        closes.reverse()

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

# ===== SUMMARY =====
def compute_summary(label, interval):

    data = get_klines(interval)

    if data is None or len(data) < 50:
        send_telegram("⚠️ Market data unavailable")
        return

    price = get_btc_price()

    if price is None:
        send_telegram("⚠️ Price fetch failed")
        return

    rsi = RSI(data).iloc[-1]
    macd_val, signal_val = MACD(data)
    macd_val = macd_val.iloc[-1]
    signal_val = signal_val.iloc[-1]

    entry = round(price,2)

    if macd_val > signal_val:
        signal_text = "BUY 📉"
        stop_loss = round(entry * 0.98,2)
        take_profit = round(entry * 1.02,2)
    else:
        signal_text = "SELL 📈"
        stop_loss = round(entry * 1.02,2)
        take_profit = round(entry * 0.98,2)

    trend_strength = round(abs(macd_val - signal_val) * 100,2)

    velocity = "High ⬆️" if abs(data.pct_change().iloc[-1]) > 0.01 else "Medium ⚖️"

    next_buy = (round(entry * 0.995,2), round(entry * 1.015,2))
    next_sell = (round(entry * 0.985,2), round(entry * 1.005,2))

    msg = f"""
⏱ {label} SUMMARY — BTCUSDT 📊

💹 Signal: {signal_text}
📧 Entry: {entry}

⚠️ Stop-loss: {stop_loss}
✅ Take-profit: {take_profit}

⚕️ Trend strength: {trend_strength}%
♻️ Velocity: {velocity}

🚀 Next prediction
BUY: {next_buy[0]} → {next_buy[1]}
SELL: {next_sell[0]} → {next_sell[1]}
"""

    send_telegram(msg)

# ===== BOT LOOP =====
def run_bot():

    send_telegram("🚀 DicksonBTC Trend Bot Started! Watching BTCUSDT...")

    while True:

        try:

            now = datetime.utcnow()
            minute = now.minute

            if minute % 5 == 0:
                compute_summary("5M","5m")

            if minute % 15 == 0:
                compute_summary("15M","15m")

            if minute == 0:
                compute_summary("1H","1h")

            time.sleep(60)

        except Exception as e:
            send_telegram(f"⚠️ Bot error: {e}")
            time.sleep(10)

# ===== START BOT THREAD =====
if __name__ == "__main__":

    threading.Thread(target=run_bot, daemon=True).start()

    port = int(os.environ.get("PORT",10000))

    app.run(host="0.0.0.0", port=port)
