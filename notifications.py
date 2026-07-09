"""
Sistema de Notificaciones para Detecciones
Soporta: Telegram, WhatsApp (Twilio), Email
Uso: python notifications.py --test-telegram
"""

import json
import os
from datetime import datetime
from pathlib import Path
import threading
import traceback

# Try to import optional dependencies
try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

try:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False


class NotificationManager:
    """
    Gestor centralizado de notificaciones
    
    Uso:
        nm = NotificationManager()
        nm.send_accident_alert(
            camera="Cámara 1",
            severity="CRÍTICO",
            frame_path="path/to/frame.jpg",
            details="Choque frontal detectado"
        )
    """
    
    def __init__(self, config_file="notifications_config.json"):
        """Inicializar gestor de notificaciones"""
        self.config_file = config_file
        self.config = self._load_config()
        self.alerts_log = []
        self._load_alerts_history()
        
        # Inicializar clientes
        self.telegram_bot = None
        self.twilio_client = None
        
        if self.config.get('telegram', {}).get('enabled'):
            self._init_telegram()
        
        if self.config.get('twilio', {}).get('enabled'):
            self._init_twilio()
    
    def _load_config(self):
        """Cargar configuración de notificaciones"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        
        # Configuración por defecto
        default_config = {
            "telegram": {
                "enabled": False,
                "token": "YOUR_TELEGRAM_BOT_TOKEN",
                "chat_id": "YOUR_CHAT_ID",
                "send_frame": True,
                "include_details": True
            },
            "twilio": {
                "enabled": False,
                "account_sid": "YOUR_ACCOUNT_SID",
                "auth_token": "YOUR_AUTH_TOKEN",
                "from_number": "+1234567890",
                "to_numbers": ["+1234567890"],
                "template": "🚨 ALERTA DE {tipo}: {camera}\n{details}"
            },
            "email": {
                "enabled": False,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "sender": "your_email@gmail.com",
                "password": "your_app_password",
                "recipients": ["recipient@example.com"],
                "include_frame": True
            },
            "alert_types": {
                "accident": {
                    "enabled": True,
                    "min_severity": "ALTO",
                    "channels": ["telegram", "twilio", "email"]
                },
                "person": {
                    "enabled": True,
                    "channels": ["telegram"]
                },
                "theft": {
                    "enabled": True,
                    "channels": ["telegram", "twilio"]
                }
            },
            "cooldown_seconds": 60  # Evitar spam (una alerta cada 60s por tipo)
        }
        
        # Guardar configuración por defecto
        self._save_config(default_config)
        return default_config
    
    def _save_config(self, config):
        """Guardar configuración a archivo"""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def _load_alerts_history(self):
        """Cargar historial de alertas"""
        history_file = "alerts_history.json"
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    self.alerts_log = json.load(f)
            except:
                self.alerts_log = []
    
    def _save_alerts_history(self):
        """Guardar historial de alertas"""
        with open("alerts_history.json", 'w') as f:
            json.dump(self.alerts_log[-1000:], f, indent=2)  # Guardar últimas 1000
    
    def _init_telegram(self):
        """Inicializar cliente Telegram"""
        if not TELEGRAM_AVAILABLE:
            print("⚠️ python-telegram-bot no está instalado")
            print("   Instalar: pip install python-telegram-bot")
            return False
        
        token = self.config['telegram'].get('token')
        if token == "YOUR_TELEGRAM_BOT_TOKEN" or not token:
            print("⚠️ Telegram no configurado. Ver: notifications_config.json")
            return False
        
        try:
            self.telegram_bot = Bot(token=token)
            print("✓ Telegram conectado correctamente")
            return True
        except Exception as e:
            print(f"✗ Error conectando Telegram: {e}")
            return False
    
    def _init_twilio(self):
        """Inicializar cliente Twilio"""
        if not TWILIO_AVAILABLE:
            print("⚠️ twilio no está instalado")
            print("   Instalar: pip install twilio")
            return False
        
        config = self.config['twilio']
        if config.get('account_sid') == "YOUR_ACCOUNT_SID":
            print("⚠️ Twilio no configurado. Ver: notifications_config.json")
            return False
        
        try:
            self.twilio_client = Client(
                config['account_sid'],
                config['auth_token']
            )
            print("✓ Twilio conectado correctamente")
            return True
        except Exception as e:
            print(f"✗ Error conectando Twilio: {e}")
            return False
    
    def _should_send_alert(self, alert_type):
        """Verificar si debe enviar alerta (control de cooldown)"""
        if alert_type not in self.config.get('alert_types', {}):
            return False
        
        if not self.config['alert_types'][alert_type].get('enabled'):
            return False
        
        # Verificar cooldown
        cooldown = self.config.get('cooldown_seconds', 60)
        now = datetime.now().timestamp()
        
        for alert in reversed(self.alerts_log):
            if alert['type'] == alert_type:
                age = now - alert['timestamp']
                if age < cooldown:
                    return False  # Aún en cooldown
                break
        
        return True
    
    def send_accident_alert(self, camera, severity="CRÍTICO", frame_path=None, details=""):
        """Enviar alerta de accidente"""
        if not self._should_send_alert('accident'):
            return False
        
        alert_data = {
            'timestamp': datetime.now().timestamp(),
            'type': 'accident',
            'camera': camera,
            'severity': severity,
            'details': details,
            'frame_path': frame_path
        }
        self.alerts_log.append(alert_data)
        self._save_alerts_history()
        
        message = f"""🚗 ALERTA DE ACCIDENTE
Cámara: {camera}
Severidad: {severity}
Detalles: {details}
Hora: {datetime.now().strftime('%H:%M:%S')}"""
        
        channels = self.config['alert_types']['accident'].get('channels', [])
        self._send_multiplatform(message, channels, frame_path, 'accident')
        return True
    
    def send_person_alert(self, camera, person_id="", details=""):
        """Enviar alerta de persona detectada"""
        if not self._should_send_alert('person'):
            return False
        
        alert_data = {
            'timestamp': datetime.now().timestamp(),
            'type': 'person',
            'camera': camera,
            'person_id': person_id,
            'details': details
        }
        self.alerts_log.append(alert_data)
        self._save_alerts_history()
        
        message = f"""👤 PERSONA DETECTADA
Cámara: {camera}
ID: {person_id or 'Desconocido'}
Detalles: {details}
Hora: {datetime.now().strftime('%H:%M:%S')}"""
        
        channels = self.config['alert_types']['person'].get('channels', [])
        self._send_multiplatform(message, channels, None, 'person')
        return True
    
    def send_theft_alert(self, camera, threat_type="DESCONOCIDO", confidence=0.0, details=""):
        """Enviar alerta de robo/amenaza"""
        if not self._should_send_alert('theft'):
            return False
        
        alert_data = {
            'timestamp': datetime.now().timestamp(),
            'type': 'theft',
            'camera': camera,
            'threat_type': threat_type,
            'confidence': confidence,
            'details': details
        }
        self.alerts_log.append(alert_data)
        self._save_alerts_history()
        
        message = f"""🚨 ALERTA DE SEGURIDAD
Cámara: {camera}
Tipo: {threat_type}
Confianza: {confidence*100:.1f}%
Detalles: {details}
Hora: {datetime.now().strftime('%H:%M:%S')}"""
        
        channels = self.config['alert_types']['theft'].get('channels', [])
        self._send_multiplatform(message, channels, None, 'theft')
        return True
    
    def _send_multiplatform(self, message, channels, frame_path=None, alert_type=''):
        """Enviar mensaje a múltiples plataformas"""
        for channel in channels:
            if channel == 'telegram':
                threading.Thread(
                    target=self._send_telegram,
                    args=(message, frame_path),
                    daemon=True
                ).start()
            elif channel == 'twilio':
                threading.Thread(
                    target=self._send_twilio,
                    args=(message, alert_type),
                    daemon=True
                ).start()
            elif channel == 'email':
                threading.Thread(
                    target=self._send_email,
                    args=(message, frame_path),
                    daemon=True
                ).start()
    
    def _send_telegram(self, message, frame_path=None):
        """Enviar mensaje por Telegram"""
        if not self.telegram_bot:
            return False
        
        try:
            config = self.config['telegram']
            chat_id = config.get('chat_id')
            
            # Enviar texto
            self.telegram_bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='HTML'
            )
            
            # Enviar frame si existe
            if frame_path and os.path.exists(frame_path) and config.get('send_frame'):
                with open(frame_path, 'rb') as photo:
                    self.telegram_bot.send_photo(
                        chat_id=chat_id,
                        photo=photo,
                        caption="Frame de detección"
                    )
            
            print(f"✓ Telegram enviado a {chat_id}")
            return True
        except Exception as e:
            print(f"✗ Error enviando Telegram: {e}")
            return False
    
    def _send_twilio(self, message, alert_type=''):
        """Enviar mensaje por WhatsApp vía Twilio"""
        if not self.twilio_client:
            return False
        
        try:
            config = self.config['twilio']
            from_number = config.get('from_number')
            to_numbers = config.get('to_numbers', [])
            
            for to_number in to_numbers:
                msg = self.twilio_client.messages.create(
                    from_=f"whatsapp:{from_number}",
                    body=message,
                    to=f"whatsapp:{to_number}"
                )
                print(f"✓ WhatsApp enviado a {to_number} (SID: {msg.sid})")
            
            return True
        except Exception as e:
            print(f"✗ Error enviando WhatsApp (Twilio): {e}")
            print("  Tip: Verifica que los números estén en formato +[país][número]")
            return False
    
    def _send_email(self, message, frame_path=None):
        """Enviar notificación por email"""
        if not EMAIL_AVAILABLE:
            return False
        
        try:
            config = self.config['email']
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = "🚨 Alerta CCTV AI PRO"
            msg['From'] = config['sender']
            msg['To'] = ", ".join(config['recipients'])
            
            # Convertir mensaje a HTML
            html_message = f"""
            <html>
              <body style="font-family: Arial;">
                <h2>🚨 ALERTA CCTV AI PRO</h2>
                <pre style="background: #f0f0f0; padding: 10px; border-radius: 5px;">
{message}
                </pre>
                <small>Sistema de vigilancia inteligente</small>
              </body>
            </html>
            """
            
            msg.attach(MIMEText(html_message, 'html'))
            
            # Enviar
            server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
            server.starttls()
            server.login(config['sender'], config['password'])
            server.send_message(msg)
            server.quit()
            
            print(f"✓ Email enviado a {', '.join(config['recipients'])}")
            return True
        except Exception as e:
            print(f"✗ Error enviando email: {e}")
            return False
    
    def get_alerts_summary(self, hours=1):
        """Obtener resumen de alertas de las últimas N horas"""
        now = datetime.now().timestamp()
        time_limit = now - (hours * 3600)
        
        recent_alerts = [a for a in self.alerts_log if a['timestamp'] > time_limit]
        
        summary = {
            'total': len(recent_alerts),
            'accidents': len([a for a in recent_alerts if a['type'] == 'accident']),
            'persons': len([a for a in recent_alerts if a['type'] == 'person']),
            'threats': len([a for a in recent_alerts if a['type'] == 'theft']),
            'alerts': recent_alerts
        }
        return summary
    
    def test_connection(self):
        """Probar conexiones configuradas"""
        print("\n📋 Probando conexiones de notificaciones...")
        print("="*60)
        
        # Telegram
        if self.config['telegram'].get('enabled'):
            print("\n🔵 Telegram:")
            if self.telegram_bot:
                try:
                    bot_info = self.telegram_bot.get_me()
                    print(f"  ✓ Bot: @{bot_info.username}")
                    print(f"  ✓ Chat ID: {self.config['telegram']['chat_id']}")
                except Exception as e:
                    print(f"  ✗ Error: {e}")
            else:
                print("  ⚠️ No configurado")
        
        # Twilio
        if self.config['twilio'].get('enabled'):
            print("\n🟢 Twilio/WhatsApp:")
            if self.twilio_client:
                try:
                    account = self.twilio_client.api.accounts.get()
                    print(f"  ✓ Account: {account.friendly_name}")
                    print(f"  ✓ Números destino: {self.config['twilio']['to_numbers']}")
                except Exception as e:
                    print(f"  ✗ Error: {e}")
            else:
                print("  ⚠️ No configurado")
        
        # Email
        if self.config['email'].get('enabled'):
            print("\n📧 Email:")
            print(f"  ✓ Desde: {self.config['email']['sender']}")
            print(f"  ✓ Para: {self.config['email']['recipients']}")
        
        print("\n" + "="*60)


# Script de prueba
if __name__ == "__main__":
    import sys
    
    print("""
╔════════════════════════════════════════╗
║    CCTV AI PRO - Sistema de Alertas    ║
╚════════════════════════════════════════╝
    """)
    
    # Crear gestor
    nm = NotificationManager()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test-telegram":
            print("\n📤 Enviando alerta de prueba a Telegram...")
            nm.send_accident_alert(
                camera="Cámara Test",
                severity="CRÍTICO",
                details="Colisión frontal - prueba de sistema"
            )
        
        elif sys.argv[1] == "--test-whatsapp":
            print("\n📤 Enviando alerta de prueba a WhatsApp...")
            nm.send_theft_alert(
                camera="Cámara Test",
                threat_type="Arma detectada",
                confidence=0.95,
                details="Prueba de sistema de alertas"
            )
        
        elif sys.argv[1] == "--test-all":
            print("\n📤 Enviando alertas de prueba a todos los canales...")
            nm.send_accident_alert(
                camera="Cámara Test",
                severity="ALTO",
                details="Prueba de accidente"
            )
            nm.send_person_alert(
                camera="Cámara Test",
                person_id="P001",
                details="Persona detectada"
            )
            nm.send_theft_alert(
                camera="Cámara Test",
                threat_type="Objeto sospechoso",
                confidence=0.87
            )
        
        elif sys.argv[1] == "--show-config":
            print("\n📋 Configuración actual:")
            print(json.dumps(nm.config, indent=2, ensure_ascii=False))
        
        elif sys.argv[1] == "--show-history":
            print("\n📊 Historial de alertas (últimas 10):")
            for alert in nm.alerts_log[-10:]:
                ts = datetime.fromtimestamp(alert['timestamp'])
                print(f"  [{ts.strftime('%H:%M:%S')}] {alert['type'].upper()}: {alert.get('camera', 'N/A')}")
        
        else:
            print("Uso: python notifications.py [OPCIÓN]")
            print("\nOpciones:")
            print("  --test-telegram    Enviar alerta de prueba a Telegram")
            print("  --test-whatsapp     Enviar alerta de prueba a WhatsApp")
            print("  --test-all          Enviar todas las alertas de prueba")
            print("  --show-config       Mostrar configuración actual")
            print("  --show-history      Mostrar historial de alertas")
    else:
        nm.test_connection()
        print("\n✓ Sistema de notificaciones listo")
        print("\nPara enviar una alerta de prueba:")
        print("  python notifications.py --test-telegram")
