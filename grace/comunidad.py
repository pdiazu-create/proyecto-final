"""Comunidad académica con afiliación y moderación verificadas en el servidor."""
from datetime import datetime, timezone
import secrets

from .archivos import ErrorDatos
from .cuentas import ErrorAcceso
from .servicio import ErrorValidacion, ServicioGrace


class Comunidad:
    def __init__(self, cursos):
        self.cursos = cursos

    def _leer(self):
        datos = self.cursos.almacen.leer('comunidad.json', {'publicaciones': [], 'reportes': []})
        if not isinstance(datos, dict) or any(not isinstance(datos.get(k), list)
                                               for k in ('publicaciones', 'reportes')):
            raise ErrorDatos('Registro de comunidad inválido.')
        return datos

    @staticmethod
    def _espacios(usuario):
        if usuario['rol'] != 'estudiante':
            return {}
        facultad, carrera = usuario.get('facultad_id'), usuario.get('carrera_id')
        if not facultad or not carrera:
            return {}
        return {'facultad': facultad, 'carrera': f'{facultad}/{carrera}'}

    @staticmethod
    def _visible(publicacion, espacios, por_id):
        padre = por_id.get(publicacion['padre']) if publicacion['padre'] else publicacion
        return (padre and not padre['oculta'] and not publicacion['oculta']
                and espacios.get(publicacion['canal']) == publicacion['espacio'])

    def listar(self, usuario):
        with self.cursos.lock:
            datos = self._leer()
            por_id = {p['id']: p for p in datos['publicaciones']}
            if usuario['rol'] == 'coordinador':
                return {'reportes': [{**r, 'publicacion': por_id[r['publicacion_id']]}
                                     for r in datos['reportes'] if not r['decision']]}
            if usuario['rol'] != 'estudiante':
                raise ErrorAcceso(403, 'Comunidad está disponible para estudiantes y Coordinación.')
            espacios = self._espacios(usuario)
            return {'canales': list(espacios), 'publicaciones': [
                {**{k: p[k] for k in ('id', 'canal', 'padre', 'autor', 'texto', 'fecha')},
                 'propia': p['cuenta_id'] == usuario['id']}
                for p in por_id.values() if self._visible(p, espacios, por_id)]}

    def guardar(self, datos, usuario):
        accion = datos.get('accion')
        with self.cursos.lock:
            estado = self._leer()
            por_id = {p['id']: p for p in estado['publicaciones']}
            if accion == 'moderar':
                resultado = self._moderar(datos, usuario, estado, por_id)
            else:
                espacios = self._espacios(usuario)
                if not espacios:
                    raise ErrorAcceso(403, 'Selecciona facultad y carrera en tu perfil.')
                resultado = self._participar(accion, datos, usuario, estado, por_id, espacios)
            self.cursos.almacen.guardar('comunidad.json', estado)
            return {'id': resultado['id']}

    def _participar(self, accion, datos, usuario, estado, por_id, espacios):
        padre_id = datos.get('publicacion_id', '')
        if not isinstance(padre_id, str):
            raise ErrorValidacion('Publicación inválida.')
        padre = por_id.get(padre_id)
        if accion in ('responder', 'reportar') and (not padre or not self._visible(padre, espacios, por_id)):
            raise ErrorAcceso(404, 'Publicación no disponible.')
        identificador = secrets.token_hex(16)
        if accion == 'reportar':
            reportes = estado['reportes']
            if padre['cuenta_id'] == usuario['id']:
                raise ErrorValidacion('Puedes reportar publicaciones de otros estudiantes.')
            if any(r['publicacion_id'] == padre_id and r['cuenta_id'] == usuario['id'] for r in reportes):
                raise ErrorAcceso(409, 'Ya reportaste esta publicación.')
            if len(reportes) >= 1000:
                raise ErrorAcceso(409, 'Se alcanzó el límite de reportes.')
            reporte = {'id': identificador, 'publicacion_id': padre_id, 'cuenta_id': usuario['id'],
                       'motivo': ServicioGrace._texto(datos.get('texto'), 'Motivo', 1, 300), 'decision': ''}
            reportes.append(reporte)
            return reporte
        if accion not in ('publicar', 'responder'):
            raise ErrorValidacion('Acción de comunidad inválida.')
        canal = padre['canal'] if padre and accion == 'responder' else datos.get('canal')
        if canal not in ('facultad', 'carrera') or (accion == 'responder' and padre['padre']):
            raise ErrorValidacion('Selecciona un canal o responde a una publicación principal.')
        publicaciones = estado['publicaciones']
        if len(publicaciones) >= 1000:
            raise ErrorAcceso(409, 'Se alcanzó el límite de publicaciones.')
        publicacion = {'id': identificador, 'canal': canal, 'espacio': espacios[canal],
                       'padre': padre_id if accion == 'responder' else '', 'cuenta_id': usuario['id'],
                       'autor': usuario['nombre'], 'texto': ServicioGrace._texto(datos.get('texto'), 'Mensaje', 1, 1000),
                       'fecha': datetime.now(timezone.utc).isoformat(), 'oculta': False}
        publicaciones.append(publicacion)
        return publicacion

    @staticmethod
    def _moderar(datos, usuario, estado, por_id):
        if usuario['rol'] != 'coordinador':
            raise ErrorAcceso(403, 'Solo Coordinación puede revisar reportes.')
        decision = datos.get('decision')
        if decision not in ('ocultar', 'conservar'):
            raise ErrorValidacion('Elige ocultar o conservar la publicación.')
        reporte = next((r for r in estado['reportes'] if r['id'] == datos.get('reporte_id')), None)
        if reporte is None or reporte['decision']:
            raise ErrorAcceso(404, 'Reporte pendiente no disponible.')
        reporte['decision'] = decision
        if decision == 'ocultar':
            por_id[reporte['publicacion_id']]['oculta'] = True
            for otro in estado['reportes']:
                if otro['publicacion_id'] == reporte['publicacion_id'] and not otro['decision']:
                    otro['decision'] = decision
        return reporte
