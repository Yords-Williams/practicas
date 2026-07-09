#!/usr/bin/env python3
"""
Script para probar Twilio + WhatsApp rápidamente
Uso: python test_twilio.py
"""

import json
import sys

def test_twilio():
    print("\n" + "="*70)
    print("🟢 TEST TWILIO + WHATSAPP")
    print("="*70 + "\n")
    
    # Cargar config
    try:
        with open("notifications_config.json", 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("❌ No encontré notifications_config.json")
        print("   Crea el archivo siguiendo TWILIO_WHATSAPP_SETUP.md")
        return False
    
    twilio_config = config.get('twilio', {})
    
    if not twilio_config.get('enabled'):
        print("⚠️  Twilio no está habilitado en notifications_config.json")
        print("   Cambia: \"enabled\": true")
        return False
    
    # Verificar credenciales
    account_sid = twilio_config.get('account_sid', '').strip()
    auth_token = twilio_config.get('auth_token', '').strip()
    from_number = twilio_config.get('from_number', '').strip()
    to_numbers = twilio_config.get('to_numbers', [])
    
    print("📋 Verificando configuración...\n")
    
    # Validación básica
    checks = {
        "Account SID": account_sid and account_sid != "ACxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "Auth Token": auth_token and auth_token != "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "From Number (Twilio)": from_number and from_number.startswith('+1'),
        "To Numbers": len(to_numbers) > 0 and all(n.strip().startswith('+') for n in to_numbers),
    }
    
    all_ok = True
    for check, result in checks.items():
        status = "✅" if result else "❌"
        print(f"{status} {check}")
        all_ok = all_ok and result
    
    if not all_ok:
        print("\n⚠️  Configura notifications_config.json correctamente:")
        print("   - Account SID: Ve a https://www.twilio.com/console")
        print("   - Auth Token: Ve a https://www.twilio.com/console")
        print("   - From Number: Ve a https://www.twilio.com/console/sms/whatsapp/sandbox")
        print("   - To Numbers: Tu número en formato +[país][número]")
        return False
    
    print("\n✅ Configuración válida\n")
    
    # Intentar conectar
    print("🔗 Conectando a Twilio...\n")
    
    try:
        from twilio.rest import Client
    except ImportError:
        print("❌ Twilio no está instalado")
        print("   Instala: pip install twilio")
        return False
    
    try:
        client = Client(account_sid, auth_token)
        account = client.api.accounts.get()
        print(f"✅ Conectado a: {account.friendly_name}")
        print(f"   Account SID: {account_sid[:10]}...")
        print(f"   From: {from_number}")
        print(f"   To: {', '.join(to_numbers)}")
    except Exception as e:
        print(f"❌ Error de autenticación: {e}")
        print("   Verifica que Account SID y Auth Token sean correctos")
        return False
    
    # Enviar mensaje de prueba
    print("\n📤 Enviando mensaje de prueba...\n")
    
    try:
        for to_number in to_numbers:
            msg = client.messages.create(
                from_=f"whatsapp:{from_number}",
                to=f"whatsapp:{to_number.replace(' ', '')}",
                body="✅ TWILIO TEST\n\n🟢 Sistema funcionando correctamente\n\nCCTV AI PRO"
            )
            print(f"✅ Mensaje enviado a {to_number}")
            print(f"   SID: {msg.sid}")
            print(f"   Estado: {msg.status}")
    except Exception as e:
        print(f"❌ Error enviando mensaje: {e}")
        print("\nPosibles problemas:")
        print("  1. Tarjeta de crédito no verificada")
        print("  2. Sandbox de WhatsApp no activado")
        print("  3. Número de teléfono en formato incorrecto")
        return False
    
    print("\n" + "="*70)
    print("✨ ¡TODO FUNCIONA! Puedes usar notifications.py")
    print("="*70 + "\n")
    
    print("Próximos pasos:")
    print("  1. Integra NotificationManager en tus módulos")
    print("  2. Prueba: python notifications.py --test-whatsapp")
    print("  3. Verifica historial: python notifications.py --show-history")
    print()
    
    return True


if __name__ == "__main__":
    success = test_twilio()
    sys.exit(0 if success else 1)
