"""Menú opcional para defender las cinco estructuras sin abrir la web.

Ejecutar: python demo_consola.py
Basado en el estilo de menús por funciones visto en clases.
No altera los datos académicos de la página web.
"""
import tempfile
from pathlib import Path

from grace.archivos import AlmacenJSON
from grace.estructuras import ArbolBinarioBusqueda, ColaEnlazada, GrafoAprendizaje


def ejemplo_listas():
    actividades = [
        {'id': 1, 'tema': 'Listas', 'entregado': False},
        {'id': 2, 'tema': 'Colas enlazadas', 'entregado': True},
        {'id': 3, 'tema': 'Árboles', 'entregado': False},
    ]
    pendientes = [a for a in actividades if not a['entregado']]
    print(f'Actividades totales: {len(actividades)}')
    for actividad in pendientes:
        print(f"Pendiente #{actividad['id']}: {actividad['tema']}")


def ejemplo_cola():
    cola = ColaEnlazada()
    for nombre in ('Ana', 'Diego', 'Sofía'):
        cola.encolar(nombre)
        print('Se agregó a la cola:', nombre)
    print('Primera persona que será atendida:', cola.ver_frente())
    while cola.tamano:
        print('Atendiendo:', cola.desencolar())
    print('Cola vacía:', cola.tamano == 0)


def ejemplo_archivos():
    with tempfile.TemporaryDirectory() as directorio:
        almacen = AlmacenJSON(directorio)
        almacen.guardar('prueba.json', {'curso': 'Programación Estructurada', 'cantidad': 3})
        print('Guardado en:', Path(directorio) / 'prueba.json')
        print('Leído desde archivo:', almacen.leer('prueba.json'))
    print('Se eliminó la carpeta temporal de la demostración.')


def ejemplo_arbol():
    arbol = ArbolBinarioBusqueda()
    for numero in (105, 102, 108, 101, 103):
        arbol.insertar(numero, {'id': numero, 'titulo': f'Actividad {numero}'})
    print('Buscar 103:', arbol.buscar(103))
    print('Recorrido en orden:', [a['id'] for a in arbol.en_orden()])
    print('Niveles:', arbol.niveles())


def ejemplo_grafo():
    grafo = GrafoAprendizaje()
    for origen, destino in (('Fundamentos', 'Funciones'), ('Funciones', 'Listas'),
                            ('Funciones', 'Archivos'), ('Listas', 'Grafos'),
                            ('Archivos', 'Grafos')):
        grafo.agregar_relacion(origen, destino)
    print('Recorrido BFS:', ' → '.join(grafo.recorrido_anchura('Fundamentos')))
    print('Ruta corta:', ' → '.join(grafo.ruta_mas_corta('Fundamentos', 'Grafos')))


def menu():
    acciones = {
        '1': ('Listas y recorridos', ejemplo_listas),
        '2': ('Cola enlazada FIFO', ejemplo_cola),
        '3': ('Archivos y persistencia JSON', ejemplo_archivos),
        '4': ('Árbol binario de búsqueda', ejemplo_arbol),
        '5': ('Grafo con BFS', ejemplo_grafo),
    }
    while True:
        print('\n=== GRACE AI · DEMOSTRACIÓN DE ESTRUCTURAS ===')
        for numero, (nombre, _) in acciones.items():
            print(f'{numero}. {nombre}')
        print('0. Salir')
        opcion = input('Elige una opción: ').strip()
        if opcion == '0':
            print('Fin de la demostración. Tiempo. Claridad. Tranquilidad.')
            break
        seleccion = acciones.get(opcion)
        if seleccion is None:
            print('Opción no válida; prueba del 0 al 5.')
            continue
        print(f'\n--- {seleccion[0]} ---')
        seleccion[1]()


if __name__ == '__main__':
    menu()
