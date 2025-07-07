import os
import requests
from fastapi import FastAPI, Request

app = FastAPI()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

@app.get("/")
def root():
    return {"status": "ok", "message": "✅ Webhook activo y funcionando"}

@app.post("/")
async def telegram_webhook(request: Request):
    data = await request.json()
    print("📩 Datos recibidos del webhook:", data)

    message = data.get("message")
    if not message:
        return {"ok": True}

    chat = message.get("chat", {})
    chat_id = str(chat.get("id"))
    text = message.get("text", "")

    if text in ("/start", "/subscribe"):
        respuesta = "Ya estás suscripto."

        # Verificar si ya está suscripto
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/subscribers?chat_id=eq.{chat_id}",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
        )
        if r.status_code == 200 and len(r.json()) == 0:
            # No existe, lo agregamos
            insert = requests.post(
                f"{SUPABASE_URL}/rest/v1/subscribers",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                },
                json={"chat_id": chat_id}
            )
            print(f"Insert status: {insert.status_code}, response: {insert.text}")
            if insert.status_code == 201:
                respuesta = "¡Suscripción confirmada! Recibirás las noticias."

        # Enviar respuesta por Telegram
        try:
            url_telegram = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN.strip()}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": respuesta
            }

            print(f"📡 Enviando mensaje a: {url_telegram}")
            print(f"📨 Datos: {payload}")

            resp_telegram = requests.post(url_telegram, data=payload)
            print(f"✅ Estado respuesta Telegram: {resp_telegram.status_code}")
            print(f"🧾 Respuesta completa: {resp_telegram.text}")

            if resp_telegram.status_code != 200:
                print("⚠️ Error al enviar mensaje de Telegram")
        except Exception as e:
            print(f"❌ Excepción al enviar mensaje de Telegram: {e}")

    return {"ok": True}
