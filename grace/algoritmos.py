# grace/algoritmos.py — extensión independiente de la aplicación

class NodoLista:
    def __init__(self, valor):
        self.valor = valor
        self.siguiente = None


class ListaEnlazada:
    def __init__(self):
        self.cabeza = None
        self.tamano = 0

    def agregar_inicio(self, valor):      # O(1)
        nodo = NodoLista(valor)
        nodo.siguiente = self.cabeza
        self.cabeza = nodo
        self.tamano += 1

    def agregar_final(self, valor):       # O(n): hay que llegar al último
        nodo = NodoLista(valor)
        if self.cabeza is None:
            self.cabeza = nodo
        else:
            actual = self.cabeza
            while actual.siguiente is not None:
                actual = actual.siguiente
            actual.siguiente = nodo
        self.tamano += 1

    def buscar(self, valor):              # O(n)
        actual = self.cabeza
        while actual is not None:
            if actual.valor == valor:
                return True
            actual = actual.siguiente
        return False

    def eliminar(self, valor):            # O(n)
        anterior, actual = None, self.cabeza
        while actual is not None:
            if actual.valor == valor:
                if anterior is None:
                    self.cabeza = actual.siguiente
                else:
                    anterior.siguiente = actual.siguiente
                self.tamano -= 1
                return True
            anterior, actual = actual, actual.siguiente
        return False

    def recorrer(self):                   # O(n)
        valores, actual = [], self.cabeza
        while actual is not None:
            valores.append(actual.valor)
            actual = actual.siguiente
        return valores


class Pila:
    def __init__(self):
        self.tope = None
        self.tamano = 0

    def apilar(self, valor):              # O(1)
        nodo = NodoLista(valor)
        nodo.siguiente = self.tope
        self.tope = nodo
        self.tamano += 1

    def desapilar(self):                  # O(1)
        if self.tope is None:
            return None
        valor = self.tope.valor
        self.tope = self.tope.siguiente
        self.tamano -= 1
        return valor

    def ver_tope(self):
        return None if self.tope is None else self.tope.valor

    def esta_vacia(self):
        return self.tope is None


def burbuja(a):
    a = a[:]                              # no modifica la lista original
    comparaciones = 0
    for i in range(len(a) - 1):
        hubo_cambio = False
        for j in range(len(a) - 1 - i):
            comparaciones += 1
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
                hubo_cambio = True
        if not hubo_cambio:
            break
    return a, comparaciones               # O(n²); O(n) si ya está ordenada


def busqueda_lineal(a, x):
    comparaciones = 0
    for i, valor in enumerate(a):
        comparaciones += 1
        if valor == x:
            return i, comparaciones
    return -1, comparaciones              # O(n)


def busqueda_binaria(a, x):               # a debe estar ordenada
    lo, hi, comparaciones = 0, len(a) - 1, 0
    while lo <= hi:
        mid = (lo + hi) // 2
        comparaciones += 1
        if a[mid] == x:
            return mid, comparaciones
        if a[mid] < x:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1, comparaciones              # O(log n)


if __name__ == "__main__":
    import random

    p = Pila()
    for v in (1, 2, 3):
        p.apilar(v)
    assert p.desapilar() == 3 and p.ver_tope() == 2

    lista = ListaEnlazada()
    lista.agregar_final("B")
    lista.agregar_inicio("A")
    lista.agregar_final("C")
    assert lista.recorrer() == ["A", "B", "C"]
    assert lista.eliminar("B") and lista.recorrer() == ["A", "C"]

    datos = random.sample(range(1, 5001), 1000)
    ordenados, c_burbuja = burbuja(datos)
    objetivo = ordenados[-1]
    _, c_lineal = busqueda_lineal(ordenados, objetivo)
    _, c_binaria = busqueda_binaria(ordenados, objetivo)
    print(f"Burbuja con 1000 datos: {c_burbuja} comparaciones")
    print(f"Buscar el último: lineal {c_lineal}, binaria {c_binaria}")