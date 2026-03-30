import yfinance as yf
import requests
import os

# 🧠 sentiment จาก keyword ข่าว
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


def generate_signal(percent, score, profit):
    total_score = 0

    if percent > 2:
        total_score += 2
    elif percent < -2:
        total_score -= 2

    total_score += score

    if profit > 10:
        total_score -= 1
    elif profit < -10:
        total_score += 1

    if total_score >= 3:
        return "🔥 Strong Buy", total_score
    elif total_score <= -3:
        return "⚠️ Strong Sell", total_score
    elif total_score > 0:
        return "📈 Buy Bias", total_score
    elif total_score < 0:
        return "📉 Sell Bias", total_score
    else:
        return "➡️ Neutral", total_score

def calculate_rsi(data, period=14):
    delta = data["Close"].diff()

    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    return rsi.iloc[-1]
# 📰 ดึงข่าว
def get_news(symbol):
    try:
        stock = yf.Ticker(symbol)
        news = stock.news

        headlines = []
        for n in news[:5]:
            if "title" in n:
                headlines.append(n["title"])

        return headlines
    except:
        return []


TOKEN = os.getenv("LINE_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

if not TOKEN or not USER_ID:
    raise ValueError("❌ TOKEN หรือ USER_ID ไม่มีค่า")


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

message_text = "📊 AI วิเคราะห์หุ้น (ข่าว + ราคา)\n\n"
recommend = ""
risk_alert = ""
results = []   # 🔥 สำหรับ top picks


for symbol, profit in portfolio.items():
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period="1mo")

        if len(data) < 2:
            continue

        today = data["Close"].iloc[-1]
        yesterday = data["Close"].iloc[-2]

        change = today - yesterday
        percent = (change / yesterday) * 100

        rsi = calculate_rsi(data)
        
        ema20 = data["Close"].ewm(span=20).mean().iloc[-1]
        ema50 = data["Close"].ewm(span=50).mean().iloc[-1]
        ma5 = data["Close"].rolling(window=5).mean().iloc[-1]
        ma20 = data["Close"].rolling(window=20).mean().iloc[-1]
        # 📊 trend
       # 📊 trend combine
        if ema20 > ema50 and today > ma5:
            trend = "🚀 ขาขึ้นแรง"
        elif ema20 < ema50 and today < ma5:
            trend = "🔻 ขาลงแรง"
        else:
            trend = "📊 sideway"

        # 📰 ข่าว
        news_list = get_news(symbol)
        sentiment, score = analyze_sentiment(news_list)

        # fallback
        if not news_list:
            if percent > 1:
                sentiment = "📈 บวก"
                score = 1
            elif percent < -1:
                sentiment = "📉 ลบ"
                score = -1
            else:
                sentiment = "➖ กลาง"
                score = 0

        print(symbol, "score:", score)

        # 🔥 AI signal
        signal, total_score = generate_signal(percent, score, profit)

        # 🔥 override logic (สำคัญมาก)
        if profit < -25 and score < 0:
            signal = "💀 Cut Loss"
        elif profit < -15 and score > 0:
            signal = "🔥 Rebound Buy"
        # 🔥 combine RSI
        if rsi < 30 and score >= 0:
            signal = "🔥 Strong Buy (RSI)"
        elif rsi > 70 and score <= 0:
            signal = "⚠️ Strong Sell (RSI)"
        # 🧠 analysis
        if score > 2 and percent > 1:
            analysis = "ข่าวแรง + ราคาขึ้น"
        elif score < -2 and percent < -1:
            analysis = "ข่าวลบ + ราคาลง"
        elif percent > 2:
            analysis = "แรงซื้อเข้า"
        elif percent < -2:
            analysis = "แรงขายออก"
        else:
            analysis = "รอดูทิศทาง"


                # 🔥 RSI logic
        if rsi > 70:
            rsi_signal = "⚠️ Overbought"
        elif rsi < 30:
            rsi_signal = "🔥 Oversold"
        else:
            rsi_signal = "➖ ปกติ"

        # 🧠 insight
        if total_score >= 3:
            insight = "มีแรงซื้อ + ข่าวสนับสนุน"
        elif total_score <= -3:
            insight = "แรงขาย + sentiment ลบ"
        elif score > 0:
            insight = "ข่าวเริ่มเป็นบวก"
        elif score < 0:
            insight = "ข่าวเริ่มเป็นลบ"
        else:
            insight = "ตลาดยังไม่เลือกทาง"

        # 📊 text
        line = f"""{symbol}: {today:.2f} ({percent:+.2f}%)
พอร์ต: {profit:+.2f}%
{sentiment} (news {score}) | {signal} ({total_score})
🧠 {analysis} | {trend}
📊 RSI: {rsi:.1f} ({rsi_signal})
📌 {insight}
"""

        message_text += line + "\n"

        # 🔥 เก็บไว้จัดอันดับ
        results.append({
            "symbol": symbol,
            "score": total_score
        })

        # 📌 แนะนำ
        if score > 2 and profit < 0:
            recommend += f"{symbol} ข่าวดี + ยังติดลบ อาจเป็นโอกาส\n"

        if score < -2 and profit < -10:
            risk_alert += f"{symbol} ข่าวลบ + ขาดทุนหนัก\n"

        if profit > 15:
            recommend += f"{symbol} กำไรสูง อาจทยอยขาย\n"

    except Exception as e:
        message_text += f"{symbol}: error ({e})\n"


# 🔥 Top picks
top = [x for x in results if x["score"] > 0]

if not top:
    top = sorted(results, key=lambda x: x["score"], reverse=True)[:3]
else:
    top = sorted(top, key=lambda x: x["score"], reverse=True)[:3]
top = sorted(top, key=lambda x: x["score"], reverse=True)[:3]

message_text += "\n🔥 ตัวน่าสนใจ:\n"
for i, s in enumerate(top, 1):
    message_text += f"{i}. {s['symbol']} (score {s['score']})\n"


# 🧠 สรุป
if recommend:
    message_text += "\n🧠 คำแนะนำ:\n" + recommend

if risk_alert:
    message_text += "\n⚠️ ความเสี่ยง:\n" + risk_alert


# 📩 ส่ง LINE
url = "https://api.line.me/v2/bot/message/push"
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}
data = {
    "to": USER_ID,
    "messages": [{"type": "text", "text": message_text}]
}

try:
    response = requests.post(url, headers=headers, json=data)
    print("✅ ส่งสำเร็จ" if response.status_code == 200 else response.text)
except Exception as e:
    print("❌ error:", e)
