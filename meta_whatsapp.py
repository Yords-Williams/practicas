"""
WhatsApp vía Meta API (GRATIS)
Para menos de 10 alertas/día

Setup: https://developers.facebook.com
"""

import requests
import json
import os
from datetime import datetime

class MetaWhatsAppNotifier:
    """Enviar alertas por WhatsApp vía Meta API (gratis)"""
    
    def __init__(self, config_file="meta_whatsapp_config.json"):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self):
        """Cargar configuración"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        
        # Configuración por defecto
        default_config = {
            "meta": {
                "phone_id": "YOUR_PHONE_NUMBER_ID",
                "access_token": "YOUR_ACCESS_TOKEN",
                "to_numbers": ["+34678123456"]
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        return default_config
    
    def send_message(self, message, to_number=None):
        """Enviar mensaje por WhatsApp"""
        
        phone_id = self.config['meta'].get('phone_id')
        access_token = self.config['meta'].get('access_token')
        
        if phone_id == "YOUR_PHONE_NUMBER_ID" or access_token == "YOUR_ACCESS_TOKEN":
            print("❌ Configura meta_whatsapp_config.json primero")
            return False
        
        numbers = [to_number] if to_number else self.config['meta'].get('to_numbers', [])
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        url = f"https://graph.instagram.com/v18.0/{phone_id}/messages"
        
        for number in numbers:
            try:
                data = {
                    "messaging_product": "whatsapp",
                    "to": number.replace(" ", ""),
                    "type": "text",
                    "text": {"body": message}
                }
                
                response = requests.post(url, headers=headers, json=data)
                result = response.json()
                
                if response.status_code == 200:
                    print(f"✅ Mensaje enviado a {number}")
                    print(f"   ID: {result.get('messages', [{}])[0].get('id', 'N/A')}")
                else:
                    print(f"❌ Error enviando a {number}: {result}")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                return False
        
        return True
    
    def send_accident_alert(self, camera, severity, details=""):
        """Enviar alerta de accidente"""
        message = f"""🚗 ALERTA DE ACCIDENTE
Cámara: {camera}
Severidad: {severity}
Detalles: {details}
Hora: {datetime.now().strftime('%H:%M:%S')}"""
        
        return self.send_message(message)
    
    def send_threat_alert(self, camera, threat_type, details=""):
        """Enviar alerta de amenaza"""
        message = f"""🚨 ALERTA DE SEGURIDAD
Cámara: {camera}
Tipo: {threat_type}
Detalles: {details}
Hora: {datetime.now().strftime('%H:%M:%S')}"""
        
        return self.send_message(message)
    
    def test_connection(self):
        """Probar conexión a Meta"""
        print("\n" + "="*70)
        print("🟣 TEST META WHATSAPP API (GRATIS)")
        print("="*70 + "\n")
        
        phone_id = self.config['meta'].get('phone_id')
        access_token = self.config['meta'].get('access_token')
        
        if phone_id == "YOUR_PHONE_NUMBER_ID":
            print("❌ Configura Phone ID en meta_whatsapp_config.json")
            print("\nPasos:")
            print("1. Ve a https://developers.facebook.com")
            print("2. Crea una app → WhatsApp")
            print("3. Activa sandbox")
            print("4. Copia Phone Number ID")
            return False
        
        if access_token == "YOUR_ACCESS_TOKEN":
            print("❌ Configura Access Token en meta_whatsapp_config.json")
            print("\nPasos:")
            print("1. Ve a Tools → API Explorer")
            print("2. Genera Access Token")
            print("3. Cópialo en el archivo de config")
            return False
        
        print(f"✓ Phone ID: {phone_id}")
        print(f"✓ Access Token: {access_token[:10]}...")
        
        # Probar envío
        print("\n📤 Enviando mensaje de prueba...\n")
        
        message = "✅ TEST META WHATSAPP\n\n🟣 Sistema funcionando correctamente\n\nCCTV AI PRO"
        
        return self.send_message(message)


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════╗
║   META WHATSAPP API - SETUP GRATIS     ║
╚════════════════════════════════════════╝

PASO 1: Crear app en https://developers.facebook.com
PASO 2: Copiar Phone ID y Access Token
PASO 3: Guardar en meta_whatsapp_config.json
PASO 4: Probar conexión

Costo: $0 (gratis)
Alertas: Ilimitadas en sandbox
    """)
    
    import sys
    
    notifier = MetaWhatsAppNotifier()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test":
            notifier.test_connection()
        elif sys.argv[1] == "--send-accident":
            notifier.send_accident_alert(
                camera="Cámara Test",
                severity="CRÍTICO",
                details="Prueba de sistema"
            )
        elif sys.argv[1] == "--send-threat":
            notifier.send_threat_alert(
                camera="Cámara Test",
                threat_type="Arma detectada",
                details="Prueba de sistema"
            )
    else:
        print("\nUso:")
        print("  python meta_whatsapp.py --test              Probar conexión")
        print("  python meta_whatsapp.py --send-accident     Enviar alerta de accidente")
        print("  python meta_whatsapp.py --send-threat       Enviar alerta de amenaza")
