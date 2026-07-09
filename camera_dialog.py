"""
Diálogo para agregar/editar cámaras RTSP
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                               QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QCheckBox)
from PySide6.QtCore import Qt
import json
import os

CAMERAS_FILE = "cameras_config.json"

class CameraDialog(QDialog):
    """Diálogo para gestionar cámaras RTSP"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestionar Cámaras RTSP")
        self.setGeometry(100, 100, 800, 400)
        
        self.cameras = self.load_cameras()
        self.init_ui()
    
    def init_ui(self):
        """Inicializar interfaz"""
        layout = QVBoxLayout()
        
        # Tabla de cámaras
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Nombre", "URL RTSP", "Acciones"])
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 400)
        self.table.setColumnWidth(2, 150)
        
        self.refresh_table()
        layout.addWidget(self.table)
        
        # Formulario para nueva cámara
        form_layout = QHBoxLayout()
        
        form_layout.addWidget(QLabel("Nombre:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("ej: Cámara Entrada")
        form_layout.addWidget(self.name_input)
        
        form_layout.addWidget(QLabel("URL:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("ej: rtsp://usuario:contraseña@192.168.1.100:554/stream")
        form_layout.addWidget(self.url_input)

        # Detección por cámara
        self.chk_fire = QCheckBox("Detectar incendios")
        self.chk_fire.setChecked(True)
        form_layout.addWidget(self.chk_fire)

        self.chk_theft = QCheckBox("Detectar robos")
        self.chk_theft.setChecked(True)
        form_layout.addWidget(self.chk_theft)

        self.chk_accident = QCheckBox("Detectar choques")
        self.chk_accident.setChecked(True)
        form_layout.addWidget(self.chk_accident)

        self.add_btn = QPushButton("Agregar Cámara")
        self.add_btn.clicked.connect(self.add_camera)
        form_layout.addWidget(self.add_btn)
        
        layout.addLayout(form_layout)
        
        # Botones de control
        btn_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Guardar Cambios")
        self.save_btn.clicked.connect(self.save_cameras)
        self.save_btn.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold;")
        btn_layout.addWidget(self.save_btn)
        
        self.close_btn = QPushButton("Cerrar")
        self.close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.close_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def refresh_table(self):
        """Actualizar tabla con cámaras"""
        self.table.setRowCount(len(self.cameras))
        
        for row, cam in enumerate(self.cameras):
            name_item = QTableWidgetItem(cam.get("name", ""))
            url_item = QTableWidgetItem(cam.get("url", ""))
            
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, url_item)
            
            # Botón eliminar
            delete_btn = QPushButton("Eliminar")
            delete_btn.clicked.connect(lambda checked, r=row: self.delete_camera(r))
            delete_btn.setStyleSheet("background-color: #e74c3c; color: white;")
            self.table.setCellWidget(row, 2, delete_btn)
    
    def add_camera(self):
        """Agregar nueva cámara"""
        name = self.name_input.text().strip()
        url = self.url_input.text().strip()
        
        if not name or not url:
            QMessageBox.warning(self, "Error", "Por favor completa nombre y URL")
            return
        
        if not url.startswith(("rtsp://", "http://", "https://")):
            QMessageBox.warning(self, "Error", "La URL debe comenzar con rtsp://, http:// o https://")
            return
        
        cam_entry = {
            "name": name,
            "url": url,
            "detect_fire": bool(self.chk_fire.isChecked()),
            "detect_theft": bool(self.chk_theft.isChecked()),
            "detect_accident": bool(self.chk_accident.isChecked())
        }
        self.cameras.append(cam_entry)
        self.name_input.clear()
        self.url_input.clear()
        self.chk_fire.setChecked(True)
        self.chk_theft.setChecked(True)
        self.chk_accident.setChecked(True)
        
        self.refresh_table()
        QMessageBox.information(self, "Éxito", "Cámara agregada. Click en 'Guardar Cambios'")
    
    def delete_camera(self, row):
        """Eliminar cámara"""
        reply = QMessageBox.question(self, "Confirmar", 
                                     f"¿Eliminar cámara: {self.cameras[row]['name']}?")
        
        if reply == QMessageBox.Yes:
            self.cameras.pop(row)
            self.refresh_table()
            QMessageBox.information(self, "Éxito", "Cámara eliminada. Click en 'Guardar Cambios'")
    
    def save_cameras(self):
        """Guardar configuración de cámaras"""
        try:
            with open(CAMERAS_FILE, 'w') as f:
                json.dump(self.cameras, f, indent=2)
            QMessageBox.information(self, "Éxito", 
                                   f"Configuración guardada en {CAMERAS_FILE}\n"
                                   f"Total de cámaras: {len(self.cameras)}\n\n"
                                   "Reinicia la aplicación para que tomen efecto.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar: {e}")
    
    @staticmethod
    def load_cameras():
        """Cargar cámaras desde archivo"""
        if os.path.exists(CAMERAS_FILE):
            try:
                with open(CAMERAS_FILE, 'r') as f:
                    data = json.load(f)
                    # Normalizar entradas antiguas para mantener compatibilidad
                    normalized = []
                    for cam in data:
                        normalized.append({
                            'name': cam.get('name', ''),
                            'url': cam.get('url', ''),
                            'detect_fire': cam.get('detect_fire', True),
                            'detect_theft': cam.get('detect_theft', True),
                            'detect_accident': cam.get('detect_accident', True)
                        })
                    return normalized
            except:
                return []
        return []
    
    @staticmethod
    def get_cameras():
        """Obtener lista de cámaras para iniciar"""
        return CameraDialog.load_cameras()
