"""Pruebas HTTP de la web local y sus límites de demostración."""
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import app
from grace.servicio import ServicioGrace


class PruebaAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.carpeta = tempfile.TemporaryDirectory()
        cls.servicio_original = app.SERVICIO
        app.SERVICIO = ServicioGrace(cls.carpeta.name)
        cls.servidor = ThreadingHTTPServer(('127.0.0.1', 0), app.ManejadorGrace)
        cls.url = f'http://127.0.0.1:{cls.servidor.server_port}'
        cls.hilo = threading.Thread(target=cls.servidor.serve_forever, daemon=True)
        cls.hilo.start()

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()
        cls.hilo.join(timeout=3)
        app.SERVICIO = cls.servicio_original
        cls.carpeta.cleanup()

    def peticion(self, path, datos=None, cabeceras=None):
        cuerpo = None if datos is None else json.dumps(datos).encode('utf-8')
        cabeceras = cabeceras if cabeceras is not None else {'Content-Type': 'application/json'}
        req = Request(self.url + path, data=cuerpo, headers=cabeceras)
        try:
            with urlopen(req, timeout=5) as response:
                return response.status, response.headers, response.read()
        except HTTPError as error:
            return error.code, error.headers, error.read()

    def test_archivos_web_y_seguridad_basica(self):
        for ruta, prefijo in [('/', b'<!doctype html>'), ('/styles.css', b':root'),
                             ('/app.js', b"'use strict'"), ('/favicon.svg', b'<svg')]:
            with self.subTest(ruta=ruta):
                estado, headers, body = self.peticion(ruta)
                self.assertEqual(estado, 200)
                self.assertTrue(body.startswith(prefijo))
                self.assertIn("default-src 'self'", headers['Content-Security-Policy'])

    def test_api_salud_y_estado(self):
        estado, _, datos = self.peticion('/api/salud')
        self.assertEqual(estado, 200)
        self.assertEqual(json.loads(datos)['version'], '0.4')
        estado, _, datos = self.peticion('/api/estado')
        self.assertEqual(estado, 200)
        self.assertEqual(json.loads(datos)['estadisticas']['estudiantes'], 3)

    def test_api_flujo_de_aprobacion(self):
        _, _, cuerpo = self.peticion('/api/planes', {'objetivo': 'Aprender listas y verificar resultados',
                                                     'tema':'Listas', 'fecha':'2026-11-20'})
        plan = json.loads(cuerpo)['resultado']
        estado, _, _ = self.peticion('/api/planes/estado', {'id': plan['id'], 'accion': 'publicar'})
        self.assertEqual(estado, 400)
        for accion in ('revisar', 'aprobar', 'publicar'):
            codigo, _, respuesta = self.peticion('/api/planes/estado', {'id':plan['id'],'accion':accion})
            self.assertEqual(codigo, 200)
        self.assertIn('actividad_id', json.loads(respuesta)['resultado'])

    def test_sin_confirmacion_no_reinicia(self):
        codigo, _, cuerpo = self.peticion('/api/reiniciar', {})
        self.assertEqual(codigo, 400)
        self.assertIn('confirmar', json.loads(cuerpo)['error'])

    def test_host_y_origen_bloqueados(self):
        estado, _, _ = self.peticion('/api/estado', cabeceras={'Host':'campus-malicioso.example'})
        self.assertEqual(estado, 403)
        estado, _, _ = self.peticion('/api/planes', {'objetivo':'Plan para la clase'},
                                      cabeceras={'Content-Type':'application/json',
                                                'Origin':'https://otro.example'})
        self.assertEqual(estado, 403)

    def test_payload_grande_rechazado(self):
        codigo, _, _ = self.peticion('/api/planes', {'objetivo':'X'*9000},
                                     cabeceras={'Content-Type':'application/json'})
        self.assertEqual(codigo, 413)


if __name__ == '__main__':
    unittest.main()
