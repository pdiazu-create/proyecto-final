"""Fase 5: detección clara de pérdida del estado al arrancar."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]


class ArranqueSeguro(unittest.TestCase):
    def test_falta_estado_despues_de_inicializar_sin_traceback(self):
        with tempfile.TemporaryDirectory() as carpeta:
            env = os.environ.copy()
            env['GRACE_DATA_DIR'] = carpeta
            env['PYTHONDONTWRITEBYTECODE'] = '1'
            # Importar ServicioGrace en un proceso separado crea el estado inicial.
            primera = subprocess.run([sys.executable, '-c',
                'from grace.servicio import ServicioGrace; import os; ServicioGrace(os.environ["GRACE_DATA_DIR"])'],
                cwd=BASE, env=env, capture_output=True, text=True, timeout=8)
            self.assertEqual(primera.returncode, 0, primera.stderr)
            estado = Path(carpeta) / 'estado.json'
            self.assertTrue(estado.exists())
            estado.unlink()
            segunda = subprocess.run([sys.executable, 'app.py'], cwd=BASE, env=env,
                                     capture_output=True, text=True, timeout=8)
            self.assertNotEqual(segunda.returncode, 0)
            self.assertIn('Falta estado.json', segunda.stderr)
            self.assertNotIn('Traceback', segunda.stderr)
            self.assertFalse(estado.exists(), 'No debe regenerarse la semilla silenciosamente')


if __name__ == '__main__':
    unittest.main()
