"""
Notificaciones WhatsApp con Selenium (Sesión Persistente)
Sin QR cada vez - Se guarda la sesión automáticamente

Primer uso: escanea QR una sola vez
Usos siguientes: directo, sin QR

Requisitos:
- Chrome/Edge instalado
- Primera vez: escanear QR

Uso:
    notifier = SeleniumWhatsAppNotifier()
    notifier.send_alert("Cámara 1", "accident", "CRÍTICO", "Colisión detectada")
"""

import json
import os
import time
from datetime import datetime
from typing import Optional, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import pyperclip
import shutil
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service


class SeleniumWhatsAppNotifier:
    """Notificador WhatsApp robusto con Selenium - Sesión Persistente"""
    
    def __init__(self, config_file: str = "notifications_config.json", headless: bool = False):
        """
        Inicializar notificador
        
        Args:
            config_file: Archivo de config
            headless: Si True, ejecuta sin mostrar navegador (para producción)
        """
        self.config_file = config_file
        self.config = self._load_config()
        self.alerts_sent = []
        self.driver = None
        self.headless = headless
        
        # Perfil de Chrome persistente
        self.chrome_profile = os.path.join(os.path.dirname(__file__), "..", "chrome_profile")
        
        print("✓ WhatsApp Selenium Notifier inicializado")
        print(f"  Perfil: {self.chrome_profile}")
    
    def _load_config(self) -> dict:
        """Cargar configuración"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        config = {
            "whatsapp_selenium": {
                "to_numbers": ["+51930240476"],
                "wait_time": 10,
                "message_delay": 2
            }
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return config
    
    def _init_driver(self):
        """Inicializar Selenium WebDriver con sesión persistente"""
        if self.driver:
            return
        
        print("🔄 Iniciando navegador Chrome (sesión guardada)...")
        
        # Crear directorio de perfil si no existe
        os.makedirs(self.chrome_profile, exist_ok=True)
        
        options = webdriver.ChromeOptions()
        
        # ✅ IMPORTANTE: Usar perfil persistente
        options.add_argument(f"user-data-dir={self.chrome_profile}")
        
        if self.headless:
            options.add_argument("--headless")
        
        # Opciones para mejor rendimiento
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-extensions")
        
        try:
            # Usar webdriver-manager para chromedriver automático
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            print("✓ Navegador iniciado con sesión guardada")
        except Exception as e:
            print(f"✗ Error iniciando Chrome: {e}")
            print("💡 Intenta: pip install --upgrade webdriver-manager")
            raise
    
    def _open_whatsapp_web(self):
        """Abrir WhatsApp Web"""
        if not self.driver:
            self._init_driver()
        
        print("📱 Abriendo WhatsApp Web...")
        self.driver.get("https://web.whatsapp.com")
        
        # Esperar a que cargue
        wait = WebDriverWait(self.driver, 30)
        
        try:
            # Esperar a que aparezca el área de chat (significa que está autenticado)
            wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "selectable-text")))
            print("✓ WhatsApp Web cargado (autenticado)")
        except:
            # Si falla, mostrar mensaje de QR
            print("⚠️ Primera vez: Escanea el código QR con tu teléfono")
            print("💡 Mantén el navegador abierto...")
            time.sleep(15)  # Esperar para que escanee QR
            
            # Verificar de nuevo si está autenticado
            try:
                wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "selectable-text")))
                print("✓ WhatsApp autenticado correctamente")
            except:
                print("✗ No se pudo autenticar. Intenta de nuevo.")
                raise
    
    def _send_to_contact(self, phone_number: str, message: str) -> bool:
        """Enviar mensaje a un contacto"""
        try:
            print(f"\n📱 Enviando a {phone_number}...")
            
            # Limpiar número
            clean_number = phone_number.replace(" ", "").replace("+", "").replace("-", "")
            
            # Construir URL de WhatsApp Web
            url = f"https://web.whatsapp.com/send?phone={clean_number}&text="
            
            self.driver.get(url)
            
            wait = WebDriverWait(self.driver, 15)
            
            # Esperar a que esté listo para escribir
            try:
                # Buscar el área de texto
                message_box = wait.until(
                    EC.presence_of_element_located((By.XPATH, "//*[@contenteditable='true'][@data-tab='10']"))
                )
                print("✓ Chat abierto")
                
                time.sleep(1)
                
                # Copiar mensaje al portapapeles
                pyperclip.copy(message)
                
                # Hacer clic en el área de mensaje
                message_box.click()
                
                # Pegar mensaje (más confiable que escribir)
                message_box.send_keys(Keys.CONTROL, "v")
                
                print("✓ Mensaje escrito")
                time.sleep(self.config.get('whatsapp_selenium', {}).get('message_delay', 2))
                
                # Presionar Enter para enviar
                message_box.send_keys(Keys.RETURN)
                
                print(f"✓ Mensaje enviado a {phone_number}")
                time.sleep(2)
                
                return True
                
            except Exception as e:
                print(f"⚠️ Error escribiendo mensaje: {e}")
                print("💡 Intenta escanear el QR nuevamente")
                return False
        
        except Exception as e:
            print(f"✗ Error: {e}")
            return False
    
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
            to_numbers = self.config.get('whatsapp_selenium', {}).get('to_numbers', [])
        
        if not to_numbers:
            print("✗ No hay números configurados")
            return False
        
        # Inicializar driver
        try:
            self._init_driver()
            self._open_whatsapp_web()
        except Exception as e:
            print(f"✗ Error iniciando WhatsApp: {e}")
            return False
        
        # Enviar a cada número
        success = True
        for number in to_numbers:
            if not self._send_to_contact(number, message):
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
    
    def close(self):
        """Cerrar navegador"""
        if self.driver:
            self.driver.quit()
            print("✓ Navegador cerrado")
    
    def reset_session(self):
        """Resetear sesión (eliminar perfil guardado)"""
        if self.driver:
            self.driver.quit()
            self.driver = None
        
        if os.path.exists(self.chrome_profile):
            shutil.rmtree(self.chrome_profile)
            print("✓ Sesión resetada - Tendrás que escanear QR nuevamente")
        else:
            print("✓ No hay sesión anterior")
    
    def test_connection(self) -> bool:
        """Probar conexión"""
        
        print("\n📱 Probando WhatsApp Selenium (Sesión Persistente)...")
        print("="*60)
        
        config = self.config.get('whatsapp_selenium', {})
        print(f"✓ Números configurados: {config.get('to_numbers')}")
        print(f"✓ Perfil Chrome: {self.chrome_profile}")
        
        # Verificar si ya hay sesión guardada
        if os.path.exists(os.path.join(self.chrome_profile, "Default")):
            print("✓ Sesión guardada (sin QR necesario)")
        else:
            print("⚠️ Primera vez (necesitarás escanear QR)")
        
        print("\n💡 Para enviar mensajes:")
        print("   1. Primera vez: escanea QR y espera a que se guarde")
        print("   2. Siguientes veces: Chrome se abre y envía automáticamente")
        print("   3. Para resetear: python ... --reset")
        print("="*60 + "\n")
        
        return True


# Script de prueba
if __name__ == "__main__":
    import sys
    
    print("""
╔═════════════════════════════════════════╗
║   WhatsApp Selenium - Sesión Persistente║
╚═════════════════════════════════════════╝
    """)
    
    notifier = SeleniumWhatsAppNotifier()
    notifier.test_connection()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test-accident":
            print("📤 Enviando alerta de accidente...\n")
            success = notifier.send_accident_alert(
                camera="Cámara Entrada",
                severity="CRÍTICO",
                vehicle_speed=85.5,
                impact_force=450.0,
                details="Colisión frontal - múltiples vehículos"
            )
            if success:
                print("\n✓ ¡Alerta enviada exitosamente!")
            notifier.close()
        
        elif sys.argv[1] == "--test-person":
            print("📤 Enviando alerta de persona...\n")
            success = notifier.send_person_alert(
                camera="Cámara Parqueo",
                person_id="P001",
                confidence=0.92,
                details="Persona sospechosa detectada"
            )
            if success:
                print("\n✓ ¡Alerta enviada exitosamente!")
            notifier.close()
        
        elif sys.argv[1] == "--test-threat":
            print("📤 Enviando alerta de amenaza...\n")
            success = notifier.send_threat_alert(
                camera="Cámara Perímetro",
                threat_type="Arma detectada",
                confidence=0.88,
                severity="CRÍTICO"
            )
            if success:
                print("\n✓ ¡Alerta enviada exitosamente!")
            notifier.close()
        
        elif sys.argv[1] == "--reset":
            print("🔄 Reseteando sesión...\n")
            notifier.reset_session()
            print("\nLa próxima vez tendrás que escanear el QR de nuevo.")
    else:
        print("\n💡 Ejemplos:")
        print("  python modulos/whatsapp_selenium.py --test-accident")
        print("  python modulos/whatsapp_selenium.py --test-person")
        print("  python modulos/whatsapp_selenium.py --test-threat")
        print("  python modulos/whatsapp_selenium.py --reset")
