import cv2
import json
import os
import psutil
from PySide6.QtWidgets import (
    QWidget, QLabel, QGridLayout, QVBoxLayout, QHBoxLayout, QPushButton,
    QFrame, QComboBox, QStackedLayout, QListWidget, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy, QLineEdit, QMessageBox,
    QFileDialog, QCheckBox, QGroupBox, QScrollArea, QSpinBox, QFormLayout,
    QStackedWidget, QRadioButton, QButtonGroup, QInputDialog
)
from PySide6.QtGui import QImage, QPixmap, QColor
from PySide6.QtCore import QTimer, Qt, Signal
from camera_dialog import CameraDialog
from camera import CamaraRTSP
from config import DETECTION_CONFIG, THREADING_CONFIG
from analysis_worker import CameraAnalysisWorker
from modulos.incendio.detector import FireDetectionSystem
from app_storage import user_data_path
from modulos.alarma.secure_config import (
    protect_notification_secrets,
    unprotect_notification_secrets,
)


class CameraViewLabel(QLabel):
    doubleClicked = Signal()

    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)


class CCTVWindow(QWidget):

    def __init__(self, cams, detector, accident_detector=None, person_tracker=None, theft_detector=None, fire_detector=None):
        super().__init__()

        self.cams = cams
        self.detector = detector
        self.accident_detector = accident_detector
        self.person_tracker = person_tracker
        self.theft_detector = theft_detector
        self.fire_detector = fire_detector or FireDetectionSystem()
        
        # Estadísticas
        self.frame_count = 0
        self.total_frames_processed = 0
        self.frame_times = []
        self.target_fps = DETECTION_CONFIG['fps_limit']
        self._single_camera_index = None

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
        self._analysis_errors = []
        self._analysis_warnings = []
        self.statusBtn.clicked.connect(self._show_analysis_errors)
        
        # Botón para gestionar cámaras
        self.camera_btn = QPushButton("📹 Gestionar Cámaras")
        self.camera_btn.setStyleSheet("QPushButton{background-color:#e74c3c; color:white; font-weight:bold; padding:8px; border-radius:6px} QPushButton:hover{background-color:#ff5b48}")
        self.camera_btn.clicked.connect(self.open_camera_manager)

        self.resolution_selector = QComboBox()
        self.resolution_selector.addItem("Vista individual: 720p", (1280, 720))
        self.resolution_selector.addItem("Vista individual: 1080p", (1920, 1080))
        self.resolution_selector.setToolTip(
            "Resolución solicitada al abrir una cámara. La resolución real depende del mainstream configurado."
        )
        self.resolution_selector.setVisible(False)
        self.resolution_selector.setStyleSheet(
            "QComboBox{padding:6px; min-width:180px; background-color:#22313f; "
            "color:white; border:1px solid #3b3b3b; border-radius:4px}"
        )
        self.resolution_selector.currentIndexChanged.connect(
            self._update_camera_stream_profiles
        )

        topLayout = QHBoxLayout()
        topLayout.addWidget(self.logo_label)
        topLayout.addSpacing(6)
        topLayout.addWidget(self.statusBtn)
        self.analysis_mode_label = QLabel("Módulos habilitados por cámara")
        self.analysis_mode_label.setStyleSheet("color:#dfe7ec; padding:6px;")
        topLayout.addWidget(self.analysis_mode_label)
        topLayout.addWidget(self.resolution_selector)
        topLayout.addWidget(self.camera_btn)
        topLayout.addStretch()
        self.topBar.setLayout(topLayout)

        # ===== GRID CAMERAS ===== (will be placed in a stacked page)
        self.grid = QGridLayout()
        self.labels = []
        self.risk_labels = []

        # Cada tarjeta contiene el video y los tres riesgos a su derecha.
        max_cameras = THREADING_CONFIG['max_cameras']
        cols = THREADING_CONFIG['grid_columns']
        self.camera_scores = [{"fire": 0.0, "accident": 0.0, "theft": 0.0} for _ in range(max_cameras)]
        for i in range(max_cameras):
            card = QFrame()
            card.setStyleSheet("QFrame{background:#0f1113; border:1px solid #2b2b2b; border-radius:8px;}")
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(4, 4, 4, 4)
            lbl = CameraViewLabel("SIN VIDEO")
            lbl.setMinimumSize(220, 140)
            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            lbl.setStyleSheet("border:none; color:#bfc9d4; font-weight:bold;")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setScaledContents(True)
            lbl.setCursor(Qt.PointingHandCursor)
            lbl.setToolTip("Doble clic para abrir esta cámara")
            lbl.doubleClicked.connect(
                lambda camera_index=i: self._show_single_camera(camera_index)
            )
            card_layout.addWidget(lbl, 1)

            scores = QVBoxLayout()
            scores.setContentsMargins(4, 8, 4, 8)
            score_labels = {}
            for key, title, color in (
                ("fire", "Fuego", "#e74c3c"),
                ("accident", "Choque", "#f39c12"),
                ("theft", "Robo", "#9b59b6"),
            ):
                value = QLabel(f"{title}\n0%")
                value.setAlignment(Qt.AlignCenter)
                value.setMinimumWidth(64)
                value.setStyleSheet(f"border:none; color:{color}; font-size:11px; font-weight:bold;")
                scores.addWidget(value)
                score_labels[key] = value
            scores.addStretch()
            card_layout.addLayout(scores)
            self.labels.append(lbl)
            self.risk_labels.append(score_labels)
            self.grid.addWidget(card, i // cols, i % cols)

        grid_widget = QWidget()
        grid_widget.setLayout(self.grid)
        self.camera_stack = QStackedWidget()
        self.camera_stack.addWidget(grid_widget)

        single_widget = QWidget()
        single_layout = QVBoxLayout(single_widget)
        single_header = QHBoxLayout()
        self.single_camera_title = QLabel("Vista individual")
        self.single_camera_title.setStyleSheet(
            "color:#e6eef6; font-size:14px; font-weight:bold;"
        )
        back_to_grid_btn = QPushButton("Volver al mosaico")
        back_to_grid_btn.clicked.connect(self._show_camera_grid)
        single_header.addWidget(self.single_camera_title)
        single_header.addStretch()
        single_header.addWidget(back_to_grid_btn)
        self.single_view_label = QLabel("SIN VIDEO")
        self.single_view_label.setAlignment(Qt.AlignCenter)
        self.single_view_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.single_view_label.setScaledContents(True)
        self.single_view_label.setStyleSheet(
            "background:#0f1113; color:#bfc9d4; font-weight:bold;"
        )
        single_layout.addLayout(single_header)
        single_layout.addWidget(self.single_view_label, 1)
        self.camera_stack.addWidget(single_widget)

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
        self._sb_analysis = _stat_lbl("🧠", "analysis")
        sb_layout.addStretch()
        self.statusBar.setLayout(sb_layout)

        # ===== STACKED CONTENT PAGES =====
        self.stacked = QStackedLayout()

        # ── Página 0: Cámaras (barra de estado al fondo) ──────────────────
        cameras_widget = QWidget()
        cam_layout = QVBoxLayout()
        cam_layout.setContentsMargins(0, 0, 0, 0)
        cam_layout.setSpacing(0)
        cam_layout.addWidget(self.camera_stack, 1)
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
        recipients_widget.setObjectName("recipientsPage")
        recipients_layout = QVBoxLayout()
        recipients_layout.setContentsMargins(20, 18, 20, 18)
        recipients_layout.setSpacing(12)

        recipients_title = QLabel("👥 Gestión de Destinatarios")
        recipients_title.setStyleSheet(
            "font-size:16px; font-weight:bold; color:#e6eef6; margin-bottom:2px;"
        )
        recipients_layout.addWidget(recipients_title)
        recipients_description = QLabel(
            "Administra los contactos que recibirán las notificaciones."
        )
        recipients_description.setStyleSheet("color:#99aab5;")
        recipients_description.setWordWrap(True)
        recipients_layout.addWidget(recipients_description)

        form_card = QFrame()
        form_card.setObjectName("recipientFormCard")
        form_card_layout = QVBoxLayout()
        form_card_layout.setContentsMargins(14, 12, 14, 14)
        form_card_layout.setSpacing(8)
        form_title = QLabel("Agregar destinatario")
        form_title.setStyleSheet("color:#e6eef6; font-weight:bold;")
        form_card_layout.addWidget(form_title)

        form_layout = QHBoxLayout()
        form_layout.setSpacing(10)
        self.rec_name = QLineEdit()
        self.rec_name.setPlaceholderText("Nombre")
        self.rec_name.setMinimumHeight(36)
        self.rec_email = QLineEdit()
        self.rec_email.setPlaceholderText("email@example.com")
        self.rec_email.setMinimumHeight(36)
        self.rec_phone = QLineEdit()
        self.rec_phone.setPlaceholderText("+1234567890")
        self.rec_phone.setMinimumHeight(36)
        self.add_recipient_btn = QPushButton("Agregar destinatario")
        self.add_recipient_btn.setObjectName("addRecipientButton")
        self.add_recipient_btn.setMinimumHeight(36)
        self.add_recipient_btn.clicked.connect(self.add_recipient_clicked)

        form_layout.addWidget(self.rec_name)
        form_layout.addWidget(self.rec_email)
        form_layout.addWidget(self.rec_phone)
        form_layout.addWidget(self.add_recipient_btn)
        form_layout.setStretch(0, 1)
        form_layout.setStretch(1, 1)
        form_layout.setStretch(2, 1)
        form_card_layout.addLayout(form_layout)
        form_card.setLayout(form_card_layout)
        recipients_layout.addWidget(form_card)

        self.recipients_table = QTableWidget()
        self.recipients_table.setObjectName("recipientsTable")
        self.recipients_table.setColumnCount(4)
        self.recipients_table.setHorizontalHeaderLabels(
            ["Usuario", "Email", "Teléfono", "Estado"]
        )
        self.recipients_table.setToolTip(
            "Haz doble clic en Usuario, Email o Teléfono para editar. "
            "Los cambios se guardan automáticamente."
        )
        header = self.recipients_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setMinimumSectionSize(110)
        self.recipients_table.verticalHeader().setVisible(False)
        self.recipients_table.verticalHeader().setDefaultSectionSize(38)
        self.recipients_table.setAlternatingRowColors(True)
        self.recipients_table.itemChanged.connect(self.update_recipient_from_table)
        recipients_layout.addWidget(self.recipients_table)

        remove_actions = QHBoxLayout()
        remove_actions.addStretch()
        remove_btn = QPushButton("Eliminar seleccionado")
        remove_btn.setObjectName("removeRecipientButton")
        remove_btn.setMinimumSize(180, 34)
        remove_btn.clicked.connect(self.remove_selected_recipient)
        remove_actions.addWidget(remove_btn)
        recipients_layout.addLayout(remove_actions)
        recipients_widget.setLayout(recipients_layout)

        # ── Página 3: Notificaciones ─────────────────────────────────────────
        notif_widget = QScrollArea()
        notif_widget.setObjectName("notificationsPage")
        notif_widget.setWidgetResizable(True)
        notif_widget.setFrameShape(QFrame.NoFrame)
        notif_content = QWidget()
        notif_content.setObjectName("notificationsContent")
        notif_layout = QVBoxLayout()
        notif_layout.setAlignment(Qt.AlignTop)
        notif_layout.setContentsMargins(18, 18, 18, 18)
        notif_layout.setSpacing(14)

        notif_title = QLabel("⚙ Configuración de Notificaciones")
        notif_title.setStyleSheet("font-size:16px; font-weight:bold; color:#e6eef6; margin-bottom:8px;")
        notif_layout.addWidget(notif_title)

        notif_desc = QLabel("Activa o desactiva los canales por los que se enviarán alertas de incidentes.")
        notif_desc.setStyleSheet("color:#99aab5; margin-bottom:16px;")
        notif_desc.setWordWrap(True)
        notif_layout.addWidget(notif_desc)

        # ── Telegram ──
        tg_group = QGroupBox("Telegram")
        tg_group.setObjectName("telegramNotificationGroup")
        tg_layout = QFormLayout()
        tg_layout.setContentsMargins(14, 20, 14, 14)
        tg_layout.setVerticalSpacing(12)
        self.telegram_mode_group, self.telegram_default_mode, self.telegram_manual_mode = (
            self._create_mode_selector("telegram")
        )
        tg_mode_row = QHBoxLayout()
        tg_mode_row.setSpacing(16)
        tg_mode_row.addWidget(self.telegram_default_mode)
        tg_mode_row.addWidget(self.telegram_manual_mode)
        tg_mode_row.addStretch()
        tg_layout.addRow("Modo:", tg_mode_row        )
        self.chk_telegram = QCheckBox("Activar notificaciones de Telegram")
        tg_layout.addRow(self.chk_telegram)
        self.telegram_manual_fields = QWidget()
        telegram_fields_layout = QFormLayout(self.telegram_manual_fields)
        self.telegram_chat_id_input = QLineEdit()
        self.telegram_chat_id_input.setMinimumHeight(32)
        self.telegram_chat_id_input.setPlaceholderText("ID de chat de Telegram")
        self.telegram_token_input = QLineEdit()
        self.telegram_token_input.setMinimumHeight(32)
        self.telegram_token_input.setEchoMode(QLineEdit.Password)
        self.telegram_token_input.setPlaceholderText("Token del bot")
        self.telegram_manual_fields.setStyleSheet(
            "QWidget{color:#e6eef6;} QLabel{color:#e6eef6;}"
            "QLineEdit{background-color:#161b22;color:#e6eef6;"
            "border:1px solid #46515c;border-radius:4px;padding:5px;}"
        )
        telegram_fields_layout.addRow("ID de chat:", self.telegram_chat_id_input)
        telegram_fields_layout.addRow("Token del bot:", self.telegram_token_input)
        tg_layout.addRow(self.telegram_manual_fields)
        tg_group.setLayout(tg_layout)
        notif_layout.addWidget(tg_group)

        # ── Gmail ──
        gm_group = QGroupBox("Gmail")
        gm_group.setObjectName("gmailNotificationGroup")
        gm_layout = QFormLayout()
        gm_layout.setContentsMargins(14, 20, 14, 14)
        gm_layout.setVerticalSpacing(12)
        self.gmail_mode_group, self.gmail_default_mode, self.gmail_manual_mode = (
            self._create_mode_selector("gmail")
        )
        gm_mode_row = QHBoxLayout()
        gm_mode_row.setSpacing(16)
        gm_mode_row.addWidget(self.gmail_default_mode)
        gm_mode_row.addWidget(self.gmail_manual_mode)
        gm_mode_row.addStretch()
        gm_layout.addRow("Modo:", gm_mode_row        )
        self.chk_gmail = QCheckBox("Activar notificaciones de Gmail")
        gm_layout.addRow(self.chk_gmail)
        self.gmail_manual_fields = QWidget()
        gmail_fields_layout = QFormLayout(self.gmail_manual_fields)
        self.gmail_sender_input = QLineEdit()
        self.gmail_sender_input.setMinimumHeight(32)
        self.gmail_sender_input.setPlaceholderText("Correo remitente de Gmail")
        self.gmail_app_password_input = QLineEdit()
        self.gmail_app_password_input.setMinimumHeight(32)
        self.gmail_app_password_input.setEchoMode(QLineEdit.Password)
        self.gmail_app_password_input.setPlaceholderText("Contraseña de aplicación")
        self.gmail_manual_fields.setStyleSheet(
            "QWidget{color:#e6eef6;} QLabel{color:#e6eef6;}"
            "QLineEdit{background-color:#161b22;color:#e6eef6;"
            "border:1px solid #46515c;border-radius:4px;padding:5px;}"
        )
        gmail_fields_layout.addRow("Correo:", self.gmail_sender_input)
        gmail_fields_layout.addRow("Contraseña de aplicación:", self.gmail_app_password_input)
        gm_layout.addRow(self.gmail_manual_fields)
        gm_group.setLayout(gm_layout)
        notif_layout.addWidget(gm_group)

        save_notif_btn = QPushButton("Guardar cambios")
        save_notif_btn.setObjectName("saveNotificationButton")
        save_notif_btn.setFixedSize(170, 32)
        save_notif_btn.clicked.connect(self.save_notifications_config)
        test_notif_btn = QPushButton("Probar notificaciones")
        test_notif_btn.setObjectName("testNotificationButton")
        test_notif_btn.setFixedSize(190, 32)
        test_notif_btn.clicked.connect(self.test_notifications)
        notif_buttons = QHBoxLayout()
        notif_buttons.setSpacing(8)
        notif_buttons.addStretch()
        notif_buttons.addWidget(save_notif_btn)
        notif_buttons.addWidget(test_notif_btn)
        notif_layout.addLayout(notif_buttons)
        notif_layout.addStretch()
        notif_content.setLayout(notif_layout)
        notif_widget.setWidget(notif_content)
        self._load_notifications_config()   # poblar campos al iniciar
        self.chk_telegram.toggled.connect(
            lambda enabled: self._on_notification_toggled("telegram", enabled)
        )
        self.chk_gmail.toggled.connect(
            lambda enabled: self._on_notification_toggled("gmail", enabled)
        )
        self.telegram_mode_group.buttonClicked.connect(
            lambda _button: self._on_notification_mode_selected("telegram")
        )
        self.gmail_mode_group.buttonClicked.connect(
            lambda _button: self._on_notification_mode_selected("gmail")
        )
        self._update_manual_notification_fields()

        # ── Página 4: Ajustes ────────────────────────────────────────────────
        settings_widget = QScrollArea()
        settings_widget.setObjectName("settingsPage")
        settings_widget.setWidgetResizable(True)
        settings_inner = QWidget()
        settings_inner.setObjectName("settingsContent")
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
            "QWidget#notificationsPage,QWidget#settingsContent{background-color:#0f1113;}"
            "QScrollArea#notificationsPage{background-color:#0f1113; border:none;}"
            "QScrollArea#notificationsPage QWidget#notificationsContent{background-color:#0f1113; color:#e6eef6;}"
            "QWidget#notificationsContent QLabel{color:#c9d1d9;}"
            "QWidget#notificationsContent QRadioButton,QWidget#notificationsContent QCheckBox{color:#e6eef6;}"
            "QWidget#notificationsContent QRadioButton::indicator{"
            "width:11px; height:11px; border:2px solid #f0f6fc; border-radius:7px;"
            "background-color:transparent;}"
            "QWidget#notificationsContent QRadioButton::indicator:checked{"
            "background-color:#ffffff; border:2px solid #ffffff;}"
            "QWidget#notificationsContent QRadioButton::indicator:hover{"
            "border-color:#58a6ff;}"
            "QWidget#notificationsContent QCheckBox::indicator{"
            "width:12px; height:12px; border:2px solid #f0f6fc; border-radius:3px;"
            "background-color:transparent;}"
            "QWidget#notificationsContent QCheckBox::indicator:checked{"
            "background-color:#ffffff; border:2px solid #ffffff;}"
            "QGroupBox#telegramNotificationGroup,QGroupBox#gmailNotificationGroup{"
            "background-color:#15191e; color:#e6eef6; font-weight:bold;"
            "border:1px solid #2e74b5; border-radius:6px; margin-top:16px;"
            "padding:18px 12px 12px 12px;}"
            "QGroupBox#telegramNotificationGroup::title,QGroupBox#gmailNotificationGroup::title{"
            "subcontrol-origin:margin; subcontrol-position:top left; left:10px;"
            "padding:1px 6px; background-color:#15191e; color:#e6eef6;}"
            "QWidget#notificationsContent QPushButton{"
            "background-color:#212b36; color:#e6eef6; border:1px solid #3b536b;"
            "border-radius:5px; padding:4px 10px;}"
            "QWidget#notificationsContent QPushButton:hover{background-color:#2b3b4d;}"
            "QWidget#notificationsContent QPushButton:pressed{background-color:#17212b;}"
            "QPushButton#saveNotificationButton{background-color:#238636; color:#ffffff;"
            "font-weight:bold; border:1px solid #2ea043; border-radius:5px; padding:4px 10px;}"
            "QPushButton#saveNotificationButton:hover{background-color:#2ea043;}"
            "QPushButton#testNotificationButton{background-color:#161b22; color:#e6eef6;"
            "border:1px solid #46515c; border-radius:5px; padding:4px 10px;}"
            "QPushButton#testNotificationButton:hover{background-color:#212b36; border-color:#58a6ff;}"
            "QWidget#recipientsPage{background-color:#0f1113; color:#e6eef6;}"
            "QFrame#recipientFormCard{background-color:#11161c; border:1px solid #30363d;"
            "border-radius:7px;}"
            "QWidget#recipientsPage QLineEdit{background-color:#0f141a; color:#e6eef6;"
            "border:1px solid #3b4652; border-radius:5px; padding:7px 9px;}"
            "QWidget#recipientsPage QLineEdit:focus{border:1px solid #58a6ff;}"
            "QPushButton#addRecipientButton{background-color:#238636; color:#ffffff;"
            "font-weight:bold; border:1px solid #2ea043; border-radius:5px; padding:6px 12px;}"
            "QPushButton#addRecipientButton:hover{background-color:#2ea043;}"
            "QPushButton#removeRecipientButton{background-color:transparent; color:#d0d7de;"
            "font-weight:normal; border:1px solid #46515c; border-radius:5px; padding:6px 14px;}"
            "QPushButton#removeRecipientButton:hover{background-color:#3a1f22; color:#ffb4ab;"
            "border-color:#a43a32;}"
            "QTableWidget#recipientsTable{background-color:#0f1113; alternate-background-color:#15191e;"
            "color:#dfe7ec; gridline-color:#252a30; border:1px solid #30363d;"
            "border-radius:6px; selection-background-color:#1f3a56; selection-color:#ffffff;"
            "alternate-background-color:#14191f;}"
            "QTableWidget#recipientsTable::item{padding:5px; border-bottom:1px solid #252a30;}"
            "QWidget#recipientsPage QHeaderView::section{background-color:#1b222b;"
            "color:#e6eef6; font-weight:bold; padding:9px 7px; border:none;"
            "border-bottom:1px solid #30363d;}"
            "QScrollArea#settingsPage{background-color:#0f1113; border:none;}"
            "QScrollArea#settingsPage QWidget#settingsContent{background-color:#0f1113;}"
            "QWidget#notificationsPage QLineEdit{background-color:#161b22; color:#dfe7ec; border:1px solid #30363d; border-radius:4px; padding:5px;}"
        )
        notif_widget.viewport().setStyleSheet("background-color:#0f1113;")
        settings_widget.viewport().setStyleSheet("background-color:#0f1113;")

        # El refresco ligero se mantiene independiente de la inferencia.
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(max(1, 1000 // self.target_fps))

        self._start_analysis_worker()

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
        db_path = self.fire_detector.db_path
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
                    if c == 2 and str(val).lower() == "fire":
                        val = "Incendio"
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
            self.fire_detector.add_recipient(
                name,
                email if email else None,
                phone if phone else None,
            )
            self.rec_name.clear()
            self.rec_email.clear()
            self.rec_phone.clear()
            QMessageBox.information(self, "Éxito", "Destinatario agregado")
            self.refresh_recipients()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo agregar: {e}")

    def refresh_recipients(self):
        """Cargar destinatarios desde la DB y mostrarlos en la tabla"""
        self.recipients_table.blockSignals(True)
        try:
            rows = self.fire_detector.list_recipients()
            self.recipients_table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                name_item = QTableWidgetItem(str(row.get('name') or ''))
                name_item.setData(Qt.UserRole, row.get("id"))
                name_item.setFlags(name_item.flags() | Qt.ItemIsEditable)
                self.recipients_table.setItem(r, 0, name_item)
                email_item = QTableWidgetItem(str(row.get('email') or ''))
                email_item.setData(Qt.UserRole, row.get("id"))
                self.recipients_table.setItem(r, 1, email_item)
                phone_item = QTableWidgetItem(str(row.get('phone') or ''))
                phone_item.setData(Qt.UserRole, row.get("id"))
                self.recipients_table.setItem(r, 2, phone_item)
                active = bool(row.get("active"))
                status_btn = QPushButton("ACTIVADO" if active else "DESACTIVADO")
                status_btn.setCheckable(True)
                status_btn.setChecked(active)
                status_btn.setStyleSheet(
                    "QPushButton{background:#922b21;color:white;font-weight:bold;"
                    "padding:5px 10px;border-radius:4px;}"
                    "QPushButton:checked{background:#148f77;}"
                )
                status_btn.clicked.connect(
                    lambda checked, recipient_id=row["id"]:
                        self.set_recipient_active(recipient_id, checked)
                )
                self.recipients_table.setCellWidget(r, 3, status_btn)
        except Exception as e:
            print(f"[UI] No se pudo cargar recipients: {e}")
        finally:
            self.recipients_table.blockSignals(False)

    def update_recipient_from_table(self, item):
        """Persist inline edits to a recipient's name, email, or phone."""
        columns = {0: "name", 1: "email", 2: "phone"}
        field = columns.get(item.column())
        recipient_id = item.data(Qt.UserRole)
        if field is None or recipient_id is None:
            return

        value = item.text().strip()
        if field == "name" and not value:
            QMessageBox.warning(self, "Destinatarios", "El nombre no puede quedar vacío.")
            self.refresh_recipients()
            return

        try:
            self.fire_detector.update_recipient(
                recipient_id,
                **{field: value or None},
            )
        except Exception as error:
            QMessageBox.critical(
                self,
                "Destinatarios",
                f"No se pudo guardar el cambio: {error}",
            )
            self.refresh_recipients()

    def set_recipient_active(self, recipient_id, active):
        """Enable or pause a recipient without deleting its saved entry."""
        try:
            self.fire_detector.set_recipient_active(recipient_id, active)
            self.refresh_recipients()
        except Exception as error:
            QMessageBox.critical(
                self,
                "Destinatarios",
                f"No se pudo actualizar el estado del destinatario: {error}",
            )

    def remove_selected_recipient(self):
        """Eliminar el destinatario seleccionado de la DB"""
        row = self.recipients_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Selecciona un destinatario")
            return
        name_item = self.recipients_table.item(row, 0)
        if not name_item:
            return
        rec_id = name_item.data(Qt.UserRole)
        if rec_id is None:
            QMessageBox.warning(self, "Error", "No se pudo identificar el destinatario seleccionado")
            return
        try:
            self.fire_detector.delete_recipient(rec_id)
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
            conn = sqlite3.connect(self.fire_detector.db_path)
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

        self.analysis_worker.stop()
        self._show_camera_grid()
        # Detener cámaras actuales
        for cam in self.cams:
            try:
                cam.stop()
            except Exception:
                pass

        # Recargar desde cameras_config.json
        self.cams = []
        for cam_cfg in CameraDialog.get_cameras()[:THREADING_CONFIG['max_cameras']]:
            try:
                cam = CamaraRTSP(
                    cam_cfg["url"],
                    cam_cfg["name"],
                    high_resolution_url=cam_cfg.get("high_resolution_url"),
                )
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
        self.camera_scores = [{"fire": 0.0, "accident": 0.0, "theft": 0.0} for _ in self.camera_scores]
        for score_labels in self.risk_labels:
            for key, label in score_labels.items():
                title = {"fire": "Fuego", "accident": "Choque", "theft": "Robo"}[key]
                label.setText(f"{title}\n0%")

        print(f"[UI] Cámaras recargadas: {len(self.cams)} activa(s)")
        self._start_analysis_worker()

    def _start_analysis_worker(self):
        self.analysis_worker = CameraAnalysisWorker(self.cams, self.fire_detector)
        self.analysis_worker.frame_analyzed.connect(self._on_frame_analyzed)
        self.analysis_worker.stats_updated.connect(self._on_analysis_stats)
        self.analysis_worker.module_error.connect(self._on_analysis_error)
        self.analysis_worker.module_warning.connect(self._on_analysis_warning)
        self.analysis_worker.start()

    def _show_single_camera(self, camera_index):
        if camera_index >= len(self.cams):
            return
        self._single_camera_index = camera_index
        self.resolution_selector.setVisible(True)
        cam = self.cams[camera_index]
        camera_name = getattr(cam, "name", f"Cámara {camera_index + 1}")
        if not getattr(cam, "high_resolution_url", ""):
            camera_name += " (sin mainstream; usando stream actual)"
        self.single_camera_title.setText(camera_name)
        self.single_view_label.setText("Conectando a mainstream...")
        self.camera_stack.setCurrentIndex(1)
        self._update_camera_stream_profiles()

    def _show_camera_grid(self):
        self._single_camera_index = None
        self.resolution_selector.setVisible(False)
        self.camera_stack.setCurrentIndex(0)
        self._update_camera_stream_profiles()

    def _update_camera_stream_profiles(self, *_):
        single_size = self.resolution_selector.currentData()
        for index, cam in enumerate(self.cams):
            if index == self._single_camera_index:
                cam.set_stream_profile("single", single_size)
            else:
                cam.set_stream_profile("mosaic", DETECTION_CONFIG["frame_resize"])

    def update(self):
        """Actualizar la vista de video sin ejecutar inferencias en la UI."""

        for i, cam in enumerate(self.cams):
            if i >= len(self.labels):
                break

            frame = cam.read()

            if frame is None:
                self.labels[i].setText("SIN VIDEO")
                self.labels[i].setStyleSheet("background-color: #1a1a1a; border: 2px solid #34495e; border-radius: 5px; color: #7f8c8d; font-weight: bold;")
                if self._single_camera_index == i:
                    self.single_view_label.setText("SIN VIDEO")
                continue

            display_frame = frame
            self.frame_count += 1
            self.total_frames_processed += 1

            rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)

            h, w, ch = rgb.shape
            img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)

            if self._single_camera_index == i:
                self.single_view_label.setPixmap(QPixmap.fromImage(img))
            elif self._single_camera_index is None:
                self.labels[i].setPixmap(QPixmap.fromImage(img))
            for key, label in self.risk_labels[i].items():
                title = {"fire": "Fuego", "accident": "Choque", "theft": "Robo"}[key]
                label.setText(f"{title}\n{self.camera_scores[i][key] * 100:.0f}%")
        
        # Actualizar barra de estado periódicamente.
        if self.frame_count % 30 == 0:
            active_cams = len([c for c in self.cams if c.frame is not None])
            self._sb_frames.setText(f"Frames: {self.total_frames_processed:,}")
            self._sb_mode.setText("Módulos: incendio/choque/robo")
            self._sb_fps.setText(f"Vista: {self.target_fps} FPS")
            self._sb_cams.setText(f"Camaras: {active_cams}/{len(self.cams)}")
            self._update_hw_labels()

    def _on_frame_analyzed(self, camera_index, scores):
        if camera_index >= len(self.camera_scores):
            return
        for module, score in scores.items():
            self.camera_scores[camera_index][module] = score

    def _on_analysis_stats(self, stats):
        self._sb_analysis.setText(
            f"IA: {stats['frames_per_second']}/{stats['target_frames_per_second']} frames/s, "
            f"{stats['inferences_per_second']}/{stats['target_base_inferences_per_second']} infer/s"
        )

    def _on_analysis_error(self, message):
        print(f"[UI] {message}")
        if message not in self._analysis_errors:
            self._analysis_errors.append(message)
        self.statusBtn.setText("⚠ ERROR DE ANÁLISIS · VER DETALLE")
        self.statusBtn.setStyleSheet(
            "QPushButton{background-color:#c0392b; color:white; font-weight:bold; "
            "padding:8px; border-radius:6px;} QPushButton:hover{background-color:#e74c3c}"
        )
        self.statusBtn.setToolTip("\n".join(self._analysis_errors))

    def _show_analysis_errors(self):
        messages = []
        if self._analysis_errors:
            messages.append("ERRORES:\n" + "\n\n".join(self._analysis_errors))
        if self._analysis_warnings:
            messages.append("AVISOS:\n" + "\n\n".join(self._analysis_warnings))
        if messages:
            QMessageBox.warning(
                self,
                "Detalles del error de análisis",
                "\n\n".join(messages),
            )

    def _on_analysis_warning(self, message):
        print(f"[UI] Aviso de análisis: {message}")
        if message not in self._analysis_warnings:
            self._analysis_warnings.append(message)
        if not self._analysis_errors:
            self.statusBtn.setText("⚠ ANÁLISIS PARCIAL · VER DETALLE")
            self.statusBtn.setStyleSheet(
                "QPushButton{background-color:#d68910; color:white; font-weight:bold; "
                "padding:8px; border-radius:6px;} QPushButton:hover{background-color:#f39c12}"
            )
        self.statusBtn.setToolTip("\n".join(self._analysis_warnings))

    def _create_mode_selector(self, channel):
        group = QButtonGroup(self)
        group.setExclusive(True)
        default_button = QRadioButton("Por defecto")
        manual_button = QRadioButton("Manual")
        for button in (default_button, manual_button):
            group.addButton(button)
        default_button.setProperty("profile", "default")
        manual_button.setProperty("profile", "manual")
        return group, default_button, manual_button

    def _selected_notification_mode(self, channel):
        button = (
            self.telegram_mode_group.checkedButton()
            if channel == "telegram"
            else self.gmail_mode_group.checkedButton()
        )
        return button.property("profile") if button else "default"

    def _read_notification_config(self):
        cfg_path = self.fire_detector.notifications_config_path
        config = {}
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as file:
                config = unprotect_notification_secrets(json.load(file))
        for channel_name, secret_key in (
            ("telegram", "token"),
            ("gmail", "app_password"),
        ):
            channel = config.setdefault(channel_name, {})
            legacy_secret = channel.pop(secret_key, None)
            if legacy_secret:
                channel["enabled"] = False
                channel["mode"] = "default"
        gmail = config.setdefault("gmail", {})
        legacy_sender = gmail.pop("sender", None)
        if legacy_sender:
            gmail["enabled"] = False
            gmail["mode"] = "default"
        config.setdefault("telegram", {}).setdefault("profiles", {}).setdefault(
            "default", {}
        )
        return config

    def _write_notification_config(self, config):
        cfg_path = self.fire_detector.notifications_config_path
        protected_config = protect_notification_secrets(config)
        with open(cfg_path, "w", encoding="utf-8") as file:
            json.dump(protected_config, file, indent=2, ensure_ascii=False)

    def _on_notification_toggled(self, channel, enabled):
        if enabled:
            if not self._save_notifications_config():
                button = self.chk_telegram if channel == "telegram" else self.chk_gmail
                button.blockSignals(True)
                button.setChecked(False)
                button.blockSignals(False)
            return
        try:
            config = self._read_notification_config()
            channel_config = config.setdefault(channel, {})
            channel_config["enabled"] = False
            self._write_notification_config(config)
        except Exception as error:
            QMessageBox.critical(
                self,
                "Notificaciones",
                f"No se pudo guardar el estado de notificaciones: {error}",
            )

    def _on_notification_mode_selected(self, channel):
        try:
            config = self._read_notification_config()
            channel_config = config.setdefault(channel, {})
            self._load_manual_notification_profile(channel, channel_config)
            self._update_manual_notification_fields()
        except Exception as error:
            QMessageBox.critical(
                self,
                "Notificaciones",
                f"No se pudo cambiar el modo: {error}",
            )

    def _update_manual_notification_fields(self):
        self.telegram_manual_fields.setVisible(self.telegram_manual_mode.isChecked())
        self.gmail_manual_fields.setVisible(self.gmail_manual_mode.isChecked())

    def _load_manual_notification_profile(self, channel, channel_config):
        profile = channel_config.get("profiles", {}).get("manual", {})
        if channel == "telegram":
            self.telegram_chat_id_input.setText(profile.get("chat_id", ""))
            self.telegram_token_input.setText(profile.get("token", ""))
        else:
            self.gmail_sender_input.setText(profile.get("sender", ""))
            self.gmail_app_password_input.setText(profile.get("app_password", ""))

    def _save_manual_notification_profiles(self, cfg):
        telegram = cfg.setdefault("telegram", {})
        telegram_profiles = telegram.setdefault("profiles", {})
        telegram_profile = telegram_profiles.setdefault("manual", {})
        telegram_profile["chat_id"] = self.telegram_chat_id_input.text().strip()
        telegram_profile["token"] = self.telegram_token_input.text().strip()

        gmail = cfg.setdefault("gmail", {})
        gmail_profiles = gmail.setdefault("profiles", {})
        gmail_profile = gmail_profiles.setdefault("manual", {})
        gmail_profile["sender"] = self.gmail_sender_input.text().strip()
        gmail_profile["app_password"] = self.gmail_app_password_input.text().strip()

    def _prompt_default_notification_credentials(self, channel):
        if channel == "telegram":
            token, accepted = QInputDialog.getText(
                self,
                "Configurar Telegram por defecto",
                "Token del bot (se guardará cifrado con DPAPI):",
                QLineEdit.Password,
            )
            if not accepted or not token.strip():
                return None
            return {"token": token.strip()}

        sender, accepted = QInputDialog.getText(
            self,
            "Configurar Gmail por defecto",
            "Correo remitente (se guardará con DPAPI):",
        )
        if not accepted or not sender.strip():
            return None
        app_password, accepted = QInputDialog.getText(
            self,
            "Configurar Gmail por defecto",
            "Contraseña de aplicación (se guardará cifrada con DPAPI):",
            QLineEdit.Password,
        )
        if not accepted or not app_password.strip():
            return None
        return {"sender": sender.strip(), "app_password": app_password.strip()}

    def _ensure_notification_profile_credentials(self, cfg, channel, mode):
        profile = cfg.setdefault(channel, {}).setdefault("profiles", {}).setdefault(
            mode, {}
        )
        if channel == "telegram":
            required = ("token",) if mode == "default" else ("chat_id", "token")
        else:
            required = ("sender", "app_password")

        if not all(profile.get(key) for key in required):
            if mode != "default":
                message = (
                    "Completa el ID de chat y el token de Telegram antes de activar el canal."
                    if channel == "telegram"
                    else "Completa el correo y la contraseña de aplicación de Gmail antes de activar el canal."
                )
                QMessageBox.warning(self, "Configuración incompleta", message)
                return False
            credentials = self._prompt_default_notification_credentials(channel)
            if credentials is None:
                return False
            profile.update(credentials)

        return True

    # ── Notificaciones ────────────────────────────────────────────────────────
    def _load_notifications_config(self):
        """Load channel mode and enabled state without displaying credentials."""
        try:
            cfg = self._read_notification_config()
            tg = cfg.get("telegram", {})
            (self.telegram_default_mode if tg.get("mode", "default") == "default"
             else self.telegram_manual_mode).setChecked(True)
            self.chk_telegram.setChecked(bool(tg.get("enabled", False)))
            self._load_manual_notification_profile("telegram", tg)

            gm = cfg.get("gmail", {})
            (self.gmail_default_mode if gm.get("mode", "default") == "default"
             else self.gmail_manual_mode).setChecked(True)
            self.chk_gmail.setChecked(bool(gm.get("enabled", False)))
            self._load_manual_notification_profile("gmail", gm)
            self._update_manual_notification_fields()
        except Exception as e:
            print(f"[UI] Error cargando notificaciones: {e}")

    def save_notifications_config(self):
        """Guardar configuración de notificaciones al JSON."""
        if self._save_notifications_config():
            QMessageBox.information(
                self,
                "Guardado",
                "Configuración de notificaciones guardada correctamente.",
            )

    def _save_notifications_config(self) -> bool:
        try:
            cfg = self._read_notification_config()
            telegram = cfg.get("telegram", {})
            telegram.pop("chat_ids", None)
            telegram.pop("chat_id", None)
            telegram["mode"] = self._selected_notification_mode("telegram")
            telegram["enabled"] = self.chk_telegram.isChecked()
            cfg["telegram"] = telegram

            gmail = cfg.get("gmail", {})
            gmail.pop("to_emails", None)
            gmail["mode"] = self._selected_notification_mode("gmail")
            gmail["enabled"] = self.chk_gmail.isChecked()
            cfg["gmail"] = gmail

            self._save_manual_notification_profiles(cfg)
            if self.chk_telegram.isChecked():
                if not self._ensure_notification_profile_credentials(
                    cfg,
                    "telegram",
                    self._selected_notification_mode("telegram"),
                ):
                    return False
            if self.chk_gmail.isChecked():
                if not self._ensure_notification_profile_credentials(
                    cfg,
                    "gmail",
                    self._selected_notification_mode("gmail"),
                ):
                    return False

            self._write_notification_config(cfg)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar: {e}")
            return False

    def test_notifications(self):
        """Enable the selected profiles, save them securely, and send a test."""
        previous_states = (
            self.chk_telegram.isChecked(),
            self.chk_gmail.isChecked(),
        )
        for button in (self.chk_telegram, self.chk_gmail):
            button.blockSignals(True)
            button.setChecked(True)
            button.blockSignals(False)

        if not self._save_notifications_config():
            for button, checked in zip(
                (self.chk_telegram, self.chk_gmail), previous_states
            ):
                button.blockSignals(True)
                button.setChecked(checked)
                button.blockSignals(False)
            return

        results = self.fire_detector.send_test_notifications()
        enabled_results = {
            "Telegram": results["telegram"],
            "Correo": results["gmail"],
        }
        active_results = {
            channel: sent
            for channel, sent in enabled_results.items()
            if sent is not None
        }
        if not active_results:
            QMessageBox.warning(
                self,
                "Canales desactivados",
                "Activa Telegram o Gmail y configura sus destinatarios antes de probar.",
            )
            return

        errors = getattr(self.fire_detector, "last_notification_errors", {})
        status = "\n".join(
            (
                f"{channel}: enviado"
                if sent
                else f"{channel}: no se pudo enviar"
                + (f" — {errors[channel]}" if channel in errors else "")
            )
            for channel, sent in active_results.items()
        )
        if all(active_results.values()):
            QMessageBox.information(self, "Prueba de notificaciones", status)
        else:
            QMessageBox.warning(self, "Prueba de notificaciones", status)

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
            cfg_path = user_data_path("cameras_config.json")
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

    def closeEvent(self, event):
        self.timer.stop()
        self.analysis_worker.stop(timeout=10)
        for camera in self.cams:
            camera.stop()
        event.accept()
