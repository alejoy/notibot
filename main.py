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

def obtener_enlaces(sitio):
    url = sitio["url"]
    nombre = sitio["nombre"]
    print(f"📥 Obteniendo enlaces de {nombre}...")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        enlaces = set()

        for link in soup.find_all("a", href=True):
            href = link["href"]
            is_article = False
            
            if "link_pattern_regex" in sitio:
                pattern_regex = sitio["link_pattern_regex"]
                if re.match(pattern_regex, href):
                    is_article = True
            elif "link_pattern" in sitio:
                pattern = sitio["link_pattern"]
                if pattern in href:
                    is_article = True

            if is_article:
                full_url = urljoin(url, href)
                enlaces.add(full_url)

        print(f"✅ Encontrados {len(enlaces)} enlaces únicos para {nombre}.")
        return list(enlaces)[:3]

    except requests.exceptions.RequestException as e:
        print(f"❌ Error al conectar con {url}: {e}")
        return []

def extraer_contenido(url, selector):
    print(f"   📄 Extrayendo contenido de: {url[:70]}...")
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        find_args = {}
        if 'class_' in selector:
            find_args['class_'] = selector['class_']
        if 'attrs' in selector:
            find_args['attrs'] = selector['attrs']

        contenedor = soup.find(selector['tag'], **find_args)

        if not contenedor:
            print(f"   ⚠️ No se encontró el contenedor principal. Intentando alternativas...")
            fallback_selectors = [
                {'tag': 'div', 'class_': 'content'},
                {'tag': 'div', 'class_': 'article-body'},
                {'tag': 'div', 'class_': 'post-content'},
                {'tag': 'article'},
                {'tag': 'main'}
            ]
            for fallback in fallback_selectors:
                fb_args = {}
                if 'class_' in fallback:
                    fb_args['class_'] = fallback['class_']
                contenedor = soup.find(fallback['tag'], **fb_args)
                if contenedor:
                    print(f"   ✅ Usando selector alternativo: {fallback}")
                    break
            if not contenedor:
                print(f"   ❌ No se pudo encontrar contenido con ningún selector")
                return None

        for script in contenedor(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        texto = ' '.join(contenedor.get_text(separator=' ', strip=True).split())
        if len(texto) < 100:
            print(f"   ⚠️ Contenido muy corto ({len(texto)} caracteres)")
            return None

        return texto

    except requests.exceptions.RequestException as e:
        print(f"❌ Error al extraer contenido de {url}: {e}")
        return None

def resumir_con_tono(texto, tono):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = TONOS.get(tono, "Resumí el siguiente texto de forma clara y breve.") + f"\n\n{texto[:4000]}"

    data = {
        "model": "mistralai/mixtral-8x7b-instruct",
        "messages": [
            {"role": "system", "content": f"Sos un analista político con enfoque {tono}."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 300
    }

    for intento in range(3):
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=40
            )
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content'].strip()
            else:
                print(f"⚠️ Intento {intento+1} fallido: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"⚠️ Error en intento {intento+1}: {e}")
        time.sleep(2)

    return "[No se pudo generar resumen]"

def ejecutar_bot():
    print("🤖 Iniciando bot de noticias...")

    chat_ids = obtener_chat_ids()
    if not chat_ids:
        print("⚠️ No hay suscriptores registrados.")
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
                    print(f"   🎭 Generando resumen con tono: {tono}")
                    resumen = resumir_con_tono(contenido, tono)
                    resumenes.append(f"🗣 *{tono.capitalize()}*\n{resumen}")

                mensaje = f"📰 *{sitio['nombre']} - Comparativa de enfoques*\n\n" + \
                          "\n\n".join(resumenes) + \
                          f"\n\n🔗 {link}"

                for chat_id in chat_ids:
                    enviar_telegram(mensaje, chat_id)
                time.sleep(5)
            else:
                print("⚠️ No se pudo extraer contenido del artículo.")

    print("\n🏁 Bot finalizado.")

if __name__ == "__main__":
    ejecutar_bot()
