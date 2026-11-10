"""Motor local de reglas. No hay IA generativa ni llamadas externas.

La clasificación utiliza puntuaciones visibles y respuestas basadas en el
estado académico que el servicio ya conserva. No modifica ese estado.
"""
from datetime import date
import re
import unicodedata


PLANTILLAS = {
    'Fundamentos': (
        'Explicar variables, tipos de datos y las instrucciones de entrada y salida.',
        'Crear un programa que reciba un nombre y muestre un mensaje.',
        'Verificar que el programa recibe los valores y produce la salida esperada.',
    ),
    'Condicionales': (
        'Comparar expresiones booleanas y explicar if, elif y else.',
        'Crear un validador de nota que distinga aprobado y pendiente.',
        'Probar los tres casos: menor, igual y mayor al límite.',
    ),
    'Ciclos': (
        'Demostrar for y while y cómo evitar un ciclo infinito.',
        'Recorrer una lista con for y repetir un menú con while.',
        'Revisar el caso de cero repeticiones y la condición de salida.',
    ),
    'Funciones': (
        'Explicar parámetros, retorno y funciones de una sola responsabilidad.',
        'Separar la entrada, el cálculo y la salida en tres funciones.',
        'Probar entradas normales y un caso de validación fallida.',
    ),
    'Listas': (
        'Explicar índices, append y recorridos de listas en Python.',
        'Registrar calificaciones y calcular mínimo, máximo y promedio.',
        'Revisar el resultado con una lista vacía y otra con varios elementos.',
    ),
    'Archivos': (
        'Explicar lectura y escritura con with, UTF-8 y manejo de errores.',
        'Guardar una lista de calificaciones en un archivo y volver a leerla.',
        'Comprobar archivo ausente y contenido incorrecto sin perder los datos.',
    ),
    'Colas enlazadas': (
        'Dibujar Nodo, frente, final y la referencia siguiente.',
        'Implementar encolar y desencolar solicitudes por orden de llegada.',
        'Probar una cola vacía y desencolar el único elemento.',
    ),
    'Árboles': (
        'Explicar raíz, hijos y orden de un árbol binario de búsqueda.',
        'Insertar claves y buscar una actividad mediante comparaciones.',
        'Comprobar inserción repetida y el caso de claves consecutivas.',
    ),
    'Grafos': (
        'Explicar vértices, aristas dirigidas y lista de adyacencia.',
        'Recorrer los prerrequisitos con BFS e índice frontal.',
        'Buscar una ruta alcanzable y otra que no exista.',
    ),
}

# Cada palabra vale 1 punto; cada expresión vale 4. Se selecciona la intención
# más puntuable, con desempate por el orden de INTENCIONES.
INTENCIONES = (
    ('resumen_semana', ('resume esta semana', 'resumen de esta semana', 'resumeme la semana'), ('resume', 'resumen', 'semana')),
    ('organizar_tareas', ('organiza mis tareas', 'organizar mis tareas', 'ordena mis tareas'), ('organiza', 'organizar', 'ordena')),
    ('explicar_tema', ('explicame este tema', 'explícame este tema', 'explica este tema'), ('explica', 'explicame', 'tema')),
    ('prerrequisitos', ('prerrequisito', 'prerrequisitos', 'estudio antes', 'estudiar antes', 'antes de', 'que aprender antes'), ('estudio', 'estudiar', 'antes')),
    ('proxima', ('proxima fecha', 'proximo vencimiento', 'cuando entrego', 'cuando vence', 'fecha de entrega'), ('proxima', 'proximo', 'fecha', 'vence', 'vencimiento')),
    ('asistencia', ('porcentaje de asistencia', 'mi asistencia', 'asistencia de clase'), ('asistencia', 'presente', 'ausente', 'inasistencia', 'porcentaje')),
    ('solicitud', ('siguiente solicitud', 'proxima solicitud', 'cola de ayuda', 'solicitudes de ayuda'), ('solicitud', 'solicitudes', 'cola', 'ayuda', 'siguiente')),
    ('pendientes', ('mis pendientes', 'tareas pendientes', 'entregas pendientes'), ('pendiente', 'pendientes', 'entrega', 'entregas', 'tarea', 'tareas')),
    ('grafo', ('explica el grafo', 'grafo de aprendizaje'), ('grafo', 'ruta', 'arbol', 'buscar')),
    ('saludo', ('buenos dias', 'buenas tardes', 'hola grace'), ('hola', 'gracias', 'buenas')),
)


def _normalizar(texto):
    texto = unicodedata.normalize('NFKD', texto.casefold())
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', texto).strip()


def detectar_intencion(mensaje):
    """Clasifica por puntuación de expresiones y palabras, sin un modelo de IA."""
    texto = _normalizar(mensaje)
    palabras = set(re.findall(r'[a-z0-9]+', texto))
    puntuaciones = {}
    for intencion, frases, vocabulario in INTENCIONES:
        valor = sum(4 for frase in frases if re.search(r'(?<!\w)' + re.escape(frase) + r'(?!\w)', texto))
        valor += sum(1 for palabra in vocabulario if palabra in palabras)
        puntuaciones[intencion] = valor
    mejor = max(puntuaciones, key=puntuaciones.get)
    return mejor if puntuaciones[mejor] else 'desconocida'


def proponer_accion(mensaje):
    """Respaldo local para acciones simples; nunca concede permisos."""
    texto = _normalizar(mensaje)
    if any(p in texto for p in ('oscuro', 'oscura', 'claro', 'clara')) and any(
            p in texto for p in ('tema', 'modo', 'ponlo', 'pon el', 'cambia')):
        tema = 'oscuro' if 'oscuro' in texto or 'oscura' in texto else 'claro'
        return {'accion': 'cambiar_tema', 'parametros': {'tema': tema}, 'respuesta': ''}
    if re.search(r'\b(cambia|cambiar|alterna|alternar)\b', texto) and re.search(
            r'\b(tema|modo)\b', texto):
        return {'accion': 'cambiar_tema', 'parametros': {'tema': 'alternar'}, 'respuesta': ''}
    if ('semana' in texto and any(p in texto for p in ('horario', 'clase', 'hora', 'resumen'))
            or 'resume esta semana' in texto or 'resumen de esta semana' in texto):
        return {'accion': 'resumen_semanal', 'parametros': {}, 'respuesta': ''}
    if any(p in texto for p in ('proxima clase', 'proximo curso', 'siguiente clase',
                                 'cuando tengo clase', 'cuando es mi clase',
                                 'proxima sesion', 'siguiente sesion')):
        return {'accion': 'proxima_sesion', 'parametros': {}, 'respuesta': ''}
    if 'horario' in texto:
        return {'accion': 'abrir_pantalla', 'parametros': {'pantalla': 'calendario'}, 'respuesta': ''}
    if 'mis clases' in texto or 'mis cursos' in texto:
        return {'accion': 'abrir_pantalla', 'parametros': {'pantalla': 'mis-clases'}, 'respuesta': ''}
    return {'accion': 'ninguna', 'parametros': {}, 'respuesta': ''}


def generar_borrador_plan(objetivo, tema):
    """Una plantilla distinta por cada tema oficial; siempre es un borrador."""
    if tema not in PLANTILLAS:
        raise ValueError('No hay plantilla para ese tema del curso.')
    desarrollo, practica, evaluacion = PLANTILLAS[tema]
    return {
        'apertura': f'Presentar el objetivo: {objetivo}',
        'desarrollo': desarrollo,
        'practica': practica,
        'evaluacion': evaluacion,
        'nota': 'Borrador generado con reglas y plantillas. Requiere revisión humana.',
    }


def _tema_en_mensaje(mensaje, temas):
    texto = _normalizar(mensaje)
    # Primero el nombre más largo, para reconocer temas con varias palabras.
    for tema in sorted(temas, key=len, reverse=True):
        if re.search(r'(?<!\w)' + re.escape(_normalizar(tema)) + r'(?!\w)', texto):
            return tema
    return None


def responder(mensaje, rol, actividades, entregas, cola, estudiante_id,
              asistencias=(), grafo=None, temas=()):
    """Todas las respuestas identifican los registros de origen utilizados."""
    if not isinstance(mensaje, str) or not mensaje.strip():
        return 'Escribe una pregunta. Fuente: reglas locales de Grace.'
    intencion = detectar_intencion(mensaje)
    enviadas = {r['actividad_id'] for r in entregas if r['estudiante_id'] == estudiante_id}
    pendientes = [a for a in actividades if a['id'] not in enviadas]

    if intencion == 'pendientes':
        if rol == 'docente':
            return (f'Hay {len(actividades)} actividades y {len(entregas)} entregas registradas. '
                    'Fuente: listas de actividades y entregas del curso (datos ficticios).')
        if pendientes:
            nombres = '; '.join(a['titulo'] for a in sorted(pendientes, key=lambda a:a['fecha'])[:4])
            return (f'Tienes {len(pendientes)} actividades sin entrega registrada: {nombres}. '
                    'Fuente: actividades publicadas y entregas de este estudiante (datos ficticios).')
        return 'No tienes pendientes registrados. Fuente: actividades y entregas del estudiante (datos ficticios).'

    if intencion == 'resumen_semana':
        ordenadas = sorted(pendientes, key=lambda a: a['fecha'])[:3]
        fechas = '; '.join(f"{a['titulo']} ({a['fecha']})" for a in ordenadas) or 'ninguna'
        registros = [a for a in asistencias if a['estudiante_id'] == estudiante_id]
        presentes = sum(1 for a in registros if a['presente'])
        asistencia = f'{round(100 * presentes / len(registros), 1)}%' if registros else 'sin registros'
        return (f'Resumen: {len(pendientes)} pendientes; próximas: {fechas}; '
                f'asistencia: {asistencia}; solicitudes en cola: {cola.tamano}. '
                'Fuente: actividades, asistencia y cola del curso (datos ficticios).')

    if intencion == 'organizar_tareas':
        ordenadas = sorted(pendientes, key=lambda a: a['fecha'])
        if not ordenadas:
            return 'No tienes tareas pendientes registradas. Fuente: actividades y entregas del estudiante (datos ficticios).'
        lista = '; '.join(f"{a['titulo']} — {a['fecha']}" for a in ordenadas[:5])
        return (f'Orden sugerido por fecha: {lista}. Empieza por la primera y confirma cada entrega. '
                'Fuente: actividades publicadas y entregas del estudiante (datos ficticios).')

    if intencion == 'explicar_tema':
        destino = _tema_en_mensaje(mensaje, temas)
        if destino is None:
            return ('Indica el tema que quieres comprender, por ejemplo «Explícame Listas». '
                    'Fuente: temas del curso y reglas locales.')
        ruta = grafo.ruta_mas_corta('Fundamentos', destino) if grafo else []
        actividades_tema = [a['titulo'] for a in actividades if a['tema'] == destino]
        detalle = PLANTILLAS.get(destino, ('', '', ''))[0]
        camino = ' → '.join(ruta) if ruta else destino
        extras = f' Actividades relacionadas: {", ".join(actividades_tema)}.' if actividades_tema else ''
        return (f'{destino}: {detalle} Ruta BFS desde Fundamentos: {camino}.{extras} '
                'Fuente: plantilla del tema y grafo de aprendizaje (datos ficticios).')

    if intencion == 'proxima':
        futuras = [a for a in pendientes if a['fecha'] >= date.today().isoformat()]
        if futuras:
            siguiente = min(futuras, key=lambda a: a['fecha'])
            return (f'La próxima actividad pendiente registrada es «{siguiente["titulo"]}» '
                    f'el {siguiente["fecha"]}. La fecha es de clase/actividad, no un plazo de entrega independiente. '
                    'Fuente: actividades del curso y entregas del estudiante (datos ficticios).')
        return ('No hay fechas futuras de actividades pendientes registradas. '
                'No existe un campo separado de fecha límite de entrega en esta demo. '
                'Fuente: actividades y entregas del curso (datos ficticios).')

    if intencion == 'asistencia':
        registros = list(asistencias) if rol == 'docente' else [
            a for a in asistencias if a['estudiante_id'] == estudiante_id]
        presentes = sum(1 for a in registros if a['presente'])
        if not registros:
            return ('Aún no hay registros de asistencia para calcular un porcentaje. '
                    'Fuente: lista de asistencias del curso (datos ficticios).')
        porcentaje = round(100 * presentes / len(registros), 1)
        sujeto = 'de la clase' if rol == 'docente' else 'de tu asistencia'
        return (f'El porcentaje {sujeto} es {porcentaje}% '
                f'({presentes} presencias de {len(registros)} registros). '
                'Fuente: lista de asistencias registradas; días sin registro no cuentan como ausencias (datos ficticios).')

    if intencion == 'solicitud':
        siguiente = cola.ver_frente()
        if siguiente is None:
            return 'No hay solicitudes pendientes. Fuente: cola enlazada de solicitudes (datos ficticios).'
        if rol == 'docente':
            return (f'La siguiente solicitud es #{siguiente["id"]}: «{siguiente["mensaje"]}». '
                    'Fuente: nodo frente de la cola enlazada FIFO (datos ficticios).')
        return (f'Hay {cola.tamano} solicitudes en espera. El detalle de otras personas no se muestra aquí. '
                'Fuente: tamaño de la cola enlazada FIFO (datos ficticios).')

    if intencion == 'prerrequisitos':
        destino = _tema_en_mensaje(mensaje, temas)
        if destino is None:
            return ('Indica un tema del curso, por ejemplo «¿qué estudio antes de Grafos?». '
                    'Fuente: temas y relaciones del grafo de aprendizaje.')
        ruta = grafo.ruta_mas_corta('Fundamentos', destino) if grafo else []
        if not ruta:
            return (f'No se encontró una ruta a {destino}. '
                    'Fuente: grafo de prerrequisitos, recorrido BFS (datos ficticios).')
        if len(ruta) == 1:
            return (f'{destino} es el punto de partida de esta ruta. '
                    'Fuente: grafo de temas, recorrido BFS (datos ficticios).')
        return (f'Antes de {destino}, la ruta más corta sugerida es: '
                + ' → '.join(ruta[:-1]) + '. BFS propone una ruta, no todos los prerrequisitos. '
                'Fuente: lista de adyacencia del grafo y BFS propio (datos ficticios).')

    if intencion == 'grafo':
        return ('En Estructuras puedes buscar rutas entre temas con BFS; '
                'el árbol permite buscar actividades por ID. '
                'Fuente: grafo y árbol de actividades de esta demostración.')

    if intencion == 'saludo':
        return 'Hola. Soy el asistente por reglas de Grace; no soy IA generativa. Fuente: reglas locales.'

    return ('Soy el asistente por reglas de Grace, no una IA generativa. '
            'Puedo consultar pendientes, próxima actividad, asistencia, cola de solicitudes y rutas del grafo. '
            'Fuente: reglas locales y datos ficticios del curso.')
