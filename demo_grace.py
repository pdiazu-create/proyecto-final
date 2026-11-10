"""Demostración limpia y temporal: python demo_grace.py [--puerto 8001]."""
import argparse
import os
from pathlib import Path
import runpy
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--puerto', type=int, default=8001)
    args = parser.parse_args()
    if not 1024 <= args.puerto <= 65535:
        parser.error('El puerto debe estar entre 1024 y 65535.')
    with tempfile.TemporaryDirectory(prefix='grace-demo-') as carpeta:
        os.environ.update(GRACE_DATA_DIR=carpeta, GRACE_IA='reglas', PORT=str(args.puerto))
        os.environ.pop('GRACE_IA_KEY', None)
        os.environ.pop('GRACE_INSTANCIA', None)
        print('Demo temporal con reglas locales. No usa ni modifica tus datos de trabajo.')
        print('Los cambios de esta demo se descartan al detenerla con Ctrl+C.')
        runpy.run_path(str(Path(__file__).with_name('app.py')), run_name='__main__')


if __name__ == '__main__':
    main()
