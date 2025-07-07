from telegram.ext import Updater, CommandHandler
import os

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUBSCRIBERS_FILE = "subscribers.txt"

def start(update, context):
    chat_id = str(update.message.chat_id)
    
    # Verificar si ya está suscripto
    if os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, 'r') as f:
            if chat_id in f.read():
                update.message.reply_text("Ya estás suscripto ✅")
                return
    
    # Guardar chat_id
    with open(SUBSCRIBERS_FILE, 'a') as f:
        f.write(chat_id + "\n")
    
    update.message.reply_text("¡Gracias por suscribirte! Vas a recibir los resúmenes diarios 🗞️")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    updater.start_polling()
    print("🤖 Bot escuchando /start...")
    updater.idle()

if __name__ == "__main__":
    main()
