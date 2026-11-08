"""Diagnóstico seguro del modo de Grace y del proveedor configurado."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from grace.ia import (DEFAULT_MODEL, OPENAI_RESPONSES_URL, TIMEOUT_SECONDS,
                      DEFAULT_GEMINI_MODEL, ProveedorGemini, ErrorIA,
                      ProveedorConRespaldo, ProveedorReglas, crear_proveedor, modo_ia)


def _datos_error(cuerpo):
    if not isinstance(cuerpo, dict):
        return None, None
    error = cuerpo.get('error')
    if not isinstance(error, dict):
        return None, None
    tipo = error.get('type') if isinstance(error.get('type'), str) else None
    codigo = error.get('code') if isinstance(error.get('code'), str) else None
    return tipo, codigo


def _contexto_prueba():
    class ColaVacia:
        tamano = 0

        @staticmethod
        def ver_frente():
            return None

    return {
        'rol': 'estudiante', 'estudiante_id': 'e1',
        'actividades_interno': [], 'entregas_interno': [],
        'cola_interna': ColaVacia(), 'asistencias_interno': [],
        'grafo_interno': None, 'temas_interno': (),
        'publico': {'actividades': [], 'fechas_actividades': [],
                    'ruta_bfs': [], 'tamano_cola': 0},
    }


def diagnosticar(transporte=None, proveedor=None):
    if os.environ.get('GRACE_IA_PROVEEDOR', '').strip().lower() == 'gemini':
        return diagnosticar_gemini(transporte, proveedor)
    modo = modo_ia()
    clave = os.environ.get('GRACE_IA_KEY', '').strip()
    modelo = os.environ.get('GRACE_IA_MODEL', '').strip() or DEFAULT_MODEL
    print(f'Modo: {modo}')
    print(f'Clave configurada: {"sí" if clave else "no"}; longitud: {len(clave)}')
    print(f'Modelo: {modelo}')

    fallo_api = None
    if not clave:
        print('Prueba API: no se hace llamada porque no hay clave configurada.')
    else:
        cuerpo = {
            'model': modelo,
            'input': [{'role': 'user', 'content': 'Prueba mínima de diagnóstico.'}],
            'max_output_tokens': 20,
            'store': False,
        }
        solicitud = Request(
            OPENAI_RESPONSES_URL,
            data=json.dumps(cuerpo, ensure_ascii=False).encode('utf-8'),
            headers={'Authorization': f'Bearer {clave}', 'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            respuesta = (transporte or urlopen)(solicitud, timeout=TIMEOUT_SECONDS)
            try:
                datos = json.loads(respuesta.read(64_000).decode('utf-8'))
            finally:
                cierre = getattr(respuesta, 'close', None)
                if cierre:
                    cierre()
            tipo, codigo = _datos_error(datos)
            print(f'HTTP: {getattr(respuesta, "status", 200)}' +
                  (f'; error.type={tipo}; error.code={codigo}' if tipo or codigo else ''))
        except HTTPError as error:
            fallo_api = f'HTTP {error.code}'
            tipo = codigo = None
            try:
                tipo, codigo = _datos_error(json.loads(error.read(64_000).decode('utf-8')))
            except (OSError, ValueError, json.JSONDecodeError):
                pass
            detalle = f'HTTP: {error.code}'
            if tipo:
                detalle += f'; error.type={tipo}'
            if codigo:
                detalle += f'; error.code={codigo}'
            print(detalle)
        except (URLError, TimeoutError, OSError) as error:
            fallo_api = type(error).__name__
            print(f'Fallo de red: {fallo_api}')
        except (ValueError, json.JSONDecodeError):
            fallo_api = 'JSON inválido'
            print('Fallo de respuesta: JSON inválido')

    try:
        usado = proveedor or crear_proveedor(transporte=transporte)
        resultado = usado.responder_chat('Prueba de diagnóstico.', _contexto_prueba())
        origen = resultado.get('origen', 'reglas')
        print(f'Origen de Grace: {origen}')
    except Exception:
        origen = 'problema'
        print('Origen de Grace: problema')

    if modo == 'reglas':
        print('Conclusión: Grace está usando reglas locales; no hace falta una clave.')
    elif modo == 'api_sin_clave':
        print('Conclusión: falta la clave; configura GRACE_IA_KEY o usa GRACE_IA=reglas.')
    elif fallo_api == 'HTTP 401':
        print('Conclusión: la clave fue rechazada; revisa que sea válida.')
    elif fallo_api and fallo_api.startswith('HTTP'):
        print('Conclusión: el proveedor devolvió un error HTTP; revisa saldo, modelo y configuración.')
    elif fallo_api:
        print('Conclusión: no hubo conexión o la respuesta no fue válida; revisa la red y el proveedor.')
    elif origen == 'reglas (respaldo)':
        print('Conclusión: la API falló durante la prueba; Grace funciona con respaldo de reglas.')
    else:
        print('Conclusión: Grace está lista con el modo configurado.')


def diagnosticar_gemini(transporte=None, proveedor=None):
    clave = os.environ.get('GRACE_IA_KEY', '').strip()
    modelo = os.environ.get('GRACE_IA_MODEL', '').strip() or DEFAULT_GEMINI_MODEL
    print(f'Modo: {modo_ia()}; proveedor: Gemini')
    print(f'Clave configurada: {"sí" if clave else "no"}; longitud: {len(clave)}')
    # El modelo es configuración pública; la clave jamás se imprime.
    print(f'Modelo: {modelo}' if clave not in modelo or not clave else 'Modelo: configuración inválida')
    if modo_ia() == 'reglas' or not clave:
        print('Conclusión: se usan reglas; activa el modo API y configura la clave en tu terminal privada.')
        return
    api = ProveedorGemini(clave, modelo, transporte)
    print(f'Tiempo de espera: {api.timeout_seconds} segundos')
    try:
        resultado = api.responder_chat('Saluda brevemente.', _contexto_prueba())
        print('HTTP: 200')
        print(f'Origen de Grace: {resultado["origen"]}')
        print('Conclusión: Gemini respondió correctamente.')
    except ErrorIA as error:
        estado = error.estado_http
        if estado:
            print(f'HTTP: {estado}')
        else:
            print(f'Fallo: {error.codigo}')
            if error.causa_red:
                print(f'Causa de red: {error.causa_red}')
        acciones = {
            400: 'Revisa la clave, el modelo y los parámetros.',
            403: 'Revisa los permisos de la clave y la disponibilidad en tu región.',
            404: 'Revisa el modelo configurado.',
            429: 'La cuota o el límite de solicitudes no permite responder ahora.',
            503: 'Google indica que el modelo no está disponible temporalmente o está sobrecargado. La clave no queda validada por este error.',
        }
        print('Origen de Grace: reglas (respaldo)')
        causas = {
            'timeout': f'Gemini excedió el límite de {api.timeout_seconds} segundos. La clave todavía no se puede dar por validada.',
            'dns': 'No se pudo resolver la dirección del proveedor. Revisa DNS o la conexión.',
            'certificado_tls': 'Falló la verificación del certificado HTTPS. No desactives esa verificación.',
            'tls': 'Falló la conexión HTTPS segura con el proveedor.',
        }
        print('Conclusión: ' + acciones.get(estado, causas.get(error.causa_red,
              'No se completó la respuesta; se mantienen las reglas de respaldo.')))


if __name__ == '__main__':
    diagnosticar()
