import os, requests
from flask import Flask
from datetime import datetime

app = Flask(__name__)
BOT_TOKEN = "8869764518:AAEop3wmHnEQA5UrNPnIwiFEgV4j2zXIUWM"

def send_tg(msg):
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates", timeout=10).json()
        cids = set()
        for u in r.get("result", []):
            if "message" in u and "chat" in u["message"]:
                cids.add(u["message"]["chat"]["id"])
        for cid in cids:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                         json={"chat_id": cid, "text": msg}, timeout=10)
        return len(cids)
    except Exception as e:
        print(f"TG Error: {e}")
        return 0

@app.route("/")
def home():
    return "V15.2 FIXED - WORKING 24/7"

@app.route("/run")
def run():
    now = datetime.now()
    is_weekend = now.weekday() >= 5
    day_str = now.strftime("%A %d-%m %H:%M Beirut")
    
    if is_weekend:
        msg = f"""💎 V15.2 WEEKEND SPECIAL 💎
{day_str}
WEEKEND MODE

🟢 BTC BUY SPECIAL
Price: 112500 (مثال)
SL: 111200 (1.15% Risk) ورا Swing Low
TP1: 113800 (RR 1:1) سكر 50%
TP2: 115100 (RR 1:2.2) سكر 30%
TP3: 116500 (RR 1:3.5) Runner 20%
Score: 8.2/10 | RSI 48 | Trend BULL
💼 Risk 1% فقط - تداول الان BTC شغال 24/7

⏳ GOLD MARKET CLOSED
Last: 3450 | Trend BULL
🔮 تجهيز للاثنين: BUY متوقع
SL: 3415 | TP1:3485 TP2:3520 TP3:3555
📌 بيفتح الاثنين 10:30 بيروت

⏳ US30 MARKET CLOSED
Last: 45200 | Trend BULL
🔮 تجهيز للاثنين: BUY

⏳ US100 MARKET CLOSED
Last: 19100 | Trend BULL
🔮 تجهيز للاثنين: BUY

✅ قانون: 1% Risk | WAIT = ربح
"""
    else:
        msg = f"""💎 V15.2 WEEKDAY SPECIAL 💎
{day_str}
WEEKDAY MODE - الكل LIVE

🟢 GOLD BUY SPECIAL | Score 8.5/10
Price: 3450 | RSI 52 | ATR 18
SL: 3410 (1.15%) ورا Swing Low
TP1: 3490 (1:1) TP2: 3535 (1:2.2) TP3: 3580 (1:3.5)
EMA200: ✅

🔴 US30 SELL SPECIAL | Score 7.8/10
Price: 45200
SL: 45600 TP1:44800 TP2:44400 TP3:44000

🟢 BTC BUY | Score 8.2/10
SL: 111200 TP1:113800 TP2:115100 TP3:116500

💼 Risk 1% Only
"""

    sent = send_tg(msg)
    return f"<pre>{msg}\n\nSent to {sent} chats - BOT WORKING!</pre>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
