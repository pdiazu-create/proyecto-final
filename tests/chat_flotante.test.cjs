// Prueba funcional del cliente sin red ni dependencias.
const {readFileSync} = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const nodos = new Map();
function nodo(id) {
  if (!nodos.has(id)) {
    const clases = new Set();
    nodos.set(id, {html:'', scrollHeight:100, scrollTop:0, atributos:{},
      classList:{toggle(c,on){if(on) clases.add(c); else clases.delete(c);},
        remove(c){clases.delete(c);}, contains(c){return clases.has(c);}},
      setAttribute(k,v){this.atributos[k]=v;}, focus(){this.enfocado=true;},
      insertAdjacentHTML(_,html){this.html += html;}
    });
  }
  return nodos.get(id);
}
let llamadas = 0;
const contexto = vm.createContext({
  sessionStorage:{getItem(){return 'estudiante';}},
  document:{getElementById:nodo,addEventListener(){}},
  fetch:async()=>{llamadas++;return {ok:true,json:async()=>({respuesta:'Respuesta de prueba',origen:'IA'})};},
  setTimeout,clearTimeout,console
});
vm.runInContext(readFileSync('web/app.js','utf8'),contexto);
(async()=>{
  vm.runInContext('mostrarChatFlotante(true)',contexto);
  assert.equal(nodo('grace-launcher').atributos['aria-expanded'],'true');
  vm.runInContext('mostrarChatFlotante(false); mostrarChatFlotante(true)',contexto);
  assert.equal(nodo('assistant-dock').classList.contains('drawer-open'),true);
  await vm.runInContext("enviarChat('hola', 'assistant-messages')",contexto);
  for (const id of ['chat','assistant-messages']) {
    assert.match(nodo(id).html,/hola/);
    assert.match(nodo(id).html,/Respuesta de prueba/);
    assert.match(nodo(id).html,/Fuente: IA/);
  }
  assert.equal(llamadas,1);
  vm.runInContext('asistenteActivado = false',contexto);
  await vm.runInContext("enviarChat('otra pregunta', 'assistant-messages')",contexto);
  assert.equal(llamadas,1);
  assert.match(nodo('assistant-messages').html,/No se envió nada al servidor/);
  console.log('OK: abrir, cerrar, reabrir, respuesta en flotante y chat, desactivado sin red.');
})().catch(error=>{console.error(error);process.exitCode=1;});
