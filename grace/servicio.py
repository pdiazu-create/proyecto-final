"""Grace: lógica académica en Python y flujo revisable por el docente.

Esta es una DEMOSTRACIÓN LOCAL, sin inicio de sesión ni permisos reales.
No usar con datos personales ni publicar el servidor en Internet.
"""
from copy import deepcopy
import os
from pathlib import Path
import re
from datetime import date, datetime, timezone
from threading import RLock

from .archivos import AlmacenJSON, ErrorDatos
from .estructuras import ArbolBinarioBusqueda, ColaEnlazada, GrafoAprendizaje
from .ia import crear_proveedor


class ErrorValidacion(ValueError):
    pass


class ColaInstantanea:
    """Vista no recursiva de la cola para el asistente."""

    def __init__(self, tamano, frente):
        self.tamano = tamano
        self._frente = frente

    def ver_frente(self):
        return self._frente


INSTITUCION = 'grace-demo'
CURSO = 'programacion-estructurada'
ESTUDIANTES = [
    {'id': 'e1', 'institucion_id': INSTITUCION, 'nombre': 'Ana López'},
    {'id': 'e2', 'institucion_id': INSTITUCION, 'nombre': 'Diego Ruiz'},
    {'id': 'e3', 'institucion_id': INSTITUCION, 'nombre': 'Sofía Pérez'},
]
TEMAS = ['Fundamentos', 'Condicionales', 'Ciclos', 'Funciones', 'Listas',
         'Archivos', 'Colas enlazadas', 'Árboles', 'Grafos']
RELACIONES = [
    ('Fundamentos', 'Condicionales'), ('Condicionales', 'Ciclos'),
    ('Ciclos', 'Funciones'), ('Funciones', 'Listas'), ('Funciones', 'Archivos'),
    ('Listas', 'Colas enlazadas'), ('Colas enlazadas', 'Árboles'),
    ('Árboles', 'Grafos'), ('Archivos', 'Grafos'),
]
TRANSICIONES = {
    'borrador': {'revisar': 'en_revision'},
    'en_revision': {'aprobar': 'aprobado', 'rechazar': 'rechazado'},
    'aprobado': {'publicar': 'publicado'},
    'publicado': {}, 'rechazado': {},
}
CAMPOS_PLAN = ('apertura', 'desarrollo', 'practica', 'evaluacion')
ARCHIVO_ESTADO = 'estado.json'
MARCADOR_INICIO = '.grace_inicializada'
VERSION_ESTADO = 4


def marca_tiempo():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _id_entero(valor, nombre='ID'):
    # Evitar bool (subclase de int) y conversiones de coma flotante a enteros.
    if isinstance(valor, bool) or not isinstance(valor, (str, int)):
        raise ErrorValidacion(f'{nombre} debe ser un entero positivo.')
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        raise ErrorValidacion(f'{nombre} debe ser un entero positivo.') from None
    if numero <= 0 or (isinstance(valor, str) and str(numero) != valor.strip()):
        raise ErrorValidacion(f'{nombre} debe ser un entero positivo.')
    return numero


class ServicioGrace:
    """Servicio modular con estructuras propias y guardado atómico de estado."""

    def __init__(self, carpeta_datos):
        self.almacen = AlmacenJSON(carpeta_datos)
        self.lock = RLock()
        self.grafo = GrafoAprendizaje()
        for tema in TEMAS:
            self.grafo.agregar_tema(tema)
        for origen, destino in RELACIONES:
            self.grafo.agregar_relacion(origen, destino)
        self.ia = crear_proveedor()
        self.actividades = []
        self.planes = []
        self.entregas = []
        self.asistencias = []
        self.atendidas = []
        self.origenes_planes = {}
        self.cola = ColaEnlazada()
        self.arbol = ArbolBinarioBusqueda()
        self._cargar_o_inicializar()

    def _estado_guardable(self):
        return {
            'version': VERSION_ESTADO, 'institucion_id': INSTITUCION, 'curso_id': CURSO,
            'actividades': self.actividades, 'planes': self.planes,
            'entregas': self.entregas, 'asistencias': self.asistencias,
            'solicitudes_pendientes': self.cola.recorrer(),
            'solicitudes_atendidas': self.atendidas,
        }

    def _aplicar_estado(self, datos):
        if not isinstance(datos, dict) or datos.get('institucion_id') != INSTITUCION or datos.get('curso_id') != CURSO:
            raise ErrorDatos('El estado de Grace no corresponde a la institución y el curso de esta demo.')
        # Lee estados de la v0.3 y v0.4; las versiones desconocidas no se inventan.
        if type(datos.get('version')) is not int or datos['version'] not in (3, VERSION_ESTADO):
            raise ErrorDatos('Versión de estado desconocida o ausente. Se requiere migración explícita.')
        campos = ('actividades', 'planes', 'entregas', 'asistencias',
                  'solicitudes_pendientes', 'solicitudes_atendidas')
        if any(not isinstance(datos.get(c), list) for c in campos):
            raise ErrorDatos('El estado contiene datos inválidos; no se reiniciará automáticamente.')
        # Comprobaciones fundamentales de integridad. Los datos dañados requieren intervención.
        actividades = datos['actividades']
        planes = datos['planes']
        ids_actividades = set()
        for a in actividades:
            if not isinstance(a, dict) or not isinstance(a.get('id'), int) or isinstance(a.get('id'), bool) or a['id'] in ids_actividades or a.get('institucion_id') != INSTITUCION:
                raise ErrorDatos('Actividades corruptas o identificadores duplicados.')
            ids_actividades.add(a['id'])
        ids_planes = set()
        for plan in planes:
            if not isinstance(plan, dict) or not isinstance(plan.get('id'), int) or plan['id'] in ids_planes or plan.get('estado') not in TRANSICIONES or not isinstance(plan.get('historial'), list) or plan.get('institucion_id') != INSTITUCION:
                raise ErrorDatos('Planes corruptos, con estado inválido o duplicados.')
            ids_planes.add(plan['id'])
            actividad_id = plan.get('actividad_id')
            if plan['estado'] == 'publicado' and actividad_id not in ids_actividades:
                raise ErrorDatos('Plan publicado sin actividad asociada: datos inconsistentes.')
            if plan['estado'] != 'publicado' and actividad_id is not None:
                raise ErrorDatos('Plan no publicado con actividad asociada.')
        self.actividades = deepcopy(actividades)
        self.planes = deepcopy(planes)
        self.origenes_planes = {p['id']: 'reglas' for p in planes}
        self.entregas = deepcopy(datos['entregas'])
        self.asistencias = deepcopy(datos['asistencias'])
        self.atendidas = deepcopy(datos['solicitudes_atendidas'])
        self.cola = ColaEnlazada()
        for solicitud in datos['solicitudes_pendientes']:
            self.cola.encolar(deepcopy(solicitud))
        self._reconstruir_arbol()

    def _reconstruir_arbol(self):
        self.arbol = ArbolBinarioBusqueda()
        for actividad in self.actividades:
            self.arbol.insertar(actividad['id'], actividad)
        # Reequilibra también estados antiguos con identificadores consecutivos.
        self.arbol.reconstruir_balanceado()

    def _guardar(self):
        self.almacen.guardar(ARCHIVO_ESTADO, self._estado_guardable())

    def _mutar(self, accion):
        """Modificar + guardar un estado; si falla el disco, revertir la memoria.

        Las dos listas (planes, actividades) quedan en un único JSON. El reemplazo
        atómico de ese archivo evita publicaciones a medias tras un fallo simple.
        """
        anterior = deepcopy(self._estado_guardable())
        try:
            resultado = accion()
            self._guardar()
            return deepcopy(resultado)
        except Exception:
            self._aplicar_estado(anterior)
            raise

    def _marcar_inicio(self):
        """Diferencia primera ejecución de borrado posterior de estado.json.

        Es un indicador, no una copia de seguridad ni otra fuente académica.
        Se escribe solamente después de que exista un estado guardado válido.
        """
        ruta = Path(self.almacen.carpeta) / MARCADOR_INICIO
        if ruta.exists():
            return
        try:
            with ruta.open('x', encoding='utf-8') as archivo:
                archivo.write('Grace inicializada; no borrar estado.json para reiniciar.\n')
                archivo.flush()
                os.fsync(archivo.fileno())
        except FileExistsError:
            pass

    def _cargar_o_inicializar(self):
        with self.lock:
            if self.almacen.existe(ARCHIVO_ESTADO):
                self._aplicar_estado(self.almacen.leer(ARCHIVO_ESTADO))
                self._marcar_inicio()
                return
            antiguos = ('actividades.json', 'planes.json', 'entregas.json',
                        'asistencias.json', 'solicitudes.json')
            if any(self.almacen.existe(a) for a in antiguos):
                # Migrar sin borrar originales. Los datos faltantes se consideran vacíos.
                solicitudes = self.almacen.leer('solicitudes.json', {})
                if not isinstance(solicitudes, dict):
                    raise ErrorDatos('Formato de solicitudes antiguas incorrecto.')
                datos = {
                    'version': VERSION_ESTADO, 'institucion_id': INSTITUCION, 'curso_id': CURSO,
                    'actividades': self.almacen.leer('actividades.json', []),
                    'planes': self.almacen.leer('planes.json', []),
                    'entregas': self.almacen.leer('entregas.json', []),
                    'asistencias': self.almacen.leer('asistencias.json', []),
                    'solicitudes_pendientes': solicitudes.get('pendientes', []),
                    'solicitudes_atendidas': solicitudes.get('atendidas', []),
                }
                self._aplicar_estado(datos)
                self._guardar()
                self._marcar_inicio()
                return
            if (Path(self.almacen.carpeta) / MARCADOR_INICIO).exists():
                raise ErrorDatos('Falta estado.json en una demo previamente inicializada. No se reinicia: recupera una copia o usa una carpeta nueva para otra demostración.')
            self._semilla()
            self._guardar()
            self._marcar_inicio()

    def _semilla(self):
        base = [
            (105, 'Aplicar listas en Python', 'Listas', '2026-11-16'),
            (102, 'Condicionales y decisiones', 'Condicionales', '2026-11-10'),
            (108, 'Árbol para buscar actividades', 'Árboles', '2026-11-25'),
            (101, 'Introducción a Python', 'Fundamentos', '2026-11-09'),
            (103, 'Practicar ciclos', 'Ciclos', '2026-11-12'),
            (107, 'Cola de solicitudes', 'Colas enlazadas', '2026-11-23'),
            (109, 'Rutas de aprendizaje', 'Grafos', '2026-11-30'),
        ]
        self.actividades = [
            {'id': identificador, 'institucion_id': INSTITUCION, 'curso_id': CURSO,
             'titulo': titulo, 'tema': tema, 'fecha': fecha,
             'descripcion': f'Práctica sobre {tema} mediante ejercicios de Python.'}
            for identificador, titulo, tema, fecha in base
        ]
        self.planes = []
        self.entregas = [
            {'institucion_id': INSTITUCION, 'actividad_id': 101, 'estudiante_id': 'e1', 'fecha': '2026-11-06'},
            {'institucion_id': INSTITUCION, 'actividad_id': 101, 'estudiante_id': 'e2', 'fecha': '2026-11-06'},
        ]
        self.asistencias = []
        self.atendidas = []
        self.cola = ColaEnlazada()
        self.cola.encolar({'id': 1, 'institucion_id': INSTITUCION, 'estudiante_id': 'e2',
                           'mensaje': '¿Cómo recorro una lista con for?', 'fecha': '2026-11-06'})
        self.cola.encolar({'id': 2, 'institucion_id': INSTITUCION, 'estudiante_id': 'e1',
                           'mensaje': '¿Cuál es la diferencia entre cola y lista?', 'fecha': '2026-11-06'})
        self._reconstruir_arbol()

    def reiniciar(self):
        with self.lock:
            return self._mutar(lambda: (self._semilla() or {'mensaje': 'Datos ficticios reiniciados.'}))

    @staticmethod
    def _validar_estudiante(estudiante_id):
        if estudiante_id not in {e['id'] for e in ESTUDIANTES}:
            raise ErrorValidacion('Selecciona un estudiante válido de la demostración.')

    @staticmethod
    def _texto(valor, nombre, minimo=1, maximo=240):
        if not isinstance(valor, str):
            raise ErrorValidacion(f'{nombre} debe ser texto.')
        valor = valor.strip()
        if not minimo <= len(valor) <= maximo:
            raise ErrorValidacion(f'{nombre} debe tener entre {minimo} y {maximo} caracteres.')
        return valor

    @staticmethod
    def _fecha(valor):
        if not isinstance(valor, str):
            raise ErrorValidacion('La fecha debe ser texto (AAAA-MM-DD).')
        try:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', valor):
                raise ValueError('Formato de fecha incorrecto')
            return date.fromisoformat(valor).isoformat()
        except ValueError:
            raise ErrorValidacion('Introduce una fecha válida (AAAA-MM-DD).') from None

    def estado(self, estudiante_id='e1'):
        with self.lock:
            self._validar_estudiante(estudiante_id)
            entregadas = {x['actividad_id'] for x in self.entregas if x['estudiante_id'] == estudiante_id}
            actividades = []
            for a in self.arbol.en_orden():
                copia = deepcopy(a)
                copia['entregada'] = a['id'] in entregadas
                copia['total_entregas'] = sum(1 for x in self.entregas if x['actividad_id'] == a['id'])
                actividades.append(copia)
            planes = deepcopy(self.planes)
            for plan in planes:
                plan['origen'] = self.origenes_planes.get(plan['id'], 'reglas')
            return {
                'version': '0.4', 'institucion': 'Campus de demostración · datos ficticios',
                'curso': 'Programación Estructurada',
                'estudiantes': deepcopy(ESTUDIANTES), 'estudiante_actual': estudiante_id,
                'actividades': actividades, 'planes': planes,
                'asistencias': deepcopy(self.asistencias),
                'resumen_asistencia': self._resumen_asistencia(),
                'estadisticas': {
                    'estudiantes': len(ESTUDIANTES), 'actividades': len(actividades),
                    'entregas': len(self.entregas), 'planes': len(self.planes),
                    'ayudas_pendientes': self.cola.tamano,
                    'mis_pendientes': len(actividades) - len(entregadas),
                },
                'solicitudes': deepcopy(self.cola.recorrer()),
                'solicitudes_atendidas': deepcopy(self.atendidas[-6:]),
                'arbol': self.arbol.niveles(),
                'grafo': {'temas': list(self.grafo.adyacencia), 'relaciones': self.grafo.conexiones()},
            }

    def crear_plan(self, datos):
        with self.lock:
            objetivo = self._texto(datos.get('objetivo'), 'Objetivo', 10, 300)
            tema = datos.get('tema')
            if tema not in TEMAS:
                raise ErrorValidacion('Selecciona un tema válido.')
            fecha = self._fecha(datos.get('fecha'))
            contexto = self._contexto_ia('e1', tema=tema)
            contexto['publico'] = {
                clave: contexto['publico'][clave]
                for clave in ('actividades', 'fechas_actividades', 'ruta_bfs', 'tamano_cola')
            }
        generado = self.ia.crear_plan(objetivo, tema, contexto, CAMPOS_PLAN)
        contenido = generado['contenido']
        if set(contenido) != set(CAMPOS_PLAN) | {'nota'}:
            raise ErrorValidacion('El borrador generado no tiene los campos esperados.')
        with self.lock:
            def mutacion():
                plan = {
                    'id': max((p['id'] for p in self.planes), default=0) + 1,
                    'institucion_id': INSTITUCION, 'curso_id': CURSO,
                    'objetivo': objetivo, 'tema': tema, 'fecha': fecha,
                    'contenido': contenido,
                    'estado': 'borrador', 'actividad_id': None,
                    'historial': [{'accion': 'crear', 'estado': 'borrador',
                                  'actor': 'docente_demo', 'cuando': marca_tiempo()}],
                }
                self.planes.append(plan)
                return plan
            resultado = self._mutar(mutacion)
            self.origenes_planes[resultado['id']] = generado['origen']
            resultado['origen'] = generado['origen']
            return resultado

    def _obtener_plan(self, datos):
        identificador = _id_entero(datos.get('id'), 'ID de plan')
        plan = next((p for p in self.planes if p['id'] == identificador), None)
        if plan is None:
            raise ErrorValidacion('No existe ese plan.')
        return plan

    def editar_plan(self, datos):
        with self.lock:
            plan = self._obtener_plan(datos)
            if plan['estado'] not in ('borrador', 'en_revision'):
                raise ErrorValidacion('Solo puedes editar planes sin aprobar.')
            cambios = datos.get('contenido')
            if not isinstance(cambios, dict) or not cambios or not set(cambios).issubset(CAMPOS_PLAN):
                raise ErrorValidacion('Selecciona al menos un campo válido para editar.')
            validos = {k: self._texto(v, k.capitalize(), 5, 400) for k, v in cambios.items()}
            def mutacion():
                plan['contenido'].update(validos)
                # Modificar durante revisión exige iniciar de nuevo el circuito de aprobación.
                plan['estado'] = 'borrador'
                plan['historial'].append({'accion': 'editar', 'estado': 'borrador',
                                          'actor': 'docente_demo', 'cuando': marca_tiempo()})
                return plan
            return self._mutar(mutacion)

    def cambiar_estado_plan(self, datos):
        with self.lock:
            plan = self._obtener_plan(datos)
            accion = datos.get('accion')
            siguiente = TRANSICIONES[plan['estado']].get(accion)
            if siguiente is None:
                raise ErrorValidacion(f"No se permite '{accion}' desde '{plan['estado']}'.")
            def mutacion():
                plan['estado'] = siguiente
                plan['historial'].append({'accion': accion, 'estado': siguiente,
                                          'actor': 'docente_demo', 'cuando': marca_tiempo()})
                if siguiente == 'publicado':
                    nuevo_id = max((a['id'] for a in self.actividades), default=100) + 1
                    actividad = {
                        'id': nuevo_id, 'institucion_id': INSTITUCION, 'curso_id': CURSO,
                        'titulo': f"Práctica: {plan['tema']}", 'tema': plan['tema'],
                        'descripcion': plan['objetivo'], 'fecha': plan['fecha'],
                    }
                    self.actividades.append(actividad)
                    self.arbol.insertar(nuevo_id, actividad)
                    self.arbol.balancear_si_necesario()
                    plan['actividad_id'] = nuevo_id
                return plan
            return self._mutar(mutacion)

    def registrar_asistencia_lote(self, datos):
        """Registra toda la clase en un único cambio reversible y un guardado JSON."""
        with self.lock:
            fecha = self._fecha(datos.get('fecha'))
            registros = datos.get('registros')
            if not isinstance(registros, list) or len(registros) != len(ESTUDIANTES):
                raise ErrorValidacion('Envía un registro por cada estudiante de la clase.')
            recibidos = {}
            for registro in registros:
                if not isinstance(registro, dict) or set(registro) != {'estudiante_id', 'presente'}:
                    raise ErrorValidacion('Cada registro necesita estudiante_id y presente.')
                estudiante_id = registro['estudiante_id']
                self._validar_estudiante(estudiante_id)
                if estudiante_id in recibidos:
                    raise ErrorValidacion('No repitas estudiantes en el lote.')
                if not isinstance(registro['presente'], bool):
                    raise ErrorValidacion('Presente debe ser verdadero o falso.')
                recibidos[estudiante_id] = registro['presente']
            if set(recibidos) != {e['id'] for e in ESTUDIANTES}:
                raise ErrorValidacion('El lote debe incluir a todos los estudiantes.')

            def mutacion():
                for estudiante_id, presente in recibidos.items():
                    existente = next((r for r in self.asistencias
                                      if r['estudiante_id'] == estudiante_id and r['fecha'] == fecha), None)
                    if existente is None:
                        self.asistencias.append({
                            'institucion_id': INSTITUCION, 'curso_id': CURSO,
                            'estudiante_id': estudiante_id, 'fecha': fecha, 'presente': presente,
                        })
                    else:
                        existente['presente'] = presente
                return {'fecha': fecha, 'registrados': len(recibidos)}
            return self._mutar(mutacion)

    def _resumen_asistencia(self):
        """Cálculos de lectura: no añade campos al archivo estado.json."""
        por_estudiante = {}
        for estudiante in ESTUDIANTES:
            registros = [r for r in self.asistencias if r['estudiante_id'] == estudiante['id']]
            presentes = sum(1 for r in registros if r['presente'])
            por_estudiante[estudiante['id']] = {
                'registrados': len(registros), 'presentes': presentes,
                'porcentaje': round(100 * presentes / len(registros), 1) if registros else None,
            }
        total = len(self.asistencias)
        presentes_clase = sum(1 for r in self.asistencias if r['presente'])
        return {
            'por_estudiante': por_estudiante,
            'clase': {'registrados': total, 'presentes': presentes_clase,
                      'porcentaje': round(100 * presentes_clase / total, 1) if total else None},
        }

    def registrar_asistencia(self, datos):
        with self.lock:
            estudiante_id = datos.get('estudiante_id')
            self._validar_estudiante(estudiante_id)
            fecha = self._fecha(datos.get('fecha'))
            presente = datos.get('presente')
            if not isinstance(presente, bool):
                raise ErrorValidacion('Presente debe ser verdadero o falso.')
            def mutacion():
                existente = next((r for r in self.asistencias if r['estudiante_id'] == estudiante_id
                                  and r['fecha'] == fecha), None)
                if existente is not None:
                    existente['presente'] = presente
                    return existente
                registro = {'institucion_id': INSTITUCION, 'curso_id': CURSO,
                            'estudiante_id': estudiante_id, 'fecha': fecha, 'presente': presente}
                self.asistencias.append(registro)
                return registro
            return self._mutar(mutacion)

    def registrar_entrega(self, datos):
        with self.lock:
            estudiante_id = datos.get('estudiante_id')
            self._validar_estudiante(estudiante_id)
            actividad_id = _id_entero(datos.get('actividad_id'), 'ID de actividad')
            if self.arbol.buscar(actividad_id) is None:
                raise ErrorValidacion('No existe esa actividad publicada.')
            if any(e['actividad_id'] == actividad_id and e['estudiante_id'] == estudiante_id
                   for e in self.entregas):
                raise ErrorValidacion('Esta entrega ya está registrada.')
            def mutacion():
                entrega = {'institucion_id': INSTITUCION, 'actividad_id': actividad_id,
                           'estudiante_id': estudiante_id, 'fecha': date.today().isoformat()}
                self.entregas.append(entrega)
                return entrega
            return self._mutar(mutacion)

    def solicitar_ayuda(self, datos):
        with self.lock:
            estudiante_id = datos.get('estudiante_id')
            self._validar_estudiante(estudiante_id)
            mensaje = self._texto(datos.get('mensaje'), 'Pregunta', 5, 240)
            ids = [s['id'] for s in self.cola.recorrer() + self.atendidas]
            def mutacion():
                nueva = {'id': max(ids, default=0) + 1,
                         'institucion_id': INSTITUCION, 'estudiante_id': estudiante_id,
                         'mensaje': mensaje, 'fecha': date.today().isoformat()}
                self.cola.encolar(nueva)
                return nueva
            return self._mutar(mutacion)

    def atender_siguiente(self):
        with self.lock:
            if self.cola.ver_frente() is None:
                raise ErrorValidacion('No hay solicitudes en espera.')
            def mutacion():
                solicitud = self.cola.desencolar()
                atendida = dict(solicitud)
                atendida['atendida_el'] = marca_tiempo()
                self.atendidas.append(atendida)
                return atendida
            return self._mutar(mutacion)

    def buscar_actividad(self, clave):
        with self.lock:
            resultado = self.arbol.buscar(_id_entero(clave, 'ID de actividad'))
            return deepcopy(resultado)

    def calcular_ruta(self, inicio, destino):
        if inicio not in TEMAS or destino not in TEMAS:
            raise ErrorValidacion('Selecciona dos temas existentes.')
        return self.grafo.ruta_mas_corta(inicio, destino)

    def _contexto_ia(self, estudiante_id, objetivo='', tema=''):
        entregadas = {x['actividad_id'] for x in self.entregas if x['estudiante_id'] == estudiante_id}
        resumen = self._resumen_asistencia()['por_estudiante'][estudiante_id]
        actividades_publicas = [
            {'id': a['id'], 'titulo': a['titulo'], 'tema': a['tema'], 'fecha': a['fecha']}
            for a in self.actividades
        ]
        ruta = self.grafo.ruta_mas_corta('Fundamentos', tema) if tema in TEMAS else []
        publico = {
            'actividades': actividades_publicas,
            'fechas_actividades': [a['fecha'] for a in actividades_publicas],
            'entregadas_ids': sorted(entregadas),
            'pendientes_ids': sorted(a['id'] for a in self.actividades if a['id'] not in entregadas),
            'ruta_bfs': ruta,
            'tamano_cola': self.cola.tamano,
            'porcentaje_asistencia': resumen['porcentaje'],
        }
        return {
            'objetivo': objetivo, 'tema': tema, 'publico': publico,
            'rol': 'estudiante', 'estudiante_id': estudiante_id,
            'actividades_interno': deepcopy(self.actividades),
            'entregas_interno': deepcopy(self.entregas),
            'cola_interna': ColaInstantanea(self.cola.tamano, deepcopy(self.cola.ver_frente())),
            'asistencias_interno': deepcopy(self.asistencias),
            'grafo_interno': deepcopy(self.grafo), 'temas_interno': tuple(TEMAS),
        }

    def conversar_detallado(self, datos):
        with self.lock:
            mensaje = self._texto(datos.get('mensaje'), 'Mensaje', 1, 500)
            rol = datos.get('rol', 'estudiante')
            if rol not in ('estudiante', 'docente'):
                raise ErrorValidacion('Rol no válido.')
            estudiante_id = datos.get('estudiante_id', 'e1')
            self._validar_estudiante(estudiante_id)
            contexto = self._contexto_ia(estudiante_id)
            contexto['rol'] = rol
        return self.ia.responder_chat(mensaje, contexto)

    def conversar(self, datos):
        return self.conversar_detallado(datos)['respuesta']
