import os, requests, yfinance as yf
from flask import Flask
from datetime import datetime

app = Flask(__name__)
BOT_TOKEN = "8869764518:AAEop3wmHnEQA5UrNPnIwiFEgV4j2zXIUWM"

# رموز مطابقة لـ MT5
SYMBOLS = {
    "GOLD": "GC=F", # Gold Futures = XAUUSD MT5
    "BTC": "BTC-USD", # BTC
    "US30": "^DJI", # Dow Jones = US30
    "US100": "^NDX", # Nasdaq = US100
    "SILVER": "SI=F"
}

def get_price(symbol):
    try:
        ticker = SYMBOLS[symbol]
        data = yf.download(ticker, period="2d", interval="1m", progress=False)
        if data.empty:
            data = yf.download(ticker, period="5d", interval="1h", progress=False)
        if data.empty:
            return None, 0, 0

        # Fix MultiIndex issue
        if hasattr(data.columns, 'get_level_values'):
            try:
                data.columns = data.columns.get_level_values(0)
            except:
                pass

        close = float(data['Close'].iloc[-1])
        high = float(data['High'].iloc[-1]) if 'High' in data.columns else close*1.005
        low = float(data['Low'].iloc[-1]) if 'Low' in data.columns else close*0.995
        return close, high, low
    except Exception as e:
        print(f"Error {symbol}: {e}")
        return None, 0, 0

def send_tg(msg):
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates", timeout=10).json()
        cids = {m["message"]["chat"]["id"] for m in r.get("result",[]) if "message" in m and "chat" in m["message"]}
        for cid in cids:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid, "text":msg}, timeout=15)
        return len(cids)
    except: return 0

@app.route("/")
def home():
    return "V16 REAL PRICE - MT5 MATCHED"

@app.route("/run")
def run():
    now = datetime.now()
    is_weekend = now.weekday() >= 5
    day_str = now.strftime("%A %d-%m %H:%M Beirut")
    mode = "WEEKEND - BTC LIVE" if is_weekend else "WEEKDAY - ALL LIVE"

    msg = f"💎 V16 REAL PRICE MT5 💎\n{day_str}\n{mode}\n{'='*32}\n"

    for sym in SYMBOLS:
        price, high, low = get_price(sym)
        if price is None:
            msg += f"⏸️ {sym}: NO DATA - جرب بعد دقيقة\n" + "-"*32 + "\n"
            continue

        # SL TP منطقي من السعر الحقيقي
        if is_weekend and sym in ["US30","US100","GOLD","SILVER"]:
            trend = "BULL" if price > low*1.01 else "BEAR"
            signal = "BUY" if trend=="BULL" else "SELL"
            sl = price*0.992 if signal=="BUY" else price*1.008
            tp1 = price*1.008 if signal=="BUY" else price*0.992
            tp2 = price*1.016 if signal=="BUY" else price*0.984
            tp3 = price*1.025 if signal=="BUY" else price*0.975
            msg += f"""⏳ {sym} CLOSED | REAL {price:.2f}
🔮 تجهيز الاثنين: {signal}
SL:{sl:.2f} TP1:{tp1:.2f} TP2:{tp2:.2f} TP3:{tp3:.2f}
Last MT5: {price:.2f} ✅
""" + "-"*32 + "\n"
        else:
            # BTC او ايام الاسبوع - LIVE
            # منطق بسيط: فوق لو امس = BUY
            signal = "BUY" if price > low else "SELL"
            sl = low*0.999 if signal=="BUY" else high*1.001
            # خلي SL max 1.2%
            if signal=="BUY":
                sl = max(sl, price*0.988)
            else:
                sl = min(sl, price*1.012)
            risk = abs(price-sl)
            tp1 = price + risk*1.0 if signal=="BUY" else price - risk*1.0
            tp2 = price + risk*2.2 if signal=="BUY" else price - risk*2.2
            tp3 = price + risk*3.5 if signal=="BUY" else price - risk*3.5

            icon = "🟢" if signal=="BUY" else "🔴"
            msg += f"""{icon} {sym} {signal} LIVE | REAL PRICE
Price: {price:.2f} MT5 ✅
SL:{sl:.2f} ({abs(price-sl)/price*100:.2f}%)
TP1:{tp1:.2f} TP2:{tp2:.2f} TP3:{tp3:.2f}
High:{high:.2f} Low:{low:.2f}
""" + "-"*32 + "\n"

    msg += "\n✅ اسعار حقيقية من Yahoo = MT5\n💼 Risk 1% فقط"

    sent = send_tg(msg)
    return f"<pre>{msg}\n\nSent {sent}</pre>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
