"""Requisitos del boceto final; solo se añaden pruebas, nunca se tocan las 70 originales."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import urlopen

import app
from grace.servicio import ServicioGrace

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / 'web'


def ejecutar_js(codigo, tz='America/Managua'):
    env = dict(os.environ, TZ=tz)
    resultado = subprocess.run(['node', '-e', codigo], cwd=RAIZ, env=env,
                               check=True, capture_output=True, text=True)
    return resultado.stdout.strip()


class TestBocetoEstatico(unittest.TestCase):
    def test_catalogo_separado_de_datos_reales(self):
        catalogo = (WEB / 'catalogo_demo.js').read_text(encoding='utf-8')
        self.assertIn('const CATALOGO_DEMOSTRACION', catalogo)
        self.assertIn('demostracion:true', catalogo)
        self.assertIn('HORARIO_CURSO_PRINCIPAL = Object.freeze([])', catalogo)
        self.assertNotIn('fetch(', catalogo)
        self.assertNotIn('estado.json', (WEB / 'horario.js').read_text(encoding='utf-8'))

    def test_vistas_por_rol_y_fichas_sin_menu_adicional(self):
        html = (WEB / 'index.html').read_text(encoding='utf-8')
        self.assertIn('href="/estudiante"', html)
        self.assertIn('href="/profesor"', html)
        self.assertIn('id="mis-clases"', html)
        self.assertIn('id="horario"', html)
        self.assertIn('id="ficha-curso"', html)
        self.assertIn('data-only="estudiante"', html)
        self.assertIn('data-only="profesor"', html)
        self.assertNotIn('data-page="ficha-curso"', html)
        self.assertIn('No hay horario semanal verificado', (WEB / 'app.js').read_text(encoding='utf-8'))

    def test_tabs_semanticos_y_dias_espanol(self):
        html = (WEB / 'index.html').read_text(encoding='utf-8')
        js = (WEB / 'horario.js').read_text(encoding='utf-8')
        self.assertIn('role="tablist"', html)
        self.assertIn('role="tabpanel"', html)
        self.assertIn('aria-controls="panel-semana"', html)
        self.assertIn('aria-controls="panel-actividades"', html)
        self.assertIn('Volver a hoy', html)
        self.assertIn("'Lunes','Martes','Miércoles','Jueves','Viernes'", js)

    def test_sin_fecha_utc_en_web(self):
        self.assertNotIn('toISOString', (WEB / 'app.js').read_text(encoding='utf-8'))
        self.assertNotIn('toISOString', (WEB / 'horario.js').read_text(encoding='utf-8'))

    def test_accesibilidad_horario_movil(self):
        css = (WEB / 'styles.css').read_text(encoding='utf-8')
        js = (WEB / 'app.js').read_text(encoding='utf-8')
        self.assertIn('@media(max-width:950px)', css)
        self.assertIn('.horario-movil{display:block}', css)
        self.assertIn('<caption>', js)
        self.assertIn('scope="col"', js)
        self.assertIn('scope="row"', js)
        self.assertIn('data-curso=', js)
        self.assertIn('etiquetaDemo()', js)
        for color in ('curso-celeste', 'curso-turquesa', 'curso-azul'):
            self.assertIn(color, css)


@unittest.skipUnless(shutil.which('node'), 'Pruebas de JS requieren Node, opcional para ejecutar Grace')
class TestFechasYHorariosJS(unittest.TestCase):
    def test_semanas_inyectables_en_husos_distintos(self):
        codigo = """const h=require('./web/horario.js');
          const sab=new Date(2026,10,7),dom=new Date(2026,10,8);
          const l=h.lunesDeSemana(dom);
          console.log(JSON.stringify([h.fechaLocal(h.lunesDeSemana(sab)),h.fechaLocal(l),
              h.fechaLocal(h.sumarDiasLocales(l,4)),h.fechaLocal(h.sumarDiasLocales(l,7))]));"""
        esperado='["2026-11-02","2026-11-02","2026-11-06","2026-11-09"]'
        for zona in ('America/Managua', 'Pacific/Auckland', 'America/Los_Angeles'):
            with self.subTest(zona=zona):
                self.assertEqual(ejecutar_js(codigo, zona), esperado)

    def test_cambio_de_ano_y_mes(self):
        codigo = """const h=require('./web/horario.js');
          const d=h.lunesDeSemana(new Date(2027,0,1));
          console.log(JSON.stringify([h.fechaLocal(d),h.fechaLocal(h.sumarDiasLocales(d,4))]));"""
        self.assertEqual(ejecutar_js(codigo), '["2026-12-28","2027-01-01"]')

    def test_catalogo_sin_solapes_y_aulas_validas(self):
        codigo = """const vm=require('vm'),fs=require('fs'),h=require('./web/horario.js');
          let c={};vm.runInNewContext(fs.readFileSync('web/catalogo_demo.js','utf8')+
          '\\n;globalThis.cat=CATALOGO_DEMOSTRACION;globalThis.base=HORARIO_CURSO_PRINCIPAL;',c);
          console.log(JSON.stringify(h.validarHorarios(c.cat,c.base)));"""
        self.assertEqual(ejecutar_js(codigo), '[]')

    def test_conflicto_entre_curso_base_y_demostracion(self):
        codigo = """const h=require('./web/horario.js'); const base=[{cursoId:'principal',dia:0,inicio:'07:30',fin:'08:00',edificio:'A',piso:1,aula:'A-101'}];
          const cat=[{id:'otro',horarios:[{dia:0,inicio:'07:00',fin:'08:30',edificio:'A',piso:1,aula:'A-101'}]}];
          console.log(JSON.stringify(h.validarHorarios(cat,base)));"""
        r=json.loads(ejecutar_js(codigo))
        self.assertTrue(any('Solape' in error for error in r))
        self.assertTrue(any('Aula repetida' in error for error in r))

    def test_aula_con_piso_incorrecto(self):
        codigo = """const h=require('./web/horario.js'); console.log(JSON.stringify(h.validarHorarios(
          [{id:'incorrecto',horarios:[{dia:2,inicio:'12:00',fin:'13:00',edificio:'C',piso:1,aula:'C-302'}]}])));"""
        self.assertIn('incoherente', ejecutar_js(codigo))


class TestLecturaHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.anterior = app.SERVICIO
        app.SERVICIO = ServicioGrace(cls.temp.name)
        cls.servidor = ThreadingHTTPServer(('127.0.0.1', 0), app.ManejadorGrace)
        cls.url = f'http://127.0.0.1:{cls.servidor.server_port}'
        cls.hilo = threading.Thread(target=cls.servidor.serve_forever, daemon=True)
        cls.hilo.start()

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()
        cls.hilo.join(timeout=3)
        app.SERVICIO = cls.anterior
        cls.temp.cleanup()

    def test_portales_y_archivos_locales(self):
        for ruta in ('/profesor', '/estudiante', '/horario.js', '/catalogo_demo.js'):
            with self.subTest(ruta=ruta):
                with urlopen(self.url+ruta) as respuesta:
                    self.assertEqual(respuesta.status, 200)
                    self.assertIn("script-src 'self'", respuesta.headers['Content-Security-Policy'])

    def test_navegacion_y_consultas_no_escriben_estado_json(self):
        archivo=Path(self.temp.name)/'estado.json'
        antes=archivo.read_bytes()
        for ruta in ('/', '/profesor', '/estudiante', '/horario.js', '/catalogo_demo.js',
                     '/api/estado?estudiante=e1', '/api/buscar?id=1'):
            with urlopen(self.url+ruta) as respuesta:
                self.assertEqual(respuesta.status, 200)
        self.assertEqual(archivo.read_bytes(), antes)


if __name__ == '__main__':
    unittest.main()
