"""Acciones cerradas que Grace puede proponer y el servidor puede ejecutar."""
from collections import defaultdict, deque
from datetime import date, datetime, timedelta
import json
import os
from pathlib import Path
import re
import threading
import unicodedata
import time as reloj

from .archivos import ErrorDatos
from .cuentas import ErrorAcceso
from .catalogo_acciones import CATALOGO_ACCIONES, ErrorPropuestaEstructurada, PANTALLAS
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

    def procesar(self, mensaje, usuario, sesion_id, proveedor, cursos):
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
        resultado = self._ejecutar(accion, validada['parametros'], usuario, cursos, origen)
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

    def _ejecutar(self, accion, parametros, usuario, cursos, origen):
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

    @staticmethod
    def _respuesta(texto, origen, accion=None, datos=None, accesos=None):
        resultado = {'respuesta': texto, 'origen': origen}
        if accion is not None:
            resultado['accion'] = accion
        if datos is not None:
            resultado['datos'] = datos
        if accesos is not None:
            resultado['accesos'] = accesos
        return resultado
