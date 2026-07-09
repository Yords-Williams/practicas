#!/usr/bin/env python3
"""
Asistente Interactivo de Configuración Twilio
Uso: python setup_twilio_interactive.py
"""

import json
import os
import sys

def print_header(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def get_input(prompt, required=True, pattern=None):
    """Obtener input del usuario con validación opcional"""
    while True:
        value = input(prompt).strip()
        
        if not value and required:
            print("⚠️  Este campo es requerido")
            continue
        
        if pattern and value:
            if not value.startswith(pattern):
                print(f"⚠️  Debe comenzar con '{pattern}'")
                continue
        
        return value

def format_phone(phone):
    """Formatear número de teléfono"""
    return phone.replace(" ", "")

def main():
    print_header("🟢 ASISTENTE TWILIO + WHATSAPP")
    
    print("""
Este asistente te guiará para configurar Twilio y enviar alertas
por WhatsApp desde tu sistema CCTV.

Necesitarás:
  ✓ Una tarjeta de crédito (Visa, Mastercard, Amex)
  ✓ Tu número de teléfono
  ✓ Acceso a email para verificación
  
Costo: ~$0.01 por alerta (muy barato)
    """)
    
    input("Presiona ENTER para continuar...")
    
    # PASO 1: Obtener credenciales
    print_header("PASO 1: OBTENER CREDENCIALES DE TWILIO")
    
    print("""
1. Ve a https://www.twilio.com/console
2. En la página principal, encontrarás:
   - Account SID (comienza con AC)
   - Auth Token (cadena larga de caracteres)
3. COPIA ambos valores""")
    
    account_sid = get_input("\n📋 Pega tu Account SID: ", pattern="AC")
    auth_token = get_input("📋 Pega tu Auth Token: ")
    
    # PASO 2: Número de Twilio
    print_header("PASO 2: NÚMERO DE TWILIO")
    
    print("""
1. Ve a https://www.twilio.com/console/sms/whatsapp/sandbox
2. Haz click en "Activate Sandbox"
3. Verifica tu número de teléfono
4. Copia el número de Twilio (algo como +1 201 555 0123)""")
    
    twilio_number = get_input("\n📱 Pega el número de Twilio: ", pattern="+")
    
    # PASO 3: Tu número de teléfono
    print_header("PASO 3: TU NÚMERO DE TELÉFONO")
    
    print("""
Formatos por país:
  España:    +34 + número (sin el 0)
  México:    +52 + número
  Colombia:  +57 + número
  Argentina: +54 + número
  Chile:     +56 + número
  Perú:      +51 + número
  USA:       +1 + número

Ejemplo España:
  Tu número: 678 123 456
  Formato:   +34678123456""")
    
    your_number = get_input("\n📱 Pega tu número en formato internacional: ", pattern="+")
    
    # PASO 4: Números adicionales (opcional)
    print_header("PASO 4: NÚMEROS ADICIONALES (Opcional)")
    
    print("""
¿Quieres que las alertas se envíen a otros números también?
(presiona ENTER si solo quieres tu número)""")
    
    additional_numbers = []
    while True:
        extra = get_input("\n📱 Otro número (o ENTER para continuar): ", required=False)
        if not extra:
            break
        additional_numbers.append(extra)
    
    all_numbers = [your_number] + additional_numbers
    
    # PASO 5: Crear configuración
    print_header("PASO 5: CREANDO CONFIGURACIÓN")
    
    config = {
        "twilio": {
            "enabled": True,
            "account_sid": account_sid.strip(),
            "auth_token": auth_token.strip(),
            "from_number": format_phone(twilio_number),
            "to_numbers": [format_phone(n) for n in all_numbers]
        },
        "telegram": {
            "enabled": False,
            "token": "YOUR_TELEGRAM_BOT_TOKEN",
            "chat_id": "YOUR_CHAT_ID"
        },
        "email": {
            "enabled": False,
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender": "your_email@gmail.com",
            "password": "your_app_password",
            "recipients": ["recipient@example.com"]
        },
        "alert_types": {
            "accident": {
                "enabled": True,
                "channels": ["twilio"]
            },
            "person": {
                "enabled": True,
                "channels": ["twilio"]
            },
            "theft": {
                "enabled": True,
                "channels": ["twilio"]
            }
        },
        "cooldown_seconds": 60
    }
    
    # Guardar configuración
    with open("notifications_config.json", 'w') as f:
        json.dump(config, f, indent=2)
    
    print("✅ Configuración guardada en notifications_config.json\n")
    
    # PASO 6: Probar conexión
    print_header("PASO 6: PROBANDO CONEXIÓN")
    
    input("Presiona ENTER para probar la conexión a Twilio...\n")
    
    try:
        from twilio.rest import Client
        
        print("🔗 Conectando...")
        client = Client(account_sid.strip(), auth_token.strip())
        account = client.api.accounts.get()
        
        print(f"✅ Conectado exitosamente")
        print(f"   Cuenta: {account.friendly_name}")
        print(f"   Desde: {format_phone(twilio_number)}")
        print(f"   Para: {', '.join([format_phone(n) for n in all_numbers])}")
        
        # Enviar mensaje de prueba
        print("\n📤 Enviando mensaje de prueba...\n")
        
        for to_num in all_numbers:
            try:
                msg = client.messages.create(
                    from_=f"whatsapp:{format_phone(twilio_number)}",
                    to=f"whatsapp:{format_phone(to_num)}",
                    body="✅ TEST TWILIO\n\n🟢 ¡Sistema funcionando!\n\nCCTV AI PRO - Alertas activadas"
                )
                print(f"✅ Mensaje enviado a {format_phone(to_num)}")
                print(f"   SID: {msg.sid}")
            except Exception as e:
                print(f"❌ Error enviando a {to_num}: {e}")
        
        print("\n" + "="*70)
        print("✨ ¡CONFIGURACIÓN COMPLETADA!")
        print("="*70 + "\n")
        
        print("""
Próximos pasos:

1. Las alertas se enviarán automáticamente cuando:
   - Se detecte un accidente
   - Se identifique una persona
   - Se detecte una amenaza/robo

2. Ver historial de alertas:
   python notifications.py --show-history

3. Prueba manual:
   python notifications.py --test-whatsapp

4. Ver configuración:
   python notifications.py --show-config

5. Iniciar la app:
   python main.py
        """)
        
    except ImportError:
        print("❌ Twilio no está instalado")
        print("   Instala: pip install twilio")
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        print("\nVerifica:")
        print("  ✓ Account SID correcto")
        print("  ✓ Auth Token correcto")
        print("  ✓ Tarjeta agregada a Twilio")
        print("  ✓ Sandbox de WhatsApp activado")
        return False
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Configuración cancelada")
        sys.exit(1)
