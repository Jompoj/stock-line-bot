import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
import time
from sklearn.ensemble import RandomForestClassifier
from flask import Flask, jsonify

# ==============================
# 🔥 CONFIG
# ==============================
portfolio = ["NVDA","GOOGL","AMZN","META","ASML","CVX","KO"]

TOKEN = os.getenv("LINE_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

# ==============================
# 📊 DATA
# ==============================
def get_data(symbol):
    try:
        data = yf.Ticker(symbol).history(period="6mo", interval="1d")
        data = data.dropna()
        if len(data) > 50:
            return data
    except:
        return None
    return None

# ==============================
# 📊 INDICATORS
# ==============================
def add_indicators(df):
    df["Return"] = df["Close"].pct_change()

    df["EMA20"] = df["Close"].ewm(span=20).mean()
    df["EMA50"] = df["Close"].ewm(span=50).mean()

    df["MA5"] = df["Close"].rolling(5).mean()

    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    ema12 = df["Close"].ewm(span=12).mean()
    ema26 = df["Close"].ewm(span=26).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_signal"] = df["MACD"].ewm(span=9).mean()

    df["Target"] = (df["Return"].shift(-1) > 0).astype(int)

    return df.dropna()

# ==============================
# 🤖 MACHINE LEARNING
# ==============================
def train_ml(df):
    features = df[["Return","RSI","MACD","Volume"]]
    target = df["Target"]

    model = RandomForestClassifier(n_estimators=100)
    model.fit(features, target)

    return model

# ==============================
# 💰 BACKTEST
# ==============================
def backtest(df):
    capital = 10000
    position = 0

    for i in range(50, len(df)):
        row = df.iloc[i]

        # momentum strategy
        if row["EMA20"] > row["EMA50"] and row["MACD"] > row["MACD_signal"]:
            if position == 0:
                position = capital / row["Close"]
                capital = 0
        else:
            if position > 0:
                capital = position * row["Close"]
                position = 0

    return capital

# ==============================
# 🚀 ANALYZE
# ==============================
def analyze_stock(symbol):
    data = get_data(symbol)
    if data is None:
        return None

    df = add_indicators(data)

    model = train_ml(df)

    latest = df.iloc[-1]

    percent = latest["Return"] * 100

    avg_volume = df["Volume"].rolling(20).mean().iloc[-1]

    # ==============================
    # 🔥 SMART SCORE SYSTEM (แม่นขึ้น)
    # ==============================
    score = 0

    # ✅ Momentum (หลัก)
    momentum_ok = percent > 2 and latest["MACD"] > latest["MACD_signal"]
    if momentum_ok:
        score += 3

    if percent > 4:
        score += 1

    # ✅ Trend confirmation
    trend_ok = latest["EMA20"] > latest["EMA50"]
    if trend_ok:
        score += 1

    # ✅ Volume (ไม่ strict เกิน)
    volume_ok = latest["Volume"] > avg_volume * 0.8
    if volume_ok:
        score += 1

    # ❌ กันหุ้นพุ่งแรงเกิน (ไม่ไล่ราคา)
    if percent > 8:
        return {
            "symbol": symbol,
            "price": round(latest["Close"],2),
            "percent": round(percent,2),
            "score": score,
            "signal": "⚠️ Overextended",
            "ml": "-",
            "backtest": 0
        }

    # ==============================
    # 🤖 MACHINE LEARNING (ลดอิทธิพล)
    # ==============================
    pred = model.predict([[latest["Return"], latest["RSI"], latest["MACD"], latest["Volume"]]])[0]

    if pred == 1:
        score += 1.5   # ลดจาก 3 → 1.5
        ml_text = "📈 ML ขึ้น"
    else:
        score -= 1
        ml_text = "📉 ML ลง"

    # ==============================
    # 🎯 FINAL SIGNAL (ฉลาดขึ้น)
    # ==============================
    if score >= 5 and momentum_ok and trend_ok:
        signal = "🔥 STRONG BUY"
    elif score >= 4 and momentum_ok:
        signal = "🔥 BUY"
    elif score <= -3:
        signal = "⚠️ SELL"
    else:
        signal = "➡️ WAIT"

    # ==============================
    # 💰 BACKTEST
    # ==============================
    bt = backtest(df)

    return {
        "symbol": symbol,
        "price": round(latest["Close"],2),
        "percent": round(percent,2),
        "score": round(score,2),
        "signal": signal,
        "ml": ml_text,
        "backtest": round(bt,2)
    }

# ==============================
# 🎯 AI เลือก 1 ตัว
# ==============================
def pick_best(results):
    results = [r for r in results if r is not None]

    # เอาเฉพาะตัวที่ "ควรเข้า"
    candidates = [r for r in results if "BUY" in r["signal"]]

    if not candidates:
        return None

    # เรียงตาม score + backtest
    candidates = sorted(candidates,
                        key=lambda x: (x["score"], x["backtest"]),
                        reverse=True)

    best = candidates[0]

    # ต้องผ่านขั้นต่ำจริง
    if best["score"] >= 4:
        return best

    return None

# ==============================
# 📩 LINE
# ==============================
def send_line(text):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "to": USER_ID,
        "messages": [{"type": "text", "text": text}]
    }
    requests.post(url, headers=headers, json=data)

# ==============================
# 🧠 MAIN BOT
# ==============================
def run_bot():
    results = []

    text = "📊 ELON BOT V3 (AI TRADING)\n\n"

    for s in portfolio:
        r = analyze_stock(s)
        if r:
            results.append(r)

            text += f"""{r['symbol']} {r['price']} ({r['percent']}%)
{r['signal']} | {r['ml']}
Score: {r['score']}
Backtest: {r['backtest']}

"""

    best = pick_best(results)

    text += "\n🚀 FINAL DECISION:\n"

    if best:
        text += f"🔥 เข้า: {best['symbol']} ({best['score']})"
    else:
        text += "❌ ไม่ควรเข้า"

    send_line(text)

    return results, best

# ==============================
# 🌐 WEB DASHBOARD
# ==============================
app = Flask(__name__)

@app.route("/")
def home():
    results, best = run_bot()
    return jsonify({
        "stocks": results,
        "best": best
    })

# ==============================
# 🚀 RUN
# ==============================
if __name__ == "__main__":
    run_bot() 
