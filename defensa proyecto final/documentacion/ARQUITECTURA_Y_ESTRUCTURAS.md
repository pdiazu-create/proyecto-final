# Arquitectura y justificación de las estructuras

## A. Separación de responsabilidades

`web/` contiene presentación e interacciones visuales. No decide si un plan se puede publicar.  
`app.py` recibe solicitudes HTTP, limita tamaño y rutas y llama al servicio.  
`grace/servicio.py` valida datos, gobierna el flujo de estados y coordina los algoritmos.  
`grace/estructuras.py` contiene implementaciones didácticas de cola, árbol y grafo.  
`grace/archivos.py` gestiona almacenamiento JSON.  
`grace/asistente.py` genera borradores mediante plantillas y responde por coincidencia de palabras.
`grace/catalogo_acciones.py` define la lista blanca y los permisos; `grace/acciones.py` valida, limita, registra y ejecuta las acciones permitidas.

## B. Invariantes verificables

**Cola enlazada:** si `tamano == 0`, entonces `frente` y `final` deben ser `None`. Si tiene un único nodo, `frente is final`. Las inserciones se hacen por `final` y las extracciones por `frente`. Los tests verifican vaciado y reutilización.

**Árbol binario de búsqueda:** para cada nodo, las claves menores van a la izquierda y las mayores a la derecha. Una clave repetida reemplaza el valor, no aumenta el tamaño. `en_orden()` devuelve las actividades ordenadas por ID. Los recorridos son iterativos, incluso con 1.800 nodos consecutivos. `reconstruir_balanceado` forma un árbol más bajo utilizando el elemento central de cada intervalo ordenado. `balancear_si_necesario` decide reconstruir cuando la altura supera `tamano.bit_length() + 2`; es una estrategia didáctica, no AVL.

**Grafo dirigido:** la tabla de adyacencia contiene una lista de vecinos por tema. BFS lleva un conjunto de visitados y una cola lógica con puntero frontal, evita ciclos, y reconstruye la ruta por predecesores. No se utiliza NetworkX.

**Listas:** las actividades, planes, asistencias y entregas se recorren, filtran, agregan y validan con expresiones y ciclos de Python. La idea es aplicar la estructura a un problema real, no acumular listas vacías.

**Archivos:** `estado.json` es la fuente persistente. El archivo se reemplaza de manera atómica por uno temporal escrito con UTF-8. La aplicación no recupera automáticamente un archivo corrupto porque hacerlo podría destruir información. La primera ejecución crea una semilla ficticia y una marca local `.grace_inicializada`. Si luego falta `estado.json`, Grace aborta en lugar de reiniciar en silencio. Los formatos de estado 3 y 4 se admiten; otras versiones se rechazan. El usuario restablece los datos deliberadamente mediante el botón de la demo.

## C. Estados y permisos de la demo

```text
crear → borrador → en_revision ──aprobar──→ aprobado ──publicar──→ publicado
                      └─rechazar──→ rechazado
editar (en borrador o revisión) → borrador
```

- Las reglas de transición y los permisos los aplica el **servidor Python**, no la interfaz.
- `historial` almacena acción, estado resultante, actor de demostración y marca temporal en UTC.
- En el servidor principal, el actor y el rol proceden de una sesión autenticada; los campos que envía el navegador o la IA no conceden permisos.
- La creación de una actividad publicada y su plan se guardan juntos.

## Acciones autorizadas de bajo riesgo

El catálogo actual permite cambiar tema, abrir pantallas autorizadas, consultar la próxima sesión y resumir el horario semanal. Cada definición incluye roles, parámetros, riesgo y requisito de confirmación. La IA propone JSON, pero el servidor valida la forma, los parámetros, la cuenta y el curso antes de ejecutar. Una acción no incluida en `CATALOGO_ACCIONES` se rechaza.

Los horarios se calculan desde los cursos visibles para la cuenta autenticada. La interfaz puede mostrar bloques ilustrativos, pero Grace no los usa como datos académicos. El tema se persiste por cuenta en `preferencias.json`; los eventos de propuesta, rechazo y ejecución van a `acciones.jsonl` sin guardar los mensajes. El archivo `config/palabras_bloqueadas.json` controla el filtro de entrada y salida.

## D. Persistencia: por qué una única unidad atómica

En v0.2, publicar escribía `actividades.json` y `planes.json`. Si fallaba el segundo archivo, podía quedar la actividad publicada sin que el plan lo reflejara.

Desde v0.3, el estado completo se escribe como `estado.json`. `ServicioGrace._mutar` mantiene un respaldo del estado previo en memoria; ante fallo de escritura, reconstruye la cola y el árbol a partir del respaldo. Esto **mejora la integridad en un proceso local**. Para entornos multiusuario y sistemas reales se necesitaría una base de datos transaccional y un control de acceso robusto.

## E. Complejidad teórica

| Operación | Orden aproximado |
|---|---|
| Encolar / desencolar solicitud | O(1) |
| Recorrer cola | O(n) |
| Insertar / buscar en BST | O(h), con h=altura; sin equilibrado puede llegar a O(n) |
| Calcular altura / reconstruir BST | O(n) cada operación; reconstrucción produce altura O(log n) |
| Recorrer árbol | O(n) |
| BFS y ruta en grafo (V temas, E aristas) | O(V + E) |
| Búsqueda lineal en lista de entregas | O(n) |
| Guardar estado completo JSON | O(tamaño total del estado) |

## F. Limitaciones reconocidas

El servidor principal exige sesión y verifica roles, pero las cuentas y cursos de este prototipo son ficticios y permanecen en archivos locales. Los bloqueos de chat se conservan en memoria y se reinician al reiniciar el proceso. El registro JSONL y los archivos JSON no sustituyen una base transaccional, auditoría centralizada ni alta disponibilidad. `demo_grace.py` es una demostración aislada y no debe confundirse con el servidor principal autenticado. Nada de esto se ha certificado para producción ni para datos institucionales reales.

## G. Preguntas para la defensa

- **¿Un árbol balanceado implica insertar siempre en O(log n)?** No. Este BST no se autoequilibra nodo por nodo: reconstruir el índice a veces cuesta O(n), aunque el árbol reconstruido tenga altura O(log n).
- **¿Por qué dos estados para revisar y aprobar si es el mismo docente?** `en_revision` señala que se dejó de editar y se comprueba el borrador; `aprobado` registra la autorización para publicar. En esta demo el actor es fijo y no es una identidad real; la separación prepara un flujo de roles futuros.
- **¿Qué significa validar Origin?** Es una limitación básica de peticiones HTTP para un servidor local, no una garantía de seguridad, autorización o antifraude.
- **¿Qué se pierde con varios procesos?** `RLock` solo sincroniza hilos del mismo proceso, no protege accesos concurrentes de múltiples servidores a `estado.json`.
