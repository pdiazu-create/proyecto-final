"""Flujo HTTP de archivos y permisos con datos temporales."""
import base64
import unittest

import test_cursos_fase2 as fase2


class TrabajoHTTP(unittest.TestCase):
    setUp = fase2.CursosFase2.setUp
    cerrar = fase2.CursosFase2.cerrar
    request = fase2.CursosFase2.request
    login = fase2.CursosFase2.login
    crear_curso = fase2.CursosFase2.crear_curso

    def test_recurso_entrega_reemplazo_y_permisos(self):
        profesor, cuenta = self.login('martin')
        coordinacion, _ = self.login('coordinacion')
        ana, _ = self.login('ana')
        diego, _ = self.login('diego')
        sofia, _ = self.login('sofia')
        curso = self.crear_curso(coordinacion, cuenta['id'], ['e1', 'e2'])
        ruta = '/api/cursos/trabajo'
        sesion = self.request('/api/cursos/sesiones', {
            'curso_id': curso['id'], 'titulo': 'Clase inicial', 'tema': '',
            'fecha': '2026-11-09', 'descripcion': 'Lectura y discusión.',
            'actividades': '', 'inicio': '09:00', 'fin': '10:00',
            'edificio': 'A', 'piso': 1, 'aula': 'A-101',
        }, profesor)[2]['resultado']
        base = {'curso_id': curso['id'], 'sesion_id': sesion['id']}
        consulta = f"?curso_id={curso['id']}&sesion_id={sesion['id']}"
        archivo = {'nombre': 'lectura.txt', 'contenido': base64.b64encode(b'Lectura').decode()}
        recurso = {**base, **archivo, 'tipo': 'recurso', 'titulo': 'Lectura'}
        self.assertEqual(self.request(ruta, recurso, ana)[0], 403)
        self.assertEqual(self.request(ruta, {**recurso, 'enlace': 'javascript:alert(1)'}, profesor)[0], 400)
        self.assertEqual(self.request(ruta, {**recurso, 'nombre': '../mal.txt'}, profesor)[0], 400)
        guardado = self.request(ruta, recurso, profesor)[2]['resultado']
        self.assertNotIn('contenido', guardado)
        self.assertEqual(self.request(ruta + consulta, cookie=ana)[0], 404)
        self.assertEqual(self.request('/api/cursos/sesiones/publicar',
                                      {'curso_id': curso['id'], 'id': sesion['id']}, profesor)[0], 200)
        actividad = self.request(ruta, {**base, 'tipo': 'actividad', 'titulo': 'Ejercicio',
                                       'instrucciones': 'Adjunta tu análisis.'}, profesor)[2]['resultado']
        self.assertEqual(self.request(ruta + consulta, cookie=sofia)[0], 403)
        self.assertEqual(self.request(ruta + consulta)[0], 401)
        descarga = ruta + '/archivo' + consulta + '&id='
        codigo, headers, cuerpo = self.request(descarga + guardado['id'], cookie=ana)
        self.assertEqual((codigo, cuerpo), (200, b'Lectura'))
        self.assertTrue(headers['Content-Disposition'].startswith('attachment;'))
        entrega = {**base, **archivo, 'tipo': 'entrega', 'actividad_id': actividad['id'],
                   'estudiante_id': 'e2'}
        primera = self.request(ruta, entrega, ana)[2]['resultado']
        self.assertEqual(primera['estudiante_id'], 'e1')
        self.assertEqual(self.request(descarga + primera['id'], cookie=diego)[0], 404)
        self.assertEqual(self.request(descarga + primera['id'], cookie=profesor)[0], 200)
        segunda = self.request(ruta, {**entrega, 'nombre': 'corregido.txt'}, ana)[2]['resultado']
        self.assertEqual(self.request(descarga + primera['id'], cookie=ana)[0], 404)
        registros = self.request(ruta + consulta, cookie=ana)[2]['registros']
        self.assertEqual([r['id'] for r in registros if r['tipo'] == 'entrega'], [segunda['id']])
        self.assertEqual((self.carpeta / 'estado.json').read_bytes(), self.estado_original)
