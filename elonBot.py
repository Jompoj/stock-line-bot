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

    # 📊 ราคา
    if percent > 2:
        total_score += 2
    elif percent < -2:
        total_score -= 2

    # 📰 ข่าว
    total_score += score

    # 💼 พอร์ต
    if profit > 10:
        total_score -= 1  # ใกล้จุดขาย
    elif profit < -10:
        total_score += 1  # อาจรีบาว

    # 🎯 ตัดสิน
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

        # 📰 ข่าว
        news_list = get_news(symbol)

        # 🧠 sentiment
        sentiment, score = analyze_sentiment(news_list)

        # 🔥 fallback ถ้าไม่มีข่าว (สำคัญมาก)
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

        # 🔍 debug (ดูใน GitHub log)
        print(symbol, "news:", news_list)
        print(symbol, "score:", score)

        signal, total_score = generate_signal(percent, score, profit)
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
        # 🧠 insight แบบ repo
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

        # 📊 format
    line = f"""{symbol}: {today:.2f} ({percent:+.2f}%)
พอร์ต: {profit:+.2f}%
{sentiment} (news {score}) | {signal} ({total_score})
🧠 {analysis}
📌 {insight}
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
