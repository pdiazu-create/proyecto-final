# Grace AI v4 · Integración del boceto final (8 de noviembre de 2026)

## Recuento verificado, sin confundir versiones

**El ZIP recibido para Claude contiene 113 pruebas Python**, verificado con `python -m unittest discover -s tests -v`. Su documento `LEER_PRIMERO_CLAUDE.md` también indica 113, no 116. La cifra 116 que se mencionó en el diálogo no consta en esta copia.

Esta integración suma los 12 casos de `test_boceto_final.py` del boceto provisional y 3 pruebas adicionales nuevas en `test_integracion_boceto.py`. Resultado: **113 originales + 12 del boceto + 3 adicionales = 128 pruebas Python; OK**. Esto **no equivale a recuperar tres pruebas originales que no estaban en el ZIP recibido**.

Adicionalmente se ejecutó `node tests/chat_flotante.test.cjs`: OK. Es una comprobación independiente y **no** se suma a las 128 pruebas de unittest.

## Qué se implementó sobre la base de Claude

- Accesos `/estudiante` y `/profesor` con selección del rol simulado, sin autenticación ni autorización real. Se conservó la interfaz existente, el selector de rol y el chat flotante.
- Catálogo aislado en `web/catalogo_demo.js` con temas genéricos y sin relación con matrícula ni sílabos oficiales. Programación Estructurada continúa como curso del prototipo local; no se inventó horario para él.
- Fichas informativas de solo lectura, accesibles desde Mis clases y los enlaces del horario, sin añadir una entrada de fichas al menú lateral.
- Horario de lunes a viernes con semana navegable y retorno a hoy, fechas calculadas localmente, etiquetas «Demostración · no oficial» y cursos celeste, turquesa y azul.
- Tabla semántica de horario para escritorio y vista por días en móvil, tabs reales con flechas de teclado, y actividades diferenciadas por curso.
- Archivos estáticos servidos con CSP local; no se añaden dependencias. El código en `grace/` y la persistencia JSON mantienen los datos originales.
- La capa de demostración es frontal y no se conecta al contexto de IA para Gemini/OpenAI ni se guarda en estado.json. Se conserva el funcionamiento de IA previa.

## Garantías comprobadas

- Los **18 archivos `tests/test_*.py` originales** de la copia suministrada son idénticos byte por byte; también se conservó `tests/chat_flotante.test.cjs`.
- El archivo `data/estado.json` es byte por byte idéntico al original suministrado (SHA256 `6629ba25c760963b0e1559fe880a50239f057db60e84acd2894fa466f4543ead`).
- `python -m unittest discover -s tests -v`: 128 tests, OK.
- `node tests/chat_flotante.test.cjs`: OK.
- `node --check web/app.js`, `node --check web/horario.js`, `node --check web/catalogo_demo.js`: sin errores.
- Revisada con Chromium y respuestas simuladas de la API: tarjetas, navegación entre clases/fichas/horario y tabs funcionan a 360 px, 768 px y 1280 px; sin overflow horizontal ni excepciones JS. Son **capturas con servidor simulado**, no una revisión del navegador real del usuario.
- Las pruebas HTTP ejercitan el servidor Python local. El navegador Chromium de esta sesión bloqueó visitas directas a localhost, de modo que el acceso visual se simuló sin afirmar que se abrió el servidor dentro de Chromium.

## Límites pendientes

- No existen cuentas ni permisos reales: `/profesor` y `/estudiante` separan pantallas para la demostración, pero el backend sigue siendo un prototipo local sin autenticación. No usar datos académicos personales.
- Los cursos y aulas son ejemplos. No se integra UAM Virtual ni un sílabo institucional.
- No se probaron conexiones reales a proveedores de IA; se preservaron las pruebas con transportes simulados existentes.
- Los archivos de documentación históricos del ZIP original pueden hablar de 113 pruebas o estados previos; corresponden al snapshot antes de esta integración. Esta nota prevalece para el resultado integrado.

## Para ejecutar

En la carpeta `Grace_AI_actual`:

```
python -m unittest discover -s tests -v
node tests/chat_flotante.test.cjs
python app.py
```

Abrir `http://127.0.0.1:8000`, seleccionar estudiante o profesor, o ir directamente a `/estudiante` y `/profesor`. No exponer el servidor fuera del dispositivo.
