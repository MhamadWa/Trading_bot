from flask import Flask
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta
import os, csv, random

app = Flask(__name__)
BOT_TOKEN = "8869764518:AAEop3wmHnEQA5UrNPnIwiFEgV4j2zXIUWM"
CSV_FILE = "trades.csv"

# ========== PRICE ==========
def get_price(sym):
    if sym == "BTC":
        try:
            r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=8).json()
            return float(r['bitcoin']['usd'])
        except:
            pass
    try:
        if sym in ["GOLD","SILVER"]:
            coin = "XAU" if sym=="GOLD" else "XAG"
            r = requests.get(f"https://api.gold-api.com/price/{coin}", timeout=8).json()
            return float(r['price'])
    except:
        pass
    try:
        m = {"GOLD":"GC=F","SILVER":"SI=F","BTC":"BTC-USD","US30":"^DJI","US100":"^NDX"}
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{m[sym]}?interval=1m&range=5d"
        rr = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json()
        c = rr['chart']['result'][0]['indicators']['quote'][0]['close']
        c = [x for x in c if x is not None]
        return float(c[-1])
    except:
        return None

def get_hist(sym, interval="15m", count=300):
    try:
        m = {"GOLD":"GC=F","SILVER":"SI=F","BTC":"BTC-USD","US30":"^DJI","US100":"^NDX"}
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{m[sym]}?interval={interval}&range=1mo"
        rr = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json()
        c = rr['chart']['result'][0]['indicators']['quote'][0]['close']
        c = [x for x in c if x is not None]
        return pd.Series(c[-count:])
    except:
        return None

# ========== INDICATORS PRO MAX ==========
def rsi(s, p=14):
    d = s.diff()
    g = d.where(d>0,0).rolling(p).mean()
    l = -d.where(d<0,0).rolling(p).mean()
    rs = g / (l+0.00001)
    return 100 - (100/(1+rs))

def ema(s,p): return s.ewm(span=p, adjust=False).mean()
def sma(s,p): return s.rolling(p).mean()
def atr(s,p=14): return s.rolling(p).apply(lambda x: max(x)-min(x)).mean()

def adx(h,l,c,p=14):
    try:
        tr = pd.concat([h-l, abs(h-c.shift()), abs(l-c.shift())], axis=1).max(axis=1)
        atr_v = tr.rolling(p).mean()
        up = h.diff(); down = -l.diff()
        plus_dm = up.where((up>down) & (up>0), 0).rolling(p).mean()
        minus_dm = down.where((down>up) & (down>0), 0).rolling(p).mean()
        plus_di = 100*plus_dm/atr_v
        minus_di = 100*minus_dm/atr_v
        dx = 100*abs(plus_di-minus_di)/(plus_di+minus_di+0.0001)
        return dx.rolling(p).mean().iloc[-1], plus_di.iloc[-1], minus_di.iloc[-1]
    except:
        return 20,20,20

def bb_pos(s,p=20):
    ma = s.rolling(p).mean().iloc[-1]
    std = s.rolling(p).std().iloc[-1]
    if std==0: return 50
    upper = ma+2*std; lower = ma-2*std
    return (s.iloc[-1]-lower)/(upper-lower+0.0001)*100

def stoch(s,p=14):
    low = s.rolling(p).min().iloc[-1]
    high = s.rolling(p).max().iloc[-1]
    if high==low: return 50
    return (s.iloc[-1]-low)/(high-low)*100

# ========== FILTERS PRO MAX ==========
def news_filter():
    # يمنع التداول وقت الاخبار القوية - الجمعة 8:30 و الاربعاء 2:00 بتوقيت بيروت
    now = datetime.now(timezone(timedelta(hours=3)))
    if now.weekday()==4 and now.hour==15 and now.minute<45: # NFP الجمعة
        return False, "NFP NEWS"
    if now.weekday()==2 and now.hour==21 and now.minute<45: # FOMC
        return False, "FOMC NEWS"
    return True, ""

def session_filter(sym):
    now = datetime.now(timezone(timedelta(hours=3)))
    h = now.hour
    if sym in ["US30","US100"]:
        if h < 16 or h > 23: # بس وقت امريكا
            return False, "US MARKET CLOSED"
    return True, ""

# ========== TREND PRO MAX ==========
def get_trend_pro(sym):
    h1 = get_hist(sym,"1h",100)
    m15 = get_hist(sym,"15m",100)
    if h1 is None or m15 is None: return "NEUTRAL",0
    e50_h1 = ema(h1,50).iloc[-1]; e20_h1 = ema(h1,20).iloc[-1]
    e50_m15 = ema(m15,50).iloc[-1]
    p = h1.iloc[-1]
    score=0
    if p>e20_h1: score+=2
    if e20_h1>e50_h1: score+=2
    if m15.iloc[-1]>e50_m15: score+=1
    if score>=4: return "BULL_STRONG",score
    if score>=3: return "BULL",score
    if score<=1: return "BEAR_STRONG",score
    if score<=2: return "BEAR",score
    return "NEUTRAL",score

def backtest_pro(sym):
    hist = get_hist(sym,"15m",400)
    if hist is None or len(hist)<150: return "0/0 0%",0,0
    wins=0; total=0; profit=0
    for i in range(100, len(hist)-15):
        sub = hist.iloc[:i]
        r = float(rsi(sub).iloc[-1])
        bb = bb_pos(sub); st = stoch(sub)
        e50 = float(ema(sub,50).iloc[-1])
        buy=0; sell=0
        if r<28: buy+=2.5
        if r>72: sell+=2.5
        if bb<10: buy+=2.5
        if bb>90: sell+=2.5
        if st<12: buy+=2
        if st>88: sell+=2
        if sub.iloc[-1]>e50: buy+=1
        else: sell+=1
        sig="WAIT"
        if buy>=5: sig="BUY"
        elif sell>=5: sig="SELL"
        if sig=="WAIT": continue
        total+=1
        entry=sub.iloc[-1]
        fut=hist.iloc[i+1:i+11]
        if len(fut)==0: continue
        if sig=="BUY" and fut.max()>entry*1.004: wins+=1; profit+=0.4
        elif sig=="SELL" and fut.min()<entry*0.996: wins+=1; profit+=0.4
        else: profit-=0.5
    if total==0: return "0/0 0%",0,0
    wr=wins/total*100
    return f"{wins}/{total} {int(wr)}% PF:{profit:.1f}", wr, profit

# ========== ANALYZE PRO PRO PRO MAX ==========
def analyze_pro_max(name):
    # فلاتر
    ok, reason = news_filter()
    if not ok: return f"{name} WAIT {reason}"
    ok, reason = session_filter(name)
    if not ok and name!="BTC": return f"{name} WAIT {reason}"

    hist = get_hist(name,"15m",200)
    hist_h1 = get_hist(name,"1h",100)
    hist_5m = get_hist(name,"5m",100)
    live = get_price(name)
    if hist is None or live is None: return f"{name} WAIT no data weekend"
    if len(hist)<50: return f"{name} WAIT short"

    price=live
    r14 = float(rsi(hist,14).iloc[-1])
    r21 = float(rsi(hist,21).iloc[-1])
    bb = bb_pos(hist,20)
    st_k = stoch(hist,14)
    st_d = stoch(hist,21)
    e9 = float(ema(hist,9).iloc[-1]); e21 = float(ema(hist,21).iloc[-1]); e50 = float(ema(hist,50).iloc[-1]); e200 = float(ema(hist,200).iloc[-1]) if len(hist)>=200 else e50
    sma50 = float(sma(hist,50).iloc[-1])

    # ADX
    try:
        adx_val, plus_di, minus_di = adx(hist, hist, hist)
    except:
        adx_val=25; plus_di=20; minus_di=20

    trend, trend_score = get_trend_pro(name)

    # ===== SCORE SYSTEM 0-10 =====
    buy_score=0; sell_score=0

    # RSI PRO
    if r14<25: buy_score+=2
    elif r14<35: buy_score+=1
    if r14>75: sell_score+=2
    elif r14>65: sell_score+=1

    if r14<40 and r21<45: buy_score+=0.5
    if r14>60 and r21>55: sell_score+=0.5

    # BB
    if bb<5: buy_score+=2.5
    elif bb<20: buy_score+=1.5
    if bb>95: sell_score+=2.5
    elif bb>80: sell_score+=1.5

    # Stoch
    if st_k<10 and st_d<20: buy_score+=2
    elif st_k<25: buy_score+=1
    if st_k>90 and st_d>80: sell_score+=2
    elif st_k>75: sell_score+=1

    # EMA
    if price>e9 and e9>e21 and e21>e50: buy_score+=1.5
    elif price<e9 and e9<e21 and e21<e50: sell_score+=1.5

    if price>e200: buy_score+=0.5
    else: sell_score+=0.5

    # ADX Trend Strength
    if adx_val>25:
        if plus_di>minus_di: buy_score+=1
        else: sell_score+=1
    if adx_val<15: # سوق ميت
        return f"{name} WAIT LOW ADX {int(adx_val)} BT"

    # Multi-timeframe confirmation
    if trend in ["BULL_STRONG"]: buy_score+=1.5
    elif trend=="BULL": buy_score+=0.8
    if trend in ["BEAR_STRONG"]: sell_score+=1.5
    elif trend=="BEAR": sell_score+=0.8

    # Volume spike simulation (based on ATR)
    atr_val = hist.rolling(14).apply(lambda x: max(x)-min(x)).mean()
    if pd.isna(atr_val): atr_val=price*0.003

    sig="WAIT"; conf=0
    total_buy=buy_score; total_sell=sell_score

    if total_buy>=6.5:
        sig="BUY"; conf=95 if total_buy>=8 else 88 if total_buy>=7 else 80
    elif total_sell>=6.5:
        sig="SELL"; conf=95 if total_sell>=8 else 88 if total_sell>=7 else 80
    elif total_buy>=5:
        sig="BUY"; conf=70
    elif total_sell>=5:
        sig="SELL"; conf=70

    bt_text, wr, pf = backtest_pro(name)

    # فلاتر نهائية PRO MAX
    if sig!="WAIT" and wr<60: return f"{name} WAIT LOW WR {bt_text} Score {max(total_buy,total_sell):.1f}/10"
    if sig!="WAIT" and pf<0: return f"{name} WAIT NEG PF {bt_text}"
    if sig=="BUY" and "BEAR_STRONG" in trend and total_buy<7.5: return f"{name} WAIT BEAR {trend} {bt_text}"
    if sig=="SELL" and "BULL_STRONG" in trend and total_sell<7.5: return f"{name} WAIT BULL {trend} {bt_text}"
    if sig=="WAIT": return f"{name} WAIT {trend} ADX{int(adx_val)} Score{max(total_buy,total_sell):.1f}/10 BT {bt_text}"

    # SL TP DYNAMIC PRO MAX
    dist = atr_val*1.2
    if dist < price*0.004: dist = price*0.004
    if dist > price*0.015: dist = price*0.015

    if sig=="BUY":
        sl = price - dist
        tp1 = price + dist*0.8
        tp2 = price + dist*1.6
        tp3 = price + dist*2.4
    else:
        sl = price + dist
        tp1 = price - dist*0.8
        tp2 = price - dist*1.6
        tp3 = price - dist*2.4

    # Save
    try:
        ex=os.path.isfile(CSV_FILE)
        with open(CSV_FILE,'a',newline='') as f:
            w=csv.writer(f)
            if not ex: w.writerow(['time','sym','sig','conf','score','price','wr','pf'])
            w.writerow([datetime.now().isoformat(),name,sig,conf,round(max(total_buy,total_sell),1),price,int(wr),round(pf,1)])
    except:
        pass

    out = f"{name} {sig} {conf}% Score{max(total_buy,total_sell):.1f}/10\n"
    out += f"Price {round(price,2)} RSI{r14:.0f} BB{bb:.0f}% ADX{int(adx_val)}\n"
    out += f"SL {round(sl,2)} TP1 {round(tp1,2)} TP2 {round(tp2,2)} TP3 {round(tp3,2)}\n"
    out += f"{trend} | BT {bt_text}"
    return out

def send_tg(text):
    try:
        base="https://api.telegram.org/bot"
        u1=base+BOT_TOKEN+"/getUpdates"
        up=requests.get(u1,timeout=10).json()
        res=up.get("result",[])
        if not res: return
        cid=res[-1].get("message",{}).get("chat",{}).get("id")
        if not cid: return
        u2=base+BOT_TOKEN+"/sendMessage"
        requests.get(u2,params={"chat_id":cid,"text":text},timeout=15)
    except:
        pass

@app.route("/run")
def run():
    names=["GOLD","SILVER","BTC","US30","US100"]
    msgs=[analyze_pro_max(n) for n in names]
    final="🔥 V12 PRO PRO PRO MAX ULTRA 🔥\n"
    final+=datetime.now(timezone(timedelta(hours=3))).strftime("%Y-%m-%d %H:%M BEIRUT")+"\n\n"
    final+="\n\n---\n\n".join(msgs)
    final+="\n\nTP 0.8% 1.6% 2.4% | News+Session Filter ON"
    send_tg(final)
    return f"<pre>{final}</pre>"

@app.route("/stats")
def stats():
    try:
        if not os.path.isfile(CSV_FILE): return "<pre>لا يوجد</pre>"
        df=pd.read_csv(CSV_FILE)
        return f"<pre>{df.tail(30).to_string()}</pre>"
    except Exception as e:
        return f"<pre>{e}</pre>"

@app.route("/")
def home():
    return "V12 PRO PRO PRO MAX LIVE - /run - /stats"
