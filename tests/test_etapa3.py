import re
import tempfile
import unittest

from grace.asistente import responder
from grace.servicio import ServicioGrace


class PruebasEtapa3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open('web/styles.css', encoding='utf-8') as archivo:
            cls.css = archivo.read()
        with open('web/index.html', encoding='utf-8') as archivo:
            cls.html = archivo.read()
        with open('web/app.js', encoding='utf-8') as archivo:
            cls.js = archivo.read()

    def test_tamanos_efectivos_no_bajan_de_12px(self):
        css_final = self.css.split('/* Última capa tipográfica:', 1)[1]
        selectores = (
            '.response-source', '.course-badge', '.assistant-dock-head small',
            '.journey-card p', '.brand small', '.progress-meta', '.switch-row',
            '.assistant-dock-body>p', '.tag', '.micro', '.helper-note',
            '.quick-chips button', 'footer',
        )
        for selector in selectores:
            with self.subTest(selector=selector):
                self.assertIn(selector, css_final)
        self.assertIn('font-size:12px !important', css_final)
        self.assertFalse(re.search(r'font-size\s*:\s*(?:[0-9]|1[01])px\s*!important', css_final))

    def test_explicar_tema_usa_selector_en_panel_y_chat(self):
        self.assertIn('id="assistant-topic"', self.html)
        self.assertIn('id="chat-topic"', self.html)
        self.assertIn("mensaje = `Explícame ${selector?.value || 'Listas'}`", self.js)

    def test_explicar_tema_concreto_funciona_con_reglas(self):
        with tempfile.TemporaryDirectory() as carpeta:
            servicio = ServicioGrace(carpeta)
            contexto = servicio._contexto_ia('e1')
            respuesta = responder(
                'Explícame Listas', contexto['rol'], contexto['actividades_interno'],
                contexto['entregas_interno'], contexto['cola_interna'],
                contexto['estudiante_id'], asistencias=contexto['asistencias_interno'],
                grafo=contexto['grafo_interno'], temas=contexto['temas_interno'])
        self.assertIn('Listas:', respuesta)
        self.assertIn('Fuente:', respuesta)


if __name__ == '__main__':
    unittest.main()
