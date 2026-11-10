"""Regresión de cupos, entregas grupales y publicación de notas."""
import json
import unittest
from unittest.mock import Mock, patch

from grace.ia import ErrorIA, ProveedorAPI
import test_cursos_fase2 as fase2


class GruposCalificaciones(unittest.TestCase):
    setUp = fase2.CursosFase2.setUp
    cerrar = fase2.CursosFase2.cerrar
    request = fase2.CursosFase2.request
    login = fase2.CursosFase2.login

    def test_entrega_grupal_cupo_y_revision_docente(self):
        profesor, _ = self.login('martin')
        ana, _ = self.login('ana')
        diego, _ = self.login('diego')
        sofia, _ = self.login('sofia')
        sesion = self.request('/api/cursos/sesiones', {
            'curso_id': 'principal', 'titulo': 'Clase', 'tema': '',
            'fecha': '2026-11-09', 'descripcion': 'Trabajo grupal.',
            'actividades': '', 'inicio': '09:00', 'fin': '10:00',
            'edificio': 'A', 'piso': 1, 'aula': 'A-101',
        }, profesor)[2]['resultado']['id']
        self.assertEqual(self.request('/api/cursos/sesiones/publicar',
                                      {'curso_id': 'principal', 'id': sesion}, profesor)[0], 200)
        ruta = '/api/cursos/trabajo'
        base = {'curso_id': 'principal', 'sesion_id': sesion}
        consulta = f'?curso_id=principal&sesion_id={sesion}'

        def post(tipo, cookie, **datos):
            return self.request(ruta, {**base, 'tipo': tipo, **datos}, cookie)

        actividad = post('actividad', profesor, titulo='Ejercicio', instrucciones='Adjunta la respuesta.',
                         cantidad=2, cupo=2, criterios='Exactitud y claridad.')[2]['resultado']['id']
        self.assertEqual(post('grupo', ana, actividad_id=actividad, grupo=1)[0], 200)
        self.assertEqual(post('grupo', diego, actividad_id=actividad, grupo=1)[0], 200)
        self.assertEqual(post('grupo', sofia, actividad_id=actividad, grupo=1)[0], 409)
        archivo = {'nombre': 'ejercicio.txt', 'contenido': 'R3JhY2U='}
        self.assertEqual(post('entrega', sofia, actividad_id=actividad, **archivo)[0], 409)
        entrega = post('entrega', ana, actividad_id=actividad, **archivo)[2]['resultado']['id']
        descarga = ruta + '/archivo' + consulta + '&id=' + entrega
        self.assertEqual(self.request(descarga, cookie=diego)[0], 200)
        self.assertEqual(self.request(descarga, cookie=sofia)[0], 404)
        self.assertEqual(post('grupo', diego, actividad_id=actividad, grupo=2)[0], 409)
        self.assertEqual(post('nota', ana, entrega_id=entrega, puntaje=99)[0], 403)

        proveedor = Mock()
        proveedor.sugerir_calificacion.return_value = {'puntaje': 82, 'comentario': 'Propuesta', 'origen': 'IA'}
        with patch.object(self.server.cursos, 'ia', proveedor):
            self.assertEqual(post('sugerir_nota', profesor, entrega_id=entrega, fragmento='Respuesta')[0], 400)
            proveedor.sugerir_calificacion.assert_not_called()
            propuesta = post('sugerir_nota', profesor, entrega_id=entrega, fragmento='Respuesta',
                             autoriza_envio=True)
            self.assertEqual(propuesta[2]['resultado']['puntaje'], 82)
            proveedor.sugerir_calificacion.assert_called_once_with('Exactitud y claridad.', 'Respuesta')
        registros = self.request(ruta + consulta, cookie=profesor)[2]['registros']
        self.assertFalse(any('nota_borrador' in r for r in registros))

        borrador = post('nota', profesor, entrega_id=entrega, puntaje=87,
                        comentario='Revisión docente.')[2]['resultado']['nota_borrador']
        registros = self.request(ruta + consulta, cookie=diego)[2]['registros']
        self.assertFalse(any('nota_borrador' in r for r in registros))
        notas = ruta + '/notas?curso_id=principal'
        self.assertEqual(self.request(notas, cookie=diego)[2]['notas'], [])
        self.assertEqual(post('publicar_nota', profesor, entrega_id=entrega, revision='obsoleta')[0], 409)
        self.assertEqual(post('publicar_nota', profesor, entrega_id=entrega, revision=borrador['revision'])[0], 200)
        self.assertEqual(self.request(notas, cookie=diego)[2]['notas'][0]['puntaje'], 87)
        self.assertEqual(self.request(notas, cookie=sofia)[2]['notas'], [])
        self.assertEqual(post('entrega', diego, actividad_id=actividad, **archivo)[0], 409)
        self.assertEqual((self.carpeta / 'estado.json').read_bytes(), self.estado_original)

    def test_proveedor_valida_propuestas(self):
        proveedor = ProveedorAPI('clave-ficticia')
        with patch.object(proveedor, '_solicitar', return_value=json.dumps({'puntaje': 85, 'comentario': 'Bien'})):
            self.assertEqual(proveedor.sugerir_calificacion('Criterio', 'Fragmento')['puntaje'], 85)
        for texto in ('no JSON', '{"puntaje":101,"comentario":"x"}', '{"puntaje":true,"comentario":"x"}'):
            with patch.object(proveedor, '_solicitar', return_value=texto), self.assertRaises(ErrorIA):
                proveedor.sugerir_calificacion('Criterio', 'Fragmento')
