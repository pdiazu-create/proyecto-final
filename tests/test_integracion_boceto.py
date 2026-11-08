"""Tres pruebas nuevas que completan cobertura de integración sin alterar las existentes.

Recuento veraz: 113 originales + 12 boceto + estas 3 = 128 pruebas de Python.
"""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from grace.servicio import ServicioGrace

RAIZ = Path(__file__).resolve().parents[1]


class PruebasIntegracionBoceto(unittest.TestCase):
    def test_catalogo_no_se_envia_como_contexto_real_a_ia(self):
        """El asistente solo recibe el contexto real del prototipo del servicio."""
        with tempfile.TemporaryDirectory() as temporal:
            servicio = ServicioGrace(temporal)
            contexto = json.dumps(servicio._contexto_ia('e1'), ensure_ascii=False, default=str)
            for tema in ('Introducción a la lógica', 'Comunicación académica',
                         'Matemática básica', 'A-101', 'B-205', 'C-302'):
                with self.subTest(dato=tema):
                    self.assertNotIn(tema, contexto)

    def test_recursos_nuevos_son_locales_y_sin_scripts_en_linea(self):
        """Los nuevos archivos mantienen la política sin CDN y el catálogo es solo lectura."""
        import app
        html = (RAIZ / 'web' / 'index.html').read_text(encoding='utf-8')
        self.assertEqual(app.ARCHIVOS['/estudiante'][0], 'index.html')
        self.assertEqual(app.ARCHIVOS['/profesor'][0], 'index.html')
        for nombre in ('catalogo_demo.js', 'horario.js'):
            self.assertIn(f'<script src="/{nombre}" defer></script>', html)
            self.assertEqual(app.ARCHIVOS['/' + nombre][0], nombre)
        self.assertNotIn('https://', html)
        self.assertNotIn('http://', html)
        self.assertNotIn('style="', html)
        self.assertNotIn('onload=', html)

    @unittest.skipUnless(shutil.which('node'), 'Node necesario para verificar franjas y hora local')
    def test_franjas_contiguas_y_cambio_de_horario_de_verano(self):
        """Una clase que termina al iniciar otra no se considera solapada; DST mantiene fecha."""
        codigo = r"""
        const h=require('./web/horario.js');
        const a=[{id:'a',horarios:[{dia:0,inicio:'09:00',fin:'10:00',edificio:'A',piso:1,aula:'A-101'}]}];
        const b=[{cursoId:'b',dia:0,inicio:'10:00',fin:'11:00',edificio:'A',piso:1,aula:'A-101'}];
        const fecha=h.lunesDeSemana(new Date(2027,2,14));
        console.log(JSON.stringify({errores:h.validarHorarios(a,b), lunes:h.fechaLocal(fecha), viernes:h.fechaLocal(h.sumarDiasLocales(fecha,4))}));
        """
        import os
        for zona in ('America/Managua', 'America/New_York'):
            with self.subTest(zona=zona):
                respuesta = subprocess.run(['node', '-e', codigo], cwd=RAIZ,
                                           env={**os.environ, 'TZ': zona}, check=True,
                                           capture_output=True, text=True)
                self.assertEqual(json.loads(respuesta.stdout), {
                    'errores': [], 'lunes': '2027-03-08', 'viernes': '2027-03-12'})
