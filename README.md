# Grace AI · Proyecto Final de Programación Estructurada

> **Tiempo. Claridad. Tranquilidad.**  
> **Versión académica 0.4 — prototipo local, Python, con IA opcional y respaldo de reglas.**

Grace es la visión de una plataforma educativa institucional privada. Este repositorio contiene **un primer tramo funcional**: un profesor crea un borrador, lo revisa, puede editarlo, lo aprueba y lo publica; un estudiante ve la actividad y registra su entrega. Se emplean listas, cola enlazada, archivos JSON, árbol binario de búsqueda y grafos implementados en Python.

**La plataforma no reemplaza ningún sistema universitario ni está lista para usarse con cuentas reales.** Su objetivo es demostrar y explicar los conceptos de Programación Estructurada con datos ficticios.

## 1. Ejecutar en Visual Studio Code (Windows)

1. Clona el repositorio independiente `pdiazu-create/proyecto-final` y abre **`Grace_AI_v0.4.code-workspace`** con Visual Studio Code; o abre la carpeta del repositorio con **Archivo → Abrir carpeta**.
2. Comprueba que tengas Python 3.10 o posterior: `python --version` (en algunos equipos, usa `py --version`).
3. Abre la terminal integrada de VS Code (Terminal → Nueva terminal).
4. Ejecuta:

```powershell
python app.py
```

Para revisar el modo configurado y hacer una prueba mínima segura del proveedor, ejecuta `python diagnostico_ia.py`. Muestra solo si hay clave, su longitud, el modelo, el estado de la respuesta y el origen usado por Grace; nunca muestra la clave.

5. Entra desde tu navegador a **http://127.0.0.1:8000**.
6. Para detener el servidor presiona `Ctrl+C` en la terminal.

No hay que instalar `flask`, paquetes de IA ni otras bibliotecas: utiliza exclusivamente Python estándar + HTML, CSS y JavaScript nativos. También puedes iniciar con el depurador de VS Code (configuración **Grace AI · Servidor local**, tecla F5) si tienes instalada la extensión Python y el depurador.

### Activar la IA por API (opcional)

#### Acceso de escritorio sin terminal

Abre `Abrir Grace` desde el escritorio. Introduce la clave Gemini en la ventana privada y pulsa Abrir Grace. El navegador se abre y el servidor permanece en segundo plano cuando se cierra la ventana de inicio. La clave solo queda en memoria del proceso. El acceso `Detener Grace` termina exclusivamente la instancia iniciada por este mecanismo. Si Grace ya está abierta desde una terminal, debes detenerla primero allí con Ctrl+C para pasar al iniciador sin consola.

Después de apagar o reiniciar la computadora será necesario abrir Grace e introducir la clave nuevamente. Cerrar el navegador no detiene el servidor. No se configura inicio automático ni se almacena la clave. El archivo local `.grace_proceso.json` solo contiene un identificador de proceso y una marca aleatoria para evitar detener procesos ajenos.

#### Gemini (Google AI Studio)

Para iniciar Gemini en Windows, abre una terminal en la carpeta del proyecto y ejecuta:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\iniciar_gemini.ps1
```

Introduce la clave solo en la entrada oculta de esa terminal. El script activa `GRACE_IA=api`, `GRACE_IA_PROVEEDOR=gemini` y `GRACE_IA_MODEL=gemini-flash-latest`. No escribe la clave en archivos. Al terminar restaura el entorno anterior. Si el puerto 8000 ya está ocupado, cierra antes la instancia anterior con Ctrl+C.

El inicio de Gemini configura `GRACE_IA_TIMEOUT=30`: cada llamada espera hasta 30 segundos antes del respaldo. El diagnóstico muestra el valor utilizado. Sin esa variable se conservan 10 segundos; el valor configurable está acotado entre 10 y 60 segundos y solo afecta a Gemini. OpenAI conserva su timeout de 10 segundos.

Actualización de respuesta rápida: el modelo predeterminado de Gemini y el inicio privado usan ahora `gemini-3.5-flash-lite`, con `thinkingConfig.thinkingLevel=minimal`. Este reemplaza la selección anterior `gemini-flash-latest`. La cuota gratuita, disponibilidad y latencia dependen de Google y de tu proyecto. Una respuesta con origen IA sigue siendo el criterio para confirmar una consulta real.

Abre http://127.0.0.1:8000 y envía un mensaje. `Fuente: IA` confirma una respuesta del proveedor; `reglas (respaldo)` indica un fallo o una cuota agotada. El nivel gratuito depende de la cuota y disponibilidad de tu proyecto; Grace no activa facturación ni recargas.

La API Gemini recibe el mismo contexto académico mínimo que el proveedor OpenAI y usa exclusivamente urllib, timeout de 10 segundos, límites de entrada y salida y respaldo de reglas. Google utiliza su propio contrato REST: no se envía el parámetro `store` de OpenAI. Consulta las condiciones de Google AI Studio antes de enviar datos personales; este proyecto conserva sus datos ficticios y filtros existentes.

Para diagnosticar Gemini, ejecuta `python diagnostico_ia.py` en un entorno con `GRACE_IA_PROVEEDOR=gemini`, `GRACE_IA=api` y la clave ya configurada privadamente en `GRACE_IA_KEY`. No hace falta instalar un SDK.

#### OpenAI

En Windows puedes ejecutar `powershell -NoProfile -ExecutionPolicy Bypass -File .\iniciar_ia.ps1` desde esta carpeta. Introduce la clave solo en esa terminal: la entrada está oculta, no se guarda en archivos y se elimina del entorno al cerrar el servidor. Abre http://127.0.0.1:8000. La respuesta muestra su origen: IA o reglas (respaldo). Abrir la plataforma de OpenAI por sí solo no configura la conexión de Grace.

El chat ahora se abre con «Hablar con Grace», flota sin reservar espacio en las páginas y conserva sus mensajes al cerrarlo y reabrirlo. Las fechas de actividades provienen del estado; las horas mostradas son horarios de demostración.

Grace funciona con reglas locales por defecto. Para activar el proveedor OpenAI por HTTP, configura las variables de entorno antes de iniciar el servidor:

```powershell
$env:GRACE_IA = "api"
$env:GRACE_IA_KEY = "tu-clave-local"
$env:GRACE_IA_MODEL = "gpt-4o-mini"
python app.py
```

También puedes dejar `GRACE_IA=reglas` o no definirla. Si falta la clave, hay un error de red, el proveedor responde con un error o el JSON no valida, Grace usa las reglas y marca el origen como `reglas (respaldo)`. La clave solo vive en el entorno del servidor: no se escribe en código, README, logs, respuestas ni navegador. La suscripción de ChatGPT Plus no rellena automáticamente `GRACE_IA_KEY`; la API requiere una clave configurada por el usuario.

La llamada utiliza exclusivamente `urllib` y el endpoint Responses de OpenAI. El servidor envía solo el objetivo o mensaje, tema y datos académicos mínimos: actividades y fechas, entregas como identificadores, ruta BFS ya calculada, tamaño de la cola y porcentaje de asistencia. No envía nombres de estudiantes ni solicitudes de otras personas. El interruptor desactivado no realiza la llamada.

Si `python` no funciona en Windows, utiliza `py app.py`.

## 2. Pruebas automáticas

```powershell
python -m unittest discover -s tests -v
```

La v0.4 se verificó con **94 pruebas**, incluyendo estructuras, persistencia, estados inválidos, fallos de escritura simulados, endpoints HTTP y respaldos seguros de IA. Estas pruebas no reemplazan una auditoría de seguridad ni las pruebas visuales en cada navegador.

### Registro de avance por fases

- Base inicial: 51 pruebas tras añadir `tests/test_interfaz.py` proporcionado por el estudiante.
- Fase 2: 53 pruebas; accesibilidad y animaciones de CSS (solo `opacity` y `transform`).
- Fase 3: 60 pruebas; asistencia por lote, actividad de la fecha y porcentajes sin cambiar el formato JSON.
- Fase 4: 69 pruebas; intenciones por puntuación, respuestas con fuentes y nueve plantillas.
- Fase 5: 70 pruebas; primera ejecución, arranque seguro ante pérdida de `estado.json`, revisión de README y carpeta limpia.
- Corrección de IA: 81 pruebas; llamadas fuera del candado, límites de salida, registro seguro y aislamiento de datos del plan.
- Corrección de cola: 82 pruebas; instantánea no recursiva y conversación con 2000 solicitudes.
- Etapa 1: 86 pruebas; diagnóstico seguro, modo de IA y origen exacto de las respuestas.
- Etapa 2: 91 pruebas; páginas separadas, panel acoplado, navegación por rol e intenciones rápidas por reglas.
- Corrección tipográfica y de temas: 94 pruebas; mínimo efectivo de 12px y tema concreto para explicar.

**Los porcentajes de asistencia usan únicamente registros existentes.** Un día sin registros no se interpreta como una falta. La fecha de una actividad no es una fecha límite independiente; por eso el asistente no promete un vencimiento que los datos no contienen. El asistente ofrece una ruta BFS de prerrequisitos, no garantiza enumerar todos los posibles caminos.

### Alternativa para mostrar solo estructuras en consola

También puedes ejecutar `python demo_consola.py`: aparece un menú interactivo (similar a los menús que trabajaste en clase) con ejemplos separados de listas, cola, archivos, árbol y grafo. **Este menú no modifica los datos de la página web.**

## 3. Funciones de la demo

| Vista | Qué se puede hacer | Estado |
|---|---|---|
| Inicio | Resumen de tareas, entregas, solicitudes y planes | Implementado |
| Docentes | Crear borradores, editar contenidos y registrar asistencia por lote de toda la clase | Implementado |
| Flujo docente | Borrador → revisión → aprobado → publicado; rechazo en revisión | Implementado |
| Estudiantes | Consultar tareas publicadas, registrar entregas, revisar su asistencia y pedir apoyo | Implementado |
| Estructuras | Ver cola FIFO, buscar en árbol, explorar grafo y ruta BFS | Implementado |
| Grace | Asistente por reglas o proveedor API opcional, con datos mínimos del curso y nueve plantillas | **Reglas locales por defecto; API opcional con respaldo** |
| Cuentas y permisos institucionales | Autenticación, roles y aislamiento real entre instituciones | **No implementado** |
| Integración con UAM | Leer o modificar información del sistema universitario | **No implementado** |
| Voz / offline | Voz y sincronización | **Propuesta futura** |

### Flujo recomendado para la exposición

1. **Docentes:** escribir un objetivo, elegir `Listas` y una fecha, crear el plan.
2. Hacer clic en **Editar contenido** y modificar la práctica. El estado queda en **borrador**.
3. **Enviar a revisión**, **Aprobar** y **Publicar**. No se puede saltar ninguna fase.
4. **Estudiantes:** encontrar la nueva actividad publicada y registrar la entrega.
5. **Estructuras:** mostrar la cola enlazada (atención FIFO), la búsqueda por ID en el árbol y la ruta entre temas con BFS.
6. **Reiniciar demo** para restaurar únicamente los datos ficticios. Se pide confirmación.

## 4. Los cinco conceptos de la asignatura

| Contenido | Implementación propia | Uso real en Grace |
|---|---|---|
| Listas | `self.actividades`, `self.planes`, `self.entregas`, recorridos con `for`, búsquedas y filtrado | Información académica |
| Cola enlazada | `NodoCola`, `ColaEnlazada`, `frente`, `final`, `encolar`, `desencolar` | Solicitudes de ayuda por orden de llegada |
| Archivos | `AlmacenJSON`, `with open`, UTF-8, JSON y reemplazo atómico | Persistencia en `data/estado.json` |
| Árboles | `NodoArbol`, `ArbolBinarioBusqueda`, inserción, búsqueda, recorrido iterativo | Índice por número de actividad |
| Grafos | `GrafoAprendizaje`, lista de adyacencia, BFS propio | Prerrequisitos y rutas de aprendizaje |

> **No confundas la cola enlazada con una lista con `pop(0)`.** La cola se programa manualmente; los recorridos BFS del grafo usan una lista con índice frontal para no necesitar librerías externas.

## 5. Arquitectura

```text
Navegador (web/index.html + styles.css + app.js)
             ↓ HTTP / JSON
app.py (servidor local y validación de solicitudes)
             ↓
grace/servicio.py (reglas, estados, validación y coordinación)
             ├── grace/estructuras.py (cola, árbol, grafo)
             ├── grace/asistente.py (plantillas y respuestas por reglas)
             ├── grace/ia.py (interfaz común, OpenAI y respaldo de reglas)
             └── grace/archivos.py (persistencia JSON)
                                  ↓
                           data/estado.json
```

**Diseño importante:** publicar un plan modifica plan y actividad **en una única operación de guardado**, para evitar la inconsistencia de archivos separados en v0.2. Si falla guardar, el servicio restaura el estado anterior en memoria. Se preservan los archivos antiguos durante la migración.

**Primera ejecución vs. pérdida de datos:** si aún no hay `data/estado.json` ni marca de inicialización, Grace crea una semilla ficticia. Después registra `data/.grace_inicializada` (ambos archivos están excluidos de GitHub). Si se borra `estado.json` *después* de arrancar la v0.4, Grace **detiene el arranque con un error** en lugar de inventar datos. Un JSON ilegible también detiene el servicio. Usa **Reiniciar demo** desde la interfaz para restablecer datos ficticios de manera intencional; no borres archivos para reiniciar.

La v0.4 puede cargar archivos `estado.json` de la v0.3 y guardar después la versión 4 del formato. Antes de actualizar una instalación que tiene trabajo importante, respalda `data/`.

Los datos se guardan en `data/estado.json`, que el programa crea al primer arranque. **No subas ese archivo a GitHub**: está ignorado por `.gitignore`. Para reiniciar los datos ficticios utiliza el botón de la página.

## 6. Archivos del proyecto

```text
proyecto-final/
├── app.py                       # Servidor HTTP y API local
├── Abrir_Grace.pyw              # Inicio de escritorio en Windows
├── demo_consola.py              # Menú de las cinco estructuras en Python
├── diagnostico_ia.py            # Diagnóstico seguro de IA
├── gestor_grace.py              # Gestión del proceso local
├── iniciar_gemini.ps1           # Inicio opcional con Gemini
├── iniciar_ia.ps1               # Inicio opcional con OpenAI
├── grace/
│   └── ...                      # Servicio, estructuras, persistencia e IA
├── web/
│   └── ...                      # HTML, CSS y JavaScript de la interfaz
├── tests/                       # 128 pruebas Python y prueba JavaScript
├── data/                        # Estado local de la aplicación
├── .vscode/                     # Tareas y depuración
├── .gitignore
├── Grace_AI_v0.4.code-workspace
└── grace boceto final/
    ├── bocetos/
    ├── documentacion/
    ├── capturas/
    ├── presentaciones/
    ├── respaldos/
    └── reportes/
```

### Material para exponer

En [`grace boceto final/documentacion/GUIA_EXPOSICION.md`](<grace boceto final/documentacion/GUIA_EXPOSICION.md>) encontrarás el guion de exposición y las presentaciones PDF/PPTX en [`grace boceto final/presentaciones/`](<grace boceto final/presentaciones/>).

Los bocetos de referencia están en [`grace boceto final/bocetos/`](<grace boceto final/bocetos/>), las capturas en [`grace boceto final/capturas/`](<grace boceto final/capturas/>) y los informes/resultados históricos en [`grace boceto final/reportes/`](<grace boceto final/reportes/>).

## 7. Limitaciones y seguridad

- **No se usan usuarios ni contraseñas reales.** Las vistas docente/estudiante son una simulación de funciones, no una autorización de seguridad. Cualquier persona con acceso a la demo puede llamar las rutas locales de la API.
- El servidor escucha únicamente en `127.0.0.1`. **No lo despliegues públicamente** ni ingreses datos académicos privados.
- La persistencia JSON sirve para aprender manejo de archivos. No soporta múltiples procesos, concurrencia entre equipos, respaldos gestionados, migraciones complejas ni auditoría institucional.
- Los nombres y actividades de ejemplo son ficticios.
- El BST **no es AVL**: en Grace v0.4 el servicio observa su altura y, si supera la altura ideal aproximada más dos niveles, lo **reconstruye balanceado** a partir de las claves ordenadas. La operación de reconstrucción cuesta O(n), y sin ella un BST degenerado busca en O(n).
- Las comprobaciones HTTP de Host/Origin no equivalen a autenticación ni protección contra ataques. El servidor usa `RLock` para serializar cambios dentro de un proceso, pero **no soporta multiproceso ni varios equipos**.
- La IA por API es opcional; las reglas locales siguen siendo el respaldo y el modo predeterminado. No es una implementación de Moodle/UAM Virtual y no hace modificaciones en servidores universitarios.

## 8. Repositorio de origen académico

El proyecto toma como referencia los ejercicios previos del curso en [Programacion_Estructurada_G6](https://github.com/pdiazu-create/Programacion_Estructurada_G6), especialmente programación de funciones, matrices, listas, archivos y el ejemplo básico de web con Flask. **No modifica ese repositorio.** Grace vive en un repositorio separado; consulta la [guía de GitHub](<grace boceto final/documentacion/GUIA_GITHUB.md>).

### ¿Qué se ha probado en navegador?

Se ejecutaron pruebas HTTP locales, y se inspeccionaron capturas renderizadas en Chromium a 360, 768 y 1280 px con el HTML/CSS real y datos de la API **simulados**. La navegación directa de Chromium al servidor local estuvo bloqueada, por lo que esa revisión no demuestra un flujo completo de navegador contra el servidor Python. Antes de exponer, abre Grace en Chrome o Edge en tu equipo y practica el recorrido de [`grace boceto final/documentacion/CHECKLIST_VISUAL.md`](<grace boceto final/documentacion/CHECKLIST_VISUAL.md>).

### ¿Puedo publicar la web con GitHub Pages?

GitHub Pages puede alojar páginas estáticas, **pero no ejecuta un servidor Python**. Como Grace necesita `/api/...` para guardar planes y entregas, **subir solo `web/index.html` a GitHub Pages no pondrá en funcionamiento la aplicación completa**. Para enseñarla, inicia `python app.py` en tu equipo. Un futuro despliegue web requiere hosting compatible con Python, HTTPS, autenticación y un almacenamiento apropiado antes de introducir usuarios reales.

## 9. Identidad de Grace

La experiencia sigue los principios del concepto de Grace: **una sola interfaz, simplicidad, decisiones revisables y trato respetuoso**. El registro de concepto v1.1 es confidencial y, por eso, **no se incluye en el ZIP ni debe subirse al repositorio público**.

Creado como proyecto académico de Ingeniería en Sistemas. No se declara una licencia de código abierto: se reserva la decisión de licenciamiento al titular del proyecto.

Desarrollado con apoyo de herramientas de IA; el autor revisó y puede explicar cada módulo.


## Actualización de boceto final (2026-11-08)

Consulta [`grace boceto final/documentacion/INTEGRACION_BOCETO_FINAL.md`](<grace boceto final/documentacion/INTEGRACION_BOCETO_FINAL.md>) para roles simulados, cursos/horarios de muestra, limitaciones y el recuento real de 128 pruebas.
