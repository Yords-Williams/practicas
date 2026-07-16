# 📹 Guía de Configuración de Cámaras RTSP

## Opciones para Agregar Cámaras

### Opción 1: Interfaz Gráfica (Recomendado)

1. Abre la aplicación CCTV AI PRO
2. Click en el botón **"📹 Gestionar Cámaras"** en la esquina superior derecha
3. Completa los campos:
   - **Nombre**: Nombre descriptivo de la cámara (ej: "Entrada", "Parqueo")
   - **URL**: URL RTSP/HTTP/HTTPS de tu cámara
4. Click en **"Agregar Cámara"**
5. Repite para más cámaras
6. Click en **"Guardar Cambios"**
7. Reinicia la aplicación

### Opción 2: Archivo JSON

1. Edita el archivo `cameras_config.json` en la carpeta raíz:
```json
[
  {
    "name": "Cámara Entrada",
    "url": "rtsp://usuario:contraseña@192.168.1.100:554/stream"
  },
  {
    "name": "Cámara Parqueo",
    "url": "rtsp://usuario:contraseña@192.168.1.101:554/stream"
  }
]
```

2. Guarda el archivo
3. Reinicia la aplicación

## Formatos de URL Soportados

### RTSP (protocolo más común)
```
rtsp://usuario:contraseña@192.168.1.100:554/stream
rtsp://admin:12345@192.168.1.100/live
```

### HTTP
```
http://192.168.1.100:8080/stream
http://admin:pass@192.168.1.100/video
```

### HTTPS
```
https://192.168.1.100:443/stream
https://admin:pass@192.168.1.100/live
```

## Cómo Encontrar la URL de tu Cámara

### Cámaras Hikvision/Dahua
```
rtsp://usuario:contraseña@IP:554/stream1
# Puerto por defecto: 554
# Usuario por defecto: admin
# Contraseña por defecto: 12345
```

### Cámaras IP Genéricas
1. Accede a la cámara en el navegador: `http://IP-CAMARA`
2. Busca en configuración → red → RTSP
3. Copia la URL RTSP proporcionada

### Cámaras Conectadas por Cable USB (Webcam)
```
Usa: videoga.mp4 (para archivos locales)
O dispositivo: 0 (para webcam integrada)
```

## Parámetros Comunes

| Parámetro | Descripción | Ejemplo |
|-----------|-------------|---------|
| Usuario | Credencial de acceso | `admin` |
| Contraseña | Credencial de acceso | `12345` |
| IP | Dirección de la cámara | `192.168.1.100` |
| Puerto | Puerto RTSP (típicamente 554) | `554` |
| Stream | Tipo de stream | `stream`, `stream1`, `ch0`, `main` |

## Troubleshooting

### Error: "Cámara no conectada"
- Verifica que la cámara esté conectada a la red
- Verifica la URL (especialmente usuario/contraseña)
- Comprueba el firewall de la cámara
- Intenta hacer ping a la IP: `ping 192.168.1.100`

### Error: "Timeout"
- Comprueba conexión de red
- Verifica que el puerto 554 (u otro) esté abierto
- Aumenta el timeout en `config.py` si es necesario

### Error: "Credenciales inválidas"
- Verifica usuario y contraseña
- Resetea la cámara a valores de fábrica si es necesario
- Consulta el manual de tu cámara

## Ejemplos de Cámaras Populares

### Dahua (DVR/NVR)
```
rtsp://admin:admin@192.168.1.100:554/stream1
```

### Hikvision
```
rtsp://admin:12345@192.168.1.100:554/h264/ch1/main/av_stream
```

### Reolink
```
rtsp://admin:password@192.168.1.100/h264Preview_01_main
```

### TP-Link Tapo
```
rtsp://admin:password@192.168.1.100:554/stream1
```

### Generic/Onvif
```
rtsp://usuario:contraseña@192.168.1.100:554/media/video1
```

## Configuración Avanzada

Para cambiar parámetros de captura, edita `config.py`:

```python
# Parámetros de detección
DETECTION_CONFIG = {
    "confidence_threshold": 0.4,  # 0-1: más alto = más exacto
    "device": "auto",              # "auto", "cpu", o "0" para GPU
    "fps_limit": 30,               # Frames por segundo
    "frame_resize": (450, 280),    # Resolución de captura
}
```

---
**Nota:** La aplicación soporta hasta 6 cámaras simultáneamente por rendimiento.
