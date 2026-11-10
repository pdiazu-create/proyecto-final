'use strict';

function leerPreferencia(tipo, defecto) {
  if (!cuentaActual) return defecto;
  try {
    return JSON.parse(localStorage.getItem(`grace:${cuentaActual.id}:${tipo}`)) ?? defecto;
  } catch {
    return defecto;
  }
}

function guardarPreferencia(tipo, valor) {
  if (!cuentaActual) return;
  try {
    localStorage.setItem(`grace:${cuentaActual.id}:${tipo}`, JSON.stringify(valor));
  } catch {
    // La preferencia aplicada sigue disponible mientras la página esté abierta.
  }
}

function aplicarLecturaGrace(apariencia = leerPreferencia('lectura', {})) {
  const tema = cuentaActual ? (cuentaActual.tema || 'claro') : apariencia?.tema;
  const oscuro = tema === 'oscuro';
  const grande = apariencia?.texto === 'grande';
  document.body.classList.toggle('grace-oscura', oscuro);
  document.body.classList.toggle('grace-letra-grande', grande);
  if ($('preferencia-tema')) $('preferencia-tema').value = oscuro ? 'oscuro' : 'claro';
  if ($('preferencia-texto')) $('preferencia-texto').value = grande ? 'grande' : 'normal';
}

function prepararLecturaGrace() {
  $('preferencias-lectura').addEventListener('change', async () => {
    const temaAnterior = cuentaActual ? (cuentaActual.tema || 'claro') : leerPreferencia('lectura', {}).tema;
    const apariencia = {tema: $('preferencia-tema').value, texto: $('preferencia-texto').value};
    if (cuentaActual) cuentaActual.tema = apariencia.tema;
    aplicarLecturaGrace(apariencia);
    guardarPreferencia('lectura', apariencia);
    if (!cuentaActual || apariencia.tema === temaAnterior) return;
    const estado = $('preferencia-feedback');
    if (estado) estado.textContent = 'Guardando el tema en tu perfil…';
    try {
      const guardado = await api('/api/preferencias', {tema: apariencia.tema});
      cuentaActual.tema = guardado.tema;
      if (estado) estado.textContent = 'Tema guardado en tu perfil.';
    } catch (error) {
      if (cuentaActual) cuentaActual.tema = temaAnterior;
      const restaurada = {...apariencia, tema: temaAnterior};
      aplicarLecturaGrace(restaurada);
      guardarPreferencia('lectura', restaurada);
      if (estado) estado.textContent = `${error.message} Se mantuvo el tema anterior.`;
    }
  });
}

function aplicarTemaDesdeGrace(tema) {
  if (!['claro', 'oscuro'].includes(tema)) return;
  if (cuentaActual) cuentaActual.tema = tema;
  const apariencia = {...leerPreferencia('lectura', {}), tema};
  guardarPreferencia('lectura', apariencia);
  aplicarLecturaGrace(apariencia);
  const estado = $('preferencia-feedback');
  if (estado) estado.textContent = 'Tema guardado en tu perfil.';
}

function personalizarTarjetasGrace(vista) {
  const contenedor = vista.querySelector('.inicio-tarjetas');
  const opciones = $('lista-tarjetas-rol');
  const tarjetas = new Map([...contenedor.children].map(t => [t.dataset.tarjetaRol, t]));
  const clave = 'tarjetas-' + rolActual;
  const predeterminadas = [...tarjetas.keys()].map(id => ({id, visible: true}));
  const guardadas = leerPreferencia(clave, []);
  let orden = [];
  if (Array.isArray(guardadas)) {
    for (const opcion of guardadas) {
      if (opcion && tarjetas.has(opcion.id) && typeof opcion.visible === 'boolean'
          && !orden.some(x => x.id === opcion.id)) orden.push(opcion);
    }
  }
  orden.push(...predeterminadas.filter(x => !orden.some(y => y.id === x.id)));

  function aplicar(foco, persistir = false) {
    if (!vista.isConnected) return;
    if (persistir) guardarPreferencia(clave, orden);
    for (const opcion of orden) {
      const tarjeta = tarjetas.get(opcion.id);
      tarjeta.hidden = !opcion.visible;
      contenedor.append(tarjeta);
    }
    vista.querySelector('.inicio-accesos-titulo').hidden = !orden.some(x => x.visible);
    opciones.innerHTML = orden.map(({id, visible}, i) => {
      const titulo = escapar(tarjetas.get(id).querySelector('h2').textContent.trim());
      return `<div class="widget-option"><label><input type="checkbox" data-tarjeta-visible="${i}" ${visible ? 'checked' : ''}>
        ${titulo}</label><span><button type="button" class="mini-btn" data-tarjeta-mover="${i}" data-direccion="-1"
        aria-label="Subir ${titulo}" ${i === 0 ? 'disabled' : ''}>↑</button>
        <button type="button" class="mini-btn" data-tarjeta-mover="${i}" data-direccion="1"
        aria-label="Bajar ${titulo}" ${i === orden.length - 1 ? 'disabled' : ''}>↓</button></span></div>`;
    }).join('');
    if (foco !== undefined) opciones.querySelector(`[data-tarjeta-visible="${foco}"]`)?.focus();
  }
  opciones.onchange = e => {
    const control = e.target.closest('[data-tarjeta-visible]');
    if (!control) return;
    const indice = Number(control.dataset.tarjetaVisible);
    orden[indice].visible = control.checked;
    aplicar(indice, true);
  };
  opciones.onclick = e => {
    const control = e.target.closest('[data-tarjeta-mover]');
    if (!control) return;
    const indice = Number(control.dataset.tarjetaMover);
    const destino = indice + Number(control.dataset.direccion);
    if (destino < 0 || destino >= orden.length) return;
    [orden[indice], orden[destino]] = [orden[destino], orden[indice]];
    aplicar(destino, true);
  };
  $('restablecer-tarjetas-rol').onclick = () => {
    orden = predeterminadas.map(x => ({...x}));
    aplicar(undefined, true);
  };
  aplicar();
}
