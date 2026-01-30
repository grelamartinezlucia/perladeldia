# Horóscopo irónico - Predicciones absurdas
import random

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
    """Genera un horóscopo irónico para un signo"""
    signo = signo.lower().strip()
    signo = signo.replace("é", "e").replace("á", "a")  # geminis, cancer
    
    if signo not in SIGNOS:
        return None, None
    
    # 30% probabilidad de predicción específica del signo
    if signo in PREDICCIONES_SIGNO and random.random() < 0.3:
        prediccion = random.choice(PREDICCIONES_SIGNO[signo])
    else:
        prediccion = random.choice(PREDICCIONES)
    
    return SIGNOS[signo], prediccion

def listar_signos():
    """Devuelve la lista de signos disponibles"""
    return list(SIGNOS.keys())
