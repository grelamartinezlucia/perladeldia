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
from dias_internacionales import DIAS_INTERNACIONALES
from horoscopo import obtener_horoscopo, listar_signos
from contenido import PALABRAS_CURIOSAS, REFRANES, FRASES_AMIGOS
from efemerides import EFEMERIDES

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
USUARIOS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'usuarios.json')

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

def cargar_usuarios():
    """Carga el registro de usuarios"""
    if os.path.exists(USUARIOS_FILE):
        with open(USUARIOS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def registrar_usuario(user):
    """Registra o actualiza un usuario"""
    usuarios = cargar_usuarios()
    user_key = str(user.id)
    usuarios[user_key] = {
        'nombre': user.first_name or 'Sin nombre',
        'username': user.username or None,
        'ultima_vez': datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    with open(USUARIOS_FILE, 'w', encoding='utf-8') as f:
        json.dump(usuarios, f, ensure_ascii=False, indent=2)

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

def obtener_efemeride():
    """Obtiene una efeméride del día - primero curada, luego Wikipedia como fallback"""
    hoy = datetime.now()
    
    # Primero intentar con el diccionario curado
    efemeride_curada = EFEMERIDES.get((hoy.month, hoy.day))
    if efemeride_curada:
        return efemeride_curada
    
    # Fallback: Wikipedia API
    try:
        url = f"https://es.wikipedia.org/api/rest_v1/feed/onthisday/events/{hoy.month}/{hoy.day}"
        response = requests.get(url, timeout=10, headers={'User-Agent': 'PerlaBotTelegram/1.0'})
        if response.status_code == 200:
            data = response.json()
            eventos = data.get('events', [])
            if eventos:
                evento = random.choice(eventos[:10])
                return f"{evento.get('year', '')}: {evento.get('text', 'Sin datos')}"
        print(f"Wikipedia API status: {response.status_code}")
    except Exception as e:
        print(f"Error obteniendo efeméride: {e}")
    return None

def obtener_dia_internacional():
    """Obtiene el día internacional de hoy"""
    hoy = datetime.now()
    return DIAS_INTERNACIONALES.get((hoy.month, hoy.day), None)

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
    registrar_usuario(message.from_user)
    bienvenida = """
🦪 *¡Ey, bienvenido/a al Bot de las Perlas!* 🦪

Soy tu dealer diario de sabiduría random y frasecitas que nadie pidió pero todos necesitamos.

*¿Qué hago yo aquí?*
📚 Cada día a las 10:00 te suelto una *palabra curiosa* para que parezcas más listo/a en las conversaciones
🎯 Un *refrán* (algunos clásicos, otros del siglo XXI)
😂 Una *frase mítica* de los colegas (sí, esas que no deberían salir del grupo)

*Comandos disponibles:*
/ahora - Si no puedes esperar a mañana, ¡perla instantánea!
/desafio - ¡Pon a prueba tu vocabulario!
/ranking - Top 10 del desafío
/sugerir [frase] - Sugiere una frase mítica para añadir
/horoscopo [signo] - Tu destino más absurdo

Prepárate para la cultura... o algo parecido 🤷‍♀️
"""
    bot.reply_to(message, bienvenida, parse_mode='Markdown')
    print(f"Chat ID: {message.chat.id}")

@bot.message_handler(commands=['michat'])
def obtener_chat_id(message):
    chat_id = message.chat.id
    bot.reply_to(message, f"Tu Chat ID es: {chat_id}")
    print(f"Chat ID: {chat_id}")

@bot.message_handler(commands=['ahora'])
def send_now(message):
    registrar_usuario(message.from_user)
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
    registrar_usuario(call.from_user)
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
    registrar_usuario(message.from_user)
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

@bot.message_handler(commands=['horoscopo'])
def ver_horoscopo(message):
    """Muestra el horóscopo irónico del día"""
    registrar_usuario(message.from_user)
    args = message.text.replace('/horoscopo', '').strip()
    
    if not args:
        signos = listar_signos()
        texto = "🔮 *HORÓSCOPO IRÓNICO*\n\n"
        texto += "Dime tu signo y te diré tu destino (absurdo)\n\n"
        texto += "Usa: `/horoscopo [signo]`\n\n"
        texto += "*Signos disponibles:*\n"
        texto += ", ".join(signos)
        bot.reply_to(message, texto, parse_mode='Markdown')
        return
    
    signo_nombre, prediccion = obtener_horoscopo(args)
    
    if not signo_nombre:
        bot.reply_to(message, "❌ Signo no reconocido. Prueba con: aries, tauro, geminis, cancer, leo, virgo, libra, escorpio, sagitario, capricornio, acuario, piscis")
        return
    
    texto = f"🔮 *HORÓSCOPO IRÓNICO*\n\n"
    texto += f"*{signo_nombre}*\n\n"
    texto += f"_{prediccion}_"
    
    bot.reply_to(message, texto, parse_mode='Markdown')

@bot.message_handler(commands=['desafio'])
def enviar_desafio(message):
    """Envía un desafío de vocabulario"""
    registrar_usuario(message.from_user)
    palabra, opciones, indice_correcto = generar_quiz()
    
    letras = ['A', 'B', 'C', 'D']
    texto = f"🧠 *DESAFÍO: ¿Qué significa...*\n\n📝 *{palabra}*?\n"
    
    for i, opcion in enumerate(opciones):
        texto += f"\n{letras[i]}) {opcion}"
    
    markup = types.InlineKeyboardMarkup(row_width=4)
    botones = [
        types.InlineKeyboardButton(letra, callback_data=f"desafio_{i}_{indice_correcto}")
        for i, letra in enumerate(letras)
    ]
    markup.add(*botones)
    
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

@bot.message_handler(commands=['stats'])
def ver_stats(message):
    """Muestra estadísticas del bot"""
    votos = cargar_votos()
    puntos = cargar_puntos()
    
    # Usuarios únicos que han votado
    usuarios_votos = set()
    total_likes = 0
    total_dislikes = 0
    for fecha, data in votos.items():
        usuarios_votos.update(data.get('up', []))
        usuarios_votos.update(data.get('down', []))
        total_likes += len(data.get('up', []))
        total_dislikes += len(data.get('down', []))
    
    # Usuarios del desafío
    usuarios_desafio = len(puntos)
    
    # Últimos 5 días de votos
    ultimos_dias = sorted(votos.keys(), reverse=True)[:5]
    
    texto = "📊 *ESTADÍSTICAS DEL BOT*\n\n"
    texto += f"👥 *Usuarios que han votado:* {len(usuarios_votos)}\n"
    texto += f"🎮 *Jugadores del desafío:* {usuarios_desafio}\n\n"
    texto += f"👍 *Total likes:* {total_likes}\n"
    texto += f"👎 *Total dislikes:* {total_dislikes}\n\n"
    
    if ultimos_dias:
        texto += "*Últimos días:*\n"
        for fecha in ultimos_dias:
            up = len(votos[fecha].get('up', []))
            down = len(votos[fecha].get('down', []))
            texto += f"📅 {fecha}: 👍{up} 👎{down}\n"
    
    bot.reply_to(message, texto, parse_mode='Markdown')

@bot.message_handler(commands=['usuarios'])
def ver_usuarios(message):
    """Muestra la lista de usuarios registrados"""
    try:
        usuarios = cargar_usuarios()
        print(f"Usuarios cargados: {len(usuarios)}")
        if not usuarios:
            bot.reply_to(message, "👥 Aún no hay usuarios registrados.")
            return
        
        texto = f"👥 *USUARIOS DEL BOT* ({len(usuarios)})\n\n"
        for user_id, data in list(usuarios.items())[-20:]:  # Últimos 20
            nombre = data.get('nombre', 'Sin nombre')
            username = data.get('username')
            ultima = data.get('ultima_vez', '?')
            if username:
                texto += f"• {nombre} (@{username})\n  └ Última vez: {ultima}\n"
            else:
                texto += f"• {nombre}\n  └ Última vez: {ultima}\n"
        
        if len(usuarios) > 20:
            texto += f"\n_...y {len(usuarios) - 20} más_"
        
        bot.reply_to(message, texto, parse_mode='Markdown')
    except Exception as e:
        print(f"Error en /usuarios: {e}")
        bot.reply_to(message, f"❌ Error: {e}")

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
    print("=" * 50)
    print("🚀 INICIANDO BOT...")
    print("=" * 50)
    
    # Iniciar servidor HTTP para Render PRIMERO
    threading.Thread(target=run_health_server, daemon=True).start()
    time.sleep(2)
    print("✅ Health server listo")
    
    # Verificar conexión con Telegram
    try:
        bot_info = bot.get_me()
        print(f"✅ Conectado a Telegram como: @{bot_info.username}")
    except Exception as e:
        print(f"❌ Error conectando a Telegram: {e}")
    
    # Iniciar el bot
    print("🔄 Iniciando polling...")
    threading.Thread(target=bot.infinity_polling, daemon=True).start()
    print("✅ Bot polling iniciado - ¡TODO OK!")
    
    # Ejecutar el schedule
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    main()