import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

from flask import Flask, jsonify

portfolio = ["NVDA","GOOGL","AMZN","META","ASML","CVX","KO"]

TOKEN = os.getenv("LINE_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

# =========================
# 📊 DATA
# =========================
def get_data(symbol):
    try:
        df = yf.Ticker(symbol).history(period="2y")
        return df.dropna() if len(df) > 200 else None
    except:
        return None

# =========================
# 📊 INDICATORS
# =========================
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

    df["ATR"] = (df["High"] - df["Low"]).rolling(14).mean()

    df["Target"] = (df["Return"].shift(-1) > 0).astype(int)

    return df.dropna()

# =========================
# 🤖 ML
# =========================
def train_ml(df):
    X = df[["Return","RSI","MACD","Volume","ATR"]]
    y = df["Target"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    model = RandomForestClassifier(n_estimators=300, max_depth=8)
    model.fit(X_train, y_train)

    acc = model.score(X_test, y_test)
    return model, acc

# =========================
# 💰 BACKTEST + EQUITY
# =========================
def backtest(df):
    capital = 10000
    position = 0
    equity = []
    wins = 0
    trades = 0

    for i in range(30, len(df)):
        row = df.iloc[i]

        buy = row["EMA20"] > row["EMA50"] and row["MACD"] > row["MACD_signal"]
        sell = row["MACD"] < row["MACD_signal"]

        if buy and position == 0:
            entry = row["Close"]
            position = capital / entry
            capital = 0

        elif sell and position > 0:
            exit_price = row["Close"]
            capital = position * exit_price
            position = 0

            trades += 1
            if exit_price > entry:
                wins += 1

        equity.append(capital if position == 0 else position * row["Close"])

    if position > 0:
        capital = position * df.iloc[-1]["Close"]

    winrate = (wins / trades * 100) if trades > 0 else 0

    return capital, winrate, equity

# =========================
# 🚀 ANALYZE
# =========================
def analyze(symbol):
    data = get_data(symbol)
    if data is None:
        return None

    df = add_indicators(data)
    model, acc = train_ml(df)
    latest = df.iloc[-1]

    capital, winrate, equity = backtest(df)

    score = 0

    # Trend + Momentum
    if latest["EMA20"] > latest["EMA50"]:
        score += 2
    if latest["MACD"] > latest["MACD_signal"]:
        score += 2

    # Volatility filter (กันผันผวนสูง)
    if latest["ATR"] / latest["Close"] < 0.05:
        score += 1

    # ML
    if acc > 0.58:
        pred = model.predict([[latest["Return"], latest["RSI"], latest["MACD"], latest["Volume"], latest["ATR"]]])[0]
        if pred == 1:
            score += 2
            ml_text = f"📈 ML ({acc:.2f})"
        else:
            score -= 2
            ml_text = f"📉 ML ({acc:.2f})"
    else:
        ml_text = f"⚠️ ML weak ({acc:.2f})"

    # Backtest influence
    if winrate > 55:
        score += 2
    elif winrate < 45:
        score -= 2

    # SIGNAL
    if score >= 7:
        signal = "🔥 STRONG BUY"
    elif score >= 5:
        signal = "🔥 BUY"
    else:
        signal = "➡️ WAIT"

    confidence = min(max((score / 10) * 100, 20), 95)

    return {
        "symbol": symbol,
        "price": round(latest["Close"],2),
        "score": score,
        "signal": signal,
        "ml": ml_text,
        "winrate": round(winrate,1),
        "confidence": int(confidence),
        "backtest": round(capital,2),
        "equity": equity[-50:]  # เอาแค่ช่วงท้าย
    }

# =========================
# 🧠 MAIN BOT
# =========================
def run_bot():
    results = []

    text = "📊 ELON BOT V6 (PRO QUANT)\n\n"

    for s in portfolio:
        r = analyze(s)
        if r:
            results.append(r)

            text += f"""{r['symbol']} {r['price']}
{r['signal']} | {r['ml']}
Score: {r['score']}
Winrate: {r['winrate']}%
Confidence: {r['confidence']}%
Backtest: {r['backtest']}

"""

    best = sorted(results, key=lambda x: (x["score"], x["confidence"]), reverse=True)[0]

    text += "\n🚀 FINAL DECISION:\n"

    if best["confidence"] >= 60:
        text += f"🔥 เข้า: {best['symbol']} ({best['confidence']}%)"
        requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "to": USER_ID,
                "messages": [{"type": "text", "text": text}]
            }
        )
    else:
        text += "❌ ยังไม่ควรเข้า (ความมั่นใจต่ำ)"

    return results, best

# =========================
# 🌐 DASHBOARD
# =========================
app = Flask(__name__)

@app.route("/")
def home():
    results, best = run_bot()
    return jsonify({
        "stocks": results,
        "best": best
    })

# =========================
if __name__ == "__main__":
    run_bot()
