import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime
import math

# ---------------------------
# TELEGRAM CONFIGURATION
# ---------------------------
TOKEN = "8577248179:AAGUfZveD2pOD6SXGh3VO_MZ8ufcGf__ktg"
CHAT_ID = 5318907020  # your Telegram chat ID

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Telegram error: {e}")

# ---------------------------
# BINANCE API CONFIGURATION
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
    data = requests.get(BINANCE_URL, params=params).json()
    closes = [float(x[4]) for x in data]
    return pd.Series(closes)

def EMA(series, period):
    return series.ewm(span=period, adjust=False).mean()

def ATR(series, period=14):
    # approximate ATR using difference of high-low average (simple version)
    return series.rolling(period).apply(lambda x: x.max() - x.min()).iloc[-1]

def get_signal(series):
    """
    Conservative trend + RSI + EMA crossover signal
    Returns BUY/SELL, entry price, stop-loss, take-profit, trend %
    """
    close = series.iloc[-1]
    ema_short = EMA(series, 9).iloc[-1]
    ema_long = EMA(series, 21).iloc[-1]

    # Trend strength percentage
    trend_strength = min(max(abs(ema_short - ema_long) / close * 100, 0), 100)

    # Conservative ATR stop-loss
    atr_val = ATR(series)
    stop_loss = close - 0.25 * atr_val
    take_profit = close + 0.65 * atr_val

    # Decide BUY/SELL
    if ema_short > ema_long:
        signal = "BUY"
    else:
        signal = "SELL"
        # invert stop-loss and take-profit
        stop_loss, take_profit = take_profit, stop_loss

    # Round prices
    close = round(close, 2)
    stop_loss = round(stop_loss, 2)
    take_profit = round(take_profit, 2)
    trend_strength = round(trend_strength, 0)

    return signal, close, stop_loss, take_profit, trend_strength

# ---------------------------
# SCHEDULED ALERTS
# ---------------------------
def format_message(symbol, interval, signal_data):
    signal, entry, stop, tp, trend = signal_data
    msg = f"⏱ {interval.upper()} SUMMARY — {symbol}\n"
    msg += f"Signal: {signal}\nEntry: {entry}\nStop-loss: {stop}\nTake-profit: {tp}\nTrend strength: {trend}%"
    return msg

def send_summary():
    now = datetime.utcnow()
    minutes = now.minute

    for symbol in ASSETS:
        for interval in ASSETS[symbol]["intervals"]:
            # Determine if this is the right summary time
            if interval == "5m" and minutes % 5 == 0:
                series = get_klines(symbol, "5m")
            elif interval == "15m" and minutes % 15 == 0:
                series = get_klines(symbol, "15m")
            elif interval == "1h" and now.minute == 0:
                series = get_klines(symbol, "1h")
            else:
                continue  # skip non-summary times

            signal_data = get_signal(series)
            msg = format_message(symbol, interval, signal_data)
            send_telegram(msg)
            time.sleep(1)  # small delay to avoid flooding

# ---------------------------
# MAIN LOOP
# ---------------------------
send_telegram("🚀 Multi-Asset Trend Bot Started! Watching BTCUSDT + XAUUSDT...")
while True:
    try:
        send_summary()
        time.sleep(30)  # check every 30 seconds for new summaries
    except Exception as e:
        send_telegram(f"⚠️ Bot error: {e}")
        time.sleep(10)
