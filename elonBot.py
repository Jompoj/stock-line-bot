import yfinance as yf
import requests
import os
import time

# ==============================
# 🧠 sentiment จากข่าว
# ==============================
def analyze_sentiment(news_list):
    positive_words = ["surge","rise","growth","beat","strong","record","profit",
        "upgrade","bullish","outperform","gain","positive"]
    
    negative_words = ["drop","fall","miss","weak","loss","fear","cut",
        "downgrade","bearish","underperform","decline","negative"]

    score = 0

    for news in news_list:
        text = news.lower()
        for word in positive_words:
            if word in text:
                score += 2
        for word in negative_words:
            if word in text:
                score -= 2

    sentiment = "📈 บวก" if score > 1 else "📉 ลบ" if score < -1 else "➖ กลาง"
    return sentiment, score


# ==============================
# 📊 Indicators
# ==============================
def calculate_rsi(data, period=14):
    delta = data["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]


def calculate_macd(data):
    ema12 = data["Close"].ewm(span=12).mean()
    ema26 = data["Close"].ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    return macd.iloc[-1], signal.iloc[-1]


# ==============================
# 📰 ข่าว
# ==============================
def get_news(symbol):
    try:
        stock = yf.Ticker(symbol)
        news = stock.news
        return [n["title"] for n in news[:5] if "title" in n]
    except:
        return []


# ==============================
# 🔥 ดึงข้อมูลแบบกันพัง
# ==============================
def get_data_safe(symbol):
    for _ in range(3):
        try:
            stock = yf.Ticker(symbol)
            data = stock.history(period="3mo")
            if not data.empty:
                return data
        except:
            time.sleep(1)
    return None


# ==============================
# 🔑 ENV
# ==============================
TOKEN = os.getenv("LINE_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

if not TOKEN or not USER_ID:
    raise ValueError("❌ TOKEN หรือ USER_ID ไม่มีค่า")


# ==============================
# 💼 PORT
# ==============================
portfolio = {
    "NVDA": -1.95,
    "JNJ": -2.45,
    "GOOGL": -5.09,
    "CVX": 16.56,
    "SPYM": 2.78,
    "JEPQ": 0.26,
    "ASML": -2.88,
    "AMZN": 3.79,
    "META": -21.64,
    "EOSE": -31.70,
    "KO": -7.45
}

message_text = "📊 AI วิเคราะห์หุ้น (PRO FINAL)\n\n"
results = []

market_bear = 0
market_bull = 0


# ==============================
# 🔁 LOOP
# ==============================
for symbol, profit in portfolio.items():
    try:
        data = get_data_safe(symbol)
        if data is None or len(data) < 35:
            continue

        today = data["Close"].iloc[-1]
        yesterday = data["Close"].iloc[-2]
        percent = ((today - yesterday) / yesterday) * 100

        rsi = calculate_rsi(data)
        macd, macd_signal = calculate_macd(data)

        ema20 = data["Close"].ewm(span=20).mean().iloc[-1]
        ema50 = data["Close"].ewm(span=50).mean().iloc[-1]
        ma5 = data["Close"].rolling(5).mean().iloc[-1]

        volume = data["Volume"].iloc[-1]
        avg_volume = data["Volume"].rolling(20).mean().iloc[-1]

        # ❌ FILTER หุ้น
        if volume < avg_volume * 0.7 and abs(percent) < 2:
            continue

        # Trend
        if ema20 > ema50 and today > ma5:
            trend = "🚀 ขาขึ้นแรง"
            market_bull += 1
        elif ema20 < ema50 and today < ma5:
            trend = "🔻 ขาลงแรง"
            market_bear += 1
        else:
            trend = "📊 sideway"

        # News
        news_list = get_news(symbol)
        sentiment, news_score = analyze_sentiment(news_list)
        if not news_list:
            sentiment = "➖ กลาง"
            news_score = 0

        # Volume
        if volume > avg_volume * 1.5:
            volume_signal = "💰 Volume เข้าแรง"
            volume_score = 2
        elif volume < avg_volume * 0.5:
            volume_signal = "💤 Volume แห้ง"
            volume_score = -2
        else:
            volume_signal = "📊 Volume ปกติ"
            volume_score = 0

        # MACD
        if macd > macd_signal:
            macd_text = "📈 MACD Bullish"
            macd_score = 2
        else:
            macd_text = "📉 MACD Bearish"
            macd_score = -2

        # Breakout
        high_20 = data["High"].rolling(20).max().iloc[-1]
        if today >= high_20:
            breakout = "🚀 Breakout"
            breakout_score = 3
        else:
            breakout = ""
            breakout_score = 0

        # SCORE
        total_score = 0

        if percent > 3:
            total_score += 2
        elif percent > 1.5:
            total_score += 1
        elif percent < -3:
            total_score -= 2

        total_score += news_score + macd_score + volume_score + breakout_score

        if trend == "🚀 ขาขึ้นแรง":
            total_score += 1
        elif trend == "🔻 ขาลงแรง":
            total_score -= 1

        # Conviction boost
        if macd > macd_signal and trend == "🚀 ขาขึ้นแรง" and volume > avg_volume:
            total_score += 2

        # SIGNAL
        if rsi < 25 and macd > macd_signal:
            signal = "🔥 Strong Buy"
        elif rsi > 75 and macd < macd_signal:
            signal = "⚠️ Strong Sell"
        elif total_score >= 3:
            signal = "🔥 Buy"
        elif total_score <= -4:
            signal = "⚠️ Sell"
        else:
            signal = "➡️ Neutral"

        # ENTRY
        if "Buy" in signal and trend != "🔻 ขาลงแรง":
            entry = "📍 เข้าได้"
        elif "Sell" in signal:
            entry = "⛔ ห้ามเข้า"
        else:
            entry = "⏳ รอ"

        # Insight
        if rsi < 30 and macd > macd_signal:
            insight = "🔥 เริ่มกลับตัว"
        elif rsi > 70:
            insight = "⚠️ เสี่ยงย่อ"
        elif breakout:
            insight = "🚀 ทะลุแนวต้าน"
        else:
            insight = "📊 ปกติ"

        confidence = int(min(max((abs(total_score) / 6) * 100, 20), 95))

        # TRADE PLAN
        atr = (data["High"] - data["Low"]).rolling(14).mean().iloc[-1]
        entry_price = today
        stop_loss = today - (atr * 1.3)
        take_profit = today + (atr * 2.5)

        rr = (take_profit - entry_price) / (entry_price - stop_loss) if (entry_price - stop_loss) != 0 else 0

        # POSITION SIZE
        risk_per_trade = 0.02
        if (entry_price - stop_loss) > 0:
            position_size = (risk_per_trade / ((entry_price - stop_loss) / entry_price)) * 100
        else:
            position_size = 0

        position_size = min(max(position_size, 5), 30)

        trade_plan = f"""📍 {entry_price:.2f}
🛑 {stop_loss:.2f}
🎯 {take_profit:.2f}
RR: {rr:.2f}
💰 ลงทุน: {position_size:.1f}%"""

        # OUTPUT
        line = f"""{symbol}: {today:.2f} ({percent:+.2f}%)
{sentiment} | {signal} ({total_score})
🎯 {confidence}% | {trend}
📊 {macd_text} | {volume_signal}
{entry}
📌 {insight}

{trade_plan}
"""

        message_text += line + "\n"
        results.append({"symbol": symbol, "score": total_score})

    except Exception as e:
        message_text += f"{symbol}: error ({e})\n"


# ==============================
# 🌍 MARKET
# ==============================
total = len(portfolio)

if market_bear > total * 0.6:
    message_text += "\n🚨 Bear Market\n"
elif market_bull > total * 0.6:
    message_text += "\n🚀 Bull Market\n"
else:
    message_text += "\n📊 Sideway Market\n"


# ==============================
# 🔥 BEST TRADE
# ==============================
top = [r for r in results if r["score"] >= 3]
top = sorted(top, key=lambda x: x["score"], reverse=True)
top = top[:1]

message_text += "\n🔥 BEST TRADE:\n"

if top:
    s = top[0]
    message_text += f"👉 {s['symbol']} ({s['score']})\n"
else:
    message_text += "❌ ไม่มีจังหวะ\n"


# ==============================
# 📩 LINE
# ==============================
url = "https://api.line.me/v2/bot/message/push"
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}
data = {
    "to": USER_ID,
    "messages": [{"type": "text", "text": message_text[:4500]}]
}

requests.post(url, headers=headers, json=data)
