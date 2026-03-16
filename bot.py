import time
import threading
import requests
import pandas as pd
from datetime import datetime
from flask import Flask

# ==============================
# 🔐 TELEGRAM SETTINGS
# ==============================
TOKEN = "8577248179:AAGUfZveD2pOD6SXGh3VO_MZ8ufcGf__ktg"
CHAT_ID = 5318907020

# ==============================
# 📡 FLASK APP (to keep Render alive)
# ==============================
app = Flask(__name__)

@app.route("/")
def home():
    return "Dickson BTC Trend Bot Running 🔥"


# ==============================
# 📤 TELEGRAM SENDER
# ==============================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print("Telegram error:", e)


# ==============================
# 📊 MARKET DATA FUNCTIONS
# ==============================
def get_btc_price():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    return float(requests.get(url).json()["price"])


def get_klines(interval="5m", limit=200):
    url = f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval={interval}&limit={limit}"
    data = requests.get(url).json()

    # Fix for: "string index out of range"
    if not isinstance(data, list) or len(data) < 50:
        raise Exception("Invalid Binance data returned")

    closes = [float(i[4]) for i in data]
    return pd.Series(closes)


# ==============================
# 📈 INDICATORS
# ==============================
def RSI(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
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


# ==============================
# 📝 SUMMARY BUILDER
# ==============================
def compute_summary(label, interval):
    data = get_klines(interval)
    price = get_btc_price()

    rsi_val = RSI(data).iloc[-1]
    macd_val, signal_val = MACD(data)
    macd_val = macd_val.iloc[-1]
    signal_val = signal_val.iloc[-1]

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

    trend_strength = round(abs(macd_val - signal_val) * 100, 2)

    last_move = abs(data.pct_change().iloc[-1])
    if last_move > 0.01:
        velocity = "High ⬆️"
    elif last_move > 0.005:
        velocity = "Medium ⚖️"
    else:
        velocity = "Low ⬇️"

    # Next prediction (simple volatility-based forecast)
    next_buy = (round(entry * 0.995, 2), round(entry * 1.015, 2))
    next_sell = (round(entry * 0.985, 2), round(entry * 1.005, 2))

    msg = (
        f"⏱ {label} SUMMARY — BTCUSDT 📊\n\n"
        f"💹 Signal: {signal_text}\n"
        f"📧 Entry: {entry}\n"
        f"⚠️ Stop-loss: {stop_loss}\n"
        f"✅ Take-profit: {take_profit}\n"
        f"⚕️ Trend strength: {trend_strength}%\n"
        f"♻️ Velocity: {velocity}\n\n"
        f"🚀 Next prediction:\n"
        f"BUY range: {next_buy[0]} → {next_buy[1]}\n"
        f"SELL range: {next_sell[0]} → {next_sell[1]}"
    )

    send_telegram(msg)


# ==============================
# 🔁 BOT LOOP (RUNS IN BACKGROUND)
# ==============================
def bot_loop():
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


# ==============================
# 🚀 START BOT THREAD + FLASK SERVER
# ==============================
if __name__ == "__main__":
    t = threading.Thread(target=bot_loop)
    t.daemon = True
    t.start()

    app.run(host="0.0.0.0", port=10000)
