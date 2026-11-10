# Grace AI · Revisión para la defensa

9 de noviembre de 2026

## Qué mostrar

Presenta Grace como un prototipo académico local con tres roles. El recorrido principal empieza en Coordinación, donde se crea el curso, se asigna el profesor y se matricula a un estudiante. El profesor prepara una sesión, publica un recurso y una actividad, y la sesión aparece en el horario. El estudiante abre la clase, consulta el material, pide una pista y entrega. El profesor publica una retroalimentación y el estudiante comprueba el resultado.

Prepara un segundo recorrido breve de Coordinación. El estudiante consulta una acreditación de horas y una justificación. El profesor aplica una falta justificada a partir de la constancia aprobada. Este recorrido ya se comprobó en el navegador con datos ficticios.

Usa un PowerPoint preparado de antemano para mostrar la exportación. El generador se ha probado con reglas y su archivo contiene un diagrama editable. La presentación generada con Gemini y su aspecto final en PowerPoint quedan pendientes de comprobar.

## Cómo explicar el código

| Pieza | Qué explicar |
| --- | --- |
| `app.py` | Entrada HTTP, autenticación y despacho de operaciones según el rol. |
| `grace/cursos.py` | Matrícula, profesor asignado, visibilidad de borradores y publicación. |
| `grace/trabajo.py` | Actividades, entregas, notas y permisos sobre preguntas y conversaciones. |
| `grace/seguimiento.py` | Solicitudes de evidencia y decisiones. La aprobación de horas suma minutos. La justificación requiere que el profesor actualice la asistencia. |
| `grace/estructuras.py` y `grace/archivos.py` | Cola FIFO de ayuda, búsqueda en el árbol, rutas BFS, listas y persistencia JSON. Muestra una operación concreta por estructura. |
| `grace/ia.py` y `grace/materiales.py` | Interfaz del proveedor, respaldo por reglas, y generación de Word y PowerPoint sin un SDK externo. El docente confirma lo que se publica. |
| `web/` | Pantallas por rol y actualización de la interfaz con datos de la API. Las preferencias visuales son locales al navegador. |

La documentación de arquitectura y los bocetos anteriores son material histórico. Para explicar el estado actual, usa los módulos y esta revisión.

## Prioridades antes de congelar la versión

1. **Arranque y versión.** El servidor activo inició antes de las modificaciones recientes. Responde a salud y reconoce publicación conjunta, pero responde 404 al módulo de personalización. Reinicia con los accesos del escritorio y comprueba que se sirvan los módulos nuevos. El aviso del lanzador comprueba una capacidad antigua. Conviene evaluar un identificador de versión que cambie con las futuras entregas.
2. **Suite completa.** Python ejecutó 177 pruebas. Pasaron 172 y fallaron 5 comprobaciones. Las 4 pruebas JavaScript pasaron. Dos comprobaciones de menú usan listas cerradas anteriores a Comunidad. Tres comprobaciones de contraste toman los últimos valores de las variables CSS y los comparan con blanco, aunque esos valores pertenecen al modo oscuro. Antes de actualizar las pruebas, verifica la navegación por rol y mide ambos temas sobre sus fondos reales. Conserva el umbral AA.
3. **Validación visual de la versión final.** Repite el flujo central en una sola instancia con datos ficticios. Comprueba que el profesor puede publicar desde el botón y que la persona matriculada ve la sesión en el curso y el horario. Revisa móvil, foco, modo oscuro y letra grande. Confirma en navegador los recorridos nuevos de Comunidad, preguntas privadas, cierre y conversación de equipo.
4. **Distribución reproducible.** Git registra el directorio de datos únicamente con su marcador vacío, pero hay cambios y módulos nuevos aún sin registrar. La rama publicada no debe confundirse con el estado del equipo. El marcador de proceso es local y debe quedar fuera de una entrega. Conserva los datos de demostración separados de los datos de trabajo.
5. **Alcance de defensa.** Las cuentas de demostración usan una clave común y el servidor está limitado al equipo local. La comunidad valida la afiliación del perfil dentro de un catálogo ficticio. Describe estas condiciones al hablar de permisos. El avatar animado, la moderación de imágenes y funciones más amplias de comunidad pueden quedar en la hoja de ruta.

## Criterio de salida

La versión para defensa queda lista cuando el arranque actualizado, la suite completa y el recorrido principal pasan sobre la misma copia. La demo debe poder repetirse en modo reglas con datos ficticios. Guarda los documentos de ejemplo y las evidencias visuales en esta carpeta.
