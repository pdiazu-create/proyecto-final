'use strict';

const RUTA_TRABAJO = '/api/cursos/trabajo';
const FORMATOS_TRABAJO = '.pdf,.docx,.pptx,.txt,.png,.jpg,.jpeg';
const CATEGORIAS_MATERIAL = {presentacion:'Presentación', lectura:'Lectura', video:'Video', apoyo:'Archivos de apoyo'};
const MOMENTOS_MATERIAL = {antes:'Antes de clase', durante:'Durante la clase', despues:'Después de clase'};
let temporizadorPresencia = null;

function iniciarLatidoPresencia(aula, cursoId, sesionId) {
  clearInterval(temporizadorPresencia);
  if (rolActual !== 'estudiante' || aula.dataset.sesionPublicada !== 'true') return;
  const enviarLatido = async () => {
    if (!aula.isConnected || !aula.classList.contains('active')) {
      clearInterval(temporizadorPresencia);
      temporizadorPresencia = null;
      return;
    }
    if (document.visibilityState === 'hidden') return;
    try {
      await api('/api/presencia', {curso_id: cursoId, sesion_id: sesionId});
    } catch (error) {
      clearInterval(temporizadorPresencia);
      temporizadorPresencia = null;
      mostrarToast('No se pudo actualizar la presencia: ' + error.message);
    }
  };
  enviarLatido();
  temporizadorPresencia = setInterval(enviarLatido, 45000);
}

function prepararTrabajo(host, curso) {
  if (!host || !['profesor', 'estudiante'].includes(rolActual)) return;
  if (rolActual === 'estudiante') {
    const calificaciones = document.createElement('details');
    calificaciones.className = 'panel';
    calificaciones.innerHTML = '<summary>Calificaciones del curso</summary><div aria-live="polite"></div>';
    calificaciones.addEventListener('toggle', async () => {
      if (!calificaciones.open) return;
      const lista = calificaciones.querySelector('div');
      lista.textContent = 'Cargando…';
      try {
        const {notas} = await api(RUTA_TRABAJO + '/notas?curso_id=' + encodeURIComponent(curso.id));
        lista.innerHTML = notas.map(n => `<article><h4>${escapar(n.actividad)}</h4>
          <p>${escapar(n.sesion)} · ${escapar(n.puntaje)}/100</p><p class="session-text">${escapar(n.comentario)}</p></article>`).join('')
          || '<p>Aún no hay calificaciones publicadas.</p>';
      } catch (error) {
        lista.textContent = error.message;
      }
    });
    host.append(calificaciones);
  }
}

function abrirAulaGrace(curso, sesion, herramienta = '', actividadId = '') {
  const anterior = $('aula-grace');
  const aula = document.createElement('section');
  aula.id = 'aula-grace';
  aula.className = 'page';
  aula.dataset.cursoId = curso.id;
  aula.dataset.sesionPublicada = String(sesion.publicada);
  if (anterior) anterior.replaceWith(aula);
  else document.querySelector('.content > footer').before(aula);
  const tema = sesion.tema || sesion.titulo;
  const profesor = rolActual === 'profesor';
  const temaBorrador = curso.temas?.some(t => t.nombre === sesion.tema && !t.publicada);
  aula.innerHTML = `<div class="aula-migas">Mis clases / ${escapar(curso.nombre)} / ${escapar(sesion.titulo)}</div>
    <button type="button" class="text-btn aula-volver" data-aula-volver>← Todas las sesiones</button>
    <div class="aula-layout">
    <div class="stack"><div class="page-heading aula-encabezado">
      ${profesor ? '<p class="paso-docente">Paso 2 de 2 · Preparar la clase</p>' : ''}
      <div class="aula-titulo-linea">${iconoAula('agenda')}<h1 id="aula-titulo" tabindex="-1">${escapar(sesion.titulo)}</h1>
        ${profesor && !sesion.publicada
          ? '<span class="tag estado-borrador">Borrador</span>' : etiquetaPublicacion(sesion.publicada)}</div>
      <p>${escapar(formatFecha(sesion.fecha))} · ${escapar(sesion.inicio)}–${escapar(sesion.fin)}
        · Edificio ${escapar(sesion.edificio)} · Aula ${escapar(sesion.aula)}</p>
      ${profesor ? '' : `<p class="session-text">${escapar(sesion.descripcion)}</p>
        ${sesion.actividades ? `<details class="aula-plan"><summary>Ver plan de la sesión</summary>
          <p class="session-text">${escapar(sesion.actividades)}</p></details>` : ''}`}</div>
    ${profesor ? `<section class="panel aula-bloque aula-plan-docente">
      <h2>${iconoAula('lectura')} Plan de la sesión</h2>
      <p class="session-text"><strong>Objetivo</strong> · ${escapar(sesion.descripcion)}</p>
      ${sesion.actividades ? `<p class="session-text">${escapar(sesion.actividades)}</p>` : ''}
    </section>` : ''}
    <p class="aula-estado" data-trabajo-estado role="status"></p><div data-trabajo-contenido></div>
      ${profesor ? `<section class="panel aula-bloque aula-publicacion">
        <h2>${iconoAula('confirmado')} Publicación</h2>
        <p>${sesion.publicada ? 'Los estudiantes matriculados pueden abrir la sesión y ver el contenido publicado.'
          : 'Al publicar, los estudiantes matriculados podrán abrir la sesión. Los materiales y actividades en borrador seguirán siendo privados.'}</p>
        ${sesion.publicada ? '' : `${temaBorrador ? '<p>El tema de esta clase está en borrador. Puedes publicar ambos en un paso.</p>' : ''}
          <button type="button" class="aula-accion aula-accion-publicar" data-aula-publicar disabled>${iconoAula('confirmado')}
            ${temaBorrador ? 'Publicar tema y sesión' : 'Publicar sesión'}</button>`}
        <p class="micro">La sesión aparecerá en Mi horario en su fecha exacta. Los bloques semanales se configuran en el curso.</p>
        <p class="aviso-docente" role="status" data-publicacion-estado></p>
      </section>` : ''}
      <div data-aula-asistencia></div></div>
      <aside class="stack aula-lateral"><section class="panel"><h2>${iconoAula('agenda')} Agenda de la clase</h2><div data-aula-agenda></div></section>
        <section class="panel" data-aula-grupo hidden></section>
        ${profesor ? '' : `<section class="panel"><h2>${iconoAula('duda')} Mi duda</h2>
          <p>${escapar(tema)}</p>
          <button type="button" class="outline-btn" data-aula-grace>Explícame este tema</button>
          <div class="aula-orientacion" data-aula-explicacion role="status"></div>
        </section>`}</aside>
    </div>`;
  aula.querySelector('[data-aula-volver]').addEventListener('click', () => {
    cursoGestionActual = curso.id;
    renderizarCursosGrace();
    navegar('mis-clases', 'curso-gestion-sesiones');
  });
  aula.querySelector('[data-aula-grace]')?.addEventListener('click', e => {
    pedirOrientacionAula(e.currentTarget, aula.querySelector('[data-aula-explicacion]'),
      {curso_id: curso.id, sesion_id: sesion.id, tipo: 'explicar'});
  });
  function abrirHerramienta(tipo) {
    const destino = aula.querySelector(`[data-herramienta-material="${tipo}"]`);
    if (!destino) return;
    destino.open = true;
    destino.scrollIntoView({block:'center'});
    destino.querySelector('select, input')?.focus({preventScroll:true});
  }
  aula.addEventListener('click', evento => {
    const boton = evento.target.closest('[data-aula-herramienta]');
    if (boton) abrirHerramienta(boton.dataset.aulaHerramienta);
  });
  const publicar = aula.querySelector('[data-aula-publicar]');
  publicar?.addEventListener('click', async () => {
    const confirmacion = temaBorrador ? '¿Publicar el tema y esta sesión para tus estudiantes?'
      : '¿Publicar esta sesión para tus estudiantes?';
    if (!window.confirm(confirmacion)) return;
    publicar.disabled = true;
    try {
      await api('/api/cursos/sesiones/publicar', {curso_id:curso.id, id:sesion.id, publicar_tema:Boolean(temaBorrador)});
      await cargarCursosGrace();
      const actualizado = cursosGrace.find(c => c.id === curso.id);
      abrirAulaGrace(actualizado, actualizado.sesiones.find(s => s.id === sesion.id));
      mostrarToast('Sesión publicada.');
    } catch (error) {
      const estado = aula.querySelector('[data-publicacion-estado]');
      estado.classList.add('aviso-error');
      const generico = error.message === 'Entrada inválida. Revisa los campos y sus límites.';
      const salud = generico ? await api('/api/salud').catch(() => null) : null;
      estado.textContent = salud && !salud.publicacion_conjunta
        ? 'Grace sigue ejecutando una versión anterior. Usa Detener Grace, vuelve a abrirla y reintenta.'
        : 'No se pudo publicar la sesión. ' + error.message;
      publicar.disabled = false;
    }
  });
  if (typeof prepararAsistenciaSesiones === 'function') {
    prepararAsistenciaSesiones(aula.querySelector('[data-aula-asistencia]'), {...curso, sesiones:[sesion]});
  }
  const entrada = new Promise(resolver => navegar('aula-grace', 'aula-titulo', resolver));
  if (sesion.fecha === fechaLocal(new Date())) {
    entrada.then(() => iniciarLatidoPresencia(aula, curso.id, sesion.id));
  }
  Promise.all([entrada, cargarTrabajo(aula, curso.id, sesion.id)]).then(([, ok]) => {
    if (!ok || !aula.isConnected) return;
    if (publicar) publicar.disabled = false;
    if (!aula.classList.contains('active')) return;
    if (herramienta) abrirHerramienta(herramienta);
    const actividad = actividadId && $('actividad-' + actividadId);
    if (actividad) {
      const detalle = actividad.querySelector('[data-revision-docente], [data-detalle-actividad]');
      if (detalle) detalle.open = true;
      if (!profesor) abrirTabActividad(actividad, 'entrega');
      actividad.scrollIntoView({block:'start'});
      actividad.focus({preventScroll:true});
    }
  });
}

function iconoAula(tipo) {
  const trazos = {
    subir:'M12 16V4 M7 9l5-5 5 5 M4 16v4h16v-4',
    grace:'M12 2l2.5 7.5L22 12l-7.5 2.5L12 22l-2.5-7.5L2 12l7.5-2.5z',
    confirmado:'M4 12l5 5L20 6',
    agenda:'M5 4h14v16H5z M5 8h14 M9 2v4 M15 2v4 M8 12h8 M8 16h5',
    presentacion:'M3 4h18v12H3z M12 16v4 M8 20h8 M8 12l3-3 2 2 3-4',
    lectura:'M12 6c-3-2-6-2-9-1v14c3-1 6-1 9 1 3-2 6-2 9-1V5c-3-1-6-1-9 1v14',
    video:'M3 5h18v14H3z M10 9l5 3-5 3z',
    apoyo:'M9 13l6-6a3 3 0 014 4l-8 8a5 5 0 01-7-7l8-8',
    grupo:'M9 11a3 3 0 100-6 3 3 0 000 6z M3 19v-2a5 5 0 015-5h2a5 5 0 015 5v2 M16 5a3 3 0 010 6 M17 12a5 5 0 014 5v2',
    duda:'M4 5h16v11H9l-5 4z M9 9h6 M9 12h4',
    actividad:'M6 4h12v16H6z M9 4V2h6v2 M9 9h6 M9 13h6 M9 17h4',
  };
  return `<svg class="aula-icono" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor"
    stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="${trazos[tipo]}"/></svg>`;
}

function archivoTrabajo(archivo) {
  if (!archivo?.size || archivo.size > 3 * 1024 * 1024) {
    throw new Error('Selecciona un archivo de hasta 3 MB.');
  }
  return new Promise((resolve, reject) => {
    const lector = new FileReader();
    lector.onload = () => resolve({nombre: archivo.name, contenido: lector.result.split(',')[1]});
    lector.onerror = () => reject(new Error('No se pudo leer el archivo.'));
    lector.readAsDataURL(archivo);
  });
}

async function cargarTrabajo(panel, cursoId, sesionId) {
  const estado = panel.querySelector('[data-trabajo-estado]');
  estado.textContent = 'Cargando…';
  const consulta = new URLSearchParams({curso_id: cursoId, sesion_id: sesionId});
  try {
    const {registros} = await api(RUTA_TRABAJO + '?' + consulta);
    renderizarTrabajo(panel, registros, consulta);
    estado.textContent = '';
    return true;
  } catch (error) {
    estado.textContent = error.message;
    return false;
  }
}

function notaPublicada(entrega) {
  const nota = entrega.nota_publicada;
  return nota ? `<p><strong>Calificación publicada · ${escapar(nota.puntaje)}/100</strong></p>
    <p class="session-text">${escapar(nota.comentario)}</p>` : '';
}

function editorNota(entrega, criterios) {
  const borrador = entrega.nota_borrador;
  const nota = borrador || entrega.nota_publicada;
  const id = escapar(entrega.id);
  return `${notaPublicada(entrega)}
    <form class="form" data-tipo-trabajo="nota" data-entrega-id="${id}">
      <label>Puntaje sobre 100 <input type="number" name="puntaje" min="0" max="100" step="0.01" value="${escapar(nota?.puntaje ?? '')}" required></label>
      <label>Retroalimentación <textarea name="comentario" maxlength="1500">${escapar(nota?.comentario || '')}</textarea></label>
      <button class="outline-btn">Guardar borrador de nota</button>
    </form>
    ${borrador ? `<form class="form" data-tipo-trabajo="publicar_nota" data-entrega-id="${id}" data-revision="${escapar(borrador.revision)}">
      <p>Borrador guardado · ${escapar(borrador.puntaje)}/100</p><button class="primary-btn">Confirmar y publicar nota</button>
    </form>` : ''}
    ${criterios ? `<details><summary>Pedir propuesta a Grace</summary>
      <form class="form" data-tipo-trabajo="sugerir_nota" data-entrega-id="${id}">
        <label>Fragmento anónimo de la entrega <textarea name="fragmento" maxlength="3000" required></textarea></label>
        <label><input type="checkbox" name="autoriza_envio" required> Autorizo enviar solo el fragmento y los criterios al proveedor configurado. Quité los datos personales.</label>
        <button class="outline-btn">Sugerir nota y comentario</button>
      </form></details>` : ''}`;
}

function gruposTrabajo(actividad, profesor, yaEntrego) {
  if (!actividad.grupos) return '';
  const grupos = actividad.grupos.map((grupo, i) => ({
    numero: i + 1, miembros: profesor ? grupo.length : grupo,
  }));
  if (profesor) return `<ul>${grupos.map(g => `<li>Grupo ${g.numero} · ${g.miembros}/${actividad.cupo}</li>`).join('')}</ul>`;
  const actual = actividad.mi_grupo;
  if (yaEntrego) return `<p>Tu grupo · Grupo ${escapar(actual)}</p>`;
  return `<form class="form" data-tipo-trabajo="grupo" data-actividad-id="${escapar(actividad.id)}">
    <label>Elige tu grupo <select name="grupo" required><option value="">Selecciona un grupo</option>
    ${grupos.map(g => `<option value="${g.numero}" ${actual === g.numero ? 'selected' : ''} ${g.miembros >= actividad.cupo && actual !== g.numero ? 'disabled' : ''}>
      Grupo ${g.numero} · ${g.miembros}/${actividad.cupo}</option>`).join('')}</select></label>
    <button class="outline-btn">Guardar grupo</button></form>`;
}

function opcionesMaterial(opciones) {
  return Object.entries(opciones).map(([id, nombre]) => `<option value="${id}">${nombre}</option>`).join('');
}

function categoriaMaterial(recurso) {
  if (recurso.categoria) return recurso.categoria;
  const extension = recurso.nombre?.split('.').pop().toLowerCase();
  if (extension === 'pptx') return 'presentacion';
  if (['docx','pdf','txt'].includes(extension)) return 'lectura';
  if (extension === 'mp4') return 'video';
  return 'apoyo';
}

function panelMateriales(panel, recursos, actividades, consulta, profesor) {
  const host = panel.querySelector('[data-aula-materiales]');
  const agenda = panel.querySelector('[data-aula-agenda]');
  host.innerHTML = `<div class="aula-pestanas" role="group" aria-label="Tipo de material">
    ${Object.entries(CATEGORIAS_MATERIAL).map(([id, nombre]) =>
      `<button type="button" class="outline-btn" data-material-tab="${id}" aria-pressed="false">${iconoAula(id)} ${nombre}</button>`).join('')}
    </div>${Object.keys(CATEGORIAS_MATERIAL).map(categoria => {
      const lista = recursos.filter(r => categoriaMaterial(r) === categoria);
      return `<div class="stack" data-material-lista="${categoria}" hidden>
        ${lista.map(r => tarjetaMaterial(r, consulta, profesor)).join('') ||
          '<p>Aún no hay material de este tipo.</p>'}</div>`;
    }).join('')}`;
  function activar(categoria) {
    host.querySelectorAll('[data-material-tab]').forEach(b =>
      b.setAttribute('aria-pressed', String(b.dataset.materialTab === categoria)));
    host.querySelectorAll('[data-material-lista]').forEach(p => {p.hidden = p.dataset.materialLista !== categoria;});
    panel.dataset.materialActivo = categoria;
  }
  host.querySelectorAll('[data-material-tab]').forEach(b => b.addEventListener('click', () => activar(b.dataset.materialTab)));
  const categorias = recursos.map(categoriaMaterial);
  activar(panel.dataset.materialActivo || (categorias.includes('presentacion') ? 'presentacion' : categorias[0]) || 'presentacion');
  const pasos = [...recursos, ...actividades];
  function abrirPaso(paso) {
    if (paso.tipo === 'recurso') activar(categoriaMaterial(paso));
    const tarjeta = $( (paso.tipo === 'recurso' ? 'material-' : 'actividad-') + paso.id);
    const detalle = tarjeta?.querySelector('[data-detalle-actividad]');
    if (detalle) detalle.open = true;
    tarjeta?.scrollIntoView({block:'center'});
    tarjeta?.focus({preventScroll:true});
  }
  if (agenda) montarAgenda(agenda, pasos.filter(p => p.publicada !== false), consulta, abrirPaso);
  host.querySelectorAll('[data-diapos]').forEach(visor => {
    let indice = 0;
    const diapositivas = [...visor.querySelectorAll('[data-diapo]')];
    const anterior = visor.querySelector('[data-diapo-anterior]');
    const siguiente = visor.querySelector('[data-diapo-siguiente]');
    function actualizar() {
      diapositivas.forEach((d, i) => {d.hidden = i !== indice;});
      anterior.disabled = indice === 0;
      siguiente.disabled = indice === diapositivas.length - 1;
      visor.querySelector('[data-diapo-cuenta]').textContent = (indice + 1) + ' de ' + diapositivas.length;
      visor.querySelectorAll('[data-ir-diapo]').forEach(b => {
        b.setAttribute('aria-current', String(Number(b.dataset.irDiapo) === indice));
      });
    }
    anterior.addEventListener('click', () => {indice--; actualizar();});
    siguiente.addEventListener('click', () => {indice++; actualizar();});
    visor.querySelectorAll('[data-ir-diapo]').forEach(b => b.addEventListener('click', () => {
      indice = Number(b.dataset.irDiapo);
      actualizar();
    }));
    visor.querySelector('[data-diapo-ampliar]')?.addEventListener('click', () => {
      if (document.fullscreenElement) document.exitFullscreen();
      else visor.requestFullscreen?.().catch(() => {});
    });
    actualizar();
  });
}

function montarAgenda(agenda, pasos, consulta, abrirPaso) {
  const clave = 'grace-agenda:' + cuentaActual.id + ':' + consulta;
  let revisados;
  try {
    revisados = new Set(JSON.parse(sessionStorage.getItem(clave) || '[]'));
  } catch {
    revisados = new Set();
  }
  const porMomento = paso => paso.momento || 'durante';
  const ordenados = Object.keys(MOMENTOS_MATERIAL).flatMap(m => pasos.filter(p => porMomento(p) === m));
  let activo = ordenados.find(p => !revisados.has(p.id))?.id;
  let abierto;
  function pintar() {
    const total = ordenados.length;
    const cuenta = ordenados.filter(p => revisados.has(p.id)).length;
    const resumen = agenda.closest('#aula-grace').querySelector('[data-cierre-agenda]');
    if (resumen) resumen.textContent = total ? `${cuenta} de ${total} pasos revisados en este navegador.`
      : 'Todavía no hay pasos publicados en la agenda.';
    agenda.innerHTML = `<div class="aula-agenda-progreso"><p>${cuenta} de ${total} pasos revisados</p>
      <progress aria-label="Pasos revisados" value="${cuenta}" max="${total || 1}"></progress></div>
      ${Object.entries(MOMENTOS_MATERIAL).map(([id, nombre]) => {
        const lista = ordenados.filter(p => porMomento(p) === id);
        return `<h3>${nombre}</h3>${lista.map(p => `<button type="button" class="aula-paso" data-agenda-id="${escapar(p.id)}"
          aria-current="${p.id === activo ? 'step' : 'false'}"><span aria-hidden="true">${revisados.has(p.id) ? '✓' : '○'}</span>${escapar(p.tipo === 'actividad' ? 'Actividad' : CATEGORIAS_MATERIAL[categoriaMaterial(p)])} · ${escapar(p.titulo)}</button>`).join('')
          || '<p class="micro">Sin pasos registrados.</p>'}`;
      }).join('')}
      <button type="button" class="primary-btn aula-continuar" data-agenda-continuar ${activo ? '' : 'disabled'}>${activo ? (abierto === activo ? 'Marcar y continuar →' : 'Continuar →') : total ? 'Agenda revisada' : 'Sin pasos registrados'}</button>`;
    agenda.querySelectorAll('[data-agenda-id]').forEach(b => b.addEventListener('click', () => {
      activo = b.dataset.agendaId;
      abierto = activo;
      pintar();
      abrirPaso(ordenados.find(p => p.id === activo));
    }));
    agenda.querySelector('[data-agenda-continuar]').addEventListener('click', () => {
      if (abierto !== activo) {
        abierto = activo;
        pintar();
        abrirPaso(ordenados.find(p => p.id === activo));
        return;
      }
      revisados.add(activo);
      sessionStorage.setItem(clave, JSON.stringify([...revisados]));
      const siguiente = ordenados.find(p => !revisados.has(p.id));
      activo = siguiente?.id;
      abierto = activo;
      pintar();
      if (siguiente) abrirPaso(siguiente);
    });
  }
  pintar();
}

function tarjetaMaterial(recurso, consulta, profesor) {
  const id = escapar(recurso.id);
  const categoria = categoriaMaterial(recurso);
  const archivo = escapar(RUTA_TRABAJO + '/archivo?' + consulta + '&id=' + encodeURIComponent(recurso.id));
  const diapositivas = categoria === 'presentacion' && recurso.secciones
    ? [{titulo:recurso.titulo, puntos:['Material de clase']}, ...recurso.secciones] : null;
  const seccion = s => {
    const diagrama = /^diagrama:/i.test(s.titulo) && s.puntos.length >= 2 && s.puntos.length <= 4;
    return `<h4>${escapar(s.titulo)}</h4><ul${diagrama ? ' class="aula-diagrama"' : ''}>
      ${s.puntos.map(p => '<li>' + escapar(p) + '</li>').join('')}</ul>`;
  };
  return `<article class="panel aula-material" id="material-${id}" tabindex="-1">
    <div class="aula-material-cabecera"><h3>${iconoAula(categoria)} ${escapar(recurso.titulo)}</h3>
    ${recurso.enlace ? `<a href="${escapar(recurso.enlace)}" target="_blank" rel="noopener noreferrer">Abrir enlace externo</a>`
      : `<a class="aula-enlace" href="${archivo}">Descargar ${escapar(recurso.nombre)}</a>`}</div>
    ${profesor ? `<p class="micro">${MOMENTOS_MATERIAL[recurso.momento || 'durante']}${recurso.origen ? ' · ' + escapar(recurso.origen) : ''}</p>` : ''}
    ${recurso.publicada === false ? '<span class="tag estado-borrador">Borrador privado</span>' : ''}
    ${recurso.nombre?.toLowerCase().endsWith('.mp4') ? `<video class="aula-video" controls preload="none" src="${archivo}&amp;reproducir=1"></video>` : ''}
    ${diapositivas ? `<div class="aula-visor" data-diapos>${diapositivas.map((s, i) =>
      `<div class="aula-diapo ${i === 0 ? 'aula-diapo-portada' : ''}" data-diapo hidden>
        <p class="aula-material-marca">GRACE / MATERIAL DE CLASE</p>
        ${i === 0 ? `<h4>${escapar(s.titulo)}</h4><p>${diapositivas.length - 1} secciones de estudio</p>`
          : seccion(s)}<p class="aula-material-folio">${i + 1} / ${diapositivas.length}</p></div>`).join('')}
      <div class="aula-visor-controles"><button class="outline-btn" type="button" data-diapo-anterior>Anterior</button>
        <span data-diapo-cuenta aria-live="polite"></span><button class="outline-btn" type="button" data-diapo-siguiente>Siguiente</button>
        <button class="text-btn" type="button" data-diapo-ampliar>Ampliar / salir</button></div>
      <details><summary>Ver miniaturas</summary><div class="aula-miniaturas">
        ${diapositivas.map((s,i) => `<button type="button" class="outline-btn" data-ir-diapo="${i}">${i+1} · ${escapar(s.titulo)}</button>`).join('')}
      </div></details></div>`
      : recurso.secciones ? `<div class="aula-lectura"><p class="aula-material-marca">GRACE / MATERIAL ACADÉMICO</p>
        ${recurso.secciones.map((s, i) => `<section><h4>${String(i + 1).padStart(2, '0')} · ${escapar(s.titulo)}</h4>
          ${s.puntos.map(p => '<p>' + escapar(p) + '</p>').join('')}</section>`).join('')}</div>` : ''}
    ${profesor ? `<form data-tipo-trabajo="${recurso.publicada === false ? 'publicar_material' : 'ocultar_material'}" data-material-id="${id}">
      <button class="outline-btn">${recurso.publicada === false ? 'Publicar en la sesión' : 'Ocultar material'}</button></form>` : ''}</article>`;
}

function camposActividad(actividad = {}) {
  return `<label>Título de la actividad <input name="titulo" maxlength="120" required value="${escapar(actividad.titulo || '')}"></label>
    <label>Instrucciones <textarea name="instrucciones" maxlength="2000" required>${escapar(actividad.instrucciones || '')}</textarea></label>
    <label>Criterios de calificación <textarea name="criterios" maxlength="2000">${escapar(actividad.criterios || '')}</textarea></label>
    <label>Momento <select name="momento">${Object.entries(MOMENTOS_MATERIAL).map(([id, nombre]) =>
      `<option value="${id}" ${id === (actividad.momento || 'durante') ? 'selected' : ''}>${nombre}</option>`).join('')}</select></label>
    <label>Fecha y hora límite (opcional) <input name="vence" type="datetime-local" value="${escapar(actividad.vence || '')}"></label>`;
}

function tarjetaActividad(actividad, asociadas, descarga, profesor, campoArchivo) {
  const a = actividad;
  const id = escapar(a.id);
  const entrega = asociadas[0];
  const vence = a.vence ? formatFecha(a.vence.slice(0,10)) + ' · ' + a.vence.slice(11) : '';
  const borrador = a.publicada === false;
  const instrucciones = a.instrucciones.split('\n').filter(linea => linea.trim());
  const cabecera = `<header class="aula-actividad-cabecera">
    <h3>${iconoAula('actividad')} Actividad · ${escapar(a.titulo)}</h3>
    <span class="tag">${a.grupos ? 'Trabajo en equipo' : 'Trabajo individual'}</span>
    ${borrador ? '<span class="tag estado-borrador">Borrador privado</span>' : ''}</header>`;
  const contenidoProfesor = `
    <p class="session-text">${escapar(a.instrucciones)}</p>
    ${vence ? `<p>Entrega · ${escapar(vence)}</p>` : ''}
    ${gruposTrabajo(a, true, false)}
    ${borrador ? `<details><summary>Editar borrador</summary>
      <form class="form" data-tipo-trabajo="editar_actividad" data-actividad-id="${id}">
        ${camposActividad(a)}<button class="outline-btn">Guardar cambios del borrador</button>
      </form></details><form data-tipo-trabajo="publicar_actividad" data-actividad-id="${id}">
      <button class="primary-btn">Publicar actividad</button></form>`
      : `<details data-revision-docente><summary>Revisión docente · ${asociadas.length} entregas</summary>
      <form class="form" data-tipo-trabajo="criterios" data-actividad-id="${id}">
        <label>Criterios de calificación <textarea name="criterios" maxlength="2000">${escapar(a.criterios || '')}</textarea></label>
        <button class="outline-btn">Guardar criterios</button></form>
      <ul class="stack">${asociadas.map(e => `<li>${e.grupo ? 'Grupo ' + escapar(e.grupo) + ' · ' : ''}
        ${escapar(e.estudiante_nombre)} · ${descarga(e)} · ${escapar(new Date(e.fecha).toLocaleString('es'))}
        ${editorNota(e, a.criterios)}</li>`).join('')}</ul></details>`}`;
  const tabs = [['instrucciones','Instrucciones'],['criterios','Criterios'],['entrega','Mi entrega']];
  if (a.mi_grupo) tabs.push(['grupo', 'Conversación del grupo']);
  const contenidoEstudiante = `<div class="aula-actividad-tabs" role="group" aria-label="Secciones de la actividad">
    ${tabs.map(([clave,nombre]) => `<button type="button" class="text-btn" data-actividad-tab="${clave}"
      aria-pressed="${clave === 'instrucciones'}">${nombre}</button>`).join('')}</div>
    <div class="aula-actividad-cuerpo" data-actividad-panel="instrucciones">
      <ol>${instrucciones.map(linea => '<li>' + escapar(linea) + '</li>').join('')}</ol>
      <button type="button" class="outline-btn" data-actividad-pista>Pedir una pista</button>
      <div class="aula-orientacion" data-actividad-orientacion role="status"></div></div>
    <div class="aula-actividad-cuerpo" data-actividad-panel="criterios" hidden>
      <p class="session-text">${escapar(a.criterios || 'El profesor aún no ha indicado criterios.')}</p></div>
    <div class="aula-actividad-cuerpo" data-actividad-panel="entrega" hidden>
      ${gruposTrabajo(a, false, Boolean(entrega))}
        ${entrega ? '<p>Archivo entregado · ' + descarga(entrega) + '</p>' + notaPublicada(entrega) : '<p>Entrega pendiente.</p>'}
        ${(!a.grupos || a.mi_grupo) && !entrega?.nota_publicada ? `<form class="form" data-tipo-trabajo="entrega" data-actividad-id="${id}">${campoArchivo}
          <button class="primary-btn">${entrega ? 'Reemplazar entrega' : 'Entregar archivo'}</button></form>` : ''}</div>
    ${a.mi_grupo ? `<section class="aula-actividad-cuerpo" data-actividad-panel="grupo" hidden>
      <h4>Conversación privada · Grupo ${escapar(a.mi_grupo)}</h4>
      <p class="micro">Solo tus compañeros del equipo pueden participar. Se muestran hasta 50 mensajes.</p>
      <p data-grupo-estado role="status"></p><div data-grupo-mensajes class="stack grupo-mensajes"></div>
      <button type="button" class="outline-btn" data-grupo-actualizar>Actualizar mensajes</button>
      <form class="form" data-grupo-chat><label>Mensaje <textarea name="texto" maxlength="800" rows="2" required></textarea></label>
        <button type="submit" class="primary-btn">Enviar al grupo</button></form>
    </section>` : ''}
    <footer class="aula-actividad-pie">
      <span>${a.grupos ? (a.mi_grupo ? 'Grupo ' + escapar(a.mi_grupo) + ' · ' + a.grupos[a.mi_grupo - 1] + ' de ' + a.cupo : 'Grupo por elegir') : 'Entrega individual'}</span>
      ${vence ? `<span>${iconoAula('agenda')} ${escapar(vence)}</span>` : ''}
      <button class="primary-btn" type="button" data-actividad-ver-entrega>${a.grupos && !a.mi_grupo ? 'Elegir grupo' : entrega ? 'Ver mi entrega' : 'Adjuntar entrega'}</button>
    </footer>`;
  return `<article class="panel aula-actividad" id="actividad-${id}" tabindex="-1">
    ${cabecera}${profesor ? contenidoProfesor : `<details data-detalle-actividad open>
      <summary>Detalles de la actividad</summary>${contenidoEstudiante}</details>`}</article>`;
}

function abrirTabActividad(tarjeta, tab) {
  tarjeta.querySelectorAll('[data-actividad-tab]').forEach(b =>
    b.setAttribute('aria-pressed', String(b.dataset.actividadTab === tab)));
  tarjeta.querySelectorAll('[data-actividad-panel]').forEach(p => {p.hidden = p.dataset.actividadPanel !== tab;});
}

async function pedirOrientacionAula(boton, destino, datos) {
  if (!asistenteActivado) {
    destino.textContent = 'Activa el asistente para recibir orientación.';
    return false;
  }
  boton.disabled = true;
  destino.textContent = 'Preparando orientación…';
  try {
    const {respuesta, origen} = await api(RUTA_TRABAJO + '/orientar', datos);
    destino.textContent = respuesta;
    const fuente = document.createElement('p');
    fuente.className = 'response-source';
    fuente.textContent = 'Fuente: ' + origen;
    destino.append(fuente);
    return true;
  } catch (error) {
    destino.textContent = error.message;
    return false;
  } finally {
    boton.disabled = false;
  }
}

function prepararConversacionGrupo(tarjeta, consulta) {
  const panel = tarjeta.querySelector('[data-actividad-panel="grupo"]');
  if (!panel) return;
  const ruta = RUTA_TRABAJO + '/grupo/chat';
  const contexto = {...Object.fromEntries(consulta), actividad_id: tarjeta.id.slice('actividad-'.length)};
  const estado = panel.querySelector('[data-grupo-estado]');
  const lista = panel.querySelector('[data-grupo-mensajes]');
  const form = panel.querySelector('[data-grupo-chat]');
  const actualizar = panel.querySelector('[data-grupo-actualizar]');
  const enviar = form.querySelector('button');
  let ocupado = false;
  async function cargar(texto) {
    if (ocupado) return;
    ocupado = actualizar.disabled = enviar.disabled = true;
    estado.textContent = texto === undefined ? 'Cargando mensajes…' : 'Enviando…';
    try {
      const {mensajes} = texto === undefined ? await api(ruta + '?' + new URLSearchParams(contexto))
        : await api(ruta, {...contexto, texto});
      lista.innerHTML = mensajes.map(m => `<article class="aula-pregunta"><strong>${escapar(m.autor)}</strong>
        <small> · ${escapar(new Date(m.fecha).toLocaleString('es'))}</small>
        <p class="session-text">${escapar(m.texto)}</p></article>`).join('') || '<p>Aún no hay mensajes.</p>';
      if (texto !== undefined) form.reset();
      estado.textContent = texto === undefined ? '' : 'Mensaje enviado.';
    } catch (error) {
      if (texto === undefined) lista.replaceChildren();
      estado.textContent = error.message;
    } finally {
      ocupado = actualizar.disabled = enviar.disabled = false;
    }
  }
  actualizar.addEventListener('click', () => cargar());
  tarjeta.querySelector('[data-actividad-tab="grupo"]').addEventListener('click', () => cargar());
  form.addEventListener('submit', evento => {
    evento.preventDefault();
    cargar(new FormData(form).get('texto'));
  });
}

function montarActividades(panel, actividades, profesor, consulta) {
  panel.querySelectorAll('.aula-actividad').forEach(tarjeta => {
    prepararConversacionGrupo(tarjeta, consulta);
    if (tarjeta.id === panel.dataset.revisionActividad) tarjeta.querySelector('[data-revision-docente]').open = true;
    if (tarjeta.id === 'actividad-' + panel.dataset.actividadEntrega) abrirTabActividad(tarjeta, 'entrega');
    tarjeta.querySelectorAll('[data-actividad-tab]').forEach(b => b.addEventListener('click', () => abrirTabActividad(tarjeta, b.dataset.actividadTab)));
    const pista = tarjeta.querySelector('[data-actividad-pista]');
    let nivel = 1;
    pista?.addEventListener('click', async () => {
      const ok = await pedirOrientacionAula(pista, tarjeta.querySelector('[data-actividad-orientacion]'),
        {...Object.fromEntries(consulta), tipo:'pista', nivel, actividad_id: tarjeta.id.slice('actividad-'.length)});
      if (ok && nivel < 3) {
        nivel++;
        pista.textContent = 'Pedir otra pista';
      }
    });
    tarjeta.querySelector('[data-actividad-ver-entrega]')?.addEventListener('click', () => {
      abrirTabActividad(tarjeta, 'entrega');
      tarjeta.querySelector('[data-actividad-panel="entrega"] input, [data-actividad-panel="entrega"] select')?.focus();
    });
  });
  const grupo = panel.querySelector('[data-aula-grupo]');
  if (!grupo || profesor) return;
  const tarea = actividades.find(a => a.mi_grupo) || actividades.find(a => a.grupos);
  grupo.hidden = !tarea;
  if (!tarea) return;
  grupo.innerHTML = `<h2>${iconoAula('grupo')} Tu grupo</h2><p>${escapar(tarea.titulo)}</p>
    <p><strong>${tarea.mi_grupo ? 'Grupo ' + escapar(tarea.mi_grupo) : 'Aún no has elegido grupo'}</strong>
      ${tarea.mi_grupo ? ' · ' + tarea.grupos[tarea.mi_grupo - 1] + ' de ' + tarea.cupo + ' integrantes' : ''}</p>
    <button class="outline-btn" type="button">${tarea.mi_grupo ? 'Abrir conversación del grupo' : 'Elegir grupo'}</button>`;
  grupo.querySelector('button').addEventListener('click', () => {
    const tarjeta = $('actividad-' + tarea.id);
    tarjeta.querySelector('[data-detalle-actividad]').open = true;
    if (tarea.mi_grupo) tarjeta.querySelector('[data-actividad-tab="grupo"]').click();
    else abrirTabActividad(tarjeta, 'entrega');
    tarjeta.scrollIntoView({block:'center'});
    tarjeta.focus({preventScroll:true});
  });
}

function preguntasDeClase(preguntas, profesor) {
  return `<section class="panel aula-bloque" aria-label="Preguntas de esta clase">
    <h2>${iconoAula('duda')} Preguntas de esta clase</h2>
    <p class="micro">${profesor ? 'Cada respuesta es visible para el estudiante que hizo la pregunta.'
      : 'Tus preguntas y respuestas son privadas entre tú y el profesor del curso.'}</p>
    <div class="stack">${preguntas.map(p => `<article class="aula-pregunta">
      <h3>${profesor ? escapar(p.estudiante_nombre) : 'Tu pregunta'}</h3><p class="session-text">${escapar(p.texto)}</p>
      ${p.respuesta ? `<p class="session-text"><strong>Respuesta del profesor</strong><br>${escapar(p.respuesta)}</p>`
        : '<p class="micro">Pendiente de respuesta.</p>'}
      ${profesor ? `<form class="form" data-tipo-trabajo="responder_pregunta" data-pregunta-id="${escapar(p.id)}">
        <label>Respuesta <textarea name="texto" required maxlength="1500" rows="2">${escapar(p.respuesta || '')}</textarea></label>
        <button class="outline-btn">${p.respuesta ? 'Actualizar respuesta' : 'Responder'}</button></form>` : ''}</article>`).join('')
      || '<p>Aún no hay preguntas.</p>'}</div>
    ${profesor ? '' : `<form class="form" data-tipo-trabajo="pregunta">
      <label>Pregunta para el profesor <textarea name="texto" required maxlength="1500" rows="2"></textarea></label>
      <button class="outline-btn">Enviar pregunta</button></form>`}</section>`;
}

function cierreDeClase(actividades, entregas) {
  const entregadas = new Set(entregas.map(e => e.actividad_id));
  return `<section class="panel aula-bloque aula-cierre"><h2>${iconoAula('confirmado')} Cierre de la sesión</h2>
    <p data-cierre-agenda aria-live="polite"></p>
    ${actividades.length ? `<ul>${actividades.map(a => `<li><strong>${escapar(a.titulo)}</strong>
      <span class="tag ${entregadas.has(a.id) ? 'estado-confirmado' : 'estado-pendiente'}">
        ${entregadas.has(a.id) ? '✓ Entregada' : '◷ Pendiente'}</span></li>`).join('')}</ul>`
      : '<p>Esta sesión no tiene actividades con entrega.</p>'}</section>`;
}

function renderizarTrabajo(panel, registros, consulta) {
  const profesor = rolActual === 'profesor';
  const contenido = panel.querySelector('[data-trabajo-contenido]');
  const descarga = (r, texto = r.nombre) =>
    `<a href="${escapar(RUTA_TRABAJO + '/archivo?' + consulta + '&id=' + encodeURIComponent(r.id))}">${escapar(texto)}</a>`;
  const recursos = registros.filter(r => r.tipo === 'recurso');
  const actividades = registros.filter(r => r.tipo === 'actividad');
  const entregas = registros.filter(r => r.tipo === 'entrega');
  const campoArchivo = `<label>Archivo <input type="file" name="archivo" accept="${FORMATOS_TRABAJO}"></label>`;
  contenido.innerHTML = `<div class="stack">
    ${profesor ? `<section class="panel aula-bloque aula-materiales-docente">
      <h2>${iconoAula('apoyo')} Materiales</h2>
      <div class="aula-acciones">
        <button type="button" class="aula-accion aula-accion-material" data-aula-herramienta="subir">${iconoAula('subir')} Subir material</button>
        <button type="button" class="aula-accion aula-accion-grace" data-aula-herramienta="generar">${iconoAula('grace')} Crear con Grace</button>
      </div>
    </section>` : ''}
    <div data-aula-materiales></div>
    ${profesor ? `<details class="panel" data-herramienta-material="subir"><summary>Subir material o agregar enlace</summary>
      <form class="form" data-tipo-trabajo="recurso"><label>Título del recurso <input name="titulo" maxlength="120" required></label>
      <label>Tipo <select name="categoria">${opcionesMaterial(CATEGORIAS_MATERIAL)}</select></label>
      <label>Momento <select name="momento">${opcionesMaterial(MOMENTOS_MATERIAL)}</select></label>
      <label>Enlace HTTPS <input name="enlace" type="url" maxlength="1500"></label>
      <label>Archivo <input type="file" name="archivo" accept="${FORMATOS_TRABAJO},.mp4"></label>
      <label><input type="checkbox" name="borrador" checked> Guardar como borrador</label>
      <p class="micro">Pega un enlace completo que empiece por https:// o selecciona un archivo de hasta 3 MB.
        «Antes», «Durante» y «Después» ordenan la agenda. Tú decides cuándo publicar.</p>
      <button class="outline-btn">Agregar material</button></form></details>
      <details class="panel" data-herramienta-material="generar"><summary>Crear materiales y actividades con Grace</summary><form class="form" data-tipo-trabajo="generar_material">
      <label>Formato <select name="formato"><option value="pptx">PowerPoint (.pptx)</option><option value="docx">Word (.docx)</option>
        <option value="guion">Guion de video (.docx)</option><option value="actividad">Actividad con instrucciones y criterios</option></select></label>
      <label>Momento <select name="momento">${opcionesMaterial(MOMENTOS_MATERIAL)}</select></label>
      <label>Objetivo o indicaciones <textarea name="objetivo" maxlength="1200"></textarea></label>
      <p class="micro">Grace usa el tema de la sesión y estas indicaciones. Revisa el borrador antes de publicarlo.</p>
      <button class="primary-btn">Generar borrador</button></form></details>` : ''}
    ${profesor ? `<section class="panel aula-bloque aula-actividades-docente">
      <h2>${iconoAula('actividad')} Actividades y entregas</h2>
      <button type="button" class="aula-accion aula-accion-actividad" data-aula-herramienta="actividad">${iconoAula('actividad')} Agregar actividad</button>
    </section>` : ''}
    ${actividades.map(a => tarjetaActividad(a, entregas.filter(e => e.actividad_id === a.id), descarga, profesor, campoArchivo)).join('')
      || '<article class="panel"><h3>Actividad de la sesión</h3><p>Aún no hay actividades con entrega.</p></article>'}
    ${profesor ? `<details class="panel" data-herramienta-material="actividad"><summary>Agregar actividad con entrega</summary>
      <form class="form" data-tipo-trabajo="actividad">${camposActividad()}
      <label>Cantidad de grupos (0 para entrega individual) <input name="cantidad" type="number" min="0" max="30" value="0" required></label>
      <label>Cupo por grupo <input name="cupo" type="number" min="1" max="12" value="4" required></label>
      <button class="primary-btn">Guardar actividad como borrador</button></form></details>` : ''}
    ${panel.dataset.sesionPublicada === 'true' ? preguntasDeClase(registros.filter(r => r.tipo === 'pregunta'), profesor) : ''}
    ${profesor ? '' : cierreDeClase(actividades, entregas)}</div>`;
  panelMateriales(panel, recursos, actividades, consulta, profesor);
  montarActividades(panel, actividades, profesor, consulta);
  contenido.querySelectorAll('form[data-tipo-trabajo]').forEach(form => form.addEventListener('submit', async e => {
    e.preventDefault();
    const estado = panel.querySelector('[data-trabajo-estado]');
    const boton = form.querySelector('button');
    let errorLocal = form.querySelector('.aviso-error');
    errorLocal?.remove();
    boton.disabled = true;
    estado.textContent = 'Guardando…';
    try {
      const tipo = form.dataset.tipoTrabajo;
      const valores = new FormData(form);
      const datos = {...Object.fromEntries(consulta), tipo};
      if (tipo === 'pregunta' || tipo === 'responder_pregunta') datos.texto = valores.get('texto');
      if (tipo === 'responder_pregunta') datos.pregunta_id = form.dataset.preguntaId;
      if (tipo === 'generar_material') {
        if (!asistenteActivado) throw new Error('Activa el asistente para generar material.');
        estado.textContent = 'Generando material… Puede tardar hasta 90 segundos.';
        boton.textContent = 'Generando material…';
        for (const campo of ['formato','momento','objetivo']) datos[campo] = valores.get(campo);
        if (datos.formato === 'actividad') {
          estado.textContent = 'Generando actividad…';
          boton.textContent = 'Generando actividad…';
          const propuesta = await api(RUTA_TRABAJO, datos);
          const editor = panel.querySelector('[data-herramienta-material="actividad"]');
          editor.open = true;
          const campos = editor.querySelector('form').elements;
          for (const campo of ['titulo','instrucciones','criterios']) campos[campo].value = propuesta[campo];
          estado.textContent = 'Propuesta de ' + propuesta.origen + '. Revisa la actividad y guárdala como borrador.';
          editor.scrollIntoView({block:'center'});
          campos.titulo.focus({preventScroll:true});
          return;
        }
      }
      if (tipo === 'publicar_material' || tipo === 'ocultar_material') datos.material_id = form.dataset.materialId;
      if (tipo === 'recurso') {
        datos.categoria = valores.get('categoria');
        datos.momento = valores.get('momento');
        datos.borrador = valores.has('borrador');
      }
      if (['actividad','editar_actividad','recurso'].includes(tipo)) datos.titulo = valores.get('titulo');
      if (tipo === 'actividad' || tipo === 'editar_actividad') {
        datos.instrucciones = valores.get('instrucciones');
        datos.vence = valores.get('vence');
        datos.momento = valores.get('momento');
      }
      if (tipo === 'actividad') {
        datos.borrador = true;
        datos.cantidad = Number(valores.get('cantidad'));
        datos.cupo = datos.cantidad ? Number(valores.get('cupo')) : 0;
      }
      if (['actividad','editar_actividad','criterios'].includes(tipo)) datos.criterios = valores.get('criterios');
      if (tipo === 'recurso') {
        const enlace = valores.get('enlace').trim();
        const archivo = valores.get('archivo');
        if (enlace && archivo?.size) throw new Error('Quita el archivo para guardar el enlace, o borra el enlace para subir el archivo.');
        if (!enlace && !archivo?.size) throw new Error('Pega un enlace HTTPS o selecciona un archivo.');
        if (enlace) datos.enlace = enlace;
        else Object.assign(datos, await archivoTrabajo(archivo));
      }
      if (tipo === 'entrega') Object.assign(datos, await archivoTrabajo(valores.get('archivo')));
      if (form.dataset.actividadId) datos.actividad_id = form.dataset.actividadId;
      if (form.dataset.entregaId) datos.entrega_id = form.dataset.entregaId;
      if (tipo === 'grupo') datos.grupo = Number(valores.get('grupo'));
      if (tipo === 'nota') {
        datos.puntaje = Number(valores.get('puntaje'));
        datos.comentario = valores.get('comentario');
      }
      if (tipo === 'publicar_nota') datos.revision = form.dataset.revision;
      if (tipo === 'sugerir_nota') {
        datos.fragmento = valores.get('fragmento');
        datos.autoriza_envio = valores.has('autoriza_envio');
        const propuesta = await api(RUTA_TRABAJO, datos);
        const editor = form.closest('li').querySelector('[data-tipo-trabajo="nota"]');
        if (propuesta.puntaje !== null) editor.elements.puntaje.value = propuesta.puntaje;
        editor.elements.comentario.value = propuesta.comentario;
        estado.textContent = 'Propuesta de ' + propuesta.origen + '. Revisa y guarda el borrador si corresponde.';
        editor.elements.puntaje.focus();
        return;
      }
      await api(RUTA_TRABAJO, datos);
      if (tipo === 'nota' || tipo === 'publicar_nota' || tipo === 'criterios') {
        panel.dataset.revisionActividad = form.closest('.aula-actividad').id;
      }
      if (tipo === 'grupo' || tipo === 'entrega') panel.dataset.actividadEntrega = datos.actividad_id;
      if (tipo === 'recurso') panel.dataset.materialActivo = datos.categoria;
      if (tipo === 'generar_material') panel.dataset.materialActivo = datos.formato === 'pptx' ? 'presentacion' : 'lectura';
      if (await cargarTrabajo(panel, consulta.get('curso_id'), consulta.get('sesion_id'))) {
        estado.textContent = tipo === 'generar_material' ? 'Borrador generado. Revisa el material antes de publicarlo.'
          : tipo === 'recurso' ? (datos.borrador ? 'Material guardado como borrador. Puedes publicarlo desde su tarjeta.'
            : 'Material guardado y publicado.')
          : tipo === 'publicar_material' ? 'Material publicado en la sesión.'
          : tipo === 'publicar_actividad' ? 'Actividad publicada.'
          : tipo === 'actividad' ? 'Actividad guardada como borrador.'
          : tipo === 'entrega' ? 'Entrega registrada.'
          : tipo === 'grupo' ? 'Grupo guardado.'
          : tipo === 'publicar_nota' ? 'Nota publicada.'
          : tipo === 'pregunta' ? 'Pregunta enviada al profesor.'
          : tipo === 'responder_pregunta' ? 'Respuesta guardada.' : 'Guardado.';
        if (tipo === 'entrega' || tipo === 'publicar_nota' || tipo === 'nota' || tipo === 'publicar_actividad') {
          renderizarInicioAcademico();
        }
      }
    } catch (error) {
      estado.textContent = '';
      errorLocal = document.createElement('p');
      errorLocal.className = 'aviso-docente aviso-error';
      errorLocal.setAttribute('role', 'alert');
      errorLocal.textContent = error.message;
      boton.before(errorLocal);
    } finally {
      boton.disabled = false;
      if (form.dataset.tipoTrabajo === 'generar_material') boton.textContent = 'Generar borrador';
    }
  }));
}
