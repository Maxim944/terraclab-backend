import os
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI(title="Terra.ai API", version="1.0.0")

# Переменные окружения из Vercel Dashboard
GREEN_API_INSTANCE = os.getenv("GREEN_API_INSTANCE", "")
GREEN_API_TOKEN = os.getenv("GREEN_API_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

SYSTEM_PROMPT = """Ты — Terra.ai, персональный ИИ-агроном и эксперт по растениеводству. 
Твоя задача — давать четкие, практичные и дружелюбные советы по уходу за растениями, борьбе с вредителями, 
подкормке и поливу. Отвечай кратко, емко и адаптировано под мессенджер WhatsApp."""

@app.get("/api")
@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Terra.ai Agronomist API", "platform": "Vercel Serverless"}

@app.post("/api/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """Прием входящих сообщений из WhatsApp через Green API"""
    data = await request.json()
    
    # Проверка типа события (входящее текстовое сообщение)
    type_webhook = data.get("typeWebhook")
    if type_webhook == "incomingMessageReceived":
        message_data = data.get("messageData", {})
        sender_data = data.get("senderData", {})
        
        chat_id = sender_data.get("chatId")
        text_message = message_data.get("textMessageData", {}).get("textMessage")
        
        if chat_id and text_message:
            # Обработка ответа ИИ
            ai_reply = await generate_ai_response(text_message)
            # Отправка ответа пользователю
            await send_whatsapp_message(chat_id, ai_reply)
            
    return {"status": "success"}

async def generate_ai_response(user_text: str) -> str:
    """Генерация ответа ИИ-агронома"""
    if not OPENAI_API_KEY:
        return "Terra.ai: Сервис временно настраивается. Напишите нам чуточку позже!"
        
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_text}
                    ],
                    "max_tokens": 500
                },
                timeout=15.0
            )
            res_json = response.json()
            return res_json["choices"][0]["message"]["content"]
        except Exception as e:
            return "Terra.ai: Произошла ошибка при обработке вашего вопроса. Попробуйте еще раз."

async def send_whatsapp_message(chat_id: str, text: str):
    """Отправка сообщения в WhatsApp через Green API"""
    if not GREEN_API_INSTANCE or not GREEN_API_TOKEN:
        return
        
    url = f"https://api.green-api.com/waInstance{GREEN_API_INSTANCE}/sendMessage/{GREEN_API_TOKEN}"
    payload = {
        "chatId": chat_id,
        "message": text
    }
    
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload, timeout=10.0)
