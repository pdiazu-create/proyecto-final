"""Acciones cerradas que Grace puede proponer y el servidor puede ejecutar."""
from collections import defaultdict, deque
from datetime import date, datetime, timedelta
import json
import os
from pathlib import Path
import re
import secrets
import threading
import unicodedata
import time as reloj

from .archivos import ErrorDatos
from .cuentas import ErrorAcceso
from .catalogo_acciones import CATALOGO_ACCIONES, ErrorPropuestaEstructurada, PANTALLAS
from .estructuras import ColaEnlazada
from .servicio import ErrorValidacion

DIAS = ('Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo')
MAX_MENSAJES_POR_MINUTO = 10
MAX_ACCIONES_POR_SESION = 8
MAX_MENSAJE = 500
VENTANA_SEGUNDOS = 60


def validar_propuesta(propuesta, usuario):
    if not isinstance(propuesta, dict) or set(propuesta) != {'accion', 'parametros'}:
        raise ErrorPropuestaEstructurada('La propuesta no tiene el formato esperado.')
    accion, parametros = propuesta['accion'], propuesta['parametros']
    if accion == 'ninguna' and parametros == {}:
        return None
    definicion = CATALOGO_ACCIONES.get(accion) if isinstance(accion, str) else None
    if definicion is None or not isinstance(parametros, dict):
        raise ErrorPropuestaEstructurada('La propuesta no pertenece al catálogo.')
    if set(parametros) != definicion['parametros']:
        raise ErrorPropuestaEstructurada('Los parámetros no coinciden con la acción.')
    if usuario.get('rol') not in definicion['roles']:
        raise PermissionError('Tu cuenta no tiene permiso para esa acción.')
    if accion == 'cambiar_tema' and parametros['tema'] not in ('claro', 'oscuro'):
        raise ErrorValidacion('El tema debe ser claro u oscuro.')
    if accion == 'abrir_pantalla':
        pantalla = parametros['pantalla']
        if pantalla not in PANTALLAS or usuario['rol'] not in PANTALLAS[pantalla]:
            raise PermissionError('Esa pantalla no está disponible para tu cuenta.')
    if accion == 'rutina_estudio':
        disponibilidad = parametros['disponibilidad']
        if (not isinstance(disponibilidad, list) or len(disponibilidad) > 4 or
                any(not isinstance(intervalo, str) or len(intervalo) > 40
                    for intervalo in disponibilidad)):
            raise ErrorValidacion('Indica hasta cuatro bloques de tiempo libre.')
    return {'accion': accion, 'parametros': parametros}


def _normalizar(texto):
    normalizado = unicodedata.normalize('NFKD', texto.casefold())
    return ''.join(c for c in normalizado if not unicodedata.combining(c))


class FiltroLenguaje:
    """Lista configurable en JSON; bloquea entradas y salidas sin guardarlas."""

    def __init__(self, ruta):
        self.ruta = Path(ruta)

    def _expresiones(self):
        try:
            with self.ruta.open('r', encoding='utf-8') as archivo:
                datos = json.load(archivo)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ErrorDatos('No se pudo leer la configuración del filtro de lenguaje.') from error
        expresiones = datos.get('expresiones') if isinstance(datos, dict) else None
        if not isinstance(datos, dict) or set(datos) != {'expresiones'} or not isinstance(expresiones, list):
            raise ErrorDatos('La configuración del filtro de lenguaje no es válida.')
        if any(not isinstance(p, str) or not p.strip() or len(p) > 80 for p in expresiones):
            raise ErrorDatos('La configuración del filtro de lenguaje no es válida.')
        return tuple(_normalizar(p.strip()) for p in expresiones)

    def bloqueado(self, texto):
        normalizado = _normalizar(texto)
        return any(re.search(r'(?<!\w)' + re.escape(p) + r'(?!\w)', normalizado)
                   for p in self._expresiones())


class RegistroAcciones:
    """Registro JSONL de eventos; nunca incluye el texto privado de la conversación."""

    def __init__(self, ruta):
        self.ruta = Path(ruta)
        self.lock = threading.Lock()

    def registrar(self, usuario, accion, estado, resultado):
        fila = {
            'fecha': datetime.now().astimezone().isoformat(timespec='seconds'),
            'usuario_id': usuario['id'],
            'rol': usuario['rol'],
            'accion': accion,
            'estado': estado,
            'resultado': resultado,
        }
        linea = json.dumps(fila, ensure_ascii=False, separators=(',', ':')) + '\n'
        with self.lock:
            with self.ruta.open('a', encoding='utf-8', newline='') as archivo:
                archivo.write(linea)
                archivo.flush()
                os.fsync(archivo.fileno())


def _sin_duplicados(bloques):
    unicos = {}
    for bloque in bloques:
        clave = (bloque['curso_id'], bloque['fecha'], bloque['inicio'], bloque['fin'], bloque['aula'])
        if clave not in unicos or 'sesion_id' in bloque:
            unicos[clave] = bloque
    return sorted(unicos.values(), key=lambda x: (x['fecha'], x['inicio'], x['curso']))


def _bloque(curso, inicio, fin, aula, fecha):
    return {
        'curso': curso['nombre'], 'curso_id': curso['id'], 'fecha': fecha.isoformat(),
        'dia': DIAS[fecha.weekday()], 'inicio': inicio, 'fin': fin, 'aula': aula,
    }


def horarios_usuario(cursos, usuario, ahora=None):
    """Devuelve clases reales autorizadas; no mezcla el catálogo ilustrativo del cliente."""
    ahora = ahora or datetime.now().astimezone()
    hoy = ahora.date()
    salida = []
    for curso in cursos.listar(usuario)['cursos']:
        for horario in curso['horarios']:
            desplazamiento = (horario['dia'] - hoy.weekday()) % 7
            fecha = hoy + timedelta(days=desplazamiento)
            if fecha == hoy and horario['inicio'] <= ahora.strftime('%H:%M'):
                fecha += timedelta(days=7)
            salida.append(_bloque(
                curso, horario['inicio'], horario['fin'],
                f"{horario['edificio']} · {horario['aula']}", fecha,
            ))
        for sesion in curso['sesiones']:
            fecha = date.fromisoformat(sesion['fecha'])
            if fecha < hoy or (fecha == hoy and sesion['inicio'] <= ahora.strftime('%H:%M')):
                continue
            salida.append(_bloque(
                curso, sesion['inicio'], sesion['fin'],
                f"{sesion['edificio']} · {sesion['aula']}", fecha,
            ) | {'sesion_id': sesion['id'], 'titulo': sesion['titulo']})
    return _sin_duplicados(salida)


def resumen_semana(cursos, usuario, ahora=None):
    ahora = ahora or datetime.now().astimezone()
    lunes = ahora.date() - timedelta(days=ahora.weekday())
    limite = lunes + timedelta(days=7)
    bloques = []
    for curso in cursos.listar(usuario)['cursos']:
        for horario in curso['horarios']:
            fecha = lunes + timedelta(days=horario['dia'])
            bloques.append(_bloque(
                curso, horario['inicio'], horario['fin'],
                f"{horario['edificio']} · {horario['aula']}", fecha,
            ))
        for sesion in curso['sesiones']:
            fecha = date.fromisoformat(sesion['fecha'])
            if lunes <= fecha < limite:
                bloques.append(_bloque(
                    curso, sesion['inicio'], sesion['fin'],
                    f"{sesion['edificio']} · {sesion['aula']}", fecha,
                ) | {'sesion_id': sesion['id'], 'titulo': sesion['titulo']})
    return _sin_duplicados(bloques)


class GestorAcciones:
    """Valida propuestas, aplica límites y ejecuta únicamente acciones de la lista blanca."""

    def __init__(self, carpeta_datos, recursos, reloj_monotono=None):
        self.recursos = recursos
        self.registro = RegistroAcciones(Path(carpeta_datos) / 'acciones.jsonl')
        self.filtro = FiltroLenguaje(
            Path(__file__).resolve().parent.parent / 'config' / 'palabras_bloqueadas.json')
        self.reloj = reloj_monotono or reloj.monotonic
        self.lock = threading.Lock()
        self.mensajes = defaultdict(deque)
        self.acciones_sesion = defaultdict(int)
        self.pendientes = ColaEnlazada()

    def procesar(self, mensaje, usuario, sesion_id, proveedor, cursos, trabajo, presencia):
        if not isinstance(mensaje, str) or not mensaje.strip() or len(mensaje) > MAX_MENSAJE:
            raise ErrorValidacion('El mensaje debe tener entre 1 y 500 caracteres.')
        self._limitar_mensaje(usuario['id'])
        if self.filtro.bloqueado(mensaje):
            self.registro.registrar(usuario, 'filtro_lenguaje', 'rechazada', 'expresion_bloqueada')
            return self._respuesta(
                'Entiendo. Mantengamos un tono respetuoso; dime qué necesitas de tus clases y te acompaño.',
                'reglas',
            )
        try:
            propuesta = proveedor.proponer_accion(mensaje)
        except ErrorPropuestaEstructurada:
            self.registro.registrar(usuario, 'intencion', 'rechazada', 'respuesta_estructurada_invalida')
            return self._respuesta(
                'No pude interpretar esa solicitud con seguridad. ¿Puedes expresarla de otra manera?',
                'IA',
            )
        origen = propuesta.get('origen', 'reglas') if isinstance(propuesta, dict) else 'reglas'
        if origen not in ('IA', 'reglas'):
            origen = 'reglas'
        if not isinstance(propuesta, dict):
            self.registro.registrar(usuario, 'intencion', 'rechazada', 'formato_invalido')
            return self._respuesta(
                'No pude interpretar esa solicitud con seguridad. ¿Puedes expresarla de otra manera?',
                origen,
            )
        if (set(propuesta) != {'accion', 'parametros', 'respuesta', 'origen'} or
                not isinstance(propuesta['respuesta'], str) or len(propuesta['respuesta']) > 1500):
            self.registro.registrar(usuario, 'intencion', 'rechazada', 'formato_invalido')
            return self._respuesta(
                'No pude interpretar esa solicitud con seguridad. ¿Puedes expresarla de otra manera?',
                origen,
            )
        if origen == 'IA' and self.filtro.bloqueado(json.dumps(propuesta, ensure_ascii=False)):
            self.registro.registrar(usuario, propuesta.get('accion'), 'rechazada', 'salida_ia_bloqueada')
            return self._respuesta(
                'No pude preparar una respuesta adecuada. Puedes intentarlo con otras palabras.',
                origen,
            )
        accion_propuesta = propuesta.get('accion', 'desconocida')
        self.registro.registrar(usuario, accion_propuesta, 'propuesta', 'recibida')
        if accion_propuesta != 'ninguna':
            with self.lock:
                if self.acciones_sesion[sesion_id] >= MAX_ACCIONES_POR_SESION:
                    self.registro.registrar(usuario, accion_propuesta, 'rechazada', 'limite_por_sesion')
                    return self._respuesta('Ya atendí varias acciones en esta sesión. Podemos continuar en un momento.',
                                           origen)
                self.acciones_sesion[sesion_id] += 1
        try:
            validada = validar_propuesta({
                'accion': propuesta.get('accion'),
                'parametros': propuesta.get('parametros'),
            }, usuario)
        except (PermissionError, ErrorValidacion, ErrorPropuestaEstructurada) as error:
            self.registro.registrar(usuario, accion_propuesta, 'rechazada', type(error).__name__)
            return self._respuesta(
                'Esa acción no está disponible para tu cuenta. La asistencia, por ejemplo, la registra el profesor.',
                origen,
            )
        if validada is None:
            if origen == 'IA' and propuesta['respuesta'].strip():
                return self._respuesta(propuesta['respuesta'].strip(), origen)
            return None
        accion = validada['accion']
        if accion == 'ninguna':
            return None
        if accion == 'rutina_estudio':
            disponibilidad = self._extraer_disponibilidad(mensaje)
            if not disponibilidad:
                resultado = self._respuesta(
                    'Claro. Dime tus horas libres, por ejemplo: “mañana de 16:00 a 18:00”. '
                    'Solo usaré los bloques que escribas y tus entregas registradas.',
                    origen, 'rutina_estudio')
                self.registro.registrar(usuario, accion, 'ejecutada', 'se_solicito_disponibilidad')
                return resultado
            validada['parametros']['disponibilidad'] = disponibilidad
        resultado = self._ejecutar(
            accion, validada['parametros'], usuario, cursos, origen, trabajo, presencia)
        if accion == 'preparar_asistencia' and resultado.get('confirmacion'):
            self.registro.registrar(usuario, accion, 'propuesta', 'borrador_pendiente_de_revision')
        else:
            self.registro.registrar(usuario, accion, 'ejecutada', 'correcto')
        return resultado

    def _limitar_mensaje(self, usuario_id):
        ahora = self.reloj()
        with self.lock:
            historial = self.mensajes[usuario_id]
            while historial and ahora - historial[0] >= VENTANA_SEGUNDOS:
                historial.popleft()
            if len(historial) >= MAX_MENSAJES_POR_MINUTO:
                raise ErrorAcceso(429, 'Grace necesita una pausa breve. Espera un minuto antes de escribir de nuevo.')
            historial.append(ahora)

    def filtrar_respuesta(self, texto):
        return self.filtro.bloqueado(texto)

    def _ejecutar(self, accion, parametros, usuario, cursos, origen, trabajo, presencia):
        if accion == 'cambiar_tema':
            tema = parametros['tema']
            if tema == 'alternar':
                tema = 'claro' if self.recursos.preferencia_tema(usuario['id']) == 'oscuro' else 'oscuro'
            self.recursos.guardar_preferencia(usuario['id'], {'tema': tema})
            mensaje = f'Cambié al modo {tema}. Puedes volver al modo {("claro" if tema == "oscuro" else "oscuro")} desde Preferencias de lectura.'
            return self._respuesta(mensaje, origen, accion, {'tema': tema})
        if accion == 'abrir_pantalla':
            pantalla = parametros['pantalla']
            titulo = 'Mi horario' if pantalla == 'calendario' else (
                'Mis clases' if pantalla == 'mis-clases' else 'Inicio')
            return self._respuesta(f'Abrí {titulo}. Puedes volver a preguntarme cuando quieras.', origen,
                                   accion, {'pantalla': pantalla},
                                   [{'etiqueta': titulo, 'pantalla': pantalla}])
        if accion == 'rutina_estudio':
            return self._rutina_estudio(parametros['disponibilidad'], usuario, cursos, trabajo, origen)
        if accion == 'preparar_asistencia':
            return self._preparar_asistencia(usuario, cursos, presencia, origen)
        if accion == 'resumen_docente':
            return self._resumen_docente(usuario, cursos, trabajo, origen)
        horarios = horarios_usuario(cursos, usuario)
        acceso = [{'etiqueta': 'Abrir Mi horario', 'pantalla': 'calendario'}]
        if accion == 'proxima_sesion':
            if not horarios:
                return self._respuesta(
                    'No encuentro una próxima sesión en los horarios registrados. No voy a inventar una fecha.',
                    origen, accion, {'sesion': None}, acceso,
                )
            siguiente = horarios[0]
            titulo = siguiente.get('titulo', siguiente['curso'])
            fecha = date.fromisoformat(siguiente['fecha']).strftime('%d/%m')
            texto = (f'Tu próxima clase es {titulo}, el {fecha}, de {siguiente["inicio"]} a '
                     f'{siguiente["fin"]}, en {siguiente["aula"]}.')
            datos = {'sesion': siguiente}
            return self._respuesta(texto, origen, accion, datos, acceso)
        bloques = resumen_semana(cursos, usuario)
        if not bloques:
            texto = 'No hay horarios registrados para esta semana. Si esperabas ver uno, revisemos el curso juntos.'
        else:
            grupos = []
            for bloque in bloques:
                fecha = date.fromisoformat(bloque['fecha'])
                grupos.append(
                    f'{DIAS[fecha.weekday()]} {fecha.strftime("%d/%m")}: {bloque["inicio"]}–{bloque["fin"]}, '
                    f'{bloque["aula"]}, {bloque["curso"]}'
                )
            texto = 'Esta semana: ' + '; '.join(grupos) + '.'
        return self._respuesta(texto, origen, accion, {'sesiones': bloques}, acceso)

    def _rutina_estudio(self, disponibilidad, usuario, cursos, trabajo, origen):
        if not disponibilidad:
            return self._respuesta(
                'Claro. Dime en qué bloques tienes tiempo libre, por ejemplo: “hoy de 16:00 a 18:00”. '
                'Usaré tus entregas publicadas y sus fechas, sin resolverlas por ti.',
                origen, 'rutina_estudio')
        ventanas = self._validar_ventanas(disponibilidad)
        pendientes = trabajo.pendientes_inicio(usuario)['pendientes']
        cursos_por_id = {c['id']: c for c in cursos.listar(usuario)['cursos']}
        tareas = []
        for pendiente in pendientes:
            curso = cursos_por_id.get(pendiente['curso_id'])
            if curso is None:
                continue
            try:
                vence = datetime.fromisoformat(pendiente['vence'])
            except (TypeError, ValueError):
                raise ErrorDatos('Una fecha de entrega publicada no tiene un formato válido.') from None
            sesion = next((s for s in curso['sesiones'] if s['id'] == pendiente['sesion_id']), None)
            tareas.append((vence, pendiente, curso['nombre'], sesion['titulo'] if sesion else ''))
        tareas.sort(key=lambda fila: fila[0])

        horarios = horarios_usuario(cursos, usuario)
        acceso = [{'etiqueta': 'Abrir Mi horario', 'pantalla': 'calendario'}]
        siguiente = horarios[0] if horarios else None
        lineas = ['Organicé bloques de hasta 50 minutos con descansos de 10; prioricé la fecha de entrega.']
        if siguiente:
            fecha = date.fromisoformat(siguiente['fecha']).strftime('%d/%m')
            lineas.append(
                f'Tu próxima clase: {siguiente.get("titulo", siguiente["curso"])}, {fecha} '
                f'{siguiente["inicio"]}–{siguiente["fin"]}.')
        indice_tarea = 0
        for inicio, fin in ventanas:
            cursor = inicio
            lineas.append(f'{DIAS[cursor.weekday()]} {cursor.strftime("%d/%m")}:')
            while cursor + timedelta(minutes=30) <= fin:
                if indice_tarea < len(tareas):
                    vence, pendiente, nombre_curso, titulo_sesion = tareas[indice_tarea]
                    bloque_fin = min(cursor + timedelta(minutes=50), fin)
                    etiqueta = f'{pendiente["titulo"]} · {nombre_curso}'
                    if titulo_sesion:
                        etiqueta += f' · {titulo_sesion}'
                    etiqueta += f' (entrega {vence.strftime("%d/%m %H:%M")})'
                    lineas.append(f'  {cursor:%H:%M}–{bloque_fin:%H:%M}: {etiqueta}; trabaja un paso.')
                    indice_tarea += 1
                else:
                    bloque_fin = min(cursor + timedelta(minutes=50), fin)
                    lineas.append(f'  {cursor:%H:%M}–{bloque_fin:%H:%M}: repasa el tema que elijas.')
                cursor = bloque_fin
                if cursor + timedelta(minutes=10) <= fin:
                    descanso = cursor + timedelta(minutes=10)
                    lineas.append(f'  {cursor:%H:%M}–{descanso:%H:%M}: descanso.')
                    cursor = descanso
        if not tareas:
            lineas.insert(1, 'No encuentro entregas pendientes con fecha registrada; no voy a inventar tareas.')
        elif indice_tarea < len(tareas):
            lineas.append('Quedaron entregas fuera de estos bloques; podemos ampliar el horario.')
        lineas.append('La rutina es una guía: tú eliges el ritmo y Grace no resuelve las actividades.')
        return self._respuesta('\n'.join(lineas), origen, 'rutina_estudio',
                               {'entregas_usadas': len(tareas)}, acceso)

    @staticmethod
    def _validar_ventanas(disponibilidad):
        if not isinstance(disponibilidad, list) or not 1 <= len(disponibilidad) <= 4:
            raise ErrorValidacion('Dime entre uno y cuatro bloques libres con fecha y horas.')
        ahora = datetime.now().astimezone().replace(tzinfo=None)
        ventanas = []
        patron = re.compile(r'^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})-(\d{2}:\d{2})$')
        for texto in disponibilidad:
            coincidencia = patron.fullmatch(texto) if isinstance(texto, str) else None
            if coincidencia is None:
                raise ErrorValidacion('Usa bloques como “2026-11-13 16:00-18:00”.')
            try:
                fecha = date.fromisoformat(coincidencia[1])
                inicio = datetime.combine(fecha, datetime.strptime(coincidencia[2], '%H:%M').time())
                fin = datetime.combine(fecha, datetime.strptime(coincidencia[3], '%H:%M').time())
            except ValueError:
                raise ErrorValidacion('La fecha o la hora del bloque no es válida.') from None
            if (fecha < ahora.date() or fecha > ahora.date() + timedelta(days=6) or
                    inicio < ahora or fin <= inicio or fin - inicio > timedelta(hours=4)):
                raise ErrorValidacion('Elige horas futuras de hoy o de los próximos seis días (máximo cuatro horas).')
            ventanas.append((inicio, fin))
        ventanas.sort()
        if any(ventanas[i][0] < ventanas[i - 1][1] for i in range(1, len(ventanas))):
            raise ErrorValidacion('Los bloques libres no pueden superponerse.')
        return ventanas

    @staticmethod
    def _extraer_disponibilidad(mensaje):
        texto = _normalizar(mensaje)
        patron = re.compile(
            r'(?<!\d)(\d{1,2}:\d{2})\s*(?:a|hasta|[-–])\s*(\d{1,2}:\d{2})(?!\d)')
        dias = {'lunes': 0, 'martes': 1, 'miercoles': 2, 'jueves': 3,
                'viernes': 4, 'sabado': 5, 'domingo': 6}
        hoy = datetime.now().astimezone()
        intervalos = []
        for coincidencia in patron.finditer(texto):
            antes = texto[max(0, coincidencia.start() - 40):coincidencia.start()]
            despues = texto[coincidencia.end():coincidencia.end() + 24]
            dias_antes = list(re.finditer(
                r'\b(hoy|manana|lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b', antes))
            dias_despues = list(re.finditer(
                r'\b(hoy|manana|lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b', despues))
            fechas_antes = list(re.finditer(r'\b\d{4}-\d{2}-\d{2}\b', antes))
            fechas_despues = list(re.finditer(r'\b\d{4}-\d{2}-\d{2}\b', despues))
            fecha_explicita = (fechas_antes[-1] if fechas_antes else
                               fechas_despues[0] if fechas_despues else None)
            dia = (dias_antes[-1].group(1) if dias_antes else
                   dias_despues[0].group(1) if dias_despues else 'hoy')
            if fecha_explicita:
                try:
                    fecha = date.fromisoformat(fecha_explicita.group())
                except ValueError:
                    return []
            elif dia == 'manana':
                fecha = hoy.date() + timedelta(days=1)
            elif dia == 'hoy':
                fecha = hoy.date()
            else:
                desplazamiento = (dias[dia] - hoy.weekday()) % 7
                fecha = hoy.date() + timedelta(days=desplazamiento)
            inicio, fin = coincidencia.groups()
            if ':' not in inicio:
                inicio += ':00'
            if ':' not in fin:
                fin += ':00'
            intervalos.append(f'{fecha.isoformat()} {inicio.zfill(5)}-{fin.zfill(5)}')
        return intervalos if len(intervalos) <= 4 else []

    def _preparar_asistencia(self, usuario, cursos, presencia, origen):
        hoy = date.today().isoformat()
        sesiones = [
            (curso, sesion) for curso in cursos.listar(usuario)['cursos']
            for sesion in curso['sesiones'] if sesion['publicada'] and sesion['fecha'] == hoy
        ]
        if not sesiones:
            return self._respuesta(
                'No encuentro una sesión publicada de hoy entre tus cursos. Si ya empezó, abre esa sesión '
                'y vuelve a pedirme la revisión.',
                origen, 'preparar_asistencia')
        if len(sesiones) > 1:
            nombres = ', '.join(curso['nombre'] for curso, _ in sesiones)
            return self._respuesta(
                f'Veo más de una sesión publicada hoy ({nombres}). Abre la sesión que quieres revisar y '
                'vuelve a pedirme la asistencia.',
                origen, 'preparar_asistencia')
        curso, sesion = sesiones[0]
        estudiantes = {e['id']: e['nombre'] for e in cursos.cuentas.estudiantes()
                       if e['id'] in cursos._roster(curso)}
        latidos = presencia.activos(curso['id'], sesion['id'], estudiantes)
        filas = [{'estudiante_id': estudiante_id, 'nombre': nombre,
                  'estado': 'presente' if estudiante_id in latidos else 'sin_registrar'}
                 for estudiante_id, nombre in estudiantes.items()]
        if not filas:
            return self._respuesta(
                'El curso no tiene estudiantes matriculados para esta sesión.',
                origen, 'preparar_asistencia')
        pendiente = {
            'id': secrets.token_urlsafe(18), 'accion': 'preparar_asistencia',
            'usuario_id': usuario['id'], 'rol': usuario['rol'],
            'curso_id': curso['id'], 'sesion_id': sesion['id'],
            'curso': curso['nombre'], 'sesion': sesion['titulo'],
            'registros': filas,
        }
        with self.lock:
            self.pendientes.encolar(pendiente)
        confirmacion = {
            'id': pendiente['id'], 'curso': pendiente['curso'], 'sesion': pendiente['sesion'],
            'registros': filas,
        }
        texto = ('Preparé una propuesta a partir de las sesiones abiertas recientemente. '
                 'Revisa cada estado; no se ha guardado asistencia.')
        return self._respuesta(texto, origen, 'preparar_asistencia',
                               {'pendiente': pendiente['id']}, confirmacion=confirmacion)

    def _resumen_docente(self, usuario, cursos, trabajo, origen):
        lista_cursos = cursos.listar(usuario)['cursos']
        siguiente = horarios_usuario(cursos, usuario)
        pendientes = trabajo.pendientes_inicio(usuario)['pendientes']
        entregas = sum(p['cantidad'] for p in pendientes)
        ayudas = sum(cursos.servicio(c['id'], usuario).cola.tamano for c in lista_cursos)
        if siguiente:
            proxima = siguiente[0]
            cuando = date.fromisoformat(proxima['fecha']).strftime('%d/%m')
            clase = (f'Tu próxima clase es {proxima.get("titulo", proxima["curso"])}, el {cuando} '
                     f'a las {proxima["inicio"]} en {proxima["aula"]}.')
        else:
            clase = 'No hay una próxima clase registrada.'
        respuesta = f'{clase} Tienes {entregas} entregas por revisar y {ayudas} solicitudes de ayuda pendientes.'
        return self._respuesta(
            respuesta, origen, 'resumen_docente',
            {'entregas_por_revisar': entregas, 'solicitudes_ayuda': ayudas},
            [{'etiqueta': 'Abrir Mi horario', 'pantalla': 'calendario'},
             {'etiqueta': 'Abrir Mis clases', 'pantalla': 'mis-clases'}])

    def confirmar(self, datos, usuario, cursos, seguimiento):
        if usuario['rol'] != 'profesor':
            raise ErrorAcceso(403, 'Solo un profesor puede confirmar esta propuesta.')
        if (not isinstance(datos, dict) or set(datos) != {'id', 'registros'} or
                not isinstance(datos['id'], str) or not isinstance(datos['registros'], list)):
            raise ErrorValidacion('La confirmación no tiene el formato esperado.')
        with self.lock:
            pendiente = next((p for p in self.pendientes.recorrer()
                              if p['id'] == datos['id'] and p['usuario_id'] == usuario['id']), None)
            if pendiente is None:
                raise ErrorAcceso(404, 'La propuesta ya no está disponible.')
            roster = {fila['estudiante_id'] for fila in pendiente['registros']}
            estados = {}
            for fila in datos['registros']:
                if (not isinstance(fila, dict) or set(fila) != {'estudiante_id', 'estado'} or
                        not isinstance(fila['estudiante_id'], str) or
                        not isinstance(fila['estado'], str) or
                        fila['estudiante_id'] not in roster or
                        fila['estado'] not in ('presente', 'ausente') or
                        fila['estudiante_id'] in estados):
                    raise ErrorValidacion('Revisa a cada estudiante y selecciona presente o ausente.')
                estados[fila['estudiante_id']] = fila['estado']
            if set(estados) != roster:
                raise ErrorValidacion('Revisa a todos los estudiantes antes de confirmar.')
            resultado = seguimiento.marcar_lote({
                'curso_id': pendiente['curso_id'], 'sesion_id': pendiente['sesion_id'],
                'registros': [{'estudiante_id': estudiante, 'estado': estado}
                              for estudiante, estado in estados.items()],
            }, usuario)
            self._quitar_pendiente(pendiente['id'])
        self.registro.registrar(usuario, pendiente['accion'], 'confirmada', 'confirmacion_docente')
        self.registro.registrar(usuario, pendiente['accion'], 'ejecutada', 'asistencia_guardada')
        return resultado

    def rechazar(self, identificador, usuario):
        if usuario['rol'] != 'profesor':
            raise ErrorAcceso(403, 'Solo un profesor puede rechazar esta propuesta.')
        if not isinstance(identificador, str) or not identificador:
            raise ErrorValidacion('La propuesta no es válida.')
        with self.lock:
            pendiente = next((p for p in self.pendientes.recorrer()
                              if p['id'] == identificador and p['usuario_id'] == usuario['id']), None)
            if pendiente is None:
                raise ErrorAcceso(404, 'La propuesta ya no está disponible.')
            self._quitar_pendiente(identificador)
        self.registro.registrar(usuario, pendiente['accion'], 'rechazada', 'rechazo_docente')
        return {'rechazada': True}

    def pendientes_usuario(self, usuario, cursos):
        if usuario['rol'] != 'profesor':
            raise ErrorAcceso(403, 'Solo un profesor puede consultar propuestas de asistencia.')
        cursos_permitidos = {curso['id'] for curso in cursos.listar(usuario)['cursos']}
        with self.lock:
            return [{
                'id': pendiente['id'], 'curso': pendiente['curso'], 'sesion': pendiente['sesion'],
                'registros': pendiente['registros'],
            } for pendiente in self.pendientes.recorrer()
                if pendiente['usuario_id'] == usuario['id']
                and pendiente['curso_id'] in cursos_permitidos]

    def _quitar_pendiente(self, identificador):
        cola = ColaEnlazada()
        encontrado = False
        while self.pendientes.ver_frente() is not None:
            pendiente = self.pendientes.desencolar()
            if pendiente['id'] == identificador:
                encontrado = True
            else:
                cola.encolar(pendiente)
        self.pendientes = cola
        if not encontrado:
            raise ErrorDatos('La cola de propuestas cambió durante la confirmación.')

    @staticmethod
    def _respuesta(texto, origen, accion=None, datos=None, accesos=None, confirmacion=None):
        resultado = {'respuesta': texto, 'origen': origen}
        if accion is not None:
            resultado['accion'] = accion
        if datos is not None:
            resultado['datos'] = datos
        if accesos is not None:
            resultado['accesos'] = accesos
        if confirmacion is not None:
            resultado['confirmacion'] = confirmacion
        return resultado
