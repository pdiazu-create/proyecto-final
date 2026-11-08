import io
import json
import socket
import ssl
import tempfile
import unittest
from contextlib import redirect_stderr
from urllib.error import URLError

from grace.ia import ProveedorGemini, ProveedorReglas, ProveedorConRespaldo
from grace.servicio import ServicioGrace


class PruebasRedGemini(unittest.TestCase):
    def test_causas_distintas_sin_filtrar_mensajes_privados(self):
        with tempfile.TemporaryDirectory() as carpeta:
            contexto = ServicioGrace(carpeta)._contexto_ia('e1')
            casos = [
                (TimeoutError('SECRETO'), 'timeout'),
                (URLError(socket.gaierror(-2, 'SECRETO')), 'dns'),
                (URLError(ssl.SSLCertVerificationError(1, 'SECRETO')), 'certificado_tls'),
                (ConnectionResetError('SECRETO'), 'conexion_interrumpida'),
            ]
            for error, codigo in casos:
                with self.subTest(causa=codigo):
                    def transporte(*_args, **_kwargs):
                        raise error
                    proveedor = ProveedorConRespaldo(
                        ProveedorGemini('CLAVE-DE-PRUEBA', transporte=transporte), ProveedorReglas())
                    with redirect_stderr(io.StringIO()) as log:
                        r = proveedor.responder_chat('hola', contexto)
                    self.assertIn(f'({codigo})', log.getvalue())
                    self.assertEqual(r['origen'], 'reglas (respaldo)')
                    self.assertNotIn('SECRETO', log.getvalue() + json.dumps(r))
                    self.assertNotIn('CLAVE-DE-PRUEBA', log.getvalue() + json.dumps(r))


if __name__ == '__main__':
    unittest.main()
