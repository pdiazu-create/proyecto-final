"""Arranque local sin consola. Ninguna clave se persiste."""
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import time
from urllib.request import urlopen

BASE = Path(__file__).resolve().parent
URL = 'http://127.0.0.1:8000'
MARCADOR = BASE / '.grace_proceso.json'


def salud():
    try:
        with urlopen(URL + '/api/salud', timeout=1) as respuesta:
            datos = json.load(respuesta)
        return datos if isinstance(datos, dict) and datos.get('estado') == 'ok' else None
    except Exception:
        return None


def iniciar(clave):
    if salud():
        return 'existente'
    if not clave.strip():
        raise ValueError('Introduce la clave de Gemini en esta ventana.')
    entorno = os.environ.copy()
    token = secrets.token_hex(16)
    entorno.update(GRACE_IA='api', GRACE_IA_PROVEEDOR='gemini',
                   GRACE_IA_MODEL='gemini-3.5-flash-lite', GRACE_IA_TIMEOUT='30',
                   GRACE_IA_KEY=clave.strip(), GRACE_INSTANCIA=token)
    ejecutable = Path(sys.executable)
    sin_consola = ejecutable.with_name('pythonw.exe')
    if os.name == 'nt' and sin_consola.exists():
        ejecutable = sin_consola
    opciones = {}
    if os.name == 'nt':
        opciones['creationflags'] = subprocess.CREATE_NO_WINDOW
    proceso = subprocess.Popen([str(ejecutable), str(BASE / 'app.py')],
                               cwd=str(BASE), env=entorno, stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               **opciones)
    del entorno
    limite = time.monotonic() + 12
    while time.monotonic() < limite:
        if proceso.poll() is not None:
            raise ValueError('Grace no pudo iniciar. Comprueba que el puerto 8000 esté libre.')
        estado = salud()
        if estado and estado.get('instancia') == token and estado.get('proceso') == proceso.pid:
            MARCADOR.write_text(json.dumps({'proceso': proceso.pid, 'instancia': token}),
                               encoding='utf-8')
            return 'iniciado'
        time.sleep(0.15)
    proceso.terminate()
    raise ValueError('No se pudo confirmar el arranque de Grace.')


def detener():
    estado = salud()
    if not estado:
        return 'Grace ya está detenida.'
    try:
        marcador = json.loads(MARCADOR.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise ValueError('Esta instancia se inició desde una terminal. Deténla allí con Ctrl+C.') from None
    pid = marcador.get('proceso')
    token = marcador.get('instancia')
    if (not isinstance(pid, int) or pid <= 0 or not token or
            estado.get('proceso') != pid or estado.get('instancia') != token):
        raise ValueError('No se identificó una instancia iniciada por este acceso directo.') from None
    os.kill(pid, signal.SIGTERM)
    MARCADOR.unlink(missing_ok=True)
    return 'Grace se ha detenido.'
