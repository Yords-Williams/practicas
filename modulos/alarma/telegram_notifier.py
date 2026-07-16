"""
Notificaciones por Telegram
Simple, confiable, sin problemas

Setup (1 minuto):
1. En Telegram: busca @BotFather
2. Escribe: /newbot
3. Nombre: CCTV_Alerts_Bot
4. Username: cctv_bot_[tunombre]
5. Copias el TOKEN

6. Busca tu bot en Telegram, escribe /start
7. Ve a: https://api.telegram.org/botTOKEN/getUpdates
8. Copia el chat_id

Uso:
    notifier = TelegramNotifier(token="...", chat_ids=["id1", "id2"])
    notifier.send_alert("Cámara 1", "accident", "Colisión detectada")
"""

import json
import os
import requests
from datetime import datetime
from typing import Optional, List


class TelegramNotifier:
    """Notificador Telegram simple y confiable con múltiples destinatarios"""
    
    def __init__(self, config_file: str = "notifications_config.json"):
        """
        Inicializar notificador Telegram
        
        Args:
            config_file: Archivo de config con token y chat_ids
        """
        self.config_file = config_file
        self.config = self._load_config()
        self.alerts_sent = []
        
        # Obtener credenciales
        telegram_config = self.config.get('telegram', {})
        self.token = telegram_config.get('token')
        
        # Soportar múltiples chat_ids y el formato legacy con chat_id
        chat_ids = telegram_config.get('chat_ids', [])
        if isinstance(chat_ids, str):
            self.chat_ids = [chat_ids]
        else:
            self.chat_ids = chat_ids if chat_ids else []

        legacy_chat_id = telegram_config.get('chat_id')
        if legacy_chat_id and legacy_chat_id not in self.chat_ids:
            self.chat_ids.append(legacy_chat_id)

        self.chat_ids = [chat_id for chat_id in self.chat_ids if chat_id and chat_id != 'YOUR_CHAT_ID_1' and chat_id != 'YOUR_CHAT_ID_2' and chat_id != 'YOUR_CHAT_ID_3' and chat_id != 'YOUR_CHAT_ID']
        
        if self.token and self.token != "YOUR_TELEGRAM_BOT_TOKEN":
            print(f"✓ Telegram Notifier inicializado")
            if self.chat_ids:
                print(f"  💬 Enviando a {len(self.chat_ids)} chat(s)")
        else:
            print("⚠️ Telegram no configurado")
    
    def _load_config(self) -> dict:
        """Cargar configuración"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Agregar telegram si no existe o si viene con formato legacy
                    if 'telegram' not in config:
                        config['telegram'] = {
                            "enabled": False,
                            "token": "YOUR_TELEGRAM_BOT_TOKEN",
                            "chat_ids": ["YOUR_CHAT_ID_1", "YOUR_CHAT_ID_2"]
                        }
                        with open(self.config_file, 'w', encoding='utf-8') as f:
                            json.dump(config, f, indent=2, ensure_ascii=False)
                    else:
                        telegram_config = config['telegram']
                        if 'enabled' not in telegram_config:
                            telegram_config['enabled'] = False
                        if 'chat_ids' not in telegram_config and 'chat_id' in telegram_config:
                            telegram_config['chat_ids'] = [telegram_config['chat_id']]
                        if 'chat_id' in telegram_config and telegram_config.get('chat_ids'):
                            telegram_config.pop('chat_id', None)
                        with open(self.config_file, 'w', encoding='utf-8') as f:
                            json.dump(config, f, indent=2, ensure_ascii=False)
                    return config
            except:
                pass
        
        config = {
            "telegram": {
                "enabled": False,
                "token": "YOUR_TELEGRAM_BOT_TOKEN",
                "chat_ids": ["YOUR_CHAT_ID_1", "YOUR_CHAT_ID_2"]
            }
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return config
    
    def send_alert(
        self,
        camera: str,
        alert_type: str,
        message: str = None,
        severity: str = "NORMAL",
        details: str = ""
    ) -> bool:
        """
        Enviar alerta por Telegram a múltiples chats
        
        Args:
            camera: Nombre de cámara
            alert_type: Tipo (accident, person, theft)
            message: Mensaje personalizado
            severity: Nivel (NORMAL, ALTO, CRÍTICO)
            details: Detalles del evento
        
        Returns:
            True si se envió a todos
        """
        if not self.token or self.token == "YOUR_TELEGRAM_BOT_TOKEN":
            print("✗ Telegram no está configurado")
            return False
        
        if not self.chat_ids:
            print("✗ No hay chats configurados")
            return False

        if self.token.startswith("YOUR"):
            print("✗ Telegram no está configurado correctamente")
            return False
        
        # Construir mensaje si no está especificado
        if not message:
            message = self._build_message(camera, alert_type, severity, details)
        
        success_count = 0
        
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            
            print(f"📤 Enviando a {len(self.chat_ids)} chat(s)...")
            
            for chat_id in self.chat_ids:
                data = {
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "HTML"
                }
                
                try:
                    response = requests.post(url, json=data, timeout=10)
                    
                    if response.status_code == 200:
                        result = response.json()
                        msg_id = result.get('result', {}).get('message_id')
                        print(f"  ✓ {chat_id} (ID: {msg_id})")
                        success_count += 1
                    else:
                        error = response.json()
                        print(f"  ✗ {chat_id}: {error}")
                        
                except requests.Timeout:
                    print(f"  ✗ {chat_id}: Timeout")
                except Exception as e:
                    print(f"  ✗ {chat_id}: {e}")
            
            if success_count > 0:
                print(f"✓ Telegram enviado a {success_count}/{len(self.chat_ids)} chat(s)")
                
                self.alerts_sent.append({
                    'timestamp': datetime.now().isoformat(),
                    'camera': camera,
                    'type': alert_type,
                    'severity': severity,
                    'recipients': success_count
                })
                return True
            else:
                print("✗ No se envió a ningún chat")
                return False
                
        except Exception as e:
            print(f"✗ Error: {e}")
            return False
    
    def _build_message(self, camera: str, alert_type: str, severity: str, details: str) -> str:
        """Construir mensaje formateado para Telegram"""
        
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
        
        message = f"""<b>{icon} ALERTA CCTV - {alert_type.upper()}</b>

<b>Cámara:</b> {camera}
<b>Severidad:</b> {sev_icon} {severity}
<b>Hora:</b> {timestamp}

<b>Detalles:</b>
{details}

<i>🤖 Sistema Alertas Tempranas</i>"""
        
        return message
    
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
        """Probar configuración sin enviar mensajes reales."""
        
        print("\n📡 Probando configuración de Telegram...")
        print("="*60)
        
        config = self.config.get('telegram', {})
        token = config.get('token')
        chat_ids = config.get('chat_ids', [])
        
        if token == "YOUR_TELEGRAM_BOT_TOKEN":
            print("⚠️ Telegram no configurado")
            print("\n💡 Setup (1 minuto):")
            print("   1. En Telegram: busca @BotFather")
            print("   2. Escribe: /newbot")
            print("   3. Nombre: CCTV_Alerts_Bot")
            print("   4. Username: cctv_bot_[tunombre]")
            print("   5. Copias el TOKEN")
            print("   ")
            print("   6. Busca tu bot en Telegram, escribe /start")
            print("   7. Ve a: https://api.telegram.org/botTOKEN/getUpdates")
            print("   8. Copia el chat_id")
            print("   ")
            print("   9. Edita notifications_config.json:")
            print('      \"token\": \"YOUR_TOKEN_AQUI\",')
            print('      \"chat_ids\": [\"CHAT_ID_1\", \"CHAT_ID_2\"]')
            return False
        
        print(f"✓ Token: {token[:10]}...{token[-10:]}")
        print(f"✓ Chats ({len(chat_ids)}):")
        for chat_id in chat_ids:
            print(f"   💬 {chat_id}")
        print("="*60 + "\n")
        
        return True


# Script de prueba
if __name__ == "__main__":
    import sys
    
    print("""
╔═════════════════════════════════════════╗
║   Telegram Notifier                     ║
╚═════════════════════════════════════════╝
    """)
    
    notifier = TelegramNotifier()
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
    else:
        print("\n💡 Ejemplos:")
        print("  python modulos/telegram_notifier.py --test-accident")
        print("  python modulos/telegram_notifier.py --test-person")
        print("  python modulos/telegram_notifier.py --test-threat")
