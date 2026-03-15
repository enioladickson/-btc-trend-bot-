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

# Test message — will send immediately on deployment
send_telegram("✅ Test message: Bot is running on Render!")

# Keep the bot alive (dummy loop)
while True:
    time.sleep(60)
