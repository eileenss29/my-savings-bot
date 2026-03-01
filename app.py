from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)

# --- ใส่รหัสกุญแจของคุณตรงนี้ ---
line_bot_api = LineBotApi('+JCnVr0NgGYIA4yIIgT5luYdcF+yOLXwm+g7RA43Xo0oOjbNTna3I77Wf+hDese6hiOj65w+tFTdexB2zUIcZ/5PJmHtZsLckuaVKGpPmycShP3KzBjtT09/GUNTdp4kX0lTc5sifwwmkAdgBAQ7vgdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('41f95879f96925fe1179edff0f5db73f')

# --- เชื่อมต่อ Firebase ---
cred = credentials.Certificate("serviceAccountKey.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['x-line-signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg_text = event.message.text
    try:
        # ถ้าเราพิมพ์ตัวเลข ระบบจะบันทึกเงินทันที
        amount = float(msg_text)
        data = {
            'amount': amount,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'user_name': 'Eileen'
        }
        db.collection('savings').add(data)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f'บันทึกยอด {amount} บาท ให้แล้วนะค๊าา!'))
    except ValueError:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text='พิมพ์เป็นตัวเลขเพื่อบันทึกเงินออมได้เลยค่ะ'))

if __name__ == "__main__":
    app.run(port=5000)