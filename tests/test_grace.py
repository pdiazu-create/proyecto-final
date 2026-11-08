"""Pruebas automáticas: ejecutar python -m unittest discover -s tests -v"""
import tempfile
import unittest

from grace.estructuras import ColaEnlazada, ArbolBinarioBusqueda, GrafoAprendizaje
from grace.servicio import ServicioGrace, ErrorValidacion, INSTITUCION


class EstructurasTest(unittest.TestCase):
    def test_cola_fifo_y_vacia(self):
        cola = ColaEnlazada()
        self.assertIsNone(cola.desencolar())
        cola.encolar('primero')
        cola.encolar('segundo')
        self.assertEqual(cola.ver_frente(), 'primero')
        self.assertEqual(cola.desencolar(), 'primero')
        self.assertEqual(cola.desencolar(), 'segundo')
        self.assertIsNone(cola.desencolar())
        self.assertEqual(cola.tamano, 0)

    def test_arbol_busqueda_ordenada(self):
        arbol = ArbolBinarioBusqueda()
        for numero in (5, 2, 9, 1, 7):
            arbol.insertar(numero, {'id':numero})
        self.assertEqual([r['id'] for r in arbol.en_orden()], [1,2,5,7,9])
        self.assertEqual(arbol.buscar(7)['id'], 7)
        self.assertIsNone(arbol.buscar(100))

    def test_grafo_ruta_bfs(self):
        grafo = GrafoAprendizaje()
        for origen, destino in [('A','B'), ('B','D'), ('A','C'), ('C','E'), ('E','D')]:
            grafo.agregar_relacion(origen, destino)
        self.assertEqual(grafo.ruta_mas_corta('A','D'), ['A','B','D'])
        self.assertEqual(grafo.ruta_mas_corta('D','A'), [])
        self.assertEqual(grafo.ruta_mas_corta('A','Z'), [])


class ServicioTest(unittest.TestCase):
    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.servicio = ServicioGrace(self.carpeta.name)

    def tearDown(self):
        self.carpeta.cleanup()

    def nuevo_plan(self):
        return self.servicio.crear_plan({
            'objetivo':'Explicar colas enlazadas con ejercicios prácticos',
            'tema':'Colas enlazadas', 'fecha':'2026-11-20'
        })

    def test_estado_inicial_con_datos_ficticios(self):
        estado = self.servicio.estado()
        self.assertEqual(estado['estadisticas']['estudiantes'], 3)
        self.assertEqual(estado['estadisticas']['actividades'], 7)
        self.assertEqual(estado['estadisticas']['ayudas_pendientes'], 2)
        self.assertTrue(all(e['institucion_id']==INSTITUCION for e in estado['estudiantes']))

    def test_flujo_aprobacion_obligatorio(self):
        plan = self.nuevo_plan()
        self.assertEqual(plan['estado'], 'borrador')
        self.assertNotIn('Explicar colas', str(self.servicio.estado()['actividades']))
        with self.assertRaises(ErrorValidacion):
            self.servicio.cambiar_estado_plan({'id':plan['id'],'accion':'publicar'})
        for accion, esperado in [('revisar','en_revision'),('aprobar','aprobado'),('publicar','publicado')]:
            resultado = self.servicio.cambiar_estado_plan({'id':plan['id'],'accion':accion})
            self.assertEqual(resultado['estado'], esperado)
        self.assertEqual(len(self.servicio.estado()['actividades']), 8)
        self.assertEqual(len(resultado['historial']), 4)
        self.assertIsNotNone(self.servicio.buscar_actividad(resultado['actividad_id']))
        with self.assertRaises(ErrorValidacion):
            self.servicio.cambiar_estado_plan({'id':plan['id'],'accion':'publicar'})

    def test_rechazo_no_publica(self):
        plan=self.nuevo_plan()
        self.servicio.cambiar_estado_plan({'id':plan['id'],'accion':'revisar'})
        self.servicio.cambiar_estado_plan({'id':plan['id'],'accion':'rechazar'})
        self.assertEqual(len(self.servicio.estado()['actividades']), 7)
        with self.assertRaises(ErrorValidacion):
            self.servicio.cambiar_estado_plan({'id':plan['id'],'accion':'publicar'})

    def test_entrega_y_validaciones(self):
        self.servicio.registrar_entrega({'actividad_id':102,'estudiante_id':'e3'})
        with self.assertRaises(ErrorValidacion):
            self.servicio.registrar_entrega({'actividad_id':102,'estudiante_id':'e3'})
        with self.assertRaises(ErrorValidacion):
            self.servicio.registrar_entrega({'actividad_id':9999,'estudiante_id':'e3'})
        with self.assertRaises(ErrorValidacion):
            self.servicio.crear_plan({'objetivo':'corto','tema':'Listas','fecha':'2026-11-20'})

    def test_archivos_se_recargan(self):
        p=self.nuevo_plan()
        self.servicio.solicitar_ayuda({'estudiante_id':'e3','mensaje':'Necesito ayuda con árboles'})
        self.servicio.registrar_asistencia({'estudiante_id':'e1','fecha':'2026-11-06','presente':False})
        segundo=ServicioGrace(self.carpeta.name)
        self.assertEqual(segundo.estado()['estadisticas']['planes'], 1)
        self.assertEqual(segundo.estado()['estadisticas']['ayudas_pendientes'], 3)
        self.assertFalse(segundo.estado()['asistencias'][0]['presente'])
        self.assertEqual(segundo.estado()['planes'][0]['id'], p['id'])

    def test_asistencia_actualizar(self):
        self.servicio.registrar_asistencia({'estudiante_id':'e1','fecha':'2026-11-06','presente':False})
        self.servicio.registrar_asistencia({'estudiante_id':'e1','fecha':'2026-11-06','presente':True})
        estado=self.servicio.estado()
        self.assertEqual(len(estado['asistencias']),1)
        self.assertTrue(estado['asistencias'][0]['presente'])

    def test_cola_atencion(self):
        primero=self.servicio.atender_siguiente()
        self.assertEqual(primero['id'],1)
        self.assertEqual(self.servicio.estado()['estadisticas']['ayudas_pendientes'],1)
        self.servicio.atender_siguiente()
        with self.assertRaises(ErrorValidacion):
            self.servicio.atender_siguiente()


if __name__=='__main__':
    unittest.main()
