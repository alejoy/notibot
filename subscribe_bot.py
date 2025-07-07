import os
import time
import requests

# Archivo donde se guardan los chat_id de los suscriptores
SUBSCRIBERS_FILE = "subscribers.txt"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    print("❌ Falta TELEGRAM_BOT_TOKEN en variables de entorno.")
    exit(1)

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def get_updates(offset=None):
    """Consulta actualizaciones nuevas desde Telegram"""
    url = f"{BASE_URL}/getUpdates"
    params = {"timeout": 10}
    if offset:
        params["offset"] = offset
    try:
        response = requests.get(url, params=params, timeout=15)
        return response.json()
    except Exception as e:
        print(f"❌ Error al obtener updates: {e}")
        return None

def send_message(chat_id, text):
    """Envía un mensaje al chat"""
    url = f"{BASE_URL}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"❌ Error al enviar mensaje a {chat_id}: {e}")

def load_subscribers():
    """Carga los chat_id suscriptos desde archivo"""
    if not os.path.exists(SUBSCRIBERS_FILE):
        return set()
    with open(SUBSCRIBERS_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip().isdigit())

def save_subscriber(chat_id):
    """Guarda un nuevo chat_id si no existe"""
    subscribers = load_subscribers()
    if str(chat_id) not in subscribers:
        with open(SUBSCRIBERS_FILE, "a") as f:
            f.write(f"{chat_id}\n")
        print(f"✅ Nuevo suscriptor agregado: {chat_id}")
    else:
        print(f"ℹ️ Usuario ya estaba suscripto: {chat_id}")

def main():
    print("🤖 Esperando comandos /start de usuarios...")
    last_update_id = None
    while True:
        updates = get_updates(offset=last_update_id)
        if updates and updates.get("ok"):
            for result in updates["result"]:
                last_update_id = result["update_id"] + 1
                message = result.get("message")
                if not message:
                    continue

                text = message.get("text")
                chat_id = message["chat"]["id"]

                if text and text.strip().lower() == "/start":
                    save_subscriber(chat_id)
                    send_message(chat_id, "✅ Te has suscripto al bot de noticias. Recibirás actualizaciones automáticamente.")
        time.sleep(5)

if __name__ == "__main__":
    main()
