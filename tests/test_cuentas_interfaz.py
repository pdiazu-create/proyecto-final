"""Regresión adicional de las cuentas; no sustituye pruebas de permisos HTTP."""
from pathlib import Path
import shutil
import subprocess
import unittest

RAIZ=Path(__file__).resolve().parents[1]

class CuentasInterfaz(unittest.TestCase):
    def test_acceso_sin_contrasena_fija_en_el_campo(self):
        html=(RAIZ/'web/index.html').read_text(encoding='utf-8')
        self.assertIn('id="acceso-clave"',html)
        self.assertIn('type="password" autocomplete="current-password"',html)
        self.assertNotIn('value="12345"',html)
        self.assertIn('src="/cuentas.js"',html)

    @unittest.skipUnless(shutil.which('node'),'Node opcional para verificar cliente')
    def test_sesion_y_perfiles_sin_red(self):
        p=subprocess.run(['node','tests/cuentas_cliente.test.cjs'],cwd=RAIZ,capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
