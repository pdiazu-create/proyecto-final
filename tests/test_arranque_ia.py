import io
import tempfile
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

import app
from grace.ia import ErrorIA, ProveedorConRespaldo, ProveedorReglas
from grace.servicio import ServicioGrace


class PruebasArranqueIA(unittest.TestCase):
    def test_servidor_no_permite_segunda_instancia(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        with patch('grace.servicio.crear_proveedor', return_value=ProveedorReglas()):
            servicio = ServicioGrace(temporal.name)
        primero = app.ServidorGrace(('127.0.0.1', 0), app.ManejadorGrace, servicio=servicio)
        self.addCleanup(primero.server_close)
        with self.assertRaises(OSError):
            segundo = app.ServidorGrace(primero.server_address, app.ManejadorGrace, servicio=servicio)
            segundo.server_close()

    def test_respaldo_informa_http_sin_exponer_detalles(self):
        class API:
            def responder_chat(self, *_):
                raise ErrorIA('error_http', 429, 'SECRETO-NO-EXPOSICION')
        class Reglas:
            def responder_chat(self, *_):
                return {'respuesta': 'Hola', 'origen':'reglas'}
        with redirect_stderr(io.StringIO()):
            resultado = ProveedorConRespaldo(API(), Reglas()).responder_chat('hola', {})
        self.assertEqual(resultado['estado_http'], 429)
        self.assertIn('cuota', resultado['aviso'])
        self.assertNotIn('SECRETO', str(resultado))

    def test_diagnostico_no_expone_errores_arbitrarios(self):
        resultado = ProveedorConRespaldo._diagnostico_publico(ValueError('clave privada'))
        self.assertNotIn('clave privada', str(resultado))


if __name__ == '__main__':
    unittest.main()
