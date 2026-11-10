"""Cursos, contenido docente y horarios persistidos fuera del estado histórico."""
from copy import deepcopy
from datetime import date
from pathlib import Path
import re
import secrets
import unicodedata
from threading import RLock

from .archivos import AlmacenJSON, ErrorDatos
from .cuentas import ErrorAcceso
from .estructuras import GrafoAprendizaje
from .servicio import CURSO, ErrorValidacion, RELACIONES, ServicioGrace, TEMAS


VERSION_CURSOS = 1
DIAS_SEMANA = 5
CAMPOS_SYLLABUS = ('objetivos', 'contenidos', 'organizacion')


class Cursos:
    def __init__(self, carpeta, cuentas, principal):
        self.almacen = AlmacenJSON(carpeta)
        self.datos_cursos = AlmacenJSON(Path(carpeta) / 'cursos')
        self.cuentas = cuentas
        self.lock = RLock()
        self.servicios = {}
        self.ia = principal.ia
        self._inicializar()
        self._leer()

    def _inicializar(self):
        marcador = self.almacen.carpeta / '.cursos_inicializados'
        if self.almacen.existe('cursos.json'):
            marcador.touch(exist_ok=True)
            return
        if marcador.exists():
            raise ErrorDatos('Falta cursos.json; recupera una copia antes de continuar.')
        profesor = next((c for c in self.cuentas.listar() if c['rol'] == 'profesor'), None)
        if profesor is None:
            raise ErrorDatos('No hay profesor para conservar el curso principal.')

        original = self.almacen.leer('estado.json')
        if not isinstance(original, dict):
            raise ErrorDatos('No se puede migrar el estado académico existente.')
        respaldo = AlmacenJSON(self.datos_cursos.carpeta / 'migraciones')
        if not respaldo.existe('estado-anterior.json'):
            respaldo.guardar('estado-anterior.json', original)

        curso = {
            'id': 'principal',
            'nombre': 'Programación Estructurada',
            'descripcion': 'Curso del prototipo local.',
            'seccion': 'Grupo 6',
            'profesor_id': profesor['id'],
            'estudiantes': [],
            'temas': [{'id': i, 'nombre': tema, 'publicada': True}
                      for i, tema in enumerate(TEMAS, 1)],
            'syllabus': {campo: '' for campo in CAMPOS_SYLLABUS} | {'publicada': False},
            'horarios': [],
            'sesiones': [],
        }
        self.almacen.guardar('cursos.json', {'version': VERSION_CURSOS, 'cursos': [curso]})
        marcador.touch(exist_ok=True)

    def _leer(self):
        datos = self.almacen.leer('cursos.json')
        try:
            if (not isinstance(datos, dict) or type(datos.get('version')) is not int or
                    datos['version'] != VERSION_CURSOS or not isinstance(datos.get('cursos'), list)):
                raise ValueError
            cursos = datos['cursos']
            ids = set()
            profesores = {c['id'] for c in self.cuentas.listar() if c['rol'] == 'profesor'}
            estudiantes = {c['estudiante_id'] for c in self.cuentas.listar() if c['rol'] == 'estudiante'}
            for curso in cursos:
                claves = {'id', 'nombre', 'descripcion', 'seccion', 'profesor_id',
                          'estudiantes', 'temas', 'syllabus', 'horarios', 'sesiones'}
                if not isinstance(curso, dict) or set(curso) != claves:
                    raise ValueError
                if (not isinstance(curso['id'], str) or
                        not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', curso['id']) or
                        curso['id'] in ids):
                    raise ValueError
                ids.add(curso['id'])
                if curso['profesor_id'] not in profesores:
                    raise ValueError
                for campo, limite in (('nombre', 120), ('descripcion', 2000), ('seccion', 80)):
                    if not isinstance(curso[campo], str) or len(curso[campo]) > limite:
                        raise ValueError
                if not curso['nombre'].strip():
                    raise ValueError
                roster = curso['estudiantes']
                if (not isinstance(roster, list) or len(set(roster)) != len(roster) or
                        any(not isinstance(e, str) or e not in estudiantes for e in roster)):
                    raise ValueError
                temas = curso['temas']
                if not isinstance(temas, list) or len(temas) > 50:
                    raise ValueError
                tema_ids, nombres = set(), set()
                for tema in temas:
                    if (not isinstance(tema, dict) or set(tema) != {'id', 'nombre', 'publicada'} or
                            type(tema['id']) is not int or tema['id'] < 1 or
                            not isinstance(tema['nombre'], str) or not tema['nombre'].strip() or
                            len(tema['nombre']) > 80 or type(tema['publicada']) is not bool or
                            tema['id'] in tema_ids or tema['nombre'].casefold() in nombres):
                        raise ValueError
                    tema_ids.add(tema['id'])
                    nombres.add(tema['nombre'].casefold())
                syllabus = curso['syllabus']
                if (not isinstance(syllabus, dict) or
                        set(syllabus) != set(CAMPOS_SYLLABUS) | {'publicada'} or
                        type(syllabus['publicada']) is not bool or
                        any(not isinstance(syllabus[c], str) or len(syllabus[c]) > 4000
                            for c in CAMPOS_SYLLABUS)):
                    raise ValueError
                if not isinstance(curso['horarios'], list) or not isinstance(curso['sesiones'], list):
                    raise ValueError
                for horario in curso['horarios']:
                    self._validar_horario(horario)
                sesiones = set()
                for sesion in curso['sesiones']:
                    self._validar_sesion(sesion, curso)
                    if sesion['id'] in sesiones:
                        raise ValueError
                    sesiones.add(sesion['id'])
            if 'principal' not in ids:
                raise ValueError
            self._validar_conflictos(datos)
        except (KeyError, TypeError, ValueError, AttributeError, ErrorValidacion):
            raise ErrorDatos('Registro de cursos inválido; acceso cerrado hasta recuperar los datos.') from None
        return datos

    def _mutar(self, accion):
        with self.lock:
            datos = deepcopy(self._leer())
            resultado = accion(datos)
            self._validar_conflictos(datos)
            self.almacen.guardar('cursos.json', datos)
            return deepcopy(resultado)

    def _roster(self, curso):
        if curso['id'] == 'principal':
            return [e['id'] for e in self.cuentas.estudiantes()]
        return list(curso['estudiantes'])

    @staticmethod
    def _obtener(datos, curso_id):
        if not isinstance(curso_id, str):
            raise ErrorValidacion('Curso inválido.')
        curso = next((c for c in datos['cursos'] if c['id'] == curso_id), None)
        if curso is None:
            raise ErrorAcceso(404, 'Curso no encontrado.')
        return curso

    def _autorizar(self, curso, usuario, escritura=False, contenido=False, publicar=False, horario=False):
        rol = usuario['rol']
        if rol == 'estudiante':
            permitido = not escritura and usuario['estudiante_id'] in self._roster(curso)
        elif rol == 'profesor':
            permitido = curso['profesor_id'] == usuario['id']
        else:
            permitido = rol == 'coordinador' and not publicar and (
                not escritura or not contenido or horario
            )
        if not permitido:
            raise ErrorAcceso(403, 'Tu cuenta no tiene permiso para esta operación en el curso.')

    def _vista(self, curso, usuario):
        resultado = deepcopy(curso)
        resultado['estudiantes'] = self._roster(curso)
        if usuario['rol'] == 'estudiante':
            resultado['estudiantes'] = [usuario['estudiante_id']]
            resultado['temas'] = [t for t in resultado['temas'] if t['publicada']]
            if not resultado['syllabus']['publicada']:
                resultado['syllabus'] = {campo: '' for campo in CAMPOS_SYLLABUS} | {'publicada': False}
            resultado['sesiones'] = [s for s in resultado['sesiones'] if s['publicada']]
        return resultado

    def listar(self, usuario):
        with self.lock:
            datos = self._leer()
            salida = []
            for curso in datos['cursos']:
                try:
                    self._autorizar(curso, usuario)
                except ErrorAcceso as error:
                    if error.codigo == 403:
                        continue
                    raise
                salida.append(self._vista(curso, usuario))
            return {'cursos': salida}

    def personas(self, usuario):
        if usuario['rol'] != 'coordinador':
            raise ErrorAcceso(403, 'Solo coordinación puede administrar asignaciones.')
        cuentas = self.cuentas.listar()
        return {
            'profesores': [{'id': c['id'], 'nombre': c['nombre']}
                           for c in cuentas if c['rol'] == 'profesor'],
            'estudiantes': [{'id': c['estudiante_id'], 'nombre': c['nombre']}
                            for c in cuentas if c['rol'] == 'estudiante'],
        }

    def _metadata(self, datos, usuario, anterior=None):
        anterior = anterior or {}
        permitidos = {'nombre', 'descripcion', 'seccion', 'profesor_id', 'estudiantes', 'curso_id'}
        if not isinstance(datos, dict) or not set(datos).issubset(permitidos):
            raise ErrorValidacion('Campos de curso inválidos.')
        if usuario['rol'] not in ('profesor', 'coordinador'):
            raise ErrorAcceso(403, 'Solo docentes y coordinación pueden administrar cursos.')
        campos = {}
        for nombre, maximo in (('nombre', 120), ('descripcion', 2000), ('seccion', 80)):
            valor = datos.get(nombre, anterior.get(nombre, ''))
            minimo = 1 if nombre == 'nombre' else 0
            campos[nombre] = ServicioGrace._texto(valor, nombre, minimo, maximo)
        profesor_id = datos.get('profesor_id', anterior.get('profesor_id', ''))
        if usuario['rol'] == 'profesor':
            if profesor_id and profesor_id != usuario['id']:
                raise ErrorAcceso(403, 'Un profesor solo puede asignarse a sí mismo.')
            profesor_id = usuario['id']
        profesores = {c['id'] for c in self.cuentas.listar() if c['rol'] == 'profesor'}
        if profesor_id not in profesores:
            raise ErrorValidacion('Selecciona un profesor válido.')
        if usuario['rol'] == 'profesor' and anterior:
            if datos.get('estudiantes', anterior['estudiantes']) != anterior['estudiantes']:
                raise ErrorAcceso(403, 'Solo coordinación puede modificar la matrícula.')
            if profesor_id != anterior['profesor_id']:
                raise ErrorAcceso(403, 'Solo coordinación puede cambiar el profesor responsable.')
        roster = datos.get('estudiantes', anterior.get('estudiantes', []))
        validos = {c['estudiante_id'] for c in self.cuentas.listar() if c['rol'] == 'estudiante'}
        if (not isinstance(roster, list) or len(set(roster)) != len(roster) or
                any(not isinstance(e, str) or e not in validos for e in roster)):
            raise ErrorValidacion('Matrícula inválida o duplicada.')
        return {**campos, 'profesor_id': profesor_id, 'estudiantes': list(roster)}

    def crear(self, datos, usuario):
        if usuario['rol'] != 'coordinador':
            raise ErrorAcceso(403, 'Solo coordinación puede crear cursos.')
        curso_id = None

        def accion(registro):
            nonlocal curso_id
            curso = self._metadata(datos, usuario)
            slug = unicodedata.normalize('NFKD', curso['nombre']).encode('ascii', 'ignore').decode().lower()
            slug = re.sub(r'[^a-z0-9]+', '-', slug).strip('-')[:36].strip('-') or 'curso'
            curso_id = f'{slug}-{secrets.token_hex(8)}'
            curso.update({
                'id': curso_id,
                'temas': [],
                'syllabus': {campo: '' for campo in CAMPOS_SYLLABUS} | {'publicada': False},
                'horarios': [],
                'sesiones': [],
            })
            registro['cursos'].append(curso)
            return curso

        resultado = self._mutar(accion)
        try:
            ServicioGrace(self.datos_cursos.carpeta / curso_id, curso_id=curso_id,
                          nombre=resultado['nombre'], temas=[], vacio=True)
        except Exception:
            with self.lock:
                datos_actuales = self._leer()
                datos_actuales['cursos'] = [c for c in datos_actuales['cursos'] if c['id'] != curso_id]
                self.almacen.guardar('cursos.json', datos_actuales)
            raise
        return resultado

    def editar(self, datos, usuario):
        if not isinstance(datos, dict):
            raise ErrorValidacion('El curso debe ser un objeto.')

        def accion(registro):
            curso = self._obtener(registro, datos.get('curso_id', ''))
            self._autorizar(curso, usuario, escritura=True)
            curso.update(self._metadata(datos, usuario, curso))
            return self._vista(curso, usuario)

        return self._mutar(accion)

    def contenido(self, operacion, datos, usuario):
        if not isinstance(datos, dict):
            raise ErrorValidacion('El contenido debe ser un objeto.')

        def accion(registro):
            curso = self._obtener(registro, datos.get('curso_id', ''))
            publicar = operacion in ('publicar_tema', 'publicar_syllabus', 'publicar_sesion')
            horario = operacion == 'horarios'
            self._autorizar(curso, usuario, escritura=True, contenido=True,
                            publicar=publicar, horario=horario)
            if operacion == 'temas':
                return self._mutar_tema(curso, datos)
            if operacion == 'syllabus':
                return self._guardar_syllabus(curso, datos)
            if operacion == 'publicar_syllabus':
                if any(not curso['syllabus'][c].strip() for c in CAMPOS_SYLLABUS):
                    raise ErrorValidacion('Completa objetivos, contenidos y organización antes de publicar.')
                curso['syllabus']['publicada'] = True
                return curso['syllabus']
            if operacion == 'sesiones':
                return self._guardar_sesion(curso, datos)
            if operacion == 'publicar_sesion':
                sesion_id = self._entero(datos.get('id'), 'ID de sesión')
                sesion = next((s for s in curso['sesiones'] if s['id'] == sesion_id), None)
                if sesion is None:
                    raise ErrorValidacion('Sesión no encontrada.')
                if sesion['tema']:
                    tema = next((t for t in curso['temas'] if t['nombre'] == sesion['tema']), None)
                    if tema is None:
                        raise ErrorValidacion('El tema no está disponible. Edita la sesión y elige un tema del curso.')
                    if not tema['publicada']:
                        if datos.get('publicar_tema') is not True:
                            raise ErrorValidacion('El tema está en borrador. Confirma la publicación del tema y la sesión.')
                        tema['publicada'] = True
                sesion['publicada'] = True
                return sesion
            if operacion == 'horarios':
                horarios = datos.get('horarios')
                if not isinstance(horarios, list) or len(horarios) > 100:
                    raise ErrorValidacion('Envía hasta 100 bloques de horario.')
                curso['horarios'] = [self._validar_horario(h) for h in horarios]
                return curso['horarios']
            raise ErrorAcceso(404, 'Operación de curso no encontrada.')

        return self._mutar(accion)

    @staticmethod
    def _mutar_tema(curso, datos):
        accion = datos.get('accion', 'agregar')
        temas = curso['temas']
        if accion == 'agregar':
            nombre = ServicioGrace._texto(datos.get('nombre'), 'Tema', 1, 80)
            if len(temas) >= 50 or any(t['nombre'].casefold() == nombre.casefold() for t in temas):
                raise ErrorValidacion('Tema repetido o límite de 50 temas alcanzado.')
            tema = {'id': max((t['id'] for t in temas), default=0) + 1,
                    'nombre': nombre, 'publicada': False}
            temas.append(tema)
            return tema
        if accion == 'editar':
            tema_id = Cursos._entero(datos.get('id'), 'ID de tema')
            tema = next((t for t in temas if t['id'] == tema_id), None)
            if tema is None:
                raise ErrorValidacion('Tema no encontrado.')
            nombre = ServicioGrace._texto(datos.get('nombre'), 'Tema', 1, 80)
            if any(t['id'] != tema_id and t['nombre'].casefold() == nombre.casefold() for t in temas):
                raise ErrorValidacion('Ya existe un tema con ese nombre.')
            anterior = tema['nombre']
            tema['nombre'] = nombre
            if nombre != anterior:
                tema['publicada'] = False
                for sesion in curso['sesiones']:
                    if sesion['tema'] == anterior:
                        sesion['tema'] = nombre
                        sesion['publicada'] = False
            return tema
        if accion == 'ordenar':
            orden = datos.get('ids')
            if (not isinstance(orden, list) or len(orden) != len(temas) or
                    set(orden) != {t['id'] for t in temas}):
                raise ErrorValidacion('El orden debe incluir cada tema exactamente una vez.')
            por_id = {t['id']: t for t in temas}
            curso['temas'] = [por_id[i] for i in orden]
            return curso['temas']
        if accion == 'publicar':
            tema_id = Cursos._entero(datos.get('id'), 'ID de tema')
            tema = next((t for t in temas if t['id'] == tema_id), None)
            if tema is None:
                raise ErrorValidacion('Tema no encontrado.')
            if type(datos.get('publicada')) is not bool:
                raise ErrorValidacion('La publicación debe ser verdadera o falsa.')
            tema['publicada'] = datos['publicada']
            if not tema['publicada']:
                for sesion in curso['sesiones']:
                    if sesion['tema'] == tema['nombre']:
                        sesion['publicada'] = False
            return tema
        raise ErrorValidacion('Acción de tema inválida.')

    @staticmethod
    def _guardar_syllabus(curso, datos):
        campos = {c: ServicioGrace._texto(datos.get(c), c, 0, 4000) for c in CAMPOS_SYLLABUS}
        syllabus = curso['syllabus']
        if any(syllabus[c] != campos[c] for c in CAMPOS_SYLLABUS):
            syllabus['publicada'] = False
        syllabus.update(campos)
        return syllabus

    def _guardar_sesion(self, curso, datos):
        campos = {'id', 'curso_id', 'titulo', 'tema', 'fecha', 'descripcion',
                  'actividades', 'inicio', 'fin', 'edificio', 'piso', 'aula'}
        if set(datos) - campos:
            raise ErrorValidacion('Campos de sesión inválidos; la publicación es una acción separada.')
        titulo = ServicioGrace._texto(datos.get('titulo'), 'Título', 1, 120)
        tema = datos.get('tema')
        if not isinstance(tema, str) or (tema and not any(t['nombre'] == tema for t in curso['temas'])):
            raise ErrorValidacion('Selecciona un tema de este curso.')
        fecha = ServicioGrace._fecha(datos.get('fecha'))
        descripcion = ServicioGrace._texto(datos.get('descripcion'), 'Descripción', 1, 3000)
        actividades = ServicioGrace._texto(datos.get('actividades', ''), 'Actividades', 0, 3000)
        hora = self._intervalo(datos.get('inicio'), datos.get('fin'))
        aula = self._validar_aula(datos)
        sesion_id = self._entero(datos['id'], 'ID de sesión') if 'id' in datos else None
        sesion = {'id': sesion_id or max((s['id'] for s in curso['sesiones']), default=0) + 1,
                  'titulo': titulo, 'tema': tema, 'fecha': fecha, 'descripcion': descripcion,
                  'actividades': actividades, **hora, **aula, 'publicada': False}
        existente = next((s for s in curso['sesiones'] if s['id'] == sesion['id']), None)
        if sesion_id and existente is None:
            raise ErrorValidacion('Sesión no encontrada.')
        if existente:
            curso['sesiones'][curso['sesiones'].index(existente)] = sesion
        else:
            curso['sesiones'].append(sesion)
        return sesion

    @staticmethod
    def _entero(valor, nombre):
        if type(valor) is not int or valor < 1:
            raise ErrorValidacion(f'{nombre} inválido.')
        return valor

    @staticmethod
    def _intervalo(inicio, fin):
        patron = r'(?:[01][0-9]|2[0-3]):[0-5][0-9]'
        if not isinstance(inicio, str) or not re.fullmatch(patron, inicio):
            raise ErrorValidacion('Hora de inicio inválida; usa HH:mm.')
        if not isinstance(fin, str) or not re.fullmatch(patron, fin) or fin <= inicio:
            raise ErrorValidacion('La hora final debe ser posterior al inicio.')
        return {'inicio': inicio, 'fin': fin}

    @classmethod
    def _validar_aula(cls, datos):
        edificio, aula, piso = datos.get('edificio'), datos.get('aula'), datos.get('piso')
        if not isinstance(edificio, str) or not re.fullmatch(r'[A-Z]', edificio):
            raise ErrorValidacion('Edificio inválido; usa una letra mayúscula.')
        if not isinstance(aula, str) or not re.fullmatch(
                edificio + r'-([1-9])(?:0[1-9]|10)', aula):
            raise ErrorValidacion('Aula inválida; usa edificio-piso y número, por ejemplo A-101.')
        piso_aula = int(aula[2])
        if type(piso) is not int or piso != piso_aula:
            raise ErrorValidacion('El piso no coincide con el aula.')
        return {'edificio': edificio, 'piso': piso, 'aula': aula}

    @classmethod
    def _validar_horario(cls, datos):
        if not isinstance(datos, dict) or type(datos.get('dia')) is not int or not 0 <= datos['dia'] < DIAS_SEMANA:
            raise ErrorValidacion('El día debe ser un entero de lunes (0) a viernes (4).')
        return {'dia': datos['dia'], **cls._intervalo(datos.get('inicio'), datos.get('fin')),
                **cls._validar_aula(datos)}

    def _validar_sesion(self, sesion, curso):
        claves = {'id', 'titulo', 'tema', 'fecha', 'descripcion', 'actividades',
                  'inicio', 'fin', 'edificio', 'piso', 'aula', 'publicada'}
        if not isinstance(sesion, dict) or set(sesion) != claves:
            raise ValueError
        self._entero(sesion['id'], 'ID de sesión')
        for campo, limite in (('titulo', 120), ('descripcion', 3000), ('actividades', 3000)):
            if not isinstance(sesion[campo], str) or len(sesion[campo]) > limite:
                raise ValueError
        if not sesion['titulo'].strip() or not sesion['descripcion'].strip():
            raise ValueError
        if not isinstance(sesion['tema'], str) or (
                sesion['tema'] and not any(t['nombre'] == sesion['tema'] for t in curso['temas'])):
            raise ValueError
        if type(sesion['publicada']) is not bool:
            raise ValueError
        try:
            if date.fromisoformat(sesion['fecha']).isoformat() != sesion['fecha']:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError from None
        self._intervalo(sesion['inicio'], sesion['fin'])
        self._validar_aula(sesion)

    @staticmethod
    def _solapa(a, b):
        return a['inicio'] < b['fin'] and b['inicio'] < a['fin']

    def _validar_conflictos(self, registro):
        eventos = []
        for curso in registro['cursos']:
            roster = set(self._roster(curso))
            for horario in curso['horarios']:
                eventos.append((curso, roster, 'semanal', horario['dia'], horario))
            for sesion in curso['sesiones']:
                eventos.append((curso, roster, 'fecha', sesion['fecha'], sesion))
        for indice, (curso_a, alumnos_a, tipo_a, dia_a, a) in enumerate(eventos):
            for curso_b, alumnos_b, tipo_b, dia_b, b in eventos[indice + 1:]:
                if tipo_a == tipo_b:
                    mismo_dia = dia_a == dia_b
                else:
                    sesion = a if tipo_a == 'fecha' else b
                    mismo_dia = date.fromisoformat(sesion['fecha']).weekday() == (
                        dia_b if tipo_a == 'semanal' else dia_a)
                if not mismo_dia or not self._solapa(a, b):
                    continue
                mismo_bloque = (
                    curso_a['id'] == curso_b['id'] and tipo_a != tipo_b and
                    a['inicio'] == b['inicio'] and a['fin'] == b['fin'] and
                    a['edificio'] == b['edificio'] and a['aula'] == b['aula']
                )
                if mismo_bloque:
                    continue
                conflicto = (
                    curso_a['profesor_id'] == curso_b['profesor_id'] or
                    bool(alumnos_a & alumnos_b) or
                    (a['edificio'], a['aula']) == (b['edificio'], b['aula'])
                )
                if conflicto:
                    raise ErrorValidacion('Horario en conflicto para un estudiante, profesor o aula.')

    def servicio(self, curso_id, usuario):
        with self.lock:
            curso = self._obtener(self._leer(), curso_id)
            if usuario['rol'] not in ('profesor', 'estudiante'):
                raise ErrorAcceso(403, 'Coordinación no tiene acceso a los datos académicos del curso.')
            self._autorizar(curso, usuario)
            carpeta = self.datos_cursos.carpeta / curso_id
            curso_estado_id = curso_id
            if curso_id == 'principal' and not (carpeta / 'estado.json').is_file():
                carpeta = self.almacen.carpeta
                curso_estado_id = CURSO
            if not (carpeta / 'estado.json').is_file():
                raise ErrorDatos('Falta el estado académico del curso; acceso cerrado.')
            clave_servicio = (curso_id, usuario['id'])
            if clave_servicio not in self.servicios:
                self.servicios[clave_servicio] = ServicioGrace(
                    carpeta, curso_id=curso_estado_id, nombre=curso['nombre'],
                    temas=[t['nombre'] for t in curso['temas']], vacio=curso_id != 'principal')
                self.servicios[clave_servicio].ia = self.ia
            servicio = self.servicios[clave_servicio]
        with servicio.lock:
            servicio.nombre = curso['nombre']
            temas = [t['nombre'] for t in curso['temas']
                     if usuario['rol'] != 'estudiante' or t['publicada']]
            servicio.temas = temas
            servicio.grafo = GrafoAprendizaje()
            for tema in temas:
                servicio.grafo.agregar_tema(tema)
            for origen, destino in RELACIONES:
                if origen in temas and destino in temas:
                    servicio.grafo.agregar_relacion(origen, destino)
            servicio.registro_estudiantes = lambda: self._estudiantes(curso_id)
            servicio.contexto_curso = lambda: self._contexto(curso_id, usuario)
        return servicio

    def _contexto(self, curso_id, usuario):
        with self.lock:
            curso = self._obtener(self._leer(), curso_id)
            return self._vista(curso, usuario)

    def _estudiantes(self, curso_id):
        with self.lock:
            curso = self._obtener(self._leer(), curso_id)
            roster = set(self._roster(curso))
        return [e for e in self.cuentas.estudiantes() if e['id'] in roster]
