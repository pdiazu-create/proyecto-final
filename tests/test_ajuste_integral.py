"""Regresión del recorrido unificado y las sesiones; no modifica pruebas previas."""
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
import unittest

RAIZ=Path(__file__).resolve().parents[1]

class Etiquetas(HTMLParser):
    def __init__(self):
        super().__init__();self.tags=[]
    def handle_starttag(self,tag,attrs):self.tags.append((tag,attrs))

class AjusteIntegral(unittest.TestCase):
    def test_html_sin_atributos_ni_ids_duplicados(self):
        p=Etiquetas();p.feed((RAIZ/'web/index.html').read_text(encoding='utf-8'));ids=[]
        for t,a in p.tags:
            keys=[k for k,_ in a];self.assertEqual(len(keys),len(set(keys)),(t,keys))
            if 'id' in keys:ids.append(dict(a)['id'])
        self.assertEqual(len(ids),len(set(ids)))

    def test_menu_movil_respeta_roles_y_no_esconde_docencia(self):
        p=Etiquetas();p.feed((RAIZ/'web/index.html').read_text(encoding='utf-8'))
        botones={dict(a).get('data-page'):dict(a) for t,a in p.tags if t=='button' and 'mobile-nav-btn' in dict(a).get('class','').split()}
        for pagina in ('docentes','estructuras'):self.assertIn('teacher-nav',botones[pagina]['class'].split())
        self.assertIn('student-nav',botones['asistencia']['class'].split())
        self.assertEqual(set(botones), {'inicio', 'cursos', 'calendario', 'asistencia',
                                        'docentes', 'estructuras', 'asistente', 'comunidad'})
        self.assertIn('comunidad-nav', botones['comunidad']['class'].split())
        self.assertNotIn('teacher-nav', botones['comunidad']['class'].split())
        self.assertNotIn('student-nav', botones['comunidad']['class'].split())
        # No ocultar duplicados al construir el diccionario por página.
        self.assertEqual(sum(t == 'button' and 'mobile-nav-btn' in dict(a).get('class', '').split()
                             for t, a in p.tags), len(botones))

    @unittest.skipUnless(shutil.which('node'),'Node solo es necesario para verificar el cliente')
    def test_recorrido_y_aislamiento_con_datos_falsos(self):
        p=subprocess.run(['node','tests/ajuste_integral.test.cjs'],cwd=RAIZ,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
