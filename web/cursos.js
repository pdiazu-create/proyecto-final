'use strict';

let cursosGrace = [];
let personasCursosGrace = {profesores: [], estudiantes: []};
let cursoGestionActual = '';
const CAMPOS_PROGRAMA = [
  ['objetivos', '◎', 'Qué vas a aprender', 'Escribe qué podrá explicar o hacer el estudiante al finalizar el curso.'],
  ['contenidos', '▤', 'Temas y unidades', 'Anota las unidades en el orden en que se estudiarán.'],
  ['organizacion', '▦', 'Cómo se trabajará', 'Describe la dinámica de clase, las entregas y cómo se evaluarán.'],
];

function etiquetaPublicacion(publicada) {
  return `<span class="tag ${publicada ? 'estado-confirmado' : 'estado-borrador'}">${publicada ? '✓ Publicado' : '✎ Borrador'}</span>`;
}

function cursosDeUsuario() {
  return cursosGrace.find(curso => curso.id === cursoGestionActual);
}

async function cargarCursosGrace() {
  const datos = await api('/api/cursos');
  cursosGrace = datos.cursos;
  if (rolActual === 'coordinador') {
    const personas = await api('/api/cursos/personas');
    personasCursosGrace = personas;
  }
  if (!cursosGrace.some(curso => curso.id === cursoGestionActual)) {
    cursoGestionActual = cursosGrace[0]?.id || '';
  }
  renderizarCursosGrace();
  renderizarHorarioReal();
  renderizarInicioAcademico();
}

async function renderizarInicioAcademico() {
  const host = $('inicio-academico');
  if (!host || !cuentaActual) return;
  const cuenta = cuentaActual;
  const profesor = cuenta.rol === 'profesor';
  const coordinador = cuenta.rol === 'coordinador';
  const estudiante = cuenta.rol === 'estudiante';
  const sesiones = cursosGrace.flatMap(curso => curso.sesiones.map(sesion => ({curso, sesion})))
    .sort((a, b) => (a.sesion.fecha + a.sesion.inicio).localeCompare(b.sesion.fecha + b.sesion.inicio));
  const hoy = fechaLocal(new Date());
  const proxima = sesiones.find(({sesion}) => sesion.publicada && sesion.fecha >= hoy);
  const borrador = sesiones.find(({sesion}) => !sesion.publicada && sesion.fecha >= hoy)
    || sesiones.find(({sesion}) => !sesion.publicada);
  const vista = document.createElement('div');
  host.replaceChildren(vista);
  const acciones = new Map();
  const boton = (nombre, accion) => {
    const id = String(acciones.size);
    acciones.set(id, accion);
    return `<button class="outline-btn" type="button" data-inicio-accion="${id}">${nombre}</button>`;
  };
  const tarjeta = (color, icono, titulo, contenido, principal = false) =>
    `<article class="panel inicio-tarjeta ${color}${principal ? ' inicio-principal' : ''}" data-tarjeta-rol="${escapar(titulo)}">
      <h2><span class="inicio-icono" aria-hidden="true">${icono}</span> ${titulo}</h2>${contenido}</article>`;
  const abrir = (item, actividadId = '') => abrirAulaGrace(item.curso, item.sesion, '', actividadId);
  const seguimiento = async destino => {
    const pagina = $('seguimiento');
    if (!pagina) return;
    navegar('seguimiento', '', async () => {
      if (!(await cargarSeguimiento(pagina)) || !pagina.classList.contains('active')) return;
      const bloque = $(destino);
      bloque?.scrollIntoView({block:'start'});
      bloque?.focus({preventScroll:true});
    });
  };
  const enlaceActividad = (pendiente, etiqueta) => boton(etiqueta, () => {
    const item = sesiones.find(({curso, sesion}) => curso.id === pendiente.curso_id && sesion.id === pendiente.sesion_id);
    if (item) abrir(item, pendiente.actividad_id);
  });
  const clase = item => `<p class="inicio-destacado">${escapar(item.sesion.titulo)}</p>
    <p>${escapar(item.curso.nombre)} · ${escapar(formatFecha(item.sesion.fecha))} ·
    ${escapar(item.sesion.inicio)} · Aula ${escapar(item.sesion.aula)}</p>`;
  const destinoCurso = () => navegar('mis-clases');
  const saludo = `<div class="page-heading inicio-bienvenida"><span class="eyebrow">ÁREA PERSONAL</span>
    <h1>Hola, ${escapar(cuenta.nombre)}</h1><p>${coordinador ? 'Gestiona tus cursos, cuentas y solicitudes.' :
      profesor ? 'Prepara tus clases y revisa el trabajo de tus estudiantes.' :
      'Encuentra tu próxima clase y consulta lo que tienes por hacer.'}</p></div>`;
  vista.innerHTML = saludo + '<p role="status">Cargando tu tablero…</p>';
  const [trabajo, campus] = await Promise.allSettled([
    coordinador ? null : api('/api/cursos/trabajo/pendientes'),
    profesor ? null : api('/api/seguimiento'),
  ]);
  if (cuenta !== cuentaActual || !vista.isConnected) return;
  const pendientes = trabajo.value?.pendientes || [];
  const solicitudes = campus.value?.solicitudes?.filter(s => s.estado === 'pendiente') || [];
  const venceHoy = estudiante && pendientes.filter(a => a.vence?.slice(0, 10) === hoy)
    .sort((a, b) => a.vence.localeCompare(b.vence))[0];
  let principal;
  if (coordinador) {
    const solicitud = solicitudes[0];
    const detalle = campus.status === 'rejected' ? 'No se pudo consultar el estado de las solicitudes.'
      : solicitud ? `${solicitudes.length} por revisar · ${escapar(solicitud.titulo)}` : 'No hay solicitudes pendientes.';
    principal = tarjeta(solicitud ? 'inicio-ambar' : 'inicio-azul', '◷', 'Solicitudes por resolver',
      `<p class="inicio-destacado">${detalle}</p>` + boton(solicitud ? 'Revisar solicitud' : 'Ver solicitudes',
        () => seguimiento(solicitud ? 'seguimiento-solicitud-' + solicitud.id : 'seguimiento-solicitudes')), true);
  } else if (venceHoy) {
    principal = tarjeta('inicio-coral', '!', 'Entrega de hoy', `<p class="inicio-destacado">${escapar(venceHoy.titulo)}</p>
      <p>Hora límite · ${escapar(venceHoy.vence.slice(11, 16))}</p>` + enlaceActividad(venceHoy, 'Abrir mi actividad'), true);
  } else if (profesor && borrador) {
    principal = tarjeta('inicio-ambar', '✎', 'Continuar preparación', clase(borrador)
      + boton('Abrir borrador', () => abrir(borrador)), true);
  } else {
    principal = tarjeta('inicio-azul', '▦', 'Próxima clase', proxima ? clase(proxima)
      + boton(profesor ? 'Preparar sesión' : 'Entrar a la sesión', () => abrir(proxima))
      : '<p>Todavía no hay próximas sesiones publicadas.</p>' + boton('Ver mis clases', destinoCurso), true);
  }
  const horario = () => tarjeta('inicio-azul', '▦', 'Mi horario', '<p>Consulta las horas y aulas de tus cursos.</p>'
    + boton('Abrir horario', () => navegar('horario')));
  const revisar = () => {
    const cantidad = pendientes.reduce((total, a) => total + a.cantidad, 0);
    if (trabajo.status === 'rejected') return '<p>No se pudo consultar la bandeja.</p>'
      + boton('Volver a consultar', renderizarInicioAcademico);
    if (!cantidad) return '<p>No hay entregas por revisar.</p>';
    return `<p>${cantidad} ${cantidad === 1 ? 'entrega pendiente' : 'entregas pendientes'}</p>
      <details><summary>Ver actividades con entregas</summary><ul>${pendientes.map(a => `<li>
        ${enlaceActividad(a, escapar(a.titulo) + ' · ' + a.cantidad)}</li>`).join('')}</ul></details>`;
  };
  vista.innerHTML = saludo + principal + '<h2 class="inicio-accesos-titulo">Accesos de trabajo</h2>' +
    `<div class="inicio-tarjetas">${profesor ? [
      tarjeta('inicio-violeta', '▤', 'Entregas por revisar', revisar()),
      tarjeta('inicio-coral', '☷', 'Solicitudes de ayuda', '<p>Consulta las dudas enviadas por estudiantes.</p>'
        + boton('Ver solicitudes', () => navegar('estructuras'))),
      horario(),
      tarjeta('inicio-verde', '✓', 'Asistencia', '<p>Abre el registro por fecha.</p>'
        + boton('Registrar asistencia', () => navegar('docentes', 'fecha-clase'))),
    ].join('') : coordinador ? [
      tarjeta('inicio-azul', '▤', 'Gestión de cursos', `<p>${cursosGrace.length} cursos registrados.</p>`
        + boton('Gestionar cursos', destinoCurso)),
      tarjeta('inicio-violeta', '◉', 'Cuentas', '<p>Administra accesos y roles.</p>'
        + boton('Abrir cuentas', () => navegar('cuentas'))),
      tarjeta('inicio-verde', '▦', 'Eventos y anuncios', '<p>Publica y consulta avisos del campus.</p>'
        + boton('Abrir eventos', () => seguimiento('seguimiento-eventos'))),
    ].join('') : [
      tarjeta('inicio-violeta', '▤', 'Mis clases', `<p>${cursosGrace.length} cursos disponibles.</p>`
        + boton('Consultar cursos', destinoCurso)),
      horario(),
      tarjeta('inicio-verde', '✓', 'Asistencia', '<p>Consulta tus registros por sesión.</p>'
        + boton('Ver asistencia', () => seguimiento('seguimiento-asistencia'))),
      tarjeta('inicio-turquesa', '◷', 'Mis horas', `<p>${campus.value ? horasSeguimiento(campus.value.minutos)
        + ' de ' + horasSeguimiento(campus.value.meta_minutos) + ' acreditadas.' : 'Consulta tu avance de horas laborales.'}</p>`
        + boton('Ver mis horas', () => seguimiento('seguimiento-horas'))),
    ].join('')}</div>`;
  personalizarTarjetasGrace(vista);
  vista.querySelectorAll('[data-inicio-accion]').forEach(control =>
    control.addEventListener('click', acciones.get(control.dataset.inicioAccion)));
}

function abrirFormularioSesion(curso, sesion = null) {
  if ($('dialogo-nueva-sesion')?.open) return;
  cursoGestionActual = curso.id;
  renderizarCursosGrace();
  const form = $('sesion-guardar');
  if (!form) {
    avisar('Tu cuenta no puede crear sesiones en este curso.', true);
    return;
  }
  const origen = document.createComment('Formulario de sesión');
  form.before(origen);
  const dialogo = document.createElement('dialog');
  dialogo.id = 'dialogo-nueva-sesion';
  dialogo.className = 'widget-dialog dialogo-sesion';
  dialogo.setAttribute('aria-labelledby', 'dialogo-sesion-titulo');
  dialogo.innerHTML = `<div class="section-heading"><h2 id="dialogo-sesion-titulo">Crear sesión</h2>
    <button type="button" class="outline-btn">Cancelar</button></div><p>${escapar(curso.nombre)}</p>
    `;
  dialogo.append(form);
  document.body.append(dialogo);
  dialogo.querySelector('button').addEventListener('click', () => dialogo.close());
  dialogo.addEventListener('close', () => {
    form.hidden = true;
    if (origen.isConnected) origen.replaceWith(form);
    dialogo.remove();
  });
  if (sesion) {
    dialogo.querySelector('h2').textContent = 'Editar sesión';
    form.querySelector('[data-sesion-paso]').textContent = 'Datos de la sesión';
    form.querySelector('[data-sesion-guia]').textContent = 'Al guardar volverás a preparar esta clase.';
    form.querySelector('button[type="submit"]').textContent = 'Guardar cambios y continuar';
    for (const campo of ['id', 'titulo', 'fecha', 'tema', 'descripcion', 'actividades', 'inicio', 'fin', 'edificio', 'piso', 'aula']) {
      form.elements[campo].value = sesion[campo] ?? '';
    }
  }
  form.hidden = false;
  dialogo.showModal();
  form.elements.titulo.focus();
}

function renderizarCursosGrace() {
  const host = $('cursos-reales');
  if (!host) return;
  const coordinador = rolActual === 'coordinador';
  host.innerHTML = `${coordinador ? `<article class="panel course-admin-form">
    <div class="panel-heading"><div><h2>Agregar curso</h2><p>El curso y su contenido se guardan en el servidor.</p></div></div>
    <form id="curso-crear" class="form"><label for="curso-nombre">Nombre</label><input id="curso-nombre" name="nombre" maxlength="120" required>
    <label for="curso-descripcion">Descripción</label><textarea id="curso-descripcion" name="descripcion" rows="2" maxlength="2000"></textarea>
    <label for="curso-seccion">Sección</label><input id="curso-seccion" name="seccion" maxlength="80">
    ${coordinador ? `<label for="curso-profesor">Profesor responsable</label><select id="curso-profesor" name="profesor_id" required>${personasCursosGrace.profesores.map(p => `<option value="${escapar(p.id)}">${escapar(p.nombre)}</option>`).join('')}</select>
    <fieldset><legend>Estudiantes inscritos</legend>${personasCursosGrace.estudiantes.map(e => `<label class="check-row"><input type="checkbox" name="estudiantes" value="${escapar(e.id)}"> ${escapar(e.nombre)}</label>`).join('')}</fieldset>` : ''}
    <button class="primary-btn" type="submit">Crear curso</button></form></article>` : ''}
    <div class="catalogo-grid" aria-label="Cursos del servidor">${cursosGrace.map(curso => `<article class="curso-tarjeta">
      <div class="curso-linea"><span class="tag">Curso académico</span>${curso.seccion ? `<span>Sección ${escapar(curso.seccion)}</span>` : ''}</div>
      <h2>${escapar(curso.nombre)}</h2><p>${escapar(curso.descripcion || 'Sin descripción.')}</p>
      <p class="micro">${curso.estudiantes.length} estudiante${curso.estudiantes.length === 1 ? '' : 's'} inscrito${curso.estudiantes.length === 1 ? '' : 's'}</p>
      <button type="button" class="outline-btn" data-curso-gestion="${escapar(curso.id)}">${coordinador ? 'Administrar curso' : 'Ver sesiones'}</button>
    </article>`).join('') || '<p class="helper-note">No hay cursos disponibles para esta cuenta.</p>'}</div>
    <div id="curso-gestion-detalle"></div>`;
  const crear = $('curso-crear');
  if (crear) crear.addEventListener('submit', crearCursoGrace);
  host.querySelectorAll('[data-curso-gestion]').forEach(boton => boton.addEventListener('click', () => {
    cursoGestionActual = boton.dataset.cursoGestion;
    renderizarCursosGrace();
    renderizarHorarioReal();
    if (coordinador) enfocarCursoGrace();
    else {
      const sesiones = $('curso-gestion-sesiones');
      sesiones?.scrollIntoView({block:'start'});
      sesiones?.focus({preventScroll:true});
    }
  }));
  renderizarDetalleCursoGrace();
}

function renderizarDetalleCursoGrace() {
  const host = $('curso-gestion-detalle');
  const curso = cursosDeUsuario();
  if (!host || !curso) return;
  host.tabIndex = -1;
  const administra = rolActual === 'profesor' || rolActual === 'coordinador';
  const coordina = rolActual === 'coordinador';
  const editaContenido = rolActual === 'profesor';
  const temas = curso.temas || [];
  const sesiones = curso.sesiones || [];
  const syllabus = curso.syllabus;
  const horario = curso.horarios || [];
  const roster = new Set(curso.estudiantes || []);
  host.innerHTML = `<article class="panel course-detail">
    <div class="section-heading"><div><span class="eyebrow">CURSO</span><h2>${escapar(curso.nombre)}</h2></div><button class="text-btn" type="button" data-curso-cerrar>Contraer</button></div>
    ${administra ? `<form id="curso-editar" class="form inline-course-form"><input type="hidden" name="curso_id" value="${escapar(curso.id)}">
      <label for="curso-editar-nombre">Nombre</label><input id="curso-editar-nombre" name="nombre" maxlength="120" value="${escapar(curso.nombre)}" required>
      <label for="curso-editar-descripcion">Descripción</label><textarea id="curso-editar-descripcion" name="descripcion" rows="2" maxlength="2000">${escapar(curso.descripcion)}</textarea>
      <label for="curso-editar-seccion">Sección</label><input id="curso-editar-seccion" name="seccion" maxlength="80" value="${escapar(curso.seccion)}">
      ${coordina ? `<label for="curso-editar-profesor">Profesor responsable</label><select id="curso-editar-profesor" name="profesor_id">${personasCursosGrace.profesores.map(p => `<option value="${escapar(p.id)}" ${p.id === curso.profesor_id ? 'selected' : ''}>${escapar(p.nombre)}</option>`).join('')}</select>
      <fieldset><legend>Matrícula</legend>${personasCursosGrace.estudiantes.map(e => `<label class="check-row"><input type="checkbox" name="estudiantes" value="${escapar(e.id)}" ${roster.has(e.id) ? 'checked' : ''}> ${escapar(e.nombre)}</label>`).join('')}</fieldset>` : ''}
      <button class="outline-btn" type="submit">Guardar datos del curso</button></form>` : ''}
    <section class="course-content-section"><div class="section-heading"><h3>Temas</h3>${etiquetaPublicacion(temas.length > 0 && temas.every(t => t.publicada))}</div>
      ${temas.length ? `<ol class="course-topic-list">${temas.map((tema, i) => `<li><div><strong>${escapar(tema.nombre)}</strong> ${etiquetaPublicacion(tema.publicada)}</div>${editaContenido ? `<form class="tema-editar inline-form" data-tema-id="${tema.id}"><input name="nombre" maxlength="80" value="${escapar(tema.nombre)}" aria-label="Nombre del tema" required><button class="mini-btn" type="submit">Guardar</button>
      <button class="mini-btn" type="button" data-tema-publicar="${tema.id}" data-publicada="${!tema.publicada}">${tema.publicada ? 'Retirar publicación' : 'Publicar tema'}</button>
      <button class="mini-btn" type="button" data-tema-mover="${tema.id}" data-direccion="-1" ${i === 0 ? 'disabled' : ''}>↑</button><button class="mini-btn" type="button" data-tema-mover="${tema.id}" data-direccion="1" ${i === temas.length - 1 ? 'disabled' : ''}>↓</button></form>` : ''}</li>`).join('')}</ol>` : '<p class="helper-note">Todavía no hay temas disponibles.</p>'}
      ${editaContenido ? `<form id="tema-agregar" class="inline-form"><label for="tema-nombre">Agregar tema</label><input id="tema-nombre" name="nombre" maxlength="80" required><button class="outline-btn" type="submit">Agregar borrador</button></form>` : ''}
    </section>
    <section class="course-content-section"><div class="section-heading"><h3>▤ Programa del curso (syllabus)</h3>${etiquetaPublicacion(syllabus.publicada)}</div>
      <p>La guía de todo el curso explica qué se aprenderá, qué temas se estudiarán y cómo se organizará el trabajo.</p>
      ${syllabus.publicada ? `<div class="syllabus-grid">${CAMPOS_PROGRAMA.map(([campo, figura, titulo]) =>
        `<article class="syllabus-bloque"><h4><span aria-hidden="true">${figura}</span> ${titulo}</h4>
          <p class="session-text">${escapar(syllabus[campo] || 'Aún sin información.')}</p></article>`).join('')}</div>`
        : '<p class="helper-note">El programa todavía no está visible para estudiantes.</p>'}
      ${editaContenido ? `<details class="syllabus-editor"><summary>${syllabus.publicada ? 'Editar programa' : 'Preparar programa'}</summary>
        <form id="syllabus-editar" class="form">${CAMPOS_PROGRAMA.map(([campo, , titulo, ayuda]) =>
          `<label for="syllabus-${campo}">${titulo}</label><p class="micro" id="syllabus-ayuda-${campo}">${ayuda}</p>
          <textarea id="syllabus-${campo}" aria-describedby="syllabus-ayuda-${campo}" name="${campo}" maxlength="4000" rows="3">${escapar(syllabus[campo])}</textarea>`).join('')}
          <button class="outline-btn" type="submit">Guardar borrador del programa</button>
        </form></details>${!syllabus.publicada && CAMPOS_PROGRAMA.some(([campo]) => syllabus[campo])
          ? '<button class="primary-btn" type="button" data-syllabus-publicar>Publicar programa</button>' : ''}` : ''}
    </section>
    <section id="curso-gestion-sesiones" tabindex="-1" class="course-content-section"><div class="section-heading"><h3>▦ Sesiones</h3>${editaContenido ? '<button class="primary-btn" type="button" data-sesion-crear>＋ Crear sesión</button>' : `<span>${sesiones.length} registradas</span>`}</div>
      <div data-trabajo-sesiones></div>
      <div data-asistencia-sesiones></div>
      ${sesiones.length ? `<div class="stack">${sesiones.map(s => `<article class="activity-row"><div class="activity-main"><strong>${escapar(s.titulo)}</strong><p>${escapar(s.fecha)} · ${escapar(s.tema || 'Sin tema')} · ${escapar(s.inicio)}–${escapar(s.fin)} · ${escapar(s.edificio)} ${escapar(s.aula)}</p><p>${escapar(s.descripcion)}</p>${etiquetaPublicacion(s.publicada)}</div>${editaContenido ? `<div><button class="mini-btn" type="button" data-sesion-editar="${s.id}">Editar</button></div>` : ''}</article>`).join('')}</div>` : `<p class="helper-note">${editaContenido ? 'Este curso todavía no tiene sesiones.' : 'El profesor todavía no ha publicado sesiones.'}</p>`}
      ${editaContenido ? `<form id="sesion-guardar" class="form formulario-sesion" hidden>
        <p class="paso-docente" data-sesion-paso>Paso 1 de 2 · Datos de la sesión</p><input type="hidden" name="id"><label for="sesion-titulo-input">Título</label><input id="sesion-titulo-input" name="titulo" maxlength="120" required>
        <label for="sesion-fecha-input">Fecha</label><input id="sesion-fecha-input" name="fecha" type="date" required>
        <label for="sesion-tema-input">Tema</label><select id="sesion-tema-input" name="tema"><option value="">Sin tema</option>${temas.map(t => `<option value="${escapar(t.nombre)}">${escapar(t.nombre)}${t.publicada ? '' : ' · borrador'}</option>`).join('')}</select>
        <label for="sesion-descripcion-input">Objetivo de la sesión</label><textarea id="sesion-descripcion-input" name="descripcion" maxlength="3000" rows="2" required></textarea>
        <label for="sesion-actividades-input">Notas para el plan (opcional)</label>
        <p id="sesion-plan-ayuda" class="micro">Las actividades con entrega se agregan al preparar la clase.</p>
        <textarea aria-describedby="sesion-plan-ayuda" id="sesion-actividades-input" name="actividades" maxlength="3000" rows="2"></textarea>
        <div class="form-row"><div><label for="sesion-inicio-input">Inicio</label><input id="sesion-inicio-input" name="inicio" type="time" required></div><div><label for="sesion-fin-input">Fin</label><input id="sesion-fin-input" name="fin" type="time" required></div></div>
        <div class="form-row"><div><label for="sesion-edificio-input">Edificio</label><input id="sesion-edificio-input" name="edificio" maxlength="1" pattern="[A-Z]" required></div><div><label for="sesion-piso-input">Piso</label><input id="sesion-piso-input" name="piso" type="number" min="1" max="9" required></div><div><label for="sesion-aula-input">Aula</label><input id="sesion-aula-input" name="aula" placeholder="A-101" pattern="[A-Z]-[1-9](0[1-9]|10)" required></div></div>
        <p class="sesion-siguiente-paso" data-sesion-guia>Después de guardar podrás subir materiales, agregar actividades o crear con Grace. La sesión seguirá en borrador hasta que la publiques.</p>
        <p class="aviso-docente" data-sesion-estado role="status"></p>
        <button class="primary-btn" type="submit">Guardar borrador y continuar</button></form>` : ''}
    </section>
    <section class="course-content-section"><div class="section-heading"><h3>Horario semanal</h3><span>De lunes a viernes</span></div>
      <p class="micro">Los bloques se repiten cada semana. Las sesiones publicadas aparecen automáticamente en su fecha.</p>
      ${horario.length ? `<ul>${horario.map(h => `<li>${DIAS_SEMANA_ES[h.dia]} · ${escapar(h.inicio)}–${escapar(h.fin)} · Edificio ${escapar(h.edificio)}, piso ${h.piso}, aula ${escapar(h.aula)}</li>`).join('')}</ul>` : '<p class="helper-note">No hay horario semanal registrado.</p>'}
      ${administra ? `<form id="horario-editar" class="form"><div id="horario-bloques">${horario.map((h, i) => bloqueHorarioForm(h, i)).join('')}</div>
        <button class="outline-btn" type="button" data-horario-agregar>Agregar bloque</button><button class="primary-btn" type="submit">Guardar horario</button></form>` : ''}
    </section>
    </article>`;
  host.querySelector('[data-curso-cerrar]').addEventListener('click', () => { cursoGestionActual = ''; renderizarCursosGrace(); });
  const editar = $('curso-editar');
  if (editar) editar.addEventListener('submit', editarCursoGrace);
  const agregar = $('tema-agregar');
  if (agregar) agregar.addEventListener('submit', agregarTemaGrace);
  host.querySelectorAll('.tema-editar').forEach(form => form.addEventListener('submit', editarTemaGrace));
  host.querySelectorAll('[data-tema-publicar]').forEach(b => b.addEventListener('click', publicarTemaGrace));
  host.querySelectorAll('[data-tema-mover]').forEach(b => b.addEventListener('click', moverTemaGrace));
  const formSyllabus = $('syllabus-editar');
  if (formSyllabus) formSyllabus.addEventListener('submit', guardarSyllabusGrace);
  const publicarSyllabus = host.querySelector('[data-syllabus-publicar]');
  if (publicarSyllabus) publicarSyllabus.addEventListener('click', publicarSyllabusGrace);
  const formSesion = $('sesion-guardar');
  if (formSesion) formSesion.addEventListener('submit', guardarSesionGrace);
  host.querySelector('[data-sesion-crear]')?.addEventListener('click', () => abrirFormularioSesion(curso));
  host.querySelectorAll('[data-sesion-editar]').forEach(b => b.addEventListener('click', () => {
    const sesion = sesiones.find(s => String(s.id) === b.dataset.sesionEditar);
    if (sesion) abrirFormularioSesion(curso, sesion);
  }));
  const formHorario = $('horario-editar');
  if (formHorario) formHorario.addEventListener('submit', guardarHorarioGrace);
  const agregarBloque = host.querySelector('[data-horario-agregar]');
  if (agregarBloque) agregarBloque.addEventListener('click', () => {
    const lista = $('horario-bloques');
    lista.insertAdjacentHTML('beforeend', bloqueHorarioForm(null, lista.children.length));
    prepararBorrarBloqueHorario();
  });
  prepararBorrarBloqueHorario();
  if (typeof prepararTrabajo === 'function') prepararTrabajo(host.querySelector('[data-trabajo-sesiones]'), curso);
  if (['profesor', 'estudiante'].includes(rolActual)) {
    const filas = host.querySelectorAll('.course-content-section .activity-row');
    sesiones.forEach((sesion, i) => {
      const fila = filas[i];
      if (!fila) return;
      const abrir = document.createElement('button');
      abrir.type = 'button';
      abrir.className = 'outline-btn';
      abrir.textContent = rolActual === 'profesor' ? 'Preparar sesión' : 'Entrar a la sesión';
      abrir.addEventListener('click', () => abrirAulaGrace(curso, sesion));
      fila.append(abrir);
    });
  }
}

function enfocarCursoGrace() {
  const detalle = $('curso-gestion-detalle');
  detalle?.scrollIntoView({block:'start'});
  detalle?.focus({preventScroll:true});
}

function bloqueHorarioForm(horario, indice) {
  const h = horario || {dia: 0, inicio: '09:00', fin: '10:00', edificio: 'A', piso: 1, aula: 'A-101'};
  return `<fieldset class="schedule-block"><legend>Bloque ${indice + 1}</legend><button class="text-btn" type="button" data-horario-borrar>Quitar</button>
    <div class="form-row"><div><label>Día</label><select data-horario="dia">${DIAS_SEMANA_ES.map((dia, i) => `<option value="${i}" ${h.dia === i ? 'selected' : ''}>${dia}</option>`).join('')}</select></div>
    <div><label>Inicio</label><input data-horario="inicio" type="time" value="${escapar(h.inicio)}" required></div><div><label>Fin</label><input data-horario="fin" type="time" value="${escapar(h.fin)}" required></div></div>
    <div class="form-row"><div><label>Edificio</label><input data-horario="edificio" maxlength="1" pattern="[A-Z]" value="${escapar(h.edificio)}" required></div>
    <div><label>Piso</label><input data-horario="piso" type="number" min="1" max="9" value="${h.piso}" required></div>
    <div><label>Aula</label><input data-horario="aula" pattern="[A-Z]-[1-9](0[1-9]|10)" value="${escapar(h.aula)}" required></div></div></fieldset>`;
}

function prepararBorrarBloqueHorario() {
  document.querySelectorAll('[data-horario-borrar]').forEach(b => {
    if (b.dataset.ligado) return;
    b.dataset.ligado = 'true';
    b.addEventListener('click', () => b.closest('.schedule-block').remove());
  });
}

function datosHorario() {
  return [...document.querySelectorAll('.schedule-block')].map(bloque => ({
    dia: Number(bloque.querySelector('[data-horario="dia"]').value),
    inicio: bloque.querySelector('[data-horario="inicio"]').value,
    fin: bloque.querySelector('[data-horario="fin"]').value,
    edificio: bloque.querySelector('[data-horario="edificio"]').value,
    piso: Number(bloque.querySelector('[data-horario="piso"]').value),
    aula: bloque.querySelector('[data-horario="aula"]').value,
  }));
}

async function mutarCursoGrace(ruta, datos, mensaje) {
  const resultado = await api(ruta, {...datos, curso_id: cursoGestionActual});
  await cargarCursosGrace();
  mostrarToast(mensaje);
  return resultado;
}

async function crearCursoGrace(evento) {
  evento.preventDefault();
  const datos = Object.fromEntries(new FormData(evento.currentTarget));
  if (rolActual === 'coordinador') {
    datos.estudiantes = [...evento.currentTarget.querySelectorAll('[name="estudiantes"]:checked')].map(e => e.value);
  }
  try {
    const resultado = await api('/api/cursos', datos);
    cursoGestionActual = resultado.id;
    await cargarCursosGrace();
    mostrarToast('Curso creado.');
  } catch (error) { avisar(error.message, true); }
}

async function editarCursoGrace(evento) {
  evento.preventDefault();
  const datos = Object.fromEntries(new FormData(evento.currentTarget));
  if (rolActual === 'coordinador') {
    datos.estudiantes = [...evento.currentTarget.querySelectorAll('[name="estudiantes"]:checked')].map(e => e.value);
  }
  try {
    await api('/api/cursos/editar', datos);
    await cargarCursosGrace();
    mostrarToast('Curso actualizado.');
  } catch (error) { avisar(error.message, true); }
}

async function agregarTemaGrace(evento) {
  evento.preventDefault();
  try {
    await mutarCursoGrace('/api/cursos/temas', Object.fromEntries(new FormData(evento.currentTarget)), 'Tema guardado como borrador.');
  } catch (error) { avisar(error.message, true); }
}

async function editarTemaGrace(evento) {
  evento.preventDefault();
  try {
    await mutarCursoGrace('/api/cursos/temas', {
      accion: 'editar', id: Number(evento.currentTarget.dataset.temaId),
      nombre: new FormData(evento.currentTarget).get('nombre'),
    }, 'Tema actualizado.');
  } catch (error) { avisar(error.message, true); }
}

async function publicarTemaGrace(evento) {
  try {
    await mutarCursoGrace('/api/cursos/temas', {
      accion: 'publicar', id: Number(evento.currentTarget.dataset.temaPublicar),
      publicada: evento.currentTarget.dataset.publicada === 'true',
    }, 'Estado de publicación actualizado.');
  } catch (error) { avisar(error.message, true); }
}

async function moverTemaGrace(evento) {
  const temas = cursosDeUsuario().temas.slice();
  const indice = temas.findIndex(tema => tema.id === Number(evento.currentTarget.dataset.temaMover));
  const destino = indice + Number(evento.currentTarget.dataset.direccion);
  [temas[indice], temas[destino]] = [temas[destino], temas[indice]];
  try {
    await mutarCursoGrace('/api/cursos/temas', {accion: 'ordenar', ids: temas.map(tema => tema.id)}, 'Orden de temas guardado.');
  } catch (error) { avisar(error.message, true); }
}

async function guardarSyllabusGrace(evento) {
  evento.preventDefault();
  try {
    await mutarCursoGrace('/api/cursos/syllabus', Object.fromEntries(new FormData(evento.currentTarget)), 'Borrador de syllabus guardado.');
  } catch (error) { avisar(error.message, true); }
}

async function publicarSyllabusGrace() {
  if (!window.confirm('¿Confirmas que este syllabus está listo para publicarse?')) return;
  try { await mutarCursoGrace('/api/cursos/syllabus/publicar', {}, 'Syllabus publicado.'); }
  catch (error) { avisar(error.message, true); }
}

async function guardarSesionGrace(evento) {
  evento.preventDefault();
  const form = evento.currentTarget;
  const dialogo = form.closest('dialog');
  const estado = form.querySelector('[data-sesion-estado]');
  const boton = form.querySelector('button[type="submit"]');
  const datos = Object.fromEntries(new FormData(form));
  if (datos.id) datos.id = Number(datos.id);
  else delete datos.id;
  datos.piso = Number(datos.piso);
  const cursoId = cursoGestionActual;
  boton.disabled = true;
  estado.classList.remove('aviso-error');
  estado.textContent = 'Guardando sesión…';
  try {
    const creada = await mutarCursoGrace('/api/cursos/sesiones', datos, 'Sesión guardada como borrador.');
    dialogo?.close();
    const curso = cursosGrace.find(c => c.id === cursoId);
    const sesion = curso?.sesiones.find(s => s.id === creada.id);
    if (sesion) abrirAulaGrace(curso, sesion);
  } catch (error) {
    estado.classList.add('aviso-error');
    estado.textContent = 'No se pudo guardar la sesión. ' + error.message;
  } finally { boton.disabled = false; }
}

async function guardarHorarioGrace(evento) {
  evento.preventDefault();
  try {
    await mutarCursoGrace('/api/cursos/horarios', {horarios: datosHorario()}, 'Horario actualizado.');
  } catch (error) { avisar(error.message, true); }
}

function bloquesHorarioReal(cursos, fecha, dia) {
  return cursos.flatMap(curso => {
    const sesiones = (curso.sesiones || []).filter(s => s.publicada && s.fecha === fecha);
    const semanales = (curso.horarios || []).filter(h => h.dia === dia && !sesiones.some(s =>
      s.inicio === h.inicio && s.fin === h.fin && s.edificio === h.edificio && s.aula === h.aula));
    return [...sesiones, ...semanales].map(b => ({...b, curso}));
  }).sort((a, b) => a.inicio.localeCompare(b.inicio));
}

function renderizarHorarioReal() {
  const host = $('horario-real');
  if (!host) return;
  if (!semanaVisible) semanaVisible = lunesDeSemana(new Date());
  const dias = [...DIAS_SEMANA_ES, 'Sábado', 'Domingo'].map((nombre, dia) => {
    const fecha = sumarDiasLocales(semanaVisible, dia);
    return {nombre, fecha, bloques: bloquesHorarioReal(cursosGrace, fechaLocal(fecha), dia)};
  });
  if (!dias.slice(5).some(dia => dia.bloques.length)) dias.splice(5);
  host.innerHTML = `<div class="semana-controles"><button class="outline-btn" type="button" data-semana-real="-7">← Anterior</button>
    <strong>${dias[0].fecha.toLocaleDateString('es-NI', {day: 'numeric', month: 'long', year: 'numeric'})} – ${dias.at(-1).fecha.toLocaleDateString('es-NI', {day: 'numeric', month: 'long', year: 'numeric'})}</strong>
    <button class="outline-btn" type="button" data-semana-real="hoy">Volver a hoy</button>
    <button class="outline-btn" type="button" data-semana-real="7">Siguiente →</button></div>
    <div class="real-schedule-grid">${dias.map(({nombre, fecha, bloques}) => `<section class="dia-horario">
      <h3>${nombre} · ${fecha.toLocaleDateString('es-NI', {day: 'numeric', month: 'long'})}</h3>
      <div class="bloques-dia">${bloques.map(b => `<article class="activity-row"><div class="activity-main">
        <p class="horario-hora">${escapar(b.inicio)}–${escapar(b.fin)}</p><strong>${escapar(b.curso.nombre)}</strong>
        ${b.titulo ? `<p>${escapar(b.titulo)}</p>` : ''}
        <p>Edificio ${escapar(b.edificio)}, piso ${b.piso}, aula ${escapar(b.aula)}</p>
      </div></article>`).join('') || '<p>Sin clases registradas.</p>'}</div></section>`).join('')}</div>`;
  host.querySelectorAll('[data-semana-real]').forEach(boton => boton.addEventListener('click', () => {
    semanaVisible = boton.dataset.semanaReal === 'hoy'
      ? lunesDeSemana(new Date())
      : sumarDiasLocales(semanaVisible, Number(boton.dataset.semanaReal));
    renderizarHorarioReal();
  }));
}

globalThis.cargarCursosGrace = cargarCursosGrace;
globalThis.renderizarCursosGrace = renderizarCursosGrace;
globalThis.renderizarHorarioReal = renderizarHorarioReal;
