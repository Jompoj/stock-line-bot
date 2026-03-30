import yfinance as yf
import requests
import os

# 🧠 sentiment แบบง่าย (เริ่มต้นก่อน)
def simple_sentiment(text):
    text = text.lower()
    if "rise" in text or "growth" in text or "profit" in text:
        return "📈 บวก"
    elif "fall" in text or "loss" in text or "drop" in text:
        return "📉 ลบ"
    return "➖ กลาง"

TOKEN = os.getenv("LINE_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

if not TOKEN or not USER_ID:
    raise ValueError("❌ TOKEN หรือ USER_ID ไม่มีค่า (เช็ค GitHub Secrets)")

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

message_text = "📊 AI วิเคราะห์พอร์ตหุ้น\n\n"
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

        # 🧠 mock ข่าว (เอาง่ายก่อน)
        news = f"{symbol} stock movement today"
        sentiment = simple_sentiment(news)

        # 🔥 signal
        if percent > 2 and profit > 0:
            signal = "🔥 Strong"
        elif percent < -3:
            signal = "⚠️ Risk"
        else:
            signal = "➡️ Neutral"

        # 🧠 analysis
        analysis = ""
        if percent < -3 and profit < -10:
            analysis = "แนวโน้มลบ ควรระวัง"
        elif percent > 2 and profit > 5:
            analysis = "โมเมนตัมดี อาจถือต่อ"
        else:
            analysis = "รอดูทิศทาง"

        # 📊 format ใหม่ (โคตรสำคัญ)
        line = f"""{symbol}: {today:.2f} ({percent:+.2f}%)
พอร์ต: {profit:+.2f}%
{sentiment} | {signal}
🧠 {analysis}
"""

        # 🔻 logic เดิมยังอยู่
        if percent < -3:
            recommend += f"{symbol} ลงแรง อาจน่าสนใจ\n"

        if profit < -20:
            risk_alert += f"{symbol} ขาดทุนหนัก {profit}%\n"

        if profit > 10:
            recommend += f"{symbol} กำไรสูง อาจขาย\n"

        message_text += line + "\n"

    except Exception as e:
        message_text += f"{symbol}: error ({e})\n"

# 🧠 สรุปท้าย
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
    print("❌ เกิดข้อผิดพลาดตอนส่ง LINE:", e)

print(response.status_code if 'response' in locals() else "No response")
