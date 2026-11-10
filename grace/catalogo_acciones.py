"""Definiciones compartidas del esquema que la IA puede proponer."""


PANTALLAS = {
    'calendario': {'estudiante', 'profesor', 'coordinador'},
    'mis-clases': {'estudiante', 'profesor'},
    'inicio': {'estudiante', 'profesor', 'coordinador'},
}

CATALOGO_ACCIONES = {
    'cambiar_tema': {
        'roles': frozenset(('estudiante', 'profesor', 'coordinador')),
        'parametros': frozenset(('tema',)), 'riesgo': 'bajo', 'confirmacion': False,
    },
    'abrir_pantalla': {
        'roles': frozenset(('estudiante', 'profesor', 'coordinador')),
        'parametros': frozenset(('pantalla',)), 'riesgo': 'bajo', 'confirmacion': False,
    },
    'proxima_sesion': {
        'roles': frozenset(('estudiante', 'profesor')),
        'parametros': frozenset(), 'riesgo': 'bajo', 'confirmacion': False,
    },
    'resumen_semanal': {
        'roles': frozenset(('estudiante', 'profesor')),
        'parametros': frozenset(), 'riesgo': 'bajo', 'confirmacion': False,
    },
}


class ErrorPropuestaEstructurada(ValueError):
    """La IA respondió con un JSON que no permite decidir una acción segura."""
