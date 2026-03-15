import time
import requests

# YOUR TELEGRAM DETAILS
TOKEN = "8577248179:AAGUfZveD2pOD6SXGh3VO_MZ8ufcGf__ktg"
CHAT_ID = 5318907020   # Your personal Telegram chat ID

# Send Telegram alert
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, data=data)
    except:
        pass

# Get price from Binance
def get_price(symbol):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    try:
        return float(requests.get(url).json()["price"])
    except:
        return None

send_telegram("🚀 Bot is LIVE on Render! Tracking BTC + GOLD.")

while True:
    btc = get_price("BTCUSDT")
    gold = get_price("XAUUSDT")  # GOLD price

    if btc:
        send_telegram(f"💠 BTC Price Update: ${btc}")

    if gold:
        send_telegram(f"🟡 GOLD Price Update: ${gold}")

    time.sleep(30)  # Runs every 30 seconds
