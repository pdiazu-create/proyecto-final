"""Publicación conjunta y recorrido académico con datos temporales."""
from datetime import date, timedelta
import unittest

import test_cursos_fase2 as fase2


class PublicacionClaseHTTP(unittest.TestCase):
    setUp = fase2.CursosFase2.setUp
    cerrar = fase2.CursosFase2.cerrar
    request = fase2.CursosFase2.request
    login = fase2.CursosFase2.login

    def test_tema_en_borrador_enlace_entrega_y_retroalimentacion(self):
        profesor, _ = self.login('martin')
        alumno, _ = self.login('ana')
        curso = 'principal'
        fecha = (date.today() + timedelta(days=7)).isoformat()

        def guardar(ruta, datos, cookie=profesor):
            codigo, _, cuerpo = self.request(ruta, datos, cookie)
            self.assertEqual(codigo, 200, cuerpo)
            return cuerpo['resultado']

        guardar('/api/cursos/temas', {'curso_id': curso, 'nombre': 'Diseño de API'})
        sesion = guardar('/api/cursos/sesiones', {
            'curso_id': curso, 'titulo': 'API en la práctica', 'tema': 'Diseño de API',
            'fecha': fecha, 'descripcion': 'Distinguir cliente y servidor.',
            'inicio': '09:00', 'fin': '10:00', 'edificio': 'A', 'piso': 1, 'aula': 'A-101',
        })['id']
        publicar = '/api/cursos/sesiones/publicar'
        seleccion = {'curso_id': curso, 'id': sesion}
        codigo, _, cuerpo = self.request(publicar, seleccion, profesor)
        self.assertEqual(codigo, 400)
        self.assertIn('tema está en borrador', cuerpo['error'])
        self.assertEqual(self.request(publicar, {**seleccion, 'publicar_tema': True}, alumno)[0], 403)

        trabajo = '/api/cursos/trabajo'
        consulta = trabajo + f'?curso_id={curso}&sesion_id={sesion}'
        base = {'curso_id': curso, 'sesion_id': sesion}
        recurso = {**base, 'tipo': 'recurso', 'titulo': 'Guía de API', 'categoria': 'lectura',
                   'momento': 'durante', 'borrador': True}
        codigo, _, cuerpo = self.request(trabajo, {**recurso, 'enlace': 'http://example.com/guia'}, profesor)
        self.assertEqual(codigo, 400)
        self.assertIn('HTTPS', cuerpo['error'])
        enlace = guardar(trabajo, {**recurso, 'enlace': 'https://example.com/guia'})
        actividad = guardar(trabajo, {
            **base, 'tipo': 'actividad', 'titulo': 'Reto API', 'instrucciones': 'Describe una petición.',
            'criterios': 'Distingue cliente y servidor.', 'vence': fecha + 'T18:00', 'borrador': True,
        })
        self.assertEqual(self.request(consulta, cookie=alumno)[0], 404)
        guardar(publicar, {**seleccion, 'publicar_tema': True})
        cursos = self.request('/api/cursos', cookie=alumno)[2]['cursos']
        publicado = next(c for c in cursos if c['id'] == curso)
        self.assertEqual(publicado['sesiones'][0]['tema'], 'Diseño de API')
        self.assertEqual(publicado['horarios'], [])
        self.assertEqual(self.request(consulta, cookie=alumno)[2]['registros'], [])
        guardar(trabajo, {**base, 'tipo': 'publicar_material', 'material_id': enlace['id']})
        guardar(trabajo, {**base, 'tipo': 'publicar_actividad', 'actividad_id': actividad['id']})
        registros = self.request(consulta, cookie=alumno)[2]['registros']
        self.assertEqual(next(r for r in registros if r['id'] == enlace['id'])['momento'], 'durante')
        pista = guardar(trabajo + '/orientar', {**base, 'tipo': 'pista', 'actividad_id': actividad['id']}, alumno)
        self.assertEqual(pista['origen'], 'reglas')
        self.assertIn('Reto API', pista['respuesta'])
        entrega = guardar(trabajo, {**base, 'tipo': 'entrega', 'actividad_id': actividad['id'],
                                    'nombre': 'reto.txt', 'contenido': 'R3JhY2U='}, alumno)
        nota = guardar(trabajo, {**base, 'tipo': 'nota', 'entrega_id': entrega['id'], 'puntaje': 90,
                                 'comentario': 'Explica también qué devuelve el servidor.'})['nota_borrador']
        self.assertFalse(any(r.get('nota_publicada') for r in self.request(consulta, cookie=alumno)[2]['registros']))
        guardar(trabajo, {**base, 'tipo': 'publicar_nota', 'entrega_id': entrega['id'], 'revision': nota['revision']})
        registros = self.request(consulta, cookie=alumno)[2]['registros']
        self.assertEqual(next(r for r in registros if r['id'] == entrega['id'])['nota_publicada']['comentario'],
                         'Explica también qué devuelve el servidor.')
        self.assertEqual((self.carpeta / 'estado.json').read_bytes(), self.estado_original)
