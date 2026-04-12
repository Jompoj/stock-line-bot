import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

portfolio = ["NVDA","GOOGL","AMZN","META","ASML","CVX","KO"]

TOKEN = os.getenv("LINE_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

# ==============================
# 📊 DATA
# ==============================
def get_data(symbol):
    try:
        data = yf.Ticker(symbol).history(period="2y")
        return data.dropna() if len(data) > 200 else None
    except:
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

    df["Target"] = (df["Return"].shift(-1) > 0).astype(int)
    return df.dropna()

# ==============================
# 🤖 ML
# ==============================
def train_ml(df):
    X = df[["Return","RSI","MACD","Volume"]]
    y = df["Target"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    model = RandomForestClassifier(n_estimators=200)
    model.fit(X_train, y_train)

    acc = model.score(X_test, y_test)
    return model, acc

# ==============================
# 💰 BACKTEST + WINRATE
# ==============================
def backtest(df):
    capital = 10000
    position = 0
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

    if position > 0:
        capital = position * df.iloc[-1]["Close"]

    winrate = (wins / trades * 100) if trades > 0 else 0
    return capital, winrate

# ==============================
# 🚀 ANALYZE
# ==============================
def analyze(symbol):
    data = get_data(symbol)
    if data is None:
        return None

    df = add_indicators(data)
    model, acc = train_ml(df)
    latest = df.iloc[-1]

    capital, winrate = backtest(df)

    score = 0

    # Trend + Momentum
    if latest["EMA20"] > latest["EMA50"]:
        score += 2
    if latest["MACD"] > latest["MACD_signal"]:
        score += 2

    # ML (ใช้เฉพาะถ้าเชื่อถือได้)
    if acc > 0.58:
        pred = model.predict([[latest["Return"], latest["RSI"], latest["MACD"], latest["Volume"]]])[0]
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
    if score >= 6:
        signal = "🔥 STRONG BUY"
    elif score >= 4:
        signal = "🔥 BUY"
    else:
        signal = "➡️ WAIT"

    confidence = min(max((score / 8) * 100, 20), 95)

    return {
        "symbol": symbol,
        "price": round(latest["Close"],2),
        "score": score,
        "signal": signal,
        "ml": ml_text,
        "capital": round(capital,2),
        "winrate": round(winrate,1),
        "confidence": int(confidence)
    }

# ==============================
# 🧠 MAIN
# ==============================
def run_bot():
    results = []

    text = "📊 ELON BOT V5 (DECISION GRADE)\n\n"

    for s in portfolio:
        r = analyze(s)
        if r:
            results.append(r)

            text += f"""{r['symbol']} {r['price']}
{r['signal']} | {r['ml']}
Score: {r['score']}
Winrate: {r['winrate']}%
Confidence: {r['confidence']}%
Backtest: {r['capital']}

"""

    best = sorted(results, key=lambda x: (x["score"], x["winrate"]), reverse=True)[0]

    text += "\n🚀 FINAL DECISION:\n"
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

# ==============================
if __name__ == "__main__":
    run_bot()
