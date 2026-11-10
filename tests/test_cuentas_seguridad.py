"""Seguridad sobre ServidorGrace real, loopback efímero y datos temporales."""
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import app
from grace.archivos import ErrorDatos
from grace.cuentas import Cuentas, COOKIE, ITERACIONES
from grace.ia import ProveedorReglas
from grace.servicio import ServicioGrace


class SeguridadCuentas(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.carpeta = Path(self.tmp.name)
        with patch('grace.servicio.crear_proveedor', return_value=ProveedorReglas()):
            self.servicio = ServicioGrace(self.carpeta)
        self.estado_inicial = (self.carpeta / 'estado.json').read_bytes()
        self.server = app.ServidorGrace(('127.0.0.1', 0), servicio=self.servicio)
        self.hilo = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.hilo.start()
        self.addCleanup(self.cerrar)

    def cerrar(self):
        self.server.shutdown()
        self.server.server_close()
        self.hilo.join(3)

    def http(self, ruta, datos=None, cookie=None, headers=None):
        conexion = HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        cabeceras = {'Content-Type': 'application/json', **(headers or {})}
        if cookie:
            cabeceras['Cookie'] = cookie
        try:
            conexion.request('GET' if datos is None else 'POST', ruta,
                             None if datos is None else json.dumps(datos), cabeceras)
            respuesta = conexion.getresponse()
            cuerpo = respuesta.read()
            tipo = respuesta.getheader('Content-Type', '')
            return respuesta.status, dict(respuesta.getheaders()), json.loads(cuerpo) if 'json' in tipo else cuerpo
        finally:
            conexion.close()

    def login(self, usuario='ana', anterior=None):
        codigo, headers, cuerpo = self.http('/api/login', {'usuario': usuario, 'contrasena': '12345'}, anterior)
        self.assertEqual(codigo, 200, cuerpo)
        return headers['Set-Cookie'].split(';')[0], cuerpo['resultado']['usuario']

    def test_publicos_y_todas_las_rutas_exigen_sesion(self):
        self.assertTrue(self.http('/api/salud')[2]['autenticacion'])
        self.assertEqual(self.http('/api/sesion')[2], {'usuario': None})
        self.assertEqual(self.http('/coordinacion')[0], 200)
        gets = ['/api/estado', '/api/buscar?id=101', '/api/ruta', '/api/perfil', '/api/cuentas', '/api/desconocida']
        posts = ['/api/planes', '/api/planes/editar', '/api/planes/estado', '/api/asistencia',
                 '/api/asistencia/lote', '/api/entregas', '/api/solicitudes', '/api/atender',
                 '/api/conversar', '/api/reiniciar', '/api/logout', '/api/perfil', '/api/cuentas']
        for ruta in gets:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.http(ruta)[0], 401)
        for ruta in posts:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.http(ruta, {})[0], 401)
        self.assertEqual(self.http('/api/estado', headers={'X-Rol': 'profesor', 'X-Usuario': 'martin'})[0], 401)
        self.assertEqual(self.http('/api/estado?autenticacion=false&rol=profesor')[0], 401)

    def test_cookies_logout_rotacion_y_ocho_horas(self):
        codigo, headers, cuerpo = self.http('/api/login', {'usuario': ' ANA ', 'contrasena': '12345'})
        self.assertEqual(codigo, 200)
        for valor in ('HttpOnly', 'SameSite=Strict', 'Path=/', 'Max-Age=28800'):
            self.assertIn(valor, headers['Set-Cookie'])
        cookie = headers['Set-Cookie'].split(';')[0]
        self.assertGreaterEqual(len(cookie.split('=', 1)[1]), 40)
        self.assertEqual(self.http('/api/sesion', cookie=cookie)[2]['usuario'], cuerpo['resultado']['usuario'])
        nueva, _ = self.login('ana', cookie)
        self.assertNotEqual(cookie, nueva)
        self.assertEqual(self.http('/api/estado', cookie=cookie)[0], 401)
        self.assertEqual(self.http('/api/logout', {}, nueva)[0], 200)
        self.assertEqual(self.http('/api/sesion', cookie=nueva)[2], {'usuario': None})
        cookie, _ = self.login()
        ahora = self.server.cuentas.reloj()
        with patch.object(self.server.cuentas, 'reloj', return_value=ahora + 8 * 3600 + 1):
            self.assertEqual(self.http('/api/perfil', cookie=cookie)[0], 401)
        self.assertEqual(self.http('/api/perfil', cookie=f'{COOKIE}=inventado')[0], 401)

    def test_roles_sin_suplantacion_coordinador_y_reinicio_deshabilitado(self):
        academicas = ['/api/planes', '/api/planes/editar', '/api/planes/estado',
                      '/api/asistencia', '/api/asistencia/lote', '/api/atender']
        for nombre in ('ana', 'coordinacion'):
            cookie, _ = self.login(nombre)
            for ruta in academicas:
                with self.subTest(nombre=nombre, ruta=ruta):
                    self.assertEqual(self.http(ruta, {}, cookie)[0], 403)
        profesor, _ = self.login('martin')
        self.assertEqual(self.http('/api/estado', cookie=profesor)[0], 200)
        for ruta in ('/api/entregas', '/api/solicitudes', '/api/cuentas'):
            self.assertEqual(self.http(ruta, {}, profesor)[0], 403)
        self.assertEqual(self.http('/api/cuentas', cookie=profesor)[0], 403)
        coordinador, _ = self.login('coordinacion')
        for ruta in ('/api/estado', '/api/buscar?id=101', '/api/ruta'):
            self.assertEqual(self.http(ruta, cookie=coordinador)[0], 403)
        self.assertEqual(self.http('/api/conversar', {'rol': 'docente'}, coordinador)[0], 403)
        for cookie in (profesor, coordinador, self.login()[0]):
            self.assertEqual(self.http('/api/reiniciar', {'confirmacion': 'REINICIAR DEMO'}, cookie)[0], 403)

    def test_creacion_normalizada_nuevo_estudiante_entrega_y_recarga(self):
        coordinador, _ = self.login('coordinacion')
        codigo, _, respuesta = self.http('/api/cuentas', {'nombre': 'Laura', 'usuario': ' LAURA_4 ', 'rol': 'estudiante'}, coordinador)
        self.assertEqual(codigo, 200)
        nueva = respuesta['resultado']
        self.assertEqual(nueva['usuario'], 'laura_4')
        self.assertEqual(nueva['estudiante_id'], 'e4')
        cuentas = self.http('/api/cuentas', cookie=coordinador)[2]['cuentas']
        self.assertEqual(len(cuentas), 6)
        self.assertEqual(Cuentas(self.carpeta).listar(), cuentas)
        self.assertEqual((self.carpeta / 'estado.json').read_bytes(), self.estado_inicial)
        cookie, perfil = self.login(' LAURA_4 ')
        self.assertEqual(perfil, nueva)
        estado = self.http('/api/estado', cookie=cookie)[2]
        self.assertEqual([e['id'] for e in estado['estudiantes']], ['e4'])
        self.assertEqual(estado['estadisticas']['entregas'], 0)
        self.assertEqual(self.http('/api/entregas', {'actividad_id': 101}, cookie)[0], 200)
        self.assertEqual(self.http('/api/solicitudes', {'mensaje': 'Ayuda con las listas'}, cookie)[0], 200)
        self.assertEqual(self.http('/api/conversar', {'mensaje': 'mis pendientes'}, cookie)[0], 200)
        profesor, _ = self.login('martin')
        registros = [{'estudiante_id': f'e{i}', 'presente': True} for i in range(1, 5)]
        self.assertEqual(self.http('/api/asistencia/lote', {'fecha': '2026-11-08', 'registros': registros}, profesor)[0], 200)
        with patch('grace.servicio.crear_proveedor', return_value=ProveedorReglas()):
            recargado = ServicioGrace(self.carpeta)
        recargado.registro_estudiantes = Cuentas(self.carpeta).estudiantes
        self.assertEqual(recargado.estado('e4')['estadisticas']['mis_pendientes'], 6)
        self.assertEqual(json.loads((self.carpeta / 'estado.json').read_text(encoding='utf-8'))['version'], 4)

    def test_perfiles_campos_limites_y_datos_academicos_solo_profesor(self):
        cookie, perfil = self.login()
        campos = {'nombre': 'A' * 80, 'carrera': 'C' * 120, 'facultad': 'F' * 120, 'presentacion': 'P' * 500}
        codigo, _, respuesta = self.http('/api/perfil', campos, cookie)
        self.assertEqual(codigo, 200)
        self.assertEqual(respuesta['resultado']['id'], perfil['id'])
        self.assertEqual(self.http('/api/perfil', cookie=cookie)[2]['usuario'], respuesta['resultado'])
        for campo, valor in campos.items():
            self.assertEqual(self.http('/api/perfil', {campo: valor + 'x'}, cookie)[0], 400)
        for campo, valor in {'rol': 'profesor', 'usuario': 'otro', 'id': 'otro', 'estudiante_id': 'e2', 'foto': 'x'}.items():
            self.assertEqual(self.http('/api/perfil', {campo: valor}, cookie)[0], 400)
        self.assertEqual(self.http('/api/perfil', {'datos_academicos': 'x'}, cookie)[0], 403)
        profesor, _ = self.login('martin')
        self.assertEqual(self.http('/api/perfil', {'datos_academicos': 'D' * 500}, profesor)[0], 200)
        self.assertEqual(self.http('/api/perfil', {'datos_academicos': 'D' * 501}, profesor)[0], 400)
        self.assertEqual(self.http('/api/perfil', {'nombre': []}, profesor)[0], 400)
        self.assertEqual(self.http('/api/perfil', {'nombre': '  '}, profesor)[0], 400)

    def test_idor_estado_entrega_solicitud_y_chat(self):
        cookie, _ = self.login()
        for ruta in ('/api/estado?estudiante=e2', '/api/estado?estudiante=e1&estudiante=e2', '/api/estado?estudiante_id=e3'):
            self.assertEqual(self.http(ruta, cookie=cookie)[0], 403)
        for ruta in ('/api/entregas', '/api/solicitudes', '/api/conversar'):
            self.assertEqual(self.http(ruta, {'estudiante_id': 'e2', 'rol': 'docente'}, cookie)[0], 403)
        antes = (self.carpeta / 'estado.json').read_bytes()
        self.assertEqual(self.http('/api/conversar', {'mensaje': 'siguiente solicitud', 'rol': 'docente'}, cookie)[0], 200)
        contexto = {}
        def responder(mensaje, datos):
            contexto.update(datos)
            return {'respuesta': 'ok', 'origen': 'reglas'}
        with patch.object(self.servicio.ia, 'responder_chat', side_effect=responder):
            self.http('/api/conversar', {'mensaje': 'mis pendientes', 'rol': 'profesor'}, cookie)
        self.assertEqual(contexto['rol'], 'estudiante')
        self.assertEqual(contexto['estudiante_id'], 'e1')
        self.assertEqual(contexto['cola_interna'].tamano, 1)
        self.assertEqual(contexto['cola_interna'].ver_frente()['estudiante_id'], 'e1')
        for campo in ('entregas_interno', 'asistencias_interno'):
            self.assertTrue(all(r['estudiante_id'] == 'e1' for r in contexto[campo]))
        self.assertEqual((self.carpeta / 'estado.json').read_bytes(), antes)

    def test_estado_propio_y_planes_publicados_seguros(self):
        profesor, _ = self.login('martin')
        datos = {'objetivo': 'Practicar listas con ejercicios de Python', 'tema': 'Listas', 'fecha': '2026-11-20'}
        plan = self.http('/api/planes', datos, profesor)[2]['resultado']
        for accion in ('revisar', 'aprobar', 'publicar'):
            self.assertEqual(self.http('/api/planes/estado', {'id': plan['id'], 'accion': accion}, profesor)[0], 200)
        self.assertEqual(self.http('/api/planes', datos, profesor)[0], 200)
        cookie, _ = self.login('sofia')
        estado = self.http('/api/estado', cookie=cookie)[2]
        self.assertEqual(len(estado['planes']), 1)
        publicado = estado['planes'][0]
        self.assertEqual(set(publicado), {'id', 'actividad_id', 'estado', 'contenido', 'tema', 'fecha', 'objetivo', 'origen', 'historial'})
        self.assertEqual(publicado['estado'], 'publicado')
        self.assertEqual(publicado['historial'], [])
        self.assertEqual(estado['estadisticas']['planes'], 1)
        self.assertEqual(estado['estadisticas']['estudiantes'], 1)
        self.assertEqual(estado['estadisticas']['entregas'], 0)
        self.assertEqual(estado['estadisticas']['ayudas_pendientes'], 0)
        self.assertEqual(estado['solicitudes'], [])
        self.assertTrue(all(a['total_entregas'] == 0 for a in estado['actividades']))
        self.assertEqual(set(estado['resumen_asistencia']['por_estudiante']), {'e3'})
        self.assertNotIn('e2', json.dumps(estado))
        actividad = self.http('/api/buscar?id=101', cookie=cookie)[2]['actividad']
        self.assertNotIn('total_entregas', actividad)
        self.assertNotIn('estudiante_id', actividad)

    def test_hash_salt_y_perfiles_sin_secretos(self):
        datos = json.loads((self.carpeta / 'cuentas.json').read_text(encoding='utf-8'))
        self.assertEqual(len({c['salt'] for c in datos['cuentas']}), 5)
        self.assertEqual(len({c['hash'] for c in datos['cuentas']}), 5)
        self.assertNotIn('12345', (self.carpeta / 'cuentas.json').read_text(encoding='utf-8'))
        for cuenta in datos['cuentas']:
            esperado = hashlib.pbkdf2_hmac('sha256', b'12345', bytes.fromhex(cuenta['salt']), ITERACIONES).hex()
            self.assertEqual(cuenta['hash'], esperado)
            self.assertTrue(all(cuenta[c] == '' for c in ('carrera', 'facultad', 'presentacion', 'datos_academicos')))
        cookie, perfil = self.login('coordinacion')
        publico = json.dumps([perfil, self.http('/api/cuentas', cookie=cookie)[2]])
        for secreto in ('hash', 'salt', 'iteraciones', 'contrasena', '12345'):
            self.assertNotIn(secreto, publico)
        self.assertFalse(Cuentas(self.carpeta).sesiones)

    def test_corrupcion_y_ausencia_cierre_seguro_sin_resembrar(self):
        cookie, _ = self.login()
        ruta = self.carpeta / 'cuentas.json'
        original = ruta.read_bytes()
        for corrupto in (b'{', b'{}', b'{"version":1,"cuentas":[{}]}'):
            ruta.write_bytes(corrupto)
            self.assertEqual(self.http('/api/estado', cookie=cookie)[0], 503)
            self.assertEqual(self.http('/api/login', {'usuario': 'ana', 'contrasena': '12345'})[0], 503)
            with self.assertRaises(ErrorDatos):
                Cuentas(self.carpeta)
            self.assertEqual(ruta.read_bytes(), corrupto)
        ruta.write_bytes(original)
        ruta.unlink()
        self.assertEqual(self.http('/api/perfil', cookie=cookie)[0], 503)
        with self.assertRaises(ErrorDatos):
            Cuentas(self.carpeta)
        self.assertFalse(ruta.exists())

    def test_fallo_guardado_atomico_no_cambia_perfil_ni_estado(self):
        cookie, perfil = self.login()
        ruta = self.carpeta / 'cuentas.json'
        antes = ruta.read_bytes()
        with patch('grace.archivos.os.replace', side_effect=OSError('fallo simulado')):
            self.assertEqual(self.http('/api/perfil', {'nombre': 'Cambio'}, cookie)[0], 500)
        self.assertEqual(ruta.read_bytes(), antes)
        self.assertEqual(self.http('/api/perfil', cookie=cookie)[2]['usuario'], perfil)
        self.assertEqual((self.carpeta / 'estado.json').read_bytes(), self.estado_inicial)
        self.assertEqual(list(self.carpeta.glob('*.tmp')), [])

    def test_rate_fallos_aciertos_limpian_y_ventana_expira(self):
        for _ in range(12):
            self.login()
        for _ in range(10):
            self.assertEqual(self.http('/api/login', {'usuario': 'ana', 'contrasena': 'mala'})[0], 401)
        self.assertEqual(self.http('/api/login', {'usuario': 'ana', 'contrasena': '12345'})[0], 429)
        ahora = self.server.cuentas.reloj()
        with patch.object(self.server.cuentas, 'reloj', return_value=ahora + 301):
            self.login()
        self.assertEqual(self.server.cuentas.intentos, {})

    def test_creacion_duplicada_concurrente_y_validacion_usuario(self):
        cookie, _ = self.login('coordinacion')
        for usuario in ('ab', 'a' * 33, 'con.punto', 'con-guion'):
            self.assertEqual(self.http('/api/cuentas', {'nombre': 'Prueba', 'usuario': usuario, 'rol': 'estudiante'}, cookie)[0], 400)
        datos = {'nombre': 'Nueva', 'usuario': 'nueva', 'rol': 'estudiante'}
        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(executor.map(lambda _: self.http('/api/cuentas', datos, cookie)[0], range(2)))
        self.assertEqual(sorted(resultados), [200, 400])
        self.assertEqual(len(Cuentas(self.carpeta).listar()), 6)

    def test_origen_y_host_bloqueados_y_logs_no_secretos(self):
        self.assertEqual(self.http('/api/login', {}, headers={'Origin': 'http://ajeno.example'})[0], 403)
        self.assertEqual(self.http('/api/salud', headers={'Host': 'ajeno.example'})[0], 403)
        with patch('sys.stderr') as stderr:
            self.http('/api/login?contrasena=secreto', {'usuario': 'ana', 'contrasena': 'secreto'})
            self.assertFalse(stderr.write.called)
        with self.assertRaises(ValueError):
            app.ServidorGrace(('0.0.0.0', 0), servicio=self.servicio)


if __name__ == '__main__':
    unittest.main()
