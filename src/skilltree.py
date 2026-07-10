# =========================================================
# FAST EMPIRE — Árbol de I+D de medicamentos + App Ventas  [Fase 15]
#
# El árbol NUEVO (no confundir con skills.py, el viejo de
# cocina/combate): una constelación que nace de un centro y
# se abre en dos ramas — NATURAL (izquierda) y SINTÉTICA
# (derecha). Cada rama tiene un TRONCO de tres tiers de
# medicamento (T1 → T2 → T3, en orden) y RAMAS CORTAS que
# cuelgan del tronco: callejones sin salida con mejoras
# utilitarias. El dilema: ¿avanzo al próximo tier o abarato
# el que ya tengo?
#
# El coste en XP (los puntos de habilidad de siempre) crece
# EXPONENCIAL con la profundidad del nodo:
#
#     coste(n) = COSTE_BASE * MULT_EXPONENCIAL ** (prof - 1)
#
# con base 100 y ×2.5: prof 1 → 100 XP, prof 2 → 250,
# prof 3 → 625. Las ramas cortas cuelgan un nivel más
# profundo que su padre, así que compiten en precio con el
# siguiente tier del tronco (ahí está el dilema).
#
# AppSalesManager es la app "Ventas" del celular: casillas
# para marcar qué tiers están A LA VENTA. Los NPCs que
# escriben al celular solo piden lo marcado (¿sin stock de
# T2? lo apagás y te vuelven a pedir T1). Todo producto
# recién desbloqueado arranca a la venta (se guarda el set
# de APAGADOS, no el de prendidos).
#
# El resto del juego pregunta acá (desbloqueado(),
# mult_precio(), pedibles()...) en vez de usar constantes
# crudas, igual que hace con skills.Habilidades.
# =========================================================

# --- Curva de coste (el rebalanceo vive en estas dos líneas) ---
COSTE_BASE = 100          # XP del primer nodo de cada tronco
MULT_EXPONENCIAL = 2.5    # crecimiento por nivel de profundidad


def coste_nodo(profundidad):
    """Coste_Nodo(n) = Coste_Base * Mult ** (profundidad - 1)."""
    return round(COSTE_BASE * MULT_EXPONENCIAL ** (profundidad - 1))


# --- Los seis productos (T1 = los meds que ya existían) ---
# "precio" es la venta base por unidad: escala AGRESIVO por
# tier (~×2.7) — mejor medicamento, mucho mejor negocio.
# "xp_venta" es cuántos puntos deja cada unidad vendida (sin
# esto, grindear 625 XP a 1 punto por venta sería eterno).
PRODUCTOS = {
    "med_nat": {
        "nombre": "Tintura de Hierbas", "plural": "naturales",
        "rama": "natural", "tier": 1, "precio": 55, "xp_venta": 5,
    },
    "med_nat2": {
        "nombre": "Extracto Botánico", "plural": "extractos botánicos",
        "rama": "natural", "tier": 2, "precio": 150, "xp_venta": 14,
    },
    "med_nat3": {
        "nombre": "Panacea Orgánica", "plural": "panaceas",
        "rama": "natural", "tier": 3, "precio": 420, "xp_venta": 40,
    },
    "med_quim": {
        "nombre": "Analgésico Sintético", "plural": "químicos",
        "rama": "sintetico", "tier": 1, "precio": 95, "xp_venta": 9,
    },
    "med_quim2": {
        "nombre": "Antiviral Complejo", "plural": "antivirales",
        "rama": "sintetico", "tier": 2, "precio": 260, "xp_venta": 24,
    },
    "med_quim3": {
        "nombre": "Suero Experimental", "plural": "sueros",
        "rama": "sintetico", "tier": 3, "precio": 700, "xp_venta": 65,
    },
}


def precio_venta(producto):
    return PRODUCTOS[producto]["precio"]


def xp_por_venta(producto):
    return PRODUCTOS[producto]["xp_venta"]


class SkillNode:
    """Un nodo de la constelación: identidad, posición (x, y)
    relativa al centro, jerarquía (padres) y qué hace. El estado
    (comprado o no) NO vive acá: lo lleva SkillTree por partida,
    así todos los saves comparten estas definiciones."""

    def __init__(self, id_nodo, nombre, desc, rama, tipo,
                 profundidad, pos, padres=(), desbloquea=None):
        self.id = id_nodo
        self.nombre = nombre
        self.desc = desc
        self.rama = rama                # "natural" | "sintetico"
        self.tipo = tipo                # "tronco" | "rama_corta"
        self.profundidad = profundidad  # nivel para la fórmula de coste
        self.pos = pos                  # (x, y) relativos al centro
        self.padres = tuple(padres)     # ids que deben estar comprados
        self.desbloquea = desbloquea    # id de PRODUCTOS o None

    @property
    def coste(self):
        return coste_nodo(self.profundidad)


# La constelación completa. Coordenadas en unidades abstractas
# alrededor del centro (0, 0): la pantalla del árbol las escala.
# Rama natural hacia la izquierda, sintética hacia la derecha;
# las ramas cortas cuelgan hacia abajo (callejones sin salida).
NODOS = {n.id: n for n in [
    # ── Rama A: medicamentos naturales ─────────────────────
    SkillNode(
        "nat_t1", "Tintura de Hierbas Básica",
        "Desbloquea la receta del medicamento natural Tier 1 "
        "en la mesa del sótano.",
        "natural", "tronco", 1, (-150, -30),
        padres=(), desbloquea="med_nat"),
    SkillNode(
        "nat_a1", "Cultivo Abundante",
        "Aprovechás cada planta: 20% de probabilidad de no "
        "consumir insumos al craftear naturales.",
        "natural", "rama_corta", 2, (-230, 110),
        padres=("nat_t1",)),
    SkillNode(
        "nat_t2", "Extracto Botánico Purificado",
        "Desbloquea el medicamento natural Tier 2: el Extracto "
        "Botánico. Se paga casi el triple que la tintura.",
        "natural", "tronco", 2, (-300, -90),
        padres=("nat_t1",), desbloquea="med_nat2"),
    SkillNode(
        "nat_a2", "Empaque Ecológico",
        "Presentación premium: la venta directa de naturales "
        "T1 y T2 se cobra un 15% más cara.",
        "natural", "rama_corta", 3, (-430, 20),
        padres=("nat_t2",)),
    SkillNode(
        "nat_t3", "Panacea Orgánica",
        "Desbloquea el medicamento natural Tier 3: la Panacea. "
        "La joya verde del catálogo.",
        "natural", "tronco", 3, (-450, -170),
        padres=("nat_t2",), desbloquea="med_nat3"),

    # ── Rama B: medicamentos sintéticos ─────────────────────
    SkillNode(
        "quim_t1", "Analgésico Sintético Base",
        "Desbloquea la receta del medicamento químico Tier 1 "
        "en la mesa y el laboratorio del sótano.",
        "sintetico", "tronco", 1, (150, -30),
        padres=(), desbloquea="med_quim"),
    SkillNode(
        "quim_b1", "Termodinámica",
        "Control fino de temperatura: el laboratorio cocina "
        "sintéticos un 40% más rápido.",
        "sintetico", "rama_corta", 2, (230, 110),
        padres=("quim_t1",)),
    SkillNode(
        "quim_t2", "Antiviral Complejo",
        "Desbloquea el medicamento químico Tier 2: el Antiviral. "
        "Química seria, plata seria.",
        "sintetico", "tronco", 2, (300, -90),
        padres=("quim_t1",), desbloquea="med_quim2"),
    SkillNode(
        "quim_b2", "Purificador de Mermas",
        "Recuperás lo que otros tiran: 25% de probabilidad de "
        "no consumir insumos al craftear sintéticos.",
        "sintetico", "rama_corta", 3, (430, 20),
        padres=("quim_t2",)),
    SkillNode(
        "quim_t3", "Suero Sintético Experimental",
        "Desbloquea el medicamento químico Tier 3: el Suero. "
        "Lo más caro y difícil de fabricar del juego.",
        "sintetico", "tronco", 3, (450, -170),
        padres=("quim_t2",), desbloquea="med_quim3"),
]}

# Orden estable para listados (app Ventas, hover, catálogos):
# primero naturales por tier, después sintéticos por tier.
_ORDEN_PRODUCTOS = sorted(
    PRODUCTOS, key=lambda p: (PRODUCTOS[p]["rama"], PRODUCTOS[p]["tier"]))


class SkillTree:
    """El estado del árbol en UNA partida: qué nodos se compraron.
    Valida jerarquía (todos los padres comprados) y cobra el coste
    exponencial en puntos de habilidad (XP) de la economía."""

    def __init__(self):
        self.comprados = set()   # ids de NODOS comprados

    # ── consulta de nodos ───────────────────────────────────
    def nodo(self, id_nodo):
        return NODOS[id_nodo]

    def tiene(self, id_nodo):
        return id_nodo in self.comprados

    def estado(self, id_nodo):
        """"comprado" | "disponible" | "bloqueado" (faltan padres)."""
        nodo = NODOS[id_nodo]
        if nodo.id in self.comprados:
            return "comprado"
        if all(p in self.comprados for p in nodo.padres):
            return "disponible"
        return "bloqueado"

    def comprar(self, id_nodo, economia):
        """Intenta comprar el nodo con los puntos de habilidad.
        Devuelve (ok, mensaje) — el mensaje va directo a la UI."""
        nodo = NODOS[id_nodo]
        estado = self.estado(id_nodo)
        if estado == "comprado":
            return False, "Ya investigaste ese nodo."
        if estado == "bloqueado":
            faltan = [NODOS[p].nombre for p in nodo.padres
                      if p not in self.comprados]
            return False, f"Primero investigá: {', '.join(faltan)}."
        if economia.puntos < nodo.coste:
            return False, (f"Te falta XP "
                           f"({economia.puntos}/{nodo.coste}).")
        economia.puntos -= nodo.coste
        self.comprados.add(nodo.id)
        return True, f"¡{nodo.nombre} investigado!"

    # ── qué medicamentos existen para esta partida ──────────
    def desbloqueado(self, producto):
        """¿Ya se investigó el nodo que enseña este medicamento?"""
        return any(NODOS[i].desbloquea == producto
                   for i in self.comprados)

    def productos_desbloqueados(self):
        """Ids de PRODUCTOS ya investigados, en orden de catálogo."""
        abiertos = {NODOS[i].desbloquea for i in self.comprados
                    if NODOS[i].desbloquea}
        return [p for p in _ORDEN_PRODUCTOS if p in abiertos]

    # ── efectos de las ramas cortas (el juego pregunta acá) ──
    def prob_insumos_gratis(self, producto):
        """Probabilidad de que un crafteo no consuma insumos:
        Cultivo Abundante (naturales) / Purificador (sintéticos)."""
        rama = PRODUCTOS[producto]["rama"]
        if rama == "natural" and self.tiene("nat_a1"):
            return 0.20
        if rama == "sintetico" and self.tiene("quim_b2"):
            return 0.25
        return 0.0

    def mult_precio(self, producto):
        """Empaque Ecológico: +15% en venta directa de nat T1/T2."""
        datos = PRODUCTOS[producto]
        if (self.tiene("nat_a2") and datos["rama"] == "natural"
                and datos["tier"] <= 2):
            return 1.15
        return 1.0

    def mult_tiempo_lab(self):
        """Termodinámica: el laboratorio tarda un 40% menos."""
        return 0.6 if self.tiene("quim_b1") else 1.0

    # ── guardado ─────────────────────────────────────────────
    def a_dict(self):
        return sorted(self.comprados)

    @classmethod
    def desde_dict(cls, datos):
        arbol = cls()
        arbol.comprados = {i for i in (datos or []) if i in NODOS}
        return arbol


class AppSalesManager:
    """La app 'Ventas' del celular: qué medicamentos están A LA
    VENTA. Los clientes que escriben (Trato) solo piden de esta
    lista. Se guarda el set de APAGADOS: así todo producto recién
    investigado arranca prendido sin pasos extra."""

    def __init__(self):
        self.apagados = set()   # ids de PRODUCTOS retirados de la venta

    def en_venta(self, producto, arbol):
        return arbol.desbloqueado(producto) and producto not in self.apagados

    def alternar(self, producto, arbol):
        """El toggle de la casilla. Devuelve el estado nuevo, o None
        si el producto ni siquiera está investigado."""
        if not arbol.desbloqueado(producto):
            return None
        if producto in self.apagados:
            self.apagados.discard(producto)
            return True
        self.apagados.add(producto)
        return False

    def pedibles(self, arbol):
        """Lo que los NPCs pueden pedir por celular: investigado Y
        marcado a la venta. Si vuelve vacío, main no genera ofertas
        (nadie te escribe por un catálogo cerrado)."""
        return [p for p in arbol.productos_desbloqueados()
                if p not in self.apagados]

    def catalogo(self, arbol):
        """Para dibujar la app: [(producto, a_la_venta), ...] de
        todo lo ya investigado."""
        return [(p, p not in self.apagados)
                for p in arbol.productos_desbloqueados()]

    # ── guardado ─────────────────────────────────────────────
    def a_dict(self):
        return sorted(self.apagados)

    @classmethod
    def desde_dict(cls, datos):
        app = cls()
        app.apagados = {p for p in (datos or []) if p in PRODUCTOS}
        return app
