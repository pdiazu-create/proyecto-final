"""Catálogo de demostración y recursos propios: HTTP real, sin red externa."""
import base64
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
import json
from pathlib import Path
import struct
import tempfile
import threading
import unittest
from unittest.mock import patch
import zlib

import app
from grace.cuentas import Cuentas
from grace.ia import ProveedorReglas
from grace.perfiles import MAX_BYTES, PREFIJO, RecursosPerfiles, validar_png
from grace.servicio import ErrorValidacion, ServicioGrace


def chunk(tipo, contenido):
    return struct.pack('>I', len(contenido)) + tipo + contenido + struct.pack('>I', zlib.crc32(tipo + contenido))


def png(ancho=2, alto=2, color=6, bits=8, inter=0, crudo=None, comprimido=None):
    if crudo is None:
        crudo = (b'\0' + bytes(ancho * (4 if color == 6 else 3))) * alto
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', ancho, alto, bits, color, 0, 0, inter)) +
            chunk(b'IDAT', zlib.compress(crudo) if comprimido is None else comprimido) + chunk(b'IEND', b''))


def url(datos):
    return PREFIJO + base64.b64encode(datos).decode('ascii')


class PerfilesRecursos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.carpeta = Path(self.tmp.name)
        with patch('grace.servicio.crear_proveedor', return_value=ProveedorReglas()):
            servicio = ServicioGrace(self.carpeta)
        self.server = app.ServidorGrace(('127.0.0.1', 0), servicio=servicio)
        self.hilo = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.hilo.start()
        self.addCleanup(self.cerrar)
        self.estado = (self.carpeta / 'estado.json').read_bytes()
        self.cuentas = (self.carpeta / 'cuentas.json').read_bytes()

    def cerrar(self):
        self.server.shutdown()
        self.server.server_close()
        self.hilo.join(3)

    def http(self, ruta, datos=None, cookie=None, headers=None):
        conexion = HTTPConnection('127.0.0.1', self.server.server_port, timeout=10)
        cabeceras = {'Content-Type': 'application/json', **(headers or {})}
        if cookie:
            cabeceras['Cookie'] = cookie
        try:
            conexion.request('GET' if datos is None else 'POST', ruta,
                             None if datos is None else json.dumps(datos), cabeceras)
            respuesta = conexion.getresponse()
            return respuesta.status, dict(respuesta.getheaders()), json.loads(respuesta.read())
        finally:
            conexion.close()

    def login(self, usuario='ana'):
        codigo, headers, respuesta = self.http('/api/login', {'usuario': usuario, 'contrasena': '12345'})
        self.assertEqual(codigo, 200, respuesta)
        return headers['Set-Cookie'].split(';')[0], respuesta['resultado']['usuario']

    def subir(self, cookie, imagen=None, tipo='foto', **extras):
        return self.http('/api/perfil/imagen', {'tipo': tipo, 'imagen': url(png()) if imagen is None else imagen, **extras}, cookie)

    def test_catalogo_todos_roles_y_pares_canonicos(self):
        for usuario in ('ana', 'martin', 'coordinacion'):
            cookie, _ = self.login(usuario)
            codigo, _, respuesta = self.http('/api/catalogo-academico', cookie=cookie)
            self.assertEqual(codigo, 200)
            self.assertEqual([f['id'] for f in respuesta['facultades']], ['ingenieria', 'negocios', 'salud'])
            for facultad in respuesta['facultades']:
                for carrera in facultad['carreras']:
                    datos = {'facultad_id': facultad['id'], 'carrera_id': carrera['id']}
                    codigo, _, resultado = self.http('/api/perfil', datos, cookie)
                    self.assertEqual(codigo, 200)
                    perfil = resultado['resultado']
                    self.assertEqual((perfil['facultad'], perfil['carrera']), (facultad['nombre'], carrera['nombre']))
                    self.assertEqual({k: perfil[k] for k in datos}, datos)
        self.assertEqual((self.carpeta / 'estado.json').read_bytes(), self.estado)
        originales = json.loads(self.cuentas)['cuentas']
        actuales = json.loads((self.carpeta / 'cuentas.json').read_bytes())['cuentas']
        self.assertEqual([set(c) for c in originales], [set(c) for c in actuales])

    def test_pares_invalidos_legacy_y_desvincular(self):
        cookie, _ = self.login()
        for datos in ({'facultad_id': 'salud', 'carrera_id': 'civil'}, {'facultad_id': 'ingenieria'},
                      {'carrera_id': 'civil'}, {'facultad_id': '', 'carrera_id': 'civil'},
                      {'facultad_id': [], 'carrera_id': 'civil'},
                      {'facultad_id': 'inventada', 'carrera_id': 'civil'},
                      {'facultad_id': 'ingenieria', 'carrera_id': 'civil', 'facultad': 'otra'}):
            self.assertEqual(self.http('/api/perfil', datos, cookie)[0], 400)
        self.assertEqual((self.carpeta / 'cuentas.json').read_bytes(), self.cuentas)
        for datos in ({'facultad': 'F' * 120, 'carrera': 'C' * 120},
                      {'facultad': 'Salud', 'carrera': 'Ingeniería Civil'}):
            codigo, _, cuerpo = self.http('/api/perfil', datos, cookie)
            self.assertEqual(codigo, 200)
            self.assertEqual((cuerpo['resultado']['facultad_id'], cuerpo['resultado']['carrera_id']), ('', ''))
            self.assertEqual(cuerpo['resultado']['rol'], 'estudiante')
        cuerpo = self.http('/api/perfil', {'facultad_id': '', 'carrera_id': ''}, cookie)[2]['resultado']
        self.assertEqual([cuerpo[k] for k in ('carrera', 'facultad', 'carrera_id', 'facultad_id')], [''] * 4)

    def test_imagenes_todos_roles_login_sesion_editar_y_quitar(self):
        for usuario in ('ana', 'martin', 'coordinacion'):
            cookie, _ = self.login(usuario)
            for tipo in ('foto', 'banner'):
                codigo, _, cuerpo = self.subir(cookie, tipo=tipo)
                self.assertEqual(codigo, 200)
                self.assertEqual(cuerpo['resultado'][tipo], url(png()))
            for ruta in ('/api/perfil', '/api/sesion'):
                self.assertEqual(self.http(ruta, cookie=cookie)[2]['usuario']['foto'], url(png()))
            self.assertEqual(self.login(usuario)[1]['banner'], url(png()))
            perfil = self.http('/api/perfil', {'nombre': 'Nuevo nombre'}, cookie)[2]['resultado']
            self.assertEqual((perfil['foto'], perfil['banner']), (url(png()), url(png())))
            self.assertEqual(self.subir(cookie, '', 'foto')[2]['resultado'], {'foto': '', 'banner': url(png())})
            self.assertEqual(self.subir(cookie, '', 'banner')[2]['resultado'], {'foto': '', 'banner': ''})
        self.assertEqual((self.carpeta / 'estado.json').read_bytes(), self.estado)

    def test_auth_idor_y_listado_sin_imagenes(self):
        self.assertEqual(self.http('/api/catalogo-academico')[0], 401)
        self.assertEqual(self.subir(None)[0], 401)
        cookie, ana = self.login()
        diego_cookie, diego = self.login('diego')
        for clave in ('id', 'usuario', 'usuario_id', 'cuenta_id', 'estudiante_id', 'ruta', 'foto'):
            self.assertEqual(self.subir(cookie, **{clave: diego['id']})[0], 400)
        self.assertEqual(self.http('/api/perfil/imagen?id=' + diego['id'], {}, cookie)[0], 404)
        self.assertEqual(self.http('/api/perfil?id=' + diego['id'], cookie=cookie)[0], 400)
        self.assertEqual(self.subir(cookie)[0], 200)
        self.assertEqual(self.http('/api/perfil', cookie=diego_cookie)[2]['usuario']['foto'], '')
        coordinador, _ = self.login('coordinacion')
        listado = self.http('/api/cuentas', cookie=coordinador)[2]['cuentas']
        self.assertTrue(all('foto' not in c and 'banner' not in c for c in listado))
        self.assertEqual(listado, Cuentas(self.carpeta).listar())
        self.assertEqual(set(json.loads((self.carpeta / 'perfiles.json').read_bytes())['perfiles']), {ana['id']})

    def test_rechazo_crc_html_mime_truncado_y_limites_png(self):
        cookie, _ = self.login()
        roto = bytearray(png())
        roto[-1] ^= 1
        invalidas = [url(roto), url(png()[:-1]), url(b'<html>hola</html>'),
                     'data:image/svg+xml;base64,PHN2Zz4=', 'data:image/jpeg;base64,AA==',
                     'data:image/png;base64,!!!!', 'DATA:image/png;base64,AA==',
                     url(png(513, 1)), url(png(1, 513)), url(png(bits=16)), url(png(inter=1)),
                     url(png(color=0)), url(png(crudo=b'\x05' + bytes(8) + b'\0' + bytes(8))),
                     url(png(crudo=bytes(17))), url(png(crudo=bytes(19))),
                     url(png(comprimido=zlib.compress(bytes(5000000)))),
                     url(png(comprimido=zlib.compress(bytes(18)) + b'extra')),
                     url(png() + b'extra'), url(bytes(MAX_BYTES + 1))]
        for imagen in invalidas:
            with self.subTest(imagen=imagen[:40]):
                self.assertEqual(self.subir(cookie, imagen)[0], 400)
        for tipo, ancho, alto in (('foto', 512, 512), ('banner', 1200, 400)):
            self.assertEqual(self.subir(cookie, url(png(ancho, alto)), tipo)[0], 200)
        for ancho, alto in ((1201, 1), (1, 401), (1200, 401)):
            self.assertEqual(self.subir(cookie, url(png(ancho, alto)), 'banner')[0], 400)
        for datos in ({'tipo': 'otro', 'imagen': ''}, {'tipo': [], 'imagen': ''}, {'tipo': 'foto', 'imagen': None}):
            self.assertEqual(self.http('/api/perfil/imagen', datos, cookie)[0], 400)

    def test_rgb_y_filtros_legales_y_chunks(self):
        for color in (2, 6):
            canales = 3 if color == 2 else 4
            crudo = b''.join(bytes([f]) + bytes(2 * canales) for f in range(5))
            imagen = url(png(2, 5, color=color, crudo=crudo))
            self.assertEqual(validar_png(imagen, 'foto'), imagen)
        base = png()
        for invalido in (base[:8] + base[33:], base[:33] + base[8:33] + base[33:],
                         base[:-12] + chunk(b'XXXX', b'') + base[-12:],
                         base[:-12] + chunk(b'tEXt', b'a\0b') + chunk(b'IDAT', b'') + base[-12:]):
            with self.assertRaises(ErrorValidacion):
                validar_png(url(invalido), 'foto')

    def test_limites_cuerpo_solo_endpoint_imagen(self):
        cookie, _ = self.login()
        self.assertEqual(self.http('/api/perfil', {'nombre': 'x' * 9000}, cookie)[0], 413)
        self.assertEqual(self.subir(cookie, 'x' * 9000)[0], 400)
        self.assertEqual(self.subir(cookie, 'x' * (2 * 1024 * 1024))[0], 413)
        self.assertEqual(self.subir(cookie, headers='extra')[0], 400)
        self.assertEqual(self.http('/api/perfil/imagen', {'tipo': 'foto', 'imagen': ''}, cookie,
                                   {'Content-Type': 'text/html'})[0], 415)

    def test_persistencia_aislada_y_fallo_atomico(self):
        cookie, perfil = self.login()
        self.assertEqual(self.subir(cookie)[0], 200)
        self.assertEqual(RecursosPerfiles(self.carpeta).perfil(perfil)['foto'], url(png()))
        ruta = self.carpeta / 'perfiles.json'
        antes = ruta.read_bytes()
        with patch('grace.archivos.os.replace', side_effect=OSError('fallo simulado')):
            self.assertEqual(self.subir(cookie, '')[0], 500)
        self.assertEqual(ruta.read_bytes(), antes)
        self.assertEqual(list(self.carpeta.glob('*.tmp')), [])
        self.assertEqual((self.carpeta / 'cuentas.json').read_bytes(), self.cuentas)
        self.assertEqual((self.carpeta / 'estado.json').read_bytes(), self.estado)
        ruta.write_text('{}', encoding='utf-8')
        self.assertEqual(self.http('/api/perfil', cookie=cookie)[0], 503)
        self.assertEqual(ruta.read_text(encoding='utf-8'), '{}')

    def test_mutaciones_concurrentes_no_pierden_recursos(self):
        cookie, _ = self.login()
        with ThreadPoolExecutor(max_workers=2) as executor:
            codigos = list(executor.map(lambda tipo: self.subir(cookie, tipo=tipo)[0], ('foto', 'banner')))
        self.assertEqual(codigos, [200, 200])
        perfil = self.http('/api/perfil', cookie=cookie)[2]['usuario']
        self.assertEqual((perfil['foto'], perfil['banner']), (url(png()), url(png())))


if __name__ == '__main__':
    unittest.main()
