import telebot
from telebot import types
from datetime import datetime, timedelta
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
import storage

# Tu token del BotFather
TOKEN = os.environ.get('TOKEN')
bot = telebot.TeleBot(TOKEN)

# Tu ID de chat
CHAT_ID = os.environ.get('CHAT_ID')

# Claves para Redis
REDIS_ESTADO = 'estado_usado'
REDIS_SUGERENCIAS = 'sugerencias'
REDIS_VOTOS = 'votos'
REDIS_PUNTOS = 'puntos'
REDIS_USUARIOS = 'usuarios'
REDIS_FRASES_APROBADAS = 'frases_aprobadas'
REDIS_USOS_AHORA = 'usos_ahora'

def cargar_estado():
    """Carga el estado de elementos ya usados"""
    return storage.obtener_dict(REDIS_ESTADO) or {'palabras': [], 'refranes': [], 'frases': []}

def guardar_estado(estado):
    """Guarda el estado de elementos usados"""
    storage.guardar_dict(REDIS_ESTADO, estado)

def cargar_sugerencias():
    """Carga las sugerencias guardadas"""
    return storage.obtener_lista(REDIS_SUGERENCIAS)

def guardar_sugerencia(user_id, chat_id, usuario, texto):
    """Guarda una nueva sugerencia con datos para notificar"""
    sugerencias = cargar_sugerencias()
    sugerencias.append({
        'id': len(sugerencias),
        'user_id': user_id,
        'chat_id': chat_id,
        'usuario': usuario,
        'texto': texto,
        'fecha': datetime.now().strftime("%d/%m/%Y %H:%M"),
        'estado': 'pendiente'
    })
    storage.guardar_lista(REDIS_SUGERENCIAS, sugerencias)

def guardar_sugerencias(sugerencias):
    """Guarda todas las sugerencias"""
    storage.guardar_lista(REDIS_SUGERENCIAS, sugerencias)

def cargar_frases_aprobadas():
    """Carga las frases aprobadas dinámicamente"""
    return storage.obtener_lista(REDIS_FRASES_APROBADAS)

def guardar_frase_aprobada(frase):
    """Añade una frase aprobada"""
    frases = cargar_frases_aprobadas()
    if frase not in frases:
        frases.append(frase)
        storage.guardar_lista(REDIS_FRASES_APROBADAS, frases)

def obtener_todas_frases():
    """Combina frases de contenido.py + aprobadas dinámicamente"""
    return FRASES_AMIGOS + cargar_frases_aprobadas()

def cargar_usuarios():
    """Carga el registro de usuarios"""
    return storage.obtener_dict(REDIS_USUARIOS)

def guardar_usuarios(usuarios):
    """Guarda todos los usuarios"""
    storage.guardar_dict(REDIS_USUARIOS, usuarios)

def registrar_usuario(user, chat_id=None):
    """Registra o actualiza un usuario con su chat_id para envíos diarios"""
    usuarios = cargar_usuarios()
    user_key = str(user.id)
    
    # Si ya existe, mantener el chat_id anterior si no se proporciona uno nuevo
    chat_id_guardado = usuarios.get(user_key, {}).get('chat_id')
    
    usuarios[user_key] = {
        'nombre': user.first_name or 'Sin nombre',
        'username': user.username or None,
        'chat_id': chat_id or chat_id_guardado,
        'ultima_vez': datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    guardar_usuarios(usuarios)

def cargar_votos():
    """Carga los votos guardados"""
    return storage.obtener_dict(REDIS_VOTOS)

def guardar_votos(votos):
    """Guarda los votos"""
    storage.guardar_dict(REDIS_VOTOS, votos)

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
    return storage.obtener_dict(REDIS_PUNTOS)

def guardar_puntos(puntos):
    """Guarda las puntuaciones"""
    storage.guardar_dict(REDIS_PUNTOS, puntos)

# Diccionario en memoria para trackear intentos por mensaje
INTENTOS_DESAFIO = {}  # {"user_id_msg_id": intentos}

def sumar_puntos(user_id, nombre, puntos_ganados):
    """Suma puntos al usuario con historial por fecha"""
    if puntos_ganados <= 0:
        return 0
    
    puntos = cargar_puntos()
    user_key = str(user_id)
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    
    if user_key not in puntos:
        puntos[user_key] = {'nombre': nombre, 'historial': []}
    
    puntos[user_key]['nombre'] = nombre
    puntos[user_key]['historial'].append({
        'fecha': fecha_hoy,
        'puntos': puntos_ganados
    })
    
    guardar_puntos(puntos)
    return calcular_puntos_semana(user_key)

def calcular_puntos_semana(user_key):
    """Calcula los puntos de la semana actual"""
    puntos = cargar_puntos()
    if user_key not in puntos:
        return 0
    
    hoy = datetime.now()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    inicio_semana = inicio_semana.replace(hour=0, minute=0, second=0, microsecond=0)
    
    total = 0
    for registro in puntos[user_key].get('historial', []):
        fecha = datetime.strptime(registro['fecha'], "%Y-%m-%d")
        if fecha >= inicio_semana:
            total += registro['puntos']
    return total

def calcular_puntos_mes(user_key):
    """Calcula los puntos del mes actual"""
    puntos = cargar_puntos()
    if user_key not in puntos:
        return 0
    
    hoy = datetime.now()
    mes_actual = hoy.month
    año_actual = hoy.year
    
    total = 0
    for registro in puntos[user_key].get('historial', []):
        fecha = datetime.strptime(registro['fecha'], "%Y-%m-%d")
        if fecha.month == mes_actual and fecha.year == año_actual:
            total += registro['puntos']
    return total

def obtener_ranking(periodo='semana'):
    """Obtiene el ranking ordenado por periodo (semana o mes)"""
    puntos = cargar_puntos()
    ranking = []
    
    for user_key, data in puntos.items():
        if periodo == 'semana':
            pts = calcular_puntos_semana(user_key)
        else:
            pts = calcular_puntos_mes(user_key)
        
        if pts > 0:
            ranking.append((user_key, data['nombre'], pts))
    
    return sorted(ranking, key=lambda x: x[2], reverse=True)[:10]

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

def obtener_sin_repetir(lista, usados_key, user_id=None):
    """Obtiene un elemento aleatorio sin repetir hasta agotar la lista (por usuario)"""
    estado = cargar_estado()
    
    # Si hay user_id, usar historial por usuario
    if user_id:
        user_key = str(user_id)
        if user_key not in estado:
            estado[user_key] = {'palabras': [], 'refranes': [], 'frases': []}
        usados = estado[user_key].get(usados_key, [])
    else:
        usados = estado.get(usados_key, [])
    
    disponibles = [item for item in lista if item not in usados]
    
    if not disponibles:
        usados = []
        disponibles = lista.copy()
    
    elegido = random.choice(disponibles)
    usados.append(elegido)
    
    # Guardar en la estructura correcta
    if user_id:
        estado[user_key][usados_key] = usados
    else:
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

def mensaje_diario(user_id=None):
    """Genera el mensaje del día (personalizado por usuario si se proporciona user_id)"""
    palabra = obtener_sin_repetir(PALABRAS_CURIOSAS, 'palabras', user_id)
    refran = obtener_sin_repetir(REFRANES, 'refranes', user_id)
    frase = obtener_sin_repetir(obtener_todas_frases(), 'frases', user_id)
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
    """Envía el mensaje diario a todos los usuarios registrados (personalizado por usuario)"""
    usuarios = cargar_usuarios()
    fecha = datetime.now().strftime("%Y-%m-%d")
    markup = crear_botones_voto(fecha)
    
    enviados = 0
    errores = 0
    
    for user_id, data in usuarios.items():
        chat_id = data.get('chat_id')
        if not chat_id:
            continue
        
        try:
            # Mensaje personalizado por usuario
            mensaje = mensaje_diario(user_id)
            bot.send_message(
                chat_id, 
                mensaje, 
                parse_mode='Markdown',
                reply_markup=markup
            )
            enviados += 1
        except Exception as e:
            errores += 1
            print(f"Error enviando a {data.get('nombre', user_id)}: {e}")
    
    print(f"Mensaje diario enviado: {enviados} OK, {errores} errores - {datetime.now()}")

# Programar envío diario a las 9:00 AM
schedule.every().day.at("09:00").do(enviar_mensaje)

@bot.message_handler(commands=['start', 'hola'])
def send_welcome(message):
    registrar_usuario(message.from_user, message.chat.id)
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
/ranking - Ranking semanal y mensual
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

def obtener_usos_ahora(user_id):
    """Obtiene cuántas veces ha usado /ahora hoy"""
    usos = storage.obtener_dict(REDIS_USOS_AHORA)
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    clave = f"{user_id}_{fecha_hoy}"
    return usos.get(clave, 0)

def incrementar_usos_ahora(user_id):
    """Incrementa el contador de usos de /ahora"""
    usos = storage.obtener_dict(REDIS_USOS_AHORA)
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    clave = f"{user_id}_{fecha_hoy}"
    
    # Limpiar usos de días anteriores
    usos = {k: v for k, v in usos.items() if k.endswith(fecha_hoy)}
    
    usos[clave] = usos.get(clave, 0) + 1
    storage.guardar_dict(REDIS_USOS_AHORA, usos)
    return usos[clave]

MENSAJES_LIMITE_AHORA = [
    # 4º intento - jocoso
    "🙊 *¡Ey, ey, ey!* ¿Pero tú no tienes nada mejor que hacer?\n\nYa van 4 perlas hoy... Que el saber no ocupa lugar, pero la avaricia rompe el saco. 💰\n\n_Vuelve mañana, anda._",
    # 5º intento - más cañero
    "😒 Mira, cielo... Esto ya es un poco obsesivo.\n\nLas perlas se disfrutan como el buen vino: *con moderación*. Tú estás bebiendo directamente de la botella.\n\n_¿No tienes un hobby o algo?_",
    # 6º+ intento - amenaza
    "🔥 *Último aviso.*\n\nComo vuelvas a darle, te voy a llamar cosas que no puedo escribir aquí porque Telegram me banea.\n\nPista: riman con _bontántula_ y _bimbrécil_.\n\n🚫 _Bot bloqueado hasta mañana (broma, pero párate ya)_"
]

@bot.message_handler(commands=['ahora'])
def send_now(message):
    registrar_usuario(message.from_user)
    user_id = message.from_user.id
    
    # Verificar límite diario
    usos = obtener_usos_ahora(user_id)
    
    if usos >= 3:
        # Ya ha usado 3 veces, mostrar mensaje según intento
        intento_extra = usos - 3  # 0, 1, 2+
        idx = min(intento_extra, len(MENSAJES_LIMITE_AHORA) - 1)
        incrementar_usos_ahora(user_id)
        bot.reply_to(message, MENSAJES_LIMITE_AHORA[idx], parse_mode='Markdown')
        return
    
    incrementar_usos_ahora(user_id)
    fecha = datetime.now().strftime("%Y-%m-%d")
    bot.send_message(
        message.chat.id, 
        mensaje_diario(user_id), 
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
    guardar_sugerencia(message.from_user.id, message.chat.id, usuario, texto)
    bot.reply_to(message, f"✅ ¡Gracias {usuario}! Tu sugerencia ha sido guardada para revisión. Te notificaré cuando sea revisada.")

@bot.message_handler(commands=['versugerencias'])
def ver_sugerencias(message):
    sugerencias = cargar_sugerencias()
    pendientes = [s for s in sugerencias if s.get('estado') == 'pendiente']
    
    if not pendientes:
        bot.reply_to(message, "📭 No hay sugerencias pendientes.")
        return
    
    # Mostrar la primera pendiente con botones
    s = pendientes[0]
    idx = sugerencias.index(s)
    
    texto = f"📬 *Sugerencia pendiente* ({len(pendientes)} en cola)\n\n"
    texto += f"_{s['texto']}_\n\n"
    texto += f"👤 {s['usuario']} - {s['fecha']}"
    
    markup = types.InlineKeyboardMarkup()
    btn_aprobar = types.InlineKeyboardButton("✅ Aprobar", callback_data=f"sug_aprobar_{idx}")
    btn_rechazar = types.InlineKeyboardButton("❌ Rechazar", callback_data=f"sug_rechazar_{idx}")
    btn_saltar = types.InlineKeyboardButton("⏭️ Siguiente", callback_data=f"sug_saltar_{idx}")
    markup.add(btn_aprobar, btn_rechazar)
    markup.add(btn_saltar)
    
    bot.reply_to(message, texto, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('sug_'))
def handle_sugerencia(call):
    """Maneja aprobar/rechazar sugerencias"""
    partes = call.data.split('_')
    accion = partes[1]
    idx = int(partes[2])
    
    sugerencias = cargar_sugerencias()
    if idx >= len(sugerencias):
        bot.answer_callback_query(call.id, "❌ Sugerencia no encontrada")
        return
    
    s = sugerencias[idx]
    
    if accion == 'saltar':
        # Buscar siguiente pendiente
        pendientes = [(i, sg) for i, sg in enumerate(sugerencias) if sg.get('estado') == 'pendiente' and i > idx]
        if not pendientes:
            pendientes = [(i, sg) for i, sg in enumerate(sugerencias) if sg.get('estado') == 'pendiente' and i != idx]
        
        if not pendientes:
            bot.edit_message_text("📭 No hay más sugerencias pendientes.",
                chat_id=call.message.chat.id, message_id=call.message.message_id)
            return
        
        next_idx, next_s = pendientes[0]
        pendientes_count = len([sg for sg in sugerencias if sg.get('estado') == 'pendiente'])
        
        texto = f"📬 *Sugerencia pendiente* ({pendientes_count} en cola)\n\n"
        texto += f"_{next_s['texto']}_\n\n"
        texto += f"👤 {next_s['usuario']} - {next_s['fecha']}"
        
        markup = types.InlineKeyboardMarkup()
        btn_aprobar = types.InlineKeyboardButton("✅ Aprobar", callback_data=f"sug_aprobar_{next_idx}")
        btn_rechazar = types.InlineKeyboardButton("❌ Rechazar", callback_data=f"sug_rechazar_{next_idx}")
        btn_saltar = types.InlineKeyboardButton("⏭️ Siguiente", callback_data=f"sug_saltar_{next_idx}")
        markup.add(btn_aprobar, btn_rechazar)
        markup.add(btn_saltar)
        
        bot.edit_message_text(texto, chat_id=call.message.chat.id, 
            message_id=call.message.message_id, parse_mode='Markdown', reply_markup=markup)
        return
    
    if accion == 'aprobar':
        sugerencias[idx]['estado'] = 'aprobada'
        guardar_sugerencias(sugerencias)
        
        # Añadir frase al archivo de frases aprobadas
        guardar_frase_aprobada(s['texto'])
        
        # Notificar al usuario
        chat_id = s.get('chat_id')
        if chat_id:
            try:
                bot.send_message(chat_id, 
                    f"🎉 *¡Tu sugerencia fue aprobada!*\n\n_{s['texto']}_\n\n¡Ya está añadida a las frases del bot! Gracias por contribuir 🙌",
                    parse_mode='Markdown')
            except:
                pass
        
        bot.answer_callback_query(call.id, "✅ Aprobada, añadida y usuario notificado")
        
    elif accion == 'rechazar':
        sugerencias[idx]['estado'] = 'rechazada'
        guardar_sugerencias(sugerencias)
        
        # Notificar al usuario
        chat_id = s.get('chat_id')
        if chat_id:
            try:
                bot.send_message(chat_id,
                    f"📝 *Sobre tu sugerencia...*\n\n_{s['texto']}_\n\nNo ha sido seleccionada esta vez, pero ¡gracias por participar! Sigue sugiriendo 🙌",
                    parse_mode='Markdown')
            except:
                pass
        
        bot.answer_callback_query(call.id, "❌ Rechazada y usuario notificado")
    
    # Mostrar siguiente o mensaje de fin
    pendientes = [sg for sg in sugerencias if sg.get('estado') == 'pendiente']
    if pendientes:
        next_s = pendientes[0]
        next_idx = sugerencias.index(next_s)
        
        texto = f"📬 *Sugerencia pendiente* ({len(pendientes)} en cola)\n\n"
        texto += f"_{next_s['texto']}_\n\n"
        texto += f"👤 {next_s['usuario']} - {next_s['fecha']}"
        
        markup = types.InlineKeyboardMarkup()
        btn_aprobar = types.InlineKeyboardButton("✅ Aprobar", callback_data=f"sug_aprobar_{next_idx}")
        btn_rechazar = types.InlineKeyboardButton("❌ Rechazar", callback_data=f"sug_rechazar_{next_idx}")
        btn_saltar = types.InlineKeyboardButton("⏭️ Siguiente", callback_data=f"sug_saltar_{next_idx}")
        markup.add(btn_aprobar, btn_rechazar)
        markup.add(btn_saltar)
        
        bot.edit_message_text(texto, chat_id=call.message.chat.id,
            message_id=call.message.message_id, parse_mode='Markdown', reply_markup=markup)
    else:
        bot.edit_message_text("✅ *¡Todas las sugerencias han sido revisadas!*",
            chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='Markdown')

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
    
    user_id = call.from_user.id
    msg_id = call.message.message_id
    clave_intento = f"{user_id}_{msg_id}"
    
    # Contar intento
    if clave_intento not in INTENTOS_DESAFIO:
        INTENTOS_DESAFIO[clave_intento] = 0
    INTENTOS_DESAFIO[clave_intento] += 1
    intento = INTENTOS_DESAFIO[clave_intento]
    
    if respuesta == correcta:
        nombre = call.from_user.first_name or "Anónimo"
        
        # Calcular puntos según intento
        if intento == 1:
            pts_ganados = 3
        elif intento == 2:
            pts_ganados = 1
        else:
            pts_ganados = 0
        
        puntos_semana = sumar_puntos(user_id, nombre, pts_ganados)
        
        if pts_ganados > 0:
            msg_pts = f"+{pts_ganados} pts (semana: {puntos_semana})"
        else:
            msg_pts = "0 pts (ya no sumaba)"
        
        bot.answer_callback_query(call.id, f"✅ ¡Correcto! {msg_pts}")
        bot.edit_message_text(
            f"✅ *¡{nombre} acertó!* ({msg_pts})\n\n" + call.message.text.replace("🧠", "🎉"),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode='Markdown'
        )
        # Limpiar intento
        del INTENTOS_DESAFIO[clave_intento]
    else:
        intentos_restantes = 2 - intento if intento < 2 else 0
        if intentos_restantes > 0:
            bot.answer_callback_query(call.id, f"❌ Incorrecto. Te queda {intentos_restantes} intento con puntos")
        else:
            bot.answer_callback_query(call.id, "❌ Incorrecto. Ya no sumas puntos, pero puedes seguir intentando")

@bot.message_handler(commands=['ranking'])
def ver_ranking(message):
    """Muestra el ranking semanal y mensual del desafío"""
    ranking_semana = obtener_ranking('semana')
    ranking_mes = obtener_ranking('mes')
    
    if not ranking_semana and not ranking_mes:
        bot.reply_to(message, "📊 Aún no hay puntuaciones. ¡Usa /desafio para jugar!")
        return
    
    medallas = ['🥇', '🥈', '🥉']
    texto = "🏆 *RANKING DEL DESAFÍO*\n"
    texto += "_3 pts a la primera, 1 pt a la segunda_\n\n"
    
    # Ranking semanal
    texto += "📅 *ESTA SEMANA:*\n"
    if ranking_semana:
        for i, (user_id, nombre, pts) in enumerate(ranking_semana[:5]):
            medalla = medallas[i] if i < 3 else f"{i+1}."
            texto += f"{medalla} {nombre}: *{pts}* pts\n"
    else:
        texto += "_Sin puntuaciones aún_\n"
    
    # Ranking mensual
    mes_nombre = datetime.now().strftime("%B").capitalize()
    texto += f"\n📆 *{mes_nombre.upper()}:*\n"
    if ranking_mes:
        for i, (user_id, nombre, pts) in enumerate(ranking_mes[:5]):
            medalla = medallas[i] if i < 3 else f"{i+1}."
            texto += f"{medalla} {nombre}: *{pts}* pts\n"
    else:
        texto += "_Sin puntuaciones aún_\n"
    
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

@bot.message_handler(commands=['datos'])
def ver_datos(message):
    """Muestra datos de contenido usado"""
    estado = cargar_estado()
    usuarios = cargar_usuarios()
    sugerencias = cargar_sugerencias()
    frases_aprobadas = cargar_frases_aprobadas()
    
    # Conteos
    palabras_usadas = len(estado.get('palabras', []))
    palabras_total = len(PALABRAS_CURIOSAS)
    refranes_usados = len(estado.get('refranes', []))
    refranes_total = len(REFRANES)
    frases_usadas = len(estado.get('frases', []))
    frases_total = len(obtener_todas_frases())
    
    usuarios_total = len(usuarios)
    usuarios_suscritos = len([u for u in usuarios.values() if u.get('chat_id')])
    sugerencias_pendientes = len([s for s in sugerencias if s.get('estado') == 'pendiente'])
    
    texto = "📊 *DATOS DEL BOT*\n\n"
    texto += f"👥 *Usuarios registrados:* {usuarios_total}\n"
    texto += f"📬 *Suscritos al diario:* {usuarios_suscritos}\n"
    texto += f"💡 *Sugerencias pendientes:* {sugerencias_pendientes}\n"
    texto += f"✅ *Frases aprobadas:* {len(frases_aprobadas)}\n\n"
    
    texto += "*Contenido usado:*\n"
    texto += f"📚 Palabras: {palabras_usadas}/{palabras_total}\n"
    texto += f"🎯 Refranes: {refranes_usados}/{refranes_total}\n"
    texto += f"😂 Frases: {frases_usadas}/{frases_total}\n\n"
    
    # Progreso visual
    def barra(usado, total):
        pct = int((usado / total) * 10) if total > 0 else 0
        return '▓' * pct + '░' * (10 - pct)
    
    texto += f"`{barra(palabras_usadas, palabras_total)}` Palabras\n"
    texto += f"`{barra(refranes_usados, refranes_total)}` Refranes\n"
    texto += f"`{barra(frases_usadas, frases_total)}` Frases"
    
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