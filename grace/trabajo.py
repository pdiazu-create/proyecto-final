"""Recursos y entregas aislados por curso y sesión."""
import base64
import binascii
from datetime import datetime, timezone
import io
import math
from pathlib import PurePath
import re
import secrets
from urllib.parse import urlsplit
from zipfile import BadZipFile, ZipFile

from .archivos import ErrorDatos
from .cuentas import ErrorAcceso
from .materiales import documento, presentacion
from .servicio import ErrorValidacion, ServicioGrace

MAX_ARCHIVO = 3 * 1024 * 1024
LIMITE_CURSO = 40 * 1024 * 1024
EXTENSIONES = {'.pdf', '.docx', '.pptx', '.txt', '.png', '.jpg', '.jpeg', '.mp4'}
CATEGORIAS = ('presentacion', 'lectura', 'video', 'apoyo')
MOMENTOS = ('antes', 'durante', 'despues')


def validar_archivo(nombre, contenido):
    if not isinstance(nombre, str) or not re.fullmatch(r'[\w .()-]{1,120}', nombre):
        raise ErrorValidacion('Nombre de archivo inválido.')
    extension = PurePath(nombre).suffix.lower()
    if extension not in EXTENSIONES or not isinstance(contenido, str):
        raise ErrorValidacion('Usa PDF, DOCX, PPTX, TXT, PNG, JPG o MP4.')
    if len(contenido) > 4 * ((MAX_ARCHIVO + 2) // 3):
        raise ErrorAcceso(413, 'El archivo supera 3 MB.')
    try:
        bruto = base64.b64decode(contenido, validate=True)
    except (ValueError, binascii.Error):
        raise ErrorValidacion('Archivo inválido.') from None
    if not bruto or len(bruto) > MAX_ARCHIVO:
        raise ErrorValidacion('El archivo debe pesar entre 1 byte y 3 MB.')
    firmas = {'.pdf': b'%PDF-', '.png': b'\x89PNG\r\n\x1a\n', '.jpg': b'\xff\xd8\xff', '.jpeg': b'\xff\xd8\xff'}
    if extension in firmas and not bruto.startswith(firmas[extension]):
        raise ErrorValidacion('El archivo no coincide con su extensión.')
    if extension == '.mp4' and bruto[4:8] != b'ftyp':
        raise ErrorValidacion('El archivo no coincide con el formato MP4.')
    if extension == '.txt':
        if '\x00' in bruto.decode('utf-8'):
            raise ErrorValidacion('El archivo TXT debe contener texto.')
    if extension in ('.docx', '.pptx'):
        try:
            with ZipFile(io.BytesIO(bruto)) as paquete:
                miembros = paquete.infolist()
                nombres = {m.filename for m in miembros}
                principal = 'word/document.xml' if extension == '.docx' else 'ppt/presentation.xml'
                if (principal not in nombres or '[Content_Types].xml' not in nombres
                        or len(miembros) > 1000 or sum(m.file_size for m in miembros) > 30 * MAX_ARCHIVO
                        or any('vbaproject' in n.lower() or '/embeddings/' in n.lower() for n in nombres)):
                    raise ErrorValidacion('El documento Office no cumple los requisitos.')
        except BadZipFile:
            raise ErrorValidacion('El documento Office es inválido.') from None
    return {'nombre': nombre, 'contenido': contenido, 'bytes': len(bruto)}


def validar_enlace(valor):
    valor = ServicioGrace._texto(valor, 'Enlace', 8, 1500)
    try:
        url = urlsplit(valor)
        puerto = url.port
    except ValueError:
        raise ErrorValidacion('El enlace no es válido. Pega la dirección HTTPS completa.') from None
    if puerto == 0:
        raise ErrorValidacion('El puerto del enlace no es válido.')
    if url.scheme != 'https' or not url.hostname or url.username or url.password or any(
            c.isspace() or ord(c) < 32 or c == '\\' for c in valor):
        raise ErrorValidacion('Usa un enlace HTTPS sin credenciales.')
    return valor


class TrabajoAcademico:
    def __init__(self, cursos):
        self.cursos = cursos

    def _curso_sesion(self, curso_id, sesion_id, usuario):
        curso = self.cursos._obtener(self.cursos._leer(), curso_id)
        self.cursos._autorizar(curso, usuario)
        if usuario['rol'] not in ('estudiante', 'profesor'):
            raise ErrorAcceso(403, 'Acceso reservado a profesor y estudiantes del curso.')
        sesion = next((s for s in curso['sesiones'] if str(s['id']) == str(sesion_id)), None)
        if not sesion or (usuario['rol'] == 'estudiante' and not sesion['publicada']):
            raise ErrorAcceso(404, 'Sesión no disponible.')
        return curso, sesion

    def _leer(self, curso):
        return self.cursos.datos_cursos.leer(curso['id'] + '-trabajo.json', [])

    @staticmethod
    def _visibles(registros, sesion, usuario):
        estudiante = usuario.get('estudiante_id')
        grupos = {a['id']: TrabajoAcademico._grupo(a, estudiante) for a in registros
                  if a['tipo'] == 'actividad'} if estudiante else {}
        return [r for r in registros if r['sesion_id'] == sesion['id']
                and (not estudiante or r.get('publicada', True))
                and (not estudiante or r['tipo'] != 'pregunta' or r['estudiante_id'] == estudiante)
                and (not estudiante or r['tipo'] != 'entrega' or (
                    grupos.get(r['actividad_id']) == r['grupo'] if 'grupo' in r
                    else r['estudiante_id'] == estudiante))]

    @staticmethod
    def _grupo(actividad, estudiante):
        return next((i for i, miembros in enumerate(actividad.get('grupos', []), 1)
                     if estudiante in miembros), None)

    def _vista(self, registro, usuario):
        vista = {k: v for k, v in registro.items() if k != 'contenido'}
        if usuario['rol'] == 'estudiante':
            vista.pop('nota_borrador', None)
            if 'grupos' in vista:
                vista['mi_grupo'] = self._grupo(registro, usuario['estudiante_id'])
                vista['grupos'] = [len(g) for g in vista['grupos']]
            if vista.get('tipo') == 'entrega' and 'grupo' in vista:
                vista.pop('estudiante_id', None)
                vista.pop('estudiante_nombre', None)
        return vista

    def conversacion_grupo(self, curso_id, sesion_id, actividad_id, usuario, datos=None):
        if usuario['rol'] != 'estudiante':
            raise ErrorAcceso(403, 'La conversación es privada para integrantes del equipo.')
        with self.cursos.lock:
            curso, sesion = self._curso_sesion(curso_id, sesion_id, usuario)
            actividad = self._registro(self._leer(curso), sesion['id'], 'actividad', actividad_id)
            self._actividad_publicada(actividad)
            estudiante = usuario['estudiante_id']
            grupo = self._grupo(actividad, estudiante)
            if grupo is None:
                raise ErrorAcceso(403, 'Elige un grupo de esta actividad antes de abrir la conversación.')
            nombre = curso['id'] + '-conversaciones.json'
            almacen = self.cursos.datos_cursos
            registros = almacen.leer(nombre, [])
            if not isinstance(registros, list):
                raise ErrorDatos('Conversaciones del curso no disponibles.')
            if datos is not None:
                texto = ServicioGrace._texto(datos.get('texto'), 'Mensaje', 1, 800)
                registros.append({'actividad_id': actividad['id'], 'grupo': grupo,
                                  'integrantes': list(actividad['grupos'][grupo - 1]),
                                  'autor': usuario['nombre'], 'texto': texto,
                                  'fecha': datetime.now(timezone.utc).isoformat()})
                almacen.guardar(nombre, registros[-1000:])
            mensajes = [{'autor': r['autor'], 'texto': r['texto'], 'fecha': r['fecha']}
                        for r in registros if r['actividad_id'] == actividad['id']
                        and r['grupo'] == grupo and estudiante in r['integrantes']]
            return {'grupo': grupo, 'mensajes': mensajes[-50:]}

    def listar(self, curso_id, sesion_id, usuario):
        with self.cursos.lock:
            curso, sesion = self._curso_sesion(curso_id, sesion_id, usuario)
            registros = self._visibles(self._leer(curso), sesion, usuario)
            return {'registros': [self._vista(r, usuario) for r in registros]}

    def pendientes_inicio(self, usuario):
        profesor = usuario['rol'] == 'profesor'
        if not profesor and usuario['rol'] != 'estudiante':
            raise ErrorAcceso(403, 'Esta vista corresponde a estudiantes y profesores.')
        pendientes = []
        with self.cursos.lock:
            for curso in self.cursos.listar(usuario)['cursos']:
                registros = self._leer(curso)
                for sesion in curso['sesiones']:
                    if not sesion['publicada']:
                        continue
                    visibles = self._visibles(registros, sesion, usuario)
                    entregas = {}
                    for entrega in visibles:
                        if entrega['tipo'] == 'entrega' and (not profesor or not entrega.get('nota_publicada')
                                                           or entrega.get('nota_borrador')):
                            actividad_id = entrega['actividad_id']
                            entregas[actividad_id] = entregas.get(actividad_id, 0) + 1
                    for actividad in visibles:
                        if actividad['tipo'] != 'actividad' or not actividad.get('publicada', True):
                            continue
                        cantidad = entregas.get(actividad['id'], 0)
                        if (profesor and cantidad) or (not profesor and not cantidad and actividad.get('vence')):
                            pendientes.append({'curso_id': curso['id'], 'sesion_id': sesion['id'],
                                               'actividad_id': actividad['id'], 'titulo': actividad['titulo'],
                                               'vence': actividad.get('vence'), 'cantidad': cantidad})
        return {'pendientes': pendientes}

    def notas(self, curso_id, usuario):
        if usuario['rol'] != 'estudiante':
            raise ErrorAcceso(403, 'Esta vista corresponde al estudiante.')
        with self.cursos.lock:
            curso = self.cursos._obtener(self.cursos._leer(), curso_id)
            self.cursos._autorizar(curso, usuario)
            registros = self._leer(curso)
            actividades = {r['id']: r['titulo'] for r in registros if r['tipo'] == 'actividad'}
            notas = []
            for sesion in curso['sesiones']:
                if not sesion['publicada']:
                    continue
                for entrega in self._visibles(registros, sesion, usuario):
                    if entrega['tipo'] == 'entrega' and entrega.get('nota_publicada'):
                        notas.append({'sesion': sesion['titulo'], 'actividad': actividades[entrega['actividad_id']],
                                      **entrega['nota_publicada']})
            return {'notas': notas}

    def descargar(self, curso_id, sesion_id, archivo_id, usuario):
        with self.cursos.lock:
            curso, sesion = self._curso_sesion(curso_id, sesion_id, usuario)
            archivo = next((r for r in self._visibles(self._leer(curso), sesion, usuario)
                            if r['id'] == archivo_id and 'contenido' in r), None)
            if archivo is None:
                raise ErrorAcceso(404, 'Archivo no disponible.')
            return archivo['nombre'], base64.b64decode(archivo['contenido'])

    def orientar(self, datos, usuario):
        if usuario['rol'] != 'estudiante':
            raise ErrorAcceso(403, 'La orientación del aula es para estudiantes matriculados.')
        tipo = datos.get('tipo')
        nivel = datos.get('nivel', 1)
        if tipo not in ('pista', 'explicar') or type(nivel) is not int or not 1 <= nivel <= 3:
            raise ErrorValidacion('Selecciona una orientación válida.')
        with self.cursos.lock:
            curso, sesion = self._curso_sesion(datos.get('curso_id'), datos.get('sesion_id'), usuario)
            contexto = {
                'tipo': tipo, 'nivel': nivel, 'tema': sesion.get('tema') or sesion['titulo'],
                'objetivo': sesion['descripcion'][:700], 'plan': sesion.get('actividades', '')[:500],
            }
            if tipo == 'pista':
                actividad = self._registro(self._leer(curso), sesion['id'], 'actividad', datos.get('actividad_id'))
                self._actividad_publicada(actividad)
                contexto.update(actividad=actividad['titulo'], instrucciones=actividad['instrucciones'][:950],
                                criterios=actividad.get('criterios', '')[:350])
        return self.cursos.ia.orientar_actividad(contexto)

    @staticmethod
    def _momento_actividad(datos, predeterminado='durante'):
        momento = datos.get('momento', predeterminado)
        if momento not in MOMENTOS:
            raise ErrorValidacion('Elige un momento de la sesión.')
        return momento

    def _preguntas(self, tipo, datos, usuario):
        es_pregunta = tipo == 'pregunta'
        if usuario['rol'] != ('estudiante' if es_pregunta else 'profesor'):
            raise ErrorAcceso(403, 'Tu cuenta no tiene permiso para esta acción.')
        texto = ServicioGrace._texto(datos.get('texto'), 'Pregunta' if es_pregunta else 'Respuesta', 1, 1500)
        with self.cursos.lock:
            curso, sesion = self._curso_sesion(datos.get('curso_id'), datos.get('sesion_id'), usuario)
            if not sesion['publicada']:
                raise ErrorAcceso(409, 'Publica la sesión para usar las preguntas.')
            registros = self._leer(curso)
            if es_pregunta:
                pregunta = {'id': secrets.token_hex(16), 'tipo': 'pregunta', 'sesion_id': sesion['id'],
                            'estudiante_id': usuario['estudiante_id'], 'estudiante_nombre': usuario['nombre'],
                            'texto': texto}
                registros.append(pregunta)
            else:
                pregunta = self._registro(registros, sesion['id'], 'pregunta', datos.get('pregunta_id'))
                pregunta['respuesta'] = texto
            self._persistir(curso, registros)
            return self._vista(pregunta, usuario)

    def guardar(self, datos, usuario):
        tipo = datos.get('tipo')
        rol = usuario['rol']
        if tipo in ('pregunta', 'responder_pregunta'):
            return self._preguntas(tipo, datos, usuario)
        if tipo in ('generar_material', 'publicar_material', 'ocultar_material',
                    'publicar_actividad', 'editar_actividad'):
            return self._material(tipo, datos, usuario)
        if tipo in ('grupo', 'criterios', 'nota', 'publicar_nota', 'sugerir_nota'):
            return self._evaluacion(tipo, datos, usuario)
        if (tipo in ('recurso', 'actividad') and rol != 'profesor'
                or tipo == 'entrega' and rol != 'estudiante'):
            raise ErrorAcceso(403, 'Tu cuenta no puede realizar esta operación.')
        registro = {'id': secrets.token_hex(16), 'tipo': tipo}
        if tipo in ('recurso', 'actividad'):
            registro['titulo'] = ServicioGrace._texto(datos.get('titulo'), 'Título', 1, 120)
        if tipo == 'actividad':
            registro['instrucciones'] = ServicioGrace._texto(datos.get('instrucciones'), 'Instrucciones', 1, 2000)
            cantidad, cupo = datos.get('cantidad', 0), datos.get('cupo', 0)
            if type(cantidad) is not int or type(cupo) is not int or not (
                    (cantidad, cupo) == (0, 0) or 1 <= cantidad <= 30 and 1 <= cupo <= 12):
                raise ErrorValidacion('Define de 1 a 30 grupos con 1 a 12 integrantes por grupo.')
            registro['criterios'] = ServicioGrace._texto(datos.get('criterios', ''), 'Criterios', 0, 2000)
            registro['publicada'] = datos.get('borrador') is not True
            registro['vence'] = self._fecha_entrega(datos)
            registro['momento'] = self._momento_actividad(datos)
            if cantidad:
                registro.update(grupos=[[] for _ in range(cantidad)], cupo=cupo)
        elif tipo == 'recurso' and datos.get('enlace'):
            registro['enlace'] = validar_enlace(datos['enlace'])
        elif tipo in ('recurso', 'entrega'):
            registro.update(validar_archivo(datos.get('nombre'), datos.get('contenido')))
        else:
            raise ErrorValidacion('Tipo de trabajo inválido.')
        if tipo == 'recurso':
            self._clasificar(registro, datos)
            registro['publicada'] = datos.get('borrador') is not True
        with self.cursos.lock:
            curso, sesion = self._curso_sesion(datos.get('curso_id'), datos.get('sesion_id'), usuario)
            registro['sesion_id'] = sesion['id']
            registros = self._leer(curso)
            if tipo == 'entrega':
                self._asociar_entrega(registro, registros, datos.get('actividad_id'), usuario)
            registros.append(registro)
            self._persistir(curso, registros)
        return self._vista(registro, usuario)

    @staticmethod
    def _clasificar(registro, datos):
        categoria = datos.get('categoria')
        if categoria is None:
            extension = PurePath(registro.get('nombre', '')).suffix.lower()
            categoria = {'.pptx': 'presentacion', '.docx': 'lectura', '.pdf': 'lectura',
                         '.txt': 'lectura', '.mp4': 'video'}.get(extension, 'apoyo')
        momento = datos.get('momento', 'durante')
        if categoria not in CATEGORIAS or momento not in MOMENTOS:
            raise ErrorValidacion('Elige un tipo de material y un momento de la sesión.')
        registro.update(categoria=categoria, momento=momento)

    def _persistir(self, curso, registros):
        if sum(r.get('bytes', 0) for r in registros) > LIMITE_CURSO or len(registros) > 500:
            raise ErrorAcceso(413, 'El curso alcanzó su límite de archivos o registros.')
        self.cursos.datos_cursos.guardar(curso['id'] + '-trabajo.json', registros)

    @staticmethod
    def _fecha_entrega(datos):
        vence = datos.get('vence', '')
        if vence == '':
            return ''
        if not isinstance(vence, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}', vence):
            raise ErrorValidacion('Fecha de entrega inválida.')
        try:
            datetime.fromisoformat(vence)
        except ValueError:
            raise ErrorValidacion('Revisa el día y la hora límite de la entrega.') from None
        return vence

    def _material(self, tipo, datos, usuario):
        if usuario['rol'] != 'profesor':
            raise ErrorAcceso(403, 'El profesor prepara y publica los materiales.')
        curso_id, sesion_id = datos.get('curso_id'), datos.get('sesion_id')
        with self.cursos.lock:
            curso, sesion = self._curso_sesion(curso_id, sesion_id, usuario)
            if tipo != 'generar_material':
                registros = self._leer(curso)
                clase = 'recurso' if tipo in ('publicar_material', 'ocultar_material') else 'actividad'
                campo = 'material_id' if clase == 'recurso' else 'actividad_id'
                recurso = self._registro(registros, sesion['id'], clase, datos.get(campo))
                if tipo == 'editar_actividad':
                    if recurso.get('publicada', True):
                        raise ErrorAcceso(409, 'Solo se puede editar una actividad en borrador.')
                    recurso.update(
                        titulo=ServicioGrace._texto(datos.get('titulo'), 'Título', 1, 120),
                        instrucciones=ServicioGrace._texto(datos.get('instrucciones'), 'Instrucciones', 1, 2000),
                        criterios=ServicioGrace._texto(datos.get('criterios', ''), 'Criterios', 0, 2000),
                        vence=self._fecha_entrega(datos),
                        momento=self._momento_actividad(datos, recurso.get('momento', 'durante')),
                    )
                else:
                    recurso['publicada'] = tipo != 'ocultar_material'
                self._persistir(curso, registros)
                return self._vista(recurso, usuario)
            tema = sesion.get('tema') or sesion['titulo']
        formato = datos.get('formato')
        if formato not in ('pptx', 'docx', 'guion', 'actividad'):
            raise ErrorValidacion('Elige PowerPoint, Word, guion o actividad.')
        objetivo = ServicioGrace._texto(datos.get('objetivo', ''), 'Objetivo', 0, 1200)
        borrador = self.cursos.ia.generar_material(tema, objetivo, formato)
        titulo, secciones = borrador['titulo'], borrador['secciones']
        if formato == 'actividad':
            return {'titulo': titulo, 'instrucciones': '\n'.join(secciones[0]['puntos']),
                    'criterios': '\n'.join(secciones[1]['puntos']), 'origen': borrador['origen']}
        exportar = presentacion if formato == 'pptx' else documento
        nombre = {'pptx': 'presentacion-grace.pptx', 'docx': 'lectura-grace.docx', 'guion': 'guion-grace.docx'}[formato]
        contenido = base64.b64encode(exportar(titulo, secciones)).decode('ascii')
        archivo = validar_archivo(nombre, contenido)
        registro = {**archivo, 'id': secrets.token_hex(16), 'tipo': 'recurso', 'titulo': titulo,
                    'publicada': False, 'secciones': secciones, 'origen': borrador['origen']}
        self._clasificar(registro, {'categoria': 'presentacion' if formato == 'pptx' else 'lectura',
                                  'momento': datos.get('momento', 'durante')})
        with self.cursos.lock:
            curso, sesion = self._curso_sesion(curso_id, sesion_id, usuario)
            registro['sesion_id'] = sesion['id']
            registros = self._leer(curso)
            registros.append(registro)
            self._persistir(curso, registros)
        return self._vista(registro, usuario)

    @staticmethod
    def _asociar_entrega(registro, registros, actividad, usuario):
        tarea = TrabajoAcademico._registro(registros, registro['sesion_id'], 'actividad', actividad)
        TrabajoAcademico._actividad_publicada(tarea)
        if tarea.get('vence') and datetime.now() > datetime.fromisoformat(tarea['vence']):
            raise ErrorAcceso(409, 'El plazo de entrega terminó.')
        estudiante = usuario['estudiante_id']
        grupo = TrabajoAcademico._grupo(tarea, estudiante)
        if 'grupos' in tarea and grupo is None:
            raise ErrorAcceso(409, 'Elige un grupo antes de entregar.')
        anterior = next((r for r in registros if r['tipo'] == 'entrega'
                         and r['actividad_id'] == actividad and (
                             r.get('grupo') == grupo if grupo is not None
                             else r['estudiante_id'] == estudiante)), None)
        if anterior:
            if anterior.get('nota_publicada'):
                raise ErrorAcceso(409, 'La entrega ya tiene una nota publicada.')
            registros.remove(anterior)
        if grupo is not None:
            registro['grupo'] = grupo
        registro.update(actividad_id=actividad, estudiante_id=estudiante, estudiante_nombre=usuario['nombre'],
                        fecha=datetime.now(timezone.utc).isoformat())

    @staticmethod
    def _registro(registros, sesion_id, tipo, identificador):
        registro = next((r for r in registros if r['tipo'] == tipo and r['id'] == identificador
                         and r['sesion_id'] == sesion_id), None)
        if registro is None:
            raise ErrorAcceso(404, 'Registro no disponible.')
        return registro

    def _evaluacion(self, tipo, datos, usuario):
        requerido = 'estudiante' if tipo == 'grupo' else 'profesor'
        if usuario['rol'] != requerido:
            raise ErrorAcceso(403, 'Tu cuenta no puede realizar esta operación.')
        with self.cursos.lock:
            curso, sesion = self._curso_sesion(datos.get('curso_id'), datos.get('sesion_id'), usuario)
            registros = self._leer(curso)
            if tipo in ('grupo', 'criterios'):
                destino = self._registro(registros, sesion['id'], 'actividad', datos.get('actividad_id'))
                if tipo == 'grupo':
                    self._actividad_publicada(destino)
                    self._elegir_grupo(destino, registros, datos.get('grupo'), usuario['estudiante_id'])
                else:
                    destino['criterios'] = ServicioGrace._texto(datos.get('criterios'), 'Criterios', 0, 2000)
            else:
                destino = self._registro(registros, sesion['id'], 'entrega', datos.get('entrega_id'))
                actividad = self._registro(registros, sesion['id'], 'actividad', destino['actividad_id'])
                if tipo == 'sugerir_nota':
                    fragmento = ServicioGrace._texto(datos.get('fragmento'), 'Fragmento anónimo', 1, 3000)
                    criterios = actividad.get('criterios', '')
                    if not criterios:
                        raise ErrorValidacion('Guarda los criterios antes de pedir una propuesta.')
                    if datos.get('autoriza_envio') is not True:
                        raise ErrorValidacion('Confirma el envío del fragmento y los criterios a Grace.')
                else:
                    self._guardar_nota(tipo, destino, datos)
            if tipo != 'sugerir_nota':
                self.cursos.datos_cursos.guardar(curso['id'] + '-trabajo.json', registros)
                return self._vista(destino, usuario)
        return self.cursos.ia.sugerir_calificacion(criterios, fragmento)

    @staticmethod
    def _actividad_publicada(tarea):
        if not tarea.get('publicada', True):
            raise ErrorAcceso(404, 'Actividad no disponible.')

    def _elegir_grupo(self, actividad, registros, grupo, estudiante):
        grupos = actividad.get('grupos', [])
        if type(grupo) is not int or not 1 <= grupo <= len(grupos):
            raise ErrorValidacion('Grupo inválido.')
        anterior = self._grupo(actividad, estudiante)
        if anterior == grupo:
            return
        if any(r['tipo'] == 'entrega' and r['actividad_id'] == actividad['id']
               and r.get('grupo') in (anterior, grupo) for r in registros):
            raise ErrorAcceso(409, 'Los grupos con una entrega ya están cerrados.')
        if len(grupos[grupo - 1]) >= actividad['cupo']:
            raise ErrorAcceso(409, 'El grupo está lleno.')
        if anterior is not None:
            grupos[anterior - 1].remove(estudiante)
        grupos[grupo - 1].append(estudiante)

    @staticmethod
    def _guardar_nota(tipo, entrega, datos):
        if tipo == 'nota':
            puntaje = datos.get('puntaje')
            if type(puntaje) not in (int, float) or not 0 <= puntaje <= 100 or not math.isfinite(puntaje):
                raise ErrorValidacion('El puntaje debe estar entre 0 y 100.')
            entrega['nota_borrador'] = {
                'puntaje': round(puntaje, 2),
                'comentario': ServicioGrace._texto(datos.get('comentario', ''), 'Comentario', 0, 1500),
                'revision': secrets.token_hex(8),
            }
        else:
            nota = entrega.get('nota_borrador')
            if not nota or nota['revision'] != datos.get('revision'):
                raise ErrorAcceso(409, 'Guarda y revisa el borrador actual antes de publicarlo.')
            entrega['nota_publicada'] = {k: v for k, v in nota.items() if k != 'revision'}
            del entrega['nota_borrador']
