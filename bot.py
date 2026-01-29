import telebot
from datetime import datetime
import schedule
import time
import random
import json
import os

# Tu token del BotFather
TOKEN = os.environ.get('TOKEN')
bot = telebot.TeleBot(TOKEN)

# Tu ID de chat
CHAT_ID = os.environ.get('CHAT_ID')

# Archivo para guardar el estado de elementos usados
ESTADO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'estado_usado.json')

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
    "Llego tarde - Maru Espasandín (cada vez que quedas con ella)",
    "Estaba tendiendo la ropa - Tania Eiros cada vez que hizo el amor",
    "Follo, fumo y como cerdo, soy un partidazo para cualquier musulmán - Cris Flores Senegal 2025",
    "Si vienes te enseño mi pimiento - Iván V.S.",
    "Cerra sesión e volve a entrar - Manuel Reyes",
    "Hoy vi un video de un trio, de cómo gestionaban sus gastos y se ahorran pasta - Alicia González",
    "Esto es el chiringuito de peine - Raquel F.S.",

]

def mensaje_diario():
    """Genera el mensaje del día"""
    palabra = obtener_sin_repetir(PALABRAS_CURIOSAS, 'palabras')
    refran = obtener_sin_repetir(REFRANES, 'refranes')
    frase = obtener_sin_repetir(FRASES_AMIGOS, 'frases')
    
    mensaje = f"""
 *PERLA DEL DÍA* 

📚 *Palabra curiosa:*
{palabra}

🎯 *Refrán:*
{refran}

😂 *Frase mítica:*
{frase}

_{datetime.now().strftime("%d/%m/%Y")}_
"""
    return mensaje

def enviar_mensaje():
    """Envía el mensaje al grupo"""
    try:
        bot.send_message(
            CHAT_ID, 
            mensaje_diario(), 
            parse_mode='Markdown'
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
    bot.send_message(message.chat.id, mensaje_diario(), parse_mode='Markdown')

# Mantener el bot corriendo
def main():
    print("Bot iniciado...")
    # Iniciar el bot
    import threading
    threading.Thread(target=bot.infinity_polling, daemon=True).start()
    
    # Ejecutar el schedule
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    main()