"""Recorrido docente-estudiante con una actividad propuesta y luego publicada."""
import unittest

import test_cursos_fase2 as fase2


class BocetoAulaHTTP(unittest.TestCase):
    setUp = fase2.CursosFase2.setUp
    cerrar = fase2.CursosFase2.cerrar
    request = fase2.CursosFase2.request
    login = fase2.CursosFase2.login

    def test_proponer_editar_publicar_y_entregar(self):
        profesor, _ = self.login('martin')
        estudiante, _ = self.login('ana')
        curso = 'principal'
        sesion = self.request('/api/cursos/sesiones', {
            'curso_id': curso, 'titulo': 'Colas enlazadas', 'tema': '',
            'fecha': '2020-11-09', 'descripcion': 'Orden de llegada.',
            'actividades': '', 'inicio': '09:00', 'fin': '10:00',
            'edificio': 'A', 'piso': 1, 'aula': 'A-101',
        }, profesor)[2]['resultado']['id']
        self.assertEqual(self.request('/api/cursos/sesiones/publicar',
                                      {'curso_id': curso, 'id': sesion}, profesor)[0], 200)
        ruta = '/api/cursos/trabajo'
        base = {'curso_id': curso, 'sesion_id': sesion}
        consulta = ruta + f'?curso_id={curso}&sesion_id={sesion}'

        def post(tipo, cookie, **campos):
            return self.request(ruta, {**base, 'tipo': tipo, **campos}, cookie)

        propuesta = post('generar_material', profesor, formato='actividad',
                         objetivo='Procesa la siguiente solicitud.')[2]['resultado']
        self.assertIn('Procesa', propuesta['instrucciones'])
        self.assertTrue(propuesta['criterios'])
        self.assertEqual(self.request(consulta, cookie=profesor)[2]['registros'], [])
        campos = {k: propuesta[k] for k in ('titulo', 'instrucciones', 'criterios')}
        actividad = post('actividad', profesor, **campos, borrador=True,
                         cantidad=2, cupo=2)[2]['resultado']['id']
        self.assertEqual(self.request(consulta, cookie=estudiante)[2]['registros'], [])
        self.assertEqual(post('grupo', estudiante, actividad_id=actividad, grupo=1)[0], 404)
        archivo = {'nombre': 'reto.txt', 'contenido': 'R3JhY2U='}
        self.assertEqual(post('entrega', estudiante, actividad_id=actividad, **archivo)[0], 404)
        campos['titulo'] = 'Reto de colas revisado'
        self.assertEqual(post('editar_actividad', profesor, actividad_id=actividad, **campos)[0], 200)
        self.assertEqual(post('publicar_actividad', estudiante, actividad_id=actividad)[0], 403)
        self.assertEqual(post('publicar_actividad', profesor, actividad_id=actividad)[0], 200)
        vista = self.request(consulta, cookie=estudiante)[2]['registros'][0]
        self.assertEqual(vista['titulo'], 'Reto de colas revisado')
        self.assertEqual(post('grupo', estudiante, actividad_id=actividad, grupo=1)[0], 200)
        self.assertEqual(post('entrega', estudiante, actividad_id=actividad, **archivo)[0], 200)
        self.assertEqual((self.carpeta / 'estado.json').read_bytes(), self.estado_original)

    def test_recurso_oculto_no_se_lista_ni_descarga(self):
        profesor, _ = self.login('martin')
        alumno, _ = self.login('ana')
        curso = 'principal'
        sesion = self.request('/api/cursos/sesiones', {
            'curso_id': curso, 'titulo': 'Materiales', 'tema': '',
            'fecha': '2020-11-09', 'descripcion': 'Revisar el archivo.',
            'actividades': '', 'inicio': '09:00', 'fin': '10:00',
            'edificio': 'A', 'piso': 1, 'aula': 'A-101',
        }, profesor)[2]['resultado']['id']
        self.request('/api/cursos/sesiones/publicar', {'curso_id': curso, 'id': sesion}, profesor)
        ruta = '/api/cursos/trabajo'
        base = {'curso_id': curso, 'sesion_id': sesion}
        recurso = self.request(ruta, {**base, 'tipo': 'recurso', 'borrador': True,
                                      'titulo': 'Lectura', 'nombre': 'lectura.txt',
                                      'contenido': 'R3JhY2U='}, profesor)[2]['resultado']['id']
        archivo = ruta + f'/archivo?curso_id={curso}&sesion_id={sesion}&id={recurso}'
        self.assertEqual(self.request(archivo, cookie=alumno)[0], 404)
        for tipo, codigo in [('publicar_material', 200), ('ocultar_material', 404)]:
            self.assertEqual(self.request(ruta, {**base, 'tipo': tipo, 'material_id': recurso}, profesor)[0], 200)
            self.assertEqual(self.request(archivo, cookie=alumno)[0], codigo)
