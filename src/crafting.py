# =========================================================
# FAST EMPIRE — El sótano: crafteo de mercadería  [Fase 14]
#
# La tienda ya no vende medicamentos hechos: vende INSUMOS
# (bolsas ziploc, semillas y compuestos químicos) y Walter
# fabrica en el sótano del local (bajada con E):
#
#   [semillas]   → maceta, esperar    → [planta]
#   MESA DE ARMADO (multi-receta, al toque):
#     [planta] + [ziploc]     → [med. natural]
#     [compuestos] + [ziploc] → [med. químico]
#   [compuestos] → laboratorio, esperar → [med. químico]
#   (el laboratorio no gasta ziploc pero lleva su tiempo: la
#   mesa es la vía rápida, el laboratorio la vía barata)
#
# También hay un ESTANTE para guardar lo que no quieras
# llevar encima (lo guardado no se pierde en arrestos).
#
# La clase Sotano es el "CraftingManager": verifica insumos
# en el inventario, los resta y suma el producto. Los timers
# de maceta y laboratorio siguen corriendo mientras jugás.
# =========================================================

from .inventory import Inventario

SEGUNDOS_PLANTA = 60.0        # cuánto tarda la maceta
SEGUNDOS_LABORATORIO = 45.0   # cuánto tarda una cocinada química

# Recetas instantáneas de la mesa de trabajo, EN ORDEN de
# prioridad (si el inventario cubre varias, sale la primera).
# Cada entrada: (producto, {insumo: cantidad})
RECETA_NATURAL = {"planta": 1, "ziploc": 1}
RECETA_QUIMICO_MESA = {"compuestos": 1, "ziploc": 1}
RECETAS_MESA = [
    ("med_nat",  RECETA_NATURAL),
    ("med_quim", RECETA_QUIMICO_MESA),
]

LISTA = -1.0   # marca de "terminó: cosechalo"


class Sotano:
    """El taller subterráneo: maceta, mesa de armado, laboratorio
    y estante. Cada estación valida contra el inventario."""

    def __init__(self):
        # None = vacía · >0 = segundos restantes · LISTA = cosechar
        self.maceta = None
        self.laboratorio = None
        self.estante = Inventario()

    # -- helper genérico de crafteo (verifica, resta y suma) --
    @staticmethod
    def craftear(inventario, receta, producto, cantidad=1):
        """Si el inventario cubre la receta, la descuenta y agrega
        el producto. Devuelve True si craftéo."""
        if not all(inventario.tiene(id_item, n)
                   for id_item, n in receta.items()):
            return False
        for id_item, n in receta.items():
            inventario.quitar(id_item, n)
        inventario.agregar(producto, cantidad)
        return True

    # -- maceta: semillas → (tiempo) → planta --
    def plantar(self, inventario):
        if self.maceta is not None or not inventario.quitar("semillas"):
            return False
        self.maceta = SEGUNDOS_PLANTA
        return True

    def cosechar_maceta(self, inventario):
        if self.maceta != LISTA:
            return False
        inventario.agregar("planta")
        self.maceta = None
        return True

    # -- mesa de armado: multi-receta (al toque) --
    def proxima_receta(self, inventario):
        """Qué produciría la mesa con lo que hay en el inventario
        (sin craftear). Devuelve el id del producto o None."""
        for producto, receta in RECETAS_MESA:
            if all(inventario.tiene(id_item, n)
                   for id_item, n in receta.items()):
                return producto
        return None

    def armar_en_mesa(self, inventario, producto=None):
        """Evalúa las recetas de la mesa contra el inventario y
        craftea la primera cubierta (o solo `producto`, si se pide
        uno puntual). Devuelve el id del producto armado o None."""
        for prod, receta in RECETAS_MESA:
            if producto is not None and prod != producto:
                continue
            if self.craftear(inventario, receta, prod):
                return prod
        return None

    def armar_natural(self, inventario):
        """Atajo histórico: la receta natural puntual."""
        return self.armar_en_mesa(inventario, "med_nat") == "med_nat"

    # -- laboratorio: compuestos → (tiempo) → med químico --
    def iniciar_laboratorio(self, inventario):
        if (self.laboratorio is not None
                or not inventario.quitar("compuestos")):
            return False
        self.laboratorio = SEGUNDOS_LABORATORIO
        return True

    def cosechar_laboratorio(self, inventario):
        if self.laboratorio != LISTA:
            return False
        inventario.agregar("med_quim")
        self.laboratorio = None
        return True

    # -- estante: guardar / retirar de a uno --
    def guardar(self, inventario, id_item, cantidad=1):
        if not inventario.quitar(id_item, cantidad):
            return False
        self.estante.agregar(id_item, cantidad)
        return True

    def retirar(self, inventario, id_item, cantidad=1):
        if not self.estante.quitar(id_item, cantidad):
            return False
        inventario.agregar(id_item, cantidad)
        return True

    # -- reloj (corre en main mientras jugás) --
    def actualizar(self, dt):
        """Devuelve eventos: ["planta_lista"] y/o ["quimico_listo"]."""
        eventos = []
        if self.maceta is not None and self.maceta != LISTA:
            self.maceta -= dt
            if self.maceta <= 0:
                self.maceta = LISTA
                eventos.append("planta_lista")
        if self.laboratorio is not None and self.laboratorio != LISTA:
            self.laboratorio -= dt
            if self.laboratorio <= 0:
                self.laboratorio = LISTA
                eventos.append("quimico_listo")
        return eventos

    # -- guardado --
    def a_dict(self):
        def timer(valor):
            return "lista" if valor == LISTA else valor
        return {"maceta": timer(self.maceta),
                "laboratorio": timer(self.laboratorio),
                "estante": self.estante.a_dict()}

    @classmethod
    def desde_dict(cls, datos):
        sotano = cls()
        if not datos:
            return sotano

        def timer(valor):
            return LISTA if valor == "lista" else valor
        sotano.maceta = timer(datos.get("maceta"))
        sotano.laboratorio = timer(datos.get("laboratorio"))
        sotano.estante = Inventario.desde_dict(datos.get("estante"))
        return sotano
