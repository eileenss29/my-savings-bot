import os
from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, 
    ShowLoadingAnimationRequest, FlexSendMessage,
    FollowEvent  # ✅ เพิ่มตัวดักจับการแอดเพื่อน
)
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)

# --- ข้อมูลการเชื่อมต่อ ---
line_bot_api = LineBotApi('+JCnVr0NgGYIA4yIIgT5luYdcF+yOLXwm+g7RA43Xo0oOjbNTna3I77Wf+hDese6hiOj65w+tFTdexB2zUIcZ/5PJmHtZsLckuaVKGpPmycShP3KzBjtT09/GUNTdp4kX0lTc5sifwwmkAdgBAQ7vgdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('41f95879f96925fe1179edff0f5db73f')

# --- เชื่อมต่อ Firebase ---
cred = credentials.Certificate("serviceAccountKey.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

# --- คลังคำพูด 5 ภาษา ---
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
    },
    'zh': {
        'welcome': "您好 {name}! 欢迎来到 My Savings Space",
        'reg_btn': "🚀 开始储蓄目标",
        'confirm': "成功将 {amt} {curr} 存入 '{goal}'! ✨",
        'error_num': "请输入数字。"
    },
    'ja': {
        'welcome': "こんにちは {name} さん! My Savings Space へようこそ",
        'reg_btn': "🚀 貯金目標を開始",
        'confirm': "{amt} {curr} を '{goal}' に貯金しました! ✨",
        'error_num': "数字を入力してください。"
    },
    'ko': {
        'welcome': "안녕하세요 {name} 님! My Savings Space 에 오신 것을 환영합니다",
        'reg_btn': "🚀 저축 목표 시작",
        'confirm': "{amt} {curr} 가 '{goal}' 에 저축되었습니다! ✨",
        'error_num': "숫자를 입력해 주세요."
    }
}

# ✅ ฟังก์ชันสำหรับส่ง Greeting Flex Message (ตามที่คุณต้องการ)
def send_greeting(event, user_name, lang_code):
    # เลือกคำพูดตามภาษาเครื่อง
    welcome_text = msg_dict[lang_code]['welcome'].format(name=user_name)
    btn_text = msg_dict[lang_code]['reg_btn']
    
    flex_greeting = {
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
          {
            "type": "text",
            "text": f"สวัสดีคุณ {user_name}! 🧑‍🚀",
            "weight": "bold",
            "size": "xl",
            "color": "#2C3E50"
          },
          {
            "type": "text",
            "text": "ยินดีต้อนรับสู่ My Savings Space พื้นที่ที่จะช่วยให้การออมเงิน 365 วันของคุณเป็นเรื่องสนุกและง่ายขึ้น!",
            "wrap": True,
            "margin": "md",
            "color": "#7f8c8d",
            "size": "sm"
          },
          {
            "type": "box",
            "layout": "vertical",
            "margin": "xxl",
            "spacing": "sm",
            "contents": [
              {
                "type": "button",
                "style": "primary",
                "color": "#FFB320",
                "action": {
                  "type": "uri",
                  "label": btn_text,
                  "uri": "https://liff.line.me/2009295672-lvQVM5Ey"
                }
              }
            ]
          }
        ]
      },
      "footer": {
        "type": "box",
        "layout": "vertical",
        "contents": [
          {
            "type": "text",
            "text": "มาสร้างวินัยการออมไปด้วยกันนะ",
            "size": "xs",
            "color": "#bdc3c7",
            "align": "center"
          }
        ]
      },
      "styles": {
        "body": { "backgroundColor": "#FFFFFF" },
        "footer": { "separator": True }
      }
    }
    
    line_bot_api.reply_message(
        event.reply_token,
        FlexSendMessage(alt_text="ยินดีต้อนรับสู่ My Savings Space", contents=flex_greeting)
    )

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['x-line-signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# --- ดักจับเหตุการณ์การแอดเพื่อน (Follow Event) ---
@handler.add(FollowEvent)
def handle_follow(event):
    user_id = event.source.user_id
    profile = line_bot_api.get_profile(user_id)
    # เช็คภาษาเครื่องเบื้องต้น
    detected_lang = profile.language if profile.language in msg_dict else 'th'
    # ส่งข้อความทักทายพร้อมปุ่มลงทะเบียนทันที
    send_greeting(event, profile.display_name, detected_lang)

@app.route("/api/register", methods=['POST'])
def register_user():
    data = request.json
    user_id = data.get('userId')
    profile = line_bot_api.get_profile(user_id)
    
    db.collection('users').document(user_id).set({
        'user_id': user_id,
        'display_name': profile.display_name,
        'goal_name': data.get('goalName'),
        'save_style': data.get('saveStyle'),
        'daily_amount': data.get('dailyAmount'),
        'currency': data.get('currency'),
        'language': data.get('language'),
        'total_target': data.get('totalTarget'),
        'registered': True,
        'created_at': firestore.SERVER_TIMESTAMP
    }, merge=True)
    
    lang = data.get('language', 'th')
    confirm_text = "Settings Saved! 🚀" if lang != 'th' else "ตั้งค่าเรียบร้อยแล้วค่ะ! 🚀"
    line_bot_api.push_message(user_id, TextSendMessage(text=confirm_text))
    return jsonify({"status": "success"})

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    msg_text = event.message.text.strip()

    line_bot_api.show_loading_animation(ShowLoadingAnimationRequest(chatId=user_id, loadingSeconds=3))

    user_ref = db.collection('users').document(user_id)
    user_doc = user_ref.get()
    
    if not user_doc.exists or not user_doc.to_dict().get('registered'):
        profile = line_bot_api.get_profile(user_id)
        detected_lang = profile.language if profile.language in msg_dict else 'th'
        send_greeting(event, profile.display_name, detected_lang)
        return

    user_data = user_doc.to_dict()
    user_lang = user_data.get('language', 'th')
    user_currency = user_data.get('currency', 'THB')
    default_goal = user_data.get('goal_name', 'General')

    try:
        if ":" in msg_text or "：" in msg_text:
            split_char = ":" if ":" in msg_text else "："
            goal_parts = msg_text.split(split_char)
            goal_name = goal_parts[0].strip()
            amount = float(goal_parts[1].strip())
        else:
            goal_name = default_goal
            amount = float(msg_text)

        db.collection('savings').add({
            'user_id': user_id,
            'goal_name': goal_name,
            'amount': amount,
            'currency': user_currency,
            'timestamp': firestore.SERVER_TIMESTAMP
        })

        response = msg_dict[user_lang]['confirm'].format(amt=amount, curr=user_currency, goal=goal_name)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))

    except ValueError:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg_dict[user_lang]['error_num']))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
