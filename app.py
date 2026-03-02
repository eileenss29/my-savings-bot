import os
from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, 
    ShowLoadingAnimationRequest, FlexSendMessage
)
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)

# --- ข้อมูลการเชื่อมต่อ (ใช้ข้อมูลเดิมของคุณ) ---
line_bot_api = LineBotApi('+JCnVr0NgGYIA4yIIgT5luYdcF+yOLXwm+g7RA43Xo0oOjbNTna3I77Wf+hDese6hiOj65w+tFTdexB2zUIcZ/5PJmHtZsLckuaVKGpPmycShP3KzBjtT09/GUNTdp4kX0lTc5sifwwmkAdgBAQ7vgdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('41f95879f96925fe1179edff0f5db73f')

# --- เชื่อมต่อ Firebase ---
cred = credentials.Certificate("serviceAccountKey.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

# --- คลังคำพูด 2 ภาษา ---
msg_dict = {
    'th': {
        'welcome': "สวัสดีค่ะคุณ {name}! ยินดีต้อนรับสู่ My Savings Space",
        'reg_btn': "ลงทะเบียนตั้งค่า",
        'confirm': "บันทึกยอด {amt} บาท ในเป้าหมาย '{goal}' เรียบร้อยแล้วค่ะ! ✨",
        'error_num': "กรุณาพิมพ์เป็นตัวเลข หรือ 'เป้าหมาย : ยอดเงิน' นะคะ"
    },
    'en': {
        'welcome': "Hello {name}! Welcome to My Savings Space",
        'reg_btn': "Register / Settings",
        'confirm': "Successfully saved {amt} THB to '{goal}'! ✨",
        'error_num': "Please enter a number or 'Goal : Amount'"
    }
}

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['x-line-signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# --- API ใหม่สำหรับรับข้อมูลจาก Popup (LIFF) ---
@app.route("/api/register", methods=['POST'])
def register_user():
    data = request.json
    user_id = data.get('userId')
    
    # อัปเดตข้อมูลการตั้งค่าลง Firebase
    db.collection('users').document(user_id).set({
        'user_id': user_id,
        'display_name': data.get('displayName'),
        'goal_name': data.get('goalName'),
        'plan': data.get('plan'),
        'language': data.get('language'),
        'registered': True
    }, merge=True)
    
    return jsonify({"status": "success"})

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    msg_text = event.message.text.strip()

    # 1. แสดง Loading Animation
    line_bot_api.show_loading_animation(ShowLoadingAnimationRequest(chatId=user_id, loadingSeconds=3))

    # 2. เช็คสถานะการลงทะเบียน
    user_ref = db.collection('users').document(user_id)
    user_doc = user_ref.get()
    profile = line_bot_api.get_profile(user_id)
    
    # ดึงภาษาเครื่องเบื้องต้น
    detected_lang = profile.language if profile.language in ['th', 'en'] else 'en'
    
    if not user_doc.exists or not user_doc.to_dict().get('registered'):
        # --- ส่ง Flex Message ทักทายพร้อมปุ่มเปิด Popup ---
        welcome_text = msg_dict[detected_lang]['welcome'].format(name=profile.display_name)
        btn_text = msg_dict[detected_lang]['reg_btn']
        
        # หมายเหตุ: ตรง 'YOUR_LIFF_URL' ต้องเปลี่ยนเป็นลิงก์ LIFF หลังจากสร้างใน LINE Dev นะคะ
        flex_msg = {
            "type": "bubble",
            "body": {
                "type": "box", "layout": "vertical",
                "contents": [
                    {"type": "text", "text": welcome_text, "weight": "bold", "size": "md"},
                    {"type": "button", "style": "primary", "margin": "md",
                     "action": {"type": "uri", "label": btn_text, "uri": "https://liff.line.me/YOUR_LIFF_ID"}}
                ]
            }
        }
        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="Welcome", contents=flex_msg))
        return

    # 3. ถ้าลงทะเบียนแล้ว ดึงการตั้งค่ามาใช้
    user_data = user_doc.to_dict()
    user_lang = user_data.get('language', 'en')
    default_goal = user_data.get('goal_name', 'General')

    # 4. ตรรกะบันทึกเงิน (รองรับการพิมพ์แยกเป้าหมายเหมือนเดิม)
    try:
        if ":" in msg_text or "：" in msg_text:
            split_char = ":" if ":" in msg_text else "："
            goal_name, amount_str = msg_text.split(split_char)
            goal_name = goal_name.strip()
            amount = float(amount_str.strip())
        else:
            goal_name = default_goal
            amount = float(msg_text)

        db.collection('savings').add({
            'user_id': user_id,
            'user_name': profile.display_name,
            'goal_name': goal_name,
            'amount': amount,
            'timestamp': firestore.SERVER_TIMESTAMP
        })

        response = msg_dict[user_lang]['confirm'].format(amt=amount, goal=goal_name)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))

    except ValueError:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg_dict[user_lang]['error_num']))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
