"""Asistencia por sesión y revisión institucional de evidencias."""
import base64
from datetime import date
from pathlib import PurePath
import secrets

from .archivos import ErrorDatos
from .cuentas import ErrorAcceso
from .perfiles import catalogo
from .servicio import ErrorValidacion, ServicioGrace
from .trabajo import validar_archivo

ESTADOS = ('presente', 'ausente', 'justificada', 'injustificada')
META_MINUTOS = 25 * 60
ARCHIVO = 'seguimiento.json'
LIMITE_EVIDENCIAS = 50 * 1024 * 1024


class Seguimiento:
    def __init__(self, cursos):
        self.cursos = cursos

    def _leer(self):
        datos = self.cursos.almacen.leer(ARCHIVO, {
            'version': 1, 'asistencias': [], 'solicitudes': [], 'eventos': [],
        })
        if not isinstance(datos, dict) or datos.get('version') != 1 or any(
                not isinstance(datos.get(k), list) for k in ('asistencias', 'solicitudes', 'eventos')):
            raise ErrorDatos('Registro de seguimiento inválido.')
        return datos

    @staticmethod
    def _sin_archivo(solicitud):
        return {k: v for k, v in solicitud.items() if k != 'contenido'}

    @staticmethod
    def _buscar(registros, identificador):
        registro = next((r for r in registros if r['id'] == identificador), None)
        if registro is None:
            raise ErrorAcceso(404, 'Registro no disponible.')
        return registro

    @staticmethod
    def _evento_visible(evento, usuario):
        return (usuario['rol'] == 'coordinador' or not evento['facultad_id']
                or usuario.get('facultad_id') == evento['facultad_id'])

    def vista(self, usuario):
        with self.cursos.lock:
            datos = self._leer()
            rol = usuario['rol']
            alumno = usuario.get('estudiante_id')
            solicitudes = [self._sin_archivo(s) for s in datos['solicitudes']
                           if rol == 'coordinador' or alumno == s['estudiante_id']]
            historial = []
            if rol == 'estudiante':
                cursos = {c['id']: c for c in self.cursos.listar(usuario)['cursos']}
                for fila in datos['asistencias']:
                    if fila['estudiante_id'] != alumno or fila['curso_id'] not in cursos:
                        continue
                    curso = cursos[fila['curso_id']]
                    sesion = next((s for s in curso['sesiones'] if s['id'] == fila['sesion_id']), None)
                    if sesion:
                        historial.append({**fila, 'curso': curso['nombre'], 'sesion': sesion['titulo'],
                                          'fecha': sesion['fecha']})
            return {'eventos': [e for e in datos['eventos'] if self._evento_visible(e, usuario)],
                    'solicitudes': solicitudes, 'asistencias': historial,
                    'minutos': sum(s.get('minutos', 0) for s in solicitudes
                                   if s['tipo'] == 'horas' and s['estado'] == 'aprobada'),
                    'meta_minutos': META_MINUTOS}

    def _sesion(self, curso_id, sesion_id, usuario):
        curso = self.cursos._obtener(self.cursos._leer(), curso_id)
        if usuario['rol'] not in ('profesor', 'estudiante'):
            raise ErrorAcceso(403, 'La asistencia corresponde al profesor y sus estudiantes.')
        self.cursos._autorizar(curso, usuario)
        sesion = next((s for s in curso['sesiones'] if str(s['id']) == str(sesion_id) and s['publicada']), None)
        if sesion is None:
            raise ErrorAcceso(404, 'Sesión publicada no disponible.')
        return curso, sesion

    @staticmethod
    def _filas(registros, curso, sesion):
        return [r for r in registros if r.get('curso_id') == curso['id'] and r.get('sesion_id') == sesion['id']]

    def asistencia(self, curso_id, sesion_id, usuario):
        with self.cursos.lock:
            curso, sesion = self._sesion(curso_id, sesion_id, usuario)
            datos = self._leer()
            filas = self._filas(datos['asistencias'], curso, sesion)
            justificaciones = self._filas(datos['solicitudes'], curso, sesion)
            if usuario['rol'] == 'estudiante':
                alumno = usuario['estudiante_id']
                return {'asistencias': [r for r in filas if r['estudiante_id'] == alumno],
                        'solicitudes': [self._sin_archivo(r) for r in justificaciones
                                        if r['estudiante_id'] == alumno]}
            matricula = set(self.cursos._roster(curso))
            return {'asistencias': filas,
                    'estudiantes': [e for e in self.cursos.cuentas.estudiantes() if e['id'] in matricula],
                    'solicitudes': [{'estudiante_id': j['estudiante_id'], 'estado': j['estado']}
                                    for j in justificaciones if j['estado'] == 'aprobada']}

    def marcar_lote(self, entrada, usuario):
        """Guarda de una vez la lista revisada por el profesor."""
        if usuario['rol'] != 'profesor':
            raise ErrorAcceso(403, 'Solo el profesor del curso puede confirmar la asistencia.')
        if not isinstance(entrada, dict) or set(entrada) != {'curso_id', 'sesion_id', 'registros'}:
            raise ErrorValidacion('La confirmación de asistencia no tiene el formato esperado.')
        registros = entrada['registros']
        if not isinstance(registros, list) or not registros:
            raise ErrorValidacion('Revisa la lista de asistencia antes de confirmar.')
        with self.cursos.lock:
            curso, sesion = self._sesion(entrada['curso_id'], entrada['sesion_id'], usuario)
            if date.fromisoformat(sesion['fecha']) > date.today():
                raise ErrorAcceso(409, 'La fecha de la sesión aún no ha llegado.')
            roster = set(self.cursos._roster(curso))
            filas = {}
            for registro in registros:
                if (not isinstance(registro, dict) or set(registro) != {'estudiante_id', 'estado'} or
                        not isinstance(registro['estudiante_id'], str) or
                        registro['estudiante_id'] in filas or
                        registro['estado'] not in ('presente', 'ausente')):
                    raise ErrorValidacion('La lista contiene un estado o estudiante inválido.')
                filas[registro['estudiante_id']] = registro['estado']
            if set(filas) != roster:
                raise ErrorValidacion('La confirmación debe incluir a toda la matrícula de la sesión.')

            datos = self._leer()
            existentes = self._filas(datos['asistencias'], curso, sesion)
            por_estudiante = {r['estudiante_id']: r for r in existentes}
            for estudiante_id, estado in filas.items():
                fila = por_estudiante.get(estudiante_id)
                if fila is None:
                    fila = {'curso_id': curso['id'], 'sesion_id': sesion['id'],
                            'estudiante_id': estudiante_id}
                    datos['asistencias'].append(fila)
                fila['estado'] = estado
            self.cursos.almacen.guardar(ARCHIVO, datos)
            return {'curso_id': curso['id'], 'sesion_id': sesion['id'], 'cantidad': len(filas)}

    def descargar(self, solicitud_id, usuario):
        with self.cursos.lock:
            solicitud = self._buscar(self._leer()['solicitudes'], solicitud_id)
            if usuario['rol'] != 'coordinador' and usuario.get('estudiante_id') != solicitud['estudiante_id']:
                raise ErrorAcceso(403, 'Evidencia privada.')
            return solicitud['nombre'], base64.b64decode(solicitud['contenido'])

    def mutar(self, entrada, usuario):
        accion = entrada.get('accion')
        permisos = {'evento': 'coordinador', 'decision': 'coordinador', 'marcar': 'profesor',
                    'solicitar': 'estudiante', 'justificar': 'estudiante', 'horas': 'estudiante'}
        if not isinstance(accion, str) or accion not in permisos or permisos[accion] != usuario['rol']:
            raise ErrorAcceso(403, 'Tu cuenta no puede realizar esta operación.')
        adjunto = self._adjunto(entrada, accion) if accion in ('justificar', 'horas') else None
        with self.cursos.lock:
            datos = self._leer()
            if accion == 'evento':
                resultado = self._crear_evento(datos, entrada)
            elif accion == 'decision':
                resultado = self._decidir(datos, entrada)
            elif accion == 'horas':
                resultado = self._solicitar_horas(datos, entrada, usuario, adjunto)
            else:
                resultado = self._mutar_asistencia(datos, entrada, usuario, adjunto)
            if sum(s['bytes'] for s in datos['solicitudes']) > LIMITE_EVIDENCIAS:
                raise ErrorAcceso(413, 'Se alcanzó el espacio disponible para evidencias.')
            self.cursos.almacen.guardar(ARCHIVO, datos)
            return self._sin_archivo(resultado)

    @staticmethod
    def _adjunto(entrada, accion):
        nombre = entrada.get('nombre')
        extensiones = {'.jpg', '.jpeg', '.png'}
        if accion == 'justificar':
            extensiones.add('.pdf')
        if not isinstance(nombre, str) or PurePath(nombre).suffix.lower() not in extensiones:
            raise ErrorValidacion('Usa JPG o PNG. Las constancias también admiten PDF.')
        return validar_archivo(nombre, entrada.get('contenido'))

    def _mutar_asistencia(self, datos, entrada, usuario, adjunto):
        curso, sesion = self._sesion(entrada.get('curso_id'), entrada.get('sesion_id'), usuario)
        if date.fromisoformat(sesion['fecha']) > date.today():
            raise ErrorAcceso(409, 'La fecha de la sesión aún no ha llegado.')
        alumno = usuario.get('estudiante_id') if usuario['rol'] == 'estudiante' else entrada.get('estudiante_id')
        if alumno not in self.cursos._roster(curso):
            raise ErrorValidacion('Estudiante fuera de la matrícula.')
        clave = {'curso_id': curso['id'], 'sesion_id': sesion['id'], 'estudiante_id': alumno}
        fila = next((r for r in datos['asistencias'] if all(r.get(k) == v for k, v in clave.items())), None)
        accion = entrada['accion']
        if accion == 'justificar':
            if not fila or fila['estado'] not in ('ausente', 'injustificada'):
                raise ErrorAcceso(409, 'Debe existir una ausencia registrada para presentar la constancia.')
            return self._solicitud(datos, usuario, 'justificacion', adjunto,
                                   {**clave, 'titulo': sesion['titulo'], 'curso': curso['nombre']})
        estado = entrada.get('estado') if accion == 'marcar' else 'solicitada'
        if accion == 'marcar' and estado not in ESTADOS:
            raise ErrorValidacion('Estado de asistencia inválido.')
        if accion == 'solicitar' and fila:
            raise ErrorAcceso(409, 'Esta sesión ya tiene un registro de asistencia.')
        if fila is None:
            fila = clave
            datos['asistencias'].append(fila)
        fila['estado'] = estado
        return fila

    @staticmethod
    def _crear_evento(datos, entrada):
        facultad = entrada.get('facultad_id', '')
        if facultad not in ['', *(f['id'] for f in catalogo()['facultades'])]:
            raise ErrorValidacion('Facultad inválida.')
        clase = entrada.get('clase')
        minutos = entrada.get('minutos')
        obligatorio = entrada.get('obligatorio')
        if clase not in ('juego', 'charla', 'evento') or type(minutos) is not int or not 0 <= minutos <= 1440:
            raise ErrorValidacion('Indica un tipo y entre 0 y 1440 minutos.')
        if type(obligatorio) is not bool:
            raise ErrorValidacion('Indica si el evento es obligatorio.')
        evento = {'id': secrets.token_hex(16),
                  'titulo': ServicioGrace._texto(entrada.get('titulo'), 'Título', 1, 120),
                  'descripcion': ServicioGrace._texto(entrada.get('descripcion', ''), 'Descripción', 0, 2000),
                  'fecha': ServicioGrace._fecha(entrada.get('fecha')),
                  'clase': clase, 'facultad_id': facultad, 'minutos': minutos, 'obligatorio': obligatorio}
        datos['eventos'].append(evento)
        return evento

    def _solicitar_horas(self, datos, entrada, usuario, adjunto):
        evento = self._buscar(datos['eventos'], entrada.get('evento_id'))
        if not self._evento_visible(evento, usuario):
            raise ErrorAcceso(403, 'Evento fuera de tu facultad.')
        if not evento['minutos'] or date.fromisoformat(evento['fecha']) > date.today():
            raise ErrorAcceso(409, 'El evento todavía no admite evidencias para acreditar horas.')
        return self._solicitud(datos, usuario, 'horas', adjunto,
                               {'evento_id': evento['id'], 'titulo': evento['titulo'],
                                'minutos': evento['minutos']})

    @staticmethod
    def _solicitud(datos, usuario, tipo, adjunto, clave):
        alumno = usuario['estudiante_id']
        anterior = next((s for s in datos['solicitudes'] if s['tipo'] == tipo and s['estudiante_id'] == alumno
                         and all(s.get(k) == clave[k] for k in ('evento_id', 'curso_id', 'sesion_id')
                                 if k in clave)), None)
        if anterior and anterior['estado'] != 'rechazada':
            raise ErrorAcceso(409, 'Ya existe una solicitud para este registro.')
        if anterior:
            datos['solicitudes'].remove(anterior)
        solicitud = {**clave, **adjunto, 'id': secrets.token_hex(16), 'tipo': tipo, 'estado': 'pendiente',
                     'estudiante_id': alumno, 'estudiante_nombre': usuario['nombre']}
        datos['solicitudes'].append(solicitud)
        return solicitud

    def _decidir(self, datos, entrada):
        solicitud = self._buscar(datos['solicitudes'], entrada.get('solicitud_id'))
        decision = entrada.get('decision')
        if solicitud['estado'] != 'pendiente' or decision not in ('aprobada', 'rechazada'):
            raise ErrorAcceso(409, 'La solicitud ya se revisó o la decisión es inválida.')
        solicitud['comentario'] = ServicioGrace._texto(
            entrada.get('comentario', ''), 'Comentario', 0, 1000)
        solicitud['estado'] = decision
        return solicitud
