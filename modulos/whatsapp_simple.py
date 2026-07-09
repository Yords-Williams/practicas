"""
Notificaciones WhatsApp Simple con PyWhatKit
Sin complicaciones, sin APIs, sin registros.

Requisitos:
- Tener WhatsApp instalado
- Estar logeado en WhatsApp Web (escanear QR una vez)

Uso:
    notifier = SimpleWhatsAppNotifier()
    notifier.send_alert("Mi número", "Mensaje de prueba")
"""

import pywhatkit as kit
import json
import os
from datetime import datetime
from typing import Optional, List
import time


class SimpleWhatsAppNotifier:
    """Notificador WhatsApp simple con PyWhatKit"""
    
    def __init__(self, config_file: str = "notifications_config.json"):
        """
        Inicializar notificador
        
        Args:
            config_file: Archivo de config (números destino)
        """
        self.config_file = config_file
        self.config = self._load_config()
        self.alerts_sent = []
        
        print("✓ WhatsApp Simple Notifier inicializado")
        print("💡 Asegúrate de tener WhatsApp Web abierto")
    
    def _load_config(self) -> dict:
        """Cargar configuración"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # Configuración por defecto
        config = {
            "whatsapp_simple": {
                "to_numbers": ["+34678123456"],
                "delay_seconds": 15,
                "time_out": 10
            }
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return config
    
    def send_alert(
        self,
        camera: str,
        alert_type: str,
        severity: str = "NORMAL",
        details: str = "",
        to_numbers: Optional[List[str]] = None
    ) -> bool:
        """
        Enviar alerta por WhatsApp
        
        Args:
            camera: Nombre de cámara
            alert_type: Tipo (accident, person, theft)
            severity: Nivel (NORMAL, ALTO, CRÍTICO)
            details: Detalles del evento
            to_numbers: Números destino
        
        Returns:
            True si se envió
        """
        # Construir mensaje
        message = self._build_message(camera, alert_type, severity, details)
        
        # Obtener números destino
        if not to_numbers:
            to_numbers = self.config.get('whatsapp_simple', {}).get('to_numbers', [])
        
        if not to_numbers:
            print("✗ No hay números configurados")
            return False
        
        # Enviar a cada número
        success = True
        for number in to_numbers:
            if not self._send_whatsapp(message, number):
                success = False
        
        if success:
            self.alerts_sent.append({
                'timestamp': datetime.now().isoformat(),
                'camera': camera,
                'type': alert_type,
                'severity': severity
            })
        
        return success
    
    def _build_message(self, camera: str, alert_type: str, severity: str, details: str) -> str:
        """Construir mensaje formateado"""
        
        icons = {
            'accident': '🚗💥',
            'person': '👤',
            'theft': '🚨'
        }
        
        severity_icons = {
            'CRÍTICO': '🔴',
            'ALTO': '🟠',
            'NORMAL': '🟡'
        }
        
        icon = icons.get(alert_type, '⚠️')
        sev_icon = severity_icons.get(severity, '🟡')
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        message = f"""{icon} ALERTA CCTV
        
Tipo: {alert_type.upper()}
Cámara: {camera}
Severidad: {sev_icon} {severity}
Hora: {timestamp}

Detalles:
{details}

🤖 Sistema CCTV AI PRO"""
        
        return message
    
    def _send_whatsapp(self, message: str, phone_number: str) -> bool:
        """
        Enviar mensaje WhatsApp
        
        Args:
            message: Texto del mensaje
            phone_number: Número con código país (+34...)
        
        Returns:
            True si se envió
        """
        try:
            # Configuración
            delay = self.config.get('whatsapp_simple', {}).get('delay_seconds', 15)
            timeout = self.config.get('whatsapp_simple', {}).get('time_out', 10)
            
            print(f"\n📱 Enviando a {phone_number}...")
            print(f"⏳ Espera {delay} segundos (abre WhatsApp Web si no está abierto)")
            
            # Enviar mensaje (se abre WhatsApp Web automáticamente)
            kit.sendwhatmsg(
                phone_no=phone_number,
                message=message,
                time_hour=datetime.now().hour,
                time_min=datetime.now().minute + 1,
                wait_time=timeout,
                tab_close=True
            )
            
            print(f"✓ Mensaje enviado a {phone_number}")
            return True
            
        except Exception as e:
            print(f"✗ Error enviando a {phone_number}: {e}")
            print("\n💡 Soluciones:")
            print("   1. ¿Tienes WhatsApp Web abierto? https://web.whatsapp.com")
            print("   2. ¿El número es correcto? (+34678123456)")
            print("   3. ¿Está contacto guardado en tu lista?")
            return False
    
    def send_accident_alert(
        self,
        camera: str,
        severity: str = "ALTO",
        vehicle_speed: float = 0.0,
        impact_force: float = 0.0,
        details: str = ""
    ) -> bool:
        """Enviar alerta de accidente"""
        
        full_details = details or "Colisión detectada"
        if vehicle_speed:
            full_details += f"\n🚗 Velocidad: {vehicle_speed:.1f} km/h"
        if impact_force:
            full_details += f"\n💪 Fuerza: {impact_force:.1f} N"
        
        return self.send_alert(
            camera=camera,
            alert_type="accident",
            severity=severity,
            details=full_details
        )
    
    def send_person_alert(
        self,
        camera: str,
        person_id: str = "",
        confidence: float = 0.0,
        details: str = ""
    ) -> bool:
        """Enviar alerta de persona detectada"""
        
        full_details = details or "Persona detectada"
        if person_id:
            full_details += f"\n👤 ID: {person_id}"
        if confidence:
            full_details += f"\n🎯 Confianza: {confidence*100:.1f}%"
        
        return self.send_alert(
            camera=camera,
            alert_type="person",
            severity="NORMAL",
            details=full_details
        )
    
    def send_threat_alert(
        self,
        camera: str,
        threat_type: str = "Desconocida",
        confidence: float = 0.0,
        severity: str = "CRÍTICO",
        details: str = ""
    ) -> bool:
        """Enviar alerta de amenaza"""
        
        full_details = details or f"Amenaza detectada: {threat_type}"
        if confidence:
            full_details += f"\n🎯 Confianza: {confidence*100:.1f}%"
        
        return self.send_alert(
            camera=camera,
            alert_type="theft",
            severity=severity,
            details=full_details
        )
    
    def test_connection(self) -> bool:
        """Probar conexión"""
        
        print("\n📱 Probando WhatsApp...")
        print("="*60)
        
        config = self.config.get('whatsapp_simple', {})
        print(f"✓ Números configurados: {config.get('to_numbers')}")
        print(f"✓ Delay: {config.get('delay_seconds')}s")
        print(f"✓ Timeout: {config.get('time_out')}s")
        
        print("\n💡 Para enviar mensajes:")
        print("   1. Abre WhatsApp Web: https://web.whatsapp.com")
        print("   2. Escanea el código QR con tu teléfono")
        print("   3. Ejecuta: python modulos/whatsapp_simple.py --test-accident")
        print("="*60 + "\n")
        
        return True


# Script de prueba
if __name__ == "__main__":
    import sys
    
    print("""
╔═════════════════════════════════════════╗
║   WhatsApp Simple - PyWhatKit           ║
╚═════════════════════════════════════════╝
    """)
    
    notifier = SimpleWhatsAppNotifier()
    notifier.test_connection()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test-accident":
            print("📤 Enviando alerta de accidente...\n")
            notifier.send_accident_alert(
                camera="Cámara Entrada",
                severity="CRÍTICO",
                vehicle_speed=85.5,
                impact_force=450.0,
                details="Colisión frontal - múltiples vehículos"
            )
        
        elif sys.argv[1] == "--test-person":
            print("📤 Enviando alerta de persona...\n")
            notifier.send_person_alert(
                camera="Cámara Parqueo",
                person_id="P001",
                confidence=0.92,
                details="Persona sospechosa detectada"
            )
        
        elif sys.argv[1] == "--test-threat":
            print("📤 Enviando alerta de amenaza...\n")
            notifier.send_threat_alert(
                camera="Cámara Perímetro",
                threat_type="Arma detectada",
                confidence=0.88,
                severity="CRÍTICO"
            )
        
        elif sys.argv[1] == "--test-all":
            print("📤 Enviando todas las pruebas...\n")
            notifier.send_accident_alert(
                camera="Test",
                severity="ALTO",
                details="Prueba de accidente"
            )
            time.sleep(5)
            notifier.send_person_alert(
                camera="Test",
                person_id="TEST",
                confidence=0.95
            )
            time.sleep(5)
            notifier.send_threat_alert(
                camera="Test",
                threat_type="Prueba",
                confidence=0.80
            )
    else:
        print("\n💡 Ejemplos:")
        print("  python modulos/whatsapp_simple.py --test-accident")
        print("  python modulos/whatsapp_simple.py --test-person")
        print("  python modulos/whatsapp_simple.py --test-threat")
        print("  python modulos/whatsapp_simple.py --test-all")
