"""
Notificaciones por Gmail
Simple, confiable, sin problemas

Setup (1 minuto):
1. Abre Gmail en https://myaccount.google.com/apppasswords
2. Selecciona: Mail y Windows (u otro)
3. Genera contraseña de app (16 caracteres)
4. Copias la contraseña

Uso:
    notifier = GmailNotifier(
        sender="tu_email@gmail.com",
        app_password="xxxx xxxx xxxx xxxx",
        to_email="tu_email@gmail.com"
    )
    notifier.send_alert("Cámara 1", "accident", "Colisión detectada")
"""

import json
import os
import smtplib
from datetime import datetime
from typing import Optional, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage


class GmailNotifier:
    """Notificador Gmail simple y confiable"""
    
    def __init__(self, config_file: str = "notifications_config.json"):
        """
        Inicializar notificador Gmail
        
        Args:
            config_file: Archivo de config con credenciales
        """
        self.config_file = config_file
        self.config = self._load_config()
        self.alerts_sent = []
        
        # Obtener credenciales
        self.sender = self.config.get('gmail', {}).get('sender')
        self.password = self.config.get('gmail', {}).get('app_password')
        
        # Soportar múltiples destinatarios
        to_emails = self.config.get('gmail', {}).get('to_emails', [])
        if isinstance(to_emails, str):
            self.to_emails = [to_emails]
        else:
            self.to_emails = to_emails if to_emails else []
        
        if self.sender and self.password and self.sender != "your_email@gmail.com":
            print(f"✓ Gmail Notifier inicializado")
            if self.to_emails:
                print(f"  📧 Enviando a {len(self.to_emails)} destinatario(s)")
        else:
            print("⚠️ Gmail no configurado")
    
    def _load_config(self) -> dict:
        """Cargar configuración"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Agregar gmail si no existe
                    if 'gmail' not in config:
                        config['gmail'] = {
                            "sender": "your_email@gmail.com",
                            "app_password": "xxxx xxxx xxxx xxxx",
                            "to_emails": ["email1@gmail.com", "email2@gmail.com"],
                            "include_frame": True
                        }
                        with open(self.config_file, 'w', encoding='utf-8') as f:
                            json.dump(config, f, indent=2, ensure_ascii=False)
                    return config
            except:
                pass
        
        config = {
            "gmail": {
                "sender": "your_email@gmail.com",
                "app_password": "xxxx xxxx xxxx xxxx",
                "to_emails": ["email1@gmail.com", "email2@gmail.com"],
                "include_frame": True
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
        details: str = "",
        frame_path: Optional[str] = None
    ) -> bool:
        """
        Enviar alerta por Gmail a múltiples destinatarios
        
        Args:
            camera: Nombre de cámara
            alert_type: Tipo (accident, person, theft)
            message: Mensaje personalizado
            severity: Nivel (NORMAL, ALTO, CRÍTICO)
            details: Detalles del evento
            frame_path: Ruta a imagen para adjuntar
        
        Returns:
            True si se envió
        """
        if not self.sender or self.sender == "your_email@gmail.com":
            print("✗ Gmail no está configurado")
            return False
        
        if not self.to_emails:
            print("✗ No hay destinatarios configurados")
            return False
        
        # Construir mensaje si no está especificado
        if not message:
            message = self._build_message(camera, alert_type, severity, details)
        
        try:
            # Crear mensaje multipart
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"🚨 ALERTA CCTV - {alert_type.upper()}"
            msg['From'] = self.sender
            msg['To'] = self.to_emails[0]  # Principal
            msg['Bcc'] = ', '.join(self.to_emails[1:]) if len(self.to_emails) > 1 else ''
            
            # Convertir a HTML
            html = f"""
            <html>
              <head></head>
              <body style="font-family: Arial; background-color: #f5f5f5;">
                <div style="max-width: 600px; margin: 20px auto; background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1);">
                  <h2 style="color: #e74c3c; text-align: center;">🚨 ALERTA CCTV</h2>
                  
                  <div style="background-color: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>Tipo:</strong> {alert_type.upper()}</p>
                    <p><strong>Cámara:</strong> {camera}</p>
                    <p><strong>Severidad:</strong> {severity}</p>
                    <p><strong>Hora:</strong> {datetime.now().strftime('%H:%M:%S')}</p>
                  </div>
                  
                  <div style="background-color: #f9f9f9; padding: 15px; border-left: 4px solid #3498db; margin: 20px 0;">
                    <p><strong>Detalles:</strong></p>
                    <p>{details.replace(chr(10), '<br>')}</p>
                  </div>
                  
                  <hr style="margin: 20px 0; border: none; border-top: 1px solid #ddd;">
                  <p style="text-align: center; color: #7f8c8d; font-size: 12px;">
                    <em>Sistema de Vigilancia CCTV AI PRO</em>
                  </p>
                </div>
              </body>
            </html>
            """
            
            msg.attach(MIMEText(html, 'html'))
            
            # Adjuntar imagen si existe
            if frame_path and os.path.exists(frame_path):
                try:
                    with open(frame_path, 'rb') as attachment:
                        part = MIMEImage(attachment.read())
                        part.add_header('Content-Disposition', 'attachment', filename="deteccion.jpg")
                        msg.attach(part)
                    print(f"  📎 Imagen adjunta: {frame_path}")
                except Exception as e:
                    print(f"  ⚠️ No se pudo adjuntar imagen: {e}")
            
            # Enviar
            print(f"📤 Enviando email a {len(self.to_emails)} destinatario(s)...")
            for email in self.to_emails:
                print(f"   📧 {email}")
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.sender, self.password)
            
            # Enviar a todos (usando BCC para privacidad)
            server.send_message(msg)
            server.quit()
            
            print(f"✓ Email enviado exitosamente a {len(self.to_emails)} destinatario(s)")
            
            self.alerts_sent.append({
                'timestamp': datetime.now().isoformat(),
                'camera': camera,
                'type': alert_type,
                'severity': severity
            })
            return True
            
        except smtplib.SMTPAuthenticationError:
            print("✗ Error: Contraseña de Gmail incorrecta")
            print("  💡 Usa contraseña de app, no tu contraseña normal")
            print("  💡 Ve a: https://myaccount.google.com/apppasswords")
            return False
        except Exception as e:
            print(f"✗ Error enviando email: {e}")
            return False
    
    def _build_message(self, camera: str, alert_type: str, severity: str, details: str) -> str:
        """Construir mensaje formateado para Gmail"""
        
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
        
        message = f"""{icon} ALERTA CCTV - {alert_type.upper()}

Cámara: {camera}
Severidad: {sev_icon} {severity}
Hora: {timestamp}

Detalles:
{details}

🤖 Sistema CCTV AI PRO"""
        
        return message
    
    def send_accident_alert(
        self,
        camera: str,
        severity: str = "ALTO",
        vehicle_speed: float = 0.0,
        impact_force: float = 0.0,
        details: str = "",
        frame_path: Optional[str] = None
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
            details=full_details,
            frame_path=frame_path
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
        
        full_details = details or "Persona detectada"
        if person_id:
            full_details += f"\n👤 ID: {person_id}"
        if confidence:
            full_details += f"\n🎯 Confianza: {confidence*100:.1f}%"
        
        return self.send_alert(
            camera=camera,
            alert_type="person",
            severity="NORMAL",
            details=full_details,
            frame_path=frame_path
        )
    
    def send_threat_alert(
        self,
        camera: str,
        threat_type: str = "Desconocida",
        confidence: float = 0.0,
        severity: str = "CRÍTICO",
        details: str = "",
        frame_path: Optional[str] = None
    ) -> bool:
        """Enviar alerta de amenaza"""
        
        full_details = details or f"Amenaza detectada: {threat_type}"
        if confidence:
            full_details += f"\n🎯 Confianza: {confidence*100:.1f}%"
        
        return self.send_alert(
            camera=camera,
            alert_type="theft",
            severity=severity,
            details=full_details,
            frame_path=frame_path
        )
    
    def test_connection(self) -> bool:
        """Probar conexión"""
        
        print("\n📧 Probando Gmail...")
        print("="*60)
        
        config = self.config.get('gmail', {})
        sender = config.get('sender')
        password = config.get('app_password')
        to_emails = config.get('to_emails', [])
        
        if sender == "your_email@gmail.com":
            print("⚠️ Gmail no configurado")
            print("\n💡 Setup (1 minuto):")
            print("   1. Ve a: https://myaccount.google.com/apppasswords")
            print("   2. Selecciona: Mail y Windows")
            print("   3. Genera contraseña de app (16 caracteres)")
            print("   4. Copias la contraseña")
            print("   5. Edita notifications_config.json:")
            print('      "sender": "tu_email@gmail.com",')
            print('      "app_password": "xxxx xxxx xxxx xxxx",')
            print('      "to_emails": ["email1@gmail.com", "email2@gmail.com"]')
            return False
        
        print(f"✓ Sender: {sender}")
        print(f"✓ Password: {password[:4]}...{password[-4:]}")
        print(f"✓ Destinatarios ({len(to_emails)}):")
        for email in to_emails:
            print(f"   📧 {email}")
        print("="*60 + "\n")
        
        return True


# Script de prueba
if __name__ == "__main__":
    import sys
    
    print("""
╔═════════════════════════════════════════╗
║   Gmail Notifier                        ║
╚═════════════════════════════════════════╝
    """)
    
    notifier = GmailNotifier()
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
        print("  python modulos/gmail_notifier.py --test-accident")
        print("  python modulos/gmail_notifier.py --test-person")
        print("  python modulos/gmail_notifier.py --test-threat")
