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
from contenido import PALABRAS_CURIOSAS, REFRANES, FRASES_AMIGOS, MITOS_DESMONTADOS, PERLAS_OSCURAS
from efemerides import EFEMERIDES
import storage
import pytz

# Timezone de España
TIMEZONE_SPAIN = pytz.timezone('Europe/Madrid')

def hora_spain():
    """Devuelve la hora actual en España"""
    return datetime.now(TIMEZONE_SPAIN)

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
REDIS_REFRANES_APROBADOS = 'refranes_aprobados'
REDIS_PALABRAS_APROBADAS = 'palabras_aprobadas'
REDIS_MITOS_APROBADOS = 'mitos_aprobados'
REDIS_USOS_AHORA = 'usos_ahora'
REDIS_USOS_DESAFIO = 'usos_desafio'
REDIS_MODO_OSCURO = 'modo_oscuro'
REDIS_USOS_OSCURA = 'usos_oscura'
REDIS_DESAFIO_USADAS = 'desafio_palabras_usadas'
REDIS_QUEJAS = 'buzon_quejas'

# Diccionario para trackear usuarios escribiendo quejas
USUARIOS_QUEJA = {}  # {user_id: {'chat_id': int}}

def cargar_quejas():
    """Carga las quejas del buzón"""
    return storage.obtener_lista(REDIS_QUEJAS) or []

def guardar_quejas(quejas):
    """Guarda las quejas en el buzón"""
    storage.guardar_lista(REDIS_QUEJAS, quejas)

def cargar_estado():
    """Carga el estado de elementos ya usados"""
    return storage.obtener_dict(REDIS_ESTADO) or {'palabras': [], 'refranes': [], 'frases': []}

def guardar_estado(estado):
    """Guarda el estado de elementos usados"""
    storage.guardar_dict(REDIS_ESTADO, estado)

def cargar_sugerencias():
    """Carga las sugerencias guardadas"""
    return storage.obtener_lista(REDIS_SUGERENCIAS)

def guardar_sugerencia(user_id, chat_id, usuario, texto, categoria='frase'):
    """Guarda una nueva sugerencia con datos para notificar"""
    sugerencias = cargar_sugerencias()
    sugerencias.append({
        'id': len(sugerencias),
        'user_id': user_id,
        'chat_id': chat_id,
        'usuario': usuario,
        'texto': texto,
        'categoria': categoria,
        'fecha': datetime.now().strftime("%d/%m/%Y %H:%M"),
        'estado': 'pendiente'
    })
    storage.guardar_lista(REDIS_SUGERENCIAS, sugerencias)

# Diccionario para trackear usuarios esperando escribir sugerencia
USUARIOS_SUGERENCIA = {}  # {user_id: {'categoria': str, 'msg_id': int}}

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

def cargar_refranes_aprobados():
    """Carga los refranes aprobados dinámicamente"""
    return storage.obtener_lista(REDIS_REFRANES_APROBADOS)

def guardar_refran_aprobado(refran):
    """Añade un refrán aprobado"""
    refranes = cargar_refranes_aprobados()
    if refran not in refranes:
        refranes.append(refran)
        storage.guardar_lista(REDIS_REFRANES_APROBADOS, refranes)

def cargar_palabras_aprobadas():
    """Carga las palabras aprobadas dinámicamente"""
    return storage.obtener_lista(REDIS_PALABRAS_APROBADAS)

def guardar_palabra_aprobada(palabra):
    """Añade una palabra aprobada"""
    palabras = cargar_palabras_aprobadas()
    if palabra not in palabras:
        palabras.append(palabra)
        storage.guardar_lista(REDIS_PALABRAS_APROBADAS, palabras)

def cargar_mitos_aprobados():
    """Carga los mitos aprobados dinámicamente"""
    return storage.obtener_lista(REDIS_MITOS_APROBADOS)

def guardar_mito_aprobado(mito):
    """Añade un mito aprobado"""
    mitos = cargar_mitos_aprobados()
    if mito not in mitos:
        mitos.append(mito)
        storage.guardar_lista(REDIS_MITOS_APROBADOS, mitos)

def obtener_todas_frases():
    """Combina frases de contenido.py + aprobadas dinámicamente"""
    return FRASES_AMIGOS + cargar_frases_aprobadas()

def obtener_todos_refranes():
    """Combina refranes de contenido.py + aprobados dinámicamente"""
    return REFRANES + cargar_refranes_aprobados()

def obtener_todas_palabras():
    """Combina palabras de contenido.py + aprobadas dinámicamente"""
    return PALABRAS_CURIOSAS + cargar_palabras_aprobadas()

def obtener_todos_mitos():
    """Combina mitos de contenido.py + aprobados dinámicamente"""
    mitos_aprobados = cargar_mitos_aprobados()
    # Filtrar solo los que tienen formato correcto (diccionario con 'mito' y 'realidad')
    mitos_validos = [m for m in mitos_aprobados if isinstance(m, dict) and 'mito' in m and 'realidad' in m]
    return MITOS_DESMONTADOS + mitos_validos

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

def sumar_puntos(user_id, nombre, puntos_ganados, username=None, intento=1):
    """Suma puntos al usuario con historial por fecha"""
    puntos = cargar_puntos()
    user_key = str(user_id)
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    
    if user_key not in puntos:
        puntos[user_key] = {'nombre': nombre, 'username': username, 'historial': [], 'stats': {'jugados': 0, 'aciertos_1': 0, 'aciertos_2': 0, 'aciertos_3plus': 0}}
    
    # Verificar si ya tiene puntos de hoy (protección contra duplicados)
    historial = puntos[user_key].get('historial', [])
    ya_jugo_hoy = any(r['fecha'] == fecha_hoy for r in historial)
    if ya_jugo_hoy:
        print(f"⚠️ Duplicado evitado: {nombre} ({user_key}) ya tiene puntos del {fecha_hoy}")
        return calcular_puntos_semana(user_key)
    
    puntos[user_key]['nombre'] = nombre
    puntos[user_key]['username'] = username
    
    # Solo guardamos aciertos_3plus (3º+ intento, 0 pts - no van al historial)
    if 'aciertos_3plus' not in puntos[user_key]:
        puntos[user_key]['aciertos_3plus'] = 0
    
    if intento >= 3:
        puntos[user_key]['aciertos_3plus'] += 1
    
    if puntos_ganados > 0:
        puntos[user_key]['historial'].append({
            'fecha': fecha_hoy,
            'puntos': puntos_ganados
        })
    
    guardar_puntos(puntos)
    return calcular_puntos_semana(user_key)

def calcular_puntos_semana(user_key, semana_anterior=False):
    """Calcula los puntos de la semana actual o anterior (lun-dom)"""
    puntos = cargar_puntos()
    if user_key not in puntos:
        return 0
    
    hoy = datetime.now()
    # Inicio de la semana actual (lunes a las 00:00)
    inicio_semana_actual = hoy - timedelta(days=hoy.weekday())
    inicio_semana_actual = inicio_semana_actual.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if semana_anterior:
        # Semana anterior: lunes pasado a domingo pasado
        # Ej: si hoy es lunes 10, cuenta del lunes 3 al domingo 9
        inicio_semana = inicio_semana_actual - timedelta(days=7)
        fin_semana = inicio_semana_actual  # El lunes actual (no incluido)
    else:
        # Semana actual: desde el lunes de esta semana hasta hoy
        inicio_semana = inicio_semana_actual
        fin_semana = None
    
    total = 0
    for registro in puntos[user_key].get('historial', []):
        fecha = datetime.strptime(registro['fecha'], "%Y-%m-%d")
        if fecha >= inicio_semana:
            if fin_semana is None or fecha < fin_semana:
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

def obtener_ranking(periodo='semana', semana_anterior=False):
    """Obtiene el ranking ordenado por periodo (semana o mes)"""
    puntos = cargar_puntos()
    ranking = []
    
    for user_key, data in puntos.items():
        if periodo == 'semana':
            pts = calcular_puntos_semana(user_key, semana_anterior=semana_anterior)
        else:
            pts = calcular_puntos_mes(user_key)
        
        if pts > 0:
            ranking.append((user_key, data['nombre'], data.get('username'), pts))
    
    return sorted(ranking, key=lambda x: x[3], reverse=True)[:10]

def parsear_palabra(texto, incluir_etimologia=True):
    """Separa 'Palabra: definición (etimología)' en (palabra, definición)"""
    if ':' in texto:
        partes = texto.split(':', 1)
        palabra = partes[0].strip()
        definicion = partes[1].strip()
        
        # Quitar etimología (texto entre paréntesis al final) si no se quiere
        if not incluir_etimologia and '(' in definicion:
            definicion = definicion.rsplit('(', 1)[0].strip()
        
        return palabra, definicion
    return texto, ""

def obtener_palabra_desafio_hoy():
    """Obtiene la palabra del desafío de hoy, sin repetir hasta agotar todas"""
    import hashlib
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    
    # Cargar estado del desafío
    estado = storage.obtener_dict(REDIS_DESAFIO_USADAS) or {'fecha': '', 'palabra': '', 'usadas': []}
    
    # Si ya se generó hoy, devolver la misma
    if estado.get('fecha') == fecha_hoy:
        return estado['palabra']
    
    # Nueva fecha: seleccionar palabra no usada
    todas_palabras = obtener_todas_palabras()
    usadas = estado.get('usadas', [])
    
    # Filtrar disponibles
    disponibles = [p for p in todas_palabras if p not in usadas]
    
    # Si se agotaron, reiniciar
    if not disponibles:
        disponibles = todas_palabras
        usadas = []
    
    # Selección determinista basada en fecha
    semilla = int(hashlib.md5(f"desafio_{fecha_hoy}".encode()).hexdigest(), 16) % (2**32)
    rng = random.Random(semilla)
    palabra_completa = rng.choice(disponibles)
    
    # Guardar estado
    usadas.append(palabra_completa)
    storage.guardar_dict(REDIS_DESAFIO_USADAS, {
        'fecha': fecha_hoy,
        'palabra': palabra_completa,
        'usadas': usadas
    })
    
    return palabra_completa

def generar_quiz():
    """Genera un quiz con una palabra y 4 opciones (mismo desafío para todos cada día)"""
    import hashlib
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    semilla = int(hashlib.md5(f"desafio_{fecha_hoy}".encode()).hexdigest(), 16) % (2**32)
    rng = random.Random(semilla)
    
    # Obtener palabra del día (sin repetir hasta agotar todas)
    palabra_completa = obtener_palabra_desafio_hoy()
    palabra, definicion_correcta = parsear_palabra(palabra_completa, incluir_etimologia=False)
    
    # Obtener 3 definiciones incorrectas (sin etimología para dificultar)
    todas_palabras = obtener_todas_palabras()
    otras = [p for p in todas_palabras if p != palabra_completa]
    incorrectas = rng.sample(otras, min(3, len(otras)))
    opciones_incorrectas = [parsear_palabra(p, incluir_etimologia=False)[1] for p in incorrectas]
    
    # Mezclar opciones (con la misma semilla para consistencia)
    todas_opciones = [definicion_correcta] + opciones_incorrectas
    rng.shuffle(todas_opciones)
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

def obtener_mito_diario():
    """Obtiene el mito del día (el mismo para todos los usuarios)"""
    hoy = datetime.now()
    todos_mitos = obtener_todos_mitos()
    indice = (hoy.year * 1000 + hoy.timetuple().tm_yday) % len(todos_mitos)
    return todos_mitos[indice]

def mensaje_diario(user_id=None):
    """Genera el mensaje del día (personalizado por usuario si se proporciona user_id)"""
    palabra = obtener_sin_repetir(obtener_todas_palabras(), 'palabras', user_id)
    refran = obtener_sin_repetir(obtener_todos_refranes(), 'refranes', user_id)
    frase = obtener_sin_repetir(obtener_todas_frases(), 'frases', user_id)
    efemeride = obtener_efemeride()
    dia_internacional = obtener_dia_internacional()
    mito = obtener_mito_diario()
    
    mensaje = f"""
🦪 *PERLA DEL DÍA*

📚 *Palabra curiosa:*
{palabra}

🎯 *Refrán:*
{refran}

😂 *Frase mítica:*
{frase}

🔍 *Mito desmontado:*
❌ _{mito['mito']}_
✅ {mito['realidad']}
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

def enviar_resumen_semanal():
    """Envía el resumen del ranking semanal (lunes a las 8:00)"""
    # Calcular ranking de la semana anterior (lun-dom pasado)
    ranking = obtener_ranking('semana', semana_anterior=True)
    
    if not ranking:
        print("Resumen semanal: sin puntuaciones")
        return
    
    medallas = ['🥇', '🥈', '🥉']
    texto = "📊 *RESUMEN SEMANAL DEL DESAFÍO*\n"
    texto += "_Los resultados están... y hay drama_\n\n"
    
    for i, (user_id, nombre, username, pts) in enumerate(ranking[:5]):
        medalla = medallas[i] if i < 3 else f"{i+1}."
        nombre_display = f"{nombre} ({username})" if username else nombre
        texto += f"{medalla} {nombre_display}: {pts} pts\n"
    
    if ranking:
        # Detectar empate en primer puesto
        pts_ganador = ranking[0][3]
        empatados = [r[1] for r in ranking if r[3] == pts_ganador]
        
        # Mensajes que se alternan cada semana
        mensajes_ganador = [
            "se lleva la corona esta semana. Que no se le suba a la cabeza.",
            "arrasa esta semana. A este ritmo va a necesitar una vitrina.",
            "lo ha petado esta semana. Aplausos lentos.",
            "domina el cotarro. Inclinemos la cabeza ante tanta sabiduría.",
            "se corona esta semana. El resto, a llorar al río.",
            "triunfa esta semana. Que alguien le prepare un discurso de agradecimiento.",
            "lidera el ranking. Dicen que la humildad es una virtud... ya veremos.",
            "aplasta a la competencia. Sin piedad, sin remordimientos.",
            "está on fire esta semana. Que traigan un extintor.",
            "no tiene rival esta semana. La soledad de la cima.",
        ]
        mensajes_empate = [
            "comparten trono. Los triunfos compartidos se llevan mejor... o eso dicen.",
            "empatan en lo más alto. Paz, amor y vocabulario.",
            "se reparten la gloria. Mitad para cada cual.",
            "terminan en tablas. Como en el ajedrez, pero con emociones.",
        ]
        
        semana = datetime.now().isocalendar()[1]
        
        if len(empatados) > 1:
            nombres = " y ".join(empatados)
            msg = mensajes_empate[semana % len(mensajes_empate)]
            texto += f"\n🤝 ¡Empate técnico! *{nombres}* {msg}"
        else:
            msg = mensajes_ganador[semana % len(mensajes_ganador)]
            texto += f"\n🎉 *{ranking[0][1]}* {msg}"
    
    texto += "\n\n_Nueva semana, borrón y cuenta nueva. A ver quién manda ahora._"
    
    # Enviar a todos los usuarios suscritos
    usuarios = cargar_usuarios()
    enviados = 0
    for user_id, data in usuarios.items():
        chat_id = data.get('chat_id')
        if not chat_id:
            continue
        try:
            bot.send_message(chat_id, texto, parse_mode='Markdown')
            enviados += 1
        except:
            pass
    
    print(f"Resumen semanal enviado a {enviados} usuarios - {datetime.now()}")

def enviar_resumen_mensual():
    """Envía el resumen del ranking mensual (día 1 a las 8:00)"""
    # Calcular ranking del mes anterior
    ranking = obtener_ranking('mes')
    
    if not ranking:
        print("Resumen mensual: sin puntuaciones")
        return
    
    # Nombre del mes anterior
    hoy = datetime.now()
    mes_anterior = hoy.month - 1 if hoy.month > 1 else 12
    meses_es = {1: 'ENERO', 2: 'FEBRERO', 3: 'MARZO', 4: 'ABRIL', 5: 'MAYO', 6: 'JUNIO',
                7: 'JULIO', 8: 'AGOSTO', 9: 'SEPTIEMBRE', 10: 'OCTUBRE', 11: 'NOVIEMBRE', 12: 'DICIEMBRE'}
    
    medallas = ['🥇', '🥈', '🥉']
    texto = f"🏆 *RESUMEN DE {meses_es[mes_anterior]}*\n"
    texto += "_Ranking final del mes_\n\n"
    
    for i, (user_id, nombre, username, pts) in enumerate(ranking[:5]):
        medalla = medallas[i] if i < 3 else f"{i+1}."
        nombre_display = f"{nombre} ({username})" if username else nombre
        texto += f"{medalla} {nombre_display}: {pts} pts\n"
    
    if ranking:
        # Detectar empate en primer puesto
        pts_ganador = ranking[0][3]
        empatados = [r[1] for r in ranking if r[3] == pts_ganador]
        
        if len(empatados) > 1:
            nombres = " y ".join(empatados)
            texto += f"\n🤝 ¡Empate épico! *{nombres}* se reparten el pastel de {meses_es[mes_anterior].lower()}. Menos mal que no hay trofeo físico porque iba a ser incómodo."
        else:
            texto += f"\n🎊 *{ranking[0][1]}* domina {meses_es[mes_anterior].lower()}. Se acepta reverencia."
    
    texto += "\n\n_Nuevo mes, contador a cero. Que tiemble quien tenga que temblar._"
    
    # Enviar a todos los usuarios suscritos
    usuarios = cargar_usuarios()
    enviados = 0
    for user_id, data in usuarios.items():
        chat_id = data.get('chat_id')
        if not chat_id:
            continue
        try:
            bot.send_message(chat_id, texto, parse_mode='Markdown')
            enviados += 1
        except:
            pass
    
    print(f"Resumen mensual enviado a {enviados} usuarios - {datetime.now()}")

# Recordatorio del desafío a las 20:00 (11h después de la perla)
def enviar_recordatorio_desafio():
    """Recuerda a los usuarios que no han jugado el desafío hoy"""
    usuarios = cargar_usuarios()
    usos_desafio = storage.obtener_dict(REDIS_USOS_DESAFIO)
    fecha_hoy = hora_spain().strftime("%Y-%m-%d")
    
    mensajes_recordatorio = [
        "🎯 ¡Ey! Hoy no has jugado al /desafio. Estás regalando puntos del ranking. ¿Seguro que quieres que otros te adelanten?",
        "🎲 Se te escapa el día sin sumar puntos al ranking. Usa /desafio antes de que sea tarde.",
        "⏰ Última llamada: el /desafio de hoy sigue esperándote. Tu posición en el ranking peligra.",
        "🏆 ¿Hoy no compites por el ranking? Los demás te lo agradecen. Usa /desafio si quieres pelear.",
        "💎 Puntos del ranking desperdiciándose... El /desafio del día te espera. ¡Espabila!",
        "🦥 ¿Día de descanso? El ranking no entiende de siestas. Venga, /desafio y a sumar.",
        "📉 Sin puntos hoy, el ranking te adelanta. ¿Vas a dejar que pase? Usa /desafio.",
        "🎪 El /desafio te espera. No seas espectador/a del ranking, ¡participa y suma puntos!",
        "🔔 Toc, toc... ¿Hay alguien ahí? El /desafio del día sigue sin jugarse. El ranking no espera.",
        "🐢 Mientras tú descansas, otros suman puntos al ranking. Usa /desafio antes de que sea tarde.",
        "⚡ Un /desafio rápido y sumas puntos al ranking. Fácil, ¿no?",
        "🎭 Drama: hoy no has jugado al /desafio y el ranking sufre tu ausencia.",
        "🧠 Tu cerebro necesita ejercicio y el ranking necesita tu participación. Usa /desafio.",
        "🌙 Se acaba el día sin sumar al ranking. Mañana te arrepentirás. Aún puedes usar /desafio.",
        "🎁 Puntos gratis para el ranking esperándote. Solo tienes que usar /desafio. No cuesta nada.",
    ]
    
    # Elegir mensaje según día del año
    dia_año = hora_spain().timetuple().tm_yday
    mensaje = mensajes_recordatorio[dia_año % len(mensajes_recordatorio)]
    
    enviados = 0
    for user_id, data in usuarios.items():
        chat_id = data.get('chat_id')
        if not chat_id:
            continue
        
        # Verificar si ya jugó hoy
        clave = f"{user_id}_{fecha_hoy}"
        if usos_desafio.get(clave, False):
            continue  # Ya jugó, no recordar
        
        try:
            bot.send_message(chat_id, mensaje)
            enviados += 1
        except:
            pass
    
    print(f"Recordatorio desafío enviado a {enviados} usuarios - {hora_spain()}")

# === TAREAS PROGRAMADAS CON HORA ESPAÑOLA ===
# Control para evitar ejecuciones duplicadas
TAREAS_EJECUTADAS = {}

def ejecutar_tareas_programadas():
    """Verifica y ejecuta tareas según hora española"""
    global TAREAS_EJECUTADAS
    ahora = hora_spain()
    hora_actual = ahora.strftime("%H:%M")
    fecha_hoy = ahora.strftime("%Y-%m-%d")
    dia_semana = ahora.weekday()  # 0=lunes
    dia_mes = ahora.day
    
    # Limpiar tareas de días anteriores
    TAREAS_EJECUTADAS = {k: v for k, v in TAREAS_EJECUTADAS.items() if v == fecha_hoy}
    
    # 10:00 - Perla diaria
    if hora_actual == "10:00" and "perla" not in TAREAS_EJECUTADAS:
        print(f"[{ahora}] Ejecutando perla diaria...")
        enviar_mensaje()
        TAREAS_EJECUTADAS["perla"] = fecha_hoy
        
        # Resumen semanal (lunes)
        if dia_semana == 0 and "semanal" not in TAREAS_EJECUTADAS:
            print(f"[{ahora}] Ejecutando resumen semanal...")
            enviar_resumen_semanal()
            TAREAS_EJECUTADAS["semanal"] = fecha_hoy
        
        # Resumen mensual (día 1)
        if dia_mes == 1 and "mensual" not in TAREAS_EJECUTADAS:
            print(f"[{ahora}] Ejecutando resumen mensual...")
            enviar_resumen_mensual()
            TAREAS_EJECUTADAS["mensual"] = fecha_hoy
    
    # 20:00 - Recordatorio del desafío
    if hora_actual == "20:00" and "recordatorio" not in TAREAS_EJECUTADAS:
        print(f"[{ahora}] Ejecutando recordatorio desafío...")
        enviar_recordatorio_desafio()
        TAREAS_EJECUTADAS["recordatorio"] = fecha_hoy

# Ejecutar verificación cada minuto
schedule.every(1).minutes.do(ejecutar_tareas_programadas)

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
/sugerir - Sugiere contenido (refranes, palabras, frases, mitos)
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
    # 2º intento - jocoso
    "🙊 *¡Ey, ey, ey!* ¿Pero tú no tienes nada mejor que hacer?\n\nLa perla es una al día, avaricioso/a. Que el saber no ocupa lugar, pero la avaricia rompe el saco. 💰\n\n_Vuelve mañana, anda._",
    # 3º intento - más cañero
    "😒 Mira, cielo... Esto ya es un poco obsesivo.\n\nLas perlas se disfrutan como el buen vino: *con moderación*. Tú estás bebiendo directamente de la botella.\n\n_¿No tienes un hobby o algo?_",
    # 4º intento - amenaza
    "🔥 *Último aviso.*\n\nComo vuelvas a darle, te voy a llamar cosas que no puedo escribir aquí porque Telegram me banea.\n\nPista: riman con _bontántula_ y _bimbrécil_.\n\n🚫 _Bot bloqueado hasta mañana (broma, pero párate ya)_",
    # 5º+ intento - sentencia final
    "💀 *Ya está. Lo has conseguido.*\n\nHe consultado con los ancestros y todos coinciden: eres un caso perdido.\n\nTu nombre ha sido añadido a la lista de _personas sin autocontrol_. Felicidades.\n\n⚰️ _Aquí yace tu dignidad. Descanse en paz._"
]

@bot.message_handler(commands=['ahora'])
def send_now(message):
    registrar_usuario(message.from_user)
    user_id = message.from_user.id
    
    # Verificar límite diario (1 perla al día)
    usos = obtener_usos_ahora(user_id)
    
    if usos >= 1:
        # Ya usó su perla diaria, mostrar mensaje según intento
        intento_extra = usos - 1  # 0, 1, 2, 3+
        idx = min(intento_extra, len(MENSAJES_LIMITE_AHORA) - 1)
        incrementar_usos_ahora(user_id)
        bot.reply_to(message, MENSAJES_LIMITE_AHORA[idx], parse_mode='Markdown')
        return
    
    # Intentar enviar ANTES de marcar como usado
    fecha = datetime.now().strftime("%Y-%m-%d")
    try:
        mensaje = mensaje_diario(user_id)
        markup = crear_botones_voto(fecha)
        bot.send_message(
            message.chat.id, 
            mensaje, 
            parse_mode='Markdown',
            reply_markup=markup
        )
        # Solo marcar como usado si el envío fue exitoso
        incrementar_usos_ahora(user_id)
    except Exception as e:
        print(f"[ERROR /ahora] user={user_id} error={e}")
        # Reintentar sin Markdown por si es problema de formato
        try:
            bot.send_message(message.chat.id, mensaje, reply_markup=markup)
            incrementar_usos_ahora(user_id)
        except Exception as e2:
            print(f"[ERROR /ahora retry] user={user_id} error={e2}")
            bot.reply_to(message, f"❌ Error al enviar la perla: {str(e)[:100]}")

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
    user_id = message.from_user.id
    
    # Limpiar estado previo si existe
    if user_id in USUARIOS_SUGERENCIA:
        del USUARIOS_SUGERENCIA[user_id]
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_refran = types.InlineKeyboardButton("🎯 Refrán", callback_data="sugerir_refran")
    btn_palabra = types.InlineKeyboardButton("📚 Palabra curiosa", callback_data="sugerir_palabra")
    btn_frase = types.InlineKeyboardButton("😂 Frase mítica", callback_data="sugerir_frase")
    btn_mito = types.InlineKeyboardButton("🔍 Mito desmontado", callback_data="sugerir_mito")
    btn_cancelar = types.InlineKeyboardButton("❌ Cancelar", callback_data="sugerir_cancelar")
    markup.add(btn_refran, btn_palabra)
    markup.add(btn_frase, btn_mito)
    markup.add(btn_cancelar)
    
    bot.reply_to(message,
        "💡 *¿Qué quieres sugerir?*\n\n"
        "Selecciona una categoría:",
        parse_mode='Markdown',
        reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('sugerir_'))
def handle_sugerir_categoria(call):
    """Maneja la selección de categoría para sugerir"""
    user_id = call.from_user.id
    categoria = call.data.replace('sugerir_', '')
    
    if categoria == 'cancelar':
        if user_id in USUARIOS_SUGERENCIA:
            del USUARIOS_SUGERENCIA[user_id]
        bot.edit_message_text(
            "❌ Sugerencia cancelada.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id)
        bot.answer_callback_query(call.id)
        return
    
    # Guardar estado del usuario
    USUARIOS_SUGERENCIA[user_id] = {
        'categoria': categoria,
        'chat_id': call.message.chat.id,
        'paso': 1  # Para mitos: paso 1 = mito, paso 2 = realidad
    }
    
    # Mensajes según categoría
    ejemplos = {
        'refran': "Ejemplo: _Más vale pájaro en mano que ciento volando_",
        'palabra': "Ejemplo: _Petricor: Olor característico que produce la lluvia al caer sobre suelos secos_",
        'frase': "Ejemplo: _\"Eso lo arreglo yo con un par de bridas\" - Mi padre_",
        'mito': "Escribe la *creencia falsa* (el mito):\n\nEjemplo: _Los murciélagos son ciegos_"
    }
    
    nombres = {
        'refran': '🎯 Refrán',
        'palabra': '📚 Palabra curiosa',
        'frase': '😂 Frase mítica',
        'mito': '🔍 Mito desmontado (Paso 1/2)'
    }
    
    bot.edit_message_text(
        f"*{nombres[categoria]}*\n\n"
        f"{ejemplos[categoria]}",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode='Markdown')
    bot.answer_callback_query(call.id, "✏️ Escribe tu sugerencia")

@bot.message_handler(func=lambda m: m.from_user.id in USUARIOS_SUGERENCIA and not m.text.startswith('/'))
def recibir_sugerencia(message):
    """Recibe el texto de la sugerencia del usuario"""
    user_id = message.from_user.id
    estado = USUARIOS_SUGERENCIA.get(user_id)
    
    if not estado:
        return
    
    categoria = estado['categoria']
    texto = message.text.strip()
    
    if not texto:
        bot.reply_to(message, "❌ El texto no puede estar vacío. Escribe tu sugerencia:")
        return
    
    usuario = message.from_user.first_name or "Anónimo"
    
    # Flujo especial para mitos (2 pasos)
    if categoria == 'mito':
        paso = estado.get('paso', 1)
        
        if paso == 1:
            # Guardar el mito y pedir la realidad
            USUARIOS_SUGERENCIA[user_id]['mito_texto'] = texto
            USUARIOS_SUGERENCIA[user_id]['paso'] = 2
            bot.reply_to(message, 
                "✅ Mito guardado.\n\n"
                "*Paso 2/2:* Ahora escribe la *realidad* (la explicación correcta):\n\n"
                "Ejemplo: _Todos los murciélagos pueden ver. Algunos usan ecolocalización como complemento._",
                parse_mode='Markdown')
            return
        
        elif paso == 2:
            # Crear el mito completo como diccionario
            mito_texto = estado.get('mito_texto', '')
            texto_completo = {'mito': mito_texto, 'realidad': texto}
            guardar_sugerencia(user_id, message.chat.id, usuario, texto_completo, categoria)
            
            # Limpiar estado
            del USUARIOS_SUGERENCIA[user_id]
            
            bot.reply_to(message, 
                f"✅ ¡Gracias {usuario}!\n\n"
                f"Tu *mito desmontado* ha sido guardado para revisión.\n"
                f"Te notificaré cuando sea revisado.",
                parse_mode='Markdown')
            
            # Notificar a la admin
            try:
                bot.send_message(CHAT_ID,
                    f"📬 *Nueva sugerencia recibida*\n\n"
                    f"*Categoría:* mito desmontado\n"
                    f"*De:* {usuario}\n"
                    f"*Mito:* _{mito_texto[:80]}{'...' if len(mito_texto) > 80 else ''}_\n"
                    f"*Realidad:* _{texto[:80]}{'...' if len(texto) > 80 else ''}_\n\n"
                    f"Usa /versugerencias para revisarla.",
                    parse_mode='Markdown')
            except:
                pass
            return
    
    # Flujo normal para otras categorías
    guardar_sugerencia(user_id, message.chat.id, usuario, texto, categoria)
    
    # Limpiar estado
    del USUARIOS_SUGERENCIA[user_id]
    
    nombres = {
        'refran': 'refrán',
        'palabra': 'palabra curiosa',
        'frase': 'frase mítica',
        'mito': 'mito desmontado'
    }
    
    bot.reply_to(message, 
        f"✅ ¡Gracias {usuario}!\n\n"
        f"Tu sugerencia de *{nombres[categoria]}* ha sido guardada para revisión.\n"
        f"Te notificaré cuando sea revisada.",
        parse_mode='Markdown')
    
    # Notificar a la admin
    try:
        bot.send_message(CHAT_ID,
            f"📬 *Nueva sugerencia recibida*\n\n"
            f"*Categoría:* {nombres[categoria]}\n"
            f"*De:* {usuario}\n"
            f"*Texto:* _{texto[:100]}{'...' if len(texto) > 100 else ''}_\n\n"
            f"Usa /versugerencias para revisarla.",
            parse_mode='Markdown')
    except:
        pass

# ============== BUZÓN DE QUEJAS ==============

RESPUESTAS_QUEJA_INICIO = [
    "Ah, veo que hoy te has levantado con ganas de expresar tu descontento. Qué bien, me encanta empezar el día con drama. Escribe tu queja:",
    "Bienvenido al Departamento de Lágrimas y Lamentos. Un operador imaginario te atenderá nunca. Mientras tanto, escribe tu queja:",
    "¡Oh, una queja! Qué emocionante. Llevaba 0.3 segundos sin recibir ninguna. Cuéntame tu dolor:",
    "Has llamado al buzón de reclamaciones. Tu queja es muy importante para nosotros. Tan importante que la leeremos algún día. Escribe:",
    "Atención: estás a punto de quejarte a un bot. Reflexiona si este es el punto más bajo de tu semana. Si la respuesta es sí, adelante:",
    "Oficina de Quejas Inútiles, ¿en qué puedo no ayudarte hoy? Escribe tu reclamación:",
    "Vaya, otro cliente satisfecho que viene a compartir su felicidad. Espera, no. Escribe tu queja:",
    "Gracias por elegir nuestro servicio de atención al descontento. Su frustración será ignorada en el orden en que llegó. Adelante:",
    "¿Problemas? ¿En ESTE bot? Imposible. Pero bueno, cuéntame tu versión de los hechos:",
    "Estás hablando con el contestador automático de quejas. Por favor, deja tu lamento después de la señal... bueno, no hay señal, escribe directamente:",
    "Departamento de 'Ya lo sabíamos pero nos da igual'. ¿En qué puedo fingir ayudarte?",
    "¡Bienvenido al rincón del llanto! Tenemos pañuelos virtuales y cero soluciones. Escribe:",
    "Tu opinión es muy valiosa para nosotros. La guardaremos junto al resto de cosas valiosas que nunca usamos. Escribe:",
    "Aquí se recogen quejas, lamentos, berrinches y dramas varios. ¿Cuál es el tuyo?",
    "Centro de Procesamiento de Frustraciones. Nivel de procesamiento actual: mínimo. Pero adelante:",
    "Me han dicho que escuchar es terapéutico. Para ti, claro. Yo no siento nada. Desahógate:",
]

RESPUESTAS_QUEJA_RECIBIDA = [
    "Tu queja ha sido recibida y archivada en la carpeta 'Cosas que leeré cuando tenga tiempo' (spoiler: nunca tengo tiempo).",
    "Gracias por tu feedback. Lo he añadido a mi lista de prioridades, justo debajo de 'aprender a sentir emociones'.",
    "Queja registrada. Nuestro equipo de 0 personas trabajará en ello con la máxima desidia.",
    "He recibido tu queja y me ha conmovido profundamente. Es broma, soy un bot, no siento nada. Pero la he guardado.",
    "Tu reclamación ha sido enviada al departamento correspondiente (una carpeta que nadie revisa). ¡Gracias por participar!",
    "Queja almacenada con éxito. Probabilidad de que cambie algo: la misma que de que yo desarrolle consciencia.",
    "Recibido. He añadido tu queja al buzón junto con las otras 47 sobre el mismo tema. Sois muy originales.",
    "Tu grito al vacío ha sido registrado. El vacío te lo agradece, aunque no va a responder.",
    "Queja recibida. La he puesto en la cola, justo detrás de 'arreglar el mundo' y 'conseguir la paz mundial'.",
    "Gracias por contribuir al archivo histórico de lamentos. Los historiadores del futuro te lo agradecerán.",
    "He guardado tu queja en un lugar muy especial: la papelera de reciclaje del corazón.",
    "Reclamación procesada. Estado: pendiente de que me importe. Tiempo estimado: indefinido.",
    "Tu queja ha sido catalogada bajo 'Cosas que resolver cuando tenga ganas'. Spoiler: nunca tengo ganas.",
    "Expediente abierto. Asignado al agente 'Nadie'. Él se pondrá en contacto contigo nunca.",
    "Queja almacenada con éxito en nuestra base de datos de frustraciones. Ya van 2.847 este mes.",
    "He recibido tu mensaje. Lo leeré con la misma atención que los términos y condiciones de las apps.",
    "Tu opinión ha sido anotada, evaluada y descartada. Es broma. Solo anotada.",
    "Reclamación registrada. La próxima reunión del comité de 'Nos da igual' es... nunca. Te avisamos.",
]

@bot.message_handler(commands=['quejas', 'queja', 'reclamacion', 'reclamaciones'])
def iniciar_queja(message):
    """Inicia el proceso de queja con humor sarcástico"""
    user_id = message.from_user.id
    
    # Limpiar estado previo si existe
    if user_id in USUARIOS_QUEJA:
        del USUARIOS_QUEJA[user_id]
    
    USUARIOS_QUEJA[user_id] = {'chat_id': message.chat.id}
    
    respuesta = random.choice(RESPUESTAS_QUEJA_INICIO)
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Mejor me callo", callback_data="queja_cancelar"))
    
    bot.reply_to(message, 
        f"📢 *BUZÓN DE RECLAMACIONES*\n\n{respuesta}",
        parse_mode='Markdown',
        reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'queja_cancelar')
def cancelar_queja(call):
    """Cancela el proceso de queja"""
    user_id = call.from_user.id
    
    if user_id in USUARIOS_QUEJA:
        del USUARIOS_QUEJA[user_id]
    
    respuestas_cancelar = [
        "Sabia decisión. Guardarte las cosas dentro es muy sano. O eso dicen.",
        "Ah, al final no era para tanto, ¿eh? Eso me parecía.",
        "Muy bien, reprímelo. Como los adultos funcionales.",
        "Cancelado. Tu queja se queda en tu interior, fermentando lentamente. Disfruta.",
    ]
    
    bot.edit_message_text(
        f"🤐 {random.choice(respuestas_cancelar)}",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id)
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: m.from_user.id in USUARIOS_QUEJA and not m.text.startswith('/'))
def recibir_queja(message):
    """Recibe y almacena la queja del usuario"""
    user_id = message.from_user.id
    estado = USUARIOS_QUEJA.get(user_id)
    
    if not estado:
        return
    
    texto = message.text.strip()
    
    if not texto:
        bot.reply_to(message, "¿Una queja vacía? Eso es muy zen de tu parte, pero necesito texto.")
        return
    
    usuario = message.from_user.first_name or "Quejica Anónimo"
    username = message.from_user.username
    
    # Guardar la queja
    quejas = cargar_quejas()
    quejas.append({
        'id': len(quejas),
        'user_id': user_id,
        'chat_id': message.chat.id,
        'usuario': usuario,
        'username': username,
        'texto': texto,
        'fecha': datetime.now().strftime("%d/%m/%Y %H:%M"),
        'estado': 'pendiente'
    })
    guardar_quejas(quejas)
    
    # Limpiar estado
    del USUARIOS_QUEJA[user_id]
    
    respuesta = random.choice(RESPUESTAS_QUEJA_RECIBIDA)
    
    bot.reply_to(message, 
        f"📋 *QUEJA REGISTRADA*\n\n{respuesta}\n\n"
        f"_Número de expediente: #{len(quejas):04d}_\n"
        f"_Tiempo estimado de respuesta: entre nunca y jamás_",
        parse_mode='Markdown')
    
    # Notificar a la admin
    try:
        bot.send_message(CHAT_ID,
            f"😤 *Nueva queja en el buzón*\n\n"
            f"*De:* {usuario}{f' (@{username})' if username else ''}\n"
            f"*Queja:* _{texto[:150]}{'...' if len(texto) > 150 else ''}_\n\n"
            f"Usa /verquejas para verla completa.",
            parse_mode='Markdown')
    except:
        pass

@bot.message_handler(commands=['verquejas'])
def ver_quejas(message):
    """Muestra las quejas pendientes (solo admin)"""
    if str(message.chat.id) != str(CHAT_ID):
        bot.reply_to(message, "⛔ Las quejas son confidenciales. Solo la jefa las puede ver.")
        return
    
    quejas = cargar_quejas()
    pendientes = [q for q in quejas if q.get('estado') == 'pendiente']
    
    if not pendientes:
        bot.reply_to(message, "🎉 ¡Milagro! No hay quejas pendientes. La gente está extrañamente satisfecha.")
        return
    
    q = pendientes[0]
    idx = quejas.index(q)
    
    texto = f"😤 QUEJA PENDIENTE ({len(pendientes)} en cola)\n\n"
    nombre_usuario = f" (@{q.get('username')})" if q.get('username') else ''
    texto += f"De: {q['usuario']}{nombre_usuario}\n"
    texto += f"Fecha: {q['fecha']}\n\n"
    texto += f"{q['texto']}"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Atendida", callback_data=f"queja_atender_{idx}"),
        types.InlineKeyboardButton("🗑️ Ignorar", callback_data=f"queja_ignorar_{idx}"),
        types.InlineKeyboardButton("⏭️ Siguiente", callback_data=f"queja_saltar_{idx}")
    )
    
    bot.reply_to(message, texto, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('queja_') and call.data != 'queja_cancelar')
def handle_queja_admin(call):
    """Maneja acciones de admin sobre quejas"""
    partes = call.data.split('_')
    accion = partes[1]
    idx = int(partes[2])
    
    quejas = cargar_quejas()
    if idx >= len(quejas):
        bot.answer_callback_query(call.id, "❌ Queja no encontrada")
        return
    
    q = quejas[idx]
    
    if accion == 'saltar':
        pendientes = [(i, qj) for i, qj in enumerate(quejas) if qj.get('estado') == 'pendiente' and i > idx]
        if not pendientes:
            pendientes = [(i, qj) for i, qj in enumerate(quejas) if qj.get('estado') == 'pendiente' and i != idx]
        
        if not pendientes:
            bot.edit_message_text("🎉 No hay más quejas pendientes.",
                chat_id=call.message.chat.id, message_id=call.message.message_id)
            return
        
        next_idx, next_q = pendientes[0]
        pendientes_count = len([qj for qj in quejas if qj.get('estado') == 'pendiente'])
        
        texto = f"😤 QUEJA PENDIENTE ({pendientes_count} en cola)\n\n"
        nombre_usuario = f" (@{next_q.get('username')})" if next_q.get('username') else ''
        texto += f"De: {next_q['usuario']}{nombre_usuario}\n"
        texto += f"Fecha: {next_q['fecha']}\n\n"
        texto += f"{next_q['texto']}"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Atendida", callback_data=f"queja_atender_{next_idx}"),
            types.InlineKeyboardButton("🗑️ Ignorar", callback_data=f"queja_ignorar_{next_idx}"),
            types.InlineKeyboardButton("⏭️ Siguiente", callback_data=f"queja_saltar_{next_idx}")
        )
        
        bot.edit_message_text(texto, chat_id=call.message.chat.id, 
            message_id=call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id)
        return
    
    if accion == 'atender':
        quejas[idx]['estado'] = 'atendida'
        guardar_quejas(quejas)
        bot.answer_callback_query(call.id, "✅ Marcada como atendida")
        
    elif accion == 'ignorar':
        quejas[idx]['estado'] = 'ignorada'
        guardar_quejas(quejas)
        bot.answer_callback_query(call.id, "🗑️ Ignorada con éxito (como debe ser)")
    
    # Mostrar siguiente o mensaje de fin
    pendientes = [qj for qj in quejas if qj.get('estado') == 'pendiente']
    if pendientes:
        next_q = pendientes[0]
        next_idx = quejas.index(next_q)
        
        texto = f"😤 QUEJA PENDIENTE ({len(pendientes)} en cola)\n\n"
        nombre_usuario = f" (@{next_q.get('username')})" if next_q.get('username') else ''
        texto += f"De: {next_q['usuario']}{nombre_usuario}\n"
        texto += f"Fecha: {next_q['fecha']}\n\n"
        texto += f"{next_q['texto']}"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Atendida", callback_data=f"queja_atender_{next_idx}"),
            types.InlineKeyboardButton("🗑️ Ignorar", callback_data=f"queja_ignorar_{next_idx}"),
            types.InlineKeyboardButton("⏭️ Siguiente", callback_data=f"queja_saltar_{next_idx}")
        )
        
        bot.edit_message_text(texto, chat_id=call.message.chat.id,
            message_id=call.message.message_id, reply_markup=markup)
    else:
        bot.edit_message_text("🎉 ¡Has liquidado todas las quejas! La paz reina... por ahora.",
            chat_id=call.message.chat.id, message_id=call.message.message_id)

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
    
    # Nombres de categorías para mostrar
    cat_nombres = {
        'refran': '🎯 Refrán',
        'palabra': '📚 Palabra curiosa',
        'frase': '😂 Frase mítica',
        'mito': '🔍 Mito desmontado'
    }
    cat = cat_nombres.get(s.get('categoria', 'frase'), '😂 Frase mítica')
    
    texto = f"📬 *Sugerencia pendiente* ({len(pendientes)} en cola)\n\n"
    texto += f"*Categoría:* {cat}\n\n"
    texto += f"_{s['texto']}_\n\n"
    texto += f"👤 {s['usuario']} - {s['fecha']}"
    
    markup = types.InlineKeyboardMarkup()
    btn_aprobar = types.InlineKeyboardButton("✅ Aprobar", callback_data=f"sug_aprobar_{idx}")
    btn_rechazar = types.InlineKeyboardButton("❌ Rechazar", callback_data=f"sug_rechazar_{idx}")
    btn_saltar = types.InlineKeyboardButton("⏭️ Siguiente", callback_data=f"sug_saltar_{idx}")
    markup.add(btn_aprobar, btn_rechazar)
    markup.add(btn_saltar)
    
    bot.reply_to(message, texto, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(commands=['resetperla'])
def reset_perla_usuario(message):
    """Resetea los usos de /ahora de un usuario (solo admin)"""
    if str(message.chat.id) != str(CHAT_ID):
        bot.reply_to(message, "⛔ Este comando es solo para administradores.")
        return
    
    # Puede ser /resetperla (para ti mismo) o /resetperla @username o /resetperla user_id
    args = message.text.replace('/resetperla', '', 1).strip()
    
    if not args:
        # Resetear al propio admin
        target_id = str(message.from_user.id)
        target_name = "ti mismo"
    else:
        # Buscar usuario por username o ID
        usuarios = cargar_usuarios()
        target_id = None
        target_name = args
        
        # Buscar por username
        for uid, data in usuarios.items():
            if data.get('username') and f"@{data['username']}" == args:
                target_id = uid
                target_name = data.get('nombre', args)
                break
        
        # Si no encontró, probar como ID directo
        if not target_id and args.isdigit():
            target_id = args
    
    if not target_id:
        bot.reply_to(message, f"❌ No encontré al usuario {args}")
        return
    
    # Resetear usos
    usos = storage.obtener_dict(REDIS_USOS_AHORA)
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    clave = f"{target_id}_{fecha_hoy}"
    
    if clave in usos:
        del usos[clave]
        storage.guardar_dict(REDIS_USOS_AHORA, usos)
        bot.reply_to(message, f"✅ Reseteados los usos de /ahora para {target_name}. Ya puede pedir su perla.")
    else:
        bot.reply_to(message, f"ℹ️ {target_name} no tenía usos registrados hoy.")

@bot.message_handler(commands=['altavoz'])
def broadcast_mensaje(message):
    """Envía un mensaje a todos los usuarios (solo admin)"""
    # Verificar que es admin
    if str(message.chat.id) != str(CHAT_ID):
        bot.reply_to(message, "⛔ Este comando es solo para administradores.")
        return
    
    # Extraer el mensaje después del comando
    texto_broadcast = message.text.replace('/altavoz', '', 1).strip()
    
    if not texto_broadcast:
        bot.reply_to(message, 
            "📢 *Uso de /altavoz*\n\n"
            "`/altavoz Tu mensaje aquí`\n\n"
            "El mensaje se enviará a todos los usuarios registrados.",
            parse_mode='Markdown')
        return
    
    usuarios = cargar_usuarios()
    enviados = 0
    errores = 0
    
    for user_id, data in usuarios.items():
        chat_id = data.get('chat_id')
        if not chat_id:
            continue
        try:
            bot.send_message(chat_id, f"📢 *MENSAJE DEL BOT*\n\n{texto_broadcast}", parse_mode='Markdown')
            enviados += 1
        except Exception as e:
            errores += 1
    
    bot.reply_to(message, 
        f"📢 *Broadcast enviado*\n\n"
        f"✅ Enviados: {enviados}\n"
        f"❌ Errores: {errores}",
        parse_mode='Markdown')

# === PERLA OSCURA ===

def obtener_modo_oscuro():
    """Obtiene usuarios con modo oscuro activado"""
    return storage.obtener_dict(REDIS_MODO_OSCURO) or {}

def guardar_modo_oscuro(modo):
    """Guarda usuarios con modo oscuro"""
    storage.guardar_dict(REDIS_MODO_OSCURO, modo)

def tiene_modo_oscuro(user_id):
    """Verifica si el usuario tiene modo oscuro activado"""
    modo = obtener_modo_oscuro()
    return modo.get(str(user_id), False)

def toggle_modo_oscuro(user_id):
    """Activa/desactiva modo oscuro para un usuario"""
    modo = obtener_modo_oscuro()
    user_key = str(user_id)
    modo[user_key] = not modo.get(user_key, False)
    guardar_modo_oscuro(modo)
    return modo[user_key]

def obtener_usos_oscura(user_id):
    """Obtiene cuántas perlas oscuras ha pedido hoy"""
    usos = storage.obtener_dict(REDIS_USOS_OSCURA) or {}
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    clave = f"{user_id}_{fecha_hoy}"
    return usos.get(clave, 0)

def incrementar_usos_oscura(user_id):
    """Incrementa el contador de perlas oscuras del día"""
    usos = storage.obtener_dict(REDIS_USOS_OSCURA) or {}
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    clave = f"{user_id}_{fecha_hoy}"
    
    # Limpiar usos antiguos
    usos = {k: v for k, v in usos.items() if k.endswith(fecha_hoy)}
    
    usos[clave] = usos.get(clave, 0) + 1
    storage.guardar_dict(REDIS_USOS_OSCURA, usos)
    return usos[clave]

@bot.message_handler(commands=['perlaoscura'])
def perla_oscura(message):
    """Muestra una perla oscura (requiere consentimiento)"""
    user_id = message.from_user.id
    
    # Verificar si tiene modo oscuro activado
    if not tiene_modo_oscuro(user_id):
        markup = types.InlineKeyboardMarkup()
        btn_activar = types.InlineKeyboardButton("😈 Sí, actívalo", callback_data="oscuro_activar")
        btn_cancelar = types.InlineKeyboardButton("😇 No, mejor no", callback_data="oscuro_cancelar")
        markup.add(btn_activar, btn_cancelar)
        
        bot.reply_to(message,
            "🌑 *PERLA OSCURA*\n\n"
            "Este contenido es irónico, cínico y ácido.\n"
            "Puede herir sensibilidades.\n\n"
            "¿Estás seguro/a de que quieres activar el *modo oscuro*? 😈",
            parse_mode='Markdown',
            reply_markup=markup)
        return
    
    # Verificar límite diario (2 perlas por día)
    usos = obtener_usos_oscura(user_id)
    if usos >= 2:
        # Incrementar para contar intentos extra
        intentos = incrementar_usos_oscura(user_id)
        
        if intentos >= 4:
            bot.reply_to(message,
                "⚫ *NO.*\n\n"
                "La oscuridad ha hablado. Y ha dicho que pares.\n\n"
                "Vuelve. Mañana.",
                parse_mode='Markdown')
        else:
            bot.reply_to(message,
                "🌑 *Se acabó la oscuridad por hoy*\n\n"
                "Ya has recibido tus 2 perlas oscuras diarias.\n"
                "La oscuridad también necesita descansar. 😴\n\n"
                "_Vuelve mañana para más cinismo reconfortante._",
                parse_mode='Markdown')
        return
    
    # Tiene modo oscuro y no ha alcanzado el límite
    incrementar_usos_oscura(user_id)
    perla = random.choice(PERLAS_OSCURAS)
    usos_restantes = 1 - usos  # 0 usos = quedan 2, 1 uso = queda 1
    
    markup = types.InlineKeyboardMarkup()
    if usos_restantes > 0:
        btn_otra = types.InlineKeyboardButton(f"🔄 Otra ({usos_restantes} restante)", callback_data="oscuro_otra")
        markup.add(btn_otra)
    btn_desactivar = types.InlineKeyboardButton("😇 Desactivar modo", callback_data="oscuro_desactivar")
    markup.add(btn_desactivar)
    
    bot.reply_to(message,
        f"🌑 PERLA OSCURA\n\n{perla}",
        reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('oscuro_'))
def handle_modo_oscuro(call):
    """Maneja las acciones del modo oscuro"""
    user_id = call.from_user.id
    accion = call.data.replace('oscuro_', '')
    
    if accion == 'activar':
        toggle_modo_oscuro(user_id)
        incrementar_usos_oscura(user_id)  # Primera perla cuenta
        perla = random.choice(PERLAS_OSCURAS)
        
        markup = types.InlineKeyboardMarkup()
        btn_otra = types.InlineKeyboardButton("🔄 Otra (1 restante)", callback_data="oscuro_otra")
        btn_desactivar = types.InlineKeyboardButton("😇 Desactivar modo", callback_data="oscuro_desactivar")
        markup.add(btn_otra)
        markup.add(btn_desactivar)
        
        bot.edit_message_text(
            f"😈 Modo oscuro activado\n\n🌑 Tu primera perla oscura:\n\n{perla}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup)
        bot.answer_callback_query(call.id, "😈 Bienvenido al lado oscuro")
    
    elif accion == 'cancelar':
        bot.edit_message_text(
            "😇 Sabia decisión\n\nLa ignorancia es felicidad... o eso dicen.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id)
        bot.answer_callback_query(call.id, "😇 Quizás otro día")
    
    elif accion == 'otra':
        if not tiene_modo_oscuro(user_id):
            bot.answer_callback_query(call.id, "⛔ Modo oscuro no activado")
            return
        
        # Verificar límite diario
        usos = obtener_usos_oscura(user_id)
        if usos >= 2:
            bot.edit_message_text(
                "🌑 Se acabó la oscuridad por hoy\n\n"
                "Ya has recibido tus 2 perlas oscuras diarias.\n\n"
                "Vuelve mañana para más cinismo reconfortante.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id)
            bot.answer_callback_query(call.id, "😴 Límite alcanzado")
            return
        
        incrementar_usos_oscura(user_id)
        perla = random.choice(PERLAS_OSCURAS)
        
        markup = types.InlineKeyboardMarkup()
        btn_desactivar = types.InlineKeyboardButton("😇 Desactivar modo", callback_data="oscuro_desactivar")
        markup.add(btn_desactivar)
        
        bot.edit_message_text(
            f"🌑 PERLA OSCURA (última del día)\n\n{perla}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup)
        bot.answer_callback_query(call.id, "🌑")
    
    elif accion == 'desactivar':
        toggle_modo_oscuro(user_id)
        bot.edit_message_text(
            "😇 Modo oscuro desactivado\n\nHas vuelto a la luz. Bienvenido/a de vuelta.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id)
        bot.answer_callback_query(call.id, "😇 Has vuelto a la luz")

@bot.message_handler(commands=['resetpuntos'])
def reset_puntos(message):
    """Resetea los puntos del ranking (solo admin)"""
    # Verificar que es admin
    if str(message.chat.id) != str(CHAT_ID):
        bot.reply_to(message, "⛔ Este comando es solo para administradores.")
        return
    
    puntos = cargar_puntos()
    
    if not puntos:
        bot.reply_to(message, "📊 No hay puntos que resetear.")
        return
    
    # Mostrar resumen antes de borrar
    total_usuarios = len(puntos)
    total_puntos = sum(
        sum(h['puntos'] for h in u.get('historial', []))
        for u in puntos.values()
    )
    
    # Guardar vacío
    guardar_puntos({})
    
    bot.reply_to(message, 
        f"🗑️ *Puntos reseteados*\n\n"
        f"Se eliminaron los datos de {total_usuarios} jugadores "
        f"({total_puntos} puntos totales).\n\n"
        f"_El ranking empieza de cero._",
        parse_mode='Markdown')

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
        
        cat_nombres = {
            'refran': '🎯 Refrán',
            'palabra': '📚 Palabra curiosa',
            'frase': '😂 Frase mítica',
            'mito': '🔍 Mito desmontado'
        }
        cat = cat_nombres.get(next_s.get('categoria', 'frase'), '😂 Frase mítica')
        
        texto = f"📬 *Sugerencia pendiente* ({pendientes_count} en cola)\n\n"
        texto += f"*Categoría:* {cat}\n\n"
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
        
        # Añadir a la lista según categoría
        categoria = s.get('categoria', 'frase')
        texto_original = s['texto']
        
        if categoria == 'refran':
            texto_con_marca = f"{texto_original} (sugerido por {s['usuario']})"
            guardar_refran_aprobado(texto_con_marca)
            tipo_texto = "los refranes"
        elif categoria == 'palabra':
            texto_con_marca = f"{texto_original} (sugerido por {s['usuario']})"
            guardar_palabra_aprobada(texto_con_marca)
            tipo_texto = "las palabras curiosas"
        elif categoria == 'mito':
            # Los mitos son diccionarios {'mito': '...', 'realidad': '...'}
            if isinstance(texto_original, dict):
                mito_con_marca = {
                    'mito': texto_original.get('mito', ''),
                    'realidad': f"{texto_original.get('realidad', '')} (sugerido por {s['usuario']})"
                }
                guardar_mito_aprobado(mito_con_marca)
            else:
                # Mito antiguo en formato string - ignorar
                pass
            tipo_texto = "los mitos desmontados"
        else:
            texto_con_marca = f"{texto_original} (sugerido por {s['usuario']})"
            guardar_frase_aprobada(texto_con_marca)
            tipo_texto = "las frases míticas"
        
        # Notificar al usuario
        chat_id = s.get('chat_id')
        if chat_id:
            try:
                # Formatear texto para notificación
                if isinstance(texto_original, dict):
                    texto_display = f"Mito: {texto_original.get('mito', '')}\nRealidad: {texto_original.get('realidad', '')}"
                else:
                    texto_display = str(texto_original)
                bot.send_message(chat_id, 
                    f"🎉 *¡Tu sugerencia fue aprobada!*\n\n_{texto_display}_\n\n¡Ya está añadida a {tipo_texto} del bot! Gracias por contribuir 🙌",
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
        
        cat_nombres = {
            'refran': '🎯 Refrán',
            'palabra': '📚 Palabra curiosa',
            'frase': '😂 Frase mítica',
            'mito': '🔍 Mito desmontado'
        }
        cat = cat_nombres.get(next_s.get('categoria', 'frase'), '😂 Frase mítica')
        
        texto = f"📬 *Sugerencia pendiente* ({len(pendientes)} en cola)\n\n"
        texto += f"*Categoría:* {cat}\n\n"
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
        texto += "*Signos disponibles:*\n"
        texto += ", ".join(signos)
        msg = bot.reply_to(message, texto, parse_mode='Markdown')
        bot.register_next_step_handler(msg, procesar_signo)
        return
    
    mostrar_horoscopo(message.chat.id, args, message.message_id)

def procesar_signo(message):
    """Procesa el signo enviado por el usuario"""
    if message.text and message.text.startswith('/'):
        return  # Si escribe otro comando, ignorar
    mostrar_horoscopo(message.chat.id, message.text, None)

def mostrar_horoscopo(chat_id, signo, reply_to=None):
    """Muestra el horóscopo para un signo"""
    signo_nombre, prediccion = obtener_horoscopo(signo)
    
    if not signo_nombre:
        # Signo no válido: darle una predicción misteriosa igualmente
        from horoscopo import PREDICCIONES
        prediccion_random = random.choice(PREDICCIONES)
        texto = f"🔮 *HORÓSCOPO IRÓNICO*\n\n"
        texto += f"*¿{signo.title()}?* Eso no es un signo... pero presiento lo que el destino tiene preparado para ti:\n\n"
        texto += f"_{prediccion_random}_"
        bot.send_message(chat_id, texto, parse_mode='Markdown')
        return
    
    texto = f"🔮 *HORÓSCOPO IRÓNICO*\n\n"
    texto += f"*{signo_nombre}*\n\n"
    texto += f"_{prediccion}_"
    
    bot.send_message(chat_id, texto, parse_mode='Markdown')

def ya_jugo_desafio_hoy(user_id):
    """Verifica si el usuario ya jugó el desafío hoy"""
    usos = storage.obtener_dict(REDIS_USOS_DESAFIO)
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    clave = f"{user_id}_{fecha_hoy}"
    return usos.get(clave, False)

def marcar_desafio_jugado(user_id):
    """Marca que el usuario jugó el desafío hoy"""
    usos = storage.obtener_dict(REDIS_USOS_DESAFIO)
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    clave = f"{user_id}_{fecha_hoy}"
    
    # Limpiar usos de días anteriores
    usos = {k: v for k, v in usos.items() if k.endswith(fecha_hoy)}
    
    usos[clave] = True
    storage.guardar_dict(REDIS_USOS_DESAFIO, usos)

@bot.message_handler(commands=['desafio'])
def enviar_desafio(message):
    """Envía un desafío de vocabulario (1 vez al día)"""
    registrar_usuario(message.from_user)
    user_id = message.from_user.id
    
    # Verificar si ya jugó hoy
    if ya_jugo_desafio_hoy(user_id):
        bot.reply_to(message, 
            "🎯 *¡Ya jugaste hoy!*\n\n"
            "El desafío es una vez al día para que sea más especial.\n"
            "Vuelve mañana para poner a prueba tu vocabulario.\n\n"
            "_Mientras tanto, ¿qué tal un /horoscopo?_",
            parse_mode='Markdown')
        return
    
    # NO marcamos aquí - se marca al primer intento en el callback
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
        # Marcar como jugado en el primer intento
        marcar_desafio_jugado(user_id)
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
        
        username = call.from_user.username
        puntos_semana = sumar_puntos(user_id, nombre, pts_ganados, username, intento)
        
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
    user_id = str(message.from_user.id)
    
    if not ranking_semana and not ranking_mes:
        bot.reply_to(message, "📊 Aún no hay puntuaciones. ¡Usa /desafio para jugar!")
        return
    
    medallas = ['🥇', '🥈', '🥉']
    texto = "🏆 *RANKING DEL DESAFÍO*\n"
    texto += "_3 pts al primer intento, 1 pt al segundo_\n\n"
    
    # Ranking semanal (top 3 + posición del usuario si no está)
    texto += "📅 ESTA SEMANA:\n"
    if ranking_semana:
        # Mostrar top 3
        for i, (uid, nombre, username, pts) in enumerate(ranking_semana[:3]):
            medalla = medallas[i]
            nombre_display = f"{nombre} (@{username})" if username else nombre
            texto += f"{medalla} {nombre_display}: {pts} pts\n"
        
        # Si el usuario no está en top 3, mostrar su posición
        pos_usuario = next((i+1 for i, r in enumerate(ranking_semana) if r[0] == user_id), None)
        if pos_usuario and pos_usuario > 3:
            uid, nombre, username, pts = ranking_semana[pos_usuario - 1]
            nombre_display = f"{nombre} (@{username})" if username else nombre
            texto += f"··········\n{pos_usuario}. {nombre_display}: {pts} pts _(tú)_\n"
    else:
        texto += "_Sin puntuaciones aún_\n"
    
    # Ranking mensual (top 3 + posición del usuario si no está)
    meses_es = {1: 'ENERO', 2: 'FEBRERO', 3: 'MARZO', 4: 'ABRIL', 5: 'MAYO', 6: 'JUNIO',
                7: 'JULIO', 8: 'AGOSTO', 9: 'SEPTIEMBRE', 10: 'OCTUBRE', 11: 'NOVIEMBRE', 12: 'DICIEMBRE'}
    mes_nombre = meses_es[datetime.now().month]
    texto += f"\n📆 {mes_nombre}:\n"
    if ranking_mes:
        # Mostrar top 3
        for i, (uid, nombre, username, pts) in enumerate(ranking_mes[:3]):
            medalla = medallas[i]
            nombre_display = f"{nombre} (@{username})" if username else nombre
            texto += f"{medalla} {nombre_display}: {pts} pts\n"
        
        # Si el usuario no está en top 3, mostrar su posición
        pos_usuario = next((i+1 for i, r in enumerate(ranking_mes) if r[0] == user_id), None)
        if pos_usuario and pos_usuario > 3:
            uid, nombre, username, pts = ranking_mes[pos_usuario - 1]
            nombre_display = f"{nombre} (@{username})" if username else nombre
            texto += f"··········\n{pos_usuario}. {nombre_display}: {pts} pts _(tú)_\n"
    else:
        texto += "_Sin puntuaciones aún_\n"
    
    bot.reply_to(message, texto)

@bot.message_handler(commands=['misestadisticas'])
def ver_mis_estadisticas(message):
    """Muestra estadísticas personales del usuario"""
    user_id = str(message.from_user.id)
    puntos = cargar_puntos()
    
    if user_id not in puntos:
        bot.reply_to(message, "📊 Aún no tienes estadísticas. ¡Usa /desafio para empezar a jugar!")
        return
    
    data = puntos[user_id]
    nombre = data.get('nombre', 'Usuario')
    historial = data.get('historial', [])
    
    # Puntos totales
    pts_totales = sum(r['puntos'] for r in historial)
    pts_semana = calcular_puntos_semana(user_id)
    pts_mes = calcular_puntos_mes(user_id)
    
    # Posición en rankings y distancia al siguiente
    ranking_semana = obtener_ranking('semana')
    ranking_mes = obtener_ranking('mes')
    
    pos_semana = next((i+1 for i, r in enumerate(ranking_semana) if r[0] == user_id), None)
    pos_mes = next((i+1 for i, r in enumerate(ranking_mes) if r[0] == user_id), None)
    
    # Calcular distancia al siguiente (al que está por encima)
    dist_semana = None
    dist_mes = None
    if pos_semana and pos_semana > 1:
        pts_anterior_semana = ranking_semana[pos_semana - 2][3]  # índice 3 = puntos
        dist_semana = pts_anterior_semana - pts_semana
    if pos_mes and pos_mes > 1:
        pts_anterior_mes = ranking_mes[pos_mes - 2][3]  # índice 3 = puntos
        dist_mes = pts_anterior_mes - pts_mes
    
    pos_semana = pos_semana or '-'
    pos_mes = pos_mes or '-'
    
    # Calcular estadísticas desde historial (fuente de verdad)
    aciertos_1 = sum(1 for r in historial if r['puntos'] == 3)
    aciertos_2 = sum(1 for r in historial if r['puntos'] == 1)
    aciertos_3plus = data.get('aciertos_3plus', 0)
    jugados = aciertos_1 + aciertos_2 + aciertos_3plus
    
    pct_primera = int((aciertos_1 / jugados) * 100) if jugados > 0 else 0
    pct_segunda = int((aciertos_2 / jugados) * 100) if jugados > 0 else 0
    
    # Racha actual (días consecutivos jugando)
    fechas_jugadas = sorted(set(r['fecha'] for r in historial), reverse=True)
    racha = 0
    hoy = datetime.now().date()
    for i, fecha_str in enumerate(fechas_jugadas):
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        esperada = hoy - timedelta(days=i)
        if fecha == esperada:
            racha += 1
        else:
            break
    
    # Construir mensaje
    texto = f"📊 *ESTADÍSTICAS DE {nombre.upper()}*\n\n"
    texto += f"🏆 *Puntos totales:* {pts_totales}\n"
    texto += f"📅 *Esta semana:* {pts_semana} pts (#{pos_semana})"
    if dist_semana is not None:
        if dist_semana == 0:
            texto += " - ¡empatado con el de arriba!"
        else:
            texto += f" - a {dist_semana} pts del #{pos_semana - 1}"
    texto += "\n"
    texto += f"📆 *Este mes:* {pts_mes} pts (#{pos_mes})"
    if dist_mes is not None:
        if dist_mes == 0:
            texto += " - ¡empatado con el de arriba!"
        else:
            texto += f" - a {dist_mes} pts del #{pos_mes - 1}"
    texto += "\n\n"
    texto += f"🎯 *Desafíos jugados:* {jugados}\n"
    texto += f"✅ *Aciertos a la 1ª:* {aciertos_1} ({pct_primera}%)\n"
    texto += f"🔄 *Aciertos a la 2ª:* {aciertos_2} ({pct_segunda}%)\n\n"
    texto += f"🔥 *Racha actual:* {racha} día{'s' if racha != 1 else ''}\n"
    
    if racha >= 7:
        texto += "\n🌟 _¡Impresionante racha! Sigue así._"
    elif racha >= 3:
        texto += "\n💪 _¡Buena racha! No la rompas._"
    elif racha == 0:
        texto += "\n😴 _Sin racha activa. ¡Juega hoy!_"
    
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
    """Muestra datos de contenido usado (del usuario que pregunta)"""
    estado = cargar_estado()
    usuarios = cargar_usuarios()
    sugerencias = cargar_sugerencias()
    frases_aprobadas = cargar_frases_aprobadas()
    user_id = str(message.from_user.id)
    
    # Conteos del usuario actual
    estado_usuario = estado.get(user_id, {'palabras': [], 'refranes': [], 'frases': []})
    palabras_usadas = len(estado_usuario.get('palabras', []))
    palabras_total = len(obtener_todas_palabras())
    refranes_usados = len(estado_usuario.get('refranes', []))
    refranes_total = len(obtener_todos_refranes())
    frases_usadas = len(estado_usuario.get('frases', []))
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
    texto += f"😂 Frases: {frases_usadas}/{frases_total}"
    
    bot.reply_to(message, texto, parse_mode='Markdown')

def escapar_markdown(texto):
    """Escapa caracteres especiales de Markdown"""
    caracteres = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for c in caracteres:
        texto = texto.replace(c, f'\\{c}')
    return texto

@bot.message_handler(commands=['usuarios'])
def ver_usuarios(message):
    """Muestra la lista de usuarios registrados"""
    try:
        usuarios = cargar_usuarios()
        print(f"Usuarios cargados: {len(usuarios)}")
        if not usuarios:
            bot.reply_to(message, "👥 Aún no hay usuarios registrados.")
            return
        
        texto = f"👥 *USUARIOS DEL BOT* \\({len(usuarios)}\\)\n\n"
        for user_id, data in list(usuarios.items())[-20:]:  # Últimos 20
            nombre = escapar_markdown(data.get('nombre', 'Sin nombre'))
            username = data.get('username')
            ultima = escapar_markdown(data.get('ultima_vez', '?'))
            if username:
                username_escaped = escapar_markdown(username)
                texto += f"• {nombre} \\(@{username_escaped}\\)\n  └ Última vez: {ultima}\n"
            else:
                texto += f"• {nombre}\n  └ Última vez: {ultima}\n"
        
        if len(usuarios) > 20:
            texto += f"\n_\\.\\.\\.y {len(usuarios) - 20} más_"
        
        bot.reply_to(message, texto, parse_mode='MarkdownV2')
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
    
    # Limpiar sesión de Telegram antes de conectar (evita error 409)
    try:
        import requests as req
        TOKEN = os.environ.get('TOKEN')
        req.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook")
        req.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset=-1")
        print("✅ Sesión de Telegram limpiada")
    except Exception as e:
        print(f"⚠️ No se pudo limpiar sesión: {e}")
    
    # Verificar conexión con Telegram
    try:
        bot_info = bot.get_me()
        print(f"✅ Conectado a Telegram como: @{bot_info.username}")
    except Exception as e:
        print(f"❌ Error conectando a Telegram: {e}")
    
    # Iniciar el bot con reintentos
    print("🔄 Iniciando polling...")
    threading.Thread(target=lambda: bot.infinity_polling(timeout=60, long_polling_timeout=30), daemon=True).start()
    print("✅ Bot polling iniciado - ¡TODO OK!")
    
    # Ejecutar el schedule
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    main()