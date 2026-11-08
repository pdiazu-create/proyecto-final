"""Persistencia JSON con escrituras atómicas y nombres de archivo restringidos.

Un único estado.json contiene una operación académica completa. Esto elimina
la inconsistencia del prototipo anterior al escribir planes y actividades
por separado. No es una base de datos de producción ni admite varios procesos.
"""
import json
import os
import tempfile
from pathlib import Path


class ErrorDatos(RuntimeError):
    """No es seguro continuar sin intervención: datos incompletos o dañados."""


class AlmacenJSON:
    def __init__(self, carpeta):
        self.carpeta = Path(carpeta)
        self.carpeta.mkdir(parents=True, exist_ok=True)

    def _ruta(self, nombre):
        if not isinstance(nombre, str) or not nombre.endswith('.json') or '/' in nombre or '\\' in nombre or name_is_unsafe(nombre):
            raise ValueError('Nombre de archivo JSON inválido.')
        return self.carpeta / nombre

    def existe(self, nombre):
        return self._ruta(nombre).exists()

    def leer(self, nombre, valor_inicial=None):
        ruta = self._ruta(nombre)
        if not ruta.exists():
            return valor_inicial
        try:
            with ruta.open('r', encoding='utf-8') as archivo:
                return json.load(archivo)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ErrorDatos(f'No se pudo leer {nombre}; conserva el archivo y revisa los datos.') from exc

    def guardar(self, nombre, datos):
        ruta = self._ruta(nombre)
        temporal = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.carpeta,
                                             suffix='.tmp', delete=False) as archivo:
                temporal = archivo.name
                json.dump(datos, archivo, ensure_ascii=False, indent=2, allow_nan=False)
                archivo.write('\n')
                archivo.flush()
                os.fsync(archivo.fileno())
            os.replace(temporal, ruta)
        finally:
            if temporal and os.path.exists(temporal):
                os.unlink(temporal)


def name_is_unsafe(nombre):
    return nombre.startswith('.') or '..' in nombre or not all(c.isalnum() or c in '._-' for c in nombre)
