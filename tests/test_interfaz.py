"""Pruebas de la interfaz web: seguridad (CSP), navegación, contraste y foco.

Estas pruebas leen los archivos de web/ como texto. No abren un navegador,
así que NO reemplazan la revisión visual en Chrome o Edge.
"""
import re
import unittest
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / 'web'


def _leer(nombre):
    return (WEB / nombre).read_text(encoding='utf-8')


def _luminancia(color):
    color = color.lstrip('#')
    canales = []
    for i in (0, 2, 4):
        c = int(color[i:i + 2], 16) / 255
        canales.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * canales[0] + 0.7152 * canales[1] + 0.0722 * canales[2]


def contraste(a, b):
    """Razón de contraste WCAG entre dos colores hexadecimales."""
    la, lb = sorted((_luminancia(a), _luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _ultima_variable(css, nombre):
    """Valor final de una variable CSS (la última definición es la que rige)."""
    valores = re.findall(r'--' + nombre + r'\s*:\s*(#[0-9a-fA-F]{6})', css)
    return valores[-1]


class PruebasInterfaz(unittest.TestCase):
    def test_no_hay_scripts_o_estilos_en_linea(self):
        html = _leer('index.html')
        self.assertNotIn('style="', html)
        self.assertNotIn('<style', html)
        self.assertNotRegex(html, r'\son\w+\s*=')  # onclick, onload...
        for etiqueta in re.findall(r'<script[^>]*>', html):
            self.assertIn('src=', etiqueta)  # solo scripts de archivo propio

    def test_tarjetas_son_botones_con_destino_y_foco(self):
        html = _leer('index.html')
        tarjetas = re.findall(r'<button[^>]*class="journey-card"[^>]*>', html)
        self.assertEqual(len(tarjetas), 4)
        for tarjeta in tarjetas:
            self.assertIn('type="button"', tarjeta)
            self.assertIn('data-go=', tarjeta)
            self.assertIn('data-focus=', tarjeta)
        self.assertIn('[data-go]', _leer('app.js'))

    def test_colores_representativos_alcanzan_contraste_aa(self):
        css = _leer('styles.css')
        muted = _ultima_variable(css, 'muted')
        pares = [
            ('texto principal sobre blanco', _ultima_variable(css, 'ink'), '#ffffff'),
            ('texto secundario sobre blanco', muted, '#ffffff'),
            ('texto secundario sobre el menú lateral', muted, _ultima_variable(css, 'sidebar')),
            ('texto blanco sobre botón principal', '#ffffff', _ultima_variable(css, 'primary')),
        ]
        for nombre, texto, fondo in pares:
            with self.subTest(nombre):
                self.assertGreaterEqual(contraste(texto, fondo), 4.5)
        # El contorno de foco es un elemento gráfico: mínimo 3:1.
        self.assertGreaterEqual(contraste(_ultima_variable(css, 'focus'), '#ffffff'), 3.0)

    def test_movimiento_reducido_declara_preferencia(self):
        css = _leer('styles.css')
        self.assertRegex(css, r'@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)')
        self.assertIn('animation:none!important', css)
        self.assertIn('transition:none!important', css)

    def test_animaciones_y_transiciones_solo_opacidad_y_transformacion(self):
        css = _leer('styles.css')
        # Solo animamos propiedades compuestas por el navegador: opacity y transform.
        transiciones = re.findall(r'\btransition(?:-property)?\s*:\s*([^;}]+)', css)
        self.assertTrue(transiciones)
        for valor in transiciones:
            if valor.strip().lower() == 'none!important':
                continue
            for parte in valor.split(','):
                propiedad = parte.strip().split()[0]
                self.assertIn(propiedad, ('opacity', 'transform'))
        self.assertIn('@keyframes grace-view-enter', css)
        self.assertIn('@keyframes grace-card-enter', css)
        self.assertIn('@keyframes preview-draft', css)
        self.assertIn('@keyframes preview-approved', css)
        self.assertIn('@keyframes preview-published', css)

    def test_estilos_de_foco_y_fuentes_locales(self):
        css = _leer('styles.css')
        self.assertIn(':focus-visible', css)
        self.assertRegex(css, r':focus-visible[^{]*\{[^}]*outline')
        self.assertNotIn('@import', css)
        self.assertNotRegex(css, r'url\(\s*["\']?https?:')
        self.assertNotIn('fonts.googleapis', _leer('index.html'))


if __name__ == '__main__':
    unittest.main()
