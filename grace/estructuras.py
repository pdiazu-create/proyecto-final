"""Estructuras hechas a mano para Programación Estructurada.

Listas: se usan para almacenar alumnos, entregas y actividades.
Cola enlazada: atención FIFO de solicitudes de ayuda.
Árbol binario: índice de actividades por identificador.
Grafo dirigido: prerrequisitos académicos y búsqueda BFS.

El propósito de estos algoritmos es didáctico, no sustituir estructuras
altamente optimizadas de Python en un entorno de producción.
"""


class NodoCola:
    def __init__(self, valor):
        self.valor = valor
        self.siguiente = None


class ColaEnlazada:
    """FIFO manual: encolar y desencolar cuestan O(1)."""

    def __init__(self):
        self.frente = None
        self.final = None
        self.tamano = 0

    def encolar(self, valor):
        nodo = NodoCola(valor)
        if self.final is None:
            self.frente = nodo
        else:
            self.final.siguiente = nodo
        self.final = nodo
        self.tamano += 1

    def desencolar(self):
        if self.frente is None:
            return None
        valor = self.frente.valor
        self.frente = self.frente.siguiente
        if self.frente is None:
            self.final = None
        self.tamano -= 1
        return valor

    def ver_frente(self):
        return self.frente.valor if self.frente is not None else None

    def recorrer(self):
        resultado = []
        cursor = self.frente
        while cursor is not None:
            resultado.append(cursor.valor)
            cursor = cursor.siguiente
        return resultado


class NodoArbol:
    def __init__(self, clave, valor):
        self.clave = clave
        self.valor = valor
        self.izquierda = None
        self.derecha = None


class ArbolBinarioBusqueda:
    """Árbol no balanceado, sin recursión para evitar desbordamiento de pila.

    Inserción/búsqueda: O(h); h puede ser n en un árbol desbalanceado.
    El servicio puede reconstruirlo a partir de las claves ordenadas.
    """

    def __init__(self):
        self.raiz = None
        self.tamano = 0

    def insertar(self, clave, valor):
        if self.raiz is None:
            self.raiz = NodoArbol(clave, valor)
            self.tamano = 1
            return
        cursor = self.raiz
        while True:
            if clave == cursor.clave:
                cursor.valor = valor
                return
            if clave < cursor.clave:
                if cursor.izquierda is None:
                    cursor.izquierda = NodoArbol(clave, valor)
                    break
                cursor = cursor.izquierda
            else:
                if cursor.derecha is None:
                    cursor.derecha = NodoArbol(clave, valor)
                    break
                cursor = cursor.derecha
        self.tamano += 1

    def buscar(self, clave):
        cursor = self.raiz
        while cursor is not None:
            if clave == cursor.clave:
                return cursor.valor
            cursor = cursor.izquierda if clave < cursor.clave else cursor.derecha
        return None

    def en_orden(self):
        """Recorrido iterativo: izquierda, raíz, derecha."""
        resultado = []
        pila = []
        cursor = self.raiz
        while pila or cursor is not None:
            while cursor is not None:
                pila.append(cursor)
                cursor = cursor.izquierda
            cursor = pila.pop()
            resultado.append(cursor.valor)
            cursor = cursor.derecha
        return resultado

    def niveles(self):
        """BFS iterativo, con índice frontal para no usar pop(0)."""
        if self.raiz is None:
            return []
        pendientes = [(self.raiz, 0, None, None)]
        indice = 0
        salida = []
        while indice < len(pendientes):
            nodo, nivel, padre, lado = pendientes[indice]
            indice += 1
            salida.append({"id": nodo.clave, "nivel": nivel, "padre": padre, "lado": lado})
            if nodo.izquierda is not None:
                pendientes.append((nodo.izquierda, nivel + 1, nodo.clave, "izquierda"))
            if nodo.derecha is not None:
                pendientes.append((nodo.derecha, nivel + 1, nodo.clave, "derecha"))
        return salida


    def altura(self):
        """Devuelve altura en cantidad de nodos (vacío = 0), sin recursión."""
        if self.raiz is None:
            return 0
        pendientes = [(self.raiz, 1)]
        frente = 0
        maxima = 0
        while frente < len(pendientes):
            nodo, nivel = pendientes[frente]
            frente += 1
            maxima = max(maxima, nivel)
            if nodo.izquierda is not None:
                pendientes.append((nodo.izquierda, nivel + 1))
            if nodo.derecha is not None:
                pendientes.append((nodo.derecha, nivel + 1))
        return maxima

    def reconstruir_balanceado(self):
        """Reordena los mismos pares clave/valor en un árbol de altura O(log n).

        En orden entrega claves ordenadas; elegir el elemento central de cada
        segmento forma un árbol equilibrado. No usa recursión ni cambia IDs.
        Reconstruir cuesta O(n); NO convierte insertar en una operación AVL.
        """
        elementos = []
        pila = []
        actual = self.raiz
        while pila or actual is not None:
            while actual is not None:
                pila.append(actual)
                actual = actual.izquierda
            actual = pila.pop()
            elementos.append((actual.clave, actual.valor))
            actual = actual.derecha

        self.raiz = None
        self.tamano = len(elementos)
        if not elementos:
            return

        pendientes = [(0, len(elementos) - 1, None, None)]
        while pendientes:
            inicio, fin, padre, lado = pendientes.pop()
            if inicio > fin:
                continue
            medio = (inicio + fin) // 2
            clave, valor = elementos[medio]
            nuevo = NodoArbol(clave, valor)
            if padre is None:
                self.raiz = nuevo
            elif lado == 'izquierda':
                padre.izquierda = nuevo
            else:
                padre.derecha = nuevo
            pendientes.append((medio + 1, fin, nuevo, 'derecha'))
            pendientes.append((inicio, medio - 1, nuevo, 'izquierda'))

    def balancear_si_necesario(self):
        """Reconstruye si altura supera altura ideal aproximada + 2 niveles.

        Esto controla el caso habitual de IDs crecientes en esta demo, pero
        comprobar la altura cuesta O(n) y reconstruir también cuesta O(n).
        """
        if self.tamano < 3:
            return False
        limite = self.tamano.bit_length() + 2
        if self.altura() <= limite:
            return False
        self.reconstruir_balanceado()
        return True


class GrafoAprendizaje:
    """Grafo dirigido representado con lista de adyacencia."""

    def __init__(self):
        self.adyacencia = {}

    def agregar_tema(self, tema):
        if tema not in self.adyacencia:
            self.adyacencia[tema] = []

    def agregar_relacion(self, origen, destino):
        self.agregar_tema(origen)
        self.agregar_tema(destino)
        if destino not in self.adyacencia[origen]:
            self.adyacencia[origen].append(destino)

    def recorrido_anchura(self, inicio):
        if inicio not in self.adyacencia:
            return []
        pendientes = [inicio]
        frente = 0
        visitados = {inicio}
        recorrido = []
        while frente < len(pendientes):
            tema = pendientes[frente]
            frente += 1
            recorrido.append(tema)
            for vecino in self.adyacencia[tema]:
                if vecino not in visitados:
                    visitados.add(vecino)
                    pendientes.append(vecino)
        return recorrido

    def ruta_mas_corta(self, inicio, destino):
        """BFS con predecesores: ruta mínima en número de enlaces."""
        if inicio not in self.adyacencia or destino not in self.adyacencia:
            return []
        pendientes = [inicio]
        frente = 0
        anteriores = {inicio: None}
        while frente < len(pendientes):
            tema = pendientes[frente]
            frente += 1
            if tema == destino:
                ruta = []
                while tema is not None:
                    ruta.append(tema)
                    tema = anteriores[tema]
                return list(reversed(ruta))
            for vecino in self.adyacencia[tema]:
                if vecino not in anteriores:
                    anteriores[vecino] = tema
                    pendientes.append(vecino)
        return []

    def conexiones(self):
        return [{"desde": origen, "hasta": destino}
                for origen, vecinos in self.adyacencia.items()
                for destino in vecinos]
