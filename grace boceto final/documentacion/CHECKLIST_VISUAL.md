# Revisión visual local pendiente antes de exponer

El servidor y la API tienen tests automatizados. La apertura de Chromium en este entorno devolvió `ERR_BLOCKED_BY_ADMINISTRATOR`, por lo que **no debemos decir que la revisión visual quedó completada**. En tu Windows con VS Code y Chrome/Edge:

- [ ] Ejecuta `python app.py` y abre `http://127.0.0.1:8000` sin errores del navegador.
- [ ] Comprueba en **Inicio** que las tarjetas muestran valores (7 actividades, 2 entregas, 2 ayudas, 0 planes al comenzar).
- [ ] **Docente:** crea un plan con objetivo válido y edita el contenido.
- [ ] Comprueba que no puedes publicar desde borrador y que la interfaz informa el error.
- [ ] **Revisar → Aprobar → Publicar:** comprueba que aparece una actividad nueva.
- [ ] **Estudiante:** abre la actividad publicada, regístrala como entregada y confirma el contador.
- [ ] **Estructuras:** atiende la solicitud 1 (FIFO); busca la actividad por ID; calcula `Fundamentos → Grafos`.
- [ ] Abre **F12 > Consola** y comprueba que no aparecen errores JavaScript no explicados.
- [ ] En DevTools activa **390 × 844 px** (móvil); revisa navegación, formularios, botones, scroll horizontal.
- [ ] Repite en **1366 × 768 px** o mayor para revisar espaciado y lectura.
- [ ] Comprueba botones y encabezados usando tabulación de teclado.
- [ ] Pulsa **Reiniciar demo** y verifica que se restauran exclusivamente los datos ficticios.
- [ ] Captura una imagen de portada, docente y estructuras para usar en la exposición si falla el Wi‑Fi o el navegador.

El diseño puede seguir ajustándose tras esta revisión. No uses información real de estudiantes ni expongas el servidor a Internet.
