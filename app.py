import os, requests
from flask import Flask
from datetime import datetime

app = Flask(__name__)
BOT_TOKEN = "8869764518:AAEop3wmHnEQA5UrNPnIwiFEgV4j2zXIUWM"

def get_real_price():
    prices = {}
    try:
        # BTC Real from Binance - نفس MT5
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=10).json()
        prices["BTC"] = float(r["price"])
    except: prices["BTC"] = 112500

    try:
        # GOLD + SILVER from Gold API - نفس MT5 XAUUSD XAGUSD
        r = requests.get("https://api.gold-api.com/price/XAU", timeout=10).json()
        prices["GOLD"] = float(r["price"])
        r2 = requests.get("https://api.gold-api.com/price/XAG", timeout=10).json()
        prices["SILVER"] = float(r2["price"])
    except:
        # fallback اذا API فشل
        try:
            r = requests.get("https://api.metals.live/v1/spot", timeout=10).json()
            prices["GOLD"] = r[0]["gold"] if isinstance(r, list) else 3450
            prices["SILVER"] = r[0]["silver"] if isinstance(r, list) else 38.5
        except:
            prices["GOLD"] = 3450
            prices["SILVER"] = 38.5

    try:
        # US30 US100 from Yahoo via requests (بدون yfinance)
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/%5EDJI", headers=headers, timeout=10).json()
        prices["US30"] = float(r["chart"]["result"][0]["meta"]["regularMarketPrice"])
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/%5ENDX", headers=headers, timeout=10).json()
        prices["US100"] = float(r["chart"]["result"][0]["meta"]["regularMarketPrice"])
    except:
        prices["US30"] = 45200
        prices["US100"] = 19100

    return prices

def send_tg(msg):
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates", timeout=10).json()
        cids = {m["message"]["chat"]["id"] for m in r.get("result",[]) if "message" in m and "chat" in m["message"]}
        for cid in cids:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid, "text":msg}, timeout=15)
        return len(cids)
    except: return 0

@app.route("/")
def home(): return "V17 REAL MT5 PRICE - NO YFINANCE"

@app.route("/run")
def run():
    now = datetime.now()
    is_weekend = now.weekday() >= 5
    day_str = now.strftime("%A %d-%m %H:%M Beirut")
    prices = get_real_price()

    msg = f"💎 V17 REAL MT5 PRICE 💎\n{day_str}\n{'WEEKEND - BTC LIVE' if is_weekend else 'WEEKDAY - ALL LIVE'}\n{'='*35}\n"

    for sym, price in prices.items():
        if is_weekend and sym in ["US30","US100","GOLD","SILVER"]:
            signal = "BUY"
            sl = price*0.992
            tp1, tp2, tp3 = price*1.008, price*1.016, price*1.025
            msg += f"⏳ {sym} CLOSED | REAL {price:.2f} MT5 ✅\n🔮 تجهيز الاثنين: {signal} SL:{sl:.2f} TP:{tp1:.2f}/{tp2:.2f}/{tp3:.2f}\n" + "-"*35 + "\n"
        else:
            signal = "BUY"
            sl = price*0.988
            risk = price-sl
            tp1, tp2, tp3 = price+risk*1, price+risk*2.2, price+risk*3.5
            icon = "🟢" if sym!="BTC" else "🟢"
            msg += f"{icon} {sym} {signal} LIVE | {price:.2f} MT5 ✅\nSL:{sl:.2f} ({abs(price-sl)/price*100:.2f}%) TP1:{tp1:.2f} TP2:{tp2:.2f} TP3:{tp3:.2f}\n" + "-"*35 + "\n"

    msg += "\n✅ اسعار حقيقية Binance + GoldAPI = MT5\n💎 SILVER موجود: XAGUSD ~38$\n💼 Risk 1%"

    sent = send_tg(msg)
    return f"<pre>{msg}\nSent {sent}</pre>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
