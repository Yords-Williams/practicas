# 🟣 META WHATSAPP API - SETUP GRATIS (10 MIN)

## 🎯 VENTAJAS
- ✅ $0 completamente gratis
- ✅ Ilimitado en sandbox
- ✅ Oficial de Meta/Facebook
- ✅ Perfecto para menos de 10 alertas/día

## ⏱️ TIEMPO TOTAL: 10 MINUTOS

---

## PASO 1: Crear App en Meta (3 min)

1. Ve a **https://developers.facebook.com**
2. Si no tienes cuenta, click **"Sign Up"** (o inicia sesión)
3. Click en **"Create App"**
4. Selecciona **"Business"**
5. Completa:
   ```
   App Name: CCTV Alerts
   App Contact Email: tu_email@gmail.com
   App Purpose: Other (o "Business Tools")
   ```
6. Click **"Create App"**

---

## PASO 2: Agregar WhatsApp a la App (2 min)

1. En el dashboard, verás "Add Products"
2. Busca **"WhatsApp"**
3. Click en **"Set Up"**
4. Sigue el asistente de configuración
5. Selecciona **"Business"**

---

## PASO 3: Obtener Phone Number ID (3 min)

1. En la app, ve a **WhatsApp** → **Getting Started**
2. Verifica tu número de teléfono:
   ```
   País: Spain (+34)
   Teléfono: Tu número (678 123 456)
   ```
3. Recibirás código en WhatsApp
4. Entra el código
5. **COPIA el "Phone Number ID"** (algo como: `1234567890`)

---

## PASO 4: Generar Access Token (2 min)

1. En https://developers.facebook.com/tools/explorer
2. En la parte superior izquierda, selecciona tu app
3. Click en **"Generate Access Token"**
4. Selecciona **"Temporarily"** (válido 2 horas)
5. **COPIA el token** (cadena larga de caracteres)

---

## PASO 5: Configurar en Python (1 min)

Crea `meta_whatsapp_config.json`:

```json
{
  "meta": {
    "phone_id": "PEGA_AQUI_TU_PHONE_ID",
    "access_token": "PEGA_AQUI_TU_ACCESS_TOKEN",
    "to_numbers": ["+34678123456"]
  }
}
```

**Reemplaza:**
- `PEGA_AQUI_TU_PHONE_ID` = De Paso 3
- `PEGA_AQUI_TU_ACCESS_TOKEN` = De Paso 4
- `+34678123456` = Tu número

---

## PASO 6: Probar (1 min)

```bash
cd C:\Users\LENOVO\Documents\cctv_ai_pro
.\venv311\Scripts\python.exe meta_whatsapp.py --test
```

Deberías recibir en WhatsApp:
```
✅ TEST META WHATSAPP

🟣 Sistema funcionando correctamente

CCTV AI PRO
```

---

## 🔄 PROBLEMA: Access Token Caduca

El token temporal dura 2 horas. Para uso permanente:

1. Ve a **Settings** → **Basic**
2. Copia **App Secret**
3. Crea un **Long-Lived Token**:

```python
import requests

def get_long_lived_token(short_token, app_secret):
    url = "https://graph.instagram.com/v18.0/oauth/access_token"
    
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": "APP_ID",
        "client_secret": app_secret,
        "fb_exchange_token": short_token
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    return data['access_token']  # Válido 60 días
```

O más fácil: **En el API Explorer, selecciona "Get long-lived token"**

---

## 📱 INTEGRACIÓN EN TUS MÓDULOS

### En `modulos/accident_detection.py`:

```python
from meta_whatsapp import MetaWhatsAppNotifier

notifier = MetaWhatsAppNotifier()

if collision_detected:
    notifier.send_accident_alert(
        camera="Cámara Principal",
        severity="CRÍTICO",
        details=f"Velocidad: {velocity} km/h"
    )
```

### En `modulos/robo_detector.py`:

```python
from meta_whatsapp import MetaWhatsAppNotifier

notifier = MetaWhatsAppNotifier()

if weapon_detected:
    notifier.send_threat_alert(
        camera="Cámara Entrada",
        threat_type="Arma detectada",
        details="Zona crítica"
    )
```

---

## 💰 COSTOS

```
Costo inicial: $0
Costo mensual: $0 (sandbox gratis)
Limite alertas: Ilimitadas en sandbox
Duración: Indefinida

Para producción (después):
- Meta cobra ~$0.002-0.01 por mensaje
- Pero todavía es gratis en sandbox
```

---

## ⚠️ LIMITACIONES DEL SANDBOX

```
✓ Puedes enviar ilimitados mensajes
✓ A números que TÚ agregues
✗ Solo a números verificados por ti

SOLUCIÓN:
Agrega más números en WhatsApp → Settings
```

---

## 🚀 COMANDOS ÚTILES

```bash
# Probar conexión
python meta_whatsapp.py --test

# Enviar alerta de accidente
python meta_whatsapp.py --send-accident

# Enviar alerta de amenaza
python meta_whatsapp.py --send-threat

# Ver configuración
python -c "import json; print(json.dumps(json.load(open('meta_whatsapp_config.json')), indent=2))"
```

---

## ✅ CHECKLIST

```
☑️ Cuenta en developers.facebook.com
☑️ App creada
☑️ WhatsApp agregado
☑️ Número verificado
☑️ Phone ID copiado
☑️ Access Token generado
☑️ meta_whatsapp_config.json creado
☑️ Prueba exitosa
```

---

## 📊 COMPARATIVA: META vs TWILIO

| Aspecto | Meta | Twilio |
|---------|------|--------|
| Costo inicial | $0 | $20 |
| Costo mensual | $0 | $0.07 |
| Setup | 10 min | 5 min |
| Para menos de 10 alertas/día | ✅ Mejor | ⚠️ Overkill |
| Para producción | ⚠️ Requiere upgrade | ✅ Listo |

---

## 🎯 RECOMENDACIÓN

**PARA TI (menos de 10 alertas/día):**
✅ **Meta API (GRATIS)**

```bash
python meta_whatsapp.py --test
```

¡Listo! Sin gastar nada.

---

¿Preguntas? Avísame en cualquier paso.
