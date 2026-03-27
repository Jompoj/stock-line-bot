import yfinance as yf
import requests
import os

TOKEN = os.getenv("vCXZ86AlBkXZ8Wd+Nag+qO+n6jeHPZLSdc7BINgjABPESF3mpr2+XaRQO9SuL/SddOpYzMpEqpsGDQvSZRrDkkL3xLFInsy7nEKExk8aC2qQs2Ft5V9hSaN9krpHhcS8TiQ7GaB0g/04tLTdWUkr/QdB04t89/1O/w1cDnyilFU=")
USER_ID = os.getenv("U2e2fadff5fb002c8110dcdf38e0bc2c3")


# 📊 พอร์ตของคุณ (ใส่ % กำไร/ขาดทุน)
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

message_text = "📊 สรุปพอร์ต + หุ้นวันนี้\n\n"

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

        line = f"{symbol}: {today:.2f} ({percent:+.2f}%) | พอร์ต {profit:+.2f}%"

        if percent < -3:
            line += " 🔻"
            recommend += f"{symbol} ลงแรงวันนี้ อาจน่าสนใจ\n"

        if profit < -20:
            line += " ⚠️ เสี่ยง"
            risk_alert += f"{symbol} ขาดทุนหนัก {profit}%\n"

        if profit > 10:
            line += " 🔥"
            recommend += f"{symbol} กำไรสูง อาจทยอยขาย\n"

        message_text += line + "\n"

    except Exception as e:
        message_text += f"{symbol}: error\n"

# 🧠 สรุป
if recommend:
    message_text += "\n🧠 แนะนำ:\n" + recommend

if risk_alert:
    message_text += "\n⚠️ ความเสี่ยง:\n" + risk_alert

# 📩 ส่งเข้า LINE
url = "https://api.line.me/v2/bot/message/push"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

data = {
    "to": USER_ID,
    "messages": [
        {
            "type": "text",
            "text": message_text
        }
    ]
}

response = requests.post(url, headers=headers, json=data)

if response.status_code != 200:
    print("❌ ส่งไม่สำเร็จ:", response.text)
else:
    print("✅ ส่งสำเร็จ")

print(response.status_code)
print(response.text)
