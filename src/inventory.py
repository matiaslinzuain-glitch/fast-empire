# =========================================================
# FAST EMPIRE — Inventario dinámico  [Fase 14]
#
# Nada de slots fijos: el inventario es una lista de STACKS
# que se llena de izquierda a derecha en el orden en que
# recogés las cosas. Los ítems idénticos se apilan en un
# solo stack (la hotbar muestra "x10" en la esquina) y al
# quedar en cero el stack desaparece y libera el lugar.
#
# La Economia expone propiedades (economia.med_nat, etc.)
# que leen y escriben acá, así todo el código viejo sigue
# funcionando sin saber que abajo hay stacks.
# =========================================================


class Inventario:
    """Lista dinámica de stacks [id_item, cantidad], en orden de
    llegada. Un ítem = un stack, sin límite de apilado."""

    def __init__(self):
        self.stacks = []   # [[id_item, cantidad], ...]

    def _stack(self, id_item):
        for stack in self.stacks:
            if stack[0] == id_item:
                return stack
        return None

    # -- consultas --
    def cantidad(self, id_item):
        stack = self._stack(id_item)
        return stack[1] if stack else 0

    def tiene(self, id_item, cantidad=1):
        return self.cantidad(id_item) >= cantidad

    # -- movimientos --
    def agregar(self, id_item, cantidad=1):
        """Suma al stack del ítem; si no existía, ocupa el próximo
        lugar libre (se agrega al final, de izquierda a derecha)."""
        if cantidad <= 0:
            return
        stack = self._stack(id_item)
        if stack is not None:
            stack[1] += cantidad
        else:
            self.stacks.append([id_item, cantidad])

    def quitar(self, id_item, cantidad=1):
        """Resta si alcanza. El stack en cero desaparece y libera
        su lugar. Devuelve True si pudo."""
        stack = self._stack(id_item)
        if stack is None or stack[1] < cantidad:
            return False
        stack[1] -= cantidad
        if stack[1] <= 0:
            self.stacks.remove(stack)
        return True

    def fijar(self, id_item, valor):
        """Deja el stack exactamente en `valor` (para las propiedades
        de Economia: `economia.med_nat = 0` confisca todo)."""
        stack = self._stack(id_item)
        if valor <= 0:
            if stack is not None:
                self.stacks.remove(stack)
        elif stack is not None:
            stack[1] = valor
        else:
            self.stacks.append([id_item, valor])

    # -- guardado --
    def a_dict(self):
        return [[id_item, cantidad] for id_item, cantidad in self.stacks]

    @classmethod
    def desde_dict(cls, datos):
        inventario = cls()
        for id_item, cantidad in (datos or []):
            if cantidad > 0:
                inventario.stacks.append([id_item, cantidad])
        return inventario
