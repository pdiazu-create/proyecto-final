# Revisión técnica de Grace v0.4

## Cambios realizados respecto de v0.2

| Hallazgo en v0.2 | Corrección en v0.3 | Cómo se comprobó |
|---|---|---|
| Archivo faltante podía reiniciar silenciosamente | Primera ejecución crea semilla y marca `.grace_inicializada`; si se borra después `estado.json`, se detiene con error. Corruptos también se rechazan | Tests de ausencia posterior, inicialización y corrupción |
| Publicación escribía planes y actividades en archivos independientes | Ambos registros se guardan en un único snapshot JSON, con recuperación de memoria si falla guardar | Test de publicación con fallo simulado de disco |
| Recorrido recursivo del árbol podía fallar con árboles profundos | `en_orden` y `niveles` ahora son iterativos | Test de 1.800 nodos |
| BFS usaba `pop(0)` en listas | Se sustituyó por índice frontal, manteniendo BFS manual | Tests de rutas, ciclos y origen=destino |
| No se podía editar un borrador | Nuevo `editar_plan`; al modificar durante revisión regresa a borrador | Test de edición y re-aprobación |
| Reinicio accesible con POST vacío | Requiere un texto explícito de confirmación para la demo | Test HTTP de reinicio no confirmado |
| Respuestas HTTP poco protegidas | Cabeceras CSP, no-store, X-Content-Type-Options; comprobación básica de Host y Origin | Pruebas HTTP de archivos y origen |
| Cobertura inicial limitada | 10 pruebas iniciales + 21 regresión + 6 HTTP + 10 específicas v0.4 = **47 pruebas** | `python -m unittest discover -s tests -v` |

## Verificado

- 47 pruebas automáticas pasan.
- La prueba HTTP completa comprobó crear, editar, revisar, aprobar y publicar un plan, así como registrar entrega, hacer búsqueda en árbol, pedir ruta y consultar al asistente.
- La sintaxis del JavaScript pasó `node --check web/app.js` (Node se utilizó solo para esta verificación; no es necesario para ejecutar Grace).
- El servidor sirve correctamente HTML, CSS, JS y favicon.

## Lo que **no** debe afirmarse

- No existen cuentas y permisos reales para profesores/estudiantes.
- No se ha conectado UAM Virtual ni se ha realizado migración académica institucional.
- No hay IA generativa: Grace aplica reglas y plantillas.
- Las pruebas de seguridad son básicas, no equivalen a auditoría de seguridad.
- No hay sincronización multiusuario, cifrado de datos en reposo, teleclases, app móvil instalable ni garantía de disponibilidad.
- Se intentó verificar visualmente con Chromium en este entorno, pero bloqueó la navegación a localhost. **El resultado visual sigue pendiente de prueba manual** en Chrome/Edge en VS Code; ver `CHECKLIST_VISUAL.md`.

## Prioridades futuras (v0.5 y posteriores)

1. Pruebas reales de uso en Chrome/Edge y móviles, corregir accesibilidad.
2. Si el profesor lo pide, implementar árbol de cursos → unidades → temas además del BST actual; no atribuirlo al código actual.
3. Autenticación real y permisos verificados por backend antes de desplegar públicamente.
4. Sustituir archivos por un almacenamiento transaccional si se incorpora multiusuario.
5. IA generativa opcional en `grace/asistente.py`, bajo revisión docente y sin enviar datos identificables a proveedores sin autorización.

**Revisión de privacidad:** el ZIP no incluye el documento confidencial de Grace v1.1 ni archivos con datos académicos reales. Los nombres de estudiantes son inventados.

## Correcciones específicas de v0.4

- **Árbol:** se añadieron `altura()`, `reconstruir_balanceado()` y `balancear_si_necesario()` en `grace/estructuras.py`. La reconstrucción elige el punto medio de cada intervalo ordenado y evita recursión. El servicio la utiliza durante la publicación si la altura excede el umbral y al cargar un estado antiguo. **Esto no es un AVL**: calcular la altura y reconstruir cuestan O(n).
- **Archivo eliminado:** se añade `.grace_inicializada` como marca local después del primer guardado. Si falta `estado.json` posteriormente, no se regenera la semilla sin avisar. Si también se borra la marca, el programa no puede saber que había datos anteriores; se necesitarían respaldos externos para recuperación real.
- **Versión del archivo:** se validan versiones 3 y 4 del estado; las desconocidas producen error explícito. Guardados nuevos se realizan en versión 4.
- **Pruebas:** 47 pruebas en total; incluyen reconstrucción de 1.800 nodos, 30 publicaciones secuenciales, lectura de formato 3, archivo faltante, archivo corrupto, versiones desconocidas y solicitudes simultáneas.
- **Persistencia:** `flush` + `fsync` del temporal + `os.replace`; esto no debe describirse como garantía de supervivencia ante cualquier apagón o fallo de hardware. No hay sincronización multiproceso ni fsync explícito del directorio tras el reemplazo.
- **Aprobación:** revisión y aprobación se ejecutan por el actor fijo `docente_demo`; su separación prepara un flujo futuro con identidades distintas, pero hoy no existe autenticación.
