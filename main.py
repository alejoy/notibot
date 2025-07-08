import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import re
import os
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Telegram Config - usar variables de entorno
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

# Validar que existan las variables
if not TELEGRAM_BOT_TOKEN:
    logger.error("❌ Falta TELEGRAM_BOT_TOKEN en variables de entorno")
    exit(1)
    
if not OPENROUTER_API_KEY:
    logger.error("❌ Falta OPENROUTER_API_KEY en variables de entorno")
    exit(1)

logger.info("✅ Variables de entorno cargadas correctamente")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

# Configuración de sitios
SITIOS = [
    {
        "nombre": "Río Negro",
        "url": "https://www.rionegro.com.ar/politica/",
        "content_selector": {
            "tag": "div",
            "class_": "newsfull__body"
        },
        "link_pattern": "/politica/"
    },
    {
        "nombre": "Página/12",
        "url": "https://www.pagina12.com.ar/secciones/el-pais",
        "content_selector": {
            "tag": "div",
            "class_": "article-main-content"
        },
        "link_pattern_regex": r"^\/\d{6,}-.+"
    },
    {
        "nombre": "La Nación",
        "url": "https://www.lanacion.com.ar/politica/",
        "content_selector": {
            "tag": "div",
            "class_": "com-paragraph"
        },
        "link_pattern": "/politica/"
    },
    {
        "nombre": "Infobae",
        "url": "https://www.infobae.com/politica/",
        "content_selector": {
            "tag": "figcaption",
            "class_": "article-figcaption-img"
        },
        "link_pattern": "/politica/"
    }
]

# Configuración de tonos
TONOS = {
    "libertario": "Analizá esta noticia desde una perspectiva libertaria, enfocándote en la libertad individual, el libre mercado y la limitación del Estado.",
    "crítico al neoliberalismo": "Analizá esta noticia con una perspectiva crítica al neoliberalismo, enfocándote en desigualdades sociales y el rol del Estado en la protección social.",
    "neutral informativo": "Resumí esta noticia de forma objetiva y neutral, presentando los hechos principales sin sesgo político."
}

TONOS_POSIBLES = ["libertario", "crítico al neoliberalismo", "neutral informativo"]

# --- FUNCIONES ---

def obtener_chat_ids():
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/subscribers?select=chat_id,nombre",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
        )
        if response.status_code == 200:
            datos = response.json()
            return [(item["chat_id"], item.get("nombre", "")) for item in datos]
        else:
            print(f"❌ Error al obtener chat_ids: {response.text}")
            return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def enviar_telegram(mensaje, chat_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print(f"✅ Mensaje enviado a {chat_id}")
            return True
        else:
            print(f"❌ Error enviando mensaje: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Excepción al enviar mensaje por Telegram: {e}")
        return False

# (Resto de funciones como obtener_enlaces, extraer_contenido, resumir_con_tono se mantienen igual)

# --- EJECUCIÓN ---
def ejecutar_bot():
    print("🤖 Iniciando bot de noticias...")

    chat_ids = obtener_chat_ids()
    if not chat_ids:
        print("⚠️ No hay suscriptores registrados en Supabase")
        return

    for sitio in SITIOS:
        print(f"\n🌐 Procesando sitio: {sitio['nombre']}")
        enlaces = obtener_enlaces(sitio)

        if not enlaces:
            print(f"No se pudieron obtener enlaces para {sitio['nombre']}. Saltando al siguiente.\n")
            continue

        for link in enlaces:
            print(f"🔗 Procesando: {link}")
            contenido = extraer_contenido(link, sitio['content_selector'])

            if contenido:
                resumenes = []

                for tono in TONOS_POSIBLES:
                    print(f"   🎝 Generando resumen con tono: {tono}")
                    resumen = resumir_con_tono(contenido, tono)

                    if resumen and resumen != "[No se pudo generar resumen]":
                        resumenes.append(f"🗣 *{tono.capitalize()}*\n{resumen}")
                    else:
                        resumenes.append(f"🗣 *{tono.capitalize()}*\n[No se pudo generar resumen]")

                mensaje = f"📰 *{sitio['nombre']} - Comparativa de enfoques*\n\n" + \
                          "\n\n".join(resumenes) + \
                          f"\n\n🔗 {link}"

                for chat_id, nombre in chat_ids:
                    mensaje_personalizado = f"Hola {nombre},\n\n{mensaje}"
                    if enviar_telegram(mensaje_personalizado, chat_id):
                        print(f"✅ Enviado a {chat_id} ({nombre})")
                    else:
                        print(f"❌ Falló envío a {chat_id} ({nombre})")

                time.sleep(5)
            else:
                print("⚠️ No se pudo extraer contenido del artículo.")

    print("\n🏁 Bot finalizado.")

if __name__ == "__main__":
    ejecutar_bot()

