'use strict';
/* Utilidades puras; aceptan fecha inyectada para pruebas con husos horarios. */
const DIAS_SEMANA_ES = Object.freeze(['Lunes','Martes','Miércoles','Jueves','Viernes']);
function fechaLocal(fecha) {
  return `${fecha.getFullYear()}-${String(fecha.getMonth()+1).padStart(2,'0')}-${String(fecha.getDate()).padStart(2,'0')}`;
}
function lunesDeSemana(fecha) {
  const d = new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate());
  d.setDate(d.getDate() - ((d.getDay()+6)%7));
  return d;
}
function sumarDiasLocales(fecha, dias) {
  return new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate()+dias);
}
function minutos(hora) {
  if(!/^([01]\d|2[0-3]):[0-5]\d$/.test(hora)) throw new Error('Hora inválida: '+hora);
  return Number(hora.slice(0,2))*60+Number(hora.slice(3));
}
function validarHorarios(catalogo, existentes=[]) {
  const sesiones = [...existentes, ...catalogo.flatMap(c=>c.horarios.map(h=>({...h,cursoId:c.id})))];
  const errores=[];
  for(const s of sesiones) {
    if (!Number.isInteger(s.dia) || s.dia<0 || s.dia>4 || minutos(s.inicio)>=minutos(s.fin))
      errores.push(`Franja inválida: ${s.cursoId}`);
    if (!/^[A-Z]$/.test(s.edificio)||!Number.isInteger(s.piso)||s.piso<1||s.piso>9||
        !new RegExp(`^${s.edificio}-${s.piso}(0[1-9]|10)$`).test(s.aula))
      errores.push(`Edificio, piso o aula incoherente: ${s.cursoId}`);
  }
  for(let i=0;i<sesiones.length;i++) for(let j=i+1;j<sesiones.length;j++) {
    const a=sesiones[i],b=sesiones[j];
    if(a.dia!==b.dia || minutos(a.inicio)>=minutos(b.fin) || minutos(b.inicio)>=minutos(a.fin)) continue;
    errores.push(`Solape entre ${a.cursoId} y ${b.cursoId}`);
    if(a.edificio===b.edificio && a.aula===b.aula)
      errores.push(`Aula repetida: ${a.edificio} ${a.aula}`);
  }
  return errores;
}
if(typeof module!=='undefined' && module.exports) module.exports={fechaLocal,lunesDeSemana,sumarDiasLocales,validarHorarios,DIAS_SEMANA_ES};
