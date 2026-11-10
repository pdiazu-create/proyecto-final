'use strict';

const RUTA_COMUNIDAD = '/api/comunidad';
const CANALES_COMUNIDAD = {carrera: 'Mi carrera', facultad: 'Mi facultad'};

function reportarComunidad(publicacion) {
  if (publicacion.propia) return '';
  return `<details><summary>Reportar</summary>
    <form class="form" data-comunidad="reportar" data-id="${escapar(publicacion.id)}">
      <label>Motivo del reporte <textarea name="texto" required maxlength="300" rows="2"></textarea></label>
      <button type="submit" class="outline-btn">Enviar a Coordinación</button>
    </form></details>`;
}

function mensajeComunidad(p) {
  return `<strong>${escapar(p.autor)}</strong>
    <p class="micro">${escapar(formatFecha(p.fecha.slice(0, 10)))}</p>
    <p class="session-text">${escapar(p.texto)}</p>`;
}

function mostrarComunidad(datos, host) {
  if (rolActual === 'coordinador') {
    host.innerHTML = `<h2>Reportes pendientes</h2>${datos.reportes.map(r =>
      `<article class="panel comunidad-reporte"><span class="tag estado-pendiente">◷ Pendiente</span>
      <h3>${escapar(CANALES_COMUNIDAD[r.publicacion.canal])} · ${escapar(r.publicacion.espacio)}</h3>
      ${mensajeComunidad(r.publicacion)}<p><strong>Motivo:</strong> ${escapar(r.motivo)}</p>
      <form class="form" data-comunidad="moderar" data-id="${escapar(r.id)}">
        <label>Decisión <select name="decision" required><option value="">Selecciona una opción</option>
          <option value="conservar">Conservar publicación</option><option value="ocultar">Ocultar publicación</option>
        </select></label><button type="submit" class="primary-btn">Confirmar decisión</button>
      </form></article>`).join('') || '<p>No hay reportes pendientes.</p>'}`;
    return;
  }
  if (!datos.canales.length) {
    host.innerHTML = '<p>Elige tu facultad y carrera en tu perfil para entrar a la comunidad.</p>';
    const boton = document.createElement('button');
    boton.type = 'button';
    boton.className = 'outline-btn';
    boton.textContent = 'Abrir mi perfil';
    boton.addEventListener('click', () => navegar('perfil'));
    host.append(boton);
    return;
  }
  const respuestas = new Map();
  for (const p of datos.publicaciones) {
    if (!p.padre) continue;
    if (!respuestas.has(p.padre)) respuestas.set(p.padre, []);
    respuestas.get(p.padre).push(p);
  }
  host.innerHTML = datos.canales.map(canal => `<section class="panel comunidad-canal" data-canal="${escapar(canal)}">
    <h2>${escapar(CANALES_COMUNIDAD[canal])}</h2>
    <form class="form" data-comunidad="publicar">
      <label>Nueva publicación <textarea name="texto" required maxlength="1000" rows="2"></textarea></label>
      <button type="submit" class="primary-btn">Publicar</button>
    </form>
    <div class="stack">${datos.publicaciones.filter(p => !p.padre && p.canal === canal).reverse().map(p =>
      `<article class="panel comunidad-publicacion">${mensajeComunidad(p)}${reportarComunidad(p)}
        <div class="comunidad-respuestas">${(respuestas.get(p.id) || []).map(r =>
          `<article>${mensajeComunidad(r)}${reportarComunidad(r)}</article>`).join('')}</div>
        <details><summary>Responder</summary><form class="form" data-comunidad="responder" data-id="${escapar(p.id)}">
          <label>Respuesta <textarea name="texto" required maxlength="1000" rows="2"></textarea></label>
          <button type="submit" class="outline-btn">Publicar respuesta</button></form></details>
      </article>`).join('') || '<p>Todavía no hay publicaciones en este espacio.</p>'}</div>
  </section>`).join('');
}

async function cargarComunidad(aviso = '') {
  const pagina = $('comunidad');
  const host = $('comunidad-contenido');
  const estado = $('comunidad-estado');
  const cuenta = cuentaActual;
  estado.textContent = 'Cargando comunidad…';
  host.replaceChildren();
  try {
    const datos = await api(RUTA_COMUNIDAD);
    if (cuenta !== cuentaActual || !pagina.classList.contains('active')) return;
    mostrarComunidad(datos, host);
    estado.textContent = aviso;
    host.querySelectorAll('form[data-comunidad]').forEach(form => form.addEventListener('submit', async e => {
      e.preventDefault();
      const accion = form.dataset.comunidad;
      const datos = {...Object.fromEntries(new FormData(form)), accion};
      if (accion === 'moderar') datos.reporte_id = form.dataset.id;
      if (accion === 'reportar' || accion === 'responder') datos.publicacion_id = form.dataset.id;
      if (accion === 'publicar') datos.canal = form.closest('[data-canal]').dataset.canal;
      const boton = form.querySelector('button');
      boton.disabled = true;
      try {
        await api(RUTA_COMUNIDAD, datos);
        await cargarComunidad(accion === 'reportar' ? 'Reporte enviado a Coordinación.'
          : accion === 'moderar' ? 'Decisión guardada.' : 'Mensaje publicado.');
      } catch (error) {
        let alerta = form.querySelector('[role="alert"]');
        if (!alerta) {
          alerta = document.createElement('p');
          alerta.className = 'aviso-docente aviso-error';
          alerta.setAttribute('role', 'alert');
          boton.before(alerta);
        }
        alerta.textContent = error.message;
      } finally {
        boton.disabled = false;
      }
    }));
  } catch (error) {
    if (cuenta === cuentaActual) estado.textContent = error.message;
  }
}
