"""Permisos, asistencia histórica y acreditación de horas en loopback."""
import base64
import unittest

import test_cursos_fase2 as fase2


class SeguimientoHTTP(unittest.TestCase):
    setUp = fase2.CursosFase2.setUp
    cerrar = fase2.CursosFase2.cerrar
    request = fase2.CursosFase2.request
    login = fase2.CursosFase2.login

    def post(self, cookie, accion, **datos):
        return self.request('/api/seguimiento', {'accion': accion, **datos}, cookie)

    def test_constancia_privada_y_correccion_docente(self):
        profesor, _ = self.login('martin')
        alumno, _ = self.login('ana')
        otro, _ = self.login('diego')
        coordinacion, _ = self.login('coordinacion')
        sesion = self.request('/api/cursos/sesiones', {
            'curso_id': 'principal', 'titulo': 'Clase anterior', 'tema': '',
            'fecha': '2020-11-09', 'descripcion': 'Ejercicio académico.',
            'actividades': '', 'inicio': '09:00', 'fin': '10:00',
            'edificio': 'A', 'piso': 1, 'aula': 'A-101',
        }, profesor)[2]['resultado']['id']
        base = {'curso_id': 'principal', 'sesion_id': sesion}
        self.assertEqual(self.request('/api/cursos/sesiones/publicar',
                                      {'curso_id': 'principal', 'id': sesion}, profesor)[0], 200)
        self.assertEqual(self.post(alumno, 'marcar', **base, estado='presente')[0], 403)
        self.assertEqual(self.post(alumno, 'solicitar', **base)[2]['resultado']['estado'], 'solicitada')
        self.assertEqual(self.post(profesor, 'marcar', **base, estudiante_id='e1', estado='ausente')[0], 200)
        contenido = base64.b64encode(b'%PDF-1.4\n%%EOF').decode()
        solicitud = self.post(alumno, 'justificar', **base, nombre='constancia.pdf',
                              contenido=contenido)[2]['resultado']
        self.assertNotIn('contenido', solicitud)
        ruta = '/api/seguimiento/archivo?id=' + solicitud['id']
        self.assertEqual(self.request(ruta, cookie=otro)[0], 403)
        self.assertEqual(self.request(ruta, cookie=profesor)[0], 403)
        self.assertEqual(self.request(ruta, cookie=coordinacion)[0], 200)
        self.assertEqual(self.post(coordinacion, 'decision', solicitud_id=solicitud['id'],
                                   decision='aprobada')[0], 200)
        vista = '/api/seguimiento/sesion?curso_id=principal&sesion_id=' + str(sesion)
        docente = self.request(vista, cookie=profesor)[2]
        self.assertEqual(docente['solicitudes'], [{'estudiante_id': 'e1', 'estado': 'aprobada'}])
        self.assertEqual(docente['asistencias'][0]['estado'], 'ausente')
        self.assertEqual(self.post(coordinacion, 'marcar', **base, estudiante_id='e1',
                                   estado='justificada')[0], 403)
        self.assertEqual(self.post(profesor, 'marcar', **base, estudiante_id='e1',
                                   estado='justificada')[0], 200)
        self.assertEqual(self.request('/api/seguimiento', cookie=alumno)[2]['asistencias'][0]['estado'], 'justificada')
        self.assertEqual(self.request('/api/seguimiento', cookie=otro)[2]['asistencias'], [])
        self.assertEqual((self.carpeta / 'estado.json').read_bytes(), self.estado_original)

    def test_evento_facultad_y_horas_solo_al_aprobar(self):
        coordinacion, _ = self.login('coordinacion')
        alumno, _ = self.login('ana')
        otro, _ = self.login('diego')
        self.assertEqual(self.request('/api/perfil', {'facultad_id': 'ingenieria', 'carrera_id': 'sistemas'}, alumno)[0], 200)
        evento = {'titulo': 'Charla de prueba', 'fecha': '2020-11-09', 'clase': 'charla',
                  'minutos': 90, 'obligatorio': True, 'facultad_id': 'ingenieria'}
        self.assertEqual(self.post(alumno, 'evento', **evento)[0], 403)
        identificador = self.post(coordinacion, 'evento', **evento)[2]['resultado']['id']
        self.assertEqual(self.request('/api/seguimiento', cookie=otro)[2]['eventos'], [])
        evidencia = {'evento_id': identificador, 'nombre': 'evidencia.jpg', 'contenido': '/9j/2Q=='}
        self.assertEqual(self.post(otro, 'horas', **evidencia)[0], 403)
        solicitud = self.post(alumno, 'horas', **evidencia)[2]['resultado']
        self.assertEqual(self.request('/api/seguimiento', cookie=alumno)[2]['minutos'], 0)
        self.assertEqual(self.post(coordinacion, 'decision', solicitud_id=solicitud['id'],
                                   decision='aprobada')[0], 200)
        self.assertEqual(self.post(alumno, 'horas', **evidencia)[0], 409)
        datos = self.request('/api/seguimiento', cookie=alumno)[2]
        self.assertEqual((datos['minutos'], datos['meta_minutos']), (90, 1500))
