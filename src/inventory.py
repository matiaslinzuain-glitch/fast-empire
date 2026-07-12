# =========================================================
# FAST EMPIRE — Inventario con slots posicionales  [Fase 15]
#
# El inventario es una GRILLA de tamaño fijo (columnas ×
# filas, configurable por contenedor): cada slot puede estar
# vacío (None) o tener un stack [id_item, cantidad]. La
# posición importa — el drag & drop de la UI mueve, apila e
# intercambia stacks entre slots (y entre contenedores:
# inventario del jugador, baúl del vehículo y estante).
#
# `stacks` sigue existiendo como property (los slots ocupados
# en orden) así todo el código viejo — hotbar, propiedades de
# Economia (economia.med_nat, etc.), crafteo — funciona igual
# sin saber que abajo hay una grilla. Como el drag & drop
# puede partir pilas, un mismo ítem puede vivir en varios
# slots: cantidad()/quitar() suman y drenan entre todos.
# =========================================================

# Ítems que ocupan un slot propio y no se mezclan al soltar
# uno sobre otro (la pistola es única: no hay "x2 pistolas")
NO_APILABLES = ("arma",)


class Inventario:
    """Grilla de slots [id_item, cantidad] | None. `expandible=True`
    (el inventario del jugador) agrega lugares de emergencia si la
    grilla se llena, para no perder ítems jamás; los contenedores
    (baúl, estante) rechazan el agregado cuando no hay lugar."""

    def __init__(self, columnas=5, filas=4, expandible=False):
        self.columnas = max(1, columnas)
        self.filas = filas
        self.expandible = expandible
        self.slots = [None] * (self.columnas * max(0, filas))

    # -- compatibilidad: los stacks ocupados, en orden de slot --
    @property
    def stacks(self):
        """Los slots ocupados (listas VIVAS: mutarlas muta el slot)."""
        return [s for s in self.slots if s is not None]

    def _stack(self, id_item):
        """El primer stack del ítem (puede haber más si se partió)."""
        for stack in self.slots:
            if stack is not None and stack[0] == id_item:
                return stack
        return None

    # -- grilla --
    def filas_visibles(self):
        """Filas que la UI debe dibujar (los lugares de emergencia
        del inventario expandible agregan filas extra)."""
        return -(-len(self.slots) // self.columnas)

    def indice_libre(self):
        for i, stack in enumerate(self.slots):
            if stack is None:
                return i
        return None

    def hay_lugar(self):
        return self.indice_libre() is not None

    def obtener(self, indice):
        if 0 <= indice < len(self.slots):
            return self.slots[indice]
        return None

    def redimensionar(self, columnas, filas):
        """Cambia el tamaño de la grilla reacomodando los stacks en
        los primeros lugares (se asume que entran: el que achica un
        baúl mueve el excedente antes)."""
        pendientes = self.stacks
        self.columnas = max(1, columnas)
        self.filas = filas
        self.slots = [None] * (self.columnas * max(0, filas))
        for stack in pendientes:
            indice = self.indice_libre()
            if indice is None:
                self.slots.append(None)
                indice = len(self.slots) - 1
            self.slots[indice] = stack

    # -- consultas --
    def cantidad(self, id_item):
        return sum(s[1] for s in self.slots
                   if s is not None and s[0] == id_item)

    def tiene(self, id_item, cantidad=1):
        return self.cantidad(id_item) >= cantidad

    # -- movimientos --
    def agregar(self, id_item, cantidad=1):
        """Suma al primer stack del ítem o estrena el primer slot
        libre. Devuelve True si entró (un contenedor lleno y sin
        stack del ítem rechaza; el inventario expandible nunca)."""
        if cantidad <= 0:
            return True
        stack = self._stack(id_item)
        if stack is not None and id_item not in NO_APILABLES:
            stack[1] += cantidad
            return True
        indice = self.indice_libre()
        if indice is None:
            if not self.expandible:
                return False
            self.slots.append(None)
            indice = len(self.slots) - 1
        self.slots[indice] = [id_item, cantidad]
        return True

    def quitar(self, id_item, cantidad=1):
        """Resta si alcanza, drenando entre todos los stacks del
        ítem (el slot en cero queda vacío). Devuelve True si pudo."""
        if self.cantidad(id_item) < cantidad:
            return False
        falta = cantidad
        for i, stack in enumerate(self.slots):
            if falta <= 0:
                break
            if stack is not None and stack[0] == id_item:
                saca = min(stack[1], falta)
                stack[1] -= saca
                falta -= saca
                if stack[1] <= 0:
                    self.slots[i] = None
        return True

    def fijar(self, id_item, valor):
        """Deja el TOTAL del ítem exactamente en `valor` (para las
        propiedades de Economia: `economia.med_nat = 0` confisca
        todo, incluso pilas partidas)."""
        actual = self.cantidad(id_item)
        if valor >= actual:
            self.agregar(id_item, valor - actual)
        else:
            self.quitar(id_item, actual - valor)

    # -- guardado --
    def a_dict(self):
        return {"columnas": self.columnas, "filas": self.filas,
                "slots": [list(s) if s else None for s in self.slots]}

    @classmethod
    def desde_dict(cls, datos, columnas=5, filas=4, expandible=False):
        inventario = cls(columnas, filas, expandible)
        if not datos:
            return inventario
        if isinstance(datos, dict):
            # Formato nuevo: slots con posición (respeta lo guardado)
            inventario.columnas = max(1, datos.get("columnas", columnas))
            inventario.filas = datos.get("filas", filas)
            guardados = datos.get("slots", [])
            base = inventario.columnas * max(0, inventario.filas)
            inventario.slots = [None] * max(base, len(guardados))
            for i, stack in enumerate(guardados):
                if stack and stack[1] > 0:
                    inventario.slots[i] = [stack[0], stack[1]]
        else:
            # Migración: la lista plana vieja llena los primeros
            # lugares libres en su orden original
            for id_item, cantidad in datos:
                if cantidad > 0:
                    inventario.agregar(id_item, cantidad)
        return inventario


def mover(inv_origen, idx_origen, inv_destino, idx_destino, cantidad=None):
    """El movimiento del drag & drop: intenta llevar `cantidad` (None
    = el stack entero) del slot origen al destino.
    - destino vacío → mueve
    - mismo ítem apilable → suma cantidades
    - ítem distinto (o no apilable) → intercambia, solo si se
      arrastra el stack COMPLETO (con media pila no hay swap)
    Devuelve True si algo cambió."""
    origen = inv_origen.obtener(idx_origen)
    if origen is None or not 0 <= idx_destino < len(inv_destino.slots):
        return False
    if inv_origen is inv_destino and idx_origen == idx_destino:
        return False
    total = origen[1]
    n = total if cantidad is None else min(cantidad, total)
    if n <= 0:
        return False
    destino = inv_destino.obtener(idx_destino)

    if destino is None:
        inv_destino.slots[idx_destino] = [origen[0], n]
    elif destino[0] == origen[0] and origen[0] not in NO_APILABLES:
        destino[1] += n
    elif n == total:
        inv_origen.slots[idx_origen] = destino
        inv_destino.slots[idx_destino] = origen
        return True
    else:
        return False

    origen[1] -= n
    if origen[1] <= 0:
        inv_origen.slots[idx_origen] = None
    return True
