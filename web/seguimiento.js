'use strict';

const RUTA_SEGUIMIENTO = '/api/seguimiento';
const ESTADOS_SESION = {
  solicitada: 'Solicitud pendiente', presente: 'Asistió', ausente: 'Ausente',
  justificada: 'Falta justificada', injustificada: 'Falta injustificada',
};

function prepararSeguimiento() {
  if ($('seguimiento')) return;
  const pagina = document.createElement('section');
  pagina.id = 'seguimiento';
  pagina.className = 'page';
  pagina.innerHTML = '<div class="page-heading"><span class="eyebrow">CAMPUS</span><h1>Seguimiento</h1></div>' +
    '<p data-seguimiento-estado role="status"></p><div class="stack" data-seguimiento-contenido></div>';
  document.querySelector('.content > footer').before(pagina);
  const boton = document.createElement('button');
  boton.type = 'button';
  boton.className = 'small-btn';
  boton.textContent = 'Seguimiento';
  boton.addEventListener('click', () => {
    navegar('seguimiento');
    cargarSeguimiento(pagina);
  });
  $('abrir-perfil').before(boton);
  const acceso = document.createElement('button');
  acceso.type = 'button';
  acceso.className = 'outline-btn';
  acceso.textContent = 'Asistencia por sesión y constancias';
  acceso.addEventListener('click', () => boton.click());
  document.querySelector('#asistencia .page-heading').append(acceso);
}

function prepararAsistenciaSesiones(host, curso) {
  if (!host || !['profesor', 'estudiante'].includes(rolActual)) return;
  for (const sesion of curso.sesiones.filter(s => s.publicada)) {
    const panel = document.createElement('details');
    panel.className = 'panel';
    panel.innerHTML = `<summary>Asistencia · ${escapar(sesion.titulo)}</summary>
      <p data-seguimiento-estado role="status"></p><div data-seguimiento-contenido></div>`;
    panel.addEventListener('toggle', () => {
      if (panel.open) cargarAsistenciaSesion(panel, curso, sesion);
    });
    host.append(panel);
  }
}

function camposSesion(curso, sesion) {
  return `<input type="hidden" name="curso_id" value="${escapar(curso.id)}">
    <input type="hidden" name="sesion_id" value="${escapar(sesion.id)}">`;
}

function adjuntarEvidencia(constancia = false) {
  return `<label>${constancia ? 'Constancia (PDF, JPG o PNG)' : 'Foto de evidencia (JPG o PNG)'}
    <input type="file" name="archivo" accept="${constancia ? '.pdf,' : ''}.jpg,.jpeg,.png" required></label>
    <p class="micro">Hasta 3 MB. La evidencia queda disponible para tu cuenta y coordinación.</p>`;
}

async function cargarAsistenciaSesion(panel, curso, sesion) {
  const consulta = new URLSearchParams({curso_id: curso.id, sesion_id: sesion.id});
  const recargar = () => cargarAsistenciaSesion(panel, curso, sesion);
  return cargarVistaSeguimiento(panel, RUTA_SEGUIMIENTO + '/sesion?' + consulta,
    datos => renderizarAsistenciaSesion(datos, curso, sesion), recargar);
}

function renderizarAsistenciaSesion(datos, curso, sesion) {
  const campos = camposSesion(curso, sesion);
  if (rolActual === 'profesor') {
    return `<div class="stack">${datos.estudiantes.map(e => {
      const fila = datos.asistencias.find(a => a.estudiante_id === e.id);
      const aprobada = datos.solicitudes.some(j => j.estudiante_id === e.id);
      return `<form class="form panel" data-seguimiento="marcar">${campos}
        <input type="hidden" name="estudiante_id" value="${escapar(e.id)}">
        <strong>${escapar(e.nombre)}</strong>
        <p>${escapar(ESTADOS_SESION[fila?.estado] || 'Sin registrar')}${aprobada ? ' · Constancia aprobada por coordinación' : ''}</p>
        <label>Estado de ${escapar(e.nombre)} <select name="estado" required><option value="">Selecciona el estado</option>
          ${Object.entries(ESTADOS_SESION).filter(([id]) => id !== 'solicitada').map(([id, nombre]) =>
            `<option value="${id}" ${id === fila?.estado ? 'selected' : ''}>${nombre}</option>`).join('')}
        </select></label><button class="primary-btn">Confirmar asistencia</button></form>`;
    }).join('') || '<p>El curso todavía no tiene estudiantes matriculados.</p>'}</div>`;
  }
  const estado = datos.asistencias[0]?.estado;
  const solicitud = datos.solicitudes[0];
  const llegoFecha = sesion.fecha <= fechaLocal(new Date());
  return `<p>${escapar(ESTADOS_SESION[estado] || 'Sin registrar')}</p>
    ${!estado && llegoFecha ? `<form data-seguimiento="solicitar">${campos}
      <button class="outline-btn">Solicitar asistencia</button></form>` : ''}
    ${solicitud ? estadoSolicitud(solicitud) : ''}
    ${['ausente','injustificada'].includes(estado) && (!solicitud || solicitud.estado === 'rechazada')
      ? `<form class="form" data-seguimiento="justificar">${campos}${adjuntarEvidencia(true)}
        <button class="primary-btn">Enviar constancia a coordinación</button></form>` : ''}`;
}

function estadoSolicitud(solicitud) {
  const estados = {
    pendiente: ['estado-pendiente', '◷ Pendiente'],
    aprobada: ['estado-confirmado', '✓ Aprobada'],
    rechazada: ['estado-alerta', '! Rechazada'],
  };
  const [clase, nombre] = estados[solicitud.estado] || ['', solicitud.estado];
  return `<p><span class="tag ${clase}">${escapar(nombre)}</span>
    ${solicitud.comentario ? ' · ' + escapar(solicitud.comentario) : ''}</p>`;
}

function formularioEvento() {
  return `<details class="panel"><summary>Publicar anuncio o evento</summary><form class="form" data-seguimiento="evento">
    <label>Título <input name="titulo" maxlength="120" required></label>
    <label>Descripción <textarea name="descripcion" maxlength="2000"></textarea></label>
    <label>Tipo <select name="clase"><option value="evento">Evento</option><option value="charla">Charla académica</option><option value="juego">Juego</option></select></label>
    <label>Facultad <select name="facultad_id"><option value="">Todo el campus</option>
      ${catalogoAcademico.map(f => `<option value="${escapar(f.id)}">${escapar(f.nombre)}</option>`).join('')}</select></label>
    <label>Fecha <input type="date" name="fecha" required></label>
    <label>Minutos acreditables <input type="number" name="minutos" min="0" max="1440" value="0" required></label>
    <label><input type="checkbox" name="obligatorio"> Asistencia obligatoria</label>
    <button class="primary-btn">Publicar evento</button></form></details>`;
}

function renderizarSeguimiento(datos) {
  const coordinacion = rolActual === 'coordinador';
  const estudiante = rolActual === 'estudiante';
  const hoy = fechaLocal(new Date());
  return `${estudiante ? `<article id="seguimiento-horas" tabindex="-1" class="panel"><h2>Mis horas laborales</h2>
    <p><strong>${horasSeguimiento(datos.minutos)} de 25 h acreditadas</strong></p>
    <progress aria-label="Horas acreditadas" max="${datos.meta_minutos}" value="${datos.minutos}"></progress>
    <p>Solo se suman evidencias aprobadas por coordinación.</p></article>
    <article id="seguimiento-asistencia" tabindex="-1" class="panel"><h2>Mi asistencia por sesión</h2>${datos.asistencias.map(a => `<p>
      ${escapar(a.curso)} · ${escapar(a.sesion)} · ${escapar(formatFecha(a.fecha))} · ${escapar(ESTADOS_SESION[a.estado])}</p>`).join('')
      || '<p>Todavía no hay registros por sesión.</p>'}</article>` : ''}
  <section id="seguimiento-eventos" tabindex="-1" class="panel"><h2>Anuncios y eventos</h2>${coordinacion ? formularioEvento() : ''}
    <div class="stack">${datos.eventos.slice().sort((a,b)=>b.fecha.localeCompare(a.fecha)).map(e => {
      const solicitud = datos.solicitudes.find(s => s.tipo === 'horas' && s.evento_id === e.id);
      const facultad = catalogoAcademico.find(f => f.id === e.facultad_id)?.nombre || 'Todo el campus';
      return `<article class="panel"><h3>${escapar(e.titulo)}</h3>
        <p>${escapar(formatFecha(e.fecha))} · ${escapar(facultad)} · ${escapar(e.clase)}</p>
        <p class="session-text">${escapar(e.descripcion)}</p>
        <p><span class="tag">${e.obligatorio ? 'Obligatorio' : 'Opcional'}</span> ${horasSeguimiento(e.minutos)} acreditables</p>
        ${estudiante && solicitud ? estadoSolicitud(solicitud) : ''}
        ${estudiante && e.minutos && e.fecha <= hoy && (!solicitud || solicitud.estado === 'rechazada')
          ? `<form class="form" data-seguimiento="horas"><input type="hidden" name="evento_id" value="${escapar(e.id)}">
            ${adjuntarEvidencia()}<button class="outline-btn">Enviar evidencia</button></form>` : ''}</article>`;
    }).join('') || '<p>Todavía no hay eventos publicados.</p>'}</div></section>
  ${coordinacion || estudiante ? `<section id="seguimiento-solicitudes" tabindex="-1" class="panel"><h2>${coordinacion ? 'Revisar constancias y evidencias' : 'Mis solicitudes'}</h2>
    <div class="stack">${datos.solicitudes.slice().reverse().sort((a, b) => coordinacion
      ? Number(b.estado === 'pendiente') - Number(a.estado === 'pendiente') : 0).map(s =>
        `<article id="seguimiento-solicitud-${escapar(s.id)}" tabindex="-1" class="panel">
      <h3>${s.tipo === 'justificacion' ? 'Justificación' : 'Horas laborales'} · ${escapar(s.titulo)}</h3>
      ${coordinacion ? `<p>${escapar(s.estudiante_nombre)}</p>` : ''}${s.curso ? `<p>${escapar(s.curso)}</p>` : ''}
      ${estadoSolicitud(s)}<a href="${RUTA_SEGUIMIENTO}/archivo?id=${encodeURIComponent(s.id)}">Descargar evidencia</a>
      ${coordinacion && s.estado === 'pendiente' ? `<form class="form" data-seguimiento="decision">
        <input type="hidden" name="solicitud_id" value="${escapar(s.id)}">
        <label>Decisión <select name="decision"><option value="aprobada">Aprobar</option><option value="rechazada">Rechazar</option></select></label>
        <label>Comentario <textarea name="comentario" maxlength="1000"></textarea></label>
        <button class="primary-btn">Confirmar decisión</button></form>` : ''}</article>`).join('') || '<p>No hay solicitudes.</p>'}</div>
  </section>` : ''}`;
}

function horasSeguimiento(minutos) {
  const horas = Math.floor(minutos / 60);
  return horas + ' h' + (minutos % 60 ? ' ' + minutos % 60 + ' min' : '');
}

function cargarSeguimiento(pagina) {
  return cargarVistaSeguimiento(pagina, RUTA_SEGUIMIENTO, renderizarSeguimiento, () => cargarSeguimiento(pagina));
}

async function cargarVistaSeguimiento(panel, ruta, renderizar, recargar) {
  const estado = panel.querySelector('[data-seguimiento-estado]');
  const contenido = panel.querySelector('[data-seguimiento-contenido]');
  estado.textContent = 'Cargando…';
  try {
    contenido.innerHTML = renderizar(await api(ruta));
    contenido.querySelectorAll('form[data-seguimiento]').forEach(form => {
      form.addEventListener('submit', evento => guardarSeguimiento(evento, estado, recargar));
    });
    estado.textContent = '';
    return true;
  } catch (error) {
    estado.textContent = error.message;
    return false;
  }
}

async function guardarSeguimiento(evento, estado, recargar) {
  evento.preventDefault();
  const form = evento.currentTarget;
  const boton = form.querySelector('button');
  const datos = Object.fromEntries(new FormData(form));
  datos.accion = form.dataset.seguimiento;
  boton.disabled = true;
  estado.textContent = 'Guardando…';
  try {
    if (datos.archivo) {
      Object.assign(datos, await archivoTrabajo(datos.archivo));
      delete datos.archivo;
    }
    if (datos.accion === 'evento') {
      datos.minutos = Number(datos.minutos);
      datos.obligatorio = Boolean(datos.obligatorio);
    }
    await api(RUTA_SEGUIMIENTO, datos);
    if (await recargar()) estado.textContent = 'Guardado.';
  } catch (error) {
    estado.textContent = error.message;
  } finally {
    boton.disabled = false;
  }
}
