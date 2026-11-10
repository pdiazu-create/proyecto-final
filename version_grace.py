"""Huella del código instalado. No incluye datos, claves ni documentos."""
from hashlib import sha256
from pathlib import Path

BASE = Path(__file__).resolve().parent


def revision_codigo(base=BASE):
    """La misma copia produce la misma huella, incluso después de clonarla."""
    base = Path(base)
    archivos = list(base.glob('*.py')) + list(base.glob('*.pyw'))
    for carpeta in ('grace', 'web'):
        archivos.extend(p for p in (base / carpeta).rglob('*')
                        if p.is_file() and p.suffix in ('.py', '.js', '.css', '.html', '.svg'))
    huella = sha256()
    for archivo in sorted(archivos, key=lambda p: p.relative_to(base).as_posix()):
        nombre = archivo.relative_to(base).as_posix().encode('utf-8')
        # Git puede convertir los saltos de línea en Windows. No cambia el código.
        contenido = archivo.read_bytes().replace(b'\r\n', b'\n')
        huella.update(nombre + b'\0' + sha256(contenido).digest())
    return huella.hexdigest()


def servidor_actual(estado):
    """Sin huella o con otra huella, debe reiniciarse antes de abrirlo."""
    return bool(estado and estado.get('revision') == revision_codigo())
