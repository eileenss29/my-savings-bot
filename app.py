import os
from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, 
    FlexSendMessage, FollowEvent
)
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)

# --- ข้อมูลการเชื่อมต่อ ---
line_bot_api = LineBotApi('+JCnVr0NgGYIA4yIIgT5luYdcF+yOLXwm+g7RA43Xo0oOjbNTna3I77Wf+hDese6hiOj65w+tFTdexB2zUIcZ/5PJmHtZsLckuaVKGpPmycShP3KzBjtT09/GUNTdp4kX0lTc5sifwwmkAdgBAQ7vgdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('41f95879f96925fe1179edff0f5db73f')

# --- เชื่อมต่อ Firebase ---
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    print(f"Firebase Error: {e}")

# --- คลังคำพูด ---
msg_dict = {
    'th': {
        'welcome': "สวัสดีค่ะคุณ {name}! ยินดีต้อนรับสู่ My Savings Space",
        'reg_btn': "🚀 เริ่มตั้งเป้าหมายการออม",
        'confirm': "บันทึกยอด {amt} {curr} เรียบร้อยแล้วค่ะ! ✨",
        'error_num': "กรุณาพิมพ์เป็นตัวเลขนะคะ"
    }
}

def send_greeting(reply_token, user_name):
    welcome_flex = {
      "type": "bubble",
      "hero": {
        "type": "image",
        "url": "https://eileenss29.github.io/my-savings-bot/นักออมอวกาศ_tran.png",
        "size": "full",
        "aspectRatio": "20:13",
        "aspectMode": "cover"
      },
      "body": {
        "type": "box",
        "layout": "vertical",
        "contents": [
          { "type": "text", "text": "My Savings Space 🧑‍🚀💰", "weight": "bold", "size": "xl", "color": "#2C3E50" },
          { "type": "text", "text": f"สวัสดีคุณ {user_name}! มาเริ่มต้นภารกิจเก็บเงินของคุณให้สำเร็จกันเถอะ", "wrap": True, "margin": "md", "color": "#555555", "size": "sm" }
        ]
      },
      "footer": {
        "type": "box",
        "layout": "vertical",
        "contents": [
          {
            "type": "button",
            "style": "primary",
            "color": "#FFB320",
            "action": { "type": "uri", "label": "🚀 ลงทะเบียนเริ่มออม", "uri": "https://liff.line.me/2009295672-lvQVM5Ey" }
          }
        ]
      }
    }
    line_bot_api.reply_message(reply_token, FlexSendMessage(alt_text="Welcome", contents=welcome_flex))

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['x-line-signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(FollowEvent)
def handle_follow(event):
    user_id = event.source.user_id
    profile = line_bot_api.get_profile(user_id)
    send_greeting(event.reply_token, profile.display_name)

@app.route("/api/register", methods=['POST'])
def register_user():
    data = request.json
    user_id = data.get('userId')
    db.collection('users').document(user_id).set(data, merge=True)
    line_bot_api.push_message(user_id, TextSendMessage(text="ตั้งค่าเรียบร้อยแล้วค่ะ! 🚀"))
    return jsonify({"status": "success"})

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    msg_text = event.message.text.strip()
    
    try:
        amount = float(msg_text)
        db.collection('savings').add({
            'user_id': user_id,
            'amount': amount,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"บันทึกยอด {amount} เรียบร้อย! ✨"))
    except:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="กรุณาพิมพ์ตัวเลขเพื่อออมเงินนะคะ"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
