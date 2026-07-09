# 🟢 SETUP TWILIO + WHATSAPP

## ⚡ PASO 1: Crear Cuenta Twilio (2 min)

1. Ve a https://www.twilio.com/try-twilio
2. Haz click en **"Sign up"**
3. Rellena:
   ```
   Email: tu_email@gmail.com
   Contraseña: (segura)
   Nombre completo: Tu nombre
   País: España (o tu país)
   ```
4. Verifica tu email (recibirás enlace de confirmación)

---

## 💳 PASO 2: Agregar Tarjeta (IMPORTANTE)

1. **En el dashboard**, ve a **Account** (esquina superior derecha)
2. Click en **"Billing"** → **"Billing Overview"**
3. Click en **"Payment Methods"** (o "Add payment method")
4. Click **"Add a payment method"**
5. **Selecciona "Credit Card"**
6. Ingresa:
   ```
   Titular: TU NOMBRE COMPLETO (como aparece en tarjeta)
   Número: 1234 5678 9012 3456
   Vencimiento: MM/YY
   CVC: 123
   Código postal: Tu código postal
   País: España
   ```
7. Click **"Add Card"**

**Tarjetas que funcionan:**
- ✅ Visa
- ✅ Mastercard  
- ✅ American Express
- ✅ Discover

---

## 🔑 PASO 3: Obtener Credenciales

1. Ve a https://www.twilio.com/console
2. **EN LA PÁGINA PRINCIPAL**, verás:
   ```
   Account SID:   ACxxxxxxxxxxxxxxxxxxxxxxxxxx
   Auth Token:    xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
3. **COPIA Y PEGA ambos valores en un lugar seguro**

---

## 📱 PASO 4: Activar WhatsApp Sandbox

1. Ve a https://www.twilio.com/console/sms/whatsapp/sandbox
2. Haz click en **"Activate Sandbox"**
3. Lee y acepta los términos
4. **Verifica tu teléfono:**
   - Recibirás un código en WhatsApp
   - Sigue las instrucciones
5. **COPIA el número de Twilio que aparece:**
   ```
   Algo como: +1 201 555 0123
   ```

---

## ⚙️ PASO 5: Instalar Twilio en Python

```bash
cd C:\Users\LENOVO\Documents\cctv_ai_pro
.\venv311\Scripts\pip install twilio
```

---

## 📝 PASO 6: Crear notifications_config.json

Abre el archivo `notifications_config.json` (si no existe, créalo) y pon esto:

```json
{
  "twilio": {
    "enabled": true,
    "account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "auth_token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "from_number": "+1 201 555 0123",
    "to_numbers": [
      "+34 678 123 456"
    ]
  },
  "telegram": {
    "enabled": false
  },
  "alert_types": {
    "accident": {
      "enabled": true,
      "channels": ["twilio"]
    },
    "person": {
      "enabled": true,
      "channels": ["twilio"]
    },
    "theft": {
      "enabled": true,
      "channels": ["twilio"]
    }
  },
  "cooldown_seconds": 60
}
```

**Reemplaza:**
- `ACxxxxxxxxxxxxxxxxxxxxxxxxxx` = Tu Account SID (paso 3)
- `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` = Tu Auth Token (paso 3)
- `+1 201 555 0123` = Número de Twilio (paso 4)
- `+34 678 123 456` = **Tu número en formato internacional**

---

## 🌍 FORMATOS DE NÚMERO POR PAÍS

```
España:      +34 + número sin el 0
  Ej: 678 123 456 → +34678123456

México:      +52 + número sin 01
  Ej: 55 1234 5678 → +5551234567

Colombia:    +57 + número
  Ej: 300 123 4567 → +573001234567

Argentina:   +54 + número sin 0
  Ej: 911 2345 6789 → +549112345678

Chile:       +56 + número
  Ej: 987 654 321 → +56987654321

Perú:        +51 + número
  Ej: 987 654 321 → +51987654321
```

---

## ✅ PASO 7: Probar la Conexión

```bash
cd C:\Users\LENOVO\Documents\cctv_ai_pro
.\venv311\Scripts\python.exe notifications.py --test-whatsapp
```

**Deberías recibir en WhatsApp:**
```
🚨 ALERTA DE SEGURIDAD
Cámara: Cámara Test
Tipo: Objeto sospechoso
Confianza: 87%
Detalles: Prueba de sistema de alertas
Hora: 14:35:22
```

Si **NO recibes nada**, verifica:
- ✓ Account SID correcto
- ✓ Auth Token correcto
- ✓ Número de Twilio correcto (+1 201...)
- ✓ Tu número en formato +[país][número]
- ✓ Sandbox activado (Paso 4)
- ✓ Tarjeta agregada (Paso 2)

---

## 🔗 PASO 8: Integrar en los Módulos

### En `modulos/accident_detection.py`:

```python
from notifications import NotificationManager

nm = NotificationManager()

# Cuando detectes accidente:
if collision_detected:
    nm.send_accident_alert(
        camera="Cámara Principal",
        severity="CRÍTICO",
        details=f"Velocidad: {velocity} km/h"
    )
```

### En `modulos/robo_detector.py`:

```python
from notifications import NotificationManager

nm = NotificationManager()

# Cuando detectes amenaza:
if weapon_detected:
    nm.send_theft_alert(
        camera="Cámara Entrada",
        threat_type="Arma detectada",
        confidence=0.95,
        details="Zona de entrada"
    )
```

### En `modulos/person_identifier.py`:

```python
from notifications import NotificationManager

nm = NotificationManager()

# Cuando identifiques persona:
nm.send_person_alert(
    camera="Cámara Salida",
    person_id="P001",
    details=f"Confianza: {confidence*100:.1f}%"
)
```

---

## 💰 COSTOS

```
Por cada alerta enviada:
- Primer mensaje: $0.0100
- Mensajes siguientes: $0.0070

EJEMPLO DE GASTOS:
- 1 alerta/día = $0.21/mes
- 10 alertas/día = $2.10/mes
- 50 alertas/día = $10.50/mes
- 100 alertas/día = $21/mes

⏰ Atención: Se cobra por mensaje, no por intento
```

---

## 🐛 SOLUCIONAR PROBLEMAS

### "Authentication Failed"
```
❌ Account SID o Auth Token incorrecto
✅ Copia exactamente (sin espacios)
✅ Ve a https://www.twilio.com/console
```

### "Invalid phone number format"
```
❌ +34678 123 456 (espacios)
❌ 34678123456 (sin +)
✅ +34678123456 (correcto)
```

### "Message Not Sent"
```
❌ Tarjeta no confirmada
✅ Vuelve a Billing → Payment Methods
✅ Asegúrate de que esté con ✓
```

### "Sandbox not active"
```
❌ No activaste el sandbox
✅ Ve a https://www.twilio.com/console/sms/whatsapp/sandbox
✅ Click "Activate Sandbox"
✅ Verifica tu número
```

### "No recibo mensajes"
```
✅ Espera 1-2 segundos (latencia de red)
✅ Revisa WhatsApp (puede estar en "Otros chats")
✅ Prueba: python notifications.py --test-whatsapp
✅ Verifica que tu número esté en to_numbers
```

---

## 📊 VER MENSAJES ENVIADOS

En el dashboard de Twilio:
1. Ve a https://www.twilio.com/console/sms/logs
2. Ves todos los mensajes enviados
3. Puedes ver errores si los hay

---

## ✨ LISTO

Ya tienes WhatsApp configurado. Ahora:

1. ✅ Crea `notifications_config.json`
2. ✅ Prueba: `python notifications.py --test-whatsapp`
3. ✅ Integra en los módulos
4. ✅ **¡Recibe alertas en WhatsApp!**

---

## 🆘 ¿PROBLEMAS?

Si algo no funciona:
```bash
# Ver configuración actual:
python notifications.py --show-config

# Ver historial:
python notifications.py --show-history

# Probar manualmente:
python -c "from twilio.rest import Client; Client('ACxxx', 'xxx').messages.create(from_='whatsapp:+1201xxx', to='whatsapp:+34xxx', body='Test')"
```

---

¡Cualquier duda, avísame! 🚀
