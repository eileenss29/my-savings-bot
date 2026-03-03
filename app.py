import os
from flask import Flask, request, abort, jsonify
from flask_cors import CORS  # ✅ ต้องติดตั้งเพิ่ม: pip install flask-cors
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, 
    FlexSendMessage, FollowEvent
)
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)
CORS(app)  # ✅ อนุญาตให้หน้าเว็บจาก GitHub ส่งข้อมูลมาที่ Render ได้

# --- ข้อมูลการเชื่อมต่อ (Eileen เช็ค Token ให้ตรงกับตัวเทสนะคะ) ---
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

# --- คลังคำพูด 5 ภาษาสำหรับระบบ Global ---
msg_dict = {
    'th': {'success': "ตั้งค่าเป้าหมาย '{goal}' เรียบร้อยแล้วค่ะ! มาเริ่มภารกิจกันเลย 🚀", 'error': "กรุณาพิมพ์เป็นตัวเลขนะคะ"},
    'en': {'success': "Goal '{goal}' set successfully! Let's start the mission 🚀", 'error': "Please enter a number."},
    'zh': {'success': "目标 '{goal}' 设置成功！让我们开始任务吧 🚀", 'error': "请输入数字。"},
    'ja': {'success': "目標 '{goal}' が設定されました！ミッションを開始しましょう 🚀", 'error': "数字を入力してください。"},
    'ko': {'success': "목표 '{goal}' 설정 완료! 미션을 시작합시다 🚀", 'error': "숫자를 입력해주세요."}
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
          { "type": "text", "text": "My Savings Space", "weight": "bold", "size": "xl", "color": "#2C3E50" },
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

# ✅ แก้ไข API ลงทะเบียนให้บันทึกข้อมูลครบถ้วน และตอบโต้ตามภาษาที่เลือก
@app.route("/api/register", methods=['POST'])
def register_user():
    try:
        data = request.json
        user_id = data.get('userId')
        goal_name = data.get('goalName')
        lang = data.get('language', 'th')

        # บันทึกข้อมูลลง Firebase (เก็บไว้ที่ document ของ User เลย)
        db.collection('users').document(user_id).set(data, merge=True)
        
        # เลือกคำตอบกลับตามภาษาที่ผู้ใช้เลือกจากหน้าเว็บ
        reply_msg = msg_dict.get(lang, msg_dict['th'])['success'].format(goal=goal_name)
        
        line_bot_api.push_message(user_id, TextSendMessage(text=reply_msg))
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Register Error: {e}")
        return jsonify({"status": "error"}), 500

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    msg_text = event.message.text.strip()
    
    # ดึงข้อมูลผู้ใช้เพื่อดูว่าใช้สกุลเงินอะไร
    user_doc = db.collection('users').document(user_id).get()
    user_data = user_doc.to_dict() if user_doc.exists else {}
    curr = user_data.get('currency', 'THB')
    lang = user_data.get('language', 'th')

    try:
        amount = float(msg_text)
        # บันทึกประวัติการออมแยกคอลเลกชัน
        db.collection('savings').add({
            'user_id': user_id,
            'amount': amount,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        
        confirm_msg = f"บันทึกยอด {amount} {curr} เรียบร้อย! ✨"
        if lang == 'en': confirm_msg = f"Saved {amount} {curr} successfully! ✨"
        # (เพิ่มเงื่อนไขภาษาอื่นๆ ได้ตามคลังคำพูด)

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=confirm_msg))
    except:
        error_msg = msg_dict.get(lang, msg_dict['th'])['error']
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=error_msg))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
