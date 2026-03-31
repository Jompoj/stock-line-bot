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

message_text = "📊 AI วิเคราะห์หุ้น (PRO+ VERSION)\n\n"
results = []

# 🌍 market tracking
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

        # Indicators
        rsi = calculate_rsi(data)
        macd, macd_signal = calculate_macd(data)

        ema20 = data["Close"].ewm(span=20).mean().iloc[-1]
        ema50 = data["Close"].ewm(span=50).mean().iloc[-1]
        ma5 = data["Close"].rolling(5).mean().iloc[-1]

        volume = data["Volume"].iloc[-1]
        avg_volume = data["Volume"].rolling(20).mean().iloc[-1]

        # Trend + market count
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

               # ==============================
        # 📊 Volume (อัปเกรด)
        # ==============================
        if volume > avg_volume * 1.5:
            volume_signal = "💰 Volume เข้าแรง"
            volume_score = 2
        elif volume < avg_volume * 0.7:
            volume_signal = "💤 Volume แห้ง"
            volume_score = -2
        else:
            volume_signal = "📊 Volume ปกติ"
            volume_score = 0

        # ==============================
        # 📊 MACD
        # ==============================
        if macd > macd_signal:
            macd_text = "📈 MACD Bullish"
            macd_score = 2
        else:
            macd_text = "📉 MACD Bearish"
            macd_score = -2

        # ==============================
        # 🚀 Breakout
        # ==============================
        high_20 = data["High"].rolling(20).max().iloc[-1]
        if today >= high_20:
            breakout = "🚀 Breakout"
            breakout_score = 3
        else:
            breakout = ""
            breakout_score = 0
        # ==============================
        # 🧠 SCORE (อัปเกรด)
        # ==============================
        total_score = 0
        
        if percent > 2:
            total_score += 3
        elif percent < -2:
            total_score -= 3
        
        total_score += news_score + macd_score + volume_score + breakout_score

        # RSI กันหลอก
       # ==============================
        # 🧠 SIGNAL (กันหลอก)
        # ==============================
        if rsi < 25 and macd > macd_signal:
            signal = "🔥 Strong Buy (Confirmed)"
            total_score += 2
        elif rsi < 25:
            signal = "⚠️ Oversold (รอเด้ง)"
        elif rsi > 75 and macd < macd_signal:
            signal = "⚠️ Strong Sell (Confirmed)"
            total_score -= 2
        elif rsi > 75:
            signal = "⚠️ Overbought"
        elif total_score >= 4:
            signal = "🔥 Buy"
        elif total_score <= -4:
            signal = "⚠️ Sell"
        else:
            signal = "➡️ Neutral"

        # Cut loss
        if profit < -30 and macd < macd_signal:
            signal = "💀 เสี่ยงสูง (Dead Cat Bounce)"
        # ==============================
        # 🚫 กัน Fake breakout
        # ==============================
        if "Strong Buy" in signal and volume < avg_volume:
            signal = "⚠️ Fake Breakout"


        # Entry logic (โปรจริง)
        # ==============================
        # 📍 Entry logic (แก้ของเดิม)
        # ==============================
        if "Dead Cat" in signal:
            entry = "⛔ ห้ามเข้าเด็ดขาด"
        elif "Fake Breakout" in signal:
            entry = "⚠️ รอสัญญาณใหม่"
        elif "Strong Buy" in signal:
            entry = "🚀 เข้าได้ทันที"
        elif "Buy" in signal and trend != "🔻 ขาลงแรง":
            entry = "📍 เข้าได้"
        elif "Oversold" in signal:
            entry = "📍 รอสัญญาณยืนยัน"
        elif signal.startswith("⚠️"):
            entry = "⛔ ห้ามเข้า"
        else:
            entry = "⏳ รอ"


        # RSI text
        if rsi > 70:
            rsi_text = "⚠️ Overbought"
        elif rsi < 30:
            rsi_text = "🔥 Oversold"
        else:
            rsi_text = "➖ ปกติ"

               
        # ==============================
        # 🧠 Insight
        # ==============================
        if rsi < 30 and macd < macd_signal:
            insight = "📉 ลงแรง แต่ยังไม่กลับตัว"
        elif rsi < 30 and macd > macd_signal:
            insight = "🔥 เริ่มกลับตัว"
        elif rsi > 70:
            insight = "⚠️ เสี่ยงย่อ"
        elif breakout:
            insight = "🚀 ทะลุแนวต้าน"
        else:
            insight = "📊 ปกติ"
        
        
        # ==============================
        # 🎯 Confidence (อัปเกรด)
        # ==============================
        confidence = int(min(max((abs(total_score) / 6) * 100, 20), 95))
        # OUTPUT
        line = f"""{symbol}: {today:.2f} ({percent:+.2f}%)
พอร์ต: {profit:+.2f}%
{sentiment} | {signal} ({total_score})
🎯 ความมั่นใจ: {confidence}%
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
# 🌍 Market Overview
# ==============================
total = len(portfolio)

if market_bear > total * 0.6:
    message_text += "\n🚨 ตลาดขาลง (Bear Market)\n"
elif market_bull > total * 0.6:
    message_text += "\n🚀 ตลาดขาขึ้น (Bull Market)\n"
else:
    message_text += "\n📊 ตลาดผันผวน\n"


# ==============================
# 🔥 TOP PICKS
# ==============================
top = sorted(results, key=lambda x: x["score"], reverse=True)[:3]

message_text += "\n🔥 ตัวน่าสนใจ:\n"
for i, s in enumerate(top, 1):
    message_text += f"{i}. {s['symbol']} ({s['score']})\n"


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
