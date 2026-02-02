# Horóscopo irónico - Predicciones absurdas
import random
from datetime import datetime

SIGNOS = {
    "aries": "♈ Aries (21 mar - 19 abr)",
    "tauro": "♉ Tauro (20 abr - 20 may)",
    "geminis": "♊ Géminis (21 may - 20 jun)",
    "cancer": "♋ Cáncer (21 jun - 22 jul)",
    "leo": "♌ Leo (23 jul - 22 ago)",
    "virgo": "♍ Virgo (23 ago - 22 sep)",
    "libra": "♎ Libra (23 sep - 22 oct)",
    "escorpio": "♏ Escorpio (23 oct - 21 nov)",
    "sagitario": "♐ Sagitario (22 nov - 21 dic)",
    "capricornio": "♑ Capricornio (22 dic - 19 ene)",
    "acuario": "♒ Acuario (20 ene - 18 feb)",
    "piscis": "♓ Piscis (19 feb - 20 mar)",
}

# Predicciones genéricas absurdas
PREDICCIONES = [
    "Hoy es un gran día para no hacer absolutamente nada productivo.",
    "Los astros indican que deberías comer pizza. Los astros siempre tienen razón.",
    "Mercurio está retrógrado, así que puedes culparle de todo lo que salga mal.",
    "Tu color de la suerte es el beige. Sí, así de emocionante será tu día.",
    "Alguien pensará en ti hoy. Probablemente para quejarse.",
    "Es un buen momento para invertir... en más horas de sueño.",
    "Hoy tendrás una revelación importante: necesitas café.",
    "Las estrellas sugieren que ignores este horóscopo. Pero ya es tarde.",
    "Tu alma gemela está cerca. En algún lugar del universo. Probablemente muy lejos.",
    "Evita discusiones hoy. O no. Los astros pasan de ti, sinceramente.",
    "Tendrás suerte en el amor si defines 'amor' como 'pizza'.",
    "Hoy es perfecto para empezar ese proyecto que nunca terminarás.",
    "Los planetas se alinean para recordarte que deberías beber más agua.",
    "Tu número de la suerte es el 404: no encontrado.",
    "Alguien te mandará un mensaje. Será spam.",
    "Hoy descubrirás que la ropa del suelo estaba limpia todo el tiempo.",
    "Venus entra en tu casa del dinero. Por favor, cierra con llave.",
    "Es un día excelente para responder ese email que llevas ignorando 3 meses.",
    "Los astros recomiendan que finjas estar ocupado/a en el trabajo.",
    "Hoy sentirás una conexión especial... con el WiFi del vecino.",
    "La Luna llena te dará energía para quedarte despierto/a viendo series.",
    "Tendrás un encuentro inesperado con el filo de la mesita.",
    "Tu talento oculto se revelará hoy: dormir con los ojos abiertos.",
    "Saturno dice que dejes de procrastinar. Pero mañana.",
    "Hoy es el día perfecto para comprar cosas que no necesitas.",
    "Los astros predicen que dirás 'último episodio' al menos 5 veces.",
    "Tu destino está escrito en las estrellas. Pero tienen muy mala letra.",
    "Recibirás dinero inesperado. Ah no, espera, era una factura.",
    "Marte sugiere que te quedes en casa. Marte es muy sabio.",
    "Júpiter favorece las decisiones impulsivas. Cómprate eso.",
    "Plutón quiere que sepas que ya no es un planeta y que le dejes en paz.",
    "Hoy es buen día para empezar una dieta. Mañana también lo será.",
    "Tu horóscopo estaba muy interesante pero se me olvidó.",
    "Los signos indican que deberías dejar de creer en los signos.",
    "El universo conspira a tu favor. Pero hoy tenía el día libre.",
    "Hoy conocerás a alguien especial. Tu yo del espejo cuenta.",
    "Las cartas dicen que deberías dejar de mezclar la ropa de color.",
    "Neptuno entra en tu casa del amor. Trae chanclas, el suelo está frío.",
    "Hoy tendrás claridad mental después del tercer café.",
    "Los astros recomiendan que no leas los términos y condiciones. Nunca.",
    "Tu chakra del wifi está bloqueado. Reinicia el router.",
    "Urano sugiere que pruebes cosas nuevas. Como levantarte antes de las 12.",
    "Hoy es un día para reflexionar. Sobre por qué no hay nada en la nevera.",
    "Las estrellas indican que ese mensaje sin responder seguirá sin responder.",
    "Tu aura necesita recargarse. Prueba con una siesta de 4 horas.",
    "Mercurio dice que ese ex va a escribirte. Mercurio es borde.",
    "Hoy el karma te devolverá algo. Probablemente ese tupperware.",
    "Los planetas favorecen las excusas creativas para no ir al gimnasio.",
    "Venus dice que mereces amor. Pero primero, mereces desayunar.",
    "Hoy descubrirás que ese ruido raro era tu estómago todo el tiempo.",
    "El cosmos susurra tu nombre. Y luego se ríe. Sin motivo aparente.",
    "Las estrellas predicen que llegarás tarde. Como siempre.",
    "Hoy tendrás un momento de inspiración. Lo olvidarás en 3 segundos.",
    "La luna nueva trae cambios. Como cambiar de postura en el sofá.",
    "Tu signo solar dice que dejes de stalkear a tu ex. Tu signo lunar también.",
    "Los astros confirman: esa notificación no era importante.",
    "Hoy es buen día para invertir en criptomonedas. Es broma. Los astros también ríen.",
    "El eclipse afectará tus finanzas. Culpa al eclipse de todo.",
    "Marte entra en tu signo. Trae pizzas.",
    "Hoy tu intuición estará afilada. Úsala para elegir qué serie ver.",
    "Los astros dicen que ese plan se va a cancelar. Ya lo sabías.",
    "Tu energía cósmica hoy es modo ahorro. Consérvala para mañana.",
    "Saturno te recuerda que ese gimnasio sigue cobrándote sin ir.",
    "Hoy el universo te enviará una señal. La ignorarás, como siempre.",
    "Las constelaciones indican que necesitas unas vacaciones. O una siesta.",
    "Tu horóscopo de hoy: sí, pero con pereza.",
    "Los planetas sugieren que dejes de mirar el móvil. Empezando mañana.",
    "Hoy sentirás motivación a las 23:59. Como siempre.",
    "El cosmos te pregunta: ¿de verdad necesitas eso en el carrito de Amazon?",
    "Venus susurra que te quieras. Empieza por no saltarte comidas.",
    "Júpiter dice que mereces ese postre. Júpiter nunca falla.",
    "Hoy tendrás una conversación incómoda. Contigo mismo en el espejo.",
    "Los astros predicen que dirás 'ahora voy' y no irás.",
    "Tu carta astral indica talento oculto para ignorar alarmas.",
    "Neptuno sugiere que te hidrates. Con café también vale.",
    "Hoy el destino pondrá a prueba tu paciencia. Cola del súper.",
    "Las estrellas avisan: ese 'luego lo hago' no va a pasar.",
    "Mercurio retrógrado justifica todos tus errores de hoy. De nada.",
    "Tu luna emocional pide que llores viendo videos de perritos.",
    "Los astros recomiendan fingir que leíste ese correo largo.",
    "Hoy es buen día para empezar algo nuevo. Tipo nueva temporada de serie.",
    "El universo te apoya. Desde lejos. Muy lejos.",
    "Tu ascendente dice que mereces un día tranquilo. El mundo no opina igual.",
    "Plutón, aunque no sea planeta, cree en ti. Algo es algo.",
    "Hoy tu aura brillará. O es el brillo de la pantalla. Difícil saberlo.",
    "Los signos indican que ese 'ahora mismo' significaba 'en una hora'.",
    "Marte te da energía para empezar cosas. No para terminarlas.",
    "El horóscopo de hoy se resume en: haz lo que puedas, eso ya es mucho.",
]

# Predicciones específicas por signo (opcionales, añaden variedad)
PREDICCIONES_SIGNO = {
    "aries": [
        "Tu impulsividad hoy te llevará a... abrir la nevera sin hambre.",
        "Lidera con el ejemplo: sé el primero en irte del trabajo.",
    ],
    "tauro": [
        "Hoy mereces darte un capricho. Y mañana. Y pasado.",
        "Tu terquedad hoy se manifestará discutiendo con el GPS.",
    ],
    "geminis": [
        "Hoy tendrás dos opiniones sobre todo. Ambas correctas, obviamente.",
        "Tu dualidad brilla: querrás socializar desde tu cama.",
    ],
    "cancer": [
        "Hoy sentirás nostalgia por algo que pasó hace 5 minutos.",
        "Tu instinto protector se activará: esconderás las galletas.",
    ],
    "leo": [
        "El mundo girará a tu alrededor hoy. Como siempre, vaya.",
        "Brillarás tanto que alguien te pedirá que bajes el brillo.",
    ],
    "virgo": [
        "Encontrarás un error que nadie más ve. Como siempre.",
        "Tu organización alcanzará nuevos niveles: ordenarás los emojis.",
    ],
    "libra": [
        "Hoy tomarás una decisión. Después de 47 horas de deliberación.",
        "Tu equilibrio interior se tambalea: ¿pizza o sushi?",
    ],
    "escorpio": [
        "Alguien te mirará raro. Tú ya sabías que lo haría.",
        "Tu intensidad hoy asustará a alguien. Probablemente a ti mismo/a.",
    ],
    "sagitario": [
        "Planearás un viaje que nunca harás. Es la tradición.",
        "Tu optimismo chocará con la realidad. Apuesta por el optimismo.",
    ],
    "capricornio": [
        "Trabajarás duro hoy. También mañana. No conoces otra cosa.",
        "Tu ambición te llevará lejos: hasta la máquina de café.",
    ],
    "acuario": [
        "Tendrás una idea revolucionaria que nadie entenderá.",
        "Tu rareza será apreciada hoy. Por otras personas raras.",
    ],
    "piscis": [
        "Soñarás despierto/a la mayor parte del día. Como siempre.",
        "Tu intuición te dice algo. Ni idea de qué, pero algo.",
    ],
}

def obtener_horoscopo(signo):
    """Genera un horóscopo irónico para un signo (consistente por día)"""
    signo = signo.lower().strip()
    signo = signo.replace("é", "e").replace("á", "a")  # geminis, cancer
    
    if signo not in SIGNOS:
        return None, None
    
    # Crear semilla determinista: fecha + signo = misma predicción todo el día
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    semilla = hash(f"{fecha_hoy}_{signo}") % (2**32)
    rng = random.Random(semilla)
    
    # 30% probabilidad de predicción específica del signo
    if signo in PREDICCIONES_SIGNO and rng.random() < 0.3:
        prediccion = rng.choice(PREDICCIONES_SIGNO[signo])
    else:
        prediccion = rng.choice(PREDICCIONES)
    
    return SIGNOS[signo], prediccion

def listar_signos():
    """Devuelve la lista de signos disponibles"""
    return list(SIGNOS.keys())
