import cv2
import numpy as np
from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QComboBox, QStackedLayout, QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem, QSizePolicy, QLineEdit, QMessageBox, QFileDialog
from PySide6.QtGui import QImage, QPixmap, QColor
from PySide6.QtCore import QTimer, Qt
from camera_dialog import CameraDialog
from config import DETECTION_CONFIG
from modulos.fire_detector import FireDetectionSystem

class CCTVWindow(QWidget):

    def __init__(self, cams, detector, accident_detector=None, person_tracker=None, theft_detector=None, fire_detector=None):
        super().__init__()

        self.cams = cams
        self.detector = detector
        self.accident_detector = accident_detector
        self.person_tracker = person_tracker
        self.theft_detector = theft_detector
        self.fire_detector = fire_detector or FireDetectionSystem(db_path="incidents.db", config_file="fire_config.json")
        
        # Modo de detección actual
        self.detection_mode = "general"  # general, accidentes, personas, robos
        
        # Estadísticas
        self.frame_count = 0
        self.total_frames_processed = 0
        self.frame_times = []
        self.target_fps = DETECTION_CONFIG['fps_limit']

        self.setWindowTitle("Alertas tempranas")
        self.setMinimumSize(1400, 850)

        # ===== TOP BAR =====
        self.topBar = QFrame()
        self.topBar.setObjectName("topBar")
        self.topBar.setStyleSheet("QFrame#topBar{background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #1f2a36, stop:1 #2c3e50); border-bottom: 2px solid #3a3a3a;}" )

        # Logo a la izquierda (si existe en assets/app.png)
        from PySide6.QtGui import QPixmap
        try:
            logo_path = None
            import os, sys
            def resource_path(relative):
                if getattr(sys, 'frozen', False):
                    return os.path.join(sys._MEIPASS, relative)
                return os.path.join(os.path.abspath(os.path.dirname(__file__)), relative)

            candidate = resource_path('assets/app.png')
            if os.path.exists(candidate):
                logo_path = candidate
            else:
                # fallback to svg or png names
                candidate2 = resource_path('assets/logo.png')
                if os.path.exists(candidate2):
                    logo_path = candidate2

            if logo_path:
                pix = QPixmap(logo_path).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.logo_label = QLabel()
                self.logo_label.setPixmap(pix)
                self.logo_label.setFixedSize(52, 52)
            else:
                self.logo_label = QLabel()
                self.logo_label.setText('')

        except Exception:
            self.logo_label = QLabel()

        self.statusBtn = QPushButton("🟢 SYSTEM ONLINE")
        self.statusBtn.setStyleSheet("QPushButton{background-color:#27ae60; color:white; font-weight:bold; padding:8px; border-radius:6px;} QPushButton:hover{background-color:#2ecc71}")
        
        # Selector de modo de detección
        self.modeSelector = QComboBox()
        self.modeSelector.addItem("🎯 Detección General", "general")
        self.modeSelector.addItem("🚗 Detección de Accidentes", "accidentes")
        self.modeSelector.addItem("👤 Rastreo de Personas", "personas")
        self.modeSelector.addItem("🚨 Detección de Robos", "robos")
        self.modeSelector.currentIndexChanged.connect(self.on_mode_changed)
        self.modeSelector.setStyleSheet("QComboBox{padding:6px; min-width:200px; background-color:#22313f; color:white; border:1px solid #3b3b3b; border-radius:4px}")
        
        # Botón para gestionar cámaras
        self.camera_btn = QPushButton("📹 Gestionar Cámaras")
        self.camera_btn.setStyleSheet("QPushButton{background-color:#e74c3c; color:white; font-weight:bold; padding:8px; border-radius:6px} QPushButton:hover{background-color:#ff5b48}")
        self.camera_btn.clicked.connect(self.open_camera_manager)

        topLayout = QHBoxLayout()
        topLayout.addWidget(self.logo_label)
        topLayout.addSpacing(6)
        topLayout.addWidget(self.statusBtn)
        topLayout.addWidget(QLabel("Modo:"))
        topLayout.addWidget(self.modeSelector)
        topLayout.addWidget(self.camera_btn)
        topLayout.addStretch()
        self.topBar.setLayout(topLayout)

        # ===== GRID CAMERAS ===== (will be placed in a stacked page)
        self.grid = QGridLayout()
        self.labels = []

        # Mostrar hasta 6 cámaras (2x3 o 3x2)
        max_cameras = 6
        cols = 3
        for i in range(max_cameras):
            lbl = QLabel("SIN VIDEO")
            lbl.setFixedSize(450, 280)
            lbl.setStyleSheet("background-color:#0f1113; border:2px solid #2b2b2b; border-radius:8px; color:#bfc9d4; font-weight:bold; text-align:center;")
            lbl.setAlignment(Qt.AlignCenter)
            self.labels.append(lbl)
            self.grid.addWidget(lbl, i // cols, i % cols)

        # ===== STATS PANEL =====
        self.statsPanel = QFrame()
        self.statsPanel.setObjectName("statsPanel")
        self.statsPanel.setStyleSheet("QFrame#statsPanel{background:#111214; color:#dfe7ec; border-radius:8px; padding:12px; border:1px solid #222}")
        
        self.statsLabel = QLabel("Estadísticas del Sistema")
        self.statsLabel.setStyleSheet("color: white; font-weight: bold; font-family: Courier;")
        
        statsLayout = QVBoxLayout()
        statsLayout.addWidget(self.statsLabel)
        self.statsPanel.setLayout(statsLayout)

        # ===== STACKED CONTENT PAGES =====
        self.stacked = QStackedLayout()

        # Cameras page
        cameras_widget = QWidget()
        cam_layout = QVBoxLayout()
        cam_layout.addLayout(self.grid)
        cameras_widget.setLayout(cam_layout)

        # Incidents page
        incidents_widget = QWidget()
        incidents_layout = QVBoxLayout()
        # Incidents table + export button
        top_incidents_bar = QHBoxLayout()
        self.export_btn = QPushButton("Exportar a Excel")
        self.export_btn.setStyleSheet("QPushButton{background-color:#2980b9; color:white; padding:6px; border-radius:6px} QPushButton:hover{background-color:#3498db}")
        self.export_btn.clicked.connect(self.export_incidents_to_excel)
        top_incidents_bar.addWidget(self.export_btn)
        top_incidents_bar.addStretch()

        self.incidents_table = QTableWidget()
        self.incidents_table.setColumnCount(5)
        self.incidents_table.setHorizontalHeaderLabels(["Hora", "Cámara", "Tipo", "Severidad", "Confianza"])
        self.incidents_table.horizontalHeader().setStretchLastSection(True)
        incidents_layout.addLayout(top_incidents_bar)
        incidents_layout.addWidget(self.incidents_table)
        incidents_widget.setLayout(incidents_layout)

        # Recipients page
        recipients_widget = QWidget()
        recipients_layout = QVBoxLayout()

        form_layout = QHBoxLayout()
        self.rec_name = QLineEdit()
        self.rec_name.setPlaceholderText("Nombre")
        self.rec_email = QLineEdit()
        self.rec_email.setPlaceholderText("email@example.com")
        self.rec_phone = QLineEdit()
        self.rec_phone.setPlaceholderText("+1234567890")
        self.add_recipient_btn = QPushButton("Agregar destinatario")
        self.add_recipient_btn.setStyleSheet("background-color:#2980b9; color:white; padding:6px; border-radius:4px;")
        self.add_recipient_btn.clicked.connect(self.add_recipient_clicked)

        form_layout.addWidget(self.rec_name)
        form_layout.addWidget(self.rec_email)
        form_layout.addWidget(self.rec_phone)
        form_layout.addWidget(self.add_recipient_btn)

        recipients_layout.addLayout(form_layout)

        self.recipients_table = QTableWidget()
        self.recipients_table.setColumnCount(5)
        self.recipients_table.setHorizontalHeaderLabels(["ID","Nombre","Email","Teléfono","Activo"])
        recipients_layout.addWidget(self.recipients_table)

        remove_btn = QPushButton("Eliminar seleccionado")
        remove_btn.setStyleSheet("background-color:#c0392b; color:white; padding:6px; border-radius:4px;")
        remove_btn.clicked.connect(self.remove_selected_recipient)
        recipients_layout.addWidget(remove_btn)

        recipients_widget.setLayout(recipients_layout)

        self.stacked.addWidget(cameras_widget)
        self.stacked.addWidget(incidents_widget)
        self.stacked.addWidget(recipients_widget)

        # ===== LEFT SIDEBAR (YouTube-style) =====
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setStyleSheet("QFrame#sidebar{background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #0b0d0f, stop:1 #111316); color:white}")
        self.sidebar.setFixedWidth(240)

        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(8, 8, 8, 8)

        self.menu_list = QListWidget()
        self.menu_list.setStyleSheet(
            "QListWidget{background: transparent; color: #e6eef6; border: none; font-size:14px;}"
            "QListWidget::item{padding:12px;} QListWidget::item:selected{background:#2b2b2b; color:#ffb3b3;}")
        for label in ["Dashboard","Cámaras","Incidentes","Destinatarios","Notificaciones","Ajustes"]:
            item = QListWidgetItem(label)
            self.menu_list.addItem(item)

        self.menu_list.setCurrentRow(1)  # default to Cámaras
        self.menu_list.currentRowChanged.connect(self.on_menu_changed)

        sidebar_layout.addWidget(self.menu_list)
        sidebar_layout.addStretch()
        self.sidebar.setLayout(sidebar_layout)

        # ===== MAIN LAYOUT =====
        main_h = QHBoxLayout()
        main_h.addWidget(self.sidebar)

        content_v = QVBoxLayout()
        content_v.addWidget(self.topBar)
        # stacked needs a widget wrapper
        stacked_widget = QWidget()
        stacked_widget.setLayout(self.stacked)
        content_v.addWidget(stacked_widget)
        content_v.addWidget(self.statsPanel)

        main_h.addLayout(content_v)
        self.setLayout(main_h)

        # Estilos globales para botones y tablas (no funcional)
        self.setStyleSheet(
            "QPushButton{font-family: Segoe UI, Arial; font-size:12px;}"
            "QTableWidget{background:#0f1113; color:#dfe7ec; gridline-color:#202124;}"
            "QHeaderView::section{background:#1b1d1f; color:#e6eef6; padding:6px; border: none;}"
        )

        # TIMER optimizado para 25 FPS
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(40)  # 40ms = 25 FPS

        # Cargar incidentes inicialmente
        self.refresh_incidents()

    def on_menu_changed(self, index):
        """Navegar entre páginas desde la barra lateral"""
        # Mapping: 0 Dashboard (cameras), 1 Cámaras, 2 Incidentes
        if index in (0, 1):
            self.stacked.setCurrentIndex(0)
        elif index == 2:
            self.stacked.setCurrentIndex(1)
            self.refresh_incidents()
        elif index == 3:
            # Destinatarios
            self.stacked.setCurrentIndex(2)
            self.refresh_recipients()
        else:
            # Otros items por ahora muestran cameras
            self.stacked.setCurrentIndex(0)

    def refresh_incidents(self):
        """Cargar incidentes desde la DB SQLite local (incidents.db)"""
        db_path = "incidents.db"
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT created_at, camera_name, incident_type, severity, confidence FROM incidents ORDER BY id DESC LIMIT 100")
            rows = cur.fetchall()
            conn.close()

            self.incidents_table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                for c, val in enumerate(row):
                    item = QTableWidgetItem(str(val))
                    item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                    self.incidents_table.setItem(r, c, item)
        except Exception as e:
            print(f"[UI] No se pudo cargar incidents.db: {e}")

    def add_recipient_clicked(self):
        """Agregar destinatario desde la UI a la DB"""
        name = self.rec_name.text().strip()
        email = self.rec_email.text().strip()
        phone = self.rec_phone.text().strip()

        if not name:
            QMessageBox.warning(self, "Error", "El nombre es obligatorio")
            return

        try:
            self.fire_detector.add_recipient(name, email if email else None, phone if phone else None)
            self.rec_name.clear()
            self.rec_email.clear()
            self.rec_phone.clear()
            QMessageBox.information(self, "Éxito", "Destinatario agregado")
            self.refresh_recipients()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo agregar: {e}")

    def refresh_recipients(self):
        """Cargar destinatarios desde la DB y mostrarlos en la tabla"""
        try:
            rows = self.fire_detector.list_recipients()
            self.recipients_table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                self.recipients_table.setItem(r, 0, QTableWidgetItem(str(row.get('id'))))
                self.recipients_table.setItem(r, 1, QTableWidgetItem(str(row.get('name') or '')))
                self.recipients_table.setItem(r, 2, QTableWidgetItem(str(row.get('email') or '')))
                self.recipients_table.setItem(r, 3, QTableWidgetItem(str(row.get('phone') or '')))
                self.recipients_table.setItem(r, 4, QTableWidgetItem(str(row.get('active'))))
        except Exception as e:
            print(f"[UI] No se pudo cargar recipients: {e}")

    def remove_selected_recipient(self):
        """Eliminar el destinatario seleccionado de la DB"""
        row = self.recipients_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Selecciona un destinatario")
            return
        id_item = self.recipients_table.item(row, 0)
        if not id_item:
            return
        rec_id = id_item.text()
        try:
            import sqlite3
            conn = sqlite3.connect(self.fire_detector.db_path)
            cur = conn.cursor()
            cur.execute("DELETE FROM recipients WHERE id = ?", (rec_id,))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Éxito", "Destinatario eliminado")
            self.refresh_recipients()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo eliminar: {e}")

    def export_incidents_to_excel(self):
        """Exportar incidents.db a un archivo Excel usando openpyxl"""
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Guardar reporte", "incidents.xlsx", "Excel Files (*.xlsx)")
            if not path:
                return
            import sqlite3
            conn = sqlite3.connect("incidents.db")
            cur = conn.cursor()
            cur.execute("SELECT id, created_at, camera_name, incident_type, severity, confidence, details FROM incidents ORDER BY id DESC")
            rows = cur.fetchall()
            conn.close()

            # Lazy import openpyxl
            try:
                from openpyxl import Workbook
            except Exception:
                QMessageBox.critical(self, "Error", "Falta dependencia 'openpyxl'. Instala: pip install openpyxl")
                return

            wb = Workbook()
            ws = wb.active
            ws.append(["ID","Hora","Cámara","Tipo","Severidad","Confianza","Detalles"])
            for row in rows:
                ws.append(list(row))
            wb.save(path)
            QMessageBox.information(self, "Éxito", f"Exportado a {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar: {e}")

    def open_camera_manager(self):
        """Abrir diálogo de gestión de cámaras"""
        dialog = CameraDialog(self)
        dialog.exec()

    def on_mode_changed(self, index):
        """Cambiar modo de detección"""
        self.detection_mode = self.modeSelector.itemData(index)
        mode_names = {
            "general": "Detección General",
            "accidentes": "Detección de Accidentes",
            "personas": "Rastreo de Personas",
            "robos": "Detección de Robos"
        }
        print(f"[UI] Modo: {mode_names.get(self.detection_mode, 'Desconocido')}")

    def update(self):
        """Actualizar frames y aplicar detecciones"""

        for i, cam in enumerate(self.cams):
            if i >= len(self.labels):
                break

            frame = cam.read()

            if frame is None:
                self.labels[i].setText("SIN VIDEO")
                self.labels[i].setStyleSheet("background-color: #1a1a1a; border: 2px solid #34495e; border-radius: 5px; color: #7f8c8d; font-weight: bold;")
                continue

            # Redimensionar según config optimizada (384x216)
            frame = cv2.resize(frame, DETECTION_CONFIG['frame_resize'])
            self.frame_count += 1
            self.total_frames_processed += 1

            # Aplicar detecciones según modo
            if i == 0:  # Solo en la primera cámara (optimización)
                if self.detection_mode == "general":
                    frame = self.detector.predict(frame)
                    
                elif self.detection_mode == "accidentes" and self.accident_detector:
                    # Ejecutar detector de accidentes solo si la cámara tiene habilitado
                    if getattr(cam, 'settings', {}).get('detect_accident', True):
                        try:
                            is_accident, details, prob = self.accident_detector.analyze_accident(frame)
                            if is_accident:
                                print(f"[UI] Posible accidente en {getattr(cam,'name',f'Cam {i+1}')}: {details} ({prob:.2f})")
                                try:
                                    self.accident_detector.log_accident(frame, (is_accident, details, prob))
                                except Exception as e:
                                    print(f"[UI] Error al loggear accidente: {e}")
                        except Exception as e:
                            print(f"[UI] Error en detector de accidentes: {e}")
                    
                elif self.detection_mode == "personas" and self.person_tracker:
                    # person tracker can be gated if needed in future
                    pass
                    
                elif self.detection_mode == "robos" and self.theft_detector:
                    # Ejecutar pipeline simplificado de detección de robos si la cámara lo permite
                    if getattr(cam, 'settings', {}).get('detect_theft', True):
                        try:
                            # Mantener contador de frames en el detector si existe
                            if hasattr(self.theft_detector, 'frame_count'):
                                try:
                                    self.theft_detector.frame_count += 1
                                except Exception:
                                    pass

                            people, objects_detected = self.theft_detector.detect_people_and_objects(frame)
                            tracked_people = self.theft_detector.track_people(people, frame)
                            tracked_objects = self.theft_detector.track_objects(objects_detected)
                            tracked_people, object_transfer = self.theft_detector.match_objects_to_people(tracked_people, tracked_objects)

                            people_with_valuables = sum(1 for p in tracked_people.values() if p.get('has_valuable'))
                            if people_with_valuables > 0:
                                suspicious_activity = self.theft_detector.detect_suspicious_activity(frame)
                            else:
                                suspicious_activity = {'fight': False, 'running': False, 'suspicious_activity': False, 'confidence': 0}

                            theft_prob, theft_details = self.theft_detector.analyze_theft(tracked_people, suspicious_activity, object_transfer)
                            if theft_prob > getattr(self.theft_detector, 'alarm_threshold', 0.6):
                                print(f"[UI] Posible robo en {getattr(cam,'name',f'Cam {i+1}')}: prob {theft_prob:.2f}")
                        except Exception as e:
                            print(f"[UI] Error en pipeline de detección de robos: {e}")

            if self.fire_detector and getattr(cam, 'settings', {}).get('detect_fire', True):
                try:
                    incident = self.fire_detector.analyze_frame(frame, camera_name=cam.name if hasattr(cam, 'name') else f'Cámara {i+1}')
                    if incident:
                        print(f"[UI] Incidente de incendio detectado en {incident['camera_name']}: {incident['details']}")
                except Exception as e:
                    print(f"[UI] Error en detector de incendios: {e}")

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            h, w, ch = rgb.shape
            img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)

            self.labels[i].setPixmap(QPixmap.fromImage(img))
        
        # Actualizar estadísticas cada 60 frames (2.4 segundos a 25 FPS)
        if self.frame_count % 60 == 0:
            camera_status = "✓" if len(self.cams) > 0 else "✗"
            active_cams = len([c for c in self.cams if c.frame is not None])
            
            stats_text = (
                f"╔═══════════════════════════════════════════════╗\n"
                f"║         ESTADÍSTICAS DEL SISTEMA             ║\n"
                f"╠═══════════════════════════════════════════════╣\n"
                f"║ Frames procesados: {self.total_frames_processed:<24}║\n"
                f"║ Modo: {self.modeSelector.currentText():<38}║\n"
                f"║ GPU: NVIDIA Quadro P1000 (FP16)               ║\n"
                f"║ FPS objetivo: {self.target_fps:<32}║\n"
                f"║ Cámaras configuradas: {len(self.cams):<27}║\n"
                f"║ Cámaras activas: {active_cams}/{len(self.cams):<33}║\n"
                f"║ Resolución: {DETECTION_CONFIG['frame_resize'][0]}x{DETECTION_CONFIG['frame_resize'][1]}  │  Batch: {DETECTION_CONFIG['batch_size']:<19}║\n"
                f"║ CPU Threads: {DETECTION_CONFIG['workers']:<34}║\n"
                f"╚═══════════════════════════════════════════════╝"
            )
            self.statsLabel.setText(stats_text)


