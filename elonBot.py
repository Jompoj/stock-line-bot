import yfinance as yf
import requests
import os
import time

# ==============================
# 🧠 sentiment จากข่าว
# ==============================
def analyze_sentiment(news_list):
    positive_words = [
        "surge","rise","growth","beat","strong","record","profit",
        "upgrade","bullish","outperform","gain","positive"
    ]
    
    negative_words = [
        "drop","fall","miss","weak","loss","fear","cut",
        "downgrade","bearish","underperform","decline","negative"
    ]

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

message_text = "📊 AI วิเคราะห์หุ้น (PRO VERSION)\n\n"
results = []
recommend = ""
risk_alert = ""


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

        # ======================
        # 📊 Indicators
        # ======================
        rsi = calculate_rsi(data)
        macd, macd_signal = calculate_macd(data)

        ema20 = data["Close"].ewm(span=20).mean().iloc[-1]
        ema50 = data["Close"].ewm(span=50).mean().iloc[-1]
        ma5 = data["Close"].rolling(5).mean().iloc[-1]

        volume = data["Volume"].iloc[-1]
        avg_volume = data["Volume"].rolling(20).mean().iloc[-1]

        # ======================
        # 📊 Trend
        # ======================
        if ema20 > ema50 and today > ma5:
            trend = "🚀 ขาขึ้นแรง"
        elif ema20 < ema50 and today < ma5:
            trend = "🔻 ขาลงแรง"
        else:
            trend = "📊 sideway"

        # ======================
        # 📰 News
        # ======================
        news_list = get_news(symbol)
        sentiment, news_score = analyze_sentiment(news_list)

        if not news_list:
            sentiment = "➖ กลาง"
            news_score = 0

        # ======================
        # 📊 Volume
        # ======================
        if volume > avg_volume * 1.5:
            volume_signal = "💰 Volume เข้า"
            volume_score = 1
        elif volume < avg_volume * 0.7:
            volume_signal = "💤 Volume แห้ง"
            volume_score = -1
        else:
            volume_signal = "📊 Volume ปกติ"
            volume_score = 0

        # ======================
        # 📊 MACD
        # ======================
        if macd > macd_signal:
            macd_text = "📈 MACD Bullish"
            macd_score = 1
        else:
            macd_text = "📉 MACD Bearish"
            macd_score = -1

        # ======================
        # 🚀 Breakout
        # ======================
        high_20 = data["High"].rolling(20).max().iloc[-1]

        if today >= high_20:
            breakout = "🚀 Breakout"
            breakout_score = 2
        else:
            breakout = ""
            breakout_score = 0

        # ======================
        # 🧠 SCORE
        # ======================
        total_score = 0

        if percent > 2:
            total_score += 2
        elif percent < -2:
            total_score -= 2

        total_score += news_score + macd_score + volume_score + breakout_score

        # ======================
        # 🔥 RSI Override (สำคัญ)
        # ======================
        if rsi < 25:
            signal = "🔥 Strong Buy (RSI)"
            total_score += 2
        elif rsi > 75:
            signal = "⚠️ Strong Sell (RSI)"
            total_score -= 2
        elif total_score >= 3:
            signal = "🔥 Buy"
        elif total_score <= -3:
            signal = "⚠️ Sell"
        else:
            signal = "➡️ Neutral"

        # 💀 Cut loss
        if profit < -25:
            signal = "💀 Cut Loss"

        # ======================
        # 📍 Entry Logic (ใหม่)
        # ======================
        if trend == "🔻 ขาลงแรง" and rsi < 30:
            entry = "📍 รอสัญญาณกลับตัว"
        elif trend == "🚀 ขาขึ้นแรง" and macd > macd_signal:
            entry = "📍 เข้าได้"
        else:
            entry = "⏳ รอ"

        # ======================
        # 📊 RSI text
        # ======================
        if rsi > 70:
            rsi_text = "⚠️ Overbought"
        elif rsi < 30:
            rsi_text = "🔥 Oversold"
        else:
            rsi_text = "➖ ปกติ"

        # ======================
        # 🧠 Insight (ฉลาดขึ้น)
        # ======================
        if rsi < 30 and macd < macd_signal:
            insight = "📉 ลงแรง แต่เริ่ม Oversold"
        elif rsi < 30 and macd > macd_signal:
            insight = "🔥 มีโอกาสเด้ง"
        elif rsi > 70:
            insight = "⚠️ เสี่ยงย่อ"
        elif breakout:
            insight = "🚀 ทะลุแนวต้าน"
        else:
            insight = "📊 ปกติ"

        # ======================
        # 📊 OUTPUT
        # ======================
        line = f"""{symbol}: {today:.2f} ({percent:+.2f}%)
พอร์ต: {profit:+.2f}%
{sentiment} | {signal} ({total_score})
🧠 {trend}
📊 RSI: {rsi:.1f} ({rsi_text})
📊 {macd_text} | {volume_signal}
{breakout}
{entry}
📌 {insight}
"""

        message_text += line + "\n"
        results.append({"symbol": symbol, "score": total_score})

    except Exception as e:
        message_text += f"{symbol}: error ({e})\n"


# ==============================
# 🔥 TOP PICKS
# ==============================
top = sorted(results, key=lambda x: x["score"], reverse=True)[:3]

message_text += "\n🔥 ตัวน่าสนใจ:\n"
for i, s in enumerate(top, 1):
    message_text += f"{i}. {s['symbol']} ({s['score']})\n"


# ==============================
# ✂️ กันข้อความยาว
# ==============================
if len(message_text) > 4500:
    message_text = message_text[:4500] + "\n... (ตัดข้อความ)"


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
    "messages": [{"type": "text", "text": message_text}]
}

requests.post(url, headers=headers, json=data)
