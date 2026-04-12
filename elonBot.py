import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

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
        data = yf.Ticker(symbol).history(period="1y", interval="1d")
        data = data.dropna()
        if len(data) > 100:
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

    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    ema12 = df["Close"].ewm(span=12).mean()
    ema26 = df["Close"].ewm(span=26).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_signal"] = df["MACD"].ewm(span=9).mean()

    df["VolumeAvg"] = df["Volume"].rolling(20).mean()

    df["Target"] = (df["Return"].shift(-1) > 0).astype(int)

    return df.dropna()

# ==============================
# 🤖 MACHINE LEARNING (จริงขึ้น)
# ==============================
def train_ml(df):
    features = df[["Return","RSI","MACD","Volume"]]
    target = df["Target"]

    X_train, X_test, y_train, y_test = train_test_split(
        features, target, test_size=0.2, shuffle=False
    )

    model = RandomForestClassifier(n_estimators=200, max_depth=6)
    model.fit(X_train, y_train)

    acc = model.score(X_test, y_test)

    return model, acc

# ==============================
# 💰 BACKTEST (สมจริงขึ้น)
# ==============================
def backtest(df):
    capital = 10000
    position = 0

    for i in range(30, len(df)):
        row = df.iloc[i]

        buy_signal = (
            row["EMA20"] > row["EMA50"]
            and row["MACD"] > row["MACD_signal"]
            and row["RSI"] < 70
        )

        sell_signal = (
            row["MACD"] < row["MACD_signal"]
            or row["RSI"] > 75
        )

        if buy_signal and position == 0:
            position = capital / row["Close"]
            capital = 0

        elif sell_signal and position > 0:
            capital = position * row["Close"]
            position = 0

    if position > 0:
        capital = position * df.iloc[-1]["Close"]

    return capital

# ==============================
# 🚀 ANALYZE
# ==============================
def analyze_stock(symbol):
    data = get_data(symbol)
    if data is None:
        return None

    df = add_indicators(data)

    model, acc = train_ml(df)

    latest = df.iloc[-1]

    percent = latest["Return"] * 100

    # ==============================
    # 🔥 SCORE SYSTEM (ฉลาดขึ้น)
    # ==============================
    score = 0

    momentum = percent > 2 and latest["MACD"] > latest["MACD_signal"]
    trend = latest["EMA20"] > latest["EMA50"]
    volume_ok = latest["Volume"] > latest["VolumeAvg"] * 0.8

    if momentum:
        score += 3
    if trend:
        score += 2
    if volume_ok:
        score += 1

    # ==============================
    # 🤖 ML (ใช้จริงขึ้น)
    # ==============================
    pred = model.predict([[latest["Return"], latest["RSI"], latest["MACD"], latest["Volume"]]])[0]

    if acc > 0.55:  # ใช้เฉพาะ model ที่พอเชื่อถือได้
        if pred == 1:
            score += 2
            ml_text = f"📈 ML ขึ้น ({acc:.2f})"
        else:
            score -= 2
            ml_text = f"📉 ML ลง ({acc:.2f})"
    else:
        ml_text = f"⚠️ ML ไม่น่าเชื่อ ({acc:.2f})"

    # ==============================
    # 🎯 SIGNAL
    # ==============================
    if score >= 6:
        signal = "🔥 STRONG BUY"
    elif score >= 4:
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
        "score": score,
        "signal": signal,
        "ml": ml_text,
        "backtest": round(bt,2)
    }

# ==============================
# 🎯 PICK BEST
# ==============================
def pick_best(results):
    candidates = [r for r in results if "BUY" in r["signal"]]

    if not candidates:
        return None

    candidates = sorted(candidates,
                        key=lambda x: (x["score"], x["backtest"]),
                        reverse=True)

    return candidates[0]

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
# 🧠 MAIN
# ==============================
def run_bot():
    results = []

    text = "📊 ELON BOT V4 (SMART AI)\n\n"

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

# ==============================
# 🚀 RUN
# ==============================
if __name__ == "__main__":
    run_bot()
