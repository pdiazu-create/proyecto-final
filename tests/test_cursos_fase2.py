"""Integración HTTP de cursos; toda escritura usa carpetas temporales."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from unittest.mock import patch
from urllib.parse import quote

import app
from grace.ia import ProveedorReglas
from grace.servicio import CURSO, ServicioGrace


class CursosFase2(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.carpeta = Path(self.tmp.name)
        with patch('grace.servicio.crear_proveedor', return_value=ProveedorReglas()):
            self.servicio = ServicioGrace(self.carpeta)
        self.estado_original = (self.carpeta / 'estado.json').read_bytes()
        self.server = app.ServidorGrace(('127.0.0.1', 0), servicio=self.servicio)
        self.hilo = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.hilo.start()
        self.addCleanup(self.cerrar)
        self.url = ('127.0.0.1', self.server.server_port)

    def cerrar(self):
        self.server.shutdown()
        self.server.server_close()
        self.hilo.join(3)

    def request(self, path, datos=None, cookie=None):
        conexion = HTTPConnection(*self.url, timeout=5)
        headers = {'Content-Type': 'application/json'}
        if cookie:
            headers['Cookie'] = cookie
        try:
            conexion.request('GET' if datos is None else 'POST', path,
                             None if datos is None else json.dumps(datos), headers)
            respuesta = conexion.getresponse()
            body = respuesta.read()
            return respuesta.status, dict(respuesta.getheaders()), (
                json.loads(body) if 'json' in respuesta.getheader('Content-Type', '') else body)
        finally:
            conexion.close()

    def login(self, usuario):
        codigo, headers, cuerpo = self.request(
            '/api/login', {'usuario': usuario, 'contrasena': '12345'})
        self.assertEqual(codigo, 200, cuerpo)
        return headers['Set-Cookie'].split(';')[0], cuerpo['resultado']['usuario']

    def crear_curso(self, cookie, profesor_id, estudiantes=None, nombre='Curso nuevo'):
        datos = {'nombre': nombre, 'descripcion': 'Descripción de prueba', 'seccion': 'A',
                 'profesor_id': profesor_id, 'estudiantes': estudiantes or []}
        codigo, _, cuerpo = self.request('/api/cursos', datos, cookie)
        self.assertEqual(codigo, 200, cuerpo)
        return cuerpo['resultado']

    def test_migracion_conserva_estado_y_crea_respaldo_verificable(self):
        curso_principal = self.carpeta / 'cursos' / 'principal' / 'estado.json'
        respaldo = self.carpeta / 'cursos' / 'migraciones' / 'estado-anterior.json'
        self.assertEqual((self.carpeta / 'estado.json').read_bytes(), self.estado_original)
        self.assertFalse(curso_principal.exists())
        self.assertTrue(respaldo.is_file())
        anterior = json.loads(self.estado_original)
        guardado = json.loads(respaldo.read_text(encoding='utf-8'))
        self.assertEqual(guardado, anterior)
        self.assertEqual(anterior['curso_id'], CURSO)
        self.assertTrue((self.carpeta / '.cursos_inicializados').is_file())

    def test_listado_por_inscripcion_y_asignacion_del_profesor(self):
        coordinador, _ = self.login('coordinacion')
        otro_id = self.request('/api/cuentas', {
            'nombre': 'Profesora Dos', 'usuario': 'profe_dos', 'rol': 'profesor'},
            coordinador)[2]['resultado']['id']
        curso = self.crear_curso(coordinador, otro_id, ['e1'], 'Cálculo I')

        estudiante_ana, _ = self.login('ana')
        estudiante_diego, _ = self.login('diego')
        cursos_ana = self.request('/api/cursos', cookie=estudiante_ana)[2]['cursos']
        cursos_diego = self.request('/api/cursos', cookie=estudiante_diego)[2]['cursos']
        self.assertIn(curso['id'], {c['id'] for c in cursos_ana})
        self.assertNotIn(curso['id'], {c['id'] for c in cursos_diego})
        visible = next(c for c in cursos_ana if c['id'] == curso['id'])
        self.assertEqual(visible['estudiantes'], ['e1'])

        otro_profesor, _ = self.login('martin')
        self.assertNotIn(curso['id'], {c['id'] for c in self.request('/api/cursos', cookie=otro_profesor)[2]['cursos']})
        self.assertEqual(self.request('/api/cursos/editar', {
            'curso_id': curso['id'], 'nombre': 'No autorizado'}, otro_profesor)[0], 403)

    def test_temas_y_syllabus_solo_se_exponen_tras_publicar(self):
        coordinador, _ = self.login('coordinacion')
        personas = self.request('/api/cursos/personas', cookie=coordinador)[2]
        martin = next(p['id'] for p in personas['profesores'] if p['nombre'] == 'Martín')
        curso = self.crear_curso(coordinador, martin, ['e1'], 'Literatura')
        profesor, _ = self.login('martin')
        ruta_temas = '/api/cursos/temas'
        codigo, _, cuerpo = self.request(ruta_temas, {
            'curso_id': curso['id'], 'nombre': 'Narración'}, profesor)
        self.assertEqual(codigo, 200, cuerpo)
        tema_id = cuerpo['resultado']['id']
        estudiante, _ = self.login('ana')
        contenido = next(c for c in self.request('/api/cursos', cookie=estudiante)[2]['cursos']
                         if c['id'] == curso['id'])
        self.assertEqual(contenido['temas'], [])
        estado = self.request(f"/api/estado?curso_id={curso['id']}", cookie=estudiante)[2]
        self.assertNotIn('Narración', estado['grafo']['temas'])
        self.assertEqual(self.request(
            f"/api/ruta?curso_id={curso['id']}&origen={quote('Narración')}&destino={quote('Narración')}",
            cookie=estudiante)[0], 400)
        self.assertEqual(self.request(ruta_temas, {
            'curso_id': curso['id'], 'accion': 'publicar', 'id': tema_id, 'publicada': True},
            coordinador)[0], 403)
        codigo, _, _ = self.request(ruta_temas, {
            'curso_id': curso['id'], 'accion': 'publicar', 'id': tema_id, 'publicada': True},
            profesor)
        self.assertEqual(codigo, 200)
        contenido = next(c for c in self.request('/api/cursos', cookie=estudiante)[2]['cursos']
                         if c['id'] == curso['id'])
        self.assertEqual([t['nombre'] for t in contenido['temas']], ['Narración'])
        estado = self.request(f"/api/estado?curso_id={curso['id']}", cookie=estudiante)[2]
        self.assertIn('Narración', estado['grafo']['temas'])

        syllabus = {'curso_id': curso['id'], 'objetivos': 'Comprender narrativas',
                    'contenidos': 'Voz y estructura', 'organizacion': 'Lectura semanal'}
        self.assertEqual(self.request('/api/cursos/syllabus', syllabus, profesor)[0], 200)
        contenido = next(c for c in self.request('/api/cursos', cookie=estudiante)[2]['cursos']
                         if c['id'] == curso['id'])
        self.assertEqual(contenido['syllabus']['objetivos'], '')
        self.assertEqual(self.request('/api/cursos/syllabus/publicar',
                                      {'curso_id': curso['id']}, coordinador)[0], 403)
        self.assertEqual(self.request('/api/cursos/syllabus/publicar',
                                      {'curso_id': curso['id']}, profesor)[0], 200)
        contenido = next(c for c in self.request('/api/cursos', cookie=estudiante)[2]['cursos']
                         if c['id'] == curso['id'])
        self.assertTrue(contenido['syllabus']['publicada'])
        self.assertEqual(contenido['syllabus']['contenidos'], 'Voz y estructura')

    def test_sesiones_siempre_nacen_borrador_y_requieren_publicacion_docente(self):
        coordinador, _ = self.login('coordinacion')
        personas = self.request('/api/cursos/personas', cookie=coordinador)[2]
        martin = next(p['id'] for p in personas['profesores'] if p['nombre'] == 'Martín')
        curso = self.crear_curso(coordinador, martin, ['e1'], 'Historia')
        profesor, _ = self.login('martin')
        tema = self.request('/api/cursos/temas', {
            'curso_id': curso['id'], 'nombre': 'Fuentes históricas'}, profesor)[2]['resultado']
        self.assertEqual(self.request('/api/cursos/temas', {
            'curso_id': curso['id'], 'accion': 'publicar', 'id': tema['id'],
            'publicada': True}, profesor)[0], 200)
        sesion = {
            'curso_id': curso['id'], 'titulo': 'Clase inicial', 'tema': tema['nombre'],
            'fecha': '2026-11-09', 'descripcion': 'Lectura y discusión.',
            'actividades': 'Comparar dos fuentes.', 'inicio': '09:00', 'fin': '10:00',
            'edificio': 'A', 'piso': 1, 'aula': 'A-101',
        }
        codigo, _, cuerpo = self.request('/api/cursos/sesiones', {**sesion, 'publicada': True}, profesor)
        self.assertEqual(codigo, 400)
        codigo, _, cuerpo = self.request('/api/cursos/sesiones', sesion, profesor)
        self.assertEqual(codigo, 200, cuerpo)
        sesion_id = cuerpo['resultado']['id']
        estudiante, _ = self.login('ana')
        contenido = next(c for c in self.request('/api/cursos', cookie=estudiante)[2]['cursos']
                         if c['id'] == curso['id'])
        self.assertEqual(contenido['sesiones'], [])
        self.assertEqual(self.request('/api/cursos/sesiones/publicar',
                                      {'curso_id': curso['id'], 'id': sesion_id}, coordinador)[0], 403)
        self.assertEqual(self.request('/api/cursos/sesiones/publicar',
                                      {'curso_id': curso['id'], 'id': sesion_id}, profesor)[0], 200)
        contenido = next(c for c in self.request('/api/cursos', cookie=estudiante)[2]['cursos']
                         if c['id'] == curso['id'])
        self.assertEqual(contenido['sesiones'][0]['actividades'], 'Comparar dos fuentes.')
        self.assertTrue(contenido['sesiones'][0]['publicada'])

    def test_horario_valida_piso_dias_y_conflictos_de_matricula_y_aula(self):
        coordinador, _ = self.login('coordinacion')
        personas = self.request('/api/cursos/personas', cookie=coordinador)[2]
        profesores = personas['profesores']
        martin = next(p['id'] for p in profesores if p['nombre'] == 'Martín')
        segundo_id = self.request('/api/cuentas', {
            'nombre': 'Profesora Dos', 'usuario': 'profe_dos', 'rol': 'profesor'},
            coordinador)[2]['resultado']['id']
        curso_a = self.crear_curso(coordinador, martin, ['e1'], 'Curso A')
        curso_b = self.crear_curso(coordinador, segundo_id, ['e1'], 'Curso B')
        bloque = {'dia': 0, 'inicio': '09:00', 'fin': '10:00',
                  'edificio': 'A', 'piso': 1, 'aula': 'A-101'}
        self.assertEqual(self.request('/api/cursos/horarios', {
            'curso_id': curso_a['id'], 'horarios': [bloque]}, coordinador)[0], 200)
        mismo_estudiante = {**bloque, 'aula': 'A-102'}
        self.assertEqual(self.request('/api/cursos/horarios', {
            'curso_id': curso_b['id'], 'horarios': [mismo_estudiante]}, coordinador)[0], 400)
        self.assertEqual(self.request('/api/cursos/editar', {
            'curso_id': curso_b['id'], 'estudiantes': ['e2']}, coordinador)[0], 200)
        misma_aula = {**bloque}
        self.assertEqual(self.request('/api/cursos/horarios', {
            'curso_id': curso_b['id'], 'horarios': [misma_aula]}, coordinador)[0], 400)
        curso_c = self.crear_curso(coordinador, segundo_id, ['e2'], 'Curso C')
        self.assertEqual(self.request('/api/cursos/horarios', {
            'curso_id': curso_c['id'], 'horarios': [{**bloque, 'piso': 2}]}, coordinador)[0], 400)
        self.assertEqual(self.request('/api/cursos/horarios', {
            'curso_id': curso_c['id'], 'horarios': [{**bloque, 'dia': 5}]}, coordinador)[0], 400)

    def test_estado_academico_migrado_y_datos_originales_no_se_modifican(self):
        profesor, _ = self.login('martin')
        codigo, _, _ = self.request('/api/planes', {
            'objetivo': 'Practicar el recorrido de listas',
            'tema': 'Listas', 'fecha': '2026-11-20', 'curso_id': 'principal'}, profesor)
        self.assertEqual(codigo, 200)
        estado_curso = json.loads((self.carpeta / 'estado.json').read_text(encoding='utf-8'))
        self.assertNotEqual((self.carpeta / 'estado.json').read_bytes(), self.estado_original)
        self.assertEqual(estado_curso['planes'][-1]['curso_id'], CURSO)

    def test_registro_invalido_se_bloquea_sin_sobrescribirlo(self):
        coordinador, _ = self.login('coordinacion')
        personas = self.request('/api/cursos/personas', cookie=coordinador)[2]
        martin = next(p['id'] for p in personas['profesores'] if p['nombre'] == 'Martín')
        curso = self.crear_curso(coordinador, martin, ['e1'], 'Curso protegido')
        archivo = self.carpeta / 'cursos.json'
        datos = json.loads(archivo.read_text(encoding='utf-8'))
        siguiente = next(c for c in datos['cursos'] if c['id'] == curso['id'])
        siguiente['horarios'] = [{'dia': 6, 'inicio': '09:00', 'fin': '10:00',
                                  'edificio': 'A', 'piso': 1, 'aula': 'A-101'}]
        archivo.write_text(json.dumps(datos), encoding='utf-8')
        corrupto = archivo.read_bytes()
        self.assertEqual(self.request('/api/cursos', cookie=coordinador)[0], 503)
        self.assertEqual(archivo.read_bytes(), corrupto)

    def test_csp_y_api_requieren_sesion(self):
        codigo, headers, _ = self.request('/api/cursos')
        self.assertEqual(codigo, 401)
        profesor, _ = self.login('martin')
        codigo, headers, cuerpo = self.request('/cursos.js', cookie=profesor)
        self.assertEqual(codigo, 200)
        self.assertIn(b"'use strict'", cuerpo)
        self.assertIn("default-src 'self'", headers['Content-Security-Policy'])
        coordinador, _ = self.login('coordinacion')
        self.assertEqual(self.request('/api/estado?curso_id=principal',
                                      cookie=coordinador)[0], 403)


if __name__ == '__main__':
    unittest.main()
