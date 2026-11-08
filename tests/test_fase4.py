"""Fase 4: asistente local por reglas, fuentes y plantillas del temario."""
import tempfile
import unittest

from grace.asistente import detectar_intencion, generar_borrador_plan
from grace.servicio import ServicioGrace, TEMAS


class AsistentePorReglas(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.s = ServicioGrace(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def preguntar(self, texto, rol='estudiante', estudiante='e1'):
        return self.s.conversar({'mensaje': texto, 'rol': rol, 'estudiante_id': estudiante})

    def test_intencion_por_puntuacion_y_acentos(self):
        ejemplos = {
            '¿Qué tareas pendientes tengo?': 'pendientes',
            '¿Cuál es mi próxima fecha de entrega?': 'proxima',
            '¿Cómo va mi porcentaje de asistencia?': 'asistencia',
            '¿Cuál es la siguiente solicitud?': 'solicitud',
            '¿Qué estudio antes de Grafos?': 'prerrequisitos',
            'Hola, Grace': 'saludo',
        }
        for frase, esperado in ejemplos.items():
            with self.subTest(frase=frase):
                self.assertEqual(detectar_intencion(frase), esperado)

    def test_pendientes_reales_del_estudiante(self):
        respuesta = self.preguntar('¿Qué tareas tengo pendientes?')
        self.assertIn('6 actividades', respuesta)
        self.assertIn('Condicionales', respuesta)
        self.assertIn('Fuente: actividades', respuesta)

    def test_proxima_fecha_diferencia_clase_y_entrega(self):
        respuesta = self.preguntar('¿Cuál es mi próxima fecha de entrega?')
        self.assertIn('Fuente:', respuesta)
        if 'próxima actividad' in respuesta:
            self.assertIn('no un plazo de entrega independiente', respuesta)
        else:
            self.assertIn('No hay fechas futuras', respuesta)

    def test_porcentaje_asistencia_toma_registros(self):
        self.s.registrar_asistencia_lote({'fecha': '2026-11-10', 'registros': [
            {'estudiante_id': 'e1', 'presente': True},
            {'estudiante_id': 'e2', 'presente': False},
            {'estudiante_id': 'e3', 'presente': True},
        ]})
        self.assertIn('100.0%', self.preguntar('¿Cuál es mi porcentaje de asistencia?'))
        respuesta = self.preguntar('¿Cuál es el porcentaje de asistencia?', rol='docente')
        self.assertIn('66.7%', respuesta)
        self.assertIn('Fuente: lista de asistencias', respuesta)

    def test_siguiente_solicitud_y_privacidad_estudiante(self):
        self.assertIn('solicitud es #1', self.preguntar('¿Cuál es la siguiente solicitud?', rol='docente'))
        respuesta = self.preguntar('¿Cuál es la siguiente solicitud?', rol='estudiante')
        self.assertIn('no se muestra', respuesta)
        self.assertNotIn('Cómo recorro una lista', respuesta)

    def test_antes_de_tema_usa_bfs_y_fuente(self):
        respuesta = self.preguntar('¿Qué estudio antes de Grafos?')
        self.assertIn('Fundamentos', respuesta)
        self.assertIn('Archivos', respuesta)
        self.assertIn('BFS', respuesta)
        self.assertIn('Fuente: lista de adyacencia', respuesta)

    def test_faltan_datos_saludo_y_desconocida(self):
        self.assertIsNone(self.s.estado()['resumen_asistencia']['por_estudiante']['e1']['porcentaje'])
        self.assertIn('no hay registros', self.preguntar('¿Cuál es mi asistencia?').lower())
        self.assertIn('no soy ia generativa', self.preguntar('hola').lower())
        self.assertIn('asistente por reglas', self.preguntar('incomprensible mensaje extraño').lower())

    def test_cada_tema_tiene_plantilla_distinta(self):
        descripciones = set()
        for tema in TEMAS:
            with self.subTest(tema=tema):
                borrador = generar_borrador_plan('Objetivo académico de prueba', tema)
                self.assertIn('Objetivo académico de prueba', borrador['apertura'])
                for campo in ('desarrollo', 'practica', 'evaluacion'):
                    self.assertGreaterEqual(len(borrador[campo]), 5)
                self.assertIn('Requiere revisión humana', borrador['nota'])
                descripciones.add(borrador['practica'])
        self.assertEqual(len(descripciones), len(TEMAS))

    def test_no_acepta_tema_desconocido_en_plantilla(self):
        with self.assertRaises(ValueError):
            generar_borrador_plan('Objetivo académico de prueba', 'Tema inventado')


if __name__ == '__main__':
    unittest.main()
