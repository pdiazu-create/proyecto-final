"""Casos límite y fallos no cubiertos por las diez pruebas originales."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from grace.archivos import AlmacenJSON, ErrorDatos
from grace.estructuras import ArbolBinarioBusqueda, ColaEnlazada, GrafoAprendizaje
from grace.servicio import ErrorValidacion, ServicioGrace, INSTITUCION, CURSO


class CasosEstructuras(unittest.TestCase):
    def test_cola_reutilizable_despues_de_vaciar(self):
        cola = ColaEnlazada()
        self.assertIsNone(cola.desencolar())
        for numero in range(5):
            cola.encolar(numero)
        self.assertEqual([cola.desencolar() for _ in range(5)], list(range(5)))
        self.assertEqual(cola.tamano, 0)
        self.assertIsNone(cola.frente)
        self.assertIsNone(cola.final)
        cola.encolar(11)
        self.assertEqual(cola.ver_frente(), 11)
        self.assertEqual(cola.desencolar(), 11)

    def test_arbol_profundo_sin_recursion(self):
        arbol = ArbolBinarioBusqueda()
        for numero in range(1800):
            arbol.insertar(numero, {'id': numero})
        self.assertEqual(arbol.tamano, 1800)
        self.assertEqual([r['id'] for r in arbol.en_orden()], list(range(1800)))
        self.assertEqual(arbol.niveles()[-1]['nivel'], 1799)
        self.assertEqual(arbol.buscar(1799), {'id': 1799})

    def test_arbol_actualizar_clave_no_duplica(self):
        arbol = ArbolBinarioBusqueda()
        arbol.insertar(5, 'a')
        arbol.insertar(5, 'b')
        self.assertEqual(arbol.tamano, 1)
        self.assertEqual(arbol.buscar(5), 'b')
        self.assertIsNone(arbol.buscar(9))

    def test_grafo_con_ciclo_y_ruta_minima(self):
        grafo = GrafoAprendizaje()
        for origen, destino in [('A','B'), ('B','A'), ('B','C'), ('A','C'), ('C','D')]:
            grafo.agregar_relacion(origen, destino)
        self.assertEqual(grafo.recorrido_anchura('A'), ['A', 'B', 'C', 'D'])
        self.assertEqual(grafo.ruta_mas_corta('A', 'D'), ['A', 'C', 'D'])
        self.assertEqual(grafo.ruta_mas_corta('D', 'A'), [])
        self.assertEqual(grafo.ruta_mas_corta('A', 'A'), ['A'])
        self.assertEqual(grafo.ruta_mas_corta('NADA', 'A'), [])


class CasosArchivos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.almacen = AlmacenJSON(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_leer_inexistente_devuelve_valor_proporcionado(self):
        self.assertEqual(self.almacen.leer('ninguno.json', []), [])

    def test_archivo_corrupto_no_se_oculta(self):
        ruta = Path(self.tmp.name) / 'estado.json'
        ruta.write_text('{no-es-json', encoding='utf-8')
        with self.assertRaises(ErrorDatos):
            self.almacen.leer('estado.json')
        self.assertEqual(ruta.read_text(encoding='utf-8'), '{no-es-json')

    def test_bloqueo_rutas_no_validas(self):
        for nombre in ('../archivo.json', '.oculto.json', 'a/b.json', 'a\\b.json', 'algo.txt'):
            with self.subTest(nombre=nombre):
                with self.assertRaises(ValueError):
                    self.almacen.leer(nombre)

    def test_escritura_reemplazo_atomico(self):
        self.almacen.guardar('estado.json', {'valor': 1})
        self.almacen.guardar('estado.json', {'valor': 2, 'texto': 'Árboles'})
        self.assertEqual(self.almacen.leer('estado.json')['texto'], 'Árboles')
        self.assertEqual(self.almacen.leer('estado.json')['valor'], 2)
        self.assertEqual(list(Path(self.tmp.name).glob('*.tmp')), [])

    def test_reemplazo_fallido_mantiene_original(self):
        self.almacen.guardar('estado.json', {'valor': 'anterior'})
        with patch('grace.archivos.os.replace', side_effect=OSError('fallo simulado')):
            with self.assertRaises(OSError):
                self.almacen.guardar('estado.json', {'valor': 'nuevo'})
        self.assertEqual(self.almacen.leer('estado.json')['valor'], 'anterior')
        self.assertEqual(list(Path(self.tmp.name).glob('*.tmp')), [])


class CasosServicio(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.servicio = ServicioGrace(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def plan(self):
        return self.servicio.crear_plan({'objetivo': 'Reconocer y recorrer una cola enlazada',
                                        'tema': 'Colas enlazadas', 'fecha': '2026-11-17'})

    def test_plan_no_publica_sin_aprobacion(self):
        plan = self.plan()
        base = len(self.servicio.actividades)
        for accion in ('publicar', 'aprobar', 'rechazar'):
            with self.subTest(accion=accion), self.assertRaises(ErrorValidacion):
                self.servicio.cambiar_estado_plan({'id':plan['id'], 'accion':accion})
        self.assertEqual(len(self.servicio.actividades), base)

    def test_edicion_exige_nueva_revision(self):
        plan = self.plan()
        self.servicio.cambiar_estado_plan({'id':plan['id'],'accion':'revisar'})
        cambio = self.servicio.editar_plan({'id':plan['id'], 'contenido':{
            'practica': 'Implementar la cola y verificar FIFO con un ejemplo'}})
        self.assertEqual(cambio['estado'], 'borrador')
        self.assertEqual(cambio['historial'][-1]['accion'], 'editar')
        self.servicio.cambiar_estado_plan({'id':plan['id'],'accion':'revisar'})
        self.servicio.cambiar_estado_plan({'id':plan['id'],'accion':'aprobar'})
        with self.assertRaises(ErrorValidacion):
            self.servicio.editar_plan({'id':plan['id'], 'contenido':{'apertura':'Cambio tardío'}})
        publicado = self.servicio.cambiar_estado_plan({'id':plan['id'],'accion':'publicar'})
        self.assertEqual(publicado['estado'], 'publicado')
        self.assertEqual(self.servicio.buscar_actividad(publicado['actividad_id'])['tema'], 'Colas enlazadas')

    def test_publicacion_reversible_en_memoria_si_falla_archivo(self):
        plan = self.plan()
        self.servicio.cambiar_estado_plan({'id':plan['id'],'accion':'revisar'})
        self.servicio.cambiar_estado_plan({'id':plan['id'],'accion':'aprobar'})
        cantidad = len(self.servicio.actividades)
        with patch.object(self.servicio.almacen, 'guardar', side_effect=OSError('disco lleno')):
            with self.assertRaises(OSError):
                self.servicio.cambiar_estado_plan({'id':plan['id'],'accion':'publicar'})
        self.assertEqual(len(self.servicio.actividades), cantidad)
        self.assertEqual(self.servicio.planes[-1]['estado'], 'aprobado')
        recuperado = ServicioGrace(self.tmp.name)
        self.assertEqual(recuperado.planes[-1]['estado'], 'aprobado')
        self.assertEqual(len(recuperado.actividades), cantidad)

    def test_cola_reversible_si_falla_guardado(self):
        anterior = self.servicio.cola.recorrer()
        with patch.object(self.servicio.almacen, 'guardar', side_effect=OSError('sin espacio')):
            with self.assertRaises(OSError):
                self.servicio.atender_siguiente()
        self.assertEqual(self.servicio.cola.recorrer(), anterior)
        self.assertEqual(self.servicio.atendidas, [])

    def test_estado_devuelve_copia_y_no_es_modificable_desde_fuera(self):
        copia = self.servicio.estado()
        copia['actividades'][0]['titulo'] = 'Manipulado'
        copia['planes'].append({'id': 12})
        self.assertNotEqual(self.servicio.actividades[0]['titulo'], 'Manipulado')
        self.assertEqual(self.servicio.planes, [])

    def test_bloqueo_ids_invalidos(self):
        for valor in (True, 1.5, '1.0', '-1', '1;DROP TABLE', None):
            with self.subTest(valor=valor), self.assertRaises(ErrorValidacion):
                self.servicio.buscar_actividad(valor)

    def test_validacion_fecha_estricta(self):
        for fecha in ('20261111', '2026-02-30', '', 'mañana'):
            with self.subTest(fecha=fecha), self.assertRaises(ErrorValidacion):
                self.servicio.crear_plan({'objetivo':'Comprender las estructuras de datos',
                                          'tema':'Listas','fecha':fecha})

    def test_estado_corrupto_no_reinicia_sin_pedir(self):
        ruta = Path(self.tmp.name)/'estado.json'
        ruta.write_text('{',encoding='utf-8')
        with self.assertRaises(ErrorDatos):
            ServicioGrace(self.tmp.name)
        self.assertEqual(ruta.read_text(encoding='utf-8'), '{')

    def test_archivo_parcial_migra_sin_borrar_contenido(self):
        with tempfile.TemporaryDirectory() as carpeta:
            actividades = [{'id': 55, 'institucion_id':INSTITUCION, 'curso_id':CURSO,
                            'titulo':'Prueba legacy','tema':'Grafos','fecha':'2026-11-07'}]
            Path(carpeta, 'actividades.json').write_text(json.dumps(actividades),encoding='utf-8')
            servicio = ServicioGrace(carpeta)
            self.assertEqual(servicio.buscar_actividad(55)['titulo'], 'Prueba legacy')
            self.assertTrue(Path(carpeta, 'estado.json').is_file())
            self.assertTrue(Path(carpeta, 'actividades.json').is_file())
            self.assertEqual(servicio.entregas, [])

    def test_solicitud_vacia_y_entrega_repetida(self):
        with self.assertRaises(ErrorValidacion):
            self.servicio.solicitar_ayuda({'estudiante_id':'e1','mensaje':'a'})
        self.servicio.registrar_entrega({'estudiante_id':'e3','actividad_id':101})
        with self.assertRaises(ErrorValidacion):
            self.servicio.registrar_entrega({'estudiante_id':'e3','actividad_id':101})

    def test_reinicio_explicito(self):
        self.plan()
        self.assertEqual(len(self.servicio.planes),1)
        self.servicio.reiniciar()
        self.assertEqual(len(self.servicio.planes),0)
        self.assertEqual(len(self.servicio.cola.recorrer()),2)

    def test_institucion_incorrecta_bloqueada(self):
        ruta = Path(self.tmp.name)/'estado.json'
        contenido=json.loads(ruta.read_text(encoding='utf-8'))
        contenido['institucion_id']='otro-campus'
        ruta.write_text(json.dumps(contenido),encoding='utf-8')
        with self.assertRaises(ErrorDatos):
            ServicioGrace(self.tmp.name)


if __name__ == '__main__':
    unittest.main()
