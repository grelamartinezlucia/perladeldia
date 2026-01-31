# 🦪 Bot de las Perlas - Documentación Funcional

Bot de Telegram que envía contenido diario: palabras curiosas, refranes, frases míticas y más.

## 📋 Comandos Disponibles

| Comando | Descripción |
|---------|-------------|
| `/start` | Bienvenida y suscripción automática al mensaje diario |
| `/ahora` | Recibe una perla instantánea (máximo 3 al día) |
| `/desafio` | Quiz de vocabulario con sistema de puntos |
| `/ranking` | Muestra el ranking semanal y mensual del desafío |
| `/sugerir [frase]` | Envía una sugerencia de frase mítica |
| `/horoscopo [signo]` | Horóscopo irónico del día |
| `/stats` | Estadísticas de uso del bot |
| `/datos` | Muestra datos de contenido usado (palabras, refranes, frases) |
| `/usuarios` | Lista de usuarios registrados |
| `/michat` | Muestra tu Chat ID |

---

## 🎯 Funcionalidades

### 1. Mensaje Diario (9:00 AM UTC)
Cada día a las 9:00 UTC, todos los usuarios que hayan hecho `/start` reciben:
- 📚 **Palabra curiosa**: Término poco común con su definición
- 🎯 **Refrán**: Clásico o moderno
- 😂 **Frase mítica**: Citas de amigos
- 📅 **Efeméride**: Evento histórico del día
- 🎉 **Día internacional**: Si aplica

Los usuarios pueden votar la perla del día con 👍 o 👎.

### 2. Desafío de Vocabulario
- Sistema de quiz con 4 opciones
- **Puntuación**:
  - 1º intento correcto: **3 puntos**
  - 2º intento correcto: **1 punto**
  - 3º+ intentos: **0 puntos**
- Rankings semanales (lunes a domingo) y mensuales

### 3. Horóscopo Irónico
Predicciones absurdas para cada signo zodiacal.
- Predicciones genéricas mezcladas con específicas por signo
- **Consistente por día**: Cada signo tiene la misma predicción durante todo el día
- Uso: `/horoscopo aries`, `/horoscopo tauro`, etc.

### 4. Sistema de Sugerencias
Los usuarios pueden sugerir frases míticas con `/sugerir [frase]`.

**Flujo de aprobación:**
1. Usuario envía `/sugerir Mi frase - Autor`
2. Admin usa `/versugerencias` para revisar
3. Aparecen botones: ✅ Aprobar | ❌ Rechazar | ⏭️ Siguiente
4. El usuario recibe notificación automática del resultado

---

## 🏗️ Arquitectura

### Archivos Principales

```
bottelegram/
├── bot.py                    # Lógica principal del bot
├── contenido.py              # Palabras curiosas, refranes, frases
├── dias_internacionales.py   # Calendario de días internacionales
├── efemerides.py             # Eventos históricos curados
├── horoscopo.py              # Predicciones irónicas
├── requirements.txt          # Dependencias Python
└── README.md                 # Esta documentación
```

### Archivos de Datos (generados en runtime)

| Archivo | Contenido |
|---------|-----------|
| `estado_usado.json` | Historial por usuario de contenido ya enviado (evita repeticiones) |
| `usuarios.json` | Registro de usuarios con chat_id para envíos diarios |
| `votos.json` | Historial de votos por fecha |
| `puntos.json` | Puntuaciones del desafío con historial por fecha |
| `sugerencias.json` | Sugerencias enviadas por usuarios |
| `frases_aprobadas.json` | Frases de usuarios aprobadas (se añaden automáticamente al aprobar) |

---

## ⚙️ Configuración

### Variables de Entorno

| Variable | Descripción |
|----------|-------------|
| `TOKEN` | Token del bot obtenido de BotFather |
| `UPSTASH_REDIS_REST_URL` | URL de Upstash Redis para almacenamiento persistente |
| `UPSTASH_REDIS_REST_TOKEN` | Token de autenticación de Upstash Redis |

### Despliegue en Render

1. **Tipo de servicio**: Web Service
2. **Build Command**: `pip install -r requirements.txt`
3. **Start Command**: `python bot.py`
4. **Variables de entorno**: Configurar `TOKEN`, `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`

El bot incluye un servidor HTTP en el puerto 10000 para el health check de Render.

### Mantener Activo

Usar [cron-job.org](https://cron-job.org) para hacer ping cada 14 minutos:
- URL: `https://tu-app.onrender.com/`
- Schedule: `*/14 * * * *`

---

## 📊 Sistema de Puntos

### Estructura de `puntos.json`
```json
{
  "user_id": {
    "nombre": "Nombre del usuario",
    "historial": [
      {"fecha": "2026-01-31", "puntos": 3},
      {"fecha": "2026-01-30", "puntos": 1}
    ]
  }
}
```

### Cálculo de Rankings
- **Semanal**: Suma de puntos desde el lunes de la semana actual
- **Mensual**: Suma de puntos del mes actual

---

## 🔧 Mantenimiento

### Añadir Contenido

- **Palabras curiosas**: Editar `contenido.py` → `PALABRAS_CURIOSAS`
- **Refranes**: Editar `contenido.py` → `REFRANES`
- **Frases míticas**: Editar `contenido.py` → `FRASES_AMIGOS`
- **Días internacionales**: Editar `dias_internacionales.py`
- **Efemérides**: Editar `efemerides.py`
- **Predicciones horóscopo**: Editar `horoscopo.py`

### Resetear Estado
Para volver a usar palabras/refranes ya enviados, eliminar `estado_usado.json`.

### Ver Logs en Render
Los logs muestran:
- Inicio del bot y conexión
- Mensajes diarios enviados (OK/errores)
- Errores de usuarios que bloquearon el bot

---

## 🤖 Configuración en BotFather

### Comandos (usar /setcommands)
```
start - Iniciar el bot y suscribirse
ahora - Perla instantánea
desafio - Quiz de vocabulario
ranking - Ver rankings
sugerir - Sugerir una frase
horoscopo - Horóscopo irónico
```

### Otras Configuraciones
- `/setdescription` - Descripción del bot
- `/setabouttext` - Texto "Acerca de"
- `/setuserpic` - Foto de perfil del bot

---

## 📝 Notas Técnicas

- El bot usa `infinity_polling` en un thread separado
- El scheduler corre en el thread principal
- Los intentos del desafío se guardan en memoria (se pierden si el bot reinicia)
- Wikipedia API se usa como fallback para efemérides no curadas
- **Almacenamiento Redis**: Todos los datos persisten en Upstash Redis
- **Historial por usuario**: Cada usuario tiene su propio historial de contenido visto
- **Límite /ahora**: Máximo 3 usos diarios con mensajes progresivos de advertencia
