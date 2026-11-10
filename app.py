"""Grace AI v0.4 — servidor local de demostración, sin dependencias.

Arrancar: python app.py
Navegador: http://127.0.0.1:8000
Servidor local con cuentas y permisos; no publicar en Internet.
"""
import json
import os
import sys
import socket
from time import monotonic
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from http.cookies import SimpleCookie, CookieError
from urllib.parse import parse_qs, urlparse
from urllib.parse import quote

from grace.trabajo import TrabajoAcademico, MAX_ARCHIVO
from grace.seguimiento import Seguimiento
from grace.comunidad import Comunidad

from grace.servicio import ErrorValidacion, ServicioGrace
from grace.archivos import ErrorDatos
from grace.ia import modo_ia
from grace.cuentas import Cuentas, ErrorAcceso, COOKIE
from grace.perfiles import RecursosPerfiles, catalogo
from grace.cursos import Cursos
from grace.acciones import GestorAcciones
from version_grace import revision_codigo

# Capturada al cargar el proceso, nunca recalculada desde los archivos cambiados.
REVISION_INICIO = revision_codigo()

BASE = Path(__file__).resolve().parent
WEB = BASE / 'web'
DATOS = Path(os.environ.get('GRACE_DATA_DIR', str(BASE / 'data')))
try:
    SERVICIO = ServicioGrace(DATOS)
except ErrorDatos as error:
    # No revelar traceback ni inventar otro estado cuando falta/corrompe el JSON.
    print(f'Grace no pudo iniciarse: {error}', file=sys.stderr)
    raise SystemExit(1) from None

ARCHIVOS = {
    '/personalizacion.js': ('personalizacion.js', 'application/javascript; charset=utf-8'),
    '/comunidad.js': ('comunidad.js', 'application/javascript; charset=utf-8'),
    '/seguimiento.js': ('seguimiento.js', 'application/javascript; charset=utf-8'),
    '/trabajo.js': ('trabajo.js', 'application/javascript; charset=utf-8'),
    '/': ('index.html', 'text/html; charset=utf-8'),
    '/estudiante': ('index.html', 'text/html; charset=utf-8'),
    '/profesor': ('index.html', 'text/html; charset=utf-8'),
    '/coordinacion': ('index.html', 'text/html; charset=utf-8'),
    '/cursos.js': ('cursos.js', 'application/javascript; charset=utf-8'),
    '/cuentas.js': ('cuentas.js', 'application/javascript; charset=utf-8'),
    '/styles.css': ('styles.css', 'text/css; charset=utf-8'),
    '/app.js': ('app.js', 'application/javascript; charset=utf-8'),
    '/catalogo_demo.js': ('catalogo_demo.js', 'application/javascript; charset=utf-8'),
    '/horario.js': ('horario.js', 'application/javascript; charset=utf-8'),
    '/favicon.svg': ('favicon.svg', 'image/svg+xml'),
}


class ManejadorGrace(BaseHTTPRequestHandler):
    @property
    def _real(self):
        # Compatibilidad exclusivamente por clase del servidor interno, nunca HTTP/env.
        return isinstance(self.server, ServidorGrace)

    def log_message(self, formato, *args):
        if self._real:
            # Ni URL/query, cuerpo, cookies o credenciales en los logs.
            return
        super().log_message(formato, *args)

    def _respuesta(self, codigo, cuerpo, tipo, descarga=None):
        if isinstance(cuerpo, str):
            cuerpo = cuerpo.encode('utf-8')
        self.send_response(codigo)
        for clave, valor in (
            ('Content-Type', tipo),
            ('Content-Length', str(len(cuerpo))),
            ('Cache-Control', 'no-store'),
            ('X-Content-Type-Options', 'nosniff'),
            ('X-Frame-Options', 'DENY'),
            ('Referrer-Policy', 'no-referrer'),
            ('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"),
        ):
            self.send_header(clave, valor)
        if getattr(self, '_cookie_salida', None):
            self.send_header('Set-Cookie', self._cookie_salida)
        if descarga is not None:
            self.send_header('Content-Disposition', "attachment; filename*=UTF-8''" + quote(descarga, safe=''))
        self.end_headers()
        self.wfile.write(cuerpo)

    def _json(self, codigo, datos):
        self._respuesta(codigo, json.dumps(datos, ensure_ascii=False).encode('utf-8'),
                        'application/json; charset=utf-8')

    def _validar_origen(self):
        # Contención mínima para una demo local. NO sustituye autenticación.
        host = self.headers.get('Host', '')
        nombre = host.split(':', 1)[0].lower()
        if nombre not in ('127.0.0.1', 'localhost'):
            self._json(403, {'error': 'Grace solo admite acceso local.'})
            return False
        origen = self.headers.get('Origin')
        if origen and origen not in ('http://' + host,):
            self._json(403, {'error': 'Origen no permitido.'})
            return False
        return True

    def do_GET(self):
        if not self._validar_origen():
            return
        if self._real:
            return self._peticion_real('GET')
        url = urlparse(self.path)
        params = parse_qs(url.query)
        try:
            if url.path == '/api/salud':
                return self._json(200, {'estado': 'ok', 'version': '0.4', 'revision': REVISION_INICIO,
                                        'modo': modo_ia(), 'cursos': True, 'proceso': os.getpid(),
                                        'instancia': os.environ.get('GRACE_INSTANCIA', '')})
            if url.path == '/api/estado':
                return self._json(200, SERVICIO.estado(params.get('estudiante', ['e1'])[0]))
            if url.path == '/api/buscar':
                return self._json(200, {'actividad': SERVICIO.buscar_actividad(params.get('id', [''])[0])})
            if url.path == '/api/ruta':
                return self._json(200, {'ruta': SERVICIO.calcular_ruta(
                    params.get('origen', [''])[0], params.get('destino', [''])[0])})
            if url.path not in ARCHIVOS:
                return self._json(404, {'error': 'Ruta no encontrada.'})
            nombre, tipo = ARCHIVOS[url.path]
            return self._respuesta(200, (WEB / nombre).read_bytes(), tipo)
        except ErrorValidacion as exc:
            return self._json(400, {'error': str(exc)})
        except Exception:
            return self._json(500, {'error': 'No se pudo procesar la solicitud.'})

    def do_POST(self):
        if not self._validar_origen():
            return
        if self._real:
            return self._peticion_real('POST')
        operaciones = {
            '/api/planes': SERVICIO.crear_plan,
            '/api/planes/editar': SERVICIO.editar_plan,
            '/api/planes/estado': SERVICIO.cambiar_estado_plan,
            '/api/asistencia': SERVICIO.registrar_asistencia,
            '/api/asistencia/lote': SERVICIO.registrar_asistencia_lote,
            '/api/entregas': SERVICIO.registrar_entrega,
            '/api/solicitudes': SERVICIO.solicitar_ayuda,
            '/api/atender': lambda _: SERVICIO.atender_siguiente(),
            '/api/conversar': lambda datos: SERVICIO.conversar_detallado(datos),
        }
        url = urlparse(self.path)
        if url.path != self.path or (url.path not in operaciones and url.path != '/api/reiniciar'):
            return self._json(404, {'error': 'Ruta no encontrada.'})
        if self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
            return self._json(415, {'error': 'Utiliza Content-Type: application/json.'})
        try:
            longitud = int(self.headers.get('Content-Length', '0'))
            if longitud < 0 or longitud > 8192:
                return self._json(413, {'error': 'Solicitud demasiado grande.'})
            datos = json.loads(self.rfile.read(longitud) or b'{}')
            if not isinstance(datos, dict):
                raise ErrorValidacion('El cuerpo debe ser un objeto JSON.')
            if self.path == '/api/reiniciar':
                if datos.get('confirmacion') != 'REINICIAR DEMO':
                    raise ErrorValidacion('Debes confirmar el reinicio de la demostración.')
                resultado = SERVICIO.reiniciar()
            else:
                resultado = operaciones[self.path](datos)
            return self._json(200, {'ok': True, 'resultado': resultado})
        except (ErrorValidacion, ValueError, json.JSONDecodeError) as exc:
            return self._json(400, {'error': str(exc) if isinstance(exc, ErrorValidacion)
                                    else 'JSON o entrada inválida.'})
        except Exception:
            return self._json(500, {'error': 'No se pudo guardar el cambio.'})

    def _token(self):
        try:
            cookie = SimpleCookie()
            cookie.load(self.headers.get('Cookie', ''))
            return cookie[COOKIE].value if COOKIE in cookie else None
        except CookieError:
            return None

    def _leer_cuerpo(self, limite=8192):
        if self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
            raise ErrorAcceso(415, 'Utiliza Content-Type: application/json.')
        try:
            longitud = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            raise ErrorValidacion('Longitud inválida.') from None
        if longitud < 0 or longitud > limite:
            if limite < longitud <= limite + 65536:
                self._descartar_cuerpo(longitud)
            raise ErrorAcceso(413, 'Solicitud demasiado grande.')
        datos = json.loads(self.rfile.read(longitud) or b'{}')
        if not isinstance(datos, dict):
            raise ErrorValidacion('El cuerpo debe ser un objeto JSON.')
        return datos

    def _descartar_cuerpo(self, restante):
        # Windows puede abortar la respuesta 413 si quedan bytes por leer.
        anterior = self.connection.gettimeout()
        vencimiento = monotonic() + 1
        try:
            while restante:
                espera = vencimiento - monotonic()
                if espera <= 0:
                    break
                self.connection.settimeout(espera)
                bloque = self.rfile.read1(min(restante, 65536))
                if not bloque:
                    break
                restante -= len(bloque)
        except OSError:
            pass
        finally:
            self.connection.settimeout(anterior)

    def _peticion_real(self, metodo):
        url = urlparse(self.path)
        ruta = url.path
        cuentas, servicio = self.server.cuentas, self.server.servicio
        try:
            if metodo == 'GET' and ruta == '/api/salud':
                return self._json(200, {'estado': 'ok', 'version': '0.4', 'revision': REVISION_INICIO, 'modo': modo_ia(),
                    'proceso': os.getpid(), 'instancia': os.environ.get('GRACE_INSTANCIA', ''),
                    'autenticacion': True, 'cursos': True, 'publicacion_conjunta': True})
            if metodo == 'GET' and not ruta.startswith('/api/'):
                if ruta not in ARCHIVOS:
                    raise ErrorAcceso(404, 'Ruta no encontrada.')
                nombre, tipo = ARCHIVOS[ruta]
                return self._respuesta(200, (WEB / nombre).read_bytes(), tipo)
            token = self._token()
            usuario = cuentas.sesion(token)
            if metodo == 'GET' and ruta == '/api/sesion':
                return self._json(200, {'usuario': self.server.recursos.perfil(usuario)})
            if metodo == 'POST' and ruta == '/api/login' and url.path == self.path:
                token, perfil = cuentas.login(self._leer_cuerpo(), self.client_address[0], token)
                self._cookie_salida = f'{COOKIE}={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=28800'
                return self._json(200, {'ok': True, 'resultado': {'usuario': self.server.recursos.perfil(perfil)}})
            if usuario is None:
                raise ErrorAcceso(401, 'Inicia sesión.')
            if ruta == '/api/comunidad' and metodo == 'GET':
                return self._json(200, self.server.comunidad.listar(usuario))
            if self.path == '/api/comunidad' and metodo == 'POST':
                resultado = self.server.comunidad.guardar(self._leer_cuerpo(8192), usuario)
                return self._json(200, {'resultado': resultado})
            if ruta == '/api/seguimiento' or ruta.startswith('/api/seguimiento/'):
                return self._peticion_seguimiento(metodo, url, usuario)
            rol = usuario['rol']
            if ruta == '/api/cursos' or ruta.startswith('/api/cursos/'):
                return self._peticion_cursos(metodo, url, usuario)
            permitidos_get = {'/api/perfil': {'estudiante', 'profesor', 'coordinador'},
                '/api/catalogo-academico': {'estudiante', 'profesor', 'coordinador'},
                '/api/cuentas': {'coordinador'}, '/api/estado': {'profesor', 'estudiante'},
                '/api/buscar': {'profesor', 'estudiante'}, '/api/ruta': {'profesor', 'estudiante'}}
            permitidos_post = {'/api/logout': {'estudiante', 'profesor', 'coordinador'},
                '/api/perfil/imagen': {'estudiante', 'profesor', 'coordinador'},
                '/api/perfil': {'estudiante', 'profesor', 'coordinador'},
                '/api/preferencias': {'estudiante', 'profesor', 'coordinador'},
                '/api/cuentas': {'coordinador'},
                '/api/planes': {'profesor'}, '/api/planes/editar': {'profesor'},
                '/api/planes/estado': {'profesor'}, '/api/asistencia': {'profesor'},
                '/api/asistencia/lote': {'profesor'}, '/api/atender': {'profesor'},
                '/api/entregas': {'estudiante'}, '/api/solicitudes': {'estudiante'},
                '/api/conversar': {'profesor', 'estudiante', 'coordinador'}, '/api/reiniciar': set()}
            permisos = permitidos_get if metodo == 'GET' else permitidos_post
            if ruta not in permisos or (metodo == 'POST' and self.path != ruta):
                raise ErrorAcceso(404, 'Ruta no encontrada.')
            if rol not in permisos[ruta]:
                raise ErrorAcceso(403, 'Tu cuenta no tiene permiso para esta operación.')
            params = parse_qs(url.query, keep_blank_values=True)
            if ruta == '/api/perfil' and params:
                raise ErrorAcceso(400, 'El perfil solo admite la cuenta de la sesión, sin parámetros.')
            if rol == 'estudiante':
                for clave in ('estudiante', 'estudiante_id'):
                    if any(v != usuario['estudiante_id'] for v in params.get(clave, [])):
                        raise ErrorAcceso(403, 'Solo puedes consultar tus datos.')
            academicas = {'/api/estado', '/api/buscar', '/api/ruta', '/api/planes',
                '/api/planes/editar', '/api/planes/estado', '/api/asistencia', '/api/asistencia/lote',
                '/api/atender', '/api/entregas', '/api/solicitudes'}
            if metodo == 'GET' and ruta in academicas:
                curso_ids = params.get('curso_id', [])
                if len(curso_ids) > 1:
                    raise ErrorValidacion('Envía un único curso_id.')
                servicio = self.server.cursos.servicio(
                    curso_ids[0] if curso_ids else 'principal', usuario)
            if metodo == 'GET':
                if ruta == '/api/catalogo-academico':
                    return self._json(200, catalogo())
                if ruta == '/api/perfil':
                    return self._json(200, {'usuario': self.server.recursos.perfil(usuario)})
                if ruta == '/api/cuentas':
                    return self._json(200, {'cuentas': cuentas.listar()})
                if ruta == '/api/estado':
                    predeterminado = servicio.estudiantes[0]['id'] if servicio.estudiantes else None
                    estudiante_id = usuario['estudiante_id'] if rol == 'estudiante' else params.get('estudiante', [predeterminado])[0]
                    estado = servicio.estado(estudiante_id)
                    if rol == 'estudiante':
                        estado = self._estado_propio(estado, estudiante_id)
                    return self._json(200, estado)
                if ruta == '/api/buscar':
                    return self._json(200, {'actividad': servicio.buscar_actividad(params.get('id', [''])[0])})
                return self._json(200, {'ruta': servicio.calcular_ruta(                params.get('origen', [''])[0], params.get('destino', [''])[0])})
            datos = self._leer_cuerpo(2 * 1024 * 1024 if ruta == '/api/perfil/imagen' else 8192)
            if ruta in academicas:
                servicio = self.server.cursos.servicio(datos.get('curso_id', 'principal'), usuario)
            if ruta == '/api/logout':
                cuentas.logout(token)
                self._cookie_salida = f'{COOKIE}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0'
                resultado = {}
            elif ruta == '/api/perfil':
                resultado = self.server.recursos.perfil(cuentas.editar(usuario['id'], datos))
            elif ruta == '/api/perfil/imagen':
                resultado = self.server.recursos.editar(usuario['id'], datos)
            elif ruta == '/api/preferencias':
                resultado = self.server.recursos.guardar_preferencia(usuario['id'], datos)
            elif ruta == '/api/cuentas':
                resultado = self.server.recursos.perfil(cuentas.crear(datos))
            elif ruta == '/api/conversar':
                if (rol == 'estudiante' and 'estudiante_id' in datos and
                        datos['estudiante_id'] != usuario['estudiante_id']):
                    raise ErrorAcceso(403, 'Solo puedes consultar tus propios datos.')
                if rol == 'coordinador' and ('rol' in datos or not isinstance(datos.get('mensaje'), str)):
                    raise ErrorAcceso(403, 'Esta consulta no está disponible para coordinación.')
                resultado = self.server.acciones.procesar(
                    datos.get('mensaje'), usuario, token,
                    self.server.cursos.ia, self.server.cursos)
                if resultado is None and rol == 'coordinador':
                    resultado = {'respuesta': 'Puedo ayudarte a cambiar la apariencia o abrir una pantalla. '
                                               'Tus datos académicos no están disponibles en este espacio.',
                                 'origen': 'reglas'}
                elif resultado is None:
                    servicio = self.server.cursos.servicio(datos.get('curso_id', 'principal'), usuario)
                    conversacion = {
                        'mensaje': datos.get('mensaje'),
                        'rol': 'docente' if rol == 'profesor' else 'estudiante',
                        'estudiante_id': usuario.get('estudiante_id'),
                    }
                    resultado = servicio.conversar_detallado(
                        conversacion, solo_propio=rol == 'estudiante')
                if self.server.acciones.filtrar_respuesta(resultado['respuesta']):
                    resultado['respuesta'] = (
                        'No encontré una forma adecuada de responder. Dime qué necesitas de tus clases '
                        'y lo revisamos con calma.'
                    )
            else:
                if rol == 'estudiante':
                    if 'estudiante_id' in datos and datos['estudiante_id'] != usuario['estudiante_id']:
                        raise ErrorAcceso(403, 'Solo puedes modificar tus datos.')
                    datos['estudiante_id'] = usuario['estudiante_id']
                if ruta == '/api/conversar':
                    datos['rol'] = 'docente' if rol == 'profesor' else 'estudiante'
                    resultado = servicio.conversar_detallado(datos, solo_propio=rol == 'estudiante')
                else:
                    operaciones = {'/api/planes': servicio.crear_plan,
                        '/api/planes/editar': servicio.editar_plan,
                        '/api/planes/estado': servicio.cambiar_estado_plan,
                        '/api/asistencia': servicio.registrar_asistencia,
                        '/api/asistencia/lote': servicio.registrar_asistencia_lote,
                        '/api/atender': lambda _: servicio.atender_siguiente(),
                        '/api/entregas': servicio.registrar_entrega,
                        '/api/solicitudes': servicio.solicitar_ayuda}
                    resultado = operaciones[ruta](datos)
            return self._json(200, {'ok': True, 'resultado': resultado})
        except ErrorAcceso as exc:
            return self._json(exc.codigo, {'error': str(exc)})
        except ErrorValidacion as exc:
            mensaje = (str(exc) if ruta in ('/api/cursos', '/api/comunidad') or ruta.startswith('/api/cursos/')
                       else 'Entrada inválida. Revisa los campos y sus límites.')
            return self._json(400, {'error': mensaje})
        except (ValueError, UnicodeError):
            return self._json(400, {'error': 'Entrada inválida. Revisa los campos y sus límites.'})
        except ErrorDatos:
            return self._json(503, {'error': 'Datos de cuentas no disponibles. Acceso cerrado.'})
        except Exception:
            return self._json(500, {'error': 'No se pudo procesar la solicitud.'})

    def _peticion_seguimiento(self, metodo, url, usuario):
        servicio = self.server.seguimiento
        ruta = url.path
        params = parse_qs(url.query)
        if metodo == 'GET':
            if ruta == '/api/seguimiento':
                return self._json(200, servicio.vista(usuario))
            if ruta == '/api/seguimiento/sesion':
                return self._json(200, servicio.asistencia(
                    params.get('curso_id', [''])[0], params.get('sesion_id', [''])[0], usuario))
            if ruta == '/api/seguimiento/archivo':
                nombre, cuerpo = servicio.descargar(params.get('id', [''])[0], usuario)
                return self._respuesta(200, cuerpo, 'application/octet-stream', descarga=nombre)
        if metodo == 'POST' and self.path == '/api/seguimiento':
            datos = self._leer_cuerpo(4 * ((MAX_ARCHIVO + 2) // 3) + 8192)
            return self._json(200, {'resultado': servicio.mutar(datos, usuario)})
        raise ErrorAcceso(404, 'Ruta no encontrada.')

    def _peticion_cursos(self, metodo, url, usuario):
        cursos = self.server.cursos
        ruta = url.path
        params = parse_qs(url.query, keep_blank_values=True)
        if ruta == '/api/cursos/trabajo' and metodo == 'POST' and self.path == ruta:
            datos = self._leer_cuerpo(4 * ((MAX_ARCHIVO + 2) // 3) + 8192)
            return self._json(200, {'resultado': self.server.trabajo.guardar(datos, usuario)})
        if ruta == '/api/cursos/trabajo/orientar' and metodo == 'POST' and self.path == ruta:
            datos = self._leer_cuerpo(2048)
            return self._json(200, {'resultado': self.server.trabajo.orientar(datos, usuario)})
        if ruta == '/api/cursos/trabajo/pendientes' and metodo == 'GET':
            return self._json(200, self.server.trabajo.pendientes_inicio(usuario))
        if ruta == '/api/cursos/trabajo/grupo/chat':
            if metodo == 'GET':
                return self._json(200, self.server.trabajo.conversacion_grupo(
                    params.get('curso_id', [''])[0], params.get('sesion_id', [''])[0],
                    params.get('actividad_id', [''])[0], usuario))
            if metodo == 'POST' and self.path == ruta:
                datos = self._leer_cuerpo(8192)
                resultado = self.server.trabajo.conversacion_grupo(
                    datos.get('curso_id'), datos.get('sesion_id'), datos.get('actividad_id'), usuario, datos)
                return self._json(200, {'resultado': resultado})
        if ruta == '/api/cursos/trabajo/notas' and metodo == 'GET':
            return self._json(200, self.server.trabajo.notas(params.get('curso_id', [''])[0], usuario))
        if metodo == 'GET' and ruta in ('/api/cursos/trabajo', '/api/cursos/trabajo/archivo'):
            curso = params.get('curso_id', [''])[0]
            sesion = params.get('sesion_id', [''])[0]
            if ruta.endswith('/archivo'):
                nombre, cuerpo = self.server.trabajo.descargar(curso, sesion, params.get('id', [''])[0], usuario)
                if nombre.lower().endswith('.mp4') and params.get('reproducir') == ['1']:
                    return self._respuesta(200, cuerpo, 'video/mp4')
                return self._respuesta(200, cuerpo, 'application/octet-stream', descarga=nombre)
            return self._json(200, self.server.trabajo.listar(curso, sesion, usuario))
        if metodo == 'GET':
            if ruta == '/api/cursos':
                return self._json(200, cursos.listar(usuario))
            if ruta == '/api/cursos/personas':
                return self._json(200, cursos.personas(usuario))
        elif metodo == 'POST' and self.path == ruta:
            operaciones = {
                '/api/cursos': cursos.crear,
                '/api/cursos/editar': cursos.editar,
                '/api/cursos/temas': lambda datos, cuenta: cursos.contenido('temas', datos, cuenta),
                '/api/cursos/syllabus': lambda datos, cuenta: cursos.contenido('syllabus', datos, cuenta),
                '/api/cursos/syllabus/publicar': lambda datos, cuenta: cursos.contenido('publicar_syllabus', datos, cuenta),
                '/api/cursos/sesiones': lambda datos, cuenta: cursos.contenido('sesiones', datos, cuenta),
                '/api/cursos/sesiones/publicar': lambda datos, cuenta: cursos.contenido('publicar_sesion', datos, cuenta),
                '/api/cursos/horarios': lambda datos, cuenta: cursos.contenido('horarios', datos, cuenta),
            }
            if ruta in operaciones:
                datos = self._leer_cuerpo(64 * 1024)
                return self._json(200, {'ok': True, 'resultado': operaciones[ruta](datos, usuario)})
        if params and metodo != 'GET':
            raise ErrorAcceso(404, 'Ruta no encontrada.')
        raise ErrorAcceso(404, 'Ruta no encontrada.')

    @staticmethod
    def _estado_propio(estado, estudiante_id):
        estado['estudiantes'] = [e for e in estado['estudiantes'] if e['id'] == estudiante_id]
        campos = {'id', 'actividad_id', 'estado', 'contenido', 'tema', 'fecha', 'objetivo', 'origen'}
        estado['planes'] = [{**{k: v for k, v in p.items() if k in campos}, 'historial': []}
                            for p in estado['planes'] if p['estado'] == 'publicado']
        for clave in ('asistencias', 'solicitudes', 'solicitudes_atendidas'):
            estado[clave] = [r for r in estado[clave] if r['estudiante_id'] == estudiante_id]
        resumen = estado['resumen_asistencia']['por_estudiante'][estudiante_id]
        estado['resumen_asistencia'] = {'por_estudiante': {estudiante_id: resumen}, 'clase': dict(resumen)}
        for actividad in estado['actividades']:
            actividad['total_entregas'] = int(actividad['entregada'])
        estado['estadisticas'].update(estudiantes=1, planes=len(estado['planes']),
            entregas=sum(a['entregada'] for a in estado['actividades']),
            ayudas_pendientes=len(estado['solicitudes']))
        return estado


class ServidorGrace(ThreadingHTTPServer):
    """Evita dos instancias enlazadas al mismo puerto en Windows."""
    allow_reuse_address = False
    allow_reuse_port = False

    def __init__(self, server_address, RequestHandlerClass=ManejadorGrace, bind_and_activate=True, *, servicio=None):
        if server_address[0] not in ('127.0.0.1', 'localhost'):
            raise ValueError('Este servidor solo admite loopback.')
        self.servicio = servicio if servicio is not None else SERVICIO
        self.cuentas = Cuentas(self.servicio.almacen.carpeta)
        self.recursos = RecursosPerfiles(self.servicio.almacen.carpeta)
        self.servicio.registro_estudiantes = self.cuentas.estudiantes
        self.cursos = Cursos(self.servicio.almacen.carpeta, self.cuentas, self.servicio)
        self.acciones = GestorAcciones(self.servicio.almacen.carpeta, self.recursos)
        self.trabajo = TrabajoAcademico(self.cursos)
        self.seguimiento = Seguimiento(self.cursos)
        self.comunidad = Comunidad(self.cursos)
        super().__init__(server_address, RequestHandlerClass, bind_and_activate)

    def server_bind(self):
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def iniciar_servidor(host='127.0.0.1', puerto=8000):
    # Permite solo el loopback para evitar exposiciones involuntarias.
    if host not in ('127.0.0.1', 'localhost'):
        raise ValueError('Este prototipo solo puede abrirse en el equipo local.')
    servidor = ServidorGrace((host, puerto), ManejadorGrace)
    print(f'Grace AI v0.4 disponible en http://{host}:{servidor.server_port}')
    print('Prototipo local con datos de prueba. Ctrl+C para salir.')
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print('\nGrace se ha cerrado.')
    finally:
        servidor.server_close()


if __name__ == '__main__':
    iniciar_servidor(puerto=int(os.environ.get('PORT', '8000')))
