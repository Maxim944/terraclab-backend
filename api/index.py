import os
from fastapi import FastAPI, Request
import httpx

# Обязательная строка для Vercel: экземпляр приложения верхнего уровня
app = FastAPI(title="Terra.ai API", version="1.0.0")

GREEN_API_INSTANCE = os.getenv("GREEN_API_INSTANCE", "")
GREEN_API_TOKEN = os.getenv("GREEN_API_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

SYSTEM_PROMPT = """Ты — Terra.ai, персональный ИИ-агроном и эксперт по растениеводству. 
Твоя задача — давать четкие, практичные и дружелюбные советы по уходу за растениями, борьбе с вредителями, 
подкормке и поливу. Отвечай кратко, емко и адаптировано под мессенджер WhatsApp."""

@app.get("/api")
@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Terra.ai Agronomist API", "platform": "Vercel Serverless"}

@app.post("/api/webhook/whatsapp")
@app.post("/api/index.py")
@app.post("/api")
@app.post("/")
async def whatsapp_webhook(request: Request):
    """Прием входящих сообщений из WhatsApp через Green API"""
    data = await request.json()
    
    type_webhook = data.get("typeWebhook")
    if type_webhook == "incomingMessageReceived":
        message_data = data.get("messageData", {})
        sender_data = data.get("senderData", {})
        
        chat_id = sender_data.get("chatId")
        
        text_message = (
            message_data.get("textMessageData", {}).get("textMessage") or
            message_data.get("extendedTextMessageData", {}).get("text")
        )
        
        if chat_id and text_message:
            ai_reply = await generate_ai_response(text_message)
            await send_whatsapp_message(chat_id, ai_reply)
            
    return {"status": "success"}

async def generate_ai_response(user_text: str) -> str:
    """Генерация ответа ИИ-агронома через Google Gemini API"""
    if not GEMINI_API_KEY:
        return "Terra.ai: Сервис временно настраивается. Напишите нам чуточку позже!"
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_text}]
            }
        ]
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=15.0)
            res_json = response.json()
            return res_json["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            print(f"Gemini API Error: {e}")
            return "Terra.ai: Произошла ошибка при обработке вашего вопроса. Попробуйте еще раз."

async def send_whatsapp_message(chat_id: str, text: str):
    """Отправка сообщения в WhatsApp через узловой хост Green API"""
    if not GREEN_API_INSTANCE or not GREEN_API_TOKEN:
        return
        
    url = f"https://7201.api.green-api.com/waInstance{GREEN_API_INSTANCE}/sendMessage/{GREEN_API_TOKEN}"
    payload = {
        "chatId": chat_id,
        "message": text
    }
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            await client.post(url, json=payload, timeout=10.0)
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")
