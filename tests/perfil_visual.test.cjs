// Catálogo vinculado y recorte de imágenes: sin navegador ni red.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const nodes=new Map();function node(id){if(!nodes.has(id))nodes.set(id,{});return nodes.get(id);}
let dibujo,tamano;
class Lector {readAsDataURL(){this.result='data:image/png;base64,falso';this.onload();}}
class Imagen {constructor(){this.naturalWidth=1600;this.naturalHeight=900;}set src(v){this.onload();}}
const c=vm.createContext({FileReader:Lector,Image:Imagen,$:node,llenarSelect(el,opciones,valor){el.opciones=opciones;el.value=valor;},document:{createElement(tipo){assert.equal(tipo,'canvas');return {getContext(){return {drawImage(...v){dibujo=v.slice(1);}}},toDataURL(tipo){tamano=[this.width,this.height];assert.equal(tipo,'image/png');return 'data:image/png;base64,resultado';}}}}});
vm.runInContext(fs.readFileSync('web/cuentas.js','utf8'),c);
vm.runInContext("catalogoAcademico=[{id:'ingenieria',nombre:'Ingeniería',carreras:[{id:'sistemas',nombre:'Ingeniería en Sistemas'}]},{id:'salud',nombre:'Salud',carreras:[{id:'medicina',nombre:'Medicina'}]}];llenarFacultades()",c);
assert.equal(node('perfil-carrera').disabled,true);
vm.runInContext("llenarCarreras('ingenieria','sistemas')",c);assert.equal(node('perfil-carrera').value,'sistemas');assert.equal(node('perfil-carrera').disabled,false);assert.equal(node('perfil-carrera').opciones.length,2);
vm.runInContext("llenarCarreras('salud')",c);assert.equal(node('perfil-carrera').value,'');assert.equal(node('perfil-carrera').opciones[1].valor,'medicina');
(async()=>{
 for(const [tipo,esperado] of [['foto',[512,512]],['banner',[1200,400]]]){c.archivo={type:'image/jpeg',size:1000};await vm.runInContext(`rasterizarPerfil(archivo,'${tipo}')`,c);assert.deepEqual(tamano,esperado);assert.ok(dibujo[0]>=0&&dibujo[1]>=0);assert.equal(dibujo[6],esperado[0]);assert.equal(dibujo[7],esperado[1]);}
 c.archivo={type:'image/svg+xml',size:100};await assert.rejects(vm.runInContext("rasterizarPerfil(archivo,'foto')",c));
 c.archivo={type:'image/png',size:6*1024*1024};await assert.rejects(vm.runInContext("rasterizarPerfil(archivo,'foto')",c));
 console.log('OK: listas vinculadas, cambio de facultad, recorte foto/banner y rechazo de tipo/tamaño.');
})().catch(e=>{console.error(e);process.exitCode=1;});
