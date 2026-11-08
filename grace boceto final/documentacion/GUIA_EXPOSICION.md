# Grace AI · Guion para exposición del proyecto final

**Curso:** Programación Estructurada · **Lenguaje:** Python  
**Tiempo objetivo:** 7–9 minutos, incluyendo demostración. Presentar 10 diapositivas; la última queda como apéndice opcional.  
**Regla de defensa:** diferenciar demo funcional, simulación y visión futura.

## 1. Apertura (45 segundos)

> Grace AI es el prototipo de una plataforma académica que busca simplificar la organización entre docentes y estudiantes. No es un chatbot comercial ni un reemplazo funcional de la plataforma de la UAM. Esta primera versión demuestra un recorrido académico completo usando Python y cinco estructuras vistas en Programación Estructurada: listas, colas enlazadas, archivos, árboles y grafos.

Explicar el lema: **Tiempo. Claridad. Tranquilidad.**

## 2. Problema y propuesta (1 minuto)

Un docente debe organizar actividades, seguimiento y consultas; un estudiante debe recordar tareas y fechas. Grace concentra estos procesos en una experiencia sencilla. Para el proyecto final usamos datos de prueba y un curso de Programación Estructurada.

## 3. Demostración guiada (3–4 minutos)

1. **Panel de inicio:** señalar las tarjetas de actividades, entregas, ayudas y planes. No son números escritos en HTML; los obtiene el navegador desde `/api/estado`.
2. **Docente:** escribir un objetivo como «Enseñar el recorrido de listas y la búsqueda lineal con ejercicios», seleccionar `Listas`, asignar una fecha y generar un borrador. Explicar que es una plantilla de reglas, **no una IA generativa**.
3. **Aprobación humana:** editar el contenido de un borrador y destacar el regreso al estado `borrador`. Pasar por `revisar → aprobar → publicar`. Intentar saltar un estado para explicar la validación.
4. **Estudiante:** abrir su espacio y registrar la entrega de la nueva actividad publicada.
5. **Estructuras:** mostrar el frente de la cola enlazada, atender la solicitud 1, buscar una actividad por ID en el árbol y calcular una ruta `Fundamentos → Grafos` usando BFS.

## 4. Explicación técnica (2 minutos)

- **Listas:** `self.actividades`, `self.entregas`, `self.planes`; búsqueda, agregado y recorrido con ciclos.
- **Cola enlazada:** `NodoCola` tiene `valor` y `siguiente`; `ColaEnlazada` mantiene `frente` y `final`. `encolar` y `desencolar` son O(1). Uso: solicitudes.
- **Archivos:** `AlmacenJSON` utiliza `with`, UTF-8, `flush`, `fsync` y `os.replace` para el temporal. Uso: el estado sobrevive a reinicios normales; un archivo ausente después de inicializar produce un error, no una semilla silenciosa. No hay garantía de durabilidad ante todo fallo físico.
- **Árbol binario:** se indexa por ID, con `insertar`, `buscar`, `en_orden`, `niveles`, `altura` y reconstrucción balanceada sin recursión. Uso: búsqueda de actividades. Reconstrucción O(n); búsqueda O(h).
- **Grafo dirigido:** `adyacencia` indica prerrequisitos, BFS explora vecinos y reconstruye la ruta mínima. Uso: temas y rutas.

## 5. Tres preguntas que pueden hacerte

### Pregunta 1. ¿Por qué una universidad usaría Grace si ya tiene su sistema académico y puede utilizar ChatGPT?

**Respuesta:** Grace propone una experiencia institucional integrada: conecta tareas y seguimiento con decisiones revisables dentro del contexto del curso. ChatGPT es un asistente general; este prototipo implementa un flujo académico. No hemos demostrado que sea superior a una plataforma universitaria, ni que reemplazarla sea viable. Lo siguiente sería medir tiempo ahorrado y facilidad de uso con permisos y un piloto autorizado.

### Pregunta 2. ¿Por qué programaron una cola enlazada y un árbol manualmente si Python ya tiene listas y diccionarios?

**Respuesta:** Porque el objetivo académico es implementar las estructuras, entender sus invariantes y justificar su complejidad. La cola necesita referencias al frente y al final y garantiza atención FIFO. El árbol es un índice ordenado por ID con búsqueda O(h), donde h es la altura. Al insertar IDs consecutivos puede degenerar; en esta versión reconstruimos el árbol desde sus elementos ordenados cuando la altura excede un umbral, operación O(n). Sabemos que un sistema comercial elegiría otras herramientas por eficiencia y escala.

### Pregunta 3. ¿Qué pasa si se pierde la conexión o se apaga el programa cuando el docente publica una actividad?

**Respuesta:** El estado de planes y actividades se escribe en un único archivo JSON mediante un temporal y reemplazo atómico. El servicio modifica memoria, intenta guardar y revierte la memoria si ocurre un error. Esto reduce inconsistencias en la demostración local; no equivale a transacciones de una base de datos real ni garantiza la persistencia ante cualquier fallo de hardware. En producción se necesitaría una base de datos transaccional.

## 6. Tres preguntas extra difíciles para practicar

**¿Tiene control de acceso por roles?** No. Las pantallas muestran el contexto de dos tipos de usuario, pero no existe autenticación segura. Afirmar lo contrario sería incorrecto. En una próxima versión se necesitaría una identidad institucional verificada, controles por recurso, sesiones seguras y auditoría.

**¿Grace tiene inteligencia artificial real?** No todavía. `generar_borrador_plan` utiliza reglas y plantillas deterministas. El diseño permite sustituir ese motor por un proveedor de IA más adelante, con protección de datos y revisión docente.

**¿Y si miles de actividades desequilibran el árbol?** Es un BST convencional, así que un orden secuencial puede convertirlo en cadena. Grace v0.4 reconstruye el índice balanceado desde un recorrido en orden si la altura supera `bit_length(n) + 2`. Reconstruir cuesta O(n), así que no es AVL ni garantiza O(log n) para toda inserción. Para producción usaríamos índices de base de datos o árboles autoequilibrados.

## 7. Archivo ausente vs. archivo corrupto (respuesta concreta)

**¿Qué ocurre si el profesor borra `data/estado.json`?** En una carpeta nueva, Grace crea datos ficticios. Al arrancar por primera vez v0.4 crea la marca `.grace_inicializada`; si después desaparece `estado.json`, el servicio deja de arrancar y pide recuperar una copia, en lugar de suponer que los datos desaparecieron voluntariamente. Un archivo ilegible también produce error y conserva sus bytes. La marca es solo una protección básica, no una copia de seguridad.

**¿Quién hace la revisión y quién aprueba?** En esta demostración es el mismo actor ficticio `docente_demo`. Separar ambos estados permite comprobar que se terminó la revisión antes de autorizar la publicación, y facilita incorporar permisos reales en el futuro; **no existe verificación de identidad en esta versión**.

## 8. Guion de 7–9 minutos por diapositiva

- **0:00–0:40:** portada y aclaración de que es un prototipo sin IA generativa.
- **0:40–1:30:** problema y alcance (diapositivas 2–3).
- **1:30–2:10:** flujo de aprobación (4).
- **2:10–2:50:** cinco estructuras (5).
- **2:50–3:30:** arquitectura y estados (6–7).
- **3:30–4:00:** pruebas, límites y diferenciación (8–9).
- **4:00–7:30:** demostración completa en navegador o consola, dependiendo del tiempo.
- **7:30–8:00:** cierre (10), con un margen breve para preguntas. La última diapositiva es de respaldo y no es parte del recorrido normal.

## 9. Cierre (20 segundos)

> Grace nace con una visión grande, pero esta entrega es deliberadamente concreta: conectar un objetivo docente con una actividad publicada, atendiendo solicitudes y mostrando rutas de aprendizaje con estructuras propias. No solo mostramos una web: podemos explicar y probar el código que funciona detrás.
