import io
import json
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout
from urllib.error import HTTPError

import diagnostico_ia
from grace.ia import ErrorIA, ProveedorAPI, ProveedorConRespaldo, ProveedorReglas, modo_ia


class RespuestaFalsa:
    status = 200

    def __init__(self, datos):
        self.datos = json.dumps(datos).encode('utf-8')

    def read(self, _limite=-1):
        return self.datos

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def close(self):
        pass


class PruebasEtapa1(unittest.TestCase):
    def setUp(self):
        self.entorno = {k: os.environ.get(k) for k in ('GRACE_IA', 'GRACE_IA_KEY', 'GRACE_IA_MODEL')}

    def tearDown(self):
        for clave, valor in self.entorno.items():
            if valor is None:
                os.environ.pop(clave, None)
            else:
                os.environ[clave] = valor

    def test_modos_sin_exponer_clave(self):
        os.environ['GRACE_IA'] = 'reglas'
        os.environ.pop('GRACE_IA_KEY', None)
        self.assertEqual(modo_ia(), 'reglas')
        os.environ['GRACE_IA'] = 'api'
        self.assertEqual(modo_ia(), 'api_sin_clave')
        os.environ['GRACE_IA_KEY'] = 'clave-falsa-no-real'
        self.assertEqual(modo_ia(), 'api')

    def test_etiqueta_conserva_cada_origen(self):
        for origen in ('IA', 'reglas', 'reglas (respaldo)'):
            self.assertEqual(origen, origen)
        with open('web/app.js', encoding='utf-8') as archivo:
            javascript = archivo.read()
        self.assertIn("const fuente = r.origen || 'reglas';", javascript)
        self.assertNotIn("r.origen === 'IA' ? 'IA' : 'reglas'", javascript)

    def test_error_http_registra_solo_estado_y_codigo(self):
        cuerpo = io.BytesIO(json.dumps({'error': {'type': 'invalid_request_error',
                                                   'code': 'invalid_api_key',
                                                   'message': 'secreto y usuario'}}).encode())
        api = ProveedorAPI('CLAVE-NUNCA-IMPRIMIR', transporte=lambda *_a, **_k: (_ for _ in ()).throw(
            HTTPError('https://example.invalid', 401, 'no', None, cuerpo)))
        proveedor = ProveedorConRespaldo(api, ProveedorReglas())
        salida = io.StringIO()
        with redirect_stderr(salida):
            proveedor.responder_chat('mensaje privado', diagnostico_ia._contexto_prueba())
        self.assertIn('HTTP 401', salida.getvalue())
        self.assertIn('error.code=invalid_api_key', salida.getvalue())
        self.assertNotIn('CLAVE-NUNCA-IMPRIMIR', salida.getvalue())
        self.assertNotIn('mensaje privado', salida.getvalue())
        self.assertNotIn('secreto y usuario', salida.getvalue())

    def test_diagnostico_con_transporte_falso_no_imprime_clave(self):
        os.environ['GRACE_IA'] = 'api'
        os.environ['GRACE_IA_KEY'] = 'CLAVE-FALSA-NUNCA-IMPRIMIR'
        os.environ['GRACE_IA_MODEL'] = 'modelo-prueba'
        salida = io.StringIO()
        with redirect_stdout(salida):
            diagnostico_ia.diagnosticar(
                transporte=lambda *_a, **_k: RespuestaFalsa({'output_text': 'ok'}))
        texto = salida.getvalue()
        self.assertIn('Modo: api', texto)
        self.assertIn('Clave configurada: sí; longitud:', texto)
        self.assertIn('HTTP: 200', texto)
        self.assertIn('Origen de Grace: IA', texto)
        self.assertNotIn('CLAVE-FALSA-NUNCA-IMPRIMIR', texto)


if __name__ == '__main__':
    unittest.main()
