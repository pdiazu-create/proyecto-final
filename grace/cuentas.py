"""Cuentas locales separadas del estado académico; sesiones solo en memoria."""
from copy import deepcopy
import hashlib
import hmac
import re
import secrets
import time
from threading import RLock

from .archivos import AlmacenJSON, ErrorDatos
from .servicio import ErrorValidacion, INSTITUCION
from .perfiles import ids_canonicos, nombres


CAMPOS = {'nombre': 80, 'carrera': 120, 'facultad': 120,
          'presentacion': 500, 'datos_academicos': 500}
ROLES = {'estudiante', 'profesor', 'coordinador'}
ITERACIONES = 260000
COOKIE = 'grace_sesion'


class ErrorAcceso(Exception):
    def __init__(self, codigo, mensaje):
        self.codigo = codigo
        super().__init__(mensaje)


class Cuentas:
    def __init__(self, carpeta):
        self.almacen = AlmacenJSON(carpeta)
        self.lock = RLock()
        self.sesiones = {}
        self.intentos = {}
        self.reloj = time.monotonic
        with self.lock:
            if not self.almacen.existe('cuentas.json'):
                marcador = self.almacen.carpeta / '.cuentas_inicializadas'
                if marcador.exists():
                    raise ErrorDatos('Falta cuentas.json; recupera una copia.')
                semillas = [('ana', 'Ana López', 'estudiante', 'e1'),
                            ('diego', 'Diego Ruiz', 'estudiante', 'e2'),
                            ('sofia', 'Sofía Pérez', 'estudiante', 'e3'),
                            ('martin', 'Martín', 'profesor', None),
                            ('coordinacion', 'Coordinación', 'coordinador', None)]
                self.almacen.guardar('cuentas.json', {
                    'version': 1, 'cuentas': [self._nueva(u, n, r, e) for u, n, r, e in semillas]})
            self._leer()
            (self.almacen.carpeta / '.cuentas_inicializadas').touch(exist_ok=True)

    @staticmethod
    def _nueva(usuario, nombre, rol, estudiante_id=None):
        salt = secrets.token_hex(16)
        cuenta = {'id': secrets.token_hex(16), 'usuario': usuario, 'rol': rol,
                  **{c: '' for c in CAMPOS}, 'nombre': nombre,
                  'salt': salt, 'iteraciones': ITERACIONES,
                  'hash': hashlib.pbkdf2_hmac('sha256', b'12345', bytes.fromhex(salt), ITERACIONES).hex()}
        if rol == 'estudiante':
            cuenta['estudiante_id'] = estudiante_id
        return cuenta

    def _leer(self):
        datos = self.almacen.leer('cuentas.json')
        try:
            if not isinstance(datos, dict) or datos.get('version') != 1 or not isinstance(datos.get('cuentas'), list) or not datos['cuentas']:
                raise ValueError
            ids, usuarios, estudiantes = set(), set(), set()
            for c in datos['cuentas']:
                esperados = {'id', 'usuario', 'rol', 'salt', 'hash', 'iteraciones'} | set(CAMPOS)
                if c.get('rol') == 'estudiante':
                    esperados.add('estudiante_id')
                if set(c) != esperados or c['rol'] not in ROLES:
                    raise ValueError
                if not isinstance(c['id'], str) or not re.fullmatch(r'[a-f0-9]{32}', c['id']) or c['id'] in ids:
                    raise ValueError
                if not isinstance(c['usuario'], str) or not re.fullmatch(r'[a-z0-9_]{3,32}', c['usuario']) or c['usuario'] in usuarios:
                    raise ValueError
                for campo, limite in CAMPOS.items():
                    if not isinstance(c[campo], str) or len(c[campo]) > limite or (campo == 'nombre' and not c[campo].strip()):
                        raise ValueError
                if type(c['iteraciones']) is not int or c['iteraciones'] != ITERACIONES or not re.fullmatch(r'[a-f0-9]{32}', c['salt']) or not re.fullmatch(r'[a-f0-9]{64}', c['hash']):
                    raise ValueError
                if c['rol'] == 'estudiante':
                    e = c['estudiante_id']
                    if not isinstance(e, str) or not re.fullmatch(r'e[1-9][0-9]*', e) or e in estudiantes:
                        raise ValueError
                    estudiantes.add(e)
                ids.add(c['id'])
                usuarios.add(c['usuario'])
        except (KeyError, TypeError, ValueError, AttributeError):
            raise ErrorDatos('Cuentas corruptas; acceso cerrado hasta recuperar los datos.') from None
        return datos

    def _mutar(self, accion):
        with self.lock:
            datos = deepcopy(self._leer())
            resultado = accion(datos['cuentas'])
            self.almacen.guardar('cuentas.json', datos)
            return deepcopy(resultado)

    @staticmethod
    def seguro(c):
        return {**{k: deepcopy(v) for k, v in c.items()
                if k in {'id', 'usuario', 'rol', 'estudiante_id'} | set(CAMPOS)},
                **ids_canonicos(c)}

    def listar(self):
        with self.lock:
            return [self.seguro(c) for c in self._leer()['cuentas']]

    def estudiantes(self):
        return [{'id': c['estudiante_id'], 'nombre': c['nombre'], 'institucion_id': INSTITUCION}
                for c in self.listar() if c['rol'] == 'estudiante']

    def crear(self, datos):
        if set(datos) != {'nombre', 'usuario', 'rol'}:
            raise ErrorValidacion('Envía nombre, usuario y rol.')
        nombre = self._texto(datos['nombre'], 'nombre')
        usuario, rol = datos['usuario'], datos['rol']
        if isinstance(usuario, str):
            usuario = usuario.strip().lower()
        if not isinstance(usuario, str) or not re.fullmatch(r'[a-z0-9_]{3,32}', usuario):
            raise ErrorValidacion('Usuario inválido: 3 a 32 letras, números o guion bajo.')
        if not isinstance(rol, str) or rol not in ROLES:
            raise ErrorValidacion('Rol inválido.')
        def accion(cuentas):
            if any(c['usuario'] == usuario for c in cuentas):
                raise ErrorValidacion('El usuario ya existe.')
            numero = max((int(c['estudiante_id'][1:]) for c in cuentas if c['rol'] == 'estudiante'), default=0) + 1
            cuenta = self._nueva(usuario, nombre, rol, f'e{numero}' if rol == 'estudiante' else None)
            cuentas.append(cuenta)
            return self.seguro(cuenta)
        return self._mutar(accion)

    @staticmethod
    def _texto(valor, campo):
        if not isinstance(valor, str) or len(valor) > CAMPOS[campo] or (campo == 'nombre' and not valor.strip()):
            raise ErrorValidacion(f'{campo}: texto de hasta {CAMPOS[campo]} caracteres' + (' no vacío.' if campo == 'nombre' else '.'))
        return valor.strip()

    def editar(self, cuenta_id, datos):
        if not datos or not set(datos).issubset(set(CAMPOS) | {'facultad_id', 'carrera_id'}):
            raise ErrorValidacion('Campos de perfil inválidos.')
        cambios = {k: self._texto(v, k) for k, v in datos.items() if k in CAMPOS}
        if 'facultad_id' in datos or 'carrera_id' in datos:
            if not {'facultad_id', 'carrera_id'}.issubset(datos) or {'facultad', 'carrera'} & set(datos):
                raise ErrorValidacion('Envía ambos IDs sin nombres libres.')
            cambios.update(nombres(datos['facultad_id'], datos['carrera_id']))
        def accion(cuentas):
            cuenta = next(c for c in cuentas if c['id'] == cuenta_id)
            if 'datos_academicos' in cambios and cuenta['rol'] != 'profesor':
                raise ErrorAcceso(403, 'Solo profesores pueden editar datos académicos.')
            cuenta.update(cambios)
            return self.seguro(cuenta)
        return self._mutar(accion)

    def login(self, datos, direccion, anterior=None):
        with self.lock:
            ahora = self.reloj()
            self.intentos = {k: v for k, v in self.intentos.items() if ahora - v[0] < 300}
            inicio, cantidad = self.intentos.get(direccion, (ahora, 0))
            if cantidad >= 10:
                raise ErrorAcceso(429, 'Demasiados intentos. Espera cinco minutos.')
            self.intentos[direccion] = (inicio, cantidad + 1)
            usuario, clave = datos.get('usuario'), datos.get('contrasena')
            if set(datos) != {'usuario', 'contrasena'} or not isinstance(usuario, str) or not isinstance(clave, str) or len(usuario) > 128 or len(clave) > 200:
                raise ErrorAcceso(401, 'Credenciales inválidas.')
            usuario = usuario.strip().lower()
            if not re.fullmatch(r'[a-z0-9_]{3,32}', usuario):
                raise ErrorAcceso(401, 'Credenciales inválidas.')
            cuenta = next((c for c in self._leer()['cuentas'] if c['usuario'] == usuario), None)
            salt = bytes.fromhex(cuenta['salt']) if cuenta else bytes(16)
            calculado = hashlib.pbkdf2_hmac('sha256', clave.encode(), salt, ITERACIONES).hex()
            if cuenta is None or not hmac.compare_digest(calculado, cuenta['hash']):
                raise ErrorAcceso(401, 'Credenciales inválidas.')
            self.intentos.pop(direccion, None)
            self._limpiar_sesiones()
            if anterior:
                self.sesiones.pop(anterior, None)
            token = secrets.token_urlsafe(32)
            self.sesiones[token] = (cuenta['id'], ahora + 8 * 3600)
            return token, self.seguro(cuenta)

    def _limpiar_sesiones(self):
        ahora = self.reloj()
        self.sesiones = {t: s for t, s in self.sesiones.items() if s[1] > ahora}

    def sesion(self, token):
        with self.lock:
            cuentas = self._leer()['cuentas']
            self._limpiar_sesiones()
            sesion = self.sesiones.get(token)
            return next((self.seguro(c) for c in cuentas if sesion and c['id'] == sesion[0]), None)

    def logout(self, token):
        with self.lock:
            self.sesiones.pop(token, None)
