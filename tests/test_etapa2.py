import re
import tempfile
import unittest

from grace.asistente import responder
from grace.servicio import ServicioGrace


class PruebasEtapa2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open('web/index.html', encoding='utf-8') as archivo:
            cls.html = archivo.read()
        with open('web/app.js', encoding='utf-8') as archivo:
            cls.js = archivo.read()
        with open('web/styles.css', encoding='utf-8') as archivo:
            cls.css = archivo.read()

    def test_menu_tiene_paginas_reales_y_un_activo(self):
        paginas = re.findall(r'<button[^>]*class="nav-btn[^>]*data-page="([^"]+)"', self.html)
        principales = [p for p in paginas if p not in ('estructuras', 'asistente', 'docentes')]
        self.assertEqual(principales, ['inicio', 'cursos', 'calendario', 'asistencia'])
        for pagina in ('inicio', 'cursos', 'curso', 'calendario', 'asistencia'):
            self.assertIn(f'id="{pagina}"', self.html)
        self.assertEqual(len(re.findall(r'<button class="nav-btn active"', self.html)), 1)
        self.assertIn('aria-current', self.js)

    def test_curso_detalle_tiene_pestanas_y_datos_reales(self):
        self.assertIn('Programación Estructurada', self.html)
        self.assertIn('data-course-tab="actividades"', self.html)
        self.assertIn('data-course-tab="asistencia"', self.html)
        self.assertIn('data-course-tab="calendario"', self.html)
        self.assertIn('data-entregar', self.js)
        self.assertIn('renderizarCalendarios', self.js)
        self.assertNotIn('Estadística Aplicada', self.html)

    def test_panel_es_columna_y_no_fixed(self):
        self.assertIn('.assistant-dock{grid-column:2', self.css)
        self.assertIn('position:sticky', self.css)
        self.assertIn('assistant-dock.drawer-open', self.css)
        self.assertNotIn('assistant-dock{position:fixed', self.css)

    def test_intenciones_rapidas_de_reglas_son_utiles(self):
        with tempfile.TemporaryDirectory() as carpeta:
            servicio = ServicioGrace(carpeta)
            contexto = servicio._contexto_ia('e1')
            for mensaje in ('Resume esta semana', 'Organiza mis tareas', 'Explícame Listas'):
                respuesta = responder(
                    mensaje, contexto['rol'], contexto['actividades_interno'],
                    contexto['entregas_interno'], contexto['cola_interna'],
                    contexto['estudiante_id'], asistencias=contexto['asistencias_interno'],
                    grafo=contexto['grafo_interno'], temas=contexto['temas_interno'])
                self.assertIn('Fuente:', respuesta)
                self.assertNotIn('No puedo ayudarte', respuesta)

    def test_panel_conecta_botones_campo_origen_carga_y_error(self):
        self.assertIn("enviarChat(b.dataset.question, b.closest('.assistant-dock') ? 'assistant-messages' : 'chat')", self.js)
        self.assertIn("enviarChat(m,'assistant-messages')", self.js)
        self.assertIn('assistant-status', self.html)
        self.assertIn('Error al consultar', self.js)
        self.assertIn('Fuente: ${fuente}', self.js)


if __name__ == '__main__':
    unittest.main()
