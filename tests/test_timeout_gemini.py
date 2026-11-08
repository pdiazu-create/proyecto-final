import os
import unittest
from unittest.mock import patch
from grace.ia import ProveedorGemini, ProveedorAPI
from tests.test_gemini import respuesta


class PruebasTimeoutGemini(unittest.TestCase):
    def test_gemini_envia_timeout_configurado_al_transporte(self):
        capturados = []
        def transporte(req, timeout):
            capturados.append(timeout)
            return respuesta('Hola')
        with patch.dict(os.environ, {'GRACE_IA_TIMEOUT':'30'}):
            api = ProveedorGemini('clave-falsa', transporte=transporte)
            api.responder_chat('hola', {'publico':{}})
        self.assertEqual(capturados, [30])

    def test_timeout_gemini_es_acotado_y_valida_configuracion(self):
        for valor, esperado in [('invalido',10), ('-3',10), ('99999',60)]:
            with self.subTest(valor=valor), patch.dict(os.environ, {'GRACE_IA_TIMEOUT':valor}):
                self.assertEqual(ProveedorGemini('clave-falsa').timeout_seconds, esperado)

    def test_openai_conserva_timeout_diez(self):
        capturados = []
        from tests.test_ia import RespuestaFalsa
        def transporte(req, timeout):
            capturados.append(timeout)
            return RespuestaFalsa({'output_text':'Hola'})
        with patch.dict(os.environ, {'GRACE_IA_TIMEOUT':'30'}):
            ProveedorAPI('clave-falsa', transporte=transporte).responder_chat('hola', {'publico':{}})
        self.assertEqual(capturados, [10])


if __name__ == '__main__':
    unittest.main()
