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
const sinMovimiento = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

const $ = id => document.getElementById(id);
const escapar = dato => String(dato ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const formatFecha = fecha => { const p = String(fecha || '').split('-'); return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : ''; };
let semanaVisible = null;
let cursoSeleccionado = 'principal';
let origenFicha = 'mis-clases';
function cursosMostrados() {
  return [{id:'principal',nombre:'Programación Estructurada',descripcion:'Curso del prototipo local. Sus actividades provienen de los datos ficticios del servidor.',temas:['Actividades publicadas en la demostración'],color:'azul',demostracion:false,horarios:HORARIO_CURSO_PRINCIPAL}, ...CATALOGO_DEMOSTRACION];
}
function etiquetaDemo() {return '<span class="etiqueta-demo">Demostración · no oficial</span>';}
function cursoPorId(id) {return cursosMostrados().find(c=>c.id===id);}
function abrirFicha(id, origen='mis-clases') {
  const c=cursoPorId(id);
  if(!c || rolActual!=='estudiante') return;
  cursoSeleccionado=id;
  origenFicha=origen;
  $('ficha-titulo').textContent=c.nombre;
  const horario=c.horarios.map(h=>`<li>${DIAS_SEMANA_ES[h.dia]} · ${h.inicio}–${h.fin} · Edificio ${h.edificio}, aula ${h.aula} (piso ${h.piso})</li>`).join('');
  $('ficha-contenido').innerHTML=`${c.demostracion?etiquetaDemo():'<span class="etiqueta-demo">Prototipo local · no oficial</span>'}<p>${escapar(c.descripcion)}</p>
    <h2>Temas de ejemplo</h2><p class="nota-demo">No son un sílabo oficial ni contenidos garantizados por una universidad.</p>
    <ul>${c.temas.map(t=>`<li>${escapar(t)}</li>`).join('')}</ul>
    <h2>Horario ilustrativo</h2>${horario?`<ul>${horario}</ul>`:'<p>No hay horario semanal verificado para este curso del prototipo.</p>'}
    <p class="nota-demo">Ficha informativa de solo lectura: navegar no registra matrícula ni modifica datos.</p>`;
  navegar('ficha-curso','ficha-titulo');
}
function renderizarCatalogo() {
  $('catalogo-cursos').innerHTML=cursosMostrados().map(c=>`<article class="curso-tarjeta curso-${escapar(c.color)}">
    <div class="curso-linea">${c.demostracion?etiquetaDemo():'<span class="etiqueta-demo">Prototipo local · no oficial</span>'}<span>${c.id==='principal'?'Curso del prototipo':'Curso de muestra'}</span></div>
    <h2>${escapar(c.nombre)}</h2><p>${escapar(c.descripcion)}</p>
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
}
function renderizarActividadesHorario() {
  const a=estado.actividades;
  $('horario-actividades').innerHTML=a.length?a.slice().sort((x,y)=>x.fecha.localeCompare(y.fecha)).map(a=>`<article class="activity-row"><div class="activity-main"><strong>${escapar(a.titulo)}</strong><p>Programación Estructurada · ${escapar(formatFecha(a.fecha))} · Curso del prototipo</p></div></article>`).join(''):cajaVacia('Programación Estructurada: sin actividades publicadas. Los cursos de muestra no incluyen tareas.');
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

function navegar(pagina, destino = '') {
  if ((pagina === 'estructuras' || pagina === 'docentes') && rolActual !== 'profesor') pagina = 'inicio';
  if (['cursos','curso','calendario','asistencia','mis-clases','horario','ficha-curso'].includes(pagina) && rolActual !== 'estudiante') return;
  const nueva = document.getElementById(pagina);
  if (!nueva || !nueva.classList.contains('page')) return;
  clearTimeout(temporizadorVista);
  document.querySelectorAll('.page.leaving').forEach(e => e.classList.remove('leaving'));
  const anterior = document.querySelector('.page.active');
  const cambiar = () => {
    document.querySelectorAll('.page').forEach(e => e.classList.toggle('active', e.id === pagina));
    document.querySelectorAll('[data-page]').forEach(e => {
      const activa = e.dataset.page === pagina;
      e.classList.toggle('active', activa);
      if (activa) e.setAttribute('aria-current','page');
      else e.removeAttribute('aria-current');
    });
    if (destino) {
      const objetivo = document.getElementById(destino);
      if (objetivo && objetivo.closest('.page')?.id === pagina) {
        objetivo.scrollIntoView({block:'start', behavior:'auto'});
        objetivo.focus({preventScroll:true});
        return;
      }
    }
    window.scrollTo({top:0,behavior:'auto'});
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
  ['chat-topic','assistant-topic'].forEach(id => { if ($(id)) llenarSelect($(id), temasAsistente.map(t=>({valor:t,nombre:t})), temasAsistente.includes('Listas') ? 'Listas' : temasAsistente[0]); });
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
  const actividades = document.querySelector('#curso .twocol');
  const asistencia = document.querySelector('#curso .attendance-student');
  const calendario = document.querySelector('#curso .course-calendar');
  if (actividades) actividades.hidden = nombre !== 'actividades';
  if (asistencia) asistencia.hidden = nombre !== 'asistencia';
  if (calendario) calendario.hidden = nombre !== 'calendario';
  document.querySelectorAll('[data-course-tab]').forEach(b => {
    const activo = b.dataset.courseTab === nombre;
    b.setAttribute('aria-selected', String(activo));
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
    const presente = registro ? registro.presente : true;
    const resumen = estado.resumen_asistencia.por_estudiante[e.id];
    return `<label class="attendance-row"><span><strong>${escapar(e.nombre)}</strong><small>Asistencia acumulada: ${escapar(porcentaje(resumen.porcentaje))} (${resumen.presentes}/${resumen.registrados})</small></span><span class="attendance-control"><input type="checkbox" role="switch" data-clase-estudiante="${escapar(e.id)}" ${presente?'checked':''}><span class="attendance-state">${presente?'Presente':'Ausente'}</span></span></label>`;
  }).join('');
  const presentes = registros.filter(r => r.presente).length;
  const ratio = registros.length ? `${Math.round(presentes * 1000 / registros.length) / 10}%` : 'Sin registros';
  $('resumen-clase').textContent = `En esta fecha: ${ratio} (${presentes}/${registros.length} registros). Acumulado de la clase: ${porcentaje(estado.resumen_asistencia.clase.porcentaje)}. Los días sin registro no cuentan como ausencias.`;
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

async function enviarChat(mensaje, destino='chat') {
  mensaje = mensaje.trim();
  if (!mensaje) return;
  const chat = $(destino);
  agregarMensajeChat(`<div class="bubble me">${escapar(mensaje)}</div>`);
  if (!asistenteActivado) {
    if (chat) chat.insertAdjacentHTML('beforeend','<div class="bubble ai">El asistente está desactivado. No se envió nada al servidor.</div>');
    return;
  }
  if (!chat) return;
  const consulta = ++secuenciaConsulta;
  agregarMensajeChat(`<div class="bubble ai" data-consulta-pendiente="${consulta}" role="status">Grace está consultando la IA. Puede tardar hasta 30 segundos…</div>`);
  const estadoAsistente = $('assistant-status');
  if (estadoAsistente) estadoAsistente.textContent = 'Consultando…';
  chat.scrollTop=chat.scrollHeight;
  try {
    const r = await api('/api/conversar',{mensaje,rol:rolActual === 'profesor' ? 'docente' : 'estudiante',estudiante_id:estudianteActual});
    const fuente = r.origen || 'reglas';
    const estadoReal = fuente === 'IA' ? 'IA conectada; respaldo de reglas disponible' :
      fuente === 'reglas (respaldo)' ? 'IA no disponible; respuesta por reglas de respaldo' : 'Asistente por reglas locales';
    document.querySelectorAll?.('[data-ia-mode]')?.forEach(e => { e.textContent = estadoReal; });
    agregarMensajeChat(`<div class="bubble ai">${escapar(r.respuesta)}<small class="response-source">Fuente: ${fuente}</small></div>`);
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
    const selector = boton.closest('.assistant-dock')?.querySelector('select') || $('chat-topic');
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
    e.target.closest('.attendance-control').querySelector('.attendance-state').textContent = e.target.checked ? 'Presente' : 'Ausente';
  });
  $('form-clase').addEventListener('submit',e=>{
    e.preventDefault();
    const registros=[...document.querySelectorAll('[data-clase-estudiante]')].map(c=>({
      estudiante_id:c.dataset.claseEstudiante, presente:c.checked,
    }));
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
    asistenteActivado = e.target.checked;
    $('assistant-state').textContent = asistenteActivado ? 'Activado' : 'Desactivado';
    $('assistant-disabled-note').hidden = asistenteActivado;
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
  $('role-gate')?.classList.toggle('hidden', Boolean(rolActual));
  if ($('role-label')) $('role-label').textContent = esProfesor ? 'Espacio docente' : 'Área personal';
  if ($('user-label')) $('user-label').textContent = esProfesor ? 'Profesor' : 'Estudiante';
  document.querySelectorAll('.student-nav').forEach(e=>e.hidden=esProfesor);
  document.querySelectorAll('.teacher-nav').forEach(e=>e.hidden=!esProfesor);
  if (esProfesor) navegar('docentes');
  else navegar('inicio');
}

function seleccionarRol(rol) {
  rolActual = rol;
  sessionStorage.setItem('grace-rol', rol);
  aplicarRol();
}

async function iniciar() {
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
    await cargar();
    const estudiantes=estado.estudiantes.map(e=>({valor:e.id,nombre:e.nombre}));
    llenarSelect($('estudiante-actual'),estudiantes,estudianteActual);
    seleccionarPestanaCurso('actividades');
  } catch (e) {avisar(`No se pudo conectar con Python: ${e.message}. Inicia el servidor con python app.py`,true);}
  eventos();
}
document.addEventListener('DOMContentLoaded',iniciar);
