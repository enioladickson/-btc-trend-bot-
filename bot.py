# flask_bot_volatility.py
from flask import Flask
import threading
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime

# ---------------------------
# TELEGRAM CONFIG
# ---------------------------
TOKEN = "8577248179:AAGUfZveD2pOD6SXGh3VO_MZ8ufcGf__ktg"
CHAT_ID = 5318907020

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Telegram error: {e}")

# ---------------------------
# BINANCE CONFIG
# ---------------------------
BINANCE_URL = "https://api.binance.com/api/v3/klines"
ASSETS = {
    "BTCUSDT": {"intervals": ["5m", "15m", "1h"]},
    "XAUUSDT": {"intervals": ["5m", "15m", "1h"]},
}

# ---------------------------
# TECHNICAL INDICATORS
# ---------------------------
def get_klines(symbol, interval, limit=200):
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        response = requests.get(BINANCE_URL, params=params, timeout=10)
        data = response.json()
        if not data or len(data) < 2:
            print(f"⚠️ No data for {symbol} {interval}")
            return pd.Series([0])
        closes = [float(x[4]) for x in data]
        return pd.Series(closes)
    except Exception as e:
        print(f"⚠️ Klines error for {symbol} {interval}: {e}")
        return pd.Series([0])

def EMA(series, period):
    return series.ewm(span=period, adjust=False).mean()

def ATR(series, period=14):
    return series.rolling(period).apply(lambda x: x.max() - x.min()).iloc[-1]

def get_volatility_level(series):
    atr = ATR(series)
    if atr < series.std() * 0.5:
        return "Low", 0.2
    elif atr < series.std() * 1.2:
        return "Medium", 0.25
    else:
        return "High", 0.35

def get_signal(series):
    close = series.iloc[-1]
    ema_short = EMA(series, 9).iloc[-1]
    ema_long = EMA(series, 21).iloc[-1]
    trend_strength = min(max(abs(ema_short - ema_long)/close*100, 0), 100)
    
    volatility, factor = get_volatility_level(series)
    atr_val = ATR(series)
    
    stop_loss = close - factor*atr_val
    take_profit = close + factor*atr_val
    
    if ema_short > ema_long:
        signal = "BUY"
    else:
        signal = "SELL"
        stop_loss, take_profit = take_profit, stop_loss
    
    close = round(close,2)
    stop_loss = round(stop_loss,2)
    take_profit = round(take_profit,2)
    trend_strength = round(trend_strength,0)
    
    return signal, close, stop_loss, take_profit, trend_strength, volatility

def format_message(symbol, interval, signal_data):
    signal, entry, stop, tp, trend, volatility = signal_data
    msg = f"⏱ {interval.upper()} SUMMARY — {symbol}\n"
    msg += f"Signal: {signal}\nEntry: {entry}\nStop-loss: {stop}\nTake-profit: {tp}\n"
    msg += f"Trend strength: {trend}%\nVolatility: {volatility}"
    return msg

# ---------------------------
# MAIN LOOP
# ---------------------------
def main_loop():
    send_telegram("🚀 Multi-Asset Trend Bot Started! Watching BTCUSDT + XAUUSDT...")
    while True:
        now = datetime.utcnow()
        minutes = now.minute
        for symbol in ASSETS:
            for interval in ASSETS[symbol]["intervals"]:
                if interval=="5m" and minutes%5==0:
                    series = get_klines(symbol,"5m")
                elif interval=="15m" and minutes%15==0:
                    series = get_klines(symbol,"15m")
                elif interval=="1h" and now.minute==0:
                    series = get_klines(symbol,"1h")
                else:
                    continue
                signal_data = get_signal(series)
                msg = format_message(symbol, interval, signal_data)
                send_telegram(msg)
                time.sleep(1)
        time.sleep(30)

# ---------------------------
# FLASK SETUP FOR RENDER
# ---------------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "DicksonBTC Trend Bot with Volatility is running ✅"

threading.Thread(target=main_loop).start()

if __name__=="__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
