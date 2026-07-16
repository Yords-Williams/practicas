import cv2
import json
import os
import numpy as np
import psutil
from PySide6.QtWidgets import (
    QWidget, QLabel, QGridLayout, QVBoxLayout, QHBoxLayout, QPushButton,
    QFrame, QComboBox, QStackedLayout, QListWidget, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QSizePolicy, QLineEdit, QMessageBox,
    QFileDialog, QCheckBox, QGroupBox, QScrollArea, QSpinBox, QFormLayout
)
from PySide6.QtGui import QImage, QPixmap, QColor
from PySide6.QtCore import QTimer, Qt
from camera_dialog import CameraDialog
from camera import CamaraRTSP
from config import DETECTION_CONFIG
from modulos.incendio.detector import FireDetectionSystem

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

        # Monitoreo de hardware (pynvml)
        self._nvml_handle = None
        try:
            import pynvml
            pynvml.nvmlInit()
            self._nvml_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        except Exception:
            pass

        self.setWindowTitle("Alertas tempranas")
        self.setMinimumSize(960, 600)

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
            lbl.setMinimumSize(280, 160)
            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            lbl.setStyleSheet("background-color:#0f1113; border:2px solid #2b2b2b; border-radius:8px; color:#bfc9d4; font-weight:bold; text-align:center;")
            lbl.setAlignment(Qt.AlignCenter)
            self.labels.append(lbl)
            self.grid.addWidget(lbl, i // cols, i % cols)

        # ===== BARRA DE ESTADO (reemplaza el panel ASCII) =====
        self.statusBar = QFrame()
        self.statusBar.setObjectName("statusBar")
        self.statusBar.setFixedHeight(36)
        self.statusBar.setStyleSheet(
            "QFrame#statusBar{background:#0d1117; border-top:1px solid #21262d;}"
        )
        sb_layout = QHBoxLayout()
        sb_layout.setContentsMargins(12, 0, 12, 0)
        sb_layout.setSpacing(20)

        def _stat_lbl(icon, key):
            lbl = QLabel(f"{icon}  —")
            lbl.setStyleSheet("color:#8b949e; font-size:11px; font-family:'Segoe UI';")
            sb_layout.addWidget(lbl)
            return lbl

        self._sb_frames   = _stat_lbl("🎞",  "frames")
        self._sb_mode     = _stat_lbl("🎯",  "modo")
        self._sb_gpu      = _stat_lbl("⚡",  "gpu")
        self._sb_fps      = _stat_lbl("🕐",  "fps")
        self._sb_cams     = _stat_lbl("📷",  "cams")
        sb_layout.addStretch()
        self.statusBar.setLayout(sb_layout)

        # ===== STACKED CONTENT PAGES =====
        self.stacked = QStackedLayout()

        # ── Página 0: Cámaras (barra de estado al fondo) ──────────────────
        cameras_widget = QWidget()
        cam_layout = QVBoxLayout()
        cam_layout.setContentsMargins(0, 0, 0, 0)
        cam_layout.setSpacing(0)
        cam_layout.addLayout(self.grid)
        cam_layout.addWidget(self.statusBar)   # barra compacta solo en cámaras
        cameras_widget.setLayout(cam_layout)

        # ── Página 1: Incidentes ─────────────────────────────────────────────
        incidents_widget = QWidget()
        incidents_layout = QVBoxLayout()
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

        # ── Página 2: Destinatarios ──────────────────────────────────────────
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

        # ── Página 3: Notificaciones ─────────────────────────────────────────
        notif_widget = QWidget()
        notif_layout = QVBoxLayout()
        notif_layout.setAlignment(Qt.AlignTop)

        notif_title = QLabel("⚙ Configuración de Notificaciones")
        notif_title.setStyleSheet("font-size:16px; font-weight:bold; color:#e6eef6; margin-bottom:8px;")
        notif_layout.addWidget(notif_title)

        notif_desc = QLabel("Activa o desactiva los canales por los que se enviarán alertas de incidentes.")
        notif_desc.setStyleSheet("color:#99aab5; margin-bottom:16px;")
        notif_desc.setWordWrap(True)
        notif_layout.addWidget(notif_desc)

        # ── Telegram ──
        tg_group = QGroupBox("Telegram")
        tg_group.setStyleSheet("QGroupBox{color:#e6eef6; font-weight:bold; border:1px solid #2e74b5; border-radius:6px; margin-top:6px; padding:12px;} QGroupBox::title{subcontrol-origin:margin; padding:0 6px;}")
        tg_layout = QFormLayout()
        self.chk_telegram = QCheckBox("Habilitado")
        self.chk_telegram.setStyleSheet("color:#e6eef6;")
        tg_layout.addRow(self.chk_telegram)
        tg_token_lbl = QLabel("Token del bot:")
        tg_token_lbl.setStyleSheet("color:#bfc9d4;")
        self.tg_token_edit = QLineEdit()
        self.tg_token_edit.setPlaceholderText("Ej: 123456:ABCDef...")
        self.tg_token_edit.setEchoMode(QLineEdit.Password)
        tg_layout.addRow(tg_token_lbl, self.tg_token_edit)
        tg_chat_lbl = QLabel("Chat ID(s) (separados por coma):")
        tg_chat_lbl.setStyleSheet("color:#bfc9d4;")
        self.tg_chats_edit = QLineEdit()
        self.tg_chats_edit.setPlaceholderText("Ej: 123456789, 987654321")
        tg_layout.addRow(tg_chat_lbl, self.tg_chats_edit)
        tg_group.setLayout(tg_layout)
        notif_layout.addWidget(tg_group)

        # ── Gmail ──
        gm_group = QGroupBox("Gmail")
        gm_group.setStyleSheet("QGroupBox{color:#e6eef6; font-weight:bold; border:1px solid #2e74b5; border-radius:6px; margin-top:12px; padding:12px;} QGroupBox::title{subcontrol-origin:margin; padding:0 6px;}")
        gm_layout = QFormLayout()
        self.chk_gmail = QCheckBox("Habilitado")
        self.chk_gmail.setStyleSheet("color:#e6eef6;")
        gm_layout.addRow(self.chk_gmail)
        gm_sender_lbl = QLabel("Correo remitente:")
        gm_sender_lbl.setStyleSheet("color:#bfc9d4;")
        self.gm_sender_edit = QLineEdit()
        self.gm_sender_edit.setPlaceholderText("tu_correo@gmail.com")
        gm_layout.addRow(gm_sender_lbl, self.gm_sender_edit)
        gm_pass_lbl = QLabel("Contraseña de aplicación:")
        gm_pass_lbl.setStyleSheet("color:#bfc9d4;")
        self.gm_pass_edit = QLineEdit()
        self.gm_pass_edit.setEchoMode(QLineEdit.Password)
        self.gm_pass_edit.setPlaceholderText("xxxx xxxx xxxx xxxx")
        gm_layout.addRow(gm_pass_lbl, self.gm_pass_edit)
        gm_dest_lbl = QLabel("Destinatarios (separados por coma):")
        gm_dest_lbl.setStyleSheet("color:#bfc9d4;")
        self.gm_dest_edit = QLineEdit()
        self.gm_dest_edit.setPlaceholderText("correo1@gmail.com, correo2@gmail.com")
        gm_layout.addRow(gm_dest_lbl, self.gm_dest_edit)
        gm_group.setLayout(gm_layout)
        notif_layout.addWidget(gm_group)

        save_notif_btn = QPushButton("💾  Guardar configuración de notificaciones")
        save_notif_btn.setStyleSheet("QPushButton{background-color:#27ae60; color:white; font-weight:bold; padding:10px; border-radius:6px; margin-top:16px;} QPushButton:hover{background-color:#2ecc71}")
        save_notif_btn.clicked.connect(self.save_notifications_config)
        notif_layout.addWidget(save_notif_btn)
        notif_layout.addStretch()
        notif_widget.setLayout(notif_layout)
        self._load_notifications_config()   # poblar campos al iniciar

        # ── Página 4: Ajustes ────────────────────────────────────────────────
        settings_widget = QScrollArea()
        settings_widget.setWidgetResizable(True)
        settings_inner = QWidget()
        settings_layout = QVBoxLayout()
        settings_layout.setAlignment(Qt.AlignTop)

        settings_title = QLabel("⚙ Ajustes del Sistema")
        settings_title.setStyleSheet("font-size:16px; font-weight:bold; color:#e6eef6; margin-bottom:8px;")
        settings_layout.addWidget(settings_title)

        # Módulos por cámara
        cam_mod_title = QLabel("Módulos de detección por cámara")
        cam_mod_title.setStyleSheet("font-size:13px; font-weight:bold; color:#2e74b5; margin-top:12px; margin-bottom:4px;")
        settings_layout.addWidget(cam_mod_title)
        cam_mod_desc = QLabel("Desactiva módulos en cámaras específicas para reducir el consumo de CPU/GPU.")
        cam_mod_desc.setStyleSheet("color:#99aab5;")
        cam_mod_desc.setWordWrap(True)
        settings_layout.addWidget(cam_mod_desc)

        self.cam_module_checks = []   # list of (cam_index, chk_fire, chk_theft, chk_accident)
        cameras_config = CameraDialog.get_cameras()
        for idx, cam_cfg in enumerate(cameras_config):
            cam_box = QGroupBox(f"📹  {cam_cfg.get('name', f'Cámara {idx+1}')}")
            cam_box.setStyleSheet(
                "QGroupBox{color:#ffffff; border:1px solid #444; border-radius:6px;"
                " margin-top:14px; padding-top:10px;}"
                "QGroupBox::title{subcontrol-origin:margin; subcontrol-position:top left;"
                " padding:2px 8px; color:#ffffff; font-size:13px; font-weight:bold;}"
            )
            cam_row = QHBoxLayout()
            chk_fire = QCheckBox("🔥 Incendios")
            chk_theft = QCheckBox("🚨 Robos")
            chk_acc = QCheckBox("🚗 Choques")
            for chk in (chk_fire, chk_theft, chk_acc):
                chk.setStyleSheet("color:#e6eef6; padding:4px 12px;")
            chk_fire.setChecked(cam_cfg.get('detect_fire', True))
            chk_theft.setChecked(cam_cfg.get('detect_theft', True))
            chk_acc.setChecked(cam_cfg.get('detect_accident', True))
            cam_row.addWidget(chk_fire)
            cam_row.addWidget(chk_theft)
            cam_row.addWidget(chk_acc)
            cam_row.addStretch()
            cam_box.setLayout(cam_row)
            settings_layout.addWidget(cam_box)
            self.cam_module_checks.append((idx, chk_fire, chk_theft, chk_acc))

        # FPS objetivo
        fps_group = QGroupBox("Rendimiento")
        fps_group.setStyleSheet(
            "QGroupBox{color:#ffffff; border:1px solid #444; border-radius:6px;"
            " margin-top:14px; padding-top:10px;}"
            "QGroupBox::title{subcontrol-origin:margin; subcontrol-position:top left;"
            " padding:2px 8px; color:#ffffff; font-size:13px; font-weight:bold;}"
        )
        fps_form = QFormLayout()
        fps_lbl = QLabel("FPS objetivo (1-30):")
        fps_lbl.setStyleSheet("color:#bfc9d4;")
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 30)
        self.fps_spin.setValue(DETECTION_CONFIG.get('fps_limit', 25))
        self.fps_spin.setStyleSheet("background:#1a1a2e; color:white; padding:4px;")
        fps_form.addRow(fps_lbl, self.fps_spin)
        fps_group.setLayout(fps_form)
        settings_layout.addWidget(fps_group)

        # Hardware del equipo
        hw_group = QGroupBox("Hardware del Equipo")
        hw_group.setStyleSheet(
            "QGroupBox{color:#ffffff; border:1px solid #444; border-radius:6px;"
            " margin-top:14px; padding-top:10px;}"
            "QGroupBox::title{subcontrol-origin:margin; subcontrol-position:top left;"
            " padding:2px 8px; color:#ffffff; font-size:13px; font-weight:bold;}"
        )
        hw_form = QFormLayout()
        hw_form.setLabelAlignment(Qt.AlignRight)
        _lbl_style = "color:#bfc9d4; font-size:12px;"
        _val_style = "color:#58a6ff; font-size:12px; font-weight:bold;"

        self._lbl_cpu      = QLabel("—"); self._lbl_cpu.setStyleSheet(_val_style)
        self._lbl_ram      = QLabel("—"); self._lbl_ram.setStyleSheet(_val_style)
        self._lbl_gpu_mem  = QLabel("—"); self._lbl_gpu_mem.setStyleSheet(_val_style)
        self._lbl_gpu_util = QLabel("—"); self._lbl_gpu_util.setStyleSheet(_val_style)

        for key, val in (("CPU:", self._lbl_cpu), ("RAM:", self._lbl_ram),
                         ("GPU VRAM:", self._lbl_gpu_mem), ("GPU Carga:", self._lbl_gpu_util)):
            lbl = QLabel(key); lbl.setStyleSheet(_lbl_style)
            hw_form.addRow(lbl, val)
        hw_group.setLayout(hw_form)
        settings_layout.addWidget(hw_group)

        save_settings_btn = QPushButton("💾  Guardar ajustes")
        save_settings_btn.setStyleSheet("QPushButton{background-color:#2980b9; color:white; font-weight:bold; padding:10px; border-radius:6px; margin-top:16px;} QPushButton:hover{background-color:#3498db}")
        save_settings_btn.clicked.connect(self.save_settings)
        settings_layout.addWidget(save_settings_btn)
        settings_layout.addStretch()
        settings_inner.setLayout(settings_layout)
        settings_widget.setWidget(settings_inner)

        self.stacked.addWidget(cameras_widget)     # 0
        self.stacked.addWidget(incidents_widget)   # 1
        self.stacked.addWidget(recipients_widget)  # 2
        self.stacked.addWidget(notif_widget)        # 3
        self.stacked.addWidget(settings_widget)    # 4

        # ===== LEFT SIDEBAR =====
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setStyleSheet(
            "QFrame#sidebar{"
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0d1117,stop:1 #161b22);"
            "border-right:1px solid #21262d;}"
        )
        self.sidebar.setFixedWidth(200)

        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Logo / título
        logo_lbl = QLabel("  Alertas Tempranas")
        logo_lbl.setFixedHeight(52)
        logo_lbl.setStyleSheet(
            "background:#010409; color:#58a6ff; font-size:14px; font-weight:bold;"
            "font-family:'Segoe UI'; border-bottom:1px solid #21262d; padding-left:8px;"
        )
        sidebar_layout.addWidget(logo_lbl)

        # ── Botones de menú (sin QListWidget → sin scroll) ──────────────────
        MENU_ITEMS = [
            ("Cámaras",         "📷"),
            ("Incidentes",      "🚨"),
            ("Destinatarios",   "👥"),
            ("Notificaciones",  "🔔"),
            ("Ajustes",         "⚙"),
        ]

        _BTN_BASE = (
            "QPushButton{"
            "background:transparent; color:#8b949e; border:none; border-left:3px solid transparent;"
            "text-align:left; padding:10px 14px; font-size:13px; font-family:'Segoe UI';}"
            "QPushButton:hover{"
            "background:#161b22; color:#c9d1d9; border-left:3px solid #30363d;}"
        )
        _BTN_ACTIVE = (
            "QPushButton{"
            "background:#1f2937; color:#58a6ff; border:none; border-left:3px solid #58a6ff;"
            "text-align:left; padding:10px 14px; font-size:13px; font-family:'Segoe UI';"
            "font-weight:bold;}"
        )

        self._menu_btns = []
        for idx, (label, icon) in enumerate(MENU_ITEMS):
            btn = QPushButton(f"  {icon}  {label}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(_BTN_ACTIVE if idx == 0 else _BTN_BASE)
            btn.clicked.connect(lambda checked, i=idx: self._on_menu_btn(i))
            sidebar_layout.addWidget(btn)
            self._menu_btns.append(btn)

        self._active_menu_idx = 0   # Cámaras por defecto
        self._btn_base_style  = _BTN_BASE
        self._btn_active_style = _BTN_ACTIVE
        sidebar_layout.addStretch()
        self.sidebar.setLayout(sidebar_layout)

        # ===== MAIN LAYOUT =====
        main_h = QHBoxLayout()
        main_h.addWidget(self.sidebar)

        content_v = QVBoxLayout()
        content_v.addWidget(self.topBar)
        stacked_widget = QWidget()
        stacked_widget.setLayout(self.stacked)
        content_v.addWidget(stacked_widget)
        # statsPanel ya está dentro de cameras_widget — no se añade aquí

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

    def _on_menu_btn(self, index):
        """Marcar botón activo y navegar a la página correspondiente."""
        for i, btn in enumerate(self._menu_btns):
            btn.setStyleSheet(self._btn_active_style if i == index else self._btn_base_style)
        self._active_menu_idx = index
        self.on_menu_changed(index)

    def on_menu_changed(self, index):
        """Navegar entre páginas desde la barra lateral"""
        if index == 0:              # Cámaras
            self.stacked.setCurrentIndex(0)
        elif index == 1:            # Incidentes
            self.stacked.setCurrentIndex(1)
            self.refresh_incidents()
        elif index == 2:            # Destinatarios
            self.stacked.setCurrentIndex(2)
            self.refresh_recipients()
        elif index == 3:            # Notificaciones
            self.stacked.setCurrentIndex(3)
            self._load_notifications_config()
        elif index == 4:            # Ajustes
            self.stacked.setCurrentIndex(4)
        else:
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
        """Abrir diálogo de gestión de cámaras y recargar en caliente al cerrar."""
        dialog = CameraDialog(self)
        dialog.exec()

        # Detener cámaras actuales
        for cam in self.cams:
            try:
                cam.stop()
            except Exception:
                pass

        # Recargar desde cameras_config.json
        self.cams = []
        for cam_cfg in CameraDialog.get_cameras():
            try:
                cam = CamaraRTSP(cam_cfg["url"], cam_cfg["name"])
                cam.settings = {
                    'detect_fire':     cam_cfg.get('detect_fire',     True),
                    'detect_theft':    cam_cfg.get('detect_theft',    True),
                    'detect_accident': cam_cfg.get('detect_accident', True),
                }
                self.cams.append(cam)
                print(f"[UI] ✓ Cámara recargada: {cam_cfg['name']}")
            except Exception as e:
                print(f"[UI] ✗ Error recargando {cam_cfg.get('name','?')}: {e}")

        # Resetear labels de la grilla
        for lbl in self.labels:
            lbl.setText("SIN VIDEO")
            lbl.setStyleSheet(
                "background-color:#0f1113; border:2px solid #2b2b2b; "
                "border-radius:8px; color:#bfc9d4; font-weight:bold;"
            )
            lbl.setPixmap(lbl.pixmap() and lbl.pixmap() or type('_',(),{'isNull':lambda s:True})())
            lbl.clear()

        print(f"[UI] Cámaras recargadas: {len(self.cams)} activa(s)")

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
        
        # Actualizar barra de estado cada 30 frames (~1.2 s a 25 FPS)
        if self.frame_count % 30 == 0:
            active_cams = len([c for c in self.cams if c.frame is not None])
            mode_name = self.modeSelector.currentText().split(' ', 1)[-1]  # sin emoji
            self._sb_frames.setText(f"Frames: {self.total_frames_processed:,}")
            self._sb_mode.setText(f"Modo: {mode_name}")
            self._sb_fps.setText(f"FPS: {self.target_fps}")
            self._sb_cams.setText(f"Camaras: {active_cams}/{len(self.cams)}")
            self._update_hw_labels()

    # ── Notificaciones ────────────────────────────────────────────────────────
    def _load_notifications_config(self):
        """Cargar y poblar los campos de notificaciones desde el JSON."""
        cfg_path = "notifications_config.json"
        try:
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            else:
                cfg = {}

            tg = cfg.get("telegram", {})
            self.chk_telegram.setChecked(bool(tg.get("enabled", False)))
            self.tg_token_edit.setText(tg.get("token", ""))
            chat_ids = tg.get("chat_ids", [])
            self.tg_chats_edit.setText(", ".join(str(c) for c in chat_ids))

            gm = cfg.get("gmail", {})
            self.chk_gmail.setChecked(bool(gm.get("enabled", False)))
            self.gm_sender_edit.setText(gm.get("sender", ""))
            self.gm_pass_edit.setText(gm.get("app_password", ""))
            to_emails = gm.get("to_emails", [])
            self.gm_dest_edit.setText(", ".join(str(e) for e in to_emails))
        except Exception as e:
            print(f"[UI] Error cargando notificaciones: {e}")

    def save_notifications_config(self):
        """Guardar configuración de notificaciones al JSON."""
        cfg_path = "notifications_config.json"
        try:
            cfg = {}
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)

            # Telegram
            token = self.tg_token_edit.text().strip()
            chat_ids_raw = self.tg_chats_edit.text().strip()
            chat_ids = [c.strip() for c in chat_ids_raw.split(",") if c.strip()]
            cfg["telegram"] = {
                "enabled": self.chk_telegram.isChecked(),
                "token": token,
                "chat_ids": chat_ids,
            }

            # Gmail
            to_emails_raw = self.gm_dest_edit.text().strip()
            to_emails = [e.strip() for e in to_emails_raw.split(",") if e.strip()]
            cfg["gmail"] = {
                "enabled": self.chk_gmail.isChecked(),
                "sender": self.gm_sender_edit.text().strip(),
                "app_password": self.gm_pass_edit.text().strip(),
                "to_emails": to_emails,
                "include_frame": True,
            }

            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)

            QMessageBox.information(self, "Guardado", "Configuración de notificaciones guardada correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar: {e}")

    # ── Ajustes ───────────────────────────────────────────────────────────────
    def _update_hw_labels(self):
        """Actualizar etiquetas de rendimiento del hardware en la página de Ajustes."""
        if not hasattr(self, '_lbl_cpu'):
            return

        def color(pct):
            return '#e74c3c' if pct > 80 else '#f39c12' if pct > 60 else '#2ecc71'

        # CPU y RAM via psutil (siempre disponible)
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            ram_pct  = mem.percent
            ram_used = mem.used  / 1024**3
            ram_tot  = mem.total / 1024**3
            self._lbl_cpu.setText(
                f"<span style='color:{color(cpu)}'>{cpu:.0f}%</span>"
            )
            self._lbl_ram.setText(
                f"<span style='color:{color(ram_pct)}'>{ram_pct:.0f}%</span>"
                f"<span style='color:#99aab5'> ({ram_used:.1f}/{ram_tot:.1f} GB)</span>"
            )
        except Exception:
            pass

        # GPU via pynvml (si funciona) o torch.cuda como fallback
        gpu_mem_txt  = "N/A"
        gpu_util_txt = "N/A"
        sb_gpu_txt   = "GPU: N/A"

        if self._nvml_handle is not None:
            try:
                import pynvml
                mi   = pynvml.nvmlDeviceGetMemoryInfo(self._nvml_handle)
                util = pynvml.nvmlDeviceGetUtilizationRates(self._nvml_handle)
                gpu_used = mi.used  / 1024**3
                gpu_tot  = mi.total / 1024**3
                gpu_pct  = util.gpu
                gpu_mem_txt  = (f"<span style='color:{color(gpu_used/gpu_tot*100)}'>"
                                f"{gpu_used:.1f}/{gpu_tot:.1f} GB</span>")
                gpu_util_txt = f"<span style='color:{color(gpu_pct)}'>{gpu_pct}%</span>"
                sb_gpu_txt   = f"GPU: {gpu_pct}%  VRAM: {gpu_used:.1f}/{gpu_tot:.1f}GB"
            except Exception:
                # Deshabilitar pynvml para no seguir intentando
                self._nvml_handle = None

        if self._nvml_handle is None:
            # Fallback: torch.cuda para memoria
            try:
                import torch
                if torch.cuda.is_available():
                    res  = torch.cuda.memory_reserved(0)  / 1024**3
                    tot  = torch.cuda.get_device_properties(0).total_memory / 1024**3
                    gpu_mem_txt  = (f"<span style='color:{color(res/tot*100)}'>"
                                    f"{res:.1f}/{tot:.1f} GB</span>")
                    gpu_util_txt = "<span style='color:#99aab5'>N/A</span>"
                    sb_gpu_txt   = f"GPU VRAM: {res:.1f}/{tot:.1f}GB"
            except Exception:
                pass

        self._lbl_gpu_mem.setText(gpu_mem_txt)
        self._lbl_gpu_util.setText(gpu_util_txt)
        self._sb_gpu.setText(sb_gpu_txt)

    def save_settings(self):
        """Guardar ajustes de módulos por cámara y FPS."""
        try:
            cameras_config = CameraDialog.get_cameras()
            for idx, chk_fire, chk_theft, chk_acc in self.cam_module_checks:
                if idx < len(cameras_config):
                    cameras_config[idx]['detect_fire']     = chk_fire.isChecked()
                    cameras_config[idx]['detect_theft']    = chk_theft.isChecked()
                    cameras_config[idx]['detect_accident'] = chk_acc.isChecked()

            # Persistir en cameras_config.json
            cfg_path = "cameras_config.json"
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cameras_config, f, indent=2, ensure_ascii=False)

            # Actualizar objetos de cámara en tiempo real
            new_fps = self.fps_spin.value()
            self.target_fps = new_fps
            self.timer.setInterval(max(1, 1000 // new_fps))
            for cam in self.cams:
                if hasattr(cam, 'settings') and cam.name:
                    for cfg in cameras_config:
                        if cfg.get('name') == cam.name:
                            cam.settings = {
                                'detect_fire':     cfg.get('detect_fire', True),
                                'detect_theft':    cfg.get('detect_theft', True),
                                'detect_accident': cfg.get('detect_accident', True),
                            }
                            break

            QMessageBox.information(self, "Guardado", "Ajustes guardados. Los cambios se aplican inmediatamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar: {e}")


