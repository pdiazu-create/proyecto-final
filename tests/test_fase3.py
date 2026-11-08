"""Fase 3: asistencia por lote, validaciones y una sola escritura."""
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import app
from grace.servicio import ErrorValidacion, ServicioGrace


def lote(fecha='2026-11-17'):
    return {'fecha': fecha, 'registros': [
        {'estudiante_id': 'e1', 'presente': True},
        {'estudiante_id': 'e2', 'presente': False},
        {'estudiante_id': 'e3', 'presente': True},
    ]}


class AsistenciaLote(unittest.TestCase):
    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.grace = ServicioGrace(self.carpeta.name)

    def tearDown(self):
        self.carpeta.cleanup()

    def test_lote_valido_una_escritura_y_formato_v4(self):
        with patch.object(self.grace.almacen, 'guardar', wraps=self.grace.almacen.guardar) as guardar:
            resultado = self.grace.registrar_asistencia_lote(lote())
        self.assertEqual(guardar.call_count, 1)
        self.assertEqual(resultado, {'fecha': '2026-11-17', 'registrados': 3})
        estado = self.grace.estado('e1')
        self.assertEqual(len(estado['asistencias']), 3)
        self.assertEqual(estado['resumen_asistencia']['clase']['porcentaje'], 66.7)
        self.assertEqual(estado['resumen_asistencia']['por_estudiante']['e2']['porcentaje'], 0.0)
        with open(self.grace.almacen.carpeta / 'estado.json', encoding='utf-8') as f:
            guardado = json.load(f)
        self.assertEqual(guardado['version'], 4)
        self.assertNotIn('resumen_asistencia', guardado)
        self.assertEqual(len(guardado['asistencias']), 3)

    def test_repetir_fecha_actualiza_sin_duplicados(self):
        self.grace.registrar_asistencia_lote(lote())
        actualizado = lote()
        actualizado['registros'][1]['presente'] = True
        self.grace.registrar_asistencia_lote(actualizado)
        self.assertEqual(len(self.grace.estado()['asistencias']), 3)
        self.assertEqual(self.grace.estado()['resumen_asistencia']['clase']['porcentaje'], 100.0)

    def test_estudiante_invalido_y_repetido_se_rechazan(self):
        datos = lote()
        datos['registros'][0]['estudiante_id'] = 'persona-ajena'
        with self.assertRaises(ErrorValidacion):
            self.grace.registrar_asistencia_lote(datos)
        datos = lote()
        datos['registros'][0]['estudiante_id'] = 'e2'
        with self.assertRaises(ErrorValidacion):
            self.grace.registrar_asistencia_lote(datos)
        self.assertEqual(self.grace.estado()['asistencias'], [])

    def test_fecha_invalida_y_booleanos_invalidos(self):
        for fecha in ('2026-02-30', '17-11-2026', ''):
            with self.subTest(fecha=fecha), self.assertRaises(ErrorValidacion):
                self.grace.registrar_asistencia_lote(lote(fecha))
        datos = lote()
        datos['registros'][0]['presente'] = 'true'
        with self.assertRaises(ErrorValidacion):
            self.grace.registrar_asistencia_lote(datos)

    def test_lote_incompleto_se_rechaza(self):
        datos = lote()
        datos['registros'].pop()
        with self.assertRaises(ErrorValidacion):
            self.grace.registrar_asistencia_lote(datos)

    def test_falla_guardado_revierte_memoria_y_archivo(self):
        anterior = self.grace.estado()['asistencias']
        archivo = (self.grace.almacen.carpeta / 'estado.json').read_bytes()
        with patch.object(self.grace.almacen, 'guardar', side_effect=OSError('Disco de prueba')):
            with self.assertRaises(OSError):
                self.grace.registrar_asistencia_lote(lote())
        self.assertEqual(self.grace.estado()['asistencias'], anterior)
        self.assertEqual((self.grace.almacen.carpeta / 'estado.json').read_bytes(), archivo)


class AsistenciaHTTP(unittest.TestCase):
    def test_endpoint_lote_y_error_400(self):
        with tempfile.TemporaryDirectory() as carpeta:
            original = app.SERVICIO
            servidor = None
            try:
                app.SERVICIO = ServicioGrace(carpeta)
                servidor = ThreadingHTTPServer(('127.0.0.1', 0), app.ManejadorGrace)
                hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
                hilo.start()
                url = f'http://127.0.0.1:{servidor.server_port}/api/asistencia/lote'
                for datos, esperado in ((lote(), 200), (lote('2026-02-30'), 400)):
                    peticion = Request(url, data=json.dumps(datos).encode('utf-8'),
                                       headers={'Content-Type': 'application/json'})
                    try:
                        with urlopen(peticion, timeout=3) as respuesta:
                            codigo = respuesta.status
                    except HTTPError as error:
                        codigo = error.code
                    self.assertEqual(codigo, esperado)
                self.assertEqual(len(app.SERVICIO.estado()['asistencias']), 3)
            finally:
                if servidor is not None:
                    servidor.shutdown()
                    servidor.server_close()
                    hilo.join(timeout=3)
                app.SERVICIO = original


if __name__ == '__main__':
    unittest.main()
