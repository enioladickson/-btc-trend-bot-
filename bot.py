# bot.py
import threading, time, requests, pandas as pd, numpy as np
from datetime import datetime
from flask import Flask

# ---------------------------
# TELEGRAM CONFIG
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
# BINANCE CONFIG
# ---------------------------
BINANCE_URL = "https://api.binance.com/api/v3/klines"
ASSETS = {
    "BTCUSDT": ["5m", "15m", "1h"],
    "PAXGUSDT": ["5m", "15m", "1h"],  # Gold
}

# ---------------------------
# INDICATORS & SIGNALS
# ---------------------------
def get_klines(symbol, interval, limit=200):
    try:
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        data = requests.get(BINANCE_URL, params=params, timeout=10).json()
        if not data or len(data) < 2:
            return None
        closes = [float(x[4]) for x in data]
        return pd.Series(closes)
    except:
        return None

def EMA(series, period):
    return series.ewm(span=period, adjust=False).mean()

def ATR(series, period=14):
    return series.rolling(period).apply(lambda x: x.max()-x.min()).iloc[-1]

def get_volatility_level(series):
    atr_val = ATR(series)
    std_val = series.std()
    if atr_val < std_val*0.5: return "Low", 0.2, "⬇️"
    elif atr_val < std_val*1.2: return "Medium", 0.25, "⚖️"
    else: return "High", 0.35, "⬆️"

def get_signal(series):
    close = series.iloc[-1]
    ema_short = EMA(series,9).iloc[-1]
    ema_long = EMA(series,21).iloc[-1]
    trend_strength = min(max(abs(ema_short-ema_long)/close*100,0),100)
    
    volatility, factor, vel_icon = get_volatility_level(series)
    atr_val = ATR(series)
    
    stop_loss = close - factor*atr_val
    take_profit = close + factor*atr_val
    
    if ema_short > ema_long:
        signal = "BUY"
        pred_buy_low = close
        pred_buy_high = close + factor*atr_val
        pred_sell_low = close - factor*atr_val
        pred_sell_high = close
    else:
        signal = "SELL"
        stop_loss, take_profit = take_profit, stop_loss
        pred_buy_low = close
        pred_buy_high = close + factor*atr_val
        pred_sell_low = close - factor*atr_val
        pred_sell_high = close
    
    # round values
    close = round(close,2)
    stop_loss = round(stop_loss,2)
    take_profit = round(take_profit,2)
    trend_strength = round(trend_strength,0)
    pred_buy_low = round(pred_buy_low,2)
    pred_buy_high = round(pred_buy_high,2)
    pred_sell_low = round(pred_sell_low,2)
    pred_sell_high = round(pred_sell_high,2)
    
    return {
        "signal": signal, "entry": close, "stop_loss": stop_loss, "take_profit": take_profit,
        "trend_strength": trend_strength, "volatility": volatility, "vel_icon": vel_icon,
        "pred_buy_low": pred_buy_low, "pred_buy_high": pred_buy_high,
        "pred_sell_low": pred_sell_low, "pred_sell_high": pred_sell_high
    }

def format_message(symbol, interval, data):
    signal_emoji = "💹 Signal:\nBUY 📉" if data["signal"]=="BUY" else "💹 Signal:\nSELL 📈"
    msg = f"⏱ {interval.upper()} SUMMARY — {symbol}📊\n"
    msg += f"{signal_emoji}\n\n"
    msg += f"📧 Entry:\n{data['entry']}\n\n"
    msg += f"⚠️ Stop-loss:\n{data['stop_loss']}\n\n"
    msg += f"✅ Take-profit:\n{data['take_profit']}\n\n"
    msg += f"⚕️ Trend strength:\n{data['trend_strength']}%\n\n"
    msg += f"♻️ Velocity:\n{data['volatility']} {data['vel_icon']}\n\n"
    msg += f"🚀 Next prediction:\nBUY: {data['pred_buy_low']} → {data['pred_buy_high']}\nSELL: {data['pred_sell_low']} → {data['pred_sell_high']}"
    return msg

# ---------------------------
# MAIN LOOP
# ---------------------------
def main_loop():
    send_telegram("🚀 DicksonBTC Trend Bot Started! Watching BTC + Gold...")
    
    last_sent = {symbol:{interval:None for interval in ASSETS[symbol]} for symbol in ASSETS}
    
    while True:
        now = datetime.utcnow()
        minutes = now.minute
        for symbol in ASSETS:
            for interval in ASSETS[symbol]:
                if interval=="5m" and minutes%5!=0: continue
                if interval=="15m" and minutes%15!=0: continue
                if interval=="1h" and minutes!=0: continue
                
                current_key = f"{now.hour}-{minutes//int(interval[:-1])}"
                if last_sent[symbol][interval]==current_key: continue
                
                series = get_klines(symbol, interval)
                if series is None: continue
                
                signal_data = get_signal(series)
                msg = format_message(symbol, interval, signal_data)
                send_telegram(msg)
                
                last_sent[symbol][interval] = current_key
        
        time.sleep(10)

# ---------------------------
# FLASK SERVER FOR RENDER
# ---------------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "DicksonBTC Trend Bot is running ✅"

threading.Thread(target=main_loop).start()

if __name__=="__main__":
    import os
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=port)
