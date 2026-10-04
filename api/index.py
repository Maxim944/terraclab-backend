import os
from fastapi import FastAPI, Request
import httpx

# 1. Инициализация FastAPI для Vercel Serverless
app = FastAPI(title="Terra.ai API", version="1.0.0")

# 2. Чтение переменных окружения с подстраховкой разных наименований
GREEN_API_INSTANCE = (
    os.getenv("GREEN_API_INSTANCE") or 
    os.getenv("GREEN_API_INSTANCE_ID") or 
    ""
)

GREEN_API_TOKEN = (
    os.getenv("GREEN_API_TOKEN") or 
    os.getenv("ЗЕЛЕНЫЙ_API_TOKEN") or 
    ""
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# 3. Инструкция (системный промпт) для ИИ-агронома
SYSTEM_PROMPT = """Ты — Terra.ai, персональный ИИ-агроном и эксперт по растениеводству. 
Твоя задача — давать четкие, практичные и дружелюбные советы по уходу за растениями, борьбе с вредителями, 
подкормке и поливу. Отвечай кратко, емко и адаптировано под мессенджер WhatsApp."""

# Маршруты проверки статуса сервера (Health Check)
@app.get("/api")
@app.get("/api/health")
def health_check():
    return {
        "status": "ok", 
        "service": "Terra.ai Agronomist API", 
        "platform": "Vercel Serverless"
    }

# Маршруты приема вебхуков от WhatsApp / Green API
@app.post("/api/webhook/whatsapp")
@app.post("/api/index.py")
@app.post("/api")
@app.post("/")
async def whatsapp_webhook(request: Request):
    """Прием входящих сообщений из WhatsApp через Green API"""
    try:
        data = await request.json()
    except Exception:
        return {"status": "error", "message": "Invalid JSON"}
    
    type_webhook = data.get("typeWebhook")
    
    # Обрабатываем только входящие текстовые сообщения
    if type_webhook == "incomingMessageReceived":
        message_data = data.get("messageData", {})
        sender_data = data.get("senderData", {})
        
        chat_id = sender_data.get("chatId")
        
        # Извлекаем текст из обычных или расширенных сообщений
        text_message = (
            message_data.get("textMessageData", {}).get("textMessage") or
            message_data.get("extendedTextMessageData", {}).get("text")
        )
        
        if chat_id and text_message:
            print(f"[Входящее] Чат: {chat_id} | Текст: {text_message}")
            ai_reply = await generate_ai_response(text_message)
            await send_whatsapp_message(chat_id, ai_reply)
            
    return {"status": "success"}

async def generate_ai_response(user_text: str) -> str:
    """Генерация ответа ИИ-агронома через Google Gemini API с автоподбором модели"""
    if not GEMINI_API_KEY:
        print("[Ошибка] GEMINI_API_KEY не найден в переменных Vercel!")
        return "Terra.ai: Сервис временно настраивается (отсутствует ключ API)."
        
    # Список моделей для автоматического перебора при 404
    models_to_try = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-2.0-flash",
        "gemini-1.5-pro"
    ]
    
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
        for model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            try:
                response = await client.post(url, json=payload, timeout=20.0)
                res_json = response.json()
                
                if response.status_code == 200:
                    if "candidates" in res_json and len(res_json["candidates"]) > 0:
                        candidate = res_json["candidates"][0]
                        parts = candidate.get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            print(f"[Успех Gemini] Модель {model} ответила успешно!")
                            return parts[0]["text"]
                elif response.status_code == 404:
                    print(f"[404 Gemini] Модель {model} не найдена для этого ключа, пробуем следующую...")
                    continue
                else:
                    print(f"[Ошибка Gemini API {response.status_code}]: {res_json}")
                    return "Terra.ai: Ошибка обращения к ИИ-сервису."
            except Exception as e:
                print(f"[Исключение Gemini на {model}]: {e}")
                
    return "Terra.ai: Не удалось сформировать ответ. Попробуйте еще раз."

async def send_whatsapp_message(chat_id: str, text: str):
    """Отправка ответа пользователю в WhatsApp через Green API"""
    if not GREEN_API_INSTANCE or not GREEN_API_TOKEN:
        print("[Ошибка] Не найдены GREEN_API_INSTANCE или GREEN_API_TOKEN!")
        return
        
    url = f"https://7201.api.green-api.com/waInstance{GREEN_API_INSTANCE}/sendMessage/{GREEN_API_TOKEN}"
    payload = {
        "chatId": chat_id,
        "message": text
    }
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            res = await client.post(url, json=payload, timeout=10.0)
            print(f"[Отправка в WhatsApp] Статус Green API: {res.status_code}")
        except Exception as e:
            print(f"[Ошибка отправки в WhatsApp]: {e}")
