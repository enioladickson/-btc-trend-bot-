import time
import requests
import pandas as pd
from datetime import datetime
from flask import Flask

# ===== FLASK KEEP-ALIVE =====
app = Flask(__name__)

@app.route("/")
def home():
    return "BTC Trend Bot Running"

# ===== TELEGRAM SETTINGS =====
TOKEN = "8577248179:AAGUfZveD2pOD6SXGh3VO_MZ8ufcGf__ktg"
CHAT_ID = 5318907020

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": msg}
        requests.post(url, data=data)
    except:
        pass

# ===== BYBIT PRICE =====
def get_btc_price():
    try:
        url = "https://api.bybit.com/v5/market/tickers"
        params = {"category": "linear", "symbol": "BTCUSDT"}

        r = requests.get(url, params=params, timeout=10)
        print("PRICE RESPONSE:", r.text)  # DEBUG LOG

        data = r.json()

        return float(data["result"]["list"][0]["lastPrice"])

    except Exception as e:
        print("PRICE ERROR:", e)
        return None

# ===== BYBIT CANDLES =====
def get_klines(interval="5", limit=200):
    try:
        url = "https://api.bybit.com/v5/market/kline"
        params = {"category": "linear", "symbol": "BTCUSDT", "interval": interval, "limit": limit}

        r = requests.get(url, params=params, timeout=10)
        print("KLINE RESPONSE:", r.text)  # DEBUG LOG

        data = r.json()

        candles = data["result"]["list"]
        closes = [float(c[4]) for c in candles]  # closing price index = 4

        return pd.Series(closes)

    except Exception as e:
        print("KLINE ERROR:", e)
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

# ===== SUMMARY & TELEGRAM MESSAGE =====
def compute_summary(name, interval_code):
    data = get_klines(interval_code)
    price = get_btc_price()

    if data is None or price is None:
        send_telegram("⚠️ Market data unavailable")
        return

    rsi = RSI(data).iloc[-1]
    macd_val, signal_val = MACD(data)
    macd_val = macd_val.iloc[-1]
    signal_val = signal_val.iloc[-1]

    # Signal decision
    trend_up = macd_val > signal_val

    entry = round(price, 2)

    if trend_up:
        signal_text = "BUY 📉"
        stop_loss = round(entry * 0.98, 2)
        take_profit = round(entry * 1.02, 2)
    else:
        signal_text = "SELL 📈"
        stop_loss = round(entry * 1.02, 2)
        take_profit = round(entry * 0.98, 2)

    trend_strength = int(abs(macd_val - signal_val) / entry * 100000)

    # Velocity
    try:
        last_move = abs(data.pct_change().iloc[-1])
        if last_move > 0.01:
            velocity = "High ⬆️"
        elif last_move > 0.005:
            velocity = "Medium ⚖️"
        else:
            velocity = "Low ⬇️"
    except:
        velocity = "Low ⬇️"

    # Next prediction forecast
    next_buy = (round(entry * 0.995, 2), round(entry * 1.015, 2))
    next_sell = (round(entry * 0.985, 2), round(entry * 1.005, 2))

    msg = (
        f"⏱ {name} SUMMARY — BTCUSDT📊\n"
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

# ===== STARTUP MESSAGE =====
send_telegram("🚀 DicksonBTC Trend Bot Started! Watching BTCUSDT...")

# ===== BACKGROUND LOOP =====
def run_bot():
    while True:
        try:
            now = datetime.utcnow()
            minute = now.minute

            if minute % 5 == 0:
                compute_summary("5M", "5")

            if minute % 15 == 0:
                compute_summary("15M", "15")

            if minute == 0:
                compute_summary("1H", "60")

            time.sleep(60)

        except Exception as e:
            send_telegram(f"⚠️ Bot error: {e}")
            time.sleep(10)

# ===== RUN BOTH FLASK + BOT =====
import threading
threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
