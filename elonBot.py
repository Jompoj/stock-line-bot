import yfinance as yf
import requests
import os

# 🧠 sentiment จาก keyword ข่าวจริง
def analyze_sentiment(news_list):
    positive_words = ["surge", "rise", "growth", "beat", "strong", "record", "profit"]
    negative_words = ["drop", "fall", "miss", "weak", "loss", "fear", "cut"]

    score = 0

    for news in news_list:
        text = news.lower()
        for word in positive_words:
            if word in text:
                score += 1
        for word in negative_words:
            if word in text:
                score -= 1

    if score > 1:
        return "📈 บวก", score
    elif score < -1:
        return "📉 ลบ", score
    else:
        return "➖ กลาง", score


# 📰 ดึงข่าวจริงจาก yfinance
def get_news(symbol):
    try:
        stock = yf.Ticker(symbol)
        news = stock.news

        headlines = []
        for n in news[:5]:  # เอา 5 ข่าวล่าสุด
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

message_text = "📊 AI วิเคราะห์หุ้น (ข่าวจริง)\n\n"
recommend = ""
risk_alert = ""

for symbol, profit in portfolio.items():
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period="2d")

        if len(data) < 2:
            continue

        today = data["Close"].iloc[-1]
        yesterday = data["Close"].iloc[-2]

        change = today - yesterday
        percent = (change / yesterday) * 100

        # 📰 ดึงข่าวจริง
        news_list = get_news(symbol)

        # 🧠 sentiment จากข่าว
        sentiment, score = analyze_sentiment(news_list)

        # 🔥 signal
        if percent > 2 and score > 0:
            signal = "🔥 Strong Buy"
        elif percent < -3 and score < 0:
            signal = "⚠️ Strong Risk"
        elif score > 0:
            signal = "📈 Positive Bias"
        elif score < 0:
            signal = "📉 Negative Bias"
        else:
            signal = "➡️ Neutral"

        # 🧠 analysis
        if score > 2:
            analysis = "ข่าวหนุนแรง มี momentum"
        elif score < -2:
            analysis = "ข่าวกดดัน เสี่ยงลงต่อ"
        elif percent > 2:
            analysis = "ราคาขึ้น แต่ข่าวยังไม่ชัด"
        elif percent < -2:
            analysis = "ราคาลง ต้องระวัง"
        else:
            analysis = "รอดูทิศทาง"

        # 📊 format
        line = f"""{symbol}: {today:.2f} ({percent:+.2f}%)
พอร์ต: {profit:+.2f}%
{sentiment} (score {score}) | {signal}
🧠 {analysis}
"""

        # 📌 แนะนำ
        if score > 2 and profit < 0:
            recommend += f"{symbol} ข่าวดี + ยังติดลบ อาจเป็นโอกาส\n"

        if score < -2 and profit < -10:
            risk_alert += f"{symbol} ข่าวลบ + ขาดทุนหนัก\n"

        if profit > 15:
            recommend += f"{symbol} กำไรสูง อาจทยอยขาย\n"

        message_text += line + "\n"

    except Exception as e:
        message_text += f"{symbol}: error ({e})\n"

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
    if response.status_code != 200:
        print("❌ ส่งไม่สำเร็จ:", response.text)
    else:
        print("✅ ส่งสำเร็จ")
except Exception as e:
    print("❌ error:", e)

print(response.status_code if 'response' in locals() else "No response")
