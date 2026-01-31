# Módulo de almacenamiento persistente con Upstash Redis
import os
import json
from upstash_redis import Redis

# Configuración de Redis
REDIS_URL = os.environ.get('UPSTASH_REDIS_REST_URL')
REDIS_TOKEN = os.environ.get('UPSTASH_REDIS_REST_TOKEN')

# Cliente Redis (None si no hay credenciales)
redis_client = None
if REDIS_URL and REDIS_TOKEN:
    try:
        redis_client = Redis(url=REDIS_URL, token=REDIS_TOKEN)
        print("✅ Conectado a Upstash Redis")
    except Exception as e:
        print(f"⚠️ Error conectando a Redis: {e}")

def redis_disponible():
    """Verifica si Redis está disponible"""
    return redis_client is not None

def obtener(clave, default=None):
    """Obtiene un valor de Redis"""
    if not redis_client:
        return default
    try:
        valor = redis_client.get(clave)
        if valor is None:
            return default
        return json.loads(valor) if isinstance(valor, str) else valor
    except Exception as e:
        print(f"Error leyendo {clave}: {e}")
        return default

def guardar(clave, valor):
    """Guarda un valor en Redis"""
    if not redis_client:
        return False
    try:
        redis_client.set(clave, json.dumps(valor, ensure_ascii=False))
        return True
    except Exception as e:
        print(f"Error guardando {clave}: {e}")
        return False

def obtener_lista(clave):
    """Obtiene una lista de Redis"""
    return obtener(clave, [])

def guardar_lista(clave, lista):
    """Guarda una lista en Redis"""
    return guardar(clave, lista)

def obtener_dict(clave):
    """Obtiene un diccionario de Redis"""
    return obtener(clave, {})

def guardar_dict(clave, diccionario):
    """Guarda un diccionario en Redis"""
    return guardar(clave, diccionario)
