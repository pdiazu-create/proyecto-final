# Grace AI — Estado actual

**Registro principal de continuidad. Leer este archivo antes de retomar.**

Verificación: **10 de noviembre de 2026, 08:19, America/Managua (UTC−06:00)**.
Proyecto: `C:\Users\Usuario\Documents\proyecto-final`.
Predefensa: 11 de noviembre. Defensa: 13 de noviembre de 2026.

## Rama, commits y alcance de esta intervención

- Rama actual comprobada: `feature/grace-authorized-actions`.
- Último commit de código verificado: **`acb5838`**, `Add study routines and reviewed attendance`.
- También existe **`abfdfd5`**, `Add authorized Grace actions for schedule and theme`.
- Ambos descienden de **`8de42b9`**, que incorporó el arranque verificable y las correcciones de navegación/contraste.
- `organizacion-grace-boceto-final` permanece en `8de42b9`. La comparación arrojó **0 commits exclusivos de defensa y 2 exclusivos de feature** antes del commit documental de esta revisión. No son dos desarrollos divergentes en este momento.
- Otras referencias locales: `main`; referencias remotas conocidas: `origin/main`, `origin/organizacion-grace-boceto-final`. No se hizo fetch, cambio de rama, merge ni push.
- El repositorio estaba **limpio**, sin cambios pendientes de Copilot ni módulos sin registrar. Se volvió a comprobar después de las pruebas.
- Esta intervención solo verifica y documenta. No modifica código, pruebas, configuración, datos académicos ni funcionalidades.
- El commit que contiene esta actualización es documental y posterior a `acb5838`. Consultar su identificador con `git log -1 --oneline`; distinguirlo del último commit de código anterior.

## Hecho y verificado

### Pruebas de esta revisión

Se ejecutó una sola suite completa sobre la rama actual. El servicio importado por las pruebas usó un directorio temporal de revisión y `GRACE_IA=reglas`. Los casos de proveedor usan simulaciones; no se utilizó una clave real ni se solicitó una respuesta a Gemini.

```text
Ran 196 tests in 127.368s

OK
```

```text
tests 4
pass 4
fail 0
skipped 0
```

`git diff --check` terminó sin problemas. La suite emitió un `ResourceWarning` al limpiar un `HTTPError` simulado; no produjo fallos, pero tampoco debe presentarse como una ejecución sin advertencias.

Salidas completas:

- [Python](defensa%20proyecto%20final/reportes/verificacion_2026-11-10_python.txt).
- [JavaScript](defensa%20proyecto%20final/reportes/verificacion_2026-11-10_javascript.txt).

Las 14 pruebas de `tests/test_acciones_autorizadas.py` forman parte de las 196. Cubren catálogo y permisos, preferencia de tema, horarios autorizados, JSON inválido, proveedor simulado, rutina con entregas publicadas, asistencia con confirmación, resumen docente, caducidad de presencia, respaldo, inyección, filtro y límite de mensajes.

### Servidor actualmente abierto

Comprobaciones HTTP de solo lectura sobre `http://127.0.0.1:8000`:

- `/api/salud`: estado `ok`, modo `api`, huella **igual al código actual**.
- `/comunidad.js`: **200**.
- `/personalizacion.js`: **200**.

Esto confirma la versión servida y la configuración de API. **No demuestra una llamada exitosa al proveedor en esta revisión.** No se reinició el servidor ni se leyó su clave.

`data/.gitkeep` es el único archivo registrado bajo `data/`. El marcador de proceso y los datos de ejecución están excluidos. Esta comprobación no equivale a revisar todo el historial remoto en busca de secretos.

### Implementación comprobada en código y pruebas

| Capacidad | Evidencia y límites |
| --- | --- |
| Cuentas y permisos por rol | Sesión del servidor, pruebas de cuentas y permisos por curso. No es un despliegue listo para producción. |
| Cambiar claro/oscuro por conversación | Catálogo, validación, guardado de la preferencia propia y conexión con el cliente. Prueba automatizada incluida. |
| Próxima sesión y resumen semanal | Se calculan desde los cursos/horarios autorizados; sin datos disponibles no inventan una clase. |
| Rutina de estudio | Usa actividades publicadas, entregas propias, fechas y disponibilidad escrita por el estudiante. Prueba de aislamiento incluida. |
| Propuesta de asistencia | Usa señales temporales y una cola propia; no guarda asistencia definitiva antes de la confirmación docente. |
| Confirmar asistencia | Valida profesor, propietario de la propuesta, estudiantes y estados; guarda un lote mediante `Seguimiento.marcar_lote`. |
| Presencia temporal | `RegistroPresencia` valida matrícula, sesión publicada y fecha de hoy. Expira tras 120 segundos; se pierde al reiniciar. |
| Resumen docente | Calcula próxima clase, entregas por revisar y solicitudes de sus cursos; cliente conectado al inicio de sesión. |
| Arranque verificable | `version_grace.py`, salud y lanzador comparan la huella del código. La instancia actual coincide. |

## Hecho pero sin verificar completamente

- **Navegador de la versión `acb5838`:** Copilot reportó recorridos A–F con datos aislados y reglas. Es evidencia reportada por otra herramienta; esta revisión no repitió esos recorridos ni recibió sus capturas guardadas.
- En la revisión anterior de `8de42b9` sí se comprobaron acceso, navegación por roles, inicio/perfil, ambos temas y una vista móvil de 360 px en Chrome aislado. No certificar automáticamente las nuevas acciones de Copilot con aquellas capturas.
- El usuario reporta capturas con «Fuente: IA». Son indicio de respuestas reales previas. La API actual solo se verificó como configurada, sin llamada externa nueva.
- El funcionamiento completo de Comunidad con Ana, los clics del encabezado con el chat abierto, conversación de equipo y los recorridos académicos recientes siguen pendientes de una comprobación visual conjunta sobre esta versión.
- PPTX/DOCX tienen implementación y pruebas anteriores. Su calidad final abierta en PowerPoint/Word con contenido de Gemini sigue sin comprobarse aquí.
- La reproducción desde el commit anterior `8de42b9` se comprobó con `python demo_grace.py --puerto 8012` y 15 rutas disponibles, sin datos privados. No se volvió a extraer y arrancar el commit de Copilot durante esta revisión.

## Problemas conocidos y estado real

| # | Problema | Estado comprobado |
| --- | --- | --- |
| 1 | Contexto autorizado y continuidad del asistente | **Integrado el 14/11/2026.** Cada mensaje usa nombre de pila y rol de la sesión, cursos autorizados y solo datos publicados; estudiantes reciben actividades, vencimiento y entrega propia; docentes reciben próxima clase y conteos de revisión/solicitudes. La acción `ninguna` utiliza ese contexto y ofrece accesos rápidos. Ocho turnos en RAM por usuario/sesión, descartados al cambiar contexto o tras 30 minutos de inactividad. Personalidad fija, sin relleno; respaldo contextual con origen exacto. Verificados SOLO `test_acciones_autorizadas.py` (17 OK) y `test_ia.py` (14 OK), con proveedores falsos. Sin navegador ni llamada real; persiste el ResourceWarning del HTTPError simulado. |
| 2 | Comunidad muestra «Failed to fetch» | **Causa del incidente no reproducida.** El módulo ya responde 200 y las pruebas pasan. El cliente aún muestra `error.message` directamente y no incorpora botón Reintentar en el error de carga. Un 200 del archivo JS no prueba la consulta autenticada de Comunidad. |
| 3 | Chat abierto intercepta «Cerrar sesión» | **Reportado por el usuario, pendiente de reproducción visual.** El panel conserva posicionamiento fijo y `z-index:40`; en ventanas bajas puede alcanzar la barra superior. No se corrigió durante esta revisión. |
| 4 | Aviso transparente sobre presencia | **Pendiente para el estudiante.** Hay aviso al profesor de que la señal no es prueba y debe confirmar. `iniciarLatidoPresencia` envía cada 45 s mientras el aula está activa y la pestaña visible; no muestra un aviso equivalente al estudiante. El servidor rechaza fechas distintas de hoy; el cliente no comprueba esa fecha antes del primer envío, por lo que abrir una sesión pasada puede provocar un aviso de error. |
| 5 | Demo limpia con sesión de hoy, próxima y actividad | Existe `demo_grace.py` con datos temporales y reglas. **No está preparado el escenario completo solicitado con fechas relativas a la defensa.** No se inspeccionaron ni cambiaron datos personales para inventar ese escenario. |
| 6 | Integrar con rama de defensa | **Pendiente.** Feature contiene las correcciones de defensa y añade dos commits de código. En el estado comprobado permite planificar avance directo de defensa, sin rehacer las funciones. No se integraron ramas en esta tarea documental. |
| 7 | Cinco fallos antiguos, lanzador antiguo y módulos sin registrar | **Resueltos en `8de42b9` y presentes en feature.** La suite actual pasa, el servidor coincide, los módulos responden y Git estaba limpio. El documento anterior estaba desactualizado. |
| 8 | Preparación de la defensa | Hay documentación y presentaciones históricas. **Faltan** guion final de 7–9 minutos, capturas de esta versión, cifras actualizadas, 15 preguntas con respuestas y respaldo probado. |

Hallazgos adicionales de la lectura, sin cambios de código:

- **Límite de acciones:** ocho acciones por usuario/sesión en ventana móvil de 60 segundos; el cupo se recupera sin iniciar otra sesión. Se conservan diez mensajes/minuto por usuario, filtro, catálogo y confirmación humana. Intervalo de API reducido de 2 a 0,2 segundos; límites verificados en las pruebas indicadas.
- **Alternar tema:** el proveedor admite `alternar` y el ejecutor tiene una rama para ello, pero `validar_propuesta` solo acepta `claro` u `oscuro`. Es una inconsistencia de código; falta un caso específico que la verifique de extremo a extremo.
- **Origen de respaldo:** la ruta contextual conserva `reglas (respaldo)` ante fallo de API; las reglas locales normales mantienen `reglas`. Se actualizó únicamente la expectativa antigua de esa etiqueta, con autorización del usuario.

## Pendientes por riesgo para la defensa

1. Contexto autorizado, memoria y límites integrados y comprobados en las dos pruebas indicadas; queda comprobar la conversación con el proveedor real tras reiniciar Grace.
2. Añadir transparencia de presencia y comprobar con cuentas separadas que una señal de conexión nunca acredita asistencia física por sí sola.
3. Reproducir y corregir Comunidad y la superposición del chat. Verificar acceso a cerrar sesión, errores comprensibles y reintento.
4. Preparar un escenario aislado y repetible con profesor, tres estudiantes, sesión de hoy, próxima sesión y actividad publicada. Conservar intactos los datos de trabajo.
5. Ensayar una historia completa en navegador, reunir capturas y solo entonces actualizar la rama de defensa y congelar una única versión identificable.
6. Verificar IA real, caída del proveedor y documentos descargables. Preparar guion, estructuras, preguntas y plan B con reglas y evidencias locales.

## Decisiones de diseño y por qué

- **La IA propone; el servidor decide.** El modelo no controla la identidad. `app.py` obtiene el usuario de la sesión y `validar_propuesta` contrasta rol y parámetros con el catálogo.
- **Lista blanca.** `grace/catalogo_acciones.py` limita acciones y parámetros; una respuesta de IA no es código ejecutable ni autorización para una operación nueva.
- **Confirmación humana.** Preparar asistencia genera una propuesta. La confirmación del profesor revalida la operación antes de guardar. Una respuesta de IA exitosa nunca sustituye esa revisión.
- **Cola enlazada propia.** Las solicitudes de ayuda usan FIFO. Las propuestas de asistencia también se almacenan en `ColaEnlazada`, pero se revisan por identificador y propietario; no afirmar que todos los profesores deban atender un frente global.
- **Presencia transparente.** Es una señal digital temporal, no vigilancia ni prueba de presencia física. La falta del aviso estudiantil es un pendiente concreto frente a esta decisión.
- **Reglas de respaldo.** Permiten mantener funciones deterministas cuando el proveedor falla. La procedencia debe mostrarse sin dar por conectada la IA solo por disponer de configuración.
- **Calma y respeto.** Las filosofías aportadas por el usuario orientan el producto: ayudar sin invadir, explicar antes de asumir, pedir confirmación cuando corresponde y reconocer límites. No se localizó ni leyó el DOCX confidencial en esta revisión; no afirmar que todos esos principios ya estén implementados por tener un filtro de palabras.

## Arranque y pruebas

Desde la raíz del proyecto:

```powershell
# Arranque habitual con los datos locales conservados
python app.py

# Ensayo aislado, reglas locales, sin clave; termina con Ctrl+C
python demo_grace.py
```

La demo abre en `http://127.0.0.1:8001` y descarta sus cambios al terminar normalmente. Las cuentas ficticias están documentadas en README. No usar datos reales para el ensayo.

Para Gemini, usar el acceso **Abrir Grace** y su ventana privada. Si ya existe una instancia, el lanzador comprueba su huella. No pegar claves en el chat, documentos, código ni Git. «Detener Grace» identifica la instancia antes de detenerla.

```powershell
$env:GRACE_IA = 'reglas'
python -m unittest discover -s tests
node --test tests/chat_flotante.test.cjs tests/ajuste_integral.test.cjs tests/cuentas_cliente.test.cjs tests/perfil_visual.test.cjs
git diff --check
```

Para repetir la auditoría sin que la importación inicial use `data/`, asignar `GRACE_DATA_DIR` a una carpeta temporal exclusiva antes de ejecutar Python. No borrar ni reutilizar los datos de trabajo como datos de prueba.

## Siguiente paso exacto

**Leer este archivo y comprobar `git status` y `git log -1` antes de cualquier edición.** Si Copilot dejó cambios nuevos, describirlos y preguntar antes de tocar esos archivos.

La tanda de contexto autorizado y límites está integrada y verificada con proveedores falsos. Mantener la rama actual hasta acordar la integración; pendiente comprobación visual y llamada real. No volver a implementar A–F.

Al terminar cada tanda, actualizar este archivo con resultados, límites de la verificación, commit de código y siguiente acción. La copia antigua en `defensa proyecto final/` debe remitir aquí para evitar estados contradictorios.

## Cómo explicarlo en la defensa

«Grace combina las estructuras propias del curso con un asistente que interpreta peticiones. Python consulta los datos autorizados, valida la acción y exige al profesor confirmar lo sensible. Si falla la IA, las reglas mantienen las operaciones compatibles. La innovación del proyecto está en integrar esa ayuda en el momento de la clase; no se afirma que sea el primer asistente educativo existente.»

| Estructura | Dónde señalarla | Explicación breve |
| --- | --- | --- |
| Listas | `grace/servicio.py`: `actividades`, `entregas`, `estado()` | Colecciones registradas que se recorren para construir el estado y calcular pendientes. |
| Cola enlazada | `grace/estructuras.py`: `ColaEnlazada.encolar`, `desencolar`, `ver_frente`; `grace/acciones.py`: `_preparar_asistencia`, `_quitar_pendiente` | Nodos propios para ayuda y propuestas. El `deque` adicional de acciones contiene tiempos del limitador, no reemplaza la cola académica propia. |
| Archivos | `grace/archivos.py`: `AlmacenJSON.leer`, `guardar`; `grace/acciones.py`: `RegistroAcciones.registrar` | Persistencia JSON y registro de eventos. El registro de acciones guarda identificadores y resultado, no el texto privado de la conversación. |
| Árbol binario | `grace/estructuras.py`: `ArbolBinarioBusqueda.insertar`, `buscar`; `grace/servicio.py`: `_reconstruir_arbol` | Índice propio para localizar actividades por ID. |
| Grafo | `grace/estructuras.py`: `GrafoAprendizaje.recorrido_anchura`, `ruta_mas_corta` | Relaciones entre temas y recorrido BFS calculado por Python; la IA puede explicar el resultado. |

Reconocer estas limitaciones antes de que se pregunten: cuentas de demostración, operación local, presencia digital sin verificación física, moderación léxica limitada, dependencia de cuota/red para IA, memoria conversacional temporal (sin persistencia) y calidad final de documentos sin validación visual actual.
