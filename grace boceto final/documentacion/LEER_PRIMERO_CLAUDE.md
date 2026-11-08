# Grace AI · Entrega para revisión de Claude

## Qué contiene este ZIP

Copia del proyecto de `C:\Users\Usuario\Documents\Grace_gemini`, utilizada en Visual Studio Code, tomada el 8 de noviembre de 2026 (America/Managua). El código y los datos existentes se copiaron sin implementar funciones adicionales para esta entrega. Se añadieron esta nota, los bocetos acordados y un manifiesto de archivos.

No se incluyeron claves de API, archivos .env, cachés, entornos, logs, accesos directos personales ni el marcador temporal .grace_proceso.json. Se revisaron patrones de credenciales incrustadas sin imprimir sus valores. Esta comprobación no sustituye una auditoría exhaustiva.

## Verificación de esta copia

Se ejecutó con modo reglas para que las pruebas no necesiten credenciales reales:

```text
python -m unittest discover -s tests
Ran 113 tests in 9.663s
OK

node tests/chat_flotante.test.cjs
OK: abrir, cerrar, reabrir, respuesta en flotante y chat, desactivado sin red.
```

Hay ResourceWarning de cierre de HTTPError en pruebas existentes; la suite termina en OK. No se debilitaron ni modificaron pruebas para preparar este ZIP. No se hizo una nueva inspección visual de navegador ni una llamada real a Gemini durante el empaquetado.

El usuario confirmó previamente una conexión real con Gemini: HTTP 200, origen IA. Eso es evidencia de una prueba anterior, no una garantía de disponibilidad o cuota futura.

## Estado actual que debes revisar en el código

- Python y biblioteca estándar con HTML/CSS/JavaScript propios, servidor local.
- Persistencia data/estado.json versión 4 y estructuras propias.
- Selector de rol simulado, sin autenticación real.
- Planes en borrador, revisión, aprobación y publicación; asistencia y entregas registradas según las funciones actuales.
- Interfaz con páginas de curso, calendario, asistencia y asistente flotante.
- Proveedor Gemini por urllib, modelo gemini-3.5-flash-lite con razonamiento mínimo, timeout configurable de Gemini (30 segundos en su iniciador), origen de respuesta y respaldo de reglas. OpenAI sigue disponible.
- Contexto mínimo de datos del curso, validaciones de planes y revisión humana. Las pruebas de API emplean proveedores y transportes falsos.
- Diagnóstico de HTTP/red/timeout, encabezado que distingue configuración de conexión y protección contra instancias duplicadas del servidor.
- Abrir_Grace.pyw y gestor_grace.py para iniciar sin consola; clave introducida en una ventana privada y conservada solo en memoria. Los accesos .lnk del equipo no son portables y no se incluyen.

No des por implementada una función solo porque aparece en los bocetos o se describe en esta nota. Verifica el código. README y documentos antiguos pueden contener cifras o textos históricos: el recuento actual verificado para esta entrega es 113.

## Diseño aprobado y funciones futuras

La carpeta `../bocetos/` contiene la lámina final de 16 vistas y la ampliación de la sesión. Son propuestas, con personas, aulas, horarios, cifras y notas ilustrativas. La aplicación no ha sido transformada aún en esas 16 pantallas funcionales.

Dirección visual: celeste protagonista, azul medio para acciones, texto azul oscuro, tarjetas blancas e iconos monocromáticos junto al nombre del tipo de contenido. Turquesa/coral solo como detalles. Chat flotante opcional, sin quitar ancho al contenido.

Funciones diseñadas, pendientes de implementación completa:

- Cuentas y permisos reales de estudiante, profesor y coordinación.
- Syllabus oficial, unidades, sesiones y horario registrado con edificio, piso, aula y sección.
- Sesión inmersiva con visor grande, agenda antes/durante/después, materiales, preguntas y actividad ampliable. La lista de sesiones permanece como índice.
- Recursos Word/PowerPoint/PDF, videos, enlaces y publicación individual durante la clase. IA para preparar documentos, y búsqueda externa como integración adicional. No asumir que la IA actual lee adjuntos ni busca recursos.
- Archivos de entrega, grupos con cupos, rúbricas y calificaciones confirmadas por el docente.
- Asistencia ampliada, solicitudes pendientes, corrección de fechas anteriores y justificaciones revisadas por facultad.
- Eventos, anuncios, evidencia privada y meta configurable de 25 horas: solo sumar horas aprobadas.
- Comunidad por carrera/facultad, canales y grupos, moderación y perfiles con foto/banner.
- Personalización limitada: modo claro/oscuro, tamaño de texto y widgets. Avatar editable/animado más adelante.

## Decisiones importantes de la conversación

- El usuario pidió retirar las explicaciones técnicas de la experiencia habitual. La sección docente se convirtió en Solicitudes de ayuda; no se debe presentar su ausencia del menú estudiantil como un cambio accidental. Se puede proponer una vista técnica docente opcional para la defensa, sujeta a aprobación del usuario.
- No es obligatorio migrar estado.json a v5 para cada función nueva: también se puede evaluar almacenamiento complementario. Cualquier alternativa exige diseño y pruebas; todavía no se decidió una migración.
- La IA propone y las personas confirman publicaciones, calificaciones, justificaciones y horas. Una solicitud de asistencia nunca prueba presencia física.
- Los archivos médicos/constancias y datos académicos deben ser privados. La simulación actual de roles no es adecuada para datos reales.
- No enviar archivos a proveedores externos automáticamente ni garantizar que todo enlace sea seguro.

## Cómo ejecutar para revisar

```powershell
python app.py
```

Abre http://127.0.0.1:8000. Sin variables de IA, el modo predeterminado es reglas. Para usar Gemini, iniciar_gemini.ps1 o Abrir_Grace.pyw solicitan la clave privadamente. Nunca solicitarla por chat ni escribirla en código o documentación.

## Revisión solicitada

Revisa primero el código y las pruebas de este ZIP. Diferencia problemas confirmados de hipótesis y propuestas visuales. Informa los comandos ejecutados y lo que no pudiste comprobar. No modifiques pruebas existentes ni implementes una ampliación de alcance sin la instrucción del usuario.
