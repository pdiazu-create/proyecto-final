// Sesión y perfiles del cliente: datos falsos, ninguna conexión.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const nodes=new Map(),removed=[];
function node(id){if(!nodes.has(id)){const classes=new Set();nodes.set(id,{value:'',textContent:'',innerHTML:'',hidden:false,classList:{add(...s){s.forEach(x=>classes.add(x));},remove(...s){s.forEach(x=>classes.delete(x));},toggle(s,on){on?classes.add(s):classes.delete(s);},contains:s=>classes.has(s)}});}return nodes.get(id);}
const c=vm.createContext({document:{getElementById:node,body:node('body'),querySelectorAll(){return [];}},sessionStorage:{removeItem:k=>removed.push(k)},rolActual:'estudiante',estado:{privado:true},escapar:s=>String(s).replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x])),api:async()=>({cuentas:[{nombre:'<img src=x onerror=alert(1)>',usuario:'ana',rol:'estudiante'}]})});
c.$=node;
vm.runInContext(fs.readFileSync('web/cuentas.js','utf8'),c);
vm.runInContext("cuentasActivas=true;cuentaActual={usuario:'ana',rol:'estudiante'};sesionCaducada()",c);
assert.equal(c.rolActual,'');assert.equal(c.estado,null);assert.ok(removed.includes('grace-rol'));assert.match(node('acceso-error').textContent,/sesión terminó/);
vm.runInContext("cuentaActual={nombre:'Ana López',usuario:'ana',rol:'estudiante',carrera:'Computación'};mostrarPerfil()",c);
assert.equal(node('perfil-iniciales').textContent,'AL');assert.equal(node('perfil-docente').hidden,true);assert.equal(node('perfil-carrera').value,'Computación');
vm.runInContext("cuentaActual={nombre:'Martín Rojas',usuario:'martin',rol:'profesor',datos_academicos:'Docente de programación'};mostrarPerfil()",c);
assert.equal(node('perfil-docente').hidden,false);assert.equal(node('perfil-academicos').value,'Docente de programación');
(async()=>{await vm.runInContext('cargarCuentas()',c);assert.ok(node('lista-cuentas').innerHTML.includes('&lt;img'));assert.ok(!node('lista-cuentas').innerHTML.includes('<img'));console.log('OK: sesión caducada, perfiles por rol y escape de nombres.');})().catch(e=>{console.error(e);process.exitCode=1;});
