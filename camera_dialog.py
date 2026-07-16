"""
Diálogo para gestionar fuentes de video: RTSP, cámara local y archivo de video.
Semana 5 — Módulo de Captura de Video
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QCheckBox, QComboBox, QFileDialog, QSpinBox, QStackedWidget, QWidget,
)
from PySide6.QtCore import Qt
import json
import os

CAMERAS_FILE = "cameras_config.json"

# Tipos de fuente de video
TYPE_RTSP  = "RTSP / Red"
TYPE_LOCAL = "Cámara Local"
TYPE_FILE  = "Archivo de Video"


class CameraDialog(QDialog):
    """Diálogo para gestionar fuentes de video (RTSP, local y archivo)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestionar Fuentes de Video")
        self.setMinimumWidth(900)
        self.setMinimumHeight(460)
        self.cameras = self.load_cameras()
        self.init_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def init_ui(self):
        layout = QVBoxLayout()

        # ── Tabla ──────────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Nombre", "Tipo", "URL / Fuente", "Acciones"])
        self.table.setColumnWidth(0, 130)
        self.table.setColumnWidth(1, 110)
        self.table.setColumnWidth(2, 380)
        self.table.setColumnWidth(3, 120)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.refresh_table()
        layout.addWidget(self.table)

        # ── Formulario de nueva fuente ─────────────────────────────────────
        form = QHBoxLayout()

        # Nombre
        form.addWidget(QLabel("Nombre:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("ej: Cámara Entrada")
        self.name_input.setFixedWidth(130)
        form.addWidget(self.name_input)

        # Tipo de fuente
        form.addWidget(QLabel("Tipo:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems([TYPE_RTSP, TYPE_LOCAL, TYPE_FILE])
        self.type_combo.setFixedWidth(130)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        form.addWidget(self.type_combo)

        # ── Panel dinámico según tipo ─────────────────────────────────────
        self.url_stack = QStackedWidget()

        # Panel RTSP
        rtsp_w = QWidget()
        rtsp_l = QHBoxLayout(rtsp_w); rtsp_l.setContentsMargins(0,0,0,0)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("rtsp://usuario:contraseña@192.168.1.100:554/stream")
        rtsp_l.addWidget(self.url_input)

        # Panel Cámara Local
        local_w = QWidget()
        local_l = QHBoxLayout(local_w); local_l.setContentsMargins(0,0,0,0)
        local_l.addWidget(QLabel("Índice:"))
        self.local_spin = QSpinBox()
        self.local_spin.setRange(0, 9)
        self.local_spin.setValue(0)
        self.local_spin.setToolTip("0 = primera webcam, 1 = segunda, …")
        local_l.addWidget(self.local_spin)
        local_l.addStretch()

        # Panel Archivo de Video
        file_w = QWidget()
        file_l = QHBoxLayout(file_w); file_l.setContentsMargins(0,0,0,0)
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("Ruta al archivo (.mp4, .avi, .mkv, …)")
        browse_btn = QPushButton("Examinar…")
        browse_btn.setFixedWidth(90)
        browse_btn.clicked.connect(self._browse_file)
        file_l.addWidget(self.file_input)
        file_l.addWidget(browse_btn)

        self.url_stack.addWidget(rtsp_w)   # 0
        self.url_stack.addWidget(local_w)  # 1
        self.url_stack.addWidget(file_w)   # 2
        form.addWidget(self.url_stack, 1)

        # Detecciones
        self.chk_fire     = QCheckBox("🔥 Incendios");  self.chk_fire.setChecked(True)
        self.chk_theft    = QCheckBox("🚨 Robos");       self.chk_theft.setChecked(True)
        self.chk_accident = QCheckBox("🚗 Choques");     self.chk_accident.setChecked(True)
        for chk in (self.chk_fire, self.chk_theft, self.chk_accident):
            form.addWidget(chk)

        add_btn = QPushButton("➕  Agregar")
        add_btn.setStyleSheet("background:#2980b9; color:white; font-weight:bold; padding:4px 10px;")
        add_btn.clicked.connect(self.add_camera)
        form.addWidget(add_btn)

        layout.addLayout(form)

        # ── Botones inferiores ─────────────────────────────────────────────
        btn_row = QHBoxLayout()
        save_btn = QPushButton("💾  Guardar Cambios")
        save_btn.setStyleSheet("background:#2ecc71; color:white; font-weight:bold; padding:6px;")
        save_btn.clicked.connect(self.save_cameras)
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_type_changed(self, idx):
        self.url_stack.setCurrentIndex(idx)

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo de video", "",
            "Video (*.mp4 *.avi *.mkv *.mov *.flv *.ts *.wmv);;Todos (*)"
        )
        if path:
            self.file_input.setText(path)

    def _get_url(self) -> str:
        """Obtener la URL/ruta según el tipo seleccionado."""
        idx = self.type_combo.currentIndex()
        if idx == 0:   # RTSP
            return self.url_input.text().strip()
        elif idx == 1:  # Local
            return f"local:{self.local_spin.value()}"
        else:           # Archivo
            return self.file_input.text().strip()

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def refresh_table(self):
        """Actualizar tabla con fuentes registradas."""
        TYPE_LABELS = {
            "rtsp":  "RTSP/Red",
            "local": "Cámara Local",
            "file":  "Archivo",
        }
        self.table.setRowCount(len(self.cameras))
        for row, cam in enumerate(self.cameras):
            tipo = TYPE_LABELS.get(cam.get("source_type", "rtsp"), "RTSP/Red")
            self.table.setItem(row, 0, QTableWidgetItem(cam.get("name", "")))
            self.table.setItem(row, 1, QTableWidgetItem(tipo))
            self.table.setItem(row, 2, QTableWidgetItem(cam.get("url", "")))
            del_btn = QPushButton("Eliminar")
            del_btn.clicked.connect(lambda checked, r=row: self.delete_camera(r))
            del_btn.setStyleSheet("background:#e74c3c; color:white;")
            self.table.setCellWidget(row, 3, del_btn)

    def add_camera(self):
        name = self.name_input.text().strip()
        url  = self._get_url()
        tipo_idx = self.type_combo.currentIndex()
        tipo_key = ["rtsp", "local", "file"][tipo_idx]

        if not name:
            QMessageBox.warning(self, "Error", "Ingresa un nombre para la fuente.")
            return
        if not url:
            QMessageBox.warning(self, "Error", "Ingresa la URL / ruta / índice.")
            return

        # Validaciones por tipo
        if tipo_idx == 0 and not url.startswith(("rtsp://", "rtsps://", "http://", "https://", "rtmp://")):
            QMessageBox.warning(self, "Error", "La URL RTSP debe comenzar con rtsp://, http:// o rtmp://")
            return
        if tipo_idx == 2 and not os.path.exists(url):
            QMessageBox.warning(self, "Error", f"No se encontró el archivo:\n{url}")
            return

        self.cameras.append({
            "name":             name,
            "url":              url,
            "source_type":      tipo_key,
            "detect_fire":      self.chk_fire.isChecked(),
            "detect_theft":     self.chk_theft.isChecked(),
            "detect_accident":  self.chk_accident.isChecked(),
        })
        self.name_input.clear()
        self.url_input.clear()
        self.file_input.clear()
        self.local_spin.setValue(0)
        self.refresh_table()
        QMessageBox.information(self, "Éxito", "Fuente agregada. Haz clic en 'Guardar Cambios'.")

    def delete_camera(self, row):
        name = self.cameras[row]['name']
        if QMessageBox.question(self, "Confirmar", f"¿Eliminar '{name}'?") == QMessageBox.Yes:
            self.cameras.pop(row)
            self.refresh_table()

    def save_cameras(self):
        try:
            with open(CAMERAS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cameras, f, indent=2, ensure_ascii=False)
            QMessageBox.information(
                self, "Éxito",
                f"Configuración guardada en {CAMERAS_FILE}\n"
                f"Total de fuentes: {len(self.cameras)}\n\n"
                "Al cerrar este diálogo los cambios se aplicarán automáticamente."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar: {e}")

    # ── Carga / acceso estático ───────────────────────────────────────────────

    @staticmethod
    def load_cameras():
        """Cargar fuentes desde archivo, normalizando entradas antiguas."""
        if not os.path.exists(CAMERAS_FILE):
            return []
        try:
            with open(CAMERAS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            normalized = []
            for cam in data:
                url = cam.get('url', '')
                # Inferir source_type si falta (compatibilidad con config antiguo)
                if 'source_type' not in cam:
                    if url.isdigit() or url.startswith(("local:", "cam:")):
                        stype = "local"
                    elif os.path.splitext(url)[1].lower() in (".mp4", ".avi", ".mkv", ".mov", ".flv", ".ts", ".wmv"):
                        stype = "file"
                    else:
                        stype = "rtsp"
                else:
                    stype = cam['source_type']
                normalized.append({
                    'name':            cam.get('name', ''),
                    'url':             url,
                    'source_type':     stype,
                    'detect_fire':     cam.get('detect_fire',     True),
                    'detect_theft':    cam.get('detect_theft',    True),
                    'detect_accident': cam.get('detect_accident', True),
                })
            return normalized
        except Exception:
            return []

    @staticmethod
    def get_cameras():
        """Obtener lista de fuentes de video configuradas."""
        return CameraDialog.load_cameras()

