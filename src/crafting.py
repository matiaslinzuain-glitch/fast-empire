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

import random

from .inventory import Inventario

# Grilla del estante del sótano (columnas, filas)
GRILLA_ESTANTE = (5, 4)

SEGUNDOS_PLANTA = 60.0        # cuánto tarda la maceta
SEGUNDOS_LABORATORIO = 45.0   # cuánto tarda una cocinada química

# Recetas instantáneas de la mesa de trabajo, EN ORDEN de
# prioridad (si el inventario cubre varias, sale la primera:
# el mejor tier primero — la mesa arma siempre lo más caro que
# se pueda pagar). Cada entrada: (producto, {insumo: cantidad}).
# Los tiers 2 y 3 los enseña el árbol de I+D (skilltree.py).
RECETA_NATURAL = {"planta": 1, "ziploc": 1}
RECETA_QUIMICO_MESA = {"compuestos": 1, "ziploc": 1}
RECETAS_MESA = [
    ("med_nat3",  {"planta": 3, "ziploc": 2}),
    ("med_quim3", {"compuestos": 4, "ziploc": 2}),
    ("med_nat2",  {"planta": 2, "ziploc": 1}),
    ("med_quim2", {"compuestos": 2, "ziploc": 1}),
    ("med_nat",   RECETA_NATURAL),
    ("med_quim",  RECETA_QUIMICO_MESA),
]

LISTA = -1.0   # marca de "terminó: cosechalo"


class Sotano:
    """El taller subterráneo: maceta, mesa de armado, laboratorio
    y estante. Cada estación valida contra el inventario."""

    def __init__(self):
        # None = vacía · >0 = segundos restantes · LISTA = cosechar
        self.maceta = None
        self.laboratorio = None
        self.estante = Inventario(*GRILLA_ESTANTE)
        # True si el ÚLTIMO crafteo salió gratis (Cultivo Abundante /
        # Purificador de Mermas): main lo lee para el cartelito
        self.ultimo_sin_insumos = False
        # True si el último crafteo produjo unidad extra (Mezcla
        # Doble / Cristalización Fina)
        self.ultimo_doble = False
        # Qué está cocinando el lab ("med_quim" o "med_nat" con
        # Doble Faz) y si la tanda va a salir fallada
        self.lab_producto = "med_quim"
        self.lab_fallo = False

    # -- helper genérico de crafteo (verifica, resta y suma) --
    @staticmethod
    def craftear(inventario, receta, producto, cantidad=1,
                 consumir=True):
        """Si el inventario cubre la receta, la descuenta (salvo que
        una habilidad perdone los insumos: `consumir=False`) y agrega
        el producto. Devuelve True si craftéo."""
        if not all(inventario.tiene(id_item, n)
                   for id_item, n in receta.items()):
            return False
        if consumir:
            for id_item, n in receta.items():
                inventario.quitar(id_item, n)
        inventario.agregar(producto, cantidad)
        return True

    @staticmethod
    def _permitido(producto, arbol):
        """¿La partida ya sabe fabricar este producto? Sin árbol
        (partidas/llamadas legado) solo se saben los tiers 1."""
        if arbol is None:
            return producto in ("med_nat", "med_quim")
        return arbol.desbloqueado(producto)

    # -- maceta: semillas → (tiempo) → planta --
    def plantar(self, inventario, arbol=None):
        if self.maceta is not None or not inventario.quitar("semillas"):
            return False
        mult = arbol.mult_tiempo_maceta() if arbol else 1.0
        self.maceta = SEGUNDOS_PLANTA * mult
        return True

    def cosechar_maceta(self, inventario):
        if self.maceta != LISTA:
            return False
        inventario.agregar("planta")
        self.maceta = None
        return True

    # -- mesa de armado: multi-receta (al toque) --
    def proxima_receta(self, inventario, arbol=None):
        """Qué produciría la mesa con lo que hay en el inventario
        (sin craftear, solo recetas ya investigadas). Devuelve el
        id del producto o None."""
        for producto, receta in RECETAS_MESA:
            if not self._permitido(producto, arbol):
                continue
            if all(inventario.tiene(id_item, n)
                   for id_item, n in receta.items()):
                return producto
        return None

    def armar_en_mesa(self, inventario, producto=None, arbol=None):
        """Evalúa las recetas investigadas contra el inventario y
        craftea la primera cubierta (o solo `producto`, si se pide
        uno puntual). Cultivo Abundante / Purificador de Mermas
        pueden perdonar los insumos (queda en `ultimo_sin_insumos`).
        Devuelve el id del producto armado o None."""
        self.ultimo_sin_insumos = False
        self.ultimo_doble = False
        for prod, receta in RECETAS_MESA:
            if producto is not None and prod != producto:
                continue
            if not self._permitido(prod, arbol):
                continue
            gratis = (arbol is not None and
                      random.random() < arbol.prob_insumos_gratis(prod))
            doble = (arbol is not None and
                     random.random() < arbol.prob_unidad_extra(prod))
            if self.craftear(inventario, receta, prod,
                             cantidad=2 if doble else 1,
                             consumir=not gratis):
                self.ultimo_sin_insumos = gratis
                self.ultimo_doble = doble
                return prod
        return None

    def armar_natural(self, inventario, arbol=None):
        """Atajo histórico: la receta natural puntual."""
        return self.armar_en_mesa(inventario, "med_nat", arbol) == "med_nat"

    # -- laboratorio: compuestos → (tiempo) → med químico --
    # (con Doble Faz también: planta → med natural, sin ziploc)
    def iniciar_laboratorio(self, inventario, arbol=None):
        """Arranca una cocinada (si el árbol ya enseñó químicos).
        Termodinámica acelera el fuego; el Purificador puede
        perdonar el compuesto. Sin Estabilizador Térmico hay un
        riesgo de que la tanda salga fallada."""
        if self.laboratorio is not None:
            return False
        producto = None
        if (self._permitido("med_quim", arbol)
                and inventario.tiene("compuestos")):
            producto, insumo = "med_quim", "compuestos"
        elif (arbol is not None and arbol.lab_acepta_naturales()
                and inventario.tiene("planta")):
            producto, insumo = "med_nat", "planta"
        if producto is None:
            return False
        gratis = (arbol is not None and
                  random.random() < arbol.prob_insumos_gratis(producto))
        if not gratis:
            inventario.quitar(insumo)
        self.ultimo_sin_insumos = gratis
        self.lab_producto = producto
        self.lab_fallo = (arbol is not None and
                          random.random() < arbol.prob_fallo_lab())
        mult = arbol.mult_tiempo_lab() if arbol else 1.0
        self.laboratorio = SEGUNDOS_LABORATORIO * mult
        return True

    def cosechar_laboratorio(self, inventario, arbol=None):
        """Devuelve None si no había nada listo, "fallo" si la
        tanda salió mal, o el id del producto cosechado."""
        if self.laboratorio != LISTA:
            return None
        self.laboratorio = None
        if self.lab_fallo:
            self.lab_fallo = False
            return "fallo"
        producto = self.lab_producto or "med_quim"
        cantidad = 1
        if (arbol is not None and
                random.random() < arbol.prob_unidad_extra(producto)):
            cantidad = 2
        self.ultimo_doble = cantidad == 2
        inventario.agregar(producto, cantidad)
        return producto

    # -- estante: guardar / retirar de a uno --
    def guardar(self, inventario, id_item, cantidad=1):
        if not inventario.tiene(id_item, cantidad):
            return False
        if not self.estante.agregar(id_item, cantidad):
            return False   # estante lleno y sin stack del ítem
        inventario.quitar(id_item, cantidad)
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
                "lab_producto": self.lab_producto,
                "lab_fallo": self.lab_fallo,
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
        sotano.lab_producto = datos.get("lab_producto", "med_quim")
        sotano.lab_fallo = datos.get("lab_fallo", False)
        sotano.estante = Inventario.desde_dict(datos.get("estante"),
                                               *GRILLA_ESTANTE)
        return sotano


class MuebleColocado:
    """Una maceta o mesa de laboratorio comprada en la mueblería y
    colocada en el mundo (main.py la coloca con la tecla del hotbar
    y la levanta con X). A diferencia de las estaciones fijas del
    sótano, cada mueble lleva SU PROPIO timer: varias macetas
    cultivan en paralelo. La lógica replica a la del Sotano, con
    los mismos efectos del árbol de I+D (Fertilizante, Doble Faz,
    Estabilizador Térmico, unidad extra, insumos gratis):
      maceta   → semillas → (tiempo) → planta
      mesa_lab → compuestos → (tiempo) → med. químico
                 (con Doble Faz también planta → med. natural)
    """

    def __init__(self, tipo, col, fila, timer=None):
        self.tipo = tipo          # "maceta" | "mesa_lab"
        self.col = col            # posición en tiles del mapa
        self.fila = fila
        self.timer = timer        # None = vacío · >0 = falta · LISTA
        self.producto = "med_quim"  # qué cocina la mesa_lab
        self.fallo = False          # la tanda va a salir arruinada
        self.ultimo_sin_insumos = False
        self.ultimo_doble = False

    @property
    def ocupado(self):
        """True si tiene trabajo en marcha o algo sin cosechar (no
        se puede levantar con X en ese estado)."""
        return self.timer is not None

    @property
    def total(self):
        """Duración total del ciclo (para la barrita de progreso)."""
        return (SEGUNDOS_PLANTA if self.tipo == "maceta"
                else SEGUNDOS_LABORATORIO)

    # -- ciclo de la maceta --
    def plantar(self, inventario, arbol=None):
        """Como Sotano.plantar: Fertilizante acorta el cultivo."""
        if self.timer is not None or not inventario.quitar("semillas"):
            return False
        mult = arbol.mult_tiempo_maceta() if arbol else 1.0
        self.timer = SEGUNDOS_PLANTA * mult
        return True

    def cosechar_planta(self, inventario):
        if self.timer != LISTA:
            return False
        inventario.agregar("planta")
        self.timer = None
        return True

    # -- ciclo de la mesa de laboratorio --
    def iniciar_cocinada(self, inventario, arbol=None):
        """Como Sotano.iniciar_laboratorio, sobre el timer propio:
        compuestos → químico (o planta → natural con Doble Faz);
        sin Estabilizador Térmico la tanda puede salir fallada."""
        if self.timer is not None:
            return False
        producto = None
        if ((arbol is None or arbol.desbloqueado("med_quim"))
                and inventario.tiene("compuestos")):
            producto, insumo = "med_quim", "compuestos"
        elif (arbol is not None and arbol.lab_acepta_naturales()
                and inventario.tiene("planta")):
            producto, insumo = "med_nat", "planta"
        if producto is None:
            return False
        gratis = (arbol is not None and
                  random.random() < arbol.prob_insumos_gratis(producto))
        if not gratis:
            inventario.quitar(insumo)
        self.ultimo_sin_insumos = gratis
        self.producto = producto
        self.fallo = (arbol is not None and
                      random.random() < arbol.prob_fallo_lab())
        mult = arbol.mult_tiempo_lab() if arbol else 1.0
        self.timer = SEGUNDOS_LABORATORIO * mult
        return True

    def retirar_producto(self, inventario, arbol=None):
        """Como Sotano.cosechar_laboratorio: None si no hay nada
        listo, "fallo" si la tanda salió mal, o el id cosechado."""
        if self.timer != LISTA:
            return None
        self.timer = None
        if self.fallo:
            self.fallo = False
            return "fallo"
        producto = self.producto or "med_quim"
        cantidad = 1
        if (arbol is not None and
                random.random() < arbol.prob_unidad_extra(producto)):
            cantidad = 2
        self.ultimo_doble = cantidad == 2
        inventario.agregar(producto, cantidad)
        return producto

    # -- reloj (corre en main junto con el del sótano) --
    def actualizar(self, dt):
        """Devuelve "planta_lista"/"quimico_listo" al terminar, o None."""
        if self.timer is None or self.timer == LISTA:
            return None
        self.timer -= dt
        if self.timer > 0:
            return None
        self.timer = LISTA
        return "planta_lista" if self.tipo == "maceta" else "quimico_listo"

    # -- guardado --
    def a_dict(self):
        return {"tipo": self.tipo, "col": self.col, "fila": self.fila,
                "timer": "lista" if self.timer == LISTA else self.timer,
                "producto": self.producto, "fallo": self.fallo}

    @classmethod
    def desde_dict(cls, datos):
        timer = datos.get("timer")
        mueble = cls(datos["tipo"], datos["col"], datos["fila"],
                     LISTA if timer == "lista" else timer)
        mueble.producto = datos.get("producto", "med_quim")
        mueble.fallo = datos.get("fallo", False)
        return mueble
