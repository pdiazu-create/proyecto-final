# Grace AI — Estado actual y continuidad

Actualizado: 9 de noviembre de 2026 (Nicaragua).
Registro principal de continuidad. Actualizar al terminar cada bloque, al cambiar de fase y antes de interrumpir el trabajo.

## Punto exacto de reanudación

**Fase actual: 0 — diagnóstico, pendiente de completar.**
La última intervención organizó la documentación y elaboró una revisión para la defensa. Esta actualización únicamente registra el estado, comprueba la rama y distingue las verificaciones anteriores de las pendientes. No reinició el servidor, no ejecutó pruebas, no modificó la aplicación y no hizo commits.

**Siguiente acción:** comprobar la instancia que atiende el puerto 8000 y actualizar su arranque sin perder datos. Verificar `/api/salud` y los módulos de la interfaz, incluido `/personalizacion.js`. Después ejecutar una sola línea base completa de pruebas y guardar su salida. Si hace falta introducir la clave, lo hace el usuario de forma privada; se puede continuar la validación con reglas.

## Copia de trabajo y entrega

- Proyecto vigente: `C:\Users\Usuario\Documents\proyecto-final`.
- Rama comprobada: `organizacion-grace-boceto-final`.
- Último commit comprobado: `2131b22` — `Hide local Python caches in VS Code`.
- La versión local contiene modificaciones y módulos sin registrar. El último commit **no representa** todas las funciones actuales.
- Documentación, capturas, bocetos, presentaciones y respaldos: `defensa proyecto final/`.
- Este registro: `defensa proyecto final/ESTADO_ACTUAL.md`. Mantener una sola copia de referencia en el proyecto.
- La carpeta anterior `grace boceto final/` se trasladó a `defensa proyecto final/`. Git todavía muestra eliminaciones en la ubicación anterior y archivos nuevos en la actual. Revisar el traslado antes de registrarlo.
- Predefensa: miércoles 11 de noviembre de 2026. Defensa: viernes 13 de noviembre de 2026.

## Evidencia y límites actuales

| Comprobación | Resultado | Alcance |
| --- | --- | --- |
| Rama, último commit y cambios locales | Comprobados al actualizar este archivo | Sin cambiar de rama, registrar cambios ni publicar |
| Archivos de datos registrados en Git | `data/.gitkeep` únicamente | No equivale a una auditoría de secretos de todo el repositorio |
| Marcador `.grace_proceso.json` | Existe sin registrar | No abrir ni distribuir su contenido; excluirlo de la entrega |
| Suite Python anterior | 177 pruebas ejecutadas, con 5 fallos reportados | Evidencia de la auditoría anterior; hay subpruebas, por lo que no afirmar automáticamente «172 pruebas aprobadas» |
| JavaScript anterior | 4 pruebas aprobadas | No reejecutadas para esta actualización documental |
| Servidor anterior en puerto 8000 | Salud respondía; `/personalizacion.js` devolvía 404 | Estado histórico; volver a comprobar antes de atribuirle un fallo al código actual |
| Recorridos por roles | Hay verificaciones anteriores con datos ficticios y una instancia aislada | No certifican todos los módulos recientes ni la versión completa actual |
| Gemini y documentos actuales | Pendientes de validación final | Una respuesta de IA antigua o la validez del archivo ZIP/XML no demuestra la calidad del documento actual |

Los cinco fallos reportados en Python pertenecen a comprobaciones de menú y contraste:

- `tests/test_ajuste_integral.py`: número esperado de botones móviles anterior a Comunidad.
- `tests/test_etapa2.py`: lista cerrada de páginas anterior a Comunidad.
- `tests/test_interfaz.py`: la búsqueda de la última variable CSS toma colores del tema oscuro y los compara con blanco; incluye fallos de subpruebas y una comprobación final.

No declarar que estos fallos son inocuos ni que el contraste cumple AA hasta medir ambos temas sobre sus fondos reales. El recuento definitivo debe salir de la próxima ejecución y conservarse literalmente.

## Inventario honesto

Las columnas se refieren a la evidencia disponible, no a una certificación de la versión actual.

| Implementado con recorrido anterior en navegador | Implementado sin verificar completamente en la versión actual | Solo propuesto o pendiente de confirmar |
| --- | --- | --- |
| Recorrido académico básico entre coordinación, profesor y estudiante con datos ficticios | Repetir todo ese recorrido en una sola versión, desde los menús de cada rol y con persistencia comprobada | Declarar una versión reproducible y lista para defensa |
| Consulta de sesión, recursos, entrega, nota y retroalimentación en recorridos anteriores | Todas las sesiones nuevas deben usar el aula funcional; visibilidad de borradores y materiales por rol | Autenticación y operación listas para producción |
| Aprobación de horas y justificación; aplicación docente de falta justificada en recorrido anterior | Resumen contextual de coordinación y trazabilidad completa de las decisiones | Mejoras innovadoras adicionales, máximo dos propuestas antes de implementarlas |
| Horario académico observado en recorridos anteriores | Sesiones publicadas automáticas, fines de semana y deduplicación en la versión final | Avatar animado y moderación de imágenes |
| Asistente con respaldo por reglas observado previamente | Gemini actual, contexto de sesión, pista gradual y generación real PPTX/DOCX abierta en aplicaciones compatibles | Afirmar que la IA siempre responde o que puede decidir/publicar por sí sola |
| — | Comunidad, preguntas privadas de clase, cierre, conversación de equipo y personalización: código y pruebas puntuales anteriores; navegador pendiente | Video de respaldo y diapositivas actualizadas con evidencias finales |

## Plan por riesgo para la defensa

1. Confirmar qué copia sirve el acceso «Abrir Grace» y actualizar la instancia antigua.
2. Ejecutar la línea base de Python y JavaScript; guardar salida completa y contar pruebas/subpruebas correctamente.
3. Incorporar un control de versión de arranque que detecte cambios posteriores a publicación conjunta.
4. Corregir navegación y contraste con pruebas por rol y por tema, conservando el criterio AA.
5. Hacer reproducible el repositorio con cambios pequeños, sin secretos ni datos privados.
6. Recorrer coordinación → profesor → estudiante → profesor y comprobar qué se guarda y quién lo ve.
7. Validar horas, justificaciones, Comunidad, preguntas, equipo y personalización.
8. Corregir visibilidad de borradores, duplicados, estados vacíos, controles de perfil y obstáculos visuales.
9. Revisar móvil, teclado, tamaño de texto, movimiento reducido y colores semánticos en los tres roles.
10. Comprobar Gemini y reglas; abrir PPTX/DOCX generados y revisar su presentación.
11. Preparar guion, mapa de estructuras, preguntas difíciles, limitaciones y respaldo sin internet.
12. Congelar solo una versión con evidencia completa; entregar cambios finales y riesgos pendientes.

## Seguimiento de las fases nuevas

Esta numeración corresponde al plan del texto adjunto del 9 de noviembre. No confundirla con las fases históricas de cuentas, cursos o trabajo académico, que ya tienen implementación y deben conservarse.

| Fase | Estado | Condición de cierre |
| --- | --- | --- |
| 0. Diagnóstico | Pendiente de completar | Instancia actual identificada, módulos disponibles, pruebas completas e inventario con evidencia |
| 1. Base confiable | Pendiente | Arranque verificable, pruebas sin fallos, repositorio reproducible y arranque con datos de demostración separados |
| 2. Historia completa | Evidencia parcial anterior | Recorrido actual por los tres roles, guardado y visibilidad cruzada, además de módulos recientes |
| 3. Pulido | Pendiente de revisión integral | Diseño celeste coherente, roles correctos, estados comprensibles y accesibilidad comprobada |
| 4. IA y diferenciador | Integración existente; validación pendiente | Contexto real, origen visible, respaldo comprobado y documentos abiertos y revisados |
| 5. Defensa | Material histórico disponible | Guion de 7–9 minutos, estructuras con funciones concretas, 15 preguntas, capturas y cifras finales, plan B |

## Reglas que siguen vigentes

- Conservar datos del usuario, `data/estado.json` v4 y las cinco estructuras propias. No reiniciar ni sustituir datos para mejorar una captura.
- Los cursos de demostración son de solo lectura y están separados del estado académico. No convertir datos reales en demostración ni inventar resultados académicos.
- No pedir, mostrar, guardar ni subir claves, contraseñas o sesiones. Usar transporte falso en pruebas automatizadas de IA.
- Conservar Gemini, respaldo de reglas, chat flotante, logo Puente y diseño celeste. Diferenciar los orígenes `IA`, `reglas` y `reglas (respaldo)`.
- La IA propone. El profesor revisa y confirma documentos, publicaciones y calificaciones. Coordinación confirma sus decisiones.
- Coordinación crea cursos y asigna profesores; el profesor administra los cursos asignados; el estudiante accede a lo autorizado. Comprobarlo en el servidor.
- No debilitar pruebas. El nuevo plan solicita actualizar las expectativas de navegación y medir AA sobre fondos reales; cualquier actualización debe conservar o ampliar cobertura y documentar el motivo.
- No cambiar de rama, sobrescribir cambios locales ni usar un registro masivo de archivos sin revisar. `tests/test_arranque_ia.py` ya tenía cambios antes de este registro.
- No introducir dependencias, estilos o scripts en línea sin una decisión expresa que cambie las restricciones existentes.
- Verificar el trabajo importante con pruebas antes y después; agrupar comprobaciones para evitar repeticiones innecesarias.
- No declarar una fase terminada solo porque existen sus archivos o pasan pruebas de texto. Registrar también el recorrido y las limitaciones.
- No eliminar funciones. Ordenar el alcance y consultar solo decisiones de producto que requieran al usuario.

## Cómo mantener este registro

En cada cierre de bloque actualizar, sin acumular informes contradictorios:

1. Fecha, fase actual y siguiente acción concreta.
2. Archivos modificados y comportamiento resultante.
3. Pruebas ejecutadas, resultado literal y ubicación de la evidencia.
4. Recorrido en navegador: rol, acción, guardado, vista del otro rol y limitaciones.
5. Pendientes, obstáculos y riesgo para la defensa.
6. Rama y último commit comprobados; si no hubo commit, indicarlo.

Evidencias nuevas: guardar en `defensa proyecto final/reportes/` y `defensa proyecto final/capturas/`. No incluir credenciales, cuerpos privados ni datos personales reales.

## Última intervención

- Creado este registro a partir del texto adjunto, el estado de Git y `reportes/REVISION_PARA_DEFENSA.md`.
- Comprobada la existencia de los módulos recientes y de la carpeta documental organizada.
- No se modificaron código, pruebas ni datos. No se ejecutaron pruebas ni se abrió el navegador en esta intervención.
- No hubo commit ni envío al repositorio. Las fases pendientes permanecen abiertas.
