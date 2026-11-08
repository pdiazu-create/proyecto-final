"""Regresiones v0.4: árbol balanceado y pérdida de archivo de estado."""
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from grace.archivos import ErrorDatos
from grace.estructuras import ArbolBinarioBusqueda
from grace.servicio import MARCADOR_INICIO, ServicioGrace


class BalanceoArbol(unittest.TestCase):
    def test_arbol_vacio_y_un_elemento(self):
        arbol = ArbolBinarioBusqueda()
        self.assertEqual(arbol.altura(), 0)
        arbol.reconstruir_balanceado()
        self.assertIsNone(arbol.raiz)
        arbol.insertar(7, 'único')
        arbol.reconstruir_balanceado()
        self.assertEqual(arbol.altura(), 1)
        self.assertEqual(arbol.buscar(7), 'único')

    def test_reconstruir_arbol_degenerado_1800_elementos(self):
        arbol = ArbolBinarioBusqueda()
        for numero in range(1, 1801):
            arbol.insertar(numero, {'id': numero, 'prueba': 'conservado'})
        self.assertEqual(arbol.altura(), 1800)
        arbol.reconstruir_balanceado()
        self.assertEqual(arbol.tamano, 1800)
        self.assertLessEqual(arbol.altura(), 11)
        self.assertEqual([x['id'] for x in arbol.en_orden()], list(range(1, 1801)))
        self.assertEqual(arbol.buscar(1200), {'id': 1200, 'prueba': 'conservado'})
        self.assertIsNone(arbol.buscar(1801))
        arbol.insertar(1200, 'actualizado')
        self.assertEqual(arbol.tamano, 1800)
        self.assertEqual(arbol.buscar(1200), 'actualizado')

    def test_reconstruye_solo_si_necesario(self):
        arbol = ArbolBinarioBusqueda()
        for numero in (5, 3, 7, 1, 4, 6, 9):
            arbol.insertar(numero, numero)
        self.assertFalse(arbol.balancear_si_necesario())
        for numero in range(10, 35):
            arbol.insertar(numero, numero)
        self.assertTrue(arbol.balancear_si_necesario())
        self.assertLessEqual(arbol.altura(), 6)
        self.assertEqual(arbol.buscar(34), 34)


class EstadoYServicio(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ruta = Path(self.tmp.name)
        self.servicio = ServicioGrace(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def publicar(self):
        plan = self.servicio.crear_plan({
            'objetivo': 'Demostrar búsqueda y recorrido en Python',
            'tema': 'Árboles', 'fecha': '2026-11-20',
        })
        for accion in ('revisar', 'aprobar', 'publicar'):
            plan = self.servicio.cambiar_estado_plan({'id': plan['id'], 'accion': accion})
        return plan['actividad_id']

    def test_treinta_publicaciones_secuenciales_y_recarga(self):
        ids = [self.publicar() for _ in range(30)]
        self.assertEqual(len(set(ids)), 30)
        self.assertEqual(len(self.servicio.actividades), 37)
        self.assertLessEqual(self.servicio.arbol.altura(), self.servicio.arbol.tamano.bit_length() + 2)
        for identificador in ids:
            self.assertEqual(self.servicio.buscar_actividad(identificador)['id'], identificador)
        recargado = ServicioGrace(self.tmp.name)
        self.assertLessEqual(recargado.arbol.altura(), recargado.arbol.tamano.bit_length())
        self.assertEqual(len(recargado.planes), 30)
        self.assertEqual(recargado.estado()['version'], '0.4')
        self.assertEqual(json.loads((self.ruta / 'estado.json').read_text(encoding='utf-8'))['version'], 4)

    def test_reinicio_limpio_crea_semilla_y_marcador(self):
        self.assertTrue((self.ruta / 'estado.json').exists())
        self.assertTrue((self.ruta / MARCADOR_INICIO).exists())
        self.assertEqual(self.servicio.arbol.tamano, 7)

    def test_estado_borrado_no_se_regenera_silenciosamente(self):
        estado = self.ruta / 'estado.json'
        estado.unlink()
        with self.assertRaisesRegex(ErrorDatos, 'Falta estado.json'):
            ServicioGrace(self.tmp.name)
        self.assertFalse(estado.exists())
        self.assertTrue((self.ruta / MARCADOR_INICIO).exists())

    def test_estado_corrupto_conserva_bytes(self):
        estado = self.ruta / 'estado.json'
        estado.write_text('INVALIDO', encoding='utf-8')
        with self.assertRaises(ErrorDatos):
            ServicioGrace(self.tmp.name)
        self.assertEqual(estado.read_text(encoding='utf-8'), 'INVALIDO')

    def test_lee_estado_anterior_version_3_y_guarda_4(self):
        estado = self.ruta / 'estado.json'
        datos = json.loads(estado.read_text(encoding='utf-8'))
        datos['version'] = 3
        estado.write_text(json.dumps(datos, ensure_ascii=False), encoding='utf-8')
        migrado = ServicioGrace(self.tmp.name)
        self.assertEqual(migrado.estado()['version'], '0.4')
        migrado.solicitar_ayuda({'estudiante_id': 'e1', 'mensaje': 'Práctica de compatibilidad v3'})
        self.assertEqual(json.loads(estado.read_text(encoding='utf-8'))['version'], 4)

    def test_estado_sin_version_o_version_desconocida_es_rechazado(self):
        estado = self.ruta / 'estado.json'
        datos = json.loads(estado.read_text(encoding='utf-8'))
        for valor in (None, 5, '4', 4.0):
            with self.subTest(version=valor):
                estado.write_text(json.dumps({**datos, 'version': valor}), encoding='utf-8')
                with self.assertRaisesRegex(ErrorDatos, 'Versión de estado'):
                    ServicioGrace(self.tmp.name)

    def test_solicitudes_simultaneas_sin_ids_duplicados(self):
        def solicitud(i):
            return self.servicio.solicitar_ayuda({'estudiante_id': 'e1', 'mensaje': f'Ayuda concurrente {i}'})['id']
        with ThreadPoolExecutor(max_workers=8) as ejecutor:
            ids = list(ejecutor.map(solicitud, range(20)))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(self.servicio.cola.tamano, 22)
        recargado = ServicioGrace(self.tmp.name)
        self.assertEqual(recargado.cola.tamano, 22)


if __name__ == '__main__':
    unittest.main()
