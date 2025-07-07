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
    first_name = chat.get("first_name") or ""
    username = chat.get("username") or ""
    user_display = first_name or username or "usuario"
    text = message.get("text", "")

    if text in ("/start", "/subscribe"):
        respuesta = f"Ya estás suscripto, {user_display}."

        # Consultar si ya está suscripto
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/subscribers?chat_id=eq.{chat_id}",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
        )

        if r.status_code == 200 and len(r.json()) == 0:
            # No está, lo agregamos con el nombre
            insert = requests.post(
                f"{SUPABASE_URL}/rest/v1/subscribers",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                },
                json={"chat_id": chat_id, "nombre": user_display}
            )

            if insert.status_code == 201:
                respuesta = f"¡Suscripción confirmada, {user_display}! Recibirás las noticias."

        # Enviar respuesta
        resp_telegram = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={"chat_id": chat_id, "text": respuesta}
        )
        print(f"Telegram sendMessage status: {resp_telegram.status_code}")

    return {"ok": True}

