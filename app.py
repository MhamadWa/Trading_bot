import os, requests, pandas as pd
from flask import Flask
from datetime import datetime
import yfinance as yf

app = Flask(__name__)
BOT_TOKEN = "8869764518:AAEop3wmHnEQA5UrNPnIwiFEgV4j2zXIUWM"
SYMBOLS = {"GOLD":"GC=F", "BTC":"BTC-USD", "US30":"^DJI", "US100":"^NDX", "SILVER":"SI=F"}

def get_df(ticker):
    try:
        df = yf.download(ticker, period="1y", interval="1h", progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        return df
    except: return None

def analyze_special(symbol, is_weekend):
    df = get_df(SYMBOLS[symbol])
    if df is None or len(df) < 220: return f"{symbol}: NO DATA"

    c, h, l = df['Close'], df['High'], df['Low']
    df['EMA20'] = c.ewm(20).mean()
    df['EMA50'] = c.ewm(50).mean()
    df['EMA200'] = c.ewm(200).mean()
    delta = c.diff()
    gain = delta.where(delta>0,0).rolling(14).mean()
    loss = -delta.where(delta<0,0).rolling(14).mean()
    df['RSI'] = 100 - (100/(1+ gain/loss.replace(0,0.001)))
    tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(14).mean()
    df['SWING_HIGH'] = h.rolling(20).max()
    df['SWING_LOW'] = l.rolling(20).min()

    last = df.iloc[-1]
    price = float(last['Close'])
    ema20, ema50, ema200 = float(last['EMA20']), float(last['EMA50']), float(last['EMA200'])
    rsi, atr = float(last['RSI']), float(last['ATR'])
    swing_high, swing_low = float(last['SWING_HIGH']), float(last['SWING_LOW'])

    # Weekend Logic
    if is_weekend and symbol in ["US30","US100"]:
        # حتى لو مسكر منحضر TP SL للاثنين
        big_trend = "BULL" if price > ema200 else "BEAR"
        signal = "BUY" if big_trend=="BULL" else "SELL"
        sl_logical = price*0.992 if signal=="BUY" else price*1.008
        tp1 = price*1.008 if signal=="BUY" else price*0.992
        tp2 = price*1.016 if signal=="BUY" else price*0.984
        tp3 = price*1.024 if signal=="BUY" else price*0.976
        return f"""⏳ {symbol} MARKET CLOSED (Weekend)
Price Last: {price:.2f} | Trend {big_trend} | RSI {rsi:.0f}
🔮 تجهيز للاثنين: {signal} متوقع
SL: {sl_logical:.2f} | TP1:{tp1:.2f} TP2:{tp2:.2f} TP3:{tp3:.2f}
📌 السوق بيفتح الاثنين 10:30 بيروت - حضّر حالك"""

    # Normal logic for BTC always + others weekdays
    if price > ema200 and ema20 > ema200 and ema50 > ema200:
        big_trend = "BULL"
    elif price < ema200 and ema20 < ema200 and ema50 < ema200:
        big_trend = "BEAR"
    else:
        return f"⏸️ {symbol} WAIT | Sideways | Price {price:.2f} | عرضي = لا تدخل"

    if big_trend == "BULL" and price > ema20 > ema50 and rsi > 45:
        signal = "BUY"
        score = 7.5 + (0.8 if rsi<50 else 0)
    elif big_trend == "BEAR" and price < ema20 < ema50 and rsi < 55:
        signal = "SELL"
        score = 7.5 + (0.8 if rsi>50 else 0)
    else:
        return f"⏸️ {symbol} WAIT | Momentum ضعيف | RSI {rsi:.0f}"

    if atr > price * 0.02:
        return f"⏸️ {symbol} WAIT | ATR مجنون {atr:.2f}"

    if signal == "BUY":
        sl_logical = max(price*0.988, min(swing_low, float(df['Low'].iloc[-10:].min())) - atr*0.5)
        tp1 = price + (price - sl_logical) * 1.0
        tp2 = price + (price - sl_logical) * 2.2
        tp3 = price + (price - sl_logical) * 3.5
    else:
        sl_logical = min(price*1.012, max(swing_high, float(df['High'].iloc[-10:].max())) + atr*0.5)
        tp1 = price - (sl_logical - price) * 1.0
        tp2 = price - (sl_logical - price) * 2.2
        tp3 = price - (sl_logical - price) * 3.5

    risk_pct = abs(price - sl_logical)/price*100
    rr = abs(tp3-price)/abs(price-sl_logical)
    status = "🔥 LIVE" if not is_weekend or symbol=="BTC" else "🔮 PRE-MARKET"

    return f"""{"🟢" if signal=="BUY" else "🔴"} {symbol} {signal} {status} | Score {score:.1f}/10
Price: {price:.2f} | {big_trend} | RSI:{rsi:.0f}
💎 SL: {sl_logical:.2f} ({risk_pct:.2f}%) ورا Swing
🎯 TP1:{tp1:.2f} TP2:{tp2:.2f} TP3:{tp3:.2f} RR 1:{rr:.1f}
💼 Risk 1% | {"تداول الان" if status=="🔥 LIVE" else "جاهز للاثنين"}"""

def send_tg(msg):
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates", timeout=10).json()
        cids = {m["message"]["chat"]["id"] for m in r.get("result",[]) if "message" in m}
        for cid in cids:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid, "text":msg}, timeout=15)
        return len(cids)
    except: return 0

@app.route("/")
def home(): return "V15.1 WEEKEND SPECIAL - 7/7 LIVE"

@app.route("/run")
def run():
    now = datetime.now()
    is_weekend = now.weekday() >= 5 # 5=Saturday 6=Sunday
    day_name = now.strftime("%A %d-%m %H:%M Beirut")
    mode = "WEEKEND MODE - BTC LIVE + تجهيز للاثنين" if is_weekend else "WEEKDAY MODE - الكل LIVE"

    msg = f"💎💎💎 V15.1 WEEKEND SPECIAL 💎💎💎\n{day_name}\n{mode}\n{'='*35}\n"
    for s in SYMBOLS:
        msg += analyze_special(s, is_weekend) + "\n" + "-"*35 + "\n"

    msg += "\n✅ السبت: BTC شغال + الباقي تجهيز\n✅ الاثنين: الكل بيدخل تلقائيا"
    sent = send_tg(msg)
    return f"<pre>{msg}\nSent {sent}</pre>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
