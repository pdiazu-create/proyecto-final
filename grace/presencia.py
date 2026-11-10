"""Latidos temporales para proponer asistencia; no sustituyen el registro docente."""
from datetime import datetime
import threading
import time

from .cuentas import ErrorAcceso
from .servicio import ErrorValidacion


VENTANA_PRESENCIA_SEGUNDOS = 120


class RegistroPresencia:
    def __init__(self, reloj=None):
        self.reloj = reloj or time.monotonic
        self.lock = threading.Lock()
        self._latidos = {}

    def registrar(self, datos, usuario, cursos):
        if usuario['rol'] != 'estudiante':
            raise ErrorAcceso(403, 'La presencia solo se registra desde una cuenta de estudiante.')
        if not isinstance(datos, dict) or set(datos) != {'curso_id', 'sesion_id'}:
            raise ErrorValidacion('Indica una sesión válida.')
        if not isinstance(datos['curso_id'], str) or not datos['curso_id']:
            raise ErrorValidacion('Indica un curso válido.')
        if type(datos['sesion_id']) not in (str, int):
            raise ErrorValidacion('Indica una sesión válida.')
        curso = next((c for c in cursos.listar(usuario)['cursos'] if c['id'] == datos['curso_id']), None)
        sesion = next((s for s in curso['sesiones']
                       if str(s['id']) == str(datos['sesion_id'])), None) if curso else None
        if sesion is None or not sesion['publicada']:
            raise ErrorAcceso(404, 'Sesión publicada no disponible.')
        if sesion['fecha'] != datetime.now().astimezone().date().isoformat():
            raise ErrorAcceso(409, 'La presencia solo se registra el día de la sesión.')
        clave = (curso['id'], sesion['id'], usuario['estudiante_id'])
        ahora = self.reloj()
        with self.lock:
            self._latidos[clave] = (ahora, datetime.now().astimezone().isoformat(timespec='seconds'))
            self._depurar(ahora)
        return {'registrada': True}

    def activos(self, curso_id, sesion_id, estudiantes):
        ahora = self.reloj()
        resultado = {}
        with self.lock:
            self._depurar(ahora)
            for estudiante_id in estudiantes:
                fila = self._latidos.get((curso_id, sesion_id, estudiante_id))
                if fila is not None:
                    resultado[estudiante_id] = fila[1]
        return resultado

    def _depurar(self, ahora):
        vencidos = [clave for clave, (latido, _) in self._latidos.items()
                    if ahora - latido > VENTANA_PRESENCIA_SEGUNDOS]
        for clave in vencidos:
            del self._latidos[clave]
