'use strict';
/* CATÁLOGO DE DEMOSTRACIÓN. No es oferta académica, matrícula ni sílabo oficial.
   Los datos no se envían a Grace ni se persisten en estado.json. */
const CATALOGO_DEMOSTRACION = Object.freeze([
  Object.freeze({id:'logica',nombre:'Introducción a la lógica',descripcion:'Ejercicios introductorios de razonamiento.',temas:['Ideas y argumentos','Resolución de problemas'],color:'celeste',demostracion:true,horarios:Object.freeze([
    {dia:0,inicio:'07:00',fin:'08:30',edificio:'A',piso:1,aula:'A-101'},
    {dia:2,inicio:'07:00',fin:'08:30',edificio:'A',piso:1,aula:'A-101'}
  ])}),
  Object.freeze({id:'comunicacion',nombre:'Comunicación académica',descripcion:'Práctica de lectura y expresión clara.',temas:['Lectura comprensiva','Presentaciones breves'],color:'turquesa',demostracion:true,horarios:Object.freeze([
    {dia:1,inicio:'09:00',fin:'10:30',edificio:'B',piso:2,aula:'B-205'},
    {dia:3,inicio:'09:00',fin:'10:30',edificio:'B',piso:2,aula:'B-205'}
  ])}),
  Object.freeze({id:'matematicas',nombre:'Matemática básica',descripcion:'Ejemplos genéricos para practicar cálculos.',temas:['Operaciones','Problemas cotidianos'],color:'azul',demostracion:true,horarios:Object.freeze([
    {dia:0,inicio:'10:00',fin:'11:30',edificio:'C',piso:3,aula:'C-302'},
    {dia:4,inicio:'10:00',fin:'11:30',edificio:'C',piso:3,aula:'C-302'}
  ])})
]);
// El prototipo original no proporciona horario verificado de Programación Estructurada.
// Mantenerlo vacío evita inventar horas, edificios y aulas del curso principal.
const HORARIO_CURSO_PRINCIPAL = Object.freeze([]);
