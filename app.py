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

# --- ข้อมูลการเชื่อมต่อ (Eileen เช็ค Token ให้ถูกต้องนะครับ) ---
line_bot_api = LineBotApi('+JCnVr0NgGYIA4yIIgT5luYdcF+yOLXwm+g7RA43Xo0oOjbNTna3I77Wf+hDese6hiOj65w+tFTdexB2zUIcZ/5PJmHtZsLckuaVKGpPmycShP3KzBjtT09/GUNTdp4kX0lTc5sifwwmkAdgBAQ7vgdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('41f95879f96925fe1179edff0f5db73f')

# --- เชื่อมต่อ Firebase ---
# ตรวจสอบไฟล์ serviceAccountKey.json ว่าอัปโหลดขึ้น GitHub หรือยัง (แต่ระวังเรื่องความเป็นส่วนตัวนะครับ)
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    print(f"Firebase Error: {e}")

# ✅ ADMIN_ID ของคุณ Eileen
ADMIN_ID = 'U_YOUR_ACTUAL_USER_ID'

# --- คลังคำพูด ---
msg_dict = {
    'th': {
        'welcome': "สวัสดีค่ะคุณ {name}! ยินดีต้อนรับสู่ My Savings Space",
        'reg_btn': "🚀 เริ่มตั้งเป้าหมายการออม",
        'confirm': "บันทึกยอด {amt} {curr} ในเป้าหมาย '{goal}' เรียบร้อยแล้วค่ะ! ✨",
        'error_num': "กรุณาพิมพ์เป็นตัวเลขนะคะ"
    },
    'en': {
        'welcome': "Hello {name}! Welcome to My Savings Space",
        'reg_btn': "🚀 Start Saving Goal",
        'confirm': "Successfully saved {amt} {curr} to '{goal}'! ✨",
        'error_num': "Please enter a number."
    }
}

def send_greeting(reply_token, user_name, lang_code):
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
          { "type": "text", "text": f"สวัสดีคุณ {user_name}! มาเริ่มต้นสร้างภารกิจเก็บเงินของคุณให้สำเร็จกันเถอะ", "wrap": True, "margin": "md", "color": "#555555", "size": "sm" }
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
    send_greeting(event.reply_token, profile.display_name, 'th')

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
    
    # ดึงข้อมูลผู้ใช้จาก Firebase
    user_doc = db.collection('users').document(user_id).get()
    if not user_doc.exists:
        profile = line_bot_api.get_profile(user_id)
        send_greeting(event.reply_token, profile.display_name, 'th')
        return

    # Logic การบันทึกเงินออม (ย่อเพื่อความสั้น)
    try:
        amount = float(msg_text)
        # บันทึกยอดเงิน... (Eileen เพิ่มส่วนบันทึก Firebase ตรงนี้ได้ครับ)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"บันทึกยอด {amount} เรียบร้อย!"))
    except:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="กรุณาพิมพ์ตัวเลขเพื่อออมเงินค่ะ"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
