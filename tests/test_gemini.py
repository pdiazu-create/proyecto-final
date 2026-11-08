"""Verifica el contrato REST de Gemini sin red ni claves reales."""
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch
from urllib.error import HTTPError

from grace.ia import (ProveedorGemini, ProveedorConRespaldo, ProveedorReglas,
                      SYSTEM_MESSAGE, crear_proveedor)
from grace.servicio import ServicioGrace, CAMPOS_PLAN
from tests.test_ia import RespuestaFalsa
import diagnostico_ia


def respuesta(texto, fin='STOP'):
    return RespuestaFalsa({'candidates': [{
        'finishReason': fin, 'content': {'parts': [{'text': texto}]},
    }]})


class PruebasGemini(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.servicio = ServicioGrace(self.temp.name)
        self.contexto = self.servicio._contexto_ia('e1')

    def test_chat_usa_rest_cabecera_sistema_fijo_y_400_tokens(self):
        capturas = []
        def transporte(req, timeout):
            capturas.append((req, timeout))
            return respuesta('Hola, soy Grace.')
        api = ProveedorGemini('secreto-falso', transporte=transporte)
        resultado = api.responder_chat('hola', self.contexto)
        req, timeout = capturas[0]
        cuerpo = json.loads(req.data)
        self.assertEqual(resultado['origen'], 'IA')
        self.assertEqual(timeout, 10)
        self.assertIn(':generateContent', req.full_url)
        self.assertNotIn('secreto-falso', req.full_url + req.data.decode())
        self.assertEqual(req.get_header('X-goog-api-key'), 'secreto-falso')
        self.assertEqual(cuerpo['systemInstruction']['parts'][0]['text'], SYSTEM_MESSAGE)
        self.assertEqual(cuerpo['generationConfig']['maxOutputTokens'], 400)
        self.assertNotIn('store', cuerpo)  # Gemini no define ese parámetro de OpenAI.

    def test_plan_usa_json_700_tokens_y_solo_datos_del_curso(self):
        capturas = []
        campos = {k: 'Texto académico suficiente.' for k in CAMPOS_PLAN}
        def transporte(req, timeout):
            capturas.append(json.loads(req.data))
            return respuesta(json.dumps(campos))
        self.servicio.ia = ProveedorConRespaldo(
            ProveedorGemini('secreto-falso', transporte=transporte), ProveedorReglas())
        plan = self.servicio.crear_plan({
            'objetivo': 'Practicar listas con ejemplos sencillos.',
            'tema': 'Listas', 'fecha': '2026-11-20',
        })
        self.assertEqual(plan['estado'], 'borrador')
        self.assertEqual(plan['origen'], 'IA')
        configuracion = capturas[0]['generationConfig']
        self.assertEqual(configuracion['maxOutputTokens'], 700)
        self.assertEqual(configuracion['responseMimeType'], 'application/json')
        self.assertEqual(set(configuracion['responseJsonSchema']['required']), set(CAMPOS_PLAN))
        datos = json.loads(capturas[0]['contents'][0]['parts'][0]['text'])
        self.assertEqual(set(datos['datos_curso']), {
            'actividades','fechas_actividades','ruta_bfs','tamano_cola'})

    def test_errores_y_respuesta_truncada_usan_respaldo(self):
        for fallo in ('timeout', 'http', 'truncado', 'vacio', 'json'):
            def transporte(*_args, **_kwargs):
                if fallo == 'timeout':
                    raise TimeoutError()
                if fallo == 'http':
                    raise HTTPError('https://example.invalid', 429, 'secreto-falso', {}, io.BytesIO())
                if fallo == 'truncado':
                    return respuesta('texto parcial', 'MAX_TOKENS')
                if fallo == 'json':
                    return RespuestaFalsa([])
                return RespuestaFalsa({})
            with self.subTest(fallo=fallo), redirect_stderr(io.StringIO()) as log:
                proveedor = ProveedorConRespaldo(
                    ProveedorGemini('secreto-falso', transporte=transporte), ProveedorReglas())
                resultado = proveedor.responder_chat('hola', self.contexto)
                self.assertEqual(resultado['origen'], 'reglas (respaldo)')
                self.assertNotIn('secreto-falso', log.getvalue() + json.dumps(resultado))

    def test_sin_clave_no_llama_red_y_factory_elige_gemini(self):
        proveedor = crear_proveedor('api', clave='', proveedor='gemini',
                                    transporte=lambda *_a, **_k: self.fail('No debe llamar red'))
        self.assertIsInstance(proveedor.api, ProveedorGemini)
        with redirect_stderr(io.StringIO()):
            self.assertEqual(proveedor.responder_chat('hola', self.contexto)['origen'], 'reglas (respaldo)')

    def test_plan_invalido_rechazado_y_clave_no_se_devuelve(self):
        for texto in ('{}', 'secreto-falso', json.dumps({k: 'x'*401 for k in CAMPOS_PLAN})):
            with self.subTest(texto=texto[:10]), redirect_stderr(io.StringIO()):
                proveedor = ProveedorConRespaldo(ProveedorGemini(
                    'secreto-falso', transporte=lambda *_a, **_k: respuesta(texto)), ProveedorReglas())
                plan = proveedor.crear_plan('Objetivo válido para listas.', 'Listas', self.contexto, CAMPOS_PLAN)
                self.assertEqual(plan['origen'], 'reglas (respaldo)')
                self.assertNotIn('secreto-falso', json.dumps(plan))

    def test_diagnostico_gemini_no_contacta_openai_ni_revela_clave(self):
        with patch.dict(os.environ, {'GRACE_IA':'api', 'GRACE_IA_PROVEEDOR':'gemini',
                                     'GRACE_IA_KEY':'secreto-falso', 'GRACE_IA_MODEL':'gemini-flash-latest'}):
            def transporte(req, timeout):
                self.assertIn('generativelanguage.googleapis.com', req.full_url)
                return respuesta('Hola')
            with redirect_stdout(io.StringIO()) as salida:
                diagnostico_ia.diagnosticar(transporte=transporte)
            self.assertIn('Origen de Grace: IA', salida.getvalue())
            self.assertNotIn('secreto-falso', salida.getvalue())


if __name__ == '__main__':
    unittest.main()
