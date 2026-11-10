"""Las preguntas de aula se limitan al autor y al profesor asignado."""
import unittest

import test_cursos_fase2 as fase2


class PreguntasAulaHTTP(unittest.TestCase):
    setUp = fase2.CursosFase2.setUp
    cerrar = fase2.CursosFase2.cerrar
    request = fase2.CursosFase2.request
    login = fase2.CursosFase2.login

    def test_pregunta_privada_y_respuesta_docente(self):
        profesor, _ = self.login('martin')
        ana, _ = self.login('ana')
        diego, _ = self.login('diego')
        curso = 'principal'
        sesion = self.request('/api/cursos/sesiones', {
            'curso_id': curso, 'titulo': 'Sesión de prueba', 'tema': '',
            'fecha': '2020-11-09', 'descripcion': 'Práctica de clase.',
            'inicio': '09:00', 'fin': '10:00', 'edificio': 'A', 'piso': 1, 'aula': 'A-101',
        }, profesor)[2]['resultado']['id']
        ruta = '/api/cursos/trabajo'
        base = {'curso_id': curso, 'sesion_id': sesion}
        consulta = ruta + f'?curso_id={curso}&sesion_id={sesion}'
        pregunta = {**base, 'tipo': 'pregunta', 'texto': '¿Cómo verifico el resultado?'}
        self.assertEqual(self.request(ruta, pregunta, ana)[0], 404)
        self.assertEqual(self.request('/api/cursos/sesiones/publicar',
                                      {'curso_id': curso, 'id': sesion}, profesor)[0], 200)
        codigo, _, cuerpo = self.request(ruta, pregunta, ana)
        self.assertEqual(codigo, 200, cuerpo)
        identificador = cuerpo['resultado']['id']
        self.assertEqual(self.request(consulta, cookie=diego)[2]['registros'], [])
        self.assertEqual(self.request(consulta, cookie=profesor)[2]['registros'][0]['id'], identificador)
        respuesta = {**base, 'tipo': 'responder_pregunta', 'pregunta_id': identificador,
                     'texto': 'Compara la salida con un caso sencillo.'}
        self.assertEqual(self.request(ruta, respuesta, diego)[0], 403)
        self.assertEqual(self.request(ruta, respuesta, profesor)[0], 200)
        self.assertEqual(self.request(consulta, cookie=ana)[2]['registros'][0]['respuesta'], respuesta['texto'])
        self.assertEqual(self.request(consulta, cookie=diego)[2]['registros'], [])
        self.assertEqual((self.carpeta / 'estado.json').read_bytes(), self.estado_original)
