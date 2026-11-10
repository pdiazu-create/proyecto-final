'use strict';
/* Cliente web pequeño: toda la lógica académica y las estructuras están en Python. */
let estado = null;
let estudianteActual = 'e1';
let mensajeTemporizador;
let temporizadorToast;
let temporizadorVista;
let cargasPendientes = 0;
let rolActual = sessionStorage.getItem('grace-rol') || '';
let asistenteActivado = true;
let modoIA = 'reglas';
let secuenciaConsulta = 0;
const sinMovimiento = () => document.body.classList.contains('movimiento-apagado') || window.matchMedia('(prefers-reduced-motion: reduce)').matches;

const $ = id => document.getElementById(id);
const escapar = dato => String(dato ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const formatFecha = fecha => { const p = String(fecha || '').split('-'); return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : ''; };
let semanaVisible = null;
let cursoSeleccionado = 'principal';
let origenFicha = 'mis-clases';
let temaContexto = '';
let sesionActual = null;
let pestanaCurso = 'sesiones';
let filtroSesiones = 'todas';
function cursosMostrados() {
  return [{id:'principal',nombre:'Programación Estructurada',descripcion:'Curso del prototipo local. Sus actividades provienen de los datos ficticios del servidor.',temas:['Actividades publicadas en la demostración'],color:'azul',demostracion:false,horarios:HORARIO_CURSO_PRINCIPAL}, ...CATALOGO_DEMOSTRACION];
}
function etiquetaDemo() {return '<span class="etiqueta-demo">Demostración · no oficial</span>';}
function cursoPorId(id) {return cursosMostrados().find(c=>c.id===id);}
function abrirFicha(id, origen='mis-clases') {
  const c=cursoPorId(id);
  if(!c || !rolActual) return;
  cursoSeleccionado=id;
  origenFicha=origen;
  $('ficha-titulo').textContent=c.nombre;
  const horario=c.horarios.map(h=>`<li>${DIAS_SEMANA_ES[h.dia]} · ${h.inicio}–${h.fin} · Edificio ${h.edificio}, aula ${h.aula} (piso ${h.piso})</li>`).join('');
  $('ficha-contenido').innerHTML=`${c.demostracion?etiquetaDemo():'<span class="etiqueta-demo">Prototipo local · no oficial</span>'}<p>${escapar(c.descripcion)}</p>
    <h2>Temas de ejemplo</h2><p class="nota-demo">No son un sílabo oficial ni contenidos garantizados por una universidad.</p>
    <ul>${c.temas.map(t=>`<li>${escapar(t)}</li>`).join('')}</ul>
    <h2>Horario ilustrativo</h2>${horario?`<ul>${horario}</ul>`:'<p>No hay horario semanal verificado para este curso del prototipo.</p>'}
    ${id==='principal'?'<div class="plan-actions"><button type="button" class="primary-btn" data-curso-vista="sesiones">Entrar a las sesiones →</button><button type="button" class="outline-btn" data-curso-vista="actividades">Ver actividades</button></div>':'<h2>Actividades y recursos</h2><p>Todavía no hay material publicado para esta asignatura.</p>'}`;
  navegar('ficha-curso','ficha-titulo');
}
function renderizarCatalogo() {
  $('catalogo-cursos').innerHTML=cursosMostrados().map(c=>`<article class="curso-tarjeta curso-${escapar(c.color)}">
    <div class="curso-linea">${c.demostracion?etiquetaDemo():'<span class="etiqueta-demo">Prototipo local · no oficial</span>'}<span>${c.id==='principal'?'Curso del prototipo':'Curso de muestra'}</span></div>
    <h2>${escapar(c.nombre)}</h2><p>${escapar(c.descripcion)}</p>${c.id==='principal'&&estado?`<p>${estado.actividades.filter(a=>a.entregada).length} de ${estado.actividades.length} actividades entregadas</p><button type="button" class="primary-btn" data-curso-vista="sesiones">Entrar al curso →</button>`:''}
    <a href="#ficha-curso" data-curso="${escapar(c.id)}" data-origen="mis-clases">Ver ficha del curso →</a></article>`).join('');
}
function bloquesHorario() {
  return CATALOGO_DEMOSTRACION.flatMap(c=>c.horarios.map(h=>({...h,cursoId:c.id,nombre:c.nombre,color:c.color})));
}
function enlaceBloque(b) {
  return `<a href="#ficha-curso" class="bloque-horario curso-${escapar(b.color)}" data-curso="${escapar(b.cursoId)}" data-origen="horario"><strong>${escapar(b.nombre)}</strong>
  <span>${escapar(b.inicio)}–${escapar(b.fin)}</span><span>Edificio ${escapar(b.edificio)} · aula ${escapar(b.aula)}</span>${etiquetaDemo()}</a>`;
}
function renderizarHorario() {
  if (!semanaVisible) semanaVisible = lunesDeSemana(new Date());
  const fechas=Array.from({length:5},(_,i)=>sumarDiasLocales(semanaVisible,i));
  $('semana-periodo').textContent=`${fechas[0].toLocaleDateString('es-NI',{day:'numeric',month:'long',year:'numeric'})} – ${fechas[4].toLocaleDateString('es-NI',{day:'numeric',month:'long',year:'numeric'})}`;
  const bloques=bloquesHorario();
  const horas=[...new Set(bloques.map(h=>h.inicio))].sort();
  $('horario-tabla').innerHTML=`<table class="tabla-horario"><caption>Horario semanal de demostración. Semana del ${escapar(fechaLocal(fechas[0]))} al ${escapar(fechaLocal(fechas[4]))}; no oficial.</caption>
  <thead><tr><th scope="col">Hora</th>${fechas.map((f,i)=>`<th scope="col">${DIAS_SEMANA_ES[i]}<span>${f.toLocaleDateString('es-NI',{day:'numeric',month:'short'})}</span></th>`).join('')}</tr></thead>
  <tbody>${horas.map(hora=>`<tr><th scope="row">${hora}</th>${fechas.map((_,dia)=>`<td>${bloques.filter(b=>b.dia===dia && b.inicio===hora).map(enlaceBloque).join('')||'<span class="sin-clase">Sin clase de muestra</span>'}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
  $('horario-movil').innerHTML=fechas.map((f,dia)=>`<section class="dia-horario"><h3>${DIAS_SEMANA_ES[dia]} · ${f.toLocaleDateString('es-NI',{day:'numeric',month:'long'})}</h3>
    <div class="bloques-dia">${bloques.filter(b=>b.dia===dia).sort((a,b)=>a.inicio.localeCompare(b.inicio)).map(enlaceBloque).join('')||'<p>Sin clases de muestra.</p>'}</div></section>`).join('');
  if (typeof renderizarHorarioReal === 'function') renderizarHorarioReal();
}
function renderizarActividadesHorario() {
  const a=estado.actividades;
  $('horario-actividades').innerHTML=a.length?a.slice().sort((x,y)=>x.fecha.localeCompare(y.fecha)).map(a=>`<article class="activity-row"><div class="activity-main"><strong>${escapar(a.titulo)}</strong><p>Programación Estructurada · ${escapar(formatFecha(a.fecha))}</p></div><button type="button" class="mini-btn" data-sesion="${escapar(a.id)}">Abrir sesión</button></article>`).join(''):cajaVacia('Programación Estructurada: sin actividades publicadas. Los cursos de muestra no incluyen tareas.');
  if ($('preview-estudiante')) $('preview-estudiante').innerHTML=a.length?a.slice().sort((x,y)=>x.fecha.localeCompare(y.fecha)).slice(0,3).map(a=>`<div class="activity-row"><strong>${escapar(a.titulo)}</strong><span>${escapar(formatFecha(a.fecha))}</span></div>`).join(''):cajaVacia('Todavía no hay actividades publicadas.');
}
function seleccionarTab(tab, enfocar=false) {
  for(const id of ['semana','actividades']) {
    const activo=id===tab,b=$('tab-'+id),p=$('panel-'+id);
    b.setAttribute('aria-selected',String(activo));b.tabIndex=activo?0:-1;p.hidden=!activo;
    if(activo && enfocar)b.focus();
  }
}
function eventosHorario() {
  $('catalogo-cursos').addEventListener('click',eventoFicha);
  $('horario-tabla').addEventListener('click',eventoFicha);
  $('horario-movil').addEventListener('click',eventoFicha);
  $('volver-ficha').addEventListener('click',()=>navegar(origenFicha));
  $('semana-anterior').addEventListener('click',()=>{semanaVisible=sumarDiasLocales(semanaVisible,-7);renderizarHorario();});
  $('semana-siguiente').addEventListener('click',()=>{semanaVisible=sumarDiasLocales(semanaVisible,7);renderizarHorario();});
  $('semana-hoy').addEventListener('click',()=>{semanaVisible=lunesDeSemana(new Date());renderizarHorario();});
  for(const id of ['semana','actividades'])$('tab-'+id).addEventListener('click',()=>seleccionarTab(id));
  $('horario').querySelector('[role=tablist]').addEventListener('keydown',e=>{
    if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;
    e.preventDefault();const actual=$('tab-semana').getAttribute('aria-selected')==='true'?0:1;
    const nuevo=e.key==='Home'?0:e.key==='End'?1:((actual+(e.key==='ArrowRight'?1:-1)+2)%2);
    seleccionarTab(['semana','actividades'][nuevo],true);
  });
}
function eventoFicha(e) {
  const a=e.target.closest('[data-curso]');if(!a)return;
  e.preventDefault();abrirFicha(a.dataset.curso,a.dataset.origen||'mis-clases');
}


const estados = {borrador:'Borrador',en_revision:'En revisión',aprobado:'Aprobado',publicado:'Publicado',rechazado:'Rechazado'};

async function api(ruta, datos) {
  const opciones = datos === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(datos)};
  const respuesta = await fetch(ruta, opciones);
  let cuerpo;
  try { cuerpo = await respuesta.json(); } catch { throw new Error('La respuesta del servidor no es válida.'); }
  if (respuesta.status === 401 && typeof sesionCaducada === 'function') sesionCaducada();
  if (!respuesta.ok) throw new Error(cuerpo.error || `Error ${respuesta.status}`);
  return cuerpo.resultado ?? cuerpo;
}

function avisar(mensaje, error=false) {
  const caja = $('notice'); caja.textContent = mensaje;
  caja.className = 'show' + (error ? ' error' : '');
  clearTimeout(mensajeTemporizador);
  mensajeTemporizador = setTimeout(() => { caja.className=''; }, 5500);
  window.scrollTo({top:0,behavior:'auto'});
}

function mostrarToast(mensaje) {
  const toast = $('toast');
  toast.textContent = mensaje;
  toast.classList.remove('visible');
  // Fuerza una nueva transición cuando se reciben avisos consecutivos.
  void toast.offsetWidth;
  toast.classList.add('visible');
  clearTimeout(temporizadorToast);
  temporizadorToast = setTimeout(() => { toast.classList.remove('visible'); }, 3600);
}

function cambiarCarga(activa) {
  cargasPendientes = Math.max(0, cargasPendientes + (activa ? 1 : -1));
  $('loading-status').hidden = cargasPendientes === 0;
  document.querySelector('.page.active')?.setAttribute('aria-busy', String(cargasPendientes > 0));
}

function navegar(pagina, destino = '', alEntrar) {
  if (typeof cuentaActual !== 'undefined' && cuentaActual?.rol === 'coordinador' &&
      !['inicio','cuentas','perfil','cursos','mis-clases','calendario','horario','seguimiento','comunidad'].includes(pagina)) pagina = 'cuentas';
  pagina = pagina === 'cursos' ? 'mis-clases' : pagina === 'calendario' ? 'horario' : pagina;
  if (pagina === 'comunidad' && !['estudiante','coordinador'].includes(rolActual)) pagina = 'inicio';
  if ((pagina === 'estructuras' || pagina === 'docentes') && rolActual !== 'profesor') pagina = 'inicio';
  if (pagina === 'asistencia' && rolActual !== 'estudiante') pagina = 'docentes';
  const nueva = document.getElementById(pagina);
  if (!nueva || !nueva.classList.contains('page')) return;
  clearTimeout(temporizadorVista);
  document.querySelectorAll('.page.leaving').forEach(e => e.classList.remove('leaving'));
  const anterior = document.querySelector('.page.active');
  const cambiar = () => {
    document.body.classList.toggle('vista-asistente', pagina === 'asistente');
    if (pagina === 'asistente') mostrarChatFlotante(false);
    if (pagina === 'curso') seleccionarPestanaCurso(pestanaCurso);
    if (pagina === 'inicio' && typeof renderizarInicioAcademico === 'function') renderizarInicioAcademico();
    const destinoMenu = ['mis-clases','curso','ficha-curso','sesion','aula-grace'].includes(pagina) ? 'cursos' : pagina === 'horario' ? 'calendario' : pagina;
    document.querySelectorAll('.page').forEach(e => e.classList.toggle('active', e.id === pagina));
    if (pagina === 'comunidad') cargarComunidad();
    document.querySelectorAll('[data-page]').forEach(e => {
      const activa = e.dataset.page === destinoMenu;
      e.classList.toggle('active', activa);
      if (activa) e.setAttribute('aria-current','page');
      else e.removeAttribute('aria-current');
    });
    if (destino) {
      const objetivo = document.getElementById(destino);
      if (objetivo && objetivo.closest('.page')?.id === pagina) {
        const plegable = objetivo.closest('details');
        if (plegable) plegable.open = true;
        if (destino === 'sesion-titulo' || destino === 'aula-titulo') window.scrollTo({top:0,behavior:'auto'});
        else objetivo.scrollIntoView({block:'start', behavior:'auto'});
        objetivo.focus({preventScroll:true});
        alEntrar?.();
        return;
      }
    }
    window.scrollTo({top:0,behavior:'auto'});
    alEntrar?.();
  };
  if (anterior && anterior !== nueva && !sinMovimiento()) {
    anterior.classList.remove('active');
    anterior.classList.add('leaving');
    temporizadorVista = setTimeout(() => { anterior.classList.remove('leaving'); cambiar(); }, 145);
  } else cambiar();
}

async function cargar() {
  cambiarCarga(true);
  try {
    estado = await api('/api/estado?estudiante=' + encodeURIComponent(estudianteActual));
    renderizar();
  } finally { cambiarCarga(false); }
}

function nombres(id) { return estado.estudiantes.find(e => e.id === id)?.nombre || 'Estudiante'; }
function cajaVacia(mensaje) { return `<div class="helper-note">${escapar(mensaje)}</div>`; }

function renderizar() {
  const n = estado.estadisticas;
  $('stat-actividades').textContent=n.actividades;
  $('stat-entregas').textContent=n.entregas;
  $('stat-ayudas').textContent=n.ayudas_pendientes;
  $('stat-planes').textContent=n.planes;
  $('mis-pendientes').textContent=n.mis_pendientes;
  const totalActividades = estado.actividades.length;
  const entregadas = estado.actividades.filter(a => a.entregada).length;
  const progreso = totalActividades ? Math.round((entregadas / totalActividades) * 100) : 0;
  const barra = $('course-progress');
  if (barra) {
    barra.className = `progress-fill progress-fill-${Math.min(10, Math.max(0, Math.round(progreso / 10)))}`;
    barra.setAttribute('aria-valuenow', String(progreso));
  }
  if ($('course-progress-label')) $('course-progress-label').textContent = `${progreso}% completado`;
  if ($('course-progress-detail')) $('course-progress-detail').textContent = `${entregadas} de ${totalActividades} actividades con entrega registrada`;
  const orden = [...estado.actividades].sort((a,b)=>a.fecha.localeCompare(b.fecha));
  $('preview-actividades').innerHTML = orden.slice(0,4).map(a => `<div class="activity-row"><div class="date-square"><b>${escapar(a.fecha.slice(8))}</b>${escapar(a.fecha.slice(5,7))}/${escapar(a.fecha.slice(0,4))}</div><div class="activity-main"><h4>${escapar(a.titulo)}</h4><p>${escapar(a.tema)} · ${escapar(a.total_entregas)} entregas</p></div><span class="tag">#${escapar(a.id)}</span></div>`).join('') || cajaVacia('Sin actividades publicadas.');
  $('actividades').innerHTML = orden.map(a => `<div class="activity-row"><div class="date-square"><b>${escapar(a.fecha.slice(8))}</b>${escapar(a.fecha.slice(5,7))}/${escapar(a.fecha.slice(0,4))}</div><div class="activity-main"><h4>${escapar(a.titulo)}</h4><p>${escapar(a.descripcion)} · ID ${escapar(a.id)}</p></div>${a.entregada?'<span class="tag green">Entregada</span>':`<button class="mini-btn" data-entregar="${escapar(a.id)}">Registrar entrega</button>`}</div>`).join('') || cajaVacia('No hay actividades publicadas aún.');
  $('planes').innerHTML = [...estado.planes].reverse().map(p => {
    const opciones = {borrador:[['revisar','Enviar a revisión']],en_revision:[['aprobar','Aprobar'],['rechazar','Rechazar']],aprobado:[['publicar','Publicar']],publicado:[],rechazado:[]}[p.estado] || [];
    const clase = p.estado==='publicado'?'green':p.estado==='rechazado'?'red':p.estado==='aprobado'?'green':'amber';
    const editable = p.estado==='borrador'||p.estado==='en_revision';
    const fuente = p.origen === 'IA' ? 'Borrador por IA' : 'Borrador por reglas';
    return `<article class="plan"><div class="plan-header"><div><h3>Plan #${escapar(p.id)} · ${escapar(p.tema)}</h3><span class="tag source-tag">${fuente}</span></div><span class="tag ${clase}">${escapar(estados[p.estado])}</span></div><p>${escapar(p.objetivo)} · ${formatFecha(p.fecha)}</p><div class="plan-notes"><div class="plan-note"><b>Inicio</b>${escapar(p.contenido.apertura)}</div><div class="plan-note"><b>Desarrollo</b>${escapar(p.contenido.desarrollo)}</div><div class="plan-note"><b>Práctica</b>${escapar(p.contenido.practica)}</div><div class="plan-note"><b>Evaluación</b>${escapar(p.contenido.evaluacion)}</div></div><div class="plan-actions">${editable?`<button type="button" data-editar="${escapar(p.id)}" class="mini-btn">✎ Editar contenido</button>`:''}${opciones.map(([accion,etiqueta])=>`<button type="button" data-plan="${escapar(p.id)}" data-accion="${accion}" class="mini-btn ${accion==='rechazar'?'danger':''}">${etiqueta}</button>`).join('')}${p.estado==='publicado'?`<span class="tag green">Actividad #${escapar(p.actividad_id)} visible para estudiantes</span>`:''}</div><div class="plan-edit-host" data-edit-host="${escapar(p.id)}"></div><div class="history"><b>Historial verificable:</b> ${p.historial.map(h=>escapar(h.accion)+' · '+escapar(h.actor)+' · '+escapar(h.cuando)).join('  →  ')}</div></article>`;
  }).join('') || cajaVacia('Aún no hay planes. Crea el primero desde el formulario.');
  renderizarClase();
  renderizarAsistenciaEstudiante();
  renderizarCalendarios();
  const temasAsistente = estado.grafo?.temas || ['Listas'];
  ['chat-topic','assistant-topic'].forEach(id => { if ($(id)) llenarSelect($(id), temasAsistente.map(t=>({valor:t,nombre:t})), temasAsistente.includes($(id).value) ? $(id).value : temasAsistente.includes('Listas') ? 'Listas' : temasAsistente[0]); });
  fijarTema(temaContexto);
  const resumen = estado.resumen_asistencia.por_estudiante[estudianteActual];
  if ($('dashboard-attendance')) $('dashboard-attendance').innerHTML = `<strong>${escapar(porcentaje(resumen.porcentaje))}</strong><span>${escapar(resumen.presentes)} presencias de ${escapar(resumen.registrados)} registros</span>`;
  $('cola').innerHTML = estado.solicitudes.map((s,i)=>`<div class="request-row"><span class="num">${i+1}</span><div class="activity-main"><h4>${escapar(nombres(s.estudiante_id))}</h4><p>${escapar(s.mensaje)}</p></div></div>`).join('') || cajaVacia('Cola vacía. Las nuevas solicitudes aparecerán aquí.');
  $('atender').disabled = estado.solicitudes.length===0;
  renderizarArbol(estado.arbol);
  renderizarGrafo(estado.grafo);
  // Los datos académicos existentes no tienen horario verificado; no se infieren horas.
  renderizarCatalogo();
  renderizarHorario();
  renderizarActividadesHorario();
  renderizarSesiones();
  if (sesionActual !== null) renderizarSesion(sesionActual);
}


function filaActividad(a) {
  return `<div class="activity-row"><div class="date-square"><b>${escapar(a.fecha.slice(8))}</b>${escapar(a.fecha.slice(5,7))}/${escapar(a.fecha.slice(0,4))}</div><div class="activity-main"><h4>${escapar(a.titulo)}</h4><p>${escapar(a.tema)} · ${escapar(a.descripcion || 'Actividad del curso')}</p></div><span class="tag">${a.entregada ? 'Entregada' : 'Pendiente'}</span></div>`;
}

function renderizarCalendarios() {
  const orden = [...estado.actividades].sort((a,b)=>a.fecha.localeCompare(b.fecha));
  const html = orden.map(filaActividad).join('') || cajaVacia('Sin actividades publicadas.');
  ['calendario-list','curso-calendario-list'].forEach(id => { if ($(id)) $(id).innerHTML = html; });
  const registros = estado.asistencias.filter(r => r.estudiante_id === estudianteActual)
    .sort((a,b) => b.fecha.localeCompare(a.fecha));
  if ($('asistencia-page-list')) $('asistencia-page-list').innerHTML =
    `<p class="helper-note">${escapar(porcentaje(estado.resumen_asistencia.por_estudiante[estudianteActual].porcentaje))} de asistencia registrada.</p>` +
    (registros.map(r=>`<div class="compact-item"><span>${escapar(formatFecha(r.fecha))}</span><span class="tag ${r.presente?'green':'red'}">${r.presente?'Presente':'Ausente'}</span></div>`).join('') || cajaVacia('Sin asistencias registradas.'));
  const total = estado.actividades.length;
  const hechas = estado.actividades.filter(a=>a.entregada).length;
  const progreso = total ? Math.round(hechas / total * 100) : 0;
  if ($('courses-progress')) {
    $('courses-progress').className = `progress-fill progress-fill-${Math.min(10, Math.max(0, Math.round(progreso / 10)))}`;
    $('courses-progress-label').textContent = `${progreso}% completado`;
    $('courses-progress-detail').textContent = `${hechas} de ${total} actividades con entrega registrada`;
  }
}

function seleccionarPestanaCurso(nombre) {
  pestanaCurso = nombre;
  const actividades = document.querySelector('#curso .twocol');
  const asistencia = document.querySelector('#curso .attendance-student');
  const calendario = document.querySelector('#curso .course-calendar');
  if (actividades) actividades.hidden = nombre !== 'actividades';
  if (asistencia) asistencia.hidden = nombre !== 'asistencia';
  if (calendario) calendario.hidden = nombre !== 'calendario';
  const sesiones = document.querySelector('#curso .course-sessions');
  if (sesiones) sesiones.hidden = nombre !== 'sesiones';
  document.querySelectorAll('[data-course-tab]').forEach(b => {
    const activo = b.dataset.courseTab === nombre;
    b.setAttribute('aria-selected', String(activo));
    b.tabIndex = activo ? 0 : -1;
    b.classList.toggle('active', activo);
  });
}

function porcentaje(valor) {
  return valor == null ? 'Sin registros' : `${valor}%`;
}

function renderizarClase() {
  const fecha = $('fecha-clase').value;
  const registros = estado.asistencias.filter(r => r.fecha === fecha);
  const actividades = estado.actividades.filter(a => a.fecha === fecha);
  $('actividad-clase').textContent = actividades.length
    ? `Actividad publicada: ${actividades.map(a => a.titulo).join('; ')}`
    : 'No hay actividad publicada para esta fecha.';
  $('lista-clase').innerHTML = estado.estudiantes.map(e => {
    const registro = registros.find(r => r.estudiante_id === e.id);
    const presente = registro ? registro.presente : false;
    const resumen = estado.resumen_asistencia.por_estudiante[e.id];
    return `<label class="attendance-row"><span><strong>${escapar(e.nombre)}</strong><small>Asistencia acumulada: ${escapar(porcentaje(resumen.porcentaje))} (${resumen.presentes}/${resumen.registrados})</small></span><select data-clase-estudiante="${escapar(e.id)}" aria-label="Asistencia de ${escapar(e.nombre)}"><option value="" ${!registro?'selected':''}>Sin registrar</option><option value="true" ${registro&&presente?'selected':''}>Presente</option><option value="false" ${registro&&!presente?'selected':''}>Ausente</option></select></label>`;
  }).join('');
  const presentes = registros.filter(r => r.presente).length;
  const ratio = registros.length ? `${Math.round(presentes * 1000 / registros.length) / 10}%` : 'Sin registros';
  $('resumen-clase').textContent = `En esta fecha: ${ratio} (${presentes}/${registros.length} registros). Acumulado de la clase: ${porcentaje(estado.resumen_asistencia.clase.porcentaje)}. Los días sin registro no cuentan como ausencias.`;
  resumenAntesDeGuardar();
}

function renderizarAsistenciaEstudiante() {
  const registros = estado.asistencias.filter(r => r.estudiante_id === estudianteActual)
    .sort((a,b) => b.fecha.localeCompare(a.fecha));
  const resumen = estado.resumen_asistencia.por_estudiante[estudianteActual];
  $('asistencia-estudiante').innerHTML = `<p class="helper-note">Porcentaje: ${escapar(porcentaje(resumen.porcentaje))}. Presencias: ${resumen.presentes} de ${resumen.registrados} clases registradas.</p>`
    + (registros.map(r=>`<div class="compact-item"><span>${escapar(formatFecha(r.fecha))}</span><span class="tag ${r.presente?'green':'red'}">${r.presente?'Presente':'Ausente'}</span></div>`).join('') || cajaVacia('Sin asistencias registradas para este estudiante.'));
}

function renderizarArbol(nodos) {
  if (!nodos.length) { $('arbol').innerHTML=cajaVacia('Árbol vacío.'); return; }
  const niveles=[...new Set(nodos.map(n=>n.nivel))].sort((a,b)=>a-b);
  $('arbol').innerHTML=niveles.map(nivel=>`<div class="tree-level"><span class="tree-level-label">Nivel ${nivel}</span>${nodos.filter(n=>n.nivel===nivel).map(n=>`<span class="tree-node">#${escapar(n.id)}<small>${n.padre==null?'Raíz del árbol':`Hijo ${n.lado==='izquierda'?'izquierdo':'derecho'} de #${escapar(n.padre)}`}</small></span>`).join('')}</div>`).join('');
}

function renderizarGrafo(grafo) {
  // El layout es exclusivamente visual: las rutas provienen del BFS en Python.
  const posiciones={
    'Fundamentos':[90,64],'Condicionales':[240,64],'Ciclos':[380,64],
    'Funciones':[510,64],'Listas':[655,26],'Archivos':[655,109],
    'Colas enlazadas':[804,26],'Árboles':[947,26],'Grafos':[1070,75]
  };
  const lineas=grafo.relaciones.map(r=>{
    const a=posiciones[r.desde], b=posiciones[r.hasta];
    if(!a||!b)return '';
    return `<path class="graph-edge" d="M ${a[0]+58} ${a[1]} L ${b[0]-62} ${b[1]}" marker-end="url(#flecha)"/>`;
  }).join('');
  const nodos=grafo.temas.map(t=>{
    const xy=posiciones[t];if(!xy)return '';
    return `<rect class="graph-node" x="${xy[0]-58}" y="${xy[1]-21}" rx="12" width="116" height="42"/><text class="graph-text" x="${xy[0]}" y="${xy[1]}">${escapar(t)}</text>`;
  }).join('');
  $('grafo').innerHTML=`<svg viewBox="0 0 1150 165" role="img" aria-label="Grafo dirigido desde Fundamentos hasta Grafos"><defs><marker id="flecha" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6" fill="none" stroke="#b8afd8" stroke-width="1.3"/></marker></defs>${lineas}${nodos}</svg><div class="graph-legend">Cada flecha indica un prerrequisito. Desliza para ver todos los temas.</div>`;
}

function mostrarEditor(id) {
  const plan=estado.planes.find(p=>p.id===id);
  if(!plan||!['borrador','en_revision'].includes(plan.estado))return;
  const host=document.querySelector(`[data-edit-host="${id}"]`);
  if(!host)return;
  if(host.innerHTML.trim()){host.innerHTML='';return;}
  const titulos={apertura:'Inicio',desarrollo:'Desarrollo',practica:'Práctica',evaluacion:'Evaluación'};
  host.innerHTML=`<div class="plan-edit"><h4>Editar plan #${escapar(id)}</h4><form data-edit-form="${escapar(id)}">${Object.entries(titulos).map(([campo,nombre])=>`<label>${nombre}<textarea name="${campo}" minlength="5" maxlength="400" required>${escapar(plan.contenido[campo])}</textarea></label>`).join('')}<div class="plan-edit-controls"><button class="primary-btn" type="submit">Guardar cambios</button><button class="outline-btn" type="button" data-cancelar="${escapar(id)}">Cancelar</button></div><p class="micro">Al editar, el plan vuelve a borrador y debe revisarse otra vez. Los cambios quedan en el historial.</p></form></div>`;
  host.querySelector('textarea')?.focus();
}

function llenarSelect(elemento, opciones, actual) {
  elemento.innerHTML = opciones.map(o=>`<option value="${escapar(o.valor)}" ${o.valor===actual?'selected':''}>${escapar(o.nombre)}</option>`).join('');
}

async function ejecutar(accion, exito) {
  try { await accion(); await cargar(); if (exito) mostrarToast(exito); return true; }
  catch (e) { avisar(e.message, true); return false; }
}

async function enviarChat(mensaje, destino='chat', contexto={}) {
  mensaje = mensaje.trim();
  if (!mensaje) return;
  const chat = $(destino);
  agregarMensajeChat(`<div class="bubble me">${escapar(mensaje)}</div>`);
  if (!asistenteActivado) {
    if (chat) agregarMensajeChat('<div class="bubble ai">El asistente está desactivado. No se envió nada al servidor.</div>');
    return;
  }
  if (!chat) return;
  const consulta = ++secuenciaConsulta;
  agregarMensajeChat(`<div class="bubble ai" data-consulta-pendiente="${consulta}" role="status">Grace está preparando una respuesta…</div>`);
  const estadoAsistente = $('assistant-status');
  if (estadoAsistente) estadoAsistente.textContent = 'Consultando…';
  chat.scrollTop=chat.scrollHeight;
  try {
    const cursoAula = document.querySelector?.('#aula-grace.active')?.dataset.cursoId;
    const datos = {mensaje};
    if (cursoAula) datos.curso_id = cursoAula;
    const r = await api('/api/conversar',{...datos,...contexto});
    if (r.accion === 'cambiar_tema' && r.datos?.tema) aplicarTemaDesdeGrace(r.datos.tema);
    if (r.accion === 'abrir_pantalla' && r.datos?.pantalla) navegar(r.datos.pantalla);
    const fuente = r.origen || 'reglas';
    const estadoReal = fuente === 'IA' ? 'IA conectada; respaldo de reglas disponible' :
      fuente === 'reglas (respaldo)' ? 'IA no disponible; respuesta por reglas de respaldo' : 'Asistente por reglas locales';
    document.querySelectorAll?.('[data-ia-mode]')?.forEach(e => { e.textContent = estadoReal; });
    const respuesta = escapar(r.respuesta).replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');
    agregarMensajeChat(`<div class="bubble ai">${respuesta}<small class="response-source">Fuente: ${fuente}</small></div>`);
    const accesos = (r.accesos || []).filter(a =>
      a && ['calendario','mis-clases','inicio'].includes(a.pantalla) &&
      typeof a.etiqueta === 'string');
    if (accesos.length) {
      agregarMensajeChat(`<div class="assistant-shortcuts">${accesos.map(a =>
        `<button type="button" class="mini-btn" data-grace-pantalla="${escapar(a.pantalla)}">${escapar(a.etiqueta)} →</button>`
      ).join('')}</div>`);
    }
    if (r.aviso) agregarMensajeChat(`<div class="helper-note" role="status">${escapar(r.aviso)}${r.estado_http ? ' (HTTP ' + Number(r.estado_http) + ')' : ''}</div>`);
    if (estadoAsistente) estadoAsistente.textContent = 'Respuesta lista';
  } catch (e) {
    chat.insertAdjacentHTML('beforeend',`<div class="bubble ai">${escapar(e.message)}<small class="response-source">No se pudo consultar Grace</small></div>`);
    if (estadoAsistente) estadoAsistente.textContent = 'Error al consultar';
  } finally {
    document.querySelectorAll?.(`[data-consulta-pendiente="${consulta}"]`)?.forEach(e => e.remove());
  }
  chat.scrollTop=chat.scrollHeight;
}

function agregarMensajeChat(html) {
  ['chat','assistant-messages'].forEach(id => {
    const contenedor = $(id);
    if (!contenedor) return;
    contenedor.insertAdjacentHTML('beforeend', html);
    contenedor.scrollTop = contenedor.scrollHeight;
  });
}

function preguntaRapida(boton) {
  let mensaje = boton.dataset.question;
  if (mensaje === 'Explícame este tema') {
    const elegido = boton.closest('.assistant-dock')?.querySelector('select') || $('chat-topic');
    const selector = {value: temaContexto || elegido?.value};
    mensaje = `Explícame ${selector?.value || 'Listas'}`;
  }
  enviarChat(mensaje, boton.closest('.assistant-dock') ? 'assistant-messages' : 'chat');
}

// Compatibilidad de lectura: el destino equivalente anterior era
// enviarChat(b.dataset.question, b.closest('.assistant-dock') ? 'assistant-messages' : 'chat').

function eventos() {
  document.querySelectorAll('[data-page]').forEach(b=>b.addEventListener('click',()=>navegar(b.dataset.page)));
  document.querySelectorAll('[data-go]').forEach(b=>b.addEventListener('click',()=>navegar(b.dataset.go, b.dataset.focus || '')));
  $('estudiante-actual').addEventListener('change', async e=>{estudianteActual=e.target.value;await ejecutar(cargar);});
  $('form-plan').addEventListener('submit', async e=>{
    e.preventDefault();
    const creado=await ejecutar(()=>api('/api/planes',{objetivo:$('objetivo').value,tema:$('tema').value,fecha:$('fecha-plan').value}), 'Borrador creado. Revísalo y apruébalo antes de publicarlo.');
    if(creado){e.target.reset(); $('fecha-plan').value=fechaLocal(new Date());}
  });
  $('planes').addEventListener('click',async e=>{
    const cancelar=e.target.closest('[data-cancelar]');
    if(cancelar){document.querySelector(`[data-edit-host="${cancelar.dataset.cancelar}"]`).innerHTML='';return;}
    const editar=e.target.closest('[data-editar]');
    if(editar){mostrarEditor(Number(editar.dataset.editar));return;}
    const btn=e.target.closest('[data-plan]'); if(!btn)return;
    if(btn.dataset.accion==='publicar'&&!confirm('¿Publicar esta actividad para los estudiantes?'))return;
    await ejecutar(()=>api('/api/planes/estado',{id:Number(btn.dataset.plan),accion:btn.dataset.accion}),'Cambio registrado en el historial del plan.');
  });
  $('planes').addEventListener('submit',async e=>{
    const form=e.target.closest('[data-edit-form]');if(!form)return;
    e.preventDefault();
    const datos=new FormData(form);
    const contenido=Object.fromEntries(['apertura','desarrollo','practica','evaluacion'].map(c=>[c,datos.get(c)]));
    await ejecutar(()=>api('/api/planes/editar',{id:Number(form.dataset.editForm),contenido}), 'Borrador editado. Se requiere revisión y aprobación de nuevo.');
  });
  $('fecha-clase').addEventListener('change',renderizarClase);
  $('lista-clase').addEventListener('change',e=>{
    if (!e.target.matches('[data-clase-estudiante]')) return;
    resumenAntesDeGuardar();
  });
  $('form-clase').addEventListener('submit',e=>{
    e.preventDefault();
    const registros=[...document.querySelectorAll('[data-clase-estudiante]')].map(c=>({
      estudiante_id:c.dataset.claseEstudiante, presente:c.value === 'true',
    }));
    const resumen = resumenAntesDeGuardar();
    if (resumen.sinRegistrar) { avisar('Selecciona Presente o Ausente para cada estudiante antes de guardar.',true); return; }
    if (!confirm(`Guardar asistencia del ${formatFecha($('fecha-clase').value)}: ${resumen.presentes} presentes y ${resumen.ausentes} ausentes. ¿Confirmas?`)) return;
    ejecutar(()=>api('/api/asistencia/lote',{fecha:$('fecha-clase').value,registros}),
      'Asistencia de toda la clase guardada.');
  });
  $('actividades').addEventListener('click',e=>{
    const btn=e.target.closest('[data-entregar]'); if(!btn)return;
    ejecutar(()=>api('/api/entregas',{actividad_id:Number(btn.dataset.entregar),estudiante_id:estudianteActual}),'Entrega registrada.');
  });
  $('form-ayuda').addEventListener('submit',e=>{
    e.preventDefault(); const mensaje=$('pregunta').value;
    ejecutar(()=>api('/api/solicitudes',{estudiante_id:estudianteActual,mensaje}),'Solicitud agregada al final de la cola enlazada.').then(ok=>{if(ok)$('pregunta').value='';});
  });
  $('atender').addEventListener('click',()=>ejecutar(()=>api('/api/atender',{}),'Se atendió la primera solicitud de la cola.'));
  $('form-buscar').addEventListener('submit',async e=>{
    e.preventDefault();try {const r=await api('/api/buscar?id='+encodeURIComponent($('id-buscar').value));$('buscar-resultado').textContent=r.actividad?`Encontrada: ${r.actividad.titulo} (${r.actividad.tema}).`:'No existe una actividad con ese ID.';}catch(err){avisar(err.message,true);}
  });
  $('form-ruta').addEventListener('submit',async e=>{
    e.preventDefault();try{const r=await api('/api/ruta?origen='+encodeURIComponent($('origen').value)+'&destino='+encodeURIComponent($('destino').value));$('ruta-resultado').innerHTML=r.ruta.length?r.ruta.map((s,i)=>`${i?'<b>→</b>':''}<span class="route-step">${escapar(s)}</span>`).join(''):'<span class="helper-note">No existe ruta dirigida entre esos temas.</span>';}catch(err){avisar(err.message,true);}
  });
  $('form-chat').addEventListener('submit',e=>{e.preventDefault();const m=$('mensaje-chat').value.trim();if(m) enviarChat(m);$('mensaje-chat').value='';});
  document.querySelectorAll('[data-question]').forEach(b=>b.addEventListener('click',()=>preguntaRapida(b)));
  document.querySelectorAll('[data-course-tab]').forEach(b=>b.addEventListener('click',()=>seleccionarPestanaCurso(b.dataset.courseTab)));
  document.querySelectorAll('[data-role]').forEach(b=>b.addEventListener('click',()=>{
    if (b.tagName !== 'A') seleccionarRol(b.dataset.role);
  }));
  $('assistant-toggle')?.addEventListener('change', e=>{
    cambiarAsistente(e.target.checked);
  });
  $('assistant-collapse')?.addEventListener('click',()=>{
    mostrarChatFlotante(false);
  });
  $('assistant-open')?.addEventListener('click',()=>{
    mostrarChatFlotante(true);
  });
  $('grace-launcher')?.addEventListener('click',()=>mostrarChatFlotante(!$('assistant-dock').classList.contains('drawer-open')));
  document.addEventListener('keydown',e=>{if(e.key==='Escape') mostrarChatFlotante(false);});
  $('dock-chat-form')?.addEventListener('submit', e=>{e.preventDefault(); const input=$('dock-message'); const m=input.value.trim(); if(m) enviarChat(m,'assistant-messages'); input.value='';});
  eventosHorario();
  $('cambiar-acceso')?.addEventListener('click',()=>{sessionStorage.removeItem('grace-rol');});
  $('reset').addEventListener('click',async()=>{
    if(!confirm('¿Restaurar todos los datos ficticios de la demostración?'))return;
    await ejecutar(()=>api('/api/reiniciar',{confirmacion:'REINICIAR DEMO'}),'Datos ficticios restaurados.');
  });
}

function mostrarChatFlotante(abierto) {
  const panel = $('assistant-dock');
  panel.classList.toggle('drawer-open', abierto);
  panel.classList.remove('collapsed');
  panel.setAttribute('aria-hidden', String(!abierto));
  $('grace-launcher')?.setAttribute('aria-expanded', String(abierto));
  $('assistant-open')?.setAttribute('aria-expanded', String(abierto));
  if (abierto) {
    $('assistant-messages').scrollTop = $('assistant-messages').scrollHeight;
    $('dock-message').focus();
  } else $('grace-launcher')?.focus();
}

function aplicarRol() {
  const esProfesor = rolActual === 'profesor';
  document.body.classList.toggle('role-profesor', esProfesor);
  document.body.classList.toggle('role-estudiante', !esProfesor);
  $('role-gate')?.classList.toggle('hidden', Boolean(rolActual) && (typeof cuentaActual === 'undefined' || Boolean(cuentaActual)));
  if ($('role-label')) $('role-label').textContent = esProfesor ? 'Espacio docente' : 'Área personal';
  if ($('user-label')) $('user-label').textContent = esProfesor ? 'Profesor' : 'Estudiante';
  document.querySelectorAll('.student-nav').forEach(e=>e.hidden=esProfesor);
  document.querySelectorAll('.teacher-nav').forEach(e=>e.hidden=!esProfesor);
  if (esProfesor) navegar('mis-clases');
  else navegar('inicio');
  if (typeof aplicarCuenta === 'function') aplicarCuenta();
}

function seleccionarRol(rol) {
  rolActual = rol;
  sessionStorage.setItem('grace-rol', rol);
  aplicarRol();
}

async function iniciar() {
  prepararInterfaz();
  if(location.pathname === '/estudiante' || location.pathname === '/profesor') {
    rolActual = location.pathname.slice(1);
    sessionStorage.setItem('grace-rol', rolActual);
  } else if (location.pathname === '/') {
    rolActual = '';
    sessionStorage.removeItem('grace-rol');
  }
  aplicarRol();
  const hoy=fechaLocal(new Date());
  $('fecha-plan').value=hoy; $('fecha-clase').value=hoy;
  const temas=['Fundamentos','Condicionales','Ciclos','Funciones','Listas','Archivos','Colas enlazadas','Árboles','Grafos'];
  for(const id of ['tema','origen','destino'])llenarSelect($(id),temas.map(t=>({valor:t,nombre:t})),id==='destino'?'Grafos':'Listas');
  try {
    const salud = await api('/api/salud');
    modoIA = salud.modo || 'reglas';
    const textoModo = modoIA === 'api' ? 'IA configurada; conexión pendiente de comprobar' : 'Asistente por reglas locales';
    document.querySelectorAll('[data-ia-mode]').forEach(e => { e.textContent = textoModo; });
    if (!salud.autenticacion && $('form-acceso')) {
      document.body.classList.add('cuentas-activa');
      $('role-gate').classList.remove('hidden');
      document.querySelector('#role-gate .role-options').hidden=true;
      document.querySelector('.role-disclaimer').textContent='Actualización instalada: cierra Grace y vuelve a abrirla con tu acceso habitual para activar las cuentas.';
      return;
    }
    if (salud.autenticacion && typeof iniciarCuentas === 'function') {
      await iniciarCuentas();
      eventos();
      return;
    }
    await cargar();
    const estudiantes=estado.estudiantes.map(e=>({valor:e.id,nombre:e.nombre}));
    llenarSelect($('estudiante-actual'),estudiantes,estudianteActual);
    seleccionarPestanaCurso('sesiones');
  } catch (e) {avisar(`No se pudo conectar con Python: ${e.message}. Inicia el servidor con python app.py`,true);}
  eventos();
}
document.addEventListener('DOMContentLoaded',iniciar);

function resumenAntesDeGuardar() {
  const controles = [...document.querySelectorAll('[data-clase-estudiante]')];
  const presentes = controles.filter(c=>c.value === 'true').length;
  const ausentes = controles.filter(c=>c.value === 'false').length;
  const sinRegistrar = controles.length - presentes - ausentes;
  if ($('confirmacion-asistencia')) $('confirmacion-asistencia').textContent = `${presentes} presentes · ${ausentes} ausentes · ${sinRegistrar} sin registrar`;
  return {presentes, ausentes, sinRegistrar};
}

function estadoSesion(fecha, hoy=fechaLocal(new Date())) {
  return fecha === hoy ? 'Hoy' : fecha < hoy ? 'Anterior' : 'Próxima';
}

function sesionesFiltradas(filtro, hoy=fechaLocal(new Date())) {
  return [...estado.actividades].filter(a=>filtro==='pendientes' ? !a.entregada : filtro==='anteriores' ? a.fecha<hoy : filtro==='proximas' ? a.fecha>=hoy : true)
    .sort((a,b)=>a.fecha.localeCompare(b.fecha)||a.id-b.id);
}

function renderizarSesiones() {
  if (!$('lista-sesiones')) return;
  $('lista-sesiones').innerHTML = sesionesFiltradas(filtroSesiones).map(a=>`<article class="panel session-link"><div><span class="tag">${escapar(estadoSesion(a.fecha))}</span><h3>${escapar(a.titulo)}</h3><p>${escapar(formatFecha(a.fecha))} · ${escapar(a.tema)}</p><span>${a.entregada?'Actividad entregada':'Actividad pendiente'}</span></div><button type="button" class="primary-btn" data-sesion="${Number(a.id)}">Entrar a la sesión →</button></article>`).join('') || cajaVacia('No hay sesiones en este filtro.');
  document.querySelectorAll('[data-filtro-sesion]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.filtroSesion===filtroSesiones)));
}

function datosSesion(id) {
  const actividad = estado.actividades.find(a=>a.id===Number(id));
  if (!actividad) return null;
  const plan = estado.planes.find(p=>p.estado==='publicado' && p.actividad_id===actividad.id);
  return {actividad, plan};
}

function abrirSesion(id) {
  if (!datosSesion(id)) { avisar('La actividad ya no está disponible.',true); return; }
  sesionActual = Number(id);
  pestanaCurso = 'sesiones';
  renderizarSesion(sesionActual);
  navegar('sesion','sesion-titulo');
}

function renderizarSesion(id) {
  const datos = datosSesion(id);
  if (!datos) return;
  const {actividad:a,plan:p} = datos;
  $('sesion-titulo').textContent = a.titulo;
  $('sesion-fecha').textContent = `${formatFecha(a.fecha)} · ${a.tema} · ${estadoSesion(a.fecha)}`;
  const bloque = (id,titulo,contenido)=>`<section class="panel session-block" id="sesion-${id}"><h2>${titulo}</h2><p class="session-text">${escapar(contenido)}</p></section>`;
  const partes = [];
  if (p) partes.push(['apertura','Antes de clase',p.contenido.apertura]);
  partes.push(['desarrollo','Durante la clase',p?.contenido.desarrollo || a.descripcion]);
  const actividad = `<section class="panel session-block" id="sesion-actividad"><span class="eyebrow">ACTIVIDAD</span><h2>${escapar(a.titulo)}</h2><p class="session-text">${escapar(p?.contenido.practica || a.descripcion)}</p><p>${a.entregada?'Entrega registrada para este estudiante.':'Esta actividad está pendiente.'}</p>${rolActual==='estudiante'&&!a.entregada?`<button type="button" class="primary-btn" data-entregar="${Number(a.id)}">Registrar entrega</button><p class="micro">Se registra la entrega; esta versión todavía no adjunta archivos.</p>`:''}</section>`;
  if (p) partes.push(['cierre','Después de clase',p.contenido.evaluacion]);
  $('sesion-contenido').innerHTML = partes.filter(([id])=>id!=='cierre').map(x=>bloque(...x)).join('') + actividad + partes.filter(([id])=>id==='cierre').map(x=>bloque(...x)).join('');
  $('sesion-agenda').innerHTML = partes.filter(([id])=>id!=='cierre').map(([id,titulo])=>`<a href="#sesion-${id}">${titulo}</a>`).join('') + '<a href="#sesion-actividad">Actividad y entrega</a>' + (p?'<a href="#sesion-cierre">Después de clase</a>':'');
  fijarTema(a.tema);
  $('explicar-sesion').textContent = `Explícame ${a.tema}`;
}

function fijarTema(tema) {
  temaContexto = tema || '';
  ['chat-topic','assistant-topic'].forEach(id=>{
    if (temaContexto && $(id) && [...$(id).options].some(o=>o.value===temaContexto)) $(id).value=temaContexto;
  });
  document.querySelectorAll('[data-question="Explícame este tema"]').forEach(b=>{b.textContent=temaContexto?`Explícame ${temaContexto}`:'Explícame este tema';});
  document.querySelectorAll('.topic-context-bar').forEach(e=>{e.textContent=temaContexto?`Tema: ${temaContexto}`:'Consulta general · Programación Estructurada';});
}

function prepararInterfaz() {
  prepararMenu();
  prepararWidgets();
  const interruptor = document.createElement('label');
  interruptor.className='switch-row chat-switch';
  interruptor.innerHTML='<span>Asistente: <strong id="chat-assistant-state">Activado</strong></span><input type="checkbox" id="chat-assistant-toggle" checked aria-label="Activar o desactivar el asistente">';
  document.querySelector('#asistente .chat-top').append(interruptor);
  $('chat-assistant-toggle').addEventListener('change',e=>cambiarAsistente(e.target.checked));
  const tabs = document.querySelector('#curso .course-tabs');
  const boton = document.createElement('button');
  boton.type='button'; boton.setAttribute('role','tab'); boton.dataset.courseTab='sesiones'; boton.textContent='Sesiones';
  tabs.prepend(boton);
  const panel = document.createElement('div');
  panel.className='course-sessions';
  panel.innerHTML='<div class="session-filter" role="group" aria-label="Filtrar sesiones"><button class="outline-btn" type="button" data-filtro-sesion="todas" aria-pressed="true">Todas</button><button class="outline-btn" type="button" data-filtro-sesion="anteriores" aria-pressed="false">Anteriores</button><button class="outline-btn" type="button" data-filtro-sesion="proximas" aria-pressed="false">Próximas</button><button class="outline-btn" type="button" data-filtro-sesion="pendientes" aria-pressed="false">Con pendientes</button></div><div id="lista-sesiones" class="session-list"></div>';
  tabs.after(panel);
  const paneles = {sesiones:panel,actividades:document.querySelector('#curso .twocol'),asistencia:document.querySelector('#curso .attendance-student'),calendario:document.querySelector('#curso .course-calendar')};
  tabs.querySelectorAll('[data-course-tab]').forEach(b=>{const id=b.dataset.courseTab;b.id='curso-tab-'+id;b.setAttribute('aria-controls','curso-panel-'+id);paneles[id].id='curso-panel-'+id;paneles[id].setAttribute('role','tabpanel');paneles[id].setAttribute('aria-labelledby',b.id);});
  tabs.addEventListener('keydown',e=>{
    if (!['ArrowLeft','ArrowRight','Home','End'].includes(e.key)) return;
    e.preventDefault(); const botones=[...tabs.querySelectorAll('[data-course-tab]')], indice=botones.indexOf(document.activeElement);
    const nuevo=e.key==='Home'?0:e.key==='End'?botones.length-1:(indice+(e.key==='ArrowRight'?1:-1)+botones.length)%botones.length;
    seleccionarPestanaCurso(botones[nuevo].dataset.courseTab); botones[nuevo].focus();
  });
  ['chat-topic','assistant-topic'].forEach(id=>{
    const etiqueta=$(id).closest('label'), detalles=document.createElement('details'), resumen=document.createElement('summary'), contexto=document.createElement('p');
    detalles.className='topic-options'; resumen.textContent='Cambiar tema'; contexto.className='topic-context-bar';
    etiqueta.before(contexto,detalles); detalles.append(resumen,etiqueta);
    $(id).addEventListener('change',e=>fijarTema(e.target.value));
  });
  $('explicar-sesion').addEventListener('click',()=>{mostrarChatFlotante(true);enviarChat(`Explícame ${temaContexto || 'Listas'}`,'assistant-messages');});
  document.addEventListener('click',e=>{
    const accesoGrace=e.target.closest('[data-grace-pantalla]');
    if(accesoGrace){
      const pantalla=accesoGrace.dataset.gracePantalla;
      if(['calendario','mis-clases','inicio'].includes(pantalla))navegar(pantalla);
      return;
    }
    const abrir=e.target.closest('[data-sesion]'); if(abrir){abrirSesion(abrir.dataset.sesion);return;}
    const vista=e.target.closest('[data-curso-vista]'); if(vista){pestanaCurso=vista.dataset.cursoVista;navegar('curso');return;}
    const filtro=e.target.closest('[data-filtro-sesion]'); if(filtro){filtroSesiones=filtro.dataset.filtroSesion;renderizarSesiones();return;}
    const entrega=e.target.closest('#sesion [data-entregar]');
    if(entrega) ejecutar(()=>api('/api/entregas',{actividad_id:Number(entrega.dataset.entregar),estudiante_id:estudianteActual}),'Entrega registrada.');
  });
  fijarTema('');
}

function prepararMenu() {
  const boton=$('menu-toggle');
  document.querySelectorAll('.sidebar .nav-btn').forEach(e=>{
    e.setAttribute('aria-label',e.textContent.trim());e.title=e.textContent.trim();
    [...e.childNodes].filter(n=>n.nodeType===Node.TEXT_NODE&&n.textContent.trim()).forEach(n=>{const texto=document.createElement('span');texto.className='nav-text';texto.textContent=n.textContent.trim();n.replaceWith(texto);});
  });
  function aplicar(valor){document.body.classList.toggle('menu-colapsado',valor);boton.setAttribute('aria-expanded',String(!valor));boton.setAttribute('aria-label',valor?'Ampliar menú':'Reducir menú');boton.querySelector('span').textContent=valor?'Ampliar menú':'Reducir menú';sessionStorage.setItem('grace-menu-colapsado',String(valor));}
  aplicar(sessionStorage.getItem('grace-menu-colapsado')==='true');
  boton.addEventListener('click',()=>aplicar(!document.body.classList.contains('menu-colapsado')));
}

function cambiarAsistente(activo) {
  asistenteActivado=Boolean(activo);
  ['assistant-toggle','chat-assistant-toggle'].forEach(id=>{if($(id))$(id).checked=asistenteActivado;});
  ['assistant-state','chat-assistant-state'].forEach(id=>{if($(id))$(id).textContent=asistenteActivado?'Activado':'Desactivado';});
  if($('assistant-disabled-note'))$('assistant-disabled-note').hidden=asistenteActivado;
}

function prepararWidgets() {
  const contenedor=$('widgets-inicio'), reloj=document.createElement('article');
  reloj.className='panel';reloj.innerHTML='<h3>Fecha y hora</h3><p id="reloj-fecha"></p><strong id="reloj-hora" class="clock-value"></strong><p class="micro">Hora local de tu dispositivo.</p>';contenedor.append(reloj);
  const tarjetas=[...contenedor.children],nombres=['Mi curso','Próximas actividades','Mi asistencia','Fecha y hora'],clave='grace-widgets-inicio';
  let orden=tarjetas.map((_,id)=>({id,visible:true}));
  try{const v=JSON.parse(sessionStorage.getItem(clave));if(Array.isArray(v)&&v.length===tarjetas.length&&new Set(v.map(x=>x.id)).size===tarjetas.length&&v.every(x=>Number.isInteger(x.id)&&x.id>=0&&x.id<tarjetas.length&&typeof x.visible==='boolean'))orden=v;}catch{}
  function aplicar(){orden.forEach(x=>{tarjetas[x.id].hidden=!x.visible;contenedor.append(tarjetas[x.id]);});sessionStorage.setItem(clave,JSON.stringify(orden));$('lista-widgets').innerHTML=orden.map((x,i)=>`<div class="widget-option"><label><input type="checkbox" data-widget-visible="${x.id}" ${x.visible?'checked':''}> ${nombres[x.id]}</label><span><button type="button" class="mini-btn" data-widget-mover="${i}" data-direccion="-1" aria-label="Subir ${nombres[x.id]}" ${i===0?'disabled':''}>↑</button><button type="button" class="mini-btn" data-widget-mover="${i}" data-direccion="1" aria-label="Bajar ${nombres[x.id]}" ${i===orden.length-1?'disabled':''}>↓</button></span></div>`).join('');}
  aplicar();
  $('personalizar-inicio').addEventListener('click',()=>$('dialogo-widgets').showModal());
  $('cerrar-widgets').addEventListener('click',()=>$('dialogo-widgets').close());
  $('restablecer-widgets').addEventListener('click',()=>{orden=tarjetas.map((_,id)=>({id,visible:true}));aplicar();});
  $('lista-widgets').addEventListener('change',e=>{const c=e.target.closest('[data-widget-visible]');if(!c)return;orden.find(x=>x.id===Number(c.dataset.widgetVisible)).visible=c.checked;aplicar();$('lista-widgets').querySelector(`[data-widget-visible="${c.dataset.widgetVisible}"]`)?.focus();});
  $('lista-widgets').addEventListener('click',e=>{const b=e.target.closest('[data-widget-mover]');if(!b)return;const i=Number(b.dataset.widgetMover),d=i+Number(b.dataset.direccion);if(d<0||d>=orden.length)return;[orden[i],orden[d]]=[orden[d],orden[i]];aplicar();});
  function movimiento(valor){$('movimiento').value=valor;document.body.classList.toggle('movimiento-apagado',valor==='off');sessionStorage.setItem('grace-movimiento',valor);}
  movimiento(sessionStorage.getItem('grace-movimiento')==='off'?'off':'auto');
  $('movimiento').addEventListener('change',e=>movimiento(e.target.value));
  function hora(){const ahora=new Date();$('reloj-fecha').textContent=ahora.toLocaleDateString('es',{weekday:'long',day:'numeric',month:'long'});$('reloj-hora').textContent=ahora.toLocaleTimeString('es',{hour:'2-digit',minute:'2-digit'});}
  hora();setInterval(hora,30000);
}
