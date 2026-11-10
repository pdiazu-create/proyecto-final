'use strict';
/* Cuentas de demostración. La identidad y los permisos los verifica el servidor. */
let cuentaActual = null;
let cuentasActivas = false;
let guardarPerfilPendiente = false;
let catalogoAcademico = [];
let imagenPendiente = false;
const ETIQUETAS_ROL = Object.freeze({estudiante:'Estudiante',profesor:'Profesor',coordinador:'Coordinación'});

async function iniciarCuentas() {
  cuentasActivas = true;
  document.body.classList.add('cuentas-activa');
  $('form-acceso').hidden = false;
  document.querySelector('.role-disclaimer').textContent = 'Demostración con cuentas ficticias. Contraseña de prueba: 12345';
  document.querySelector('#role-gate .role-options').hidden = true;
  document.querySelector('#role-gate .role-card > p').textContent = 'Entra con tu usuario. Grace abre el espacio que corresponde a tu cuenta.';
  crearVistasCuenta();
  llenarFacultades();
  $('form-acceso').addEventListener('submit', async e => {
    e.preventDefault();
    const boton=e.target.querySelector('button[type="submit"]');
    boton.disabled=true; $('acceso-error').textContent='Comprobando acceso…';
    try {
      const resultado=await api('/api/login',{usuario:$('acceso-usuario').value.trim(),contrasena:$('acceso-clave').value});
      $('acceso-clave').value='';
      await entrarCuenta(resultado.usuario);
      $('acceso-error').textContent='';
    } catch(error) { $('acceso-error').textContent=error.message; }
    finally { boton.disabled=false; }
  });
  const sesion=await api('/api/sesion');
  if(sesion.usuario) await entrarCuenta(sesion.usuario);
  else sesionCaducada(false);
}

function sesionCaducada(mostrar=true) {
  if(!cuentasActivas) return;
  cuentaActual=null; rolActual=''; estado=null;
  if (typeof aplicarLecturaGrace === 'function') aplicarLecturaGrace();
  sessionStorage.removeItem('grace-rol');
  document.body.classList.remove('sesion-activa','role-coordinador','vista-asistente');
  $('role-gate').classList.remove('hidden');
  $('acceso-clave').value='';
  if(mostrar) $('acceso-error').textContent='Tu sesión terminó. Vuelve a entrar.';
}

async function entrarCuenta(cuenta) {
  if(!catalogoAcademico.length){
    try{catalogoAcademico=(await api('/api/catalogo-academico')).facultades;llenarFacultades();}
    catch(error){$('acceso-error').textContent='Reinicia Grace con Detener Grace y Abrir Grace para activar los perfiles actualizados.';throw new Error($('acceso-error').textContent);}
  }
  cuentaActual=cuenta;
  rolActual=cuenta.rol;
  estudianteActual=cuenta.estudiante_id || 'e1';
  // Preferencias del navegador no son una fuente de identidad.
  sessionStorage.removeItem('grace-rol');
  $('chat').replaceChildren(); $('assistant-messages').replaceChildren();
  document.body.classList.add('sesion-activa');
  aplicarRol();
  mostrarPerfil();
  const ruta=cuenta.rol==='coordinador'?'/coordinacion':'/'+cuenta.rol;
  history.replaceState(null,'',ruta);
  await cargarCursosGrace();
  if(cuenta.rol==='coordinador') {
    await cargarCuentas(); navegar('inicio');
  } else {
    await cargar();
    llenarSelect($('estudiante-actual'),estado.estudiantes.map(e=>({valor:e.id,nombre:e.nombre})),estudianteActual);
    seleccionarPestanaCurso('sesiones');
  }
  if (typeof prepararSeguimiento === 'function') prepararSeguimiento();
}

function aplicarCuenta() {
  if(!cuentasActivas || !cuentaActual) return;
  const coordinador=cuentaActual.rol==='coordinador';
  if (typeof aplicarLecturaGrace === 'function') aplicarLecturaGrace();
  document.body.classList.toggle('role-coordinador',coordinador);
  document.body.classList.toggle('role-estudiante',cuentaActual.rol==='estudiante');
  $('user-label').textContent=cuentaActual.nombre;
  $('user-label').title=cuentaActual.nombre;
  const avatar=document.querySelector('.user-avatar');
  avatar.replaceChildren();
  if(cuentaActual.foto){const foto=document.createElement('img');foto.src=cuentaActual.foto;foto.alt='';avatar.append(foto);}else avatar.textContent='◉';
  $('role-label').textContent=ETIQUETAS_ROL[cuentaActual.rol];
  $('cambiar-acceso').textContent='Cerrar sesión';
  $('reset').hidden=true;
  document.querySelectorAll('.account-coordination').forEach(e=>e.hidden=!coordinador);
  document.querySelectorAll('.student-tools').forEach(e=>e.hidden=cuentaActual.rol!=='profesor');
  document.querySelector('[data-course-tab="asistencia"]').hidden=cuentaActual.rol!=='estudiante';
  document.querySelector('#form-ayuda').closest('article').hidden=cuentaActual.rol!=='estudiante';
  $('perfil-nav').hidden=false;
}

function camposPerfil() {
  return `<label for="perfil-nombre">Nombre visible</label><input id="perfil-nombre" name="nombre" maxlength="80" required>
  <label for="perfil-facultad">Facultad</label><select id="perfil-facultad" name="facultad_id" aria-describedby="afiliacion-nota"></select>
  <label for="perfil-carrera">Carrera</label><select id="perfil-carrera" name="carrera_id" aria-describedby="afiliacion-nota"></select>
  <p id="afiliacion-nota" class="micro">Elige tu facultad y después tu carrera. La comunidad usa esta afiliación.</p>
  <label for="perfil-presentacion">Sobre mí</label><textarea id="perfil-presentacion" name="presentacion" rows="3" maxlength="500"></textarea>
  <div id="perfil-docente" class="form"><label for="perfil-academicos">Información académica</label><textarea id="perfil-academicos" name="datos_academicos" rows="3" maxlength="500"></textarea></div>`;
}

function crearVistasCuenta() {
  const perfil=document.createElement('section');perfil.id='perfil';perfil.className='page';
  perfil.innerHTML=`<div class="page-heading"><span class="eyebrow">TU CUENTA</span><h1>Mi perfil</h1><p>Tu espacio en Grace. Estos datos pertenecen a una cuenta ficticia.</p></div>
    <div class="profile-grid"><article class="panel profile-card"><img id="perfil-banner" class="profile-banner" alt="Banner del perfil" hidden><img id="perfil-foto" class="profile-photo" alt="Foto de perfil" hidden><div class="profile-initials" id="perfil-iniciales" aria-hidden="true"></div><h2 id="perfil-resumen-nombre"></h2><p id="perfil-resumen-rol"></p><p id="perfil-resumen-usuario"></p><span class="tag">Cuenta de demostración</span><div class="profile-media-tools"><label class="outline-btn" for="archivo-foto">Cambiar foto</label><input id="archivo-foto" class="profile-file" type="file" accept="image/jpeg,image/png,image/webp"><button id="quitar-foto" type="button" class="text-btn">Quitar foto</button><label class="outline-btn" for="archivo-banner">Cambiar banner</label><input id="archivo-banner" class="profile-file" type="file" accept="image/jpeg,image/png,image/webp"><button id="quitar-banner" type="button" class="text-btn">Quitar banner</button><p class="micro">JPG, PNG o WebP, hasta 5 MB. Se recorta al centro y se guarda sin metadatos.</p><p id="imagen-resultado" class="account-feedback" role="status" aria-live="polite"></p></div></article>
    <article class="panel"><h2>Datos personales</h2><form id="form-perfil" class="form">${camposPerfil()}<p id="perfil-resultado" class="account-feedback" role="status" aria-live="polite"></p><button class="primary-btn" type="submit">Guardar perfil</button></form></article></div>
    <section id="preferencias-lectura" class="panel preferencias-lectura">
      <h2>Preferencias de lectura</h2><p>Los cambios se aplican al instante y se guardan en este navegador.</p>
      <div class="form form-row">
        <label>Apariencia <select id="preferencia-tema"><option value="claro">Claro</option><option value="oscuro">Oscuro</option></select></label>
        <label>Tamaño de letra <select id="preferencia-texto"><option value="normal">Normal</option><option value="grande">Grande</option></select></label>
      </div>
    </section>`;
  const coordinacion=document.createElement('section');coordinacion.id='cuentas';coordinacion.className='page';
  coordinacion.innerHTML=`<div class="page-heading"><span class="eyebrow">COORDINACIÓN</span><h1>Cuentas de Grace</h1><p>Crea accesos de demostración y asigna el espacio de cada persona.</p></div>
    <div class="account-admin-grid"><article class="panel"><h2>Agregar cuenta</h2><form id="form-cuenta" class="form">
    <label for="cuenta-nombre">Nombre</label><input id="cuenta-nombre" name="nombre" maxlength="80" required>
    <label for="cuenta-usuario">Usuario para entrar</label><input id="cuenta-usuario" name="usuario" pattern="[a-zA-Z0-9_]{3,32}" minlength="3" maxlength="32" required aria-describedby="usuario-ayuda"><p id="usuario-ayuda" class="micro">De 3 a 32 letras sin tilde, números o guion bajo. Debe ser único.</p>
    <label for="cuenta-rol">Tipo de cuenta</label><select id="cuenta-rol" name="rol"><option value="estudiante">Estudiante</option><option value="profesor">Profesor</option><option value="coordinador">Coordinación</option></select>
    <p class="helper-note">Contraseña de prueba: <b>12345</b>. Los permisos corresponden al tipo de cuenta.</p><p id="cuenta-resultado" class="account-feedback" role="status" aria-live="polite"></p><button type="submit" class="primary-btn">Crear cuenta</button></form></article>
    <article class="panel"><div class="panel-heading"><h2>Cuentas registradas</h2><button id="actualizar-cuentas" class="outline-btn" type="button">Actualizar</button></div><div id="lista-cuentas" class="account-list" aria-live="polite"></div></article></div>`;
  document.querySelector('.content > footer').before(perfil,coordinacion);
  const botonPerfil=document.createElement('button');botonPerfil.type='button';botonPerfil.className='small-btn';botonPerfil.id='abrir-perfil';botonPerfil.textContent='Mi perfil';botonPerfil.addEventListener('click',()=>{mostrarPerfil();navegar('perfil');});
  $('cambiar-acceso').before(botonPerfil);
  const nav=document.createElement('button');nav.type='button';nav.className='nav-btn account-personal';nav.id='perfil-nav';nav.dataset.page='perfil';nav.innerHTML='<span aria-hidden="true">◉</span><span class="nav-text">Mi perfil</span>';nav.setAttribute('aria-label','Mi perfil');nav.title='Mi perfil';
  const coord=document.createElement('button');coord.type='button';coord.className='nav-btn account-coordination';coord.dataset.page='cuentas';coord.innerHTML='<span aria-hidden="true">▤</span><span class="nav-text">Cuentas</span>';coord.hidden=true;
  $('menu-cuenta-titulo').hidden=false;
  $('menu-principal').append(coord,nav);
  // La barra móvil original conserva su contrato; estos accesos se añaden por cuenta.
  for(const [pagina,texto] of [['cuentas','Cuentas'],['perfil','Perfil']]) {
    const b=document.createElement('button');b.type='button';b.className='account-mobile '+(pagina==='cuentas'?'account-coordination':'account-personal');b.dataset.page=pagina;b.textContent=texto;document.querySelector('.mobile-nav').append(b);
  }
  $('cambiar-acceso').addEventListener('click',async e=>{e.preventDefault();try{await api('/api/logout',{});location.assign('/');}catch(error){avisar(error.message,true);}});
  $('form-perfil').addEventListener('submit',guardarPerfil);
  if (typeof prepararLecturaGrace === 'function') prepararLecturaGrace();
  $('perfil-facultad').addEventListener('change',()=>llenarCarreras($('perfil-facultad').value));
  for(const tipo of ['foto','banner']) {
    $('archivo-'+tipo).addEventListener('change',e=>guardarImagen(tipo,e.target.files[0]));
    $('quitar-'+tipo).addEventListener('click',()=>guardarImagen(tipo,null));
  }
  $('form-cuenta').addEventListener('submit',crearCuenta);
  $('actualizar-cuentas').addEventListener('click',()=>cargarCuentas().catch(e=>{$('lista-cuentas').textContent=e.message;}));
}

function mostrarPerfil() {
  if(!cuentaActual)return;
  const p=cuentaActual;
  $('perfil-iniciales').textContent=p.nombre.trim().split(/\s+/).slice(0,2).map(t=>t[0]).join('').toUpperCase();
  $('perfil-resumen-nombre').textContent=p.nombre;
  $('perfil-resumen-rol').textContent=ETIQUETAS_ROL[p.rol];
  $('perfil-resumen-usuario').textContent='@'+p.usuario;
  for(const campo of ['nombre','carrera','facultad','presentacion','datos_academicos']) $('perfil-'+(campo==='datos_academicos'?'academicos':campo)).value=p[campo]||'';
  if(catalogoAcademico.length) {
    $('perfil-facultad').value=p.facultad_id||'';
    llenarCarreras(p.facultad_id||'',p.carrera_id||'');
    $('afiliacion-nota').textContent=(!p.facultad_id&&(p.facultad||p.carrera))?'El perfil anterior tenía texto libre. Elige una opción del catálogo para vincularte correctamente.':'Elige facultad y carrera para entrar a tu comunidad.';
  }
  for(const tipo of ['foto','banner']) {
    $('perfil-'+tipo).src=p[tipo]||'';
    $('perfil-'+tipo).hidden=!p[tipo];
    $('quitar-'+tipo).disabled=!p[tipo];
  }
  $('perfil-iniciales').hidden=Boolean(p.foto);
  $('perfil-docente').hidden=p.rol!=='profesor';
}

async function guardarPerfil(e) {
  e.preventDefault();if(guardarPerfilPendiente)return;
  const boton=e.target.querySelector('button[type="submit"]');boton.disabled=true;guardarPerfilPendiente=true;
  $('perfil-resultado').textContent='Guardando…';
  try {
    const datos=Object.fromEntries(new FormData(e.target));
    datos.facultad_id=$('perfil-facultad').value;
    datos.carrera_id=$('perfil-carrera').value;
    if(cuentaActual.rol!=='profesor') delete datos.datos_academicos;
    cuentaActual=await api('/api/perfil',datos);
    mostrarPerfil();aplicarCuenta();
    $('perfil-resultado').textContent='Perfil guardado.';
  }catch(error){$('perfil-resultado').textContent=error.message;}
  finally{boton.disabled=false;guardarPerfilPendiente=false;}
}

function llenarFacultades() {
  const opciones=[{valor:'',nombre:'Selecciona facultad'},...catalogoAcademico.map(f=>({valor:f.id,nombre:f.nombre}))];
  llenarSelect($('perfil-facultad'),opciones,'');
  llenarCarreras('');
}

function llenarCarreras(facultad,seleccion='') {
  const carreras=catalogoAcademico.find(f=>f.id===facultad)?.carreras||[];
  llenarSelect($('perfil-carrera'),[{valor:'',nombre:facultad?'Selecciona carrera':'Primero elige facultad'},...carreras.map(c=>({valor:c.id,nombre:c.nombre}))],seleccion);
  $('perfil-carrera').disabled=!facultad;
}

function rasterizarPerfil(archivo,tipo) {
  return new Promise((resolve,reject)=>{
    if(!['image/jpeg','image/png','image/webp'].includes(archivo.type)||archivo.size>5*1024*1024){reject(new Error('Elige JPG, PNG o WebP de hasta 5 MB.'));return;}
    const lector=new FileReader();
    lector.onerror=()=>reject(new Error('No se pudo leer la imagen.'));
    lector.onload=()=>{
      const imagen=new Image();
      imagen.onerror=()=>reject(new Error('El archivo no contiene una imagen válida.'));
      imagen.onload=()=>{
        try{
          const w=imagen.naturalWidth,h=imagen.naturalHeight;
          if(!w||!h||w*h>20000000)throw new Error('La imagen es demasiado grande; usa una de hasta 20 megapíxeles.');
          const ancho=tipo==='foto'?512:1200,alto=tipo==='foto'?512:400;
          const lienzo=document.createElement('canvas');lienzo.width=ancho;lienzo.height=alto;
          const escala=Math.max(ancho/w,alto/h),origenW=ancho/escala,origenH=alto/escala;
          lienzo.getContext('2d').drawImage(imagen,(w-origenW)/2,(h-origenH)/2,origenW,origenH,0,0,ancho,alto);
          resolve(lienzo.toDataURL('image/png'));
        }catch(error){reject(error);}
      };
      imagen.src=lector.result;
    };
    lector.readAsDataURL(archivo);
  });
}

async function guardarImagen(tipo,archivo) {
  if(imagenPendiente)return;
  imagenPendiente=true;
  for(const t of ['foto','banner']){$('archivo-'+t).disabled=true;$('quitar-'+t).disabled=true;}
  $('imagen-resultado').textContent=archivo?'Preparando imagen…':'Quitando imagen…';
  try{
    const imagen=archivo?await rasterizarPerfil(archivo,tipo):'';
    const recursos=await api('/api/perfil/imagen',{tipo,imagen});
    Object.assign(cuentaActual,recursos);
    mostrarPerfil();aplicarCuenta();
    $('imagen-resultado').textContent=archivo?'Imagen guardada.':'Imagen eliminada del perfil.';
  }catch(error){$('imagen-resultado').textContent=error.message;}
  finally{imagenPendiente=false;for(const t of ['foto','banner']){$('archivo-'+t).disabled=false;$('archivo-'+t).value='';$('quitar-'+t).disabled=!cuentaActual[t];}}
}

async function cargarCuentas() {
  const datos=await api('/api/cuentas');
  $('lista-cuentas').innerHTML=datos.cuentas.map(p=>`<article class="account-row"><div><h3>${escapar(p.nombre)}</h3><p>@${escapar(p.usuario)}</p></div><span class="tag">${escapar(ETIQUETAS_ROL[p.rol])}</span></article>`).join('');
}

async function crearCuenta(e) {
  e.preventDefault();const boton=e.target.querySelector('button[type="submit"]');boton.disabled=true;
  $('cuenta-resultado').textContent='Creando cuenta…';
  try {
    const p=await api('/api/cuentas',Object.fromEntries(new FormData(e.target)));
    e.target.reset();$('cuenta-resultado').textContent=`Cuenta @${p.usuario} creada. Contraseña de prueba: 12345.`;
    await cargarCuentas();
  }catch(error){$('cuenta-resultado').textContent=error.message;}
  finally{boton.disabled=false;}
}
