"""
Módulo de Notificaciones WhatsApp vía Meta API
Completamente gratuito con limitaciones diarias

Requisitos:
- Cuenta Facebook Business
- Número de teléfono verificado
- Access Token de Meta API

Uso:
    notifier = WhatsAppNotifier()
    notifier.send_alert(
        camera="Cámara 1",
        alert_type="accident",
        severity="CRÍTICO",
        details="Colisión frontal detectada",
        frame_path="frame.jpg"
    )
"""

import json
import os
import requests
from datetime import datetime
from typing import List, Optional, Dict
import base64
from pathlib import Path


class WhatsAppNotifier:
    """
    Gestor centralizado de notificaciones WhatsApp vía Meta API
    Gratis y sin requiere tarjeta de crédito
    """
    
    def __init__(self, config_file: str = None):
        """
        Inicializar notificador WhatsApp Meta API
        
        Args:
            config_file: Ruta al archivo de configuración JSON
        """
        self.config_file = config_file or self._get_default_config_file()
        self.config = self._load_config()
        self.alerts_sent = []
        
        self._init_meta()
        print("✓ WhatsApp Notifier (Meta API) inicializado")
    
    def _get_default_config_file(self) -> str:
        """Obtener ruta por defecto del archivo de configuración"""
        workspace = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(workspace, "notifications_config.json")
    
    def _load_config(self) -> Dict:
        """Cargar configuración desde archivo JSON"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Error cargando config: {e}")
                return self._get_default_config()
        
        config = self._get_default_config()
        self._save_config(config)
        return config
    
    def _get_default_config(self) -> Dict:
        """Configuración por defecto"""
        return {
            "whatsapp": {
                "meta": {
                    "phone_id": "YOUR_PHONE_NUMBER_ID",
                    "access_token": "YOUR_ACCESS_TOKEN",
                    "to_numbers": ["+34678123456"]
                },
                "settings": {
                    "send_frame": True,
                    "max_frame_size_mb": 5,
                    "cooldown_seconds": 60,
                    "retry_attempts": 3,
                    "retry_delay_seconds": 2
                }
            }
        }
    
    def _save_config(self, config: Dict):
        """Guardar configuración a archivo"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"✓ Config guardada en {self.config_file}")
        except Exception as e:
            print(f"✗ Error guardando config: {e}")
    
    def _init_meta(self):
        """Validar configuración Meta API"""
        config = self.config.get('whatsapp', {}).get('meta', {})
        
        if config.get('phone_id') == "YOUR_PHONE_NUMBER_ID":
            print("⚠️ Meta API no configurado")
            self.meta_ready = False
            return
        
        self.meta_ready = True
        print(f"✓ Meta API configurado (Phone ID: {config.get('phone_id')})")
    
    def send_alert(
        self,
        camera: str,
        alert_type: str,
        message: str = None,
        severity: str = "NORMAL",
        details: str = "",
        frame_path: Optional[str] = None,
        to_numbers: Optional[List[str]] = None,
        **kwargs
    ) -> bool:
        """
        Enviar alerta por WhatsApp vía Meta API
        
        Args:
            camera: Nombre de la cámara
            alert_type: Tipo de alerta (accident, person, theft)
            message: Mensaje personalizado
            severity: Nivel de severidad (NORMAL, ALTO, CRÍTICO)
            details: Detalles adicionales
            frame_path: Ruta a imagen para adjuntar
            to_numbers: Lista de números destino
            **kwargs: Parámetros adicionales
        
        Returns:
            True si se envió exitosamente
        """
        # Construir mensaje si no está especificado
        if not message:
            message = self._build_message(camera, alert_type, severity, details, **kwargs)
        
        # Obtener números destino
        if not to_numbers:
            to_numbers = self.config.get('whatsapp', {}).get('meta', {}).get('to_numbers', [])
        
        if not to_numbers:
            print("✗ No hay números de destino configurados")
            return False
        
        # Enviar vía Meta
        success = self._send_meta(message, frame_path, to_numbers)
        
        if success:
            self.alerts_sent.append({
                'timestamp': datetime.now().isoformat(),
                'camera': camera,
                'type': alert_type,
                'severity': severity,
                'provider': 'meta'
            })
        
        return success
    
    def _build_message(
        self,
        camera: str,
        alert_type: str,
        severity: str,
        details: str,
        **kwargs
    ) -> str:
        """Construir mensaje formateado para WhatsApp"""
        
        icons = {
            'accident': '🚗💥',
            'person': '👤',
            'theft': '🚨',
            'default': '⚠️'
        }
        
        severity_icons = {
            'CRÍTICO': '🔴',
            'ALTO': '🟠',
            'NORMAL': '🟡'
        }
        
        icon = icons.get(alert_type, icons['default'])
        sev_icon = severity_icons.get(severity, '🟡')
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        message = f"""
{icon} ALERTA CCTV - {alert_type.upper()}

Cámara: {camera}
Severidad: {sev_icon} {severity}
Hora: {timestamp}

Detalles:
{details}

---
Sistema CCTV AI PRO
        """.strip()
        
        # Agregar info adicional si existe
        for key, value in kwargs.items():
            if value:
                message += f"\n{key}: {value}"
        
        return message
    
    def _send_meta(
        self,
        message: str,
        frame_path: Optional[str] = None,
        to_numbers: List[str] = None
    ) -> bool:
        """Enviar mensaje vía Meta API"""
        
        if not self.meta_ready:
            print("✗ Meta API no está configurado")
            return False
        
        config = self.config.get('whatsapp', {}).get('meta', {})
        phone_id = config.get('phone_id')
        access_token = config.get('access_token')
        
        if not to_numbers:
            to_numbers = config.get('to_numbers', [])
        
        url = f"https://graph.instagram.com/v18.0/{phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        success = True
        
        for to_number in to_numbers:
            try:
                # Limpiar número
                clean_number = to_number.replace(" ", "").replace("+", "")
                if not clean_number.startswith("34"):  # Agregar código país si es necesario
                    clean_number = "34" + clean_number
                
                # Enviar texto
                data = {
                    "messaging_product": "whatsapp",
                    "to": clean_number,
                    "type": "text",
                    "text": {"body": message}
                }
                
                response = requests.post(url, json=data, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✓ WhatsApp enviado a {to_number}")
                    print(f"  ID: {result.get('messages', [{}])[0].get('id', 'N/A')}")
                    
                    # Enviar imagen si existe
                    if frame_path and os.path.exists(frame_path):
                        self._send_meta_image(to_number, frame_path, phone_id, access_token)
                else:
                    error = response.json()
                    print(f"✗ Error Meta: {error}")
                    success = False
                    
            except requests.Timeout:
                print(f"✗ Timeout enviando a {to_number}")
                success = False
            except Exception as e:
                print(f"✗ Error: {e}")
                success = False
        
        return success
    
    def _send_meta_image(
        self,
        to_number: str,
        image_path: str,
        phone_id: str,
        access_token: str
    ) -> bool:
        """Enviar imagen vía Meta API"""
        
        try:
            # Verificar tamaño
            file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
            max_size = self.config.get('whatsapp', {}).get('settings', {}).get('max_frame_size_mb', 5)
            
            if file_size_mb > max_size:
                print(f"⚠️ Imagen muy grande ({file_size_mb:.1f}MB > {max_size}MB)")
                return False
            
            # Subir a Meta (necesita URL pública o pasar base64)
            url = f"https://graph.instagram.com/v18.0/{phone_id}/messages"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Convertir imagen a base64
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode()
            
            data = {
                "messaging_product": "whatsapp",
                "to": to_number.replace(" ", "").replace("+", ""),
                "type": "image",
                "image": {
                    "data": image_data
                }
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=10)
            
            if response.status_code == 200:
                print(f"✓ Imagen enviada a {to_number}")
                return True
            else:
                print(f"⚠️ Error enviando imagen: {response.json()}")
                return False
                
        except Exception as e:
            print(f"⚠️ Error: {e}")
            return False
    
    def send_accident_alert(
        self,
        camera: str,
        severity: str = "ALTO",
        vehicle_speed: float = 0.0,
        impact_force: float = 0.0,
        frame_path: Optional[str] = None,
        details: str = ""
    ) -> bool:
        """Enviar alerta de accidente"""
        
        extra_info = {
            "Velocidad": f"{vehicle_speed:.1f} km/h" if vehicle_speed else None,
            "Fuerza de impacto": f"{impact_force:.1f} N" if impact_force else None,
        }
        
        return self.send_alert(
            camera=camera,
            alert_type="accident",
            severity=severity,
            details=details or "Colisión detectada",
            frame_path=frame_path,
            **extra_info
        )
    
    def send_person_alert(
        self,
        camera: str,
        person_id: str = "",
        confidence: float = 0.0,
        details: str = "",
        frame_path: Optional[str] = None
    ) -> bool:
        """Enviar alerta de persona detectada"""
        
        extra_info = {
            "ID Persona": person_id if person_id else "Desconocido",
            "Confianza": f"{confidence*100:.1f}%" if confidence else None,
        }
        
        return self.send_alert(
            camera=camera,
            alert_type="person",
            severity="NORMAL",
            details=details or "Persona detectada",
            frame_path=frame_path,
            **extra_info
        )
    
    def send_threat_alert(
        self,
        camera: str,
        threat_type: str,
        confidence: float = 0.0,
        severity: str = "CRÍTICO",
        details: str = "",
        frame_path: Optional[str] = None
    ) -> bool:
        """Enviar alerta de amenaza/robo"""
        
        extra_info = {
            "Tipo de amenaza": threat_type,
            "Confianza": f"{confidence*100:.1f}%" if confidence else None,
        }
        
        return self.send_alert(
            camera=camera,
            alert_type="theft",
            severity=severity,
            details=details or "Amenaza detectada",
            frame_path=frame_path,
            **extra_info
        )
    
    def test_connection(self) -> bool:
        """Probar conexión de Meta API"""
        
        print(f"\n📱 Probando conexión WhatsApp (Meta API)...")
        print("="*60)
        
        if self.meta_ready:
            config = self.config.get('whatsapp', {}).get('meta', {})
            print(f"✓ Phone ID: {config.get('phone_id')}")
            print(f"✓ To: {config.get('to_numbers')}")
            print("="*60 + "\n")
            return True
        else:
            print("✗ Meta API no configurado")
            return False


# Script de prueba
if __name__ == "__main__":
    import sys
    
    print("""
╔═════════════════════════════════════════╗
║   WhatsApp Notifier - Meta API          ║
╚═════════════════════════════════════════╝
    """)
    
    # Crear notificador (solo Meta API)
    notifier = WhatsAppNotifier()
    
    # Probar conexión
    notifier.test_connection()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test-accident":
            print("📤 Enviando alerta de accidente...")
            notifier.send_accident_alert(
                camera="Cámara Entrada",
                severity="CRÍTICO",
                vehicle_speed=85.5,
                impact_force=450.0,
                details="Colisión frontal - múltiples vehículos"
            )
        
        elif sys.argv[1] == "--test-person":
            print("📤 Enviando alerta de persona...")
            notifier.send_person_alert(
                camera="Cámara Parqueo",
                person_id="P001",
                confidence=0.92,
                details="Persona sospechosa detectada"
            )
        
        elif sys.argv[1] == "--test-threat":
            print("📤 Enviando alerta de amenaza...")
            notifier.send_threat_alert(
                camera="Cámara Perímetro",
                threat_type="Arma detectada",
                confidence=0.88,
                severity="CRÍTICO",
                details="Objeto peligroso identificado"
            )
        
        elif sys.argv[1] == "--test-all":
            print("📤 Enviando todas las pruebas...")
            notifier.send_accident_alert(
                camera="Test Camera",
                severity="ALTO",
                vehicle_speed=60.0,
                details="Prueba de accidente"
            )
            notifier.send_person_alert(
                camera="Test Camera",
                person_id="TEST",
                confidence=0.95,
                details="Prueba de persona"
            )
            notifier.send_threat_alert(
                camera="Test Camera",
                threat_type="Prueba",
                confidence=0.80,
                details="Prueba de amenaza"
            )
    else:
        print("\n💡 Ejemplos de uso:")
        print("  python modulos/whatsapp_notifier.py --test-accident")
        print("  python modulos/whatsapp_notifier.py --test-person")
        print("  python modulos/whatsapp_notifier.py --test-threat")
        print("  python modulos/whatsapp_notifier.py --test-all")
