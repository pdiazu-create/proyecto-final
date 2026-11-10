"""Catálogo de DEMOSTRACIÓN (no oficial UAM) y recursos privados de perfil."""
import base64
import binascii
from copy import deepcopy
import re
import struct
from threading import RLock
import zlib

from .archivos import AlmacenJSON, ErrorDatos
from .servicio import ErrorValidacion


CATALOGO = (
    ('ingenieria', 'Ingeniería', (('sistemas', 'Ingeniería en Sistemas'),
                                 ('civil', 'Ingeniería Civil'),
                                 ('industrial', 'Ingeniería Industrial'))),
    ('negocios', 'Negocios', (('administracion', 'Administración'), ('marketing', 'Marketing'))),
    ('salud', 'Salud', (('medicina', 'Medicina'), ('psicologia', 'Psicología'))),
)
PREFIJO = 'data:image/png;base64,'
MAX_BYTES = 1024 * 1024


def catalogo():
    return {'facultades': [{'id': fid, 'nombre': nombre,
            'carreras': [{'id': cid, 'nombre': carrera} for cid, carrera in carreras]}
            for fid, nombre, carreras in CATALOGO]}


def nombres(facultad_id, carrera_id):
    if isinstance(facultad_id, str) and isinstance(carrera_id, str):
        if facultad_id == carrera_id == '':
            return {'facultad': '', 'carrera': ''}
        for fid, facultad, carreras in CATALOGO:
            for cid, carrera in carreras:
                if (fid, cid) == (facultad_id, carrera_id):
                    return {'facultad': facultad, 'carrera': carrera}
    raise ErrorValidacion('Elige una carrera de la facultad seleccionada.')


def ids_canonicos(cuenta):
    for fid, facultad, carreras in CATALOGO:
        for cid, carrera in carreras:
            if (cuenta.get('facultad'), cuenta.get('carrera')) == (facultad, carrera):
                return {'facultad_id': fid, 'carrera_id': cid}
    return {'facultad_id': '', 'carrera_id': ''}


def validar_png(imagen, tipo):
    """Admite solo PNG RGB/RGBA de 8 bits con un flujo zlib acotado."""
    if not isinstance(imagen, str) or not imagen.startswith(PREFIJO):
        raise ErrorValidacion('Utiliza una imagen PNG en formato data URL.')
    texto = imagen[len(PREFIJO):]
    if len(texto) > 4 * ((MAX_BYTES + 2) // 3):
        raise ErrorValidacion('Imagen demasiado grande.')
    try:
        png = base64.b64decode(texto, validate=True)
    except (ValueError, binascii.Error):
        raise ErrorValidacion('Base64 inválido.') from None
    if len(png) > MAX_BYTES or not png.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ErrorValidacion('PNG inválido.')
    posicion, cabecera, terminado, cerrado = 8, None, False, False
    comprimido = bytearray()
    hubo_idat = False
    while posicion < len(png):
        if posicion + 12 > len(png):
            raise ErrorValidacion('PNG truncado.')
        largo, chunk = struct.unpack('>I4s', png[posicion:posicion + 8])
        fin = posicion + 12 + largo
        if fin > len(png) or not re.fullmatch(b'[A-Za-z]{4}', chunk) or chunk[2] & 32:
            raise ErrorValidacion('Chunk PNG inválido.')
        contenido = png[posicion + 8:fin - 4]
        crc = struct.unpack('>I', png[fin - 4:fin])[0]
        if zlib.crc32(chunk + contenido) != crc:
            raise ErrorValidacion('CRC PNG inválido.')
        if cabecera is None and chunk != b'IHDR':
            raise ErrorValidacion('Falta IHDR.')
        if chunk == b'IHDR':
            if cabecera is not None or largo != 13:
                raise ErrorValidacion('IHDR inválido.')
            ancho, alto, bits, color, comp, filtro, inter = struct.unpack('>IIBBBBB', contenido)
            max_ancho, max_alto = (512, 512) if tipo == 'foto' else (1200, 400)
            if not (0 < ancho <= max_ancho and 0 < alto <= max_alto and ancho * alto <= 480000):
                raise ErrorValidacion('Dimensiones fuera de límite.')
            if bits != 8 or color not in (2, 6) or (comp, filtro, inter) != (0, 0, 0):
                raise ErrorValidacion('PNG debe ser RGB/RGBA de 8 bits sin interlazado.')
            cabecera = (ancho, alto, 3 if color == 2 else 4)
        elif chunk == b'IDAT':
            if cerrado:
                raise ErrorValidacion('IDAT no consecutivos.')
            hubo_idat = True
            comprimido.extend(contenido)
        elif chunk == b'IEND':
            if largo or not hubo_idat or fin != len(png):
                raise ErrorValidacion('IEND inválido.')
            terminado = True
        else:
            if hubo_idat:
                cerrado = True
            if chunk == b'PLTE':
                if hubo_idat or largo == 0 or largo > 768 or largo % 3:
                    raise ErrorValidacion('PLTE inválido.')
            elif not chunk[0] & 32:
                raise ErrorValidacion('Chunk crítico desconocido.')
        posicion = fin
    if not terminado:
        raise ErrorValidacion('Falta IEND.')
    ancho, alto, canales = cabecera
    paso = 1 + ancho * canales
    esperado = alto * paso
    try:
        descompresor = zlib.decompressobj()
        pixeles = descompresor.decompress(comprimido, esperado + 1)
        if (len(pixeles) != esperado or not descompresor.eof or
                descompresor.unused_data or descompresor.unconsumed_tail or
                any(pixeles[i] > 4 for i in range(0, esperado, paso))):
            raise ErrorValidacion('Datos de píxeles inválidos.')
    except zlib.error:
        raise ErrorValidacion('Compresión PNG inválida.') from None
    return PREFIJO + base64.b64encode(png).decode('ascii')


class RecursosPerfiles:
    def __init__(self, carpeta):
        self.almacen = AlmacenJSON(carpeta)
        self.lock = RLock()

    def _leer(self):
        datos = self.almacen.leer('perfiles.json', {'version': 1, 'perfiles': {}})
        if (not isinstance(datos, dict) or set(datos) != {'version', 'perfiles'} or
                type(datos['version']) is not int or datos['version'] != 1 or
                not isinstance(datos['perfiles'], dict)):
            raise ErrorDatos('Recursos de perfil corruptos.')
        for identificador, recursos in datos['perfiles'].items():
            if (not re.fullmatch(r'[a-f0-9]{32}', identificador) or
                    not isinstance(recursos, dict) or set(recursos) != {'foto', 'banner'}):
                raise ErrorDatos('Recursos de perfil corruptos.')
            for tipo, valor in recursos.items():
                try:
                    if valor != '':
                        validar_png(valor, tipo)
                except ErrorValidacion:
                    raise ErrorDatos('Recursos de perfil corruptos.') from None
        return datos

    def _mutar(self, accion):
        with self.lock:
            datos = deepcopy(self._leer())
            resultado = accion(datos['perfiles'])
            self.almacen.guardar('perfiles.json', datos)
            return deepcopy(resultado)

    def perfil(self, cuenta):
        if cuenta is None:
            return None
        with self.lock:
            recursos = self._leer()['perfiles'].get(cuenta['id'], {'foto': '', 'banner': ''})
            return {**deepcopy(cuenta), **deepcopy(recursos),
                    'tema': self.preferencia_tema(cuenta['id'])}

    def _leer_preferencias(self):
        datos = self.almacen.leer('preferencias.json', {'version': 1, 'perfiles': {}})
        if (not isinstance(datos, dict) or set(datos) != {'version', 'perfiles'} or
                type(datos['version']) is not int or datos['version'] != 1 or
                not isinstance(datos['perfiles'], dict)):
            raise ErrorDatos('Preferencias de perfil corruptas.')
        for identificador, preferencia in datos['perfiles'].items():
            if (not re.fullmatch(r'[a-f0-9]{32}', identificador) or
                    not isinstance(preferencia, dict) or set(preferencia) != {'tema'} or
                    preferencia['tema'] not in ('claro', 'oscuro')):
                raise ErrorDatos('Preferencias de perfil corruptas.')
        return datos

    def preferencia_tema(self, cuenta_id):
        with self.lock:
            preferencia = self._leer_preferencias()['perfiles'].get(cuenta_id)
            return preferencia['tema'] if preferencia else 'claro'

    def guardar_preferencia(self, cuenta_id, datos):
        if (not isinstance(datos, dict) or set(datos) != {'tema'} or
                datos['tema'] not in ('claro', 'oscuro')):
            raise ErrorValidacion('El tema debe ser claro u oscuro.')
        if not isinstance(cuenta_id, str) or not re.fullmatch(r'[a-f0-9]{32}', cuenta_id):
            raise ErrorValidacion('Cuenta inválida.')
        with self.lock:
            preferencias = deepcopy(self._leer_preferencias())
            preferencias['perfiles'][cuenta_id] = {'tema': datos['tema']}
            self.almacen.guardar('preferencias.json', preferencias)
            return {'tema': datos['tema']}

    def editar(self, cuenta_id, datos):
        if set(datos) != {'tipo', 'imagen'} or datos['tipo'] not in ('foto', 'banner'):
            raise ErrorValidacion('Envía solo tipo e imagen.')
        imagen = '' if datos['imagen'] == '' else validar_png(datos['imagen'], datos['tipo'])
        def accion(perfiles):
            recursos = perfiles.setdefault(cuenta_id, {'foto': '', 'banner': ''})
            recursos[datos['tipo']] = imagen
            return recursos
        return self._mutar(accion)
