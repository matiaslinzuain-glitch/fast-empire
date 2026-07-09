# =========================================================
# FAST EMPIRE — Economía  [Fase 11]
#
# El negocio tiene dos caras:
# - LEGAL: el local de comidas. Se piden ingredientes por
#   el celular (llegan en cajas), se cocina y se atiende a
#   la fila del mostrador. Ingreso chico pero seguro.
# - ILEGAL: medicamentos (naturales y químicos). Desde la
#   Fase 11 los compradores NO aparecen de la nada: te
#   escriben al celular, acuerdan LUGAR y HORA, y a esa hora
#   te esperan en el punto. Vos decidís qué tratos aceptar.
#
# Clases: Economia (estado único), Produccion (cocinar),
# Caja (paquete entregado), Trato (venta acordada).
# =========================================================

import random

import pygame

from .settings import TILE, COLOR_CAJA, COLOR_CAJA_CINTA

# --- Balance económico (todo junto para ajustar fácil) ---
DINERO_INICIAL = 200
INGREDIENTES_INICIALES = 6
INGREDIENTES_POR_TANDA = 3       # lo que consume una cocinada clásica
UNIDADES_POR_TANDA = 4           # platos que produce
DURACION_PRODUCCION = 5.0        # segundos de cocina
CALIDAD_MINIMA = 0.60            # la receta todavía no es perfecta...
CALIDAD_MAXIMA = 0.90            # ...las habilidades la van a mejorar
PRECIO_COMIDA_BASE = 16          # por plato en el mostrador (× calidad)

# --- Recetas (la Especial se aprende cumpliendo la primera misión
# del Proveedor; su calidad >100% multiplica el precio del plato) ---
RECETAS = {
    "clasica": {
        "nombre": "Clásica",
        "ingredientes": INGREDIENTES_POR_TANDA,
        "costo_extra": 0,
        "calidad": (CALIDAD_MINIMA, CALIDAD_MAXIMA),
    },
    "especial": {
        "nombre": "Especial del Proveedor",
        "ingredientes": 5,
        "costo_extra": 15,   # las especias del puerto
        "calidad": (1.30, 1.60),
    },
}

# --- Pedidos por teléfono: (nombre, contenido, costo) ---
TIEMPO_ENTREGA = 25.0            # segundos hasta que llega la caja
PEDIDOS = {
    "ing6":  ("Caja de ingredientes x6",    {"ingredientes": 6},  60),
    "ing12": ("Caja grande x12",            {"ingredientes": 12}, 110),
    "nat3":  ("Medicamentos naturales x3",  {"med_nat": 3},       90),
    "nat6":  ("Naturales x6 (mayorista)",   {"med_nat": 6},       160),
    "quim3": ("Medicamentos químicos x3",   {"med_quim": 3},      150),
    "quim6": ("Químicos x6 (mayorista)",    {"med_quim": 6},      270),
}

# --- Venta ilegal: precio base por unidad en el punto ---
VENTA_MED = {"med_nat": 55, "med_quim": 95}
NOMBRE_MED = {"med_nat": "naturales", "med_quim": "químicos"}

# --- Armas y curación (almacén del barrio) ---
PRECIO_PISTOLA = 150
BALAS_POR_PACK = 12
PRECIO_BALAS = 30
PRECIO_SANGUCHE = 25
CURA_SANGUCHE = 30
MAX_SANGUCHES = 5      # los sanguches se guardan en el inventario
PRECIO_CURACION = 50   # la clínica del distrito sur cura al 100%

# --- Consecuencias ---
PORCENTAJE_MULTA = 0.25          # arresto: 25% del dinero + meds confiscados
PORCENTAJE_PERDIDA_MUERTE = 0.40 # muerte: 40% del dinero + meds perdidos

# --- Puntos de habilidad (el árbol llega en la Fase 5) ---
PUNTOS_POR_VENTA = 1
PUNTOS_POR_RIVAL = 5
PUNTOS_POR_ESCAPE = 2

# A partir de cuánto facturado en negro los rivales te atacan
UMBRAL_AMENAZA_RIVALES = 150

# Facturación del local necesaria para que "el proveedor" te
# contacte y se desbloqueen los medicamentos en el teléfono
UMBRAL_DESBLOQUEO_MEDS = 200


class Economia:
    """Estado económico del jugador. Toda compra/venta pasa por acá."""

    def __init__(self):
        self.dinero = DINERO_INICIAL
        self.ingredientes = INGREDIENTES_INICIALES
        self.producto = 0        # platos de comida listos
        self.calidad = 0.0       # calidad promedio del stock (0 a 1)
        self.med_nat = 0         # medicamentos naturales
        self.med_quim = 0        # medicamentos químicos
        self.tiene_pistola = False
        self.arma_equipada = False  # con pistola: alternar pistola/puños
        self.balas = 0
        self.sanguches = 0       # curación de bolsillo (inventario)
        self.puntos = 0          # puntos de habilidad acumulados
        self.total_ilegal = 0    # facturación en negro: fama ante rivales
        self.total_comida = 0    # facturación del local: atrae al proveedor
        # Se pone en True al TERMINAR el diálogo con el Proveedor
        # (que aparece al superar UMBRAL_DESBLOQUEO_MEDS de comida)
        self.meds_desbloqueados = False
        self.receta_especial = False  # la enseña el Proveedor (1ra misión)
        self.franquicias = 0     # puestos comprados (ingreso pasivo)
        # Lo depositado en el banco NO se pierde en arrestos ni
        # muertes (esas penas solo tocan el efectivo `dinero`)
        self.banco = 0

    def depositar(self, monto):
        """Mueve efectivo al banco. Devuelve cuánto entró de verdad."""
        monto = max(0, min(monto, self.dinero))
        self.dinero -= monto
        self.banco += monto
        return monto

    def retirar(self, monto):
        """Trae plata del banco al bolsillo. Devuelve cuánto salió."""
        monto = max(0, min(monto, self.banco))
        self.banco -= monto
        self.dinero += monto
        return monto

    def pagar(self, costo):
        """Descuenta si alcanza. Devuelve True si pudo pagar."""
        if self.dinero < costo:
            return False
        self.dinero -= costo
        return True

    def recibir_pedido(self, contenido):
        """Suma el contenido de una caja al inventario."""
        self.ingredientes += contenido.get("ingredientes", 0)
        self.med_nat += contenido.get("med_nat", 0)
        self.med_quim += contenido.get("med_quim", 0)

    def agregar_producto(self, unidades, calidad):
        """Suma una tanda al stock. La calidad del stock es el promedio
        ponderado entre lo que había y lo nuevo."""
        total = self.producto + unidades
        self.calidad = (self.calidad * self.producto + calidad * unidades) / total
        self.producto = total

    def vender_comida(self, mult=1.0):
        """Atiende un cliente del mostrador (legal). `mult` viene de
        las habilidades de venta. Devuelve el precio cobrado."""
        precio = max(1, round(PRECIO_COMIDA_BASE * self.calidad * mult))
        self.producto -= 1
        self.dinero += precio
        if self.producto == 0:
            self.calidad = 0.0
        self.puntos += PUNTOS_POR_VENTA
        self.total_comida += precio
        return precio

    def tiene_meds(self):
        return self.med_nat + self.med_quim > 0

    def stock_med(self, tipo):
        return self.med_nat if tipo == "med_nat" else self.med_quim

    def vender_trato(self, tipo, cantidad, precio_unit):
        """Cierra un trato acordado por celular: entrega hasta
        `cantidad` unidades (lo que haya en stock) al precio pactado.
        Devuelve (unidades vendidas, plata cobrada)."""
        vendidas = min(cantidad, self.stock_med(tipo))
        if vendidas <= 0:
            return 0, 0
        if tipo == "med_nat":
            self.med_nat -= vendidas
        else:
            self.med_quim -= vendidas
        cobrado = vendidas * precio_unit
        self.dinero += cobrado
        self.total_ilegal += cobrado
        self.puntos += PUNTOS_POR_VENTA * vendidas
        return vendidas, cobrado

    def es_amenaza(self):
        """True cuando los rivales ya te conocen y te atacan."""
        return self.total_ilegal >= UMBRAL_AMENAZA_RIVALES

    def _confiscar_meds(self):
        confiscados = self.med_nat + self.med_quim
        self.med_nat = 0
        self.med_quim = 0
        return confiscados

    def arresto(self):
        """Multa + medicamentos confiscados (la comida es legal y queda).
        Devuelve (multa, meds confiscados)."""
        multa = round(self.dinero * PORCENTAJE_MULTA)
        self.dinero -= multa
        return multa, self._confiscar_meds()

    def muerte(self):
        """Se pierde parte del dinero y los medicamentos que llevabas.
        Devuelve (dinero perdido, meds perdidos)."""
        perdido = round(self.dinero * PORCENTAJE_PERDIDA_MUERTE)
        self.dinero -= perdido
        return perdido, self._confiscar_meds()


class Produccion:
    """Cocinada en curso. Se inicia desde la cocina (tecla E) y avanza
    sola aunque Walter se aleje. Cada tanda recuerda su receta."""

    def __init__(self):
        self.en_curso = False
        self.progreso = 0.0  # 0 a 1
        self.receta = "clasica"

    def iniciar(self, economia, receta="clasica"):
        """Arranca una tanda si alcanzan los ingredientes (y la plata,
        si la receta lleva especias) y no hay otra en curso."""
        datos = RECETAS[receta]
        if self.en_curso or economia.ingredientes < datos["ingredientes"]:
            return False
        if datos["costo_extra"] and not economia.pagar(datos["costo_extra"]):
            return False
        economia.ingredientes -= datos["ingredientes"]
        self.en_curso = True
        self.progreso = 0.0
        self.receta = receta
        return True

    def actualizar(self, dt, economia, habilidades=None):
        """Avanza la cocción. Al terminar suma el producto y devuelve la
        calidad de la tanda; si no terminó nada, devuelve None.
        Las habilidades de cocina mejoran duración/calidad/cantidad."""
        if not self.en_curso:
            return None
        duracion = habilidades.duracion_produccion() if habilidades \
            else DURACION_PRODUCCION
        self.progreso += dt / duracion
        if self.progreso < 1.0:
            return None
        self.en_curso = False
        calidad_min, calidad_max = RECETAS[self.receta]["calidad"]
        if self.receta == "clasica" and habilidades:
            calidad_min = habilidades.calidad_minima()
        unidades = habilidades.unidades_por_tanda() if habilidades \
            else UNIDADES_POR_TANDA
        calidad = random.uniform(calidad_min, calidad_max)
        economia.agregar_producto(unidades, calidad)
        return calidad


class Caja:
    """Paquete entregado en la puerta del local. Se junta con E."""

    def __init__(self, x, y, contenido, nombre):
        self.rect = pygame.Rect(int(x), int(y), 22, 18)
        self.contenido = contenido
        self.nombre = nombre

    def dibujar(self, superficie, camara):
        r = camara.aplicar(self.rect)
        pygame.draw.rect(superficie, COLOR_CAJA, r)
        # Cinta de embalaje en cruz
        pygame.draw.rect(superficie, COLOR_CAJA_CINTA,
                         (r.centerx - 2, r.y, 4, r.height))
        pygame.draw.rect(superficie, COLOR_CAJA_CINTA,
                         (r.x, r.centery - 2, r.width, 4))


# --- Franquicias: territorio con ingreso pasivo ---
# Para comprar un puesto hay que eliminar al rival de esa zona y
# cerrar el trato antes de que llegue su reemplazo (60 segundos).
# Comprado el puesto, esa zona queda tuya: el rival no vuelve.
INGRESO_FRANQUICIA = 20      # $ por puesto...
INTERVALO_FRANQUICIA = 30.0  # ...cada tantos segundos

DATOS_FRANQUICIAS = [
    # (id de zona — coincide con el rival —, nombre, tile, precio)
    ("mercado", "Puesto del Mercado",    (25, 21), 400),
    ("campo",   "Parada del Campo",      (50, 24), 550),
    ("sur",     "Kiosco del Sur",        (37, 38), 700),
    ("puerto",  "Depósito del Puerto",   (40, 50), 850),
    ("feria",   "Puesto de la Feria",    (44, 62), 950),
    ("muelle",  "Depósito del Muelle",   (36, 94), 1100),
]


class Franquicia:
    """Puesto de comida comprable. Sin dueño se ve gris y cerrado;
    comprado, con toldo dorado y luz adentro."""

    def __init__(self, id_zona, nombre, tile, precio):
        self.id_zona = id_zona
        self.nombre = nombre
        self.rect = pygame.Rect(tile[0] * TILE + 2, tile[1] * TILE + 4, 28, 24)
        self.precio = precio
        self.comprada = False

    def dibujar(self, superficie, camara):
        r = camara.aplicar(self.rect)
        # Cuerpo del puesto
        pygame.draw.rect(superficie, (104, 72, 48), r)
        # Toldo: gris cerrado / dorado abierto
        toldo = (222, 178, 84) if self.comprada else (96, 96, 100)
        pygame.draw.rect(superficie, toldo, (r.x - 2, r.y - 4, r.width + 4, 8))
        # Ventanita: iluminada solo si está operando
        luz = (255, 226, 130) if self.comprada else (34, 30, 26)
        pygame.draw.rect(superficie, luz, (r.x + 8, r.y + 9, 12, 8))


def crear_franquicias():
    return [Franquicia(*datos) for datos in DATOS_FRANQUICIAS]


# --- Lugares de venta (para acordar tratos por celular) ---
# (nombre, (col, fila, ancho, alto) en tiles). Con el mapa de la
# Fase 11 hay puntos en todos los distritos.
LUGARES_VENTA = [
    ("Parque del Norte",    (19, 3, 10, 2)),
    ("Baldío del Mercado",  (18, 19, 10, 5)),
    ("Baldío Sur",          (32, 35, 10, 5)),
    ("Campo Abierto",       (47, 19, 11, 7)),
    ("Terminal Vieja",      (28, 41, 14, 2)),
    ("Puerto Sur",          (36, 48, 18, 5)),
    ("La Costanera",        (68, 12, 6, 10)),
    ("Plaza Este",          (91, 4, 12, 5)),
    ("Galería Muerta",      (91, 21, 12, 4)),
    ("Feria del Sur",       (41, 59, 24, 6)),
    ("Playón Industrial",   (12, 71, 27, 4)),
    ("Callejón del Bajo",   (88, 80, 10, 5)),
    ("Muelle Nuevo",        (30, 93, 18, 3)),
]

# Ventana del encuentro (en minutos de juego): el comprador llega
# un rato antes de la hora pactada y espera un rato después
MINUTOS_LLEGA_ANTES = 15
MINUTOS_ESPERA = 45
MINUTOS_EXPIRA_OFERTA = (45, 90)     # cuánto vive una oferta sin aceptar
MINUTOS_CITA = (120, 300)            # a cuántos minutos se pacta la cita
BONUS_TRATO = (1.15, 1.45)           # sobreprecio por venta acordada
MAX_TRATOS_ACTIVOS = 3
MAX_OFERTAS = 2

_NOMBRES_COMPRADOR = ["R.", "El Flaco", "M.", "La Turca", "Gaita",
                      "El Ruso", "Piba del sur", "Don Nadie", "K.",
                      "El Primo", "Santi B.", "Morocho"]


class Trato:
    """Una venta acordada por celular: comprador, mercadería, lugar
    y hora. Estados: oferta → aceptado → encuentro → hecho/fallido."""

    def __init__(self, reloj):
        self.comprador_nombre = random.choice(_NOMBRES_COMPRADOR)
        self.lugar_idx = random.randrange(len(LUGARES_VENTA))
        self.tipo = random.choice(("med_nat", "med_quim"))
        self.cantidad = random.randint(2, 5)
        self.precio_unit = round(VENTA_MED[self.tipo]
                                 * random.uniform(*BONUS_TRATO))
        self.minuto_cita = reloj.en_minutos(random.randint(*MINUTOS_CITA))
        self.minuto_expira = reloj.en_minutos(
            random.randint(*MINUTOS_EXPIRA_OFERTA))
        self.estado = "oferta"

    @property
    def nombre_lugar(self):
        return LUGARES_VENTA[self.lugar_idx][0]

    @property
    def rect(self):
        col, fila, ancho, alto = LUGARES_VENTA[self.lugar_idx][1]
        return pygame.Rect(col * TILE, fila * TILE, ancho * TILE, alto * TILE)

    @property
    def total(self):
        return self.cantidad * self.precio_unit

    def punto_espera(self):
        """Dónde se para el comprador a esperar (centro de la zona)."""
        return self.rect.center

    def punto_spawn(self):
        """Punto del perímetro por el que entra caminando."""
        rect = self.rect
        lado = random.randint(0, 3)
        if lado == 0:
            return random.randint(rect.left, rect.right), rect.top
        if lado == 1:
            return random.randint(rect.left, rect.right), rect.bottom
        if lado == 2:
            return rect.left, random.randint(rect.top, rect.bottom)
        return rect.right, random.randint(rect.top, rect.bottom)

    def mensaje(self, reloj):
        """El texto del chat en el celular."""
        return (f"Busco {self.cantidad} {NOMBRE_MED[self.tipo]}. "
                f"{self.nombre_lugar}, {reloj.texto_hora(self.minuto_cita)}. "
                f"Pago ${self.total}.")

    def hora_llegada(self):
        return self.minuto_cita - MINUTOS_LLEGA_ANTES

    def hora_limite(self):
        return self.minuto_cita + MINUTOS_ESPERA

    # --- guardado ---
    def a_dict(self):
        return {"comprador": self.comprador_nombre,
                "lugar": self.lugar_idx, "tipo": self.tipo,
                "cantidad": self.cantidad, "precio": self.precio_unit,
                "cita": self.minuto_cita, "expira": self.minuto_expira,
                "estado": self.estado}

    @classmethod
    def desde_dict(cls, datos, reloj):
        trato = cls(reloj)
        trato.comprador_nombre = datos["comprador"]
        trato.lugar_idx = datos["lugar"]
        trato.tipo = datos["tipo"]
        trato.cantidad = datos["cantidad"]
        trato.precio_unit = datos["precio"]
        trato.minuto_cita = datos["cita"]
        trato.minuto_expira = datos["expira"]
        # Un encuentro en curso se retoma como "aceptado": el
        # comprador vuelve a entrar apenas cargue la partida
        trato.estado = ("aceptado" if datos["estado"] == "encuentro"
                        else datos["estado"])
        return trato
