import telebot
from telebot import types
from datetime import datetime
import schedule
import time
import random
import json
import os
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Tu token del BotFather
TOKEN = os.environ.get('TOKEN')
bot = telebot.TeleBot(TOKEN)

# Tu ID de chat
CHAT_ID = os.environ.get('CHAT_ID')

# Archivo para guardar el estado de elementos usados
ESTADO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'estado_usado.json')
SUGERENCIAS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sugerencias.json')
VOTOS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'votos.json')
PUNTOS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'puntos.json')

def cargar_estado():
    """Carga el estado de elementos ya usados"""
    if os.path.exists(ESTADO_FILE):
        with open(ESTADO_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'palabras': [], 'refranes': [], 'frases': []}

def guardar_estado(estado):
    """Guarda el estado de elementos usados"""
    with open(ESTADO_FILE, 'w', encoding='utf-8') as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)

def cargar_sugerencias():
    """Carga las sugerencias guardadas"""
    if os.path.exists(SUGERENCIAS_FILE):
        with open(SUGERENCIAS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def guardar_sugerencia(usuario, texto):
    """Guarda una nueva sugerencia"""
    sugerencias = cargar_sugerencias()
    sugerencias.append({
        'usuario': usuario,
        'texto': texto,
        'fecha': datetime.now().strftime("%d/%m/%Y %H:%M")
    })
    with open(SUGERENCIAS_FILE, 'w', encoding='utf-8') as f:
        json.dump(sugerencias, f, ensure_ascii=False, indent=2)

def cargar_votos():
    """Carga los votos guardados"""
    if os.path.exists(VOTOS_FILE):
        with open(VOTOS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def guardar_votos(votos):
    """Guarda los votos"""
    with open(VOTOS_FILE, 'w', encoding='utf-8') as f:
        json.dump(votos, f, ensure_ascii=False, indent=2)

def registrar_voto(fecha, user_id, voto):
    """Registra un voto (True=👍, False=👎). Retorna (exito, ya_voto)"""
    votos = cargar_votos()
    if fecha not in votos:
        votos[fecha] = {'up': [], 'down': []}
    
    # Verificar si ya votó
    if user_id in votos[fecha]['up'] or user_id in votos[fecha]['down']:
        return False, True
    
    if voto:
        votos[fecha]['up'].append(user_id)
    else:
        votos[fecha]['down'].append(user_id)
    
    guardar_votos(votos)
    return True, False

def obtener_conteo_votos(fecha):
    """Obtiene el conteo de votos para una fecha"""
    votos = cargar_votos()
    if fecha not in votos:
        return 0, 0
    return len(votos[fecha]['up']), len(votos[fecha]['down'])

def cargar_puntos():
    """Carga las puntuaciones del quiz"""
    if os.path.exists(PUNTOS_FILE):
        with open(PUNTOS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def guardar_puntos(puntos):
    """Guarda las puntuaciones"""
    with open(PUNTOS_FILE, 'w', encoding='utf-8') as f:
        json.dump(puntos, f, ensure_ascii=False, indent=2)

def sumar_punto(user_id, nombre):
    """Suma un punto al usuario"""
    puntos = cargar_puntos()
    user_key = str(user_id)
    if user_key not in puntos:
        puntos[user_key] = {'nombre': nombre, 'puntos': 0}
    puntos[user_key]['puntos'] += 1
    puntos[user_key]['nombre'] = nombre
    guardar_puntos(puntos)
    return puntos[user_key]['puntos']

def parsear_palabra(texto):
    """Separa 'Palabra: definición' en (palabra, definición)"""
    if ':' in texto:
        partes = texto.split(':', 1)
        return partes[0].strip(), partes[1].strip()
    return texto, ""

def generar_quiz():
    """Genera un quiz con una palabra y 4 opciones"""
    palabra_completa = random.choice(PALABRAS_CURIOSAS)
    palabra, definicion_correcta = parsear_palabra(palabra_completa)
    
    # Obtener 3 definiciones incorrectas
    otras = [p for p in PALABRAS_CURIOSAS if p != palabra_completa]
    incorrectas = random.sample(otras, min(3, len(otras)))
    opciones_incorrectas = [parsear_palabra(p)[1] for p in incorrectas]
    
    # Mezclar opciones
    todas_opciones = [definicion_correcta] + opciones_incorrectas
    random.shuffle(todas_opciones)
    indice_correcto = todas_opciones.index(definicion_correcta)
    
    return palabra, todas_opciones, indice_correcto

def obtener_sin_repetir(lista, usados_key):
    """Obtiene un elemento aleatorio sin repetir hasta agotar la lista"""
    estado = cargar_estado()
    usados = estado.get(usados_key, [])
    
    disponibles = [item for item in lista if item not in usados]
    
    if not disponibles:
        usados = []
        disponibles = lista.copy()
    
    elegido = random.choice(disponibles)
    usados.append(elegido)
    estado[usados_key] = usados
    guardar_estado(estado)
    
    return elegido

# Tus contenidos
PALABRAS_CURIOSAS = [
    "Petricor: el olor de la lluvia al caer sobre tierra seca",
    "Procrastinar: posponer tareas constantemente",
    "Serendipia: descubrimiento afortunado e inesperado",
    "Indócil: que no tiene la cualidad de ser obediente",
    "Alipende: Se refiere a una persona pilla, traviesa o 'de una pieza' ",
    "Arrebol: Color rojo, especialmente el de las nubes iluminadas por los rayos del sol o el del rostro",
    "Inefable: Que no puede explicar con palabras",
    "Melifluo: Dulce, suave, delicado y tierno en el trato o en la manera de hablar",
    "Limerencia: Estado mental involuntario de atracción romántica obsesiva",
    "Bonhomía: Afabilidad, sencillez y bondad en el carácter",
    "Ademán: Movimiento o actitud del cuerpo o de alguna parte suya con que se manifiesta disposición, intención o sentimiento",
    "Ataraxia: Imperturbabilidad, serenidad",
]

REFRANES = [
    "A quien madruga, Dios le ayuda",
    "Más vale un backup a tiempo que cien disculpas después",
    "No por mucho madrugar amanece más temprano",
    "No es oro todo lo que aparece en Instagram",
    "Más vale pájaro en mano que ciento volando",
    "Hecha la ley, hecha la VPN",
    "Dime qué posteas y te diré quién eres",
    "Mal de muchos, consuelo de tontos",
    "Gato escaldado del agua fría huye",
    "La pereza anda tan despacio que la pobreza la alcanza",
    "No hay atajo sin trabajo",
    "No vendas la piel del oso antes de cazarlo",
    "Nadie es profeta en su tierra",
    "No se ganó Zamora en una hora",
    "El que tropieza dos veces con la misma piedra, merece que se le caiga encima",
    "Golondrina que por San Blas ves, o se helará o hambre tendrá",
    "Padres vendedores, hijos gastadores; nietos pordioseros",
    "El que guarda, halla",
    "Cara bonita, poco dura",
    "Desgracia compartida, menos sentida",
    "A otro perro con ese hueso",
]

FRASES_AMIGOS = [
    "Sé que mi destino está escrito - Mi abuela",
    "'Llego tarde' - Maru Espasandín (cada vez que quedas con ella)",
    "Estaba tendiendo la ropa - Tania Eiros cada vez que hizo el amor",
    "Follo, fumo y como cerdo, soy un partidazo para cualquier musulmán - Cris Flores Senegal 2025",
    "Si vienes te enseño mi pimiento - Iván V.S.",
    "Somos escarabajos peloteros creando montañas de estiércol - Raquel F.S.",
    "Cerra sesión e volve a entrar - Manuel Reyes",
    "Hoy vi un video de un trio, de cómo gestionaban sus gastos y se ahorran pasta - Alicia González",
    "Esto es el chiringuito de peine - Raquel F.S.",
    "'¡Furcia!' (mientras aplasta una hormiga) - Loreto M.S. ",
    "Al final en este  país la opción más realista de tener una vivienda es ser okupa- Lucía Fisio",
    "Pasarlo bien, venga ciao - Carliños",
]

def obtener_efemeride():
    """Obtiene una efeméride del día desde Wikipedia API"""
    try:
        hoy = datetime.now()
        url = f"https://es.wikipedia.org/api/rest_v1/feed/onthisday/events/{hoy.month}/{hoy.day}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            eventos = data.get('events', [])
            if eventos:
                evento = random.choice(eventos[:10])  # De los 10 más relevantes
                return f"{evento.get('year', '')}: {evento.get('text', 'Sin datos')}"
    except:
        pass
    return None

def obtener_dia_internacional():
    """Obtiene el día internacional de hoy"""
    try:
        hoy = datetime.now()
        url = f"https://www.diasinternacionales.com/api/v1/days?month={hoy.month}&day={hoy.day}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return data[0].get('name', None)
    except:
        pass
    # Fallback: días internacionales más conocidos
    dias_conocidos = {
        (1, 1): "Día de la Paz Mundial",
        (1, 30): "Día internacional de la no violencia y paz (aunque también es el día del Croissant)",
        (1, 31): "Día internacional de la cebra",
        (2, 1): "Día mundial del Galgo",
        (2, 2): "Día de la Marmota",
        (2, 3): "Día internacional del abogado",
        (2, 4): "Día contra el cáncer",
        (2, 9): "Día mundial de la pizza",
        (2, 10): "Día internacional de internet seguro",
        (2, 14): "Día de San Valentín",
        (3, 8): "Día Internacional de la Mujer",
        (4, 22): "Día de la Tierra",
        (5, 1): "Día del Trabajo",
        (6, 5): "Día del Medio Ambiente",
        (10, 31): "Halloween",
        (12, 25): "Navidad",
    }
    return dias_conocidos.get((hoy.month, hoy.day), None)

def mensaje_diario():
    """Genera el mensaje del día"""
    palabra = obtener_sin_repetir(PALABRAS_CURIOSAS, 'palabras')
    refran = obtener_sin_repetir(REFRANES, 'refranes')
    frase = obtener_sin_repetir(FRASES_AMIGOS, 'frases')
    efemeride = obtener_efemeride()
    dia_internacional = obtener_dia_internacional()
    
    mensaje = f"""
 *PERLA DEL DÍA*

📚 *Palabra curiosa:*
{palabra}

🎯 *Refrán:*
{refran}

😂 *Frase mítica:*
{frase}
"""
    
    if dia_internacional:
        mensaje += f"\n🌐 *Hoy se celebra:*\n{dia_internacional}\n"
    
    if efemeride:
        mensaje += f"\n📅 *Tal día como hoy:*\n{efemeride}\n"
    
    mensaje += f"\n_{datetime.now().strftime('%d/%m/%Y')}_"
    
    return mensaje

def crear_botones_voto(fecha):
    """Crea los botones de votación"""
    markup = types.InlineKeyboardMarkup()
    up, down = obtener_conteo_votos(fecha)
    btn_up = types.InlineKeyboardButton(f"👍 {up}", callback_data=f"voto_up_{fecha}")
    btn_down = types.InlineKeyboardButton(f"👎 {down}", callback_data=f"voto_down_{fecha}")
    markup.add(btn_up, btn_down)
    return markup

def enviar_mensaje():
    """Envía el mensaje al grupo"""
    try:
        fecha = datetime.now().strftime("%Y-%m-%d")
        bot.send_message(
            CHAT_ID, 
            mensaje_diario(), 
            parse_mode='Markdown',
            reply_markup=crear_botones_voto(fecha)
        )
        print(f"Mensaje enviado: {datetime.now()}")
    except Exception as e:
        print(f"Error: {e}")

# Programar envío diario a las 9:00 AM
schedule.every().day.at("09:00").do(enviar_mensaje)

@bot.message_handler(commands=['start', 'hola'])
def send_welcome(message):
    bienvenida = """
🦪 *¡Ey, bienvenido/a al Bot de las Perlas!* 🦪

Soy tu dealer diario de sabiduría random y frasecitas que nadie pidió pero todos necesitamos.

*¿Qué hago yo aquí?*
📚 Cada día a las 9:00 te suelto una *palabra curiosa* para que parezcas más listo/a en las conversaciones
🎯 Un *refrán* (algunos clásicos, otros del siglo XXI)
😂 Una *frase mítica* de los colegas (sí, esas que no deberían salir del grupo)

*Comandos disponibles:*
/ahora - Si no puedes esperar a mañana, ¡perla instantánea!
/desafio - ¡Pon a prueba tu vocabulario!
/ranking - Top 10 del desafío
/sugerir [frase] - Sugiere una frase mítica para añadir

Prepárate para la cultura... o algo parecido 🤷‍♀️
"""
    bot.reply_to(message, bienvenida, parse_mode='Markdown')
    # Imprime el chat_id para configurarlo
    print(f"Chat ID: {message.chat.id}")

@bot.message_handler(commands=['michat'])
def obtener_chat_id(message):
    chat_id = message.chat.id
    bot.reply_to(message, f"Tu Chat ID es: {chat_id}")
    print(f"Chat ID: {chat_id}")

@bot.message_handler(commands=['ahora'])
def send_now(message):
    fecha = datetime.now().strftime("%Y-%m-%d")
    bot.send_message(
        message.chat.id, 
        mensaje_diario(), 
        parse_mode='Markdown',
        reply_markup=crear_botones_voto(fecha)
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('voto_'))
def handle_voto(call):
    """Maneja los votos de los usuarios"""
    partes = call.data.split('_')
    tipo_voto = partes[1]  # 'up' o 'down'
    fecha = partes[2]
    user_id = call.from_user.id
    
    voto = (tipo_voto == 'up')
    exito, ya_voto = registrar_voto(fecha, user_id, voto)
    
    if ya_voto:
        bot.answer_callback_query(call.id, "⚠️ Ya votaste hoy!")
        return
    
    # Actualizar botones con nuevo conteo
    bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=crear_botones_voto(fecha)
    )
    
    emoji = "👍" if voto else "👎"
    bot.answer_callback_query(call.id, f"{emoji} ¡Voto registrado!")

@bot.message_handler(commands=['sugerir'])
def sugerir_frase(message):
    texto = message.text.replace('/sugerir', '').strip()
    if not texto:
        bot.reply_to(message, "✏️ Usa: /sugerir Tu frase mítica - Autor")
        return
    
    usuario = message.from_user.first_name or "Anónimo"
    guardar_sugerencia(usuario, texto)
    bot.reply_to(message, f"✅ ¡Gracias {usuario}! Tu sugerencia ha sido guardada para revisión.")

@bot.message_handler(commands=['versugerencias'])
def ver_sugerencias(message):
    sugerencias = cargar_sugerencias()
    if not sugerencias:
        bot.reply_to(message, "📭 No hay sugerencias pendientes.")
        return
    
    texto = "📬 *Sugerencias pendientes:*\n\n"
    for i, s in enumerate(sugerencias[-10:], 1):  # Últimas 10
        texto += f"{i}. _{s['texto']}_\n   👤 {s['usuario']} - {s['fecha']}\n\n"
    bot.reply_to(message, texto, parse_mode='Markdown')

@bot.message_handler(commands=['desafio'])
def enviar_desafio(message):
    """Envía un desafío de vocabulario"""
    palabra, opciones, indice_correcto = generar_quiz()
    
    texto = f"🧠 *DESAFÍO: ¿Qué significa...*\n\n📝 *{palabra}*?"
    
    markup = types.InlineKeyboardMarkup()
    letras = ['A', 'B', 'C', 'D']
    for i, opcion in enumerate(opciones):
        # Acortar opción si es muy larga
        opcion_corta = opcion[:50] + "..." if len(opcion) > 50 else opcion
        btn = types.InlineKeyboardButton(
            f"{letras[i]}) {opcion_corta}", 
            callback_data=f"desafio_{i}_{indice_correcto}"
        )
        markup.add(btn)
    
    bot.send_message(message.chat.id, texto, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('desafio_'))
def handle_desafio(call):
    """Maneja las respuestas del desafío"""
    partes = call.data.split('_')
    respuesta = int(partes[1])
    correcta = int(partes[2])
    
    if respuesta == correcta:
        nombre = call.from_user.first_name or "Anónimo"
        puntos_total = sumar_punto(call.from_user.id, nombre)
        bot.answer_callback_query(call.id, f"✅ ¡Correcto! Llevas {puntos_total} pts")
        bot.edit_message_text(
            f"✅ *¡{nombre} acertó!*\n\n" + call.message.text.replace("🧠", "🎉"),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode='Markdown'
        )
    else:
        bot.answer_callback_query(call.id, "❌ Incorrecto, ¡intenta otro desafío!")

@bot.message_handler(commands=['ranking'])
def ver_ranking(message):
    """Muestra el top 10 del desafío"""
    puntos = cargar_puntos()
    if not puntos:
        bot.reply_to(message, "📊 Aún no hay puntuaciones. ¡Usa /desafio para jugar!")
        return
    
    # Ordenar por puntos
    ranking = sorted(puntos.items(), key=lambda x: x[1]['puntos'], reverse=True)[:10]
    
    texto = "🏆 *RANKING DEL DESAFÍO*\n\n"
    medallas = ['🥇', '🥈', '🥉']
    for i, (user_id, data) in enumerate(ranking):
        medalla = medallas[i] if i < 3 else f"{i+1}."
        texto += f"{medalla} {data['nombre']}: *{data['puntos']}* pts\n"
    
    bot.reply_to(message, texto, parse_mode='Markdown')

# Servidor HTTP simple para Render
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot running')
    def log_message(self, format, *args):
        pass  # Silenciar logs HTTP

def run_health_server():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"Health server en puerto {port}")
    server.serve_forever()

# Mantener el bot corriendo
def main():
    print("Bot iniciado...")
    # Iniciar servidor HTTP para Render PRIMERO
    threading.Thread(target=run_health_server, daemon=True).start()
    time.sleep(2)  # Dar tiempo al servidor HTTP para iniciar
    print("Health server listo")
    # Iniciar el bot
    threading.Thread(target=bot.infinity_polling, daemon=True).start()
    print("Bot polling iniciado")
    
    # Ejecutar el schedule
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    main()