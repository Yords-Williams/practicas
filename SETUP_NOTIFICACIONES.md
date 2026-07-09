# 📱 Configurar Notificaciones (Telegram/WhatsApp)

## 🚀 Opción 1: TELEGRAM (RECOMENDADO - Gratis)

### Paso 1: Crear Bot en Telegram

1. Abre Telegram y busca **@BotFather**
2. Envía: `/newbot`
3. Elige un nombre (ej: "CCTV_AI_PRO")
4. Elige un username (ej: "cctv_ai_pro_bot")
5. **Copia el TOKEN** (algo como: `123456789:ABCDefghIjKLmnoPQRstUVWXyz`)

### Paso 2: Obtener tu Chat ID

1. Abre Telegram y busca **@userinfobot**
2. Envía: `/start`
3. Verás tu **User ID** (número largo)
4. O crea un grupo, agrega el bot, y envía: `/start`

### Paso 3: Instalar Telegram Bot

```bash
pip install python-telegram-bot
```

### Paso 4: Configurar

Edita `notifications_config.json` o ejecuta:

```python
import json

config = {
    "telegram": {
        "enabled": True,
        "token": "PEGA_TU_TOKEN_AQUI",
        "chat_id": "PEGA_TU_CHAT_ID_AQUI",
        "send_frame": True,  # Enviar frames de detección
        "include_details": True
    },
    "alert_types": {
        "accident": {"enabled": True, "channels": ["telegram"]},
        "person": {"enabled": True, "channels": ["telegram"]},
        "theft": {"enabled": True, "channels": ["telegram"]}
    }
}

with open("notifications_config.json", 'w') as f:
    json.dump(config, f, indent=2)
```

### Paso 5: Probar

```bash
python notifications.py --test-telegram
```

Deberías recibir un mensaje en Telegram con la alerta ✓

---

## 🟢 Opción 2: WhatsApp vía TWILIO (Profesional)

### Paso 1: Crear cuenta en Twilio

1. Ve a https://www.twilio.com/console
2. Crea una cuenta gratuita
3. Verifica tu teléfono
4. Ve a **Messaging > Try it out > Sandbox**
5. Sigue las instrucciones para activar WhatsApp Sandbox

### Paso 2: Obtener credenciales

En https://www.twilio.com/console:

1. Copia tu **Account SID** (algo como: `ACxxxxxxxxxx`)
2. Copia tu **Auth Token** (algo como: `xxxxxxxxxxxxxx`)
3. Ve a **Phone Numbers > Manage Numbers**
4. Nota el número de Twilio (ej: `+1201xxxxxxx`)

### Paso 3: Instalar Twilio

```bash
pip install twilio
```

### Paso 4: Configurar

```python
import json

config = {
    "twilio": {
        "enabled": True,
        "account_sid": "PEGA_TU_ACCOUNT_SID",
        "auth_token": "PEGA_TU_AUTH_TOKEN",
        "from_number": "+1201xxxxxxx",  # Número de Twilio
        "to_numbers": [
            "+34 6xx xxx xxx",  # Tu número en formato internacional
            "+1 202 555 0173"   # Otros números
        ]
    }
}

with open("notifications_config.json", 'w') as f:
    json.dump(config, f, indent=2)
```

**Formato de números:**
- España: `+34` + número sin el 0
- México: `+52` + número
- Colombia: `+57` + número
- Argentina: `+54` + número
- USA: `+1` + número

### Paso 5: Probar

```bash
python notifications.py --test-whatsapp
```

---

## 📧 Opción 3: Email (Alternativa)

### Paso 1: Configurar Gmail con contraseña de aplicación

1. Ve a https://myaccount.google.com/apppasswords
2. Selecciona **Mail** y **Windows Computer**
3. Copia la contraseña de 16 caracteres

### Paso 2: Configurar

```python
config = {
    "email": {
        "enabled": True,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "sender": "tu_email@gmail.com",
        "password": "xxxx xxxx xxxx xxxx",  # Contraseña de aplicación
        "recipients": [
            "receptor1@gmail.com",
            "receptor2@hotmail.com"
        ],
        "include_frame": True
    }
}
```

---

## ⚙️ Integración con Módulos de Detección

### Accidentes

```python
from notifications import NotificationManager

nm = NotificationManager()

# En accident_detection.py
if collision_detected:
    nm.send_accident_alert(
        camera="Cámara Principal",
        severity="CRÍTICO",
        frame_path="detected_frame.jpg",
        details=f"Velocidad: {velocity} km/h, Tipo: {collision_type}"
    )
```

### Personas

```python
# En person_identifier.py
if person_detected:
    nm.send_person_alert(
        camera="Cámara Entrada",
        person_id=track_id,
        details=f"Confianza: {confidence*100:.1f}%"
    )
```

### Robos/Amenazas

```python
# En robo_detector.py
if weapon_detected or threat_detected:
    nm.send_theft_alert(
        camera="Cámara Parque",
        threat_type="Arma detectada" if weapon_detected else "Objeto sospechoso",
        confidence=confidence,
        details=f"Localización: {location}, Velocidad: {speed}"
    )
```

---

## 🔧 Control de Alertas (Anti-Spam)

### Evitar demasiadas notificaciones

En `notifications_config.json`:

```json
{
  "cooldown_seconds": 60,
  "alert_types": {
    "accident": {
      "enabled": true,
      "min_severity": "ALTO",
      "channels": ["telegram", "twilio"]
    },
    "person": {
      "enabled": false,
      "channels": ["telegram"]
    },
    "theft": {
      "enabled": true,
      "channels": ["telegram", "twilio"]
    }
  }
}
```

**Parámetros:**
- `cooldown_seconds`: Mínimo tiempo entre alertas del mismo tipo
- `enabled`: Habilitar/deshabilitar tipo de alerta
- `channels`: Por dónde enviar (telegram/twilio/email)

---

## 📊 Ver Historial de Alertas

```bash
python notifications.py --show-history
```

Muestra las últimas 10 alertas registradas.

---

## 🐛 Solucionar Problemas

### "Telegram no está instalado"
```bash
pip install python-telegram-bot
```

### "Token inválido" en Telegram
- Verifica que el token sea correcto (sin espacios)
- Prueba: `python -c "from telegram import Bot; Bot('TU_TOKEN').get_me()"`

### "Error enviando WhatsApp"
- Verifica el formato de números: `+[país][número]`
- Asegúrate de tener el Sandbox de Twilio activado
- Comprueba que tus credenciales sean correctas

### "No recibo las notificaciones"
- Verifica que `enabled: true` en cada servicio
- Comprueba `chat_id` (Telegram) o `to_numbers` (WhatsApp)
- Ejecuta: `python notifications.py --test-telegram`

---

## 💰 Costos

| Servicio | Costo | Límite |
|----------|-------|--------|
| **Telegram** | Gratis | Ilimitado |
| **Twilio** | $0.001/SMS | Pay-as-you-go |
| **Email** | Gratis | Ilimitado |

---

## 📌 Próximos Pasos

1. ✅ Instala `python notifications.py --test-telegram`
2. ✅ Prueba con una alerta: `python notifications.py --test-all`
3. ✅ Integra en `main.py` para inicializar notificaciones al arrancar
4. ✅ Personaliza `cooldown_seconds` según tus necesidades

¡Listo! Ahora recibirás notificaciones cuando se detecten accidentes, personas o robos.
