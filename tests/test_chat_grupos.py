"""La conversación de cada actividad queda limitada a su equipo."""
import unittest
from urllib.parse import urlencode

import test_cursos_fase2 as fase2


class ChatGruposHTTP(unittest.TestCase):
    setUp = fase2.CursosFase2.setUp
    cerrar = fase2.CursosFase2.cerrar
    request = fase2.CursosFase2.request
    login = fase2.CursosFase2.login

    def test_chat_aislado_por_grupo_y_actividad(self):
        profesor, ana, diego, sofia = [self.login(u)[0] for u in ('martin', 'ana', 'diego', 'sofia')]
        curso = 'principal'
        sesion = self.request('/api/cursos/sesiones', {
            'curso_id': curso, 'titulo': 'Clase de prueba', 'tema': '',
            'fecha': '2020-11-09', 'descripcion': 'Trabajo en equipo.',
            'inicio': '09:00', 'fin': '10:00', 'edificio': 'A', 'piso': 1, 'aula': 'A-101',
        }, profesor)[2]['resultado']['id']
        self.assertEqual(self.request('/api/cursos/sesiones/publicar',
                                      {'curso_id': curso, 'id': sesion}, profesor)[0], 200)
        trabajo = '/api/cursos/trabajo'
        base = {'curso_id': curso, 'sesion_id': sesion}
        actividad = self.request(trabajo, {**base, 'tipo': 'actividad', 'titulo': 'Ejercicio grupal',
                                            'instrucciones': 'Coordinen el ejercicio.',
                                            'cantidad': 2, 'cupo': 3}, profesor)[2]['resultado']['id']
        base['actividad_id'] = actividad
        ruta = trabajo + '/grupo/chat'
        consulta = ruta + '?' + urlencode(base)
        self.assertEqual(self.request(consulta, cookie=ana)[0], 403)
        for cuenta, grupo in ((ana, 1), (diego, 1), (sofia, 2)):
            self.assertEqual(self.request(trabajo, {**base, 'tipo': 'grupo', 'grupo': grupo}, cuenta)[0], 200)
        self.assertEqual(self.request(ruta, {**base, 'texto': 'Revisemos el ejemplo.'}, ana)[0], 200)
        self.assertEqual(self.request(consulta, cookie=diego)[2]['mensajes'][0]['texto'], 'Revisemos el ejemplo.')
        self.assertEqual(self.request(consulta, cookie=sofia)[2]['mensajes'], [])
        self.assertEqual(self.request(consulta, cookie=profesor)[0], 403)
        self.assertEqual(self.request(trabajo, {**base, 'tipo': 'grupo', 'grupo': 1}, sofia)[0], 200)
        self.assertEqual(self.request(consulta, cookie=sofia)[2]['mensajes'], [])
