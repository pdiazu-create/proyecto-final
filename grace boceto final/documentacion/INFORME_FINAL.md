# Grace AI v0.4 — Informe de fases 2 a 5

**Punto de partida:** `Grace_AI_v04_Interfaz_Parte2 (1).zip` proporcionado en la conversación. Contenía 47 pruebas. Se añadió literalmente el archivo `tests/test_interfaz.py` suministrado por el estudiante, y las 51 pruebas pasaron (`OK`) **antes de iniciar la fase 2**. No se alteró ni eliminó ninguna prueba original.

| Etapa | Archivos cambiados o agregados | Pruebas antes → después | Resultado |
|---|---|---:|---|
| Base | `tests/test_interfaz.py` (nuevo, código suministrado) | 47 → 51 | OK |
| Fase 2, interfaz | `web/styles.css`, `tests/test_interfaz.py` (dos pruebas nuevas antes de cerrar fase) | 51 → 53 | OK |
| Fase 3, clase y asistencia | `grace/servicio.py`, `app.py`, `web/index.html`, `web/app.js`, `web/styles.css`, `tests/test_fase3.py` | 53 → 60 | OK |
| Fase 4, reglas | `grace/asistente.py`, `grace/servicio.py`, `web/index.html`, `tests/test_fase4.py` | 60 → 69 | OK |
| Fase 5, auditoría | `app.py`, `README.md`, `web/styles.css`, `web/app.js`, `tests/test_fase5.py`, `docs/INFORME_FINAL.md` | 69 → 70 | OK |

## Explicación sencilla

- **Fase 2:** se conservan las transiciones ya presentes en el ZIP de partida. Se limitaron las transiciones CSS a `opacity` y `transform`. Se mantuvo `prefers-reduced-motion` y se añadieron dos pruebas. En la auditoría final también se retiró el desplazamiento de página animado para cumplir estrictamente con «solo `opacity` y `transform`».
- **Fase 3:** la página de docentes muestra la fecha, la actividad publicada para ese día y tres interruptores de asistencia. Guardar envía **una petición** que valida a todos los estudiantes y pasa por una única llamada a `_mutar`. Si falla el guardado, se restaura la memoria. La vista de estudiantes muestra su propia asistencia; los porcentajes se calculan únicamente con registros existentes, no con días ausentes.
- **Fase 4:** un conjunto de expresiones y palabras clave suma puntos para elegir una intención. Las respuestas consultan datos reales del prototipo e indican su origen. El temario tiene nueve plantillas de clase distintas. La ruta BFS se presenta como sugerencia de recorrido, no como lista exhaustiva de prerrequisitos. El campo `fecha` se aclara como fecha de clase/actividad, no como plazo independiente de entrega.
- **Fase 5:** se descomprimió la versión anterior en una carpeta limpia y se ejecutaron las pruebas. El servidor arrancó inicialmente y respondió por HTTP local. Se comprobó el fallo de inicio cuando se borra `estado.json`: antes había traceback; ahora se imprime un mensaje breve y sale sin regenerar la semilla. Se revisaron los archivos citados por el README.

## Garantías y límites

- `data/estado.json` mantiene **versión 4 y las mismas claves**; los resúmenes de asistencia no se guardan como nuevos campos.
- No se añadió ningún paquete, servicio de IA externo ni petición a servicios fuera del servidor local.
- Se conservaron las implementaciones propias de cola enlazada, árbol, grafo, listas y archivo JSON.
- Las pruebas anteriores no se modificaron. Solo se añadieron casos nuevos.
- `web/index.html` carece de scripts y estilos en línea. CSS/JS permanecen como archivos locales; no hay CDN ni fuentes externas.
- No existe autenticación institucional ni separación de permisos real. Todos los usuarios son ficticios. No usar datos personales.

## Lo ejecutado y comprobado

- Suite completa `python -m unittest discover -s tests -v` con resultado `OK` tras cada fase y en carpeta limpia.
- Verificación de ZIP, integridad de contenido y ausencia de modificaciones en las cuatro pruebas originales.
- Operación HTTP local de asistencia por lote y respuesta a errores 400 en una prueba real.
- Primera ejecución en carpeta de datos vacía: crea `estado.json` y la marca. Arranque HTTP responde. Si se elimina `estado.json` después, el servidor informa el problema y termina sin traceback.
- Revisión visual por capturas en Chromium con HTML/CSS reales y **respuesta simulada** de `/api/estado` a 360, 768 y 1280 px. Se midió que el documento no excede el ancho de cada ventana. Se comprobó en esa simulación que el panel docente abre y contiene tres interruptores.

## Lo que NO pudo comprobarse

- No se verificó el flujo completo del navegador **contra el servidor Python real**: el navegador de este entorno bloquea la navegación local directa. Las capturas usaron una respuesta simulada.
- No se probó en Chrome, Edge, Safari o dispositivos físicos del estudiante.
- No se hizo una auditoría de seguridad integral, ni una evaluación WCAG con herramientas de asistencia reales, ni pruebas de varios procesos/conexiones simultáneas desde equipos distintos.

## Comandos

```sh
python -m unittest discover -s tests -v
python app.py
```

Abre `http://127.0.0.1:8000` desde el mismo equipo. Consulta también `docs/CHECKLIST_VISUAL.md`.
