import io
import json
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from urllib.error import HTTPError

import diagnostico_ia
from grace.ia import ProveedorGemini, DEFAULT_GEMINI_MODEL
from tests.test_gemini import respuesta


class PruebasGeminiLite(unittest.TestCase):
    def test_flash_lite_tiene_razonamiento_minimo(self):
        capturada = {}
        def transporte(req, timeout):
            capturada.update(json.loads(req.data))
            self.assertIn('gemini-3.5-flash-lite:generateContent', req.full_url)
            return respuesta('Hola')
        proveedor = ProveedorGemini('clave-ficticia', transporte=transporte)
        self.assertEqual(DEFAULT_GEMINI_MODEL, 'gemini-3.5-flash-lite')
        self.assertEqual(proveedor.responder_chat('hola', {'publico':{}})['origen'], 'IA')
        self.assertEqual(capturada['generationConfig']['thinkingConfig'], {'thinkingLevel':'minimal'})
        self.assertEqual(capturada['generationConfig']['maxOutputTokens'], 400)

    def test_otro_modelo_no_recibe_parametros_especificos_de_lite(self):
        capturada = {}
        def transporte(req, timeout):
            capturada.update(json.loads(req.data))
            return respuesta('Hola')
        ProveedorGemini('clave-ficticia', modelo='gemini-flash-latest',
                        transporte=transporte).responder_chat('hola', {'publico':{}})
        self.assertNotIn('thinkingConfig', capturada['generationConfig'])

    def test_diagnostico_503_informa_sobrecarga_sin_clave(self):
        def transporte(*_args, **_kwargs):
            raise HTTPError('https://example.invalid', 503, 'mensaje privado', {}, io.BytesIO())
        with patch.dict(os.environ, {'GRACE_IA':'api','GRACE_IA_PROVEEDOR':'gemini',
                'GRACE_IA_KEY':'clave-ficticia','GRACE_IA_MODEL':'gemini-3.5-flash-lite'}):
            with redirect_stdout(io.StringIO()) as salida:
                diagnostico_ia.diagnosticar(transporte=transporte)
        self.assertIn('HTTP: 503', salida.getvalue())
        self.assertIn('sobrecargado', salida.getvalue())
        self.assertNotIn('clave-ficticia', salida.getvalue())
        self.assertNotIn('mensaje privado', salida.getvalue())


if __name__ == '__main__':
    unittest.main()
