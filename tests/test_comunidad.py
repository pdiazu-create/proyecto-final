"""Aislamiento por afiliación y moderación de la comunidad."""
import unittest

import test_cursos_fase2 as fase2


class ComunidadHTTP(unittest.TestCase):
    setUp = fase2.CursosFase2.setUp
    cerrar = fase2.CursosFase2.cerrar
    request = fase2.CursosFase2.request
    login = fase2.CursosFase2.login

    def test_afiliacion_respuestas_reporte_y_ocultamiento(self):
        ana, _ = self.login('ana')
        diego, _ = self.login('diego')
        sofia, _ = self.login('sofia')
        coord, _ = self.login('coordinacion')
        profe, _ = self.login('martin')
        ruta = '/api/comunidad'
        publicacion = {'accion': 'publicar', 'canal': 'carrera', 'texto': 'Material académico'}
        self.assertEqual(self.request(ruta, publicacion, ana)[0], 403)
        self.assertEqual(self.request(ruta, cookie=profe)[0], 403)
        for cuenta, facultad, carrera in ((ana, 'ingenieria', 'sistemas'),
                                          (diego, 'ingenieria', 'sistemas'),
                                          (sofia, 'ingenieria', 'civil')):
            self.assertEqual(self.request('/api/perfil', {'facultad_id': facultad,
                                                          'carrera_id': carrera}, cuenta)[0], 200)
        codigo, _, cuerpo = self.request(ruta, publicacion, ana)
        self.assertEqual(codigo, 200, cuerpo)
        post = cuerpo['resultado']['id']
        self.assertEqual(self.request(ruta, {**publicacion, 'canal': 'facultad'}, ana)[0], 200)
        vista = self.request(ruta, cookie=sofia)[2]['publicaciones']
        self.assertEqual([p['canal'] for p in vista], ['facultad'])
        respuesta = {'accion': 'responder', 'publicacion_id': post, 'texto': 'Gracias por compartir.'}
        self.assertEqual(self.request(ruta, respuesta, sofia)[0], 404)
        self.assertEqual(self.request(ruta, respuesta, diego)[0], 200)
        reporte = {'accion': 'reportar', 'publicacion_id': post, 'texto': 'Revisar publicación de prueba.'}
        self.assertEqual(self.request(ruta, reporte, diego)[0], 200)
        self.assertEqual(self.request(ruta, reporte, diego)[0], 409)
        pendientes = self.request(ruta, cookie=coord)[2]['reportes']
        decision = {'accion': 'moderar', 'reporte_id': pendientes[0]['id'], 'decision': 'ocultar'}
        self.assertEqual(self.request(ruta, decision, diego)[0], 403)
        self.assertEqual(self.request(ruta, decision, coord)[0], 200)
        self.assertEqual(self.request(ruta, cookie=coord)[2]['reportes'], [])
        vista = self.request(ruta, cookie=diego)[2]['publicaciones']
        self.assertEqual([p['canal'] for p in vista], ['facultad'])
        self.assertEqual((self.carpeta / 'estado.json').read_bytes(), self.estado_original)
