"""Grace AI v0.4 — servidor local de demostración, sin dependencias.

Arrancar: python app.py
Navegador: http://127.0.0.1:8000
No publicar este servidor en Internet: NO existe autenticación real.
"""
import json
import os
import sys
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from grace.servicio import ErrorValidacion, ServicioGrace
from grace.archivos import ErrorDatos
from grace.ia import modo_ia

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
    '/': ('index.html', 'text/html; charset=utf-8'),
    '/estudiante': ('index.html', 'text/html; charset=utf-8'),
    '/profesor': ('index.html', 'text/html; charset=utf-8'),
    '/styles.css': ('styles.css', 'text/css; charset=utf-8'),
    '/app.js': ('app.js', 'application/javascript; charset=utf-8'),
    '/catalogo_demo.js': ('catalogo_demo.js', 'application/javascript; charset=utf-8'),
    '/horario.js': ('horario.js', 'application/javascript; charset=utf-8'),
    '/favicon.svg': ('favicon.svg', 'image/svg+xml'),
}


class ManejadorGrace(BaseHTTPRequestHandler):
    def _respuesta(self, codigo, cuerpo, tipo):
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
        url = urlparse(self.path)
        params = parse_qs(url.query)
        try:
            if url.path == '/api/salud':
                return self._json(200, {'estado': 'ok', 'version': '0.4',
                                        'modo': modo_ia(), 'proceso': os.getpid(),
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


class ServidorGrace(ThreadingHTTPServer):
    """Evita dos instancias enlazadas al mismo puerto en Windows."""
    allow_reuse_address = False
    allow_reuse_port = False

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
