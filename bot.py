import time
import requests
import pandas as pd
from datetime import datetime

# ===== TELEGRAM SETTINGS =====
TOKEN = "8577248179:AAGUfZveD2pOD6SXGh3VO_MZ8ufcGf__ktg"
CHAT_ID = 5318907020  # Your personal Telegram chat ID

# ===== FUNCTIONS =====
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, data=data)
    except:
        pass

def get_btc_price():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    return float(requests.get(url).json()["price"])

def get_klines(interval="5m", limit=200):
    url = f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval={interval}&limit={limit}"
    data = requests.get(url).json()
    closes = [float(i[4]) for i in data]
    return pd.Series(closes)

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

def compute_summary(interval_name, interval_code):
    data = get_klines(interval=interval_code)
    price = get_btc_price()
    rsi = RSI(data).iloc[-1]
    macd_val, signal_val = MACD(data)
    macd_val = macd_val.iloc[-1]
    signal_val = signal_val.iloc[-1]

    trend_up = macd_val > signal_val
    trend_down = macd_val < signal_val

    # Example stop-loss & take-profit logic
    entry = round(price, 2)
    if trend_up:
        stop_loss = round(entry * 0.98, 2)
        take_profit = round(entry * 1.02, 2)
        signal_text = "BUY 📉"
    else:
        stop_loss = round(entry * 1.02, 2)
        take_profit = round(entry * 0.98, 2)
        signal_text = "SELL 📈"

    # Trend strength example (0-100)
    trend_strength = int(abs(macd_val - signal_val) / price * 1000)

    # Velocity example
    velocity = "High ⬆️" if abs(data.pct_change().iloc[-1]) > 0.01 else "Medium ⚖️"

    # Next predicted price ranges (very simple forecast based on recent movement)
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

# ===== MAIN LOOP =====
send_telegram("🚀 DicksonBTC Trend Bot Started! Watching BTCUSDT...")

intervals = [
    ("5M", "5m"),
    ("15M", "15m"),
    ("1H", "1h")
]

while True:
    try:
        now = datetime.utcnow()
        minute = now.minute

        # 5M summary
        if minute % 5 == 0:
            compute_summary("5M", "5m")

        # 15M summary
        if minute % 15 == 0:
            compute_summary("15M", "15m")

        # 1H summary
        if minute == 0:
            compute_summary("1H", "1h")

        time.sleep(60)

    except Exception as e:
        send_telegram(f"⚠️ Bot error: {e}")
        time.sleep(10)
