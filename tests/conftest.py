"""
conftest.py — agrega el directorio raíz al path de Python para que
los tests en esta carpeta puedan importar los módulos del proyecto.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
