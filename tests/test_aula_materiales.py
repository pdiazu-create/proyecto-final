"""Documentos descargables y publicación explícita en el aula."""
from io import BytesIO
import json
import unittest
from unittest.mock import patch
from xml.etree import ElementTree
from zipfile import ZipFile

from grace.ia import ProveedorGemini
import test_cursos_fase2 as fase2


class MaterialesAula(unittest.TestCase):
    setUp = fase2.CursosFase2.setUp
    cerrar = fase2.CursosFase2.cerrar
    request = fase2.CursosFase2.request
    login = fase2.CursosFase2.login

    def test_generar_descargar_y_publicar(self):
        profesor, _ = self.login('martin')
        alumno, _ = self.login('ana')
        curso = 'principal'
        sesion = self.request('/api/cursos/sesiones', {
            'curso_id': curso, 'titulo': 'API y datos', 'tema': '',
            'fecha': '2020-11-09', 'descripcion': 'Ejemplos de clase.',
            'actividades': '', 'inicio': '09:00', 'fin': '10:00',
            'edificio': 'A', 'piso': 1, 'aula': 'A-101',
        }, profesor)[2]['resultado']['id']
        self.assertEqual(self.request('/api/cursos/sesiones/publicar',
                                      {'curso_id': curso, 'id': sesion}, profesor)[0], 200)
        ruta = '/api/cursos/trabajo'
        consulta = f'?curso_id={curso}&sesion_id={sesion}'
        base = {'curso_id': curso, 'sesion_id': sesion}
        for formato, principal in [('pptx', 'ppt/presentation.xml'), ('docx', 'word/document.xml'),
                                   ('guion', 'word/document.xml')]:
            with self.subTest(formato=formato):
                datos = {**base, 'tipo': 'generar_material', 'formato': formato,
                         'objetivo': 'Explicar <cliente> & servidor.', 'momento': 'antes'}
                self.assertEqual(self.request(ruta, datos, alumno)[0], 403)
                codigo, _, respuesta = self.request(ruta, datos, profesor)
                self.assertEqual(codigo, 200, respuesta)
                borrador = respuesta['resultado']
                self.assertFalse(borrador['publicada'])
                listado = self.request(ruta + consulta, cookie=alumno)[2]['registros']
                self.assertNotIn(borrador['id'], {r['id'] for r in listado})
                url = ruta + '/archivo' + consulta + '&id=' + borrador['id']
                self.assertEqual(self.request(url, cookie=alumno)[0], 404)
                codigo, headers, cuerpo = self.request(url, cookie=profesor)
                self.assertEqual(codigo, 200)
                self.assertTrue(headers['Content-Disposition'].startswith('attachment;'))
                with ZipFile(BytesIO(cuerpo)) as paquete:
                    self.assertIn(principal, paquete.namelist())
                    for nombre in paquete.namelist():
                        ElementTree.fromstring(paquete.read(nombre))
                publicar = {**base, 'tipo': 'publicar_material', 'material_id': borrador['id']}
                self.assertEqual(self.request(ruta, publicar, alumno)[0], 403)
                self.assertEqual(self.request(ruta, publicar, profesor)[0], 200)
                self.assertEqual(self.request(url, cookie=alumno)[2], cuerpo)
        self.assertEqual((self.carpeta / 'estado.json').read_bytes(), self.estado_original)

    def test_material_usa_espera_mayor_y_estructura_validada(self):
        proveedor = ProveedorGemini('clave-ficticia')
        salida = json.dumps({'titulo': 'API', 'secciones': [{'titulo': 'Ejemplo', 'puntos': ['Cliente']}]})
        with patch.object(proveedor, '_solicitar', return_value=salida) as transporte:
            self.assertEqual(proveedor.generar_material('API', 'Introducción', 'pptx')['origen'], 'IA')
        self.assertEqual(transporte.call_args.kwargs['espera'], 90)
        self.assertEqual(set(transporte.call_args.args[0]), {'tarea', 'tema', 'objetivo', 'formato', 'estructura'})
