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
from .inventory import Inventario
from .skilltree import PRODUCTOS

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
# La mercadería NO se compra hecha: se compran INSUMOS y se
# fabrica en el sótano del local (ver crafting.py).
TIEMPO_ENTREGA = 25.0            # segundos hasta que llega la caja
PEDIDOS = {
    "ing6":  ("Caja de ingredientes x6",    {"ingredientes": 6},  60),
    "ing12": ("Caja grande x12",            {"ingredientes": 12}, 110),
    "ziploc10":  ("Bolsas ziploc x10",      {"ziploc": 10},       40),
    "semillas4": ("Semillas x4",            {"semillas": 4},      70),
    "comp4": ("Compuestos químicos x4",     {"compuestos": 4},    120),
    "compant2": ("Comp. de antiviral x2",   {"comp_antiviral": 2}, 180),
    "compsue1": ("Compuesto de suero x1",   {"comp_suero": 1},     250),
}

# --- Venta ilegal: precio base por unidad en el punto ---
# La tabla sale del árbol de I+D (skilltree.PRODUCTOS): los seis
# tiers de medicamento con precios que escalan agresivo por tier.
VENTA_MED = {pid: datos["precio"] for pid, datos in PRODUCTOS.items()}
NOMBRE_MED = {pid: datos["plural"] for pid, datos in PRODUCTOS.items()}

# Nombres legibles de todos los ítems del inventario dinámico
NOMBRE_ITEM = {
    "celular": "Celular",        "arma": "Pistola",
    "balas": "Balas",            "ingredientes": "Ingredientes",
    "sanguche": "Sanguches",     "med_nat": "Med. naturales",
    "med_quim": "Med. químicos", "ziploc": "Bolsas ziploc",
    "semillas": "Semillas",      "compuestos": "Compuestos",
    "planta": "Plantas",         "quimico_crudo": "Químico crudo",
    "comp_antiviral": "Comp. de antiviral",
    "comp_suero": "Comp. de suero",
    "med_nat2": "Extractos botánicos", "med_nat3": "Panaceas",
    "med_quim2": "Antivirales",        "med_quim3": "Sueros",
    "maceta": "Maceta",  "mesa_lab": "Mesa de laboratorio",
}

# --- Vehículos (concesionaria del Playón Industrial) ---
# Un solo vehículo a la vez: comprar otro vende el actual al 50%.
# El "baúl" son lugares (stacks) EXTRA de inventario: viven en
# economia.baul y se administran desde el inventario grande (O).
# El vehículo queda ESTACIONADO en el mundo: con F te subís y
# conducís (velocidad = base × MULT_CONDUCIR × factor del modelo);
# con F de nuevo lo estacionás donde estés.
REVENTA_VEHICULO = 0.5
MULT_CONDUCIR = 1.6   # conducir es mucho más rápido que caminar
# Manejo (física de src/vehicle.py, multiplican las bases de settings):
#   acel   — qué tan rápido levanta velocidad
#   giro   — qué tan fino dobla el volante
#   agarre — 0 = agarre perfecto; cerca de 1 = patina en las curvas
VEHICULOS = {
    "moto": {
        "nombre": "Moto", "precio": 300, "baul": 0, "velocidad": 1.20,
        "desc": "+20% de velocidad · sin baúl",
        "acel": 1.25, "giro": 1.25, "agarre": 0.82,
    },
    "auto": {
        "nombre": "Auto", "precio": 700, "baul": 5, "velocidad": 1.0,
        "desc": "Baúl de 5 lugares · velocidad normal",
        "acel": 1.0, "giro": 1.0, "agarre": 0.90,
    },
    "camioneta": {
        "nombre": "Camioneta", "precio": 1400, "baul": 10, "velocidad": 0.90,
        "desc": "Baúl de 10 lugares · -10% de velocidad",
        "acel": 0.8, "giro": 0.85, "agarre": 0.94,
    },
}
# Estos no se pueden guardar en el baúl (van siempre encima)
ITEMS_SIEMPRE_ENCIMA = ("celular", "arma")

# --- Mueblería (tile Q del tileset) ---
# Los muebles comprados van al INVENTARIO como ítems: la tecla del
# hotbar (1-9) coloca el mueble en el tile al que apuntás con el
# mouse, y X frente a un mueble vacío lo levanta de vuelta. Cada
# mueble colocado cultiva/cocina con su propio timer (MuebleColocado
# en crafting.py).
MUEBLES = {
    "maceta": {
        "nombre": "Maceta", "precio": 150,
        "desc": "Cultivá plantas donde quieras — se coloca desde el hotbar",
    },
    "mesa_lab": {
        "nombre": "Mesa de laboratorio", "precio": 400,
        "desc": "Cociná químicos donde quieras — se coloca desde el hotbar",
    },
}

# Grilla del inventario del jugador (expandible: nunca pierde ítems)
GRILLA_JUGADOR = (5, 4)


def dim_baul(lugares):
    """(columnas, filas) de la grilla del baúl según sus lugares."""
    if lugares <= 0:
        return (1, 0)
    columnas = min(5, lugares)
    return (columnas, -(-lugares // columnas))

# --- Personal del local (se contrata desde la app del celular) ---
# El Mozo atiende la fila solo; el Chef cocina tandas clásicas
# tomando ingredientes del CONTENEDOR de al lado de los hornos
# (nunca del inventario de Walter). Cobran por trabajo hecho:
# el Mozo a comisión (así nunca vende a pérdida) y el Chef un
# fijo chico por tanda.
COMISION_MOZO = 0.20  # se queda este % de cada venta que atiende
SUELDO_CHEF = 6       # $ por tanda cocinada
SUELDO_REPOSITOR = 3  # $ por caja llevada al contenedor
PRECIO_MOZO = 300
PRECIO_CHEF = 450
PRECIO_REPOSITOR = 250
MAX_CONTENEDOR = 24  # límite del contenedor de ingredientes (unidades)
GRILLA_CONTENEDOR = (4, 1)  # slots visibles del contenedor del Chef

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
# La comida TIENE que dar algo de XP: el primer nodo del árbol de
# I+D cuesta 100 y sin esto no hay forma de arrancar el negocio
# (no podés vender meds sin investigar ni investigar sin vender).
PUNTOS_POR_VENTA = 1
PUNTOS_POR_RIVAL = 3
PUNTOS_POR_ESCAPE = 1

# A partir de cuánto facturado en negro los rivales te atacan
UMBRAL_AMENAZA_RIVALES = 150

# Facturación del local necesaria para que "el proveedor" te
# contacte y se desbloqueen los medicamentos en el teléfono
UMBRAL_DESBLOQUEO_MEDS = 200


def _item_inventario(id_item):
    """Propiedad respaldada por el inventario dinámico: leer devuelve
    la cantidad del stack; asignar lo fija (0 borra el stack y libera
    el lugar de la hotbar). Así `economia.med_nat -= 1` y todo el
    código existente siguen andando sobre los stacks."""
    def leer(self):
        return self.inventario.cantidad(id_item)

    def escribir(self, valor):
        self.inventario.fijar(id_item, valor)
    return property(leer, escribir)


class Economia:
    """Estado económico del jugador. Toda compra/venta pasa por acá.
    Lo que Walter lleva encima vive en `inventario` (stacks dinámicos,
    ver inventory.py); el resto (plata, banco, puntos) son campos."""

    # Ítems apilables del inventario dinámico
    ingredientes = _item_inventario("ingredientes")
    med_nat = _item_inventario("med_nat")
    med_quim = _item_inventario("med_quim")
    balas = _item_inventario("balas")
    sanguches = _item_inventario("sanguche")
    ziploc = _item_inventario("ziploc")
    semillas = _item_inventario("semillas")
    compuestos = _item_inventario("compuestos")
    planta = _item_inventario("planta")
    quimico_crudo = _item_inventario("quimico_crudo")

    def __init__(self):
        self.inventario = Inventario(*GRILLA_JUGADOR, expandible=True)
        self.inventario.agregar("celular")   # tu primer "ítem"
        self.dinero = DINERO_INICIAL
        self.ingredientes = INGREDIENTES_INICIALES
        self.producto = 0        # platos de comida listos (del local)
        self.calidad = 0.0       # calidad promedio del stock (0 a 1)
        self.tiene_pistola = False
        self.arma_equipada = False  # con pistola: alternar pistola/puños
        self.puntos = 0          # puntos de habilidad acumulados
        self.total_ilegal = 0    # facturación en negro: fama ante rivales
        self.total_comida = 0    # facturación del local: atrae al proveedor
        # Se pone en True al TERMINAR el diálogo con el Proveedor
        # (que aparece al superar UMBRAL_DESBLOQUEO_MEDS de comida)
        self.meds_desbloqueados = False
        self.receta_especial = False  # la enseña el Proveedor (1ra misión)
        # Lo depositado en el banco NO se pierde en arrestos ni
        # muertes (esas penas solo tocan el efectivo `dinero`)
        self.banco = 0
        # Vehículo activo (id de VEHICULOS o None) y su baúl:
        # un inventario aparte con lugares limitados por el modelo
        self.vehiculo = None
        self.baul = Inventario(*dim_baul(0))
        # Personal del local: si morís un empleado, se pierde la
        # contratación (hay que volver a pagarla)
        self.tiene_mozo = False
        self.tiene_chef = False
        self.tiene_repositor = False
        # El contenedor de ingredientes al lado del horno (Chef):
        # una grilla propia — `contenedor_ing` (abajo) lo expone
        # como el contador de siempre para npcs.py y el savegame
        self.contenedor = Inventario(*GRILLA_CONTENEDOR)

    # El contador histórico del contenedor: leer suma lo que hay,
    # asignar lo fija (así `economia.contenedor_ing -= 3` del Chef
    # y el campo del savegame siguen funcionando igual)
    @property
    def contenedor_ing(self):
        return self.contenedor.cantidad("ingredientes")

    @contenedor_ing.setter
    def contenedor_ing(self, valor):
        self.contenedor.fijar("ingredientes", valor)

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

    # -- vehículos y baúl --
    def velocidad_vehiculo(self):
        """Multiplicador de velocidad del vehículo equipado."""
        return VEHICULOS[self.vehiculo]["velocidad"] if self.vehiculo else 1.0

    def slots_baul(self):
        return VEHICULOS[self.vehiculo]["baul"] if self.vehiculo else 0

    def reventa_vehiculo(self):
        """Lo que paga la concesionaria por tu vehículo actual."""
        if not self.vehiculo:
            return 0
        return round(VEHICULOS[self.vehiculo]["precio"] * REVENTA_VEHICULO)

    def _achicar_baul(self, slots_nuevos):
        """Pasa a mano los stacks que no entran en el baúl nuevo
        (el inventario personal no tiene límite: siempre hay lugar).
        Devuelve cuántos stacks se movieron."""
        movidos = 0
        while len(self.baul.stacks) > slots_nuevos:
            id_item, cantidad = self.baul.stacks[-1]
            self.baul.quitar(id_item, cantidad)
            self.inventario.agregar(id_item, cantidad)
            movidos += 1
        return movidos

    def comprar_vehiculo(self, id_v):
        """Compra en la concesionaria. Solo efectivo (el banco no
        cuenta); el vehículo anterior se entrega en parte de pago
        al 50%. Devuelve (ok, mensaje)."""
        datos = VEHICULOS[id_v]
        if self.vehiculo == id_v:
            return False, f"Ya andás en {datos['nombre']}."
        reventa = self.reventa_vehiculo()
        if self.dinero + reventa < datos["precio"]:
            return False, ("No te alcanza el efectivo "
                           "(el banco no cuenta acá).")
        movidos = self._achicar_baul(datos["baul"])
        self.baul.redimensionar(*dim_baul(datos["baul"]))
        self.dinero += reventa - datos["precio"]
        anterior = self.vehiculo
        self.vehiculo = id_v
        mensaje = f"¡Ya andás en {datos['nombre']}!"
        if anterior:
            mensaje += (f" Entregaste tu "
                        f"{VEHICULOS[anterior]['nombre']} (+${reventa}).")
        if movidos:
            mensaje += f" {movidos} cosas del baúl pasaron a tu mano."
        return True, mensaje

    def vender_vehiculo(self):
        """Vende el vehículo actual al 50% y vacía su baúl a mano.
        Devuelve (ok, mensaje)."""
        if not self.vehiculo:
            return False, "No tenés vehículo para vender."
        nombre = VEHICULOS[self.vehiculo]["nombre"]
        reventa = self.reventa_vehiculo()
        movidos = self._achicar_baul(0)
        self.baul.redimensionar(*dim_baul(0))
        self.dinero += reventa
        self.vehiculo = None
        mensaje = f"Vendiste tu {nombre} por ${reventa}."
        if movidos:
            mensaje += f" El baúl se vació a tu mano ({movidos} stacks)."
        return True, mensaje

    def mover_a_baul(self, id_item):
        """Guarda el stack ENTERO en el baúl. Devuelve (ok, mensaje)."""
        if not self.vehiculo:
            return False, "No tenés vehículo con baúl."
        if id_item in ITEMS_SIEMPRE_ENCIMA:
            return False, "Eso va siempre encima."
        if self.baul._stack(id_item) is None and not self.baul.hay_lugar():
            return False, f"El baúl está lleno ({self.slots_baul()} lugares)."
        cantidad = self.inventario.cantidad(id_item)
        if not cantidad:
            return False, "No tenés eso encima."
        self.inventario.quitar(id_item, cantidad)
        self.baul.agregar(id_item, cantidad)
        return True, f"{NOMBRE_ITEM.get(id_item, id_item)} al baúl."

    def sacar_de_baul(self, id_item):
        """Trae el stack entero del baúl a la mano."""
        cantidad = self.baul.cantidad(id_item)
        if not cantidad:
            return False, "Eso no está en el baúl."
        self.baul.quitar(id_item, cantidad)
        self.inventario.agregar(id_item, cantidad)
        return True, f"{NOMBRE_ITEM.get(id_item, id_item)} a tu mano."

    def recibir_pedido(self, contenido):
        """Suma el contenido de una caja al inventario dinámico
        (cada ítem se apila o estrena su stack)."""
        for id_item, cantidad in contenido.items():
            self.inventario.agregar(id_item, cantidad)

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
        return any(self.inventario.tiene(pid) for pid in PRODUCTOS)

    def stock_med(self, tipo):
        """Stock de cualquier tier de medicamento (id de PRODUCTOS)."""
        return self.inventario.cantidad(tipo)

    def vender_trato(self, tipo, cantidad, precio_unit):
        """Cierra un trato acordado por celular: entrega hasta
        `cantidad` unidades (lo que haya en stock) al precio pactado.
        Devuelve (unidades vendidas, plata cobrada)."""
        vendidas = min(cantidad, self.stock_med(tipo))
        if vendidas <= 0:
            return 0, 0
        self.inventario.quitar(tipo, vendidas)
        cobrado = vendidas * precio_unit
        self.dinero += cobrado
        self.total_ilegal += cobrado
        # El XP escala por tier (skilltree): vender mejor
        # medicamento también acelera la investigación
        self.puntos += PRODUCTOS[tipo]["xp_venta"] * vendidas
        return vendidas, cobrado

    def es_amenaza(self):
        """True cuando los rivales ya te conocen y te atacan."""
        return self.total_ilegal >= UMBRAL_AMENAZA_RIVALES

    def _confiscar_meds(self, conservar_naturales=False):
        """Se pierde TODO medicamento encima, de cualquier tier —
        también lo escondido en el baúl del vehículo (lo revisan
        igual). Con Aceite Esencial (skilltree) los naturales
        sobreviven."""
        confiscados = 0
        for pid in PRODUCTOS:
            if conservar_naturales and PRODUCTOS[pid]["rama"] == "natural":
                continue
            confiscados += self.inventario.cantidad(pid)
            self.inventario.fijar(pid, 0)
            confiscados += self.baul.cantidad(pid)
            self.baul.fijar(pid, 0)
        return confiscados

    def arresto(self):
        """Multa + medicamentos confiscados (la comida es legal y queda).
        Devuelve (multa, meds confiscados)."""
        multa = round(self.dinero * PORCENTAJE_MULTA)
        self.dinero -= multa
        return multa, self._confiscar_meds()

    def muerte(self, arbol=None):
        """Se pierde parte del dinero y los medicamentos que llevabas
        (los naturales se salvan con Aceite Esencial).
        Devuelve (dinero perdido, meds perdidos)."""
        perdido = round(self.dinero * PORCENTAJE_PERDIDA_MUERTE)
        self.dinero -= perdido
        conservar = arbol is not None and arbol.conserva_naturales()
        return perdido, self._confiscar_meds(conservar)


class Produccion:
    """Cocinada en curso. Se inicia desde la cocina (tecla E) y avanza
    sola aunque Walter se aleje. Cada tanda recuerda su receta."""

    def __init__(self):
        self.en_curso = False
        self.progreso = 0.0  # 0 a 1
        self.receta = "clasica"
        self.del_chef = False  # quién puso esta tanda al fuego

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
        self.del_chef = False
        return True

    def iniciar_chef(self):
        """Arranca la tanda del Chef (siempre receta clásica). Los
        ingredientes ya salieron del contenedor, así que acá no se
        toca el inventario de Walter."""
        if self.en_curso:
            return False
        self.en_curso = True
        self.progreso = 0.0
        self.receta = "clasica"
        self.del_chef = True
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


# --- La Red de venta: zonas, matones y vendedores ---
# La ciudad se conquista EN ORDEN. La zona 1 (Parque del Norte) es
# libre: vendé ahí VENTAS_PARA_CONTACTO veces y "El Flaco" te pasa
# su contacto. Cada zona siguiente está custodiada por matones
# (más cuanto más lejos: ver MATONES_POR_ZONA en enemies.py) y hay
# que eliminar a TODOS los del paso para conquistarla(s). Una zona
# limpiada queda VULNERABLE: si no colocás a su vendedor antes de
# SEGUNDOS_RECONQUISTA, los matones la recuperan y se pelea de
# nuevo; con el vendedor puesto queda asegurada para siempre. Cada
# vendedor vende solo lo que le deposites (menos su comisión) y,
# con ventas suficientes, te presenta al contacto siguiente.
VENTAS_PARA_CONTACTO = 7      # ventas que destraban un contacto nuevo
COMISION_VENDEDOR = 0.25      # lo que se queda cada vendedor
INTERVALO_VENTA_RED = (45.0, 75.0)  # seg reales entre ventas de cada uno
# Tiempo de gracia de una zona limpiada: si en estos segundos no
# colocás a su vendedor, los matones la RECONQUISTAN y hay que
# pelearla de cero. Colocar al vendedor la asegura para siempre.
SEGUNDOS_RECONQUISTA = 75.0

# Pasos de conquista (índices de LUGARES_VENTA; la zona 0 es libre).
# Los grupos [5,6], [7,8] y [10,11,12] se desbloquean juntos
# (zonas 6+7, 8+9 y 11+12+13 hablando en números de mapa).
PASOS_CONQUISTA = [[1], [2], [3], [4], [5, 6], [7, 8], [9], [10, 11, 12]]

NOMBRES_VENDEDORES = ["El Flaco", "La Turca", "El Ruso", "Gaita",
                      "El Primo", "Morocho", "Santi B.", "La Piba",
                      "Don Nadie", "K.", "El Gallego", "Chino"]


class Vendedor:
    """Un dealer de la red: atado a SU zona. Vende solo lo que le
    depositás y se queda una comisión."""

    def __init__(self, zona_idx, nombre):
        self.zona_idx = zona_idx
        self.nombre = nombre
        self.descubierto = False   # ya tenés su contacto
        self.colocado = False      # ya trabaja en su zona
        # {producto: unidades} — acepta CUALQUIER tier (skilltree):
        # darle mejor mercadería multiplica lo que te reporta
        self.stock = {}
        self.ventas = 0
        self.timer = random.uniform(*INTERVALO_VENTA_RED)

    @property
    def nombre_zona(self):
        return LUGARES_VENTA[self.zona_idx][0]

    # Compatibilidad con la UI vieja (muestra N: y Q:)
    @property
    def stock_nat(self):
        return self.stock.get("med_nat", 0)

    @property
    def stock_quim(self):
        return self.stock.get("med_quim", 0)

    @property
    def stock_total(self):
        return sum(self.stock.values())

    def agregar_stock(self, producto, cantidad=1):
        self.stock[producto] = self.stock.get(producto, 0) + cantidad

    def sacar_una(self, producto):
        """Descuenta una unidad (el stack en cero desaparece)."""
        self.stock[producto] -= 1
        if self.stock[producto] <= 0:
            del self.stock[producto]

    def a_dict(self):
        return {"zona": self.zona_idx, "nombre": self.nombre,
                "descubierto": self.descubierto, "colocado": self.colocado,
                "stock": {p: n for p, n in sorted(self.stock.items()) if n > 0},
                "ventas": self.ventas}

    @classmethod
    def desde_dict(cls, datos):
        v = cls(datos["zona"], datos["nombre"])
        v.descubierto = datos.get("descubierto", False)
        v.colocado = datos.get("colocado", False)
        v.stock = {p: n for p, n in datos.get("stock", {}).items()
                   if p in PRODUCTOS and n > 0}
        # Migración de partidas viejas (contadores "nat"/"quim")
        for clave, pid in (("nat", "med_nat"), ("quim", "med_quim")):
            if datos.get(clave, 0) > 0:
                v.agregar_stock(pid, datos[clave])
        v.ventas = datos.get("ventas", 0)
        return v


class RedVentas:
    """El estado completo de la conquista de la ciudad."""

    def __init__(self):
        self.ventas_parque = 0       # tus ventas en la zona 1
        self.paso = 0                # índice del paso en disputa
        self.guardias_muertas = set()  # zonas del paso ya limpiadas
        # Estados de la reconquista:
        # - vulnerables: zona limpiada → segundos que quedan para
        #   protegerla colocando a su vendedor
        # - perdidas: zonas ya ganadas que los matones recuperaron
        #   (hay que limpiarlas otra vez)
        self.vulnerables = {}
        self.perdidas = set()
        # Operativo policial (soborno impago): mientras corra, los
        # vendedores se borran de la calle y no generan un peso
        self.clausura = 0.0
        self.vendedores = [Vendedor(i + 1, NOMBRES_VENDEDORES[i])
                           for i in range(len(NOMBRES_VENDEDORES))]

    @property
    def flaco_desbloqueado(self):
        return self.vendedores[0].descubierto

    def zonas_conquistadas(self):
        """Zonas ganadas (aunque estén vulnerables), menos las que
        los matones recuperaron."""
        return [z for p in PASOS_CONQUISTA[:self.paso] for z in p
                if z not in self.perdidas]

    def zonas_en_disputa(self):
        """Zonas con matones: las del paso actual sin limpiar más
        las que se perdieron por no protegerlas a tiempo."""
        if not self.flaco_desbloqueado:
            return []
        zonas = sorted(self.perdidas)
        if self.paso < len(PASOS_CONQUISTA):
            zonas += [z for z in PASOS_CONQUISTA[self.paso]
                      if z not in self.guardias_muertas
                      and z not in zonas]
        return zonas

    def lugares_para_tratos(self):
        """Dónde pueden proponerte tratos: el Parque + lo conquistado."""
        return [0] + self.zonas_conquistadas()

    def registrar_venta_parque(self):
        """Una venta tuya en el Parque del Norte. Devuelve "flaco" en
        la venta que desbloquea el primer contacto."""
        if self.flaco_desbloqueado:
            # El Flaco administra el Parque además del Baldío: tus
            # ventas ahí suman a su historial (destraban contactos
            # igual que las que hace él en persona)
            self.vendedores[0].ventas += 1
            return None
        self.ventas_parque += 1
        if self.ventas_parque >= VENTAS_PARA_CONTACTO:
            self.vendedores[0].descubierto = True
            return "flaco"
        return None

    def eliminar_guardia(self, zona_idx):
        """Cayó el ÚLTIMO matón de una zona: queda limpiada pero
        VULNERABLE — arranca su tiempo de gracia para colocar al
        vendedor antes de que los matones la recuperen.
        Devuelve los nombres de las zonas que pasaron a ser tuyas
        (el paso completo, o la zona recuperada); None si el paso
        sigue en disputa."""
        self.vulnerables[zona_idx] = SEGUNDOS_RECONQUISTA
        if zona_idx in self.perdidas:
            # Era una zona tuya que habían recuperado: vuelve a vos
            self.perdidas.discard(zona_idx)
            return [LUGARES_VENTA[zona_idx][0]]
        self.guardias_muertas.add(zona_idx)
        paso = PASOS_CONQUISTA[self.paso]
        if all(z in self.guardias_muertas for z in paso):
            self.paso += 1
            self.guardias_muertas = set()
            return [LUGARES_VENTA[z][0] for z in paso]
        return None

    def _perder_zona(self, zona_idx):
        """Venció la gracia sin vendedor: los matones la recuperan
        y hay que conquistarla desde cero."""
        if (self.paso < len(PASOS_CONQUISTA)
                and zona_idx in PASOS_CONQUISTA[self.paso]):
            # El paso seguía en disputa: la zona vuelve a pelearse
            self.guardias_muertas.discard(zona_idx)
        else:
            # Era parte de un paso ya completado: retrocede
            self.perdidas.add(zona_idx)

    def vendedor_de(self, zona_idx):
        return self.vendedores[zona_idx - 1] if zona_idx >= 1 else None

    def colocar(self, vendedor):
        """Lo manda a trabajar a su zona (si está conquistada).
        Con el vendedor en su puesto la zona queda ASEGURADA:
        se frena el reloj de reconquista para siempre."""
        if (not vendedor.descubierto or vendedor.colocado
                or vendedor.zona_idx not in self.zonas_conquistadas()):
            return False
        vendedor.colocado = True
        self.vulnerables.pop(vendedor.zona_idx, None)
        return True

    def deshabilitar_vendedores(self, segundos):
        """Castigo del soborno impago: los vendedores se esconden
        (sin NPCs ni ventas) hasta que pase el operativo."""
        self.clausura = max(self.clausura, segundos)

    def limpiar_inventarios(self):
        """La policía requisa TODO el stock de los vendedores.
        Devuelve cuántas unidades se perdieron."""
        requisado = 0
        for vendedor in self.vendedores:
            requisado += vendedor.stock_total
            vendedor.stock.clear()
        return requisado

    def depositar(self, vendedor, tipo, economia, cantidad=1):
        """Le dejás mercadería tuya (cualquier tier) para que la venda."""
        if economia.stock_med(tipo) < cantidad:
            return False
        economia.inventario.quitar(tipo, cantidad)
        vendedor.agregar_stock(tipo, cantidad)
        return True

    def actualizar(self, dt, economia, arbol=None):
        """Reloj de reconquista + ventas pasivas de los colocados +
        cadena de contactos. Devuelve eventos [("venta", vendedor, $),
        ("contacto", v, 0), ("perdida", v, 0)]. Con Red de
        Distribución (skilltree) la comisión baja y venden más seguido."""
        eventos = []
        # Zonas limpiadas sin proteger: se agota la gracia
        for zona_idx in list(self.vulnerables):
            self.vulnerables[zona_idx] -= dt
            if self.vulnerables[zona_idx] > 0:
                continue
            del self.vulnerables[zona_idx]
            self._perder_zona(zona_idx)
            eventos.append(("perdida", self.vendedor_de(zona_idx), 0))
        # Operativo policial: nadie vende hasta que se enfríe
        if self.clausura > 0:
            self.clausura -= dt
            if self.clausura <= 0:
                self.clausura = 0.0
                eventos.append(("reapertura", None, 0))
            return eventos
        for vendedor in self.vendedores:
            if not (vendedor.colocado and vendedor.stock_total > 0):
                continue
            vendedor.timer -= dt
            if vendedor.timer > 0:
                continue
            mult_int = arbol.mult_intervalo_red() if arbol else 1.0
            vendedor.timer = random.uniform(*INTERVALO_VENTA_RED) * mult_int
            # Vende del stack más grande (desempata por precio).
            # La ganancia escala con el tier: proveerlos con mejor
            # medicamento multiplica lo que reporta la red.
            tipo = max(vendedor.stock,
                       key=lambda p: (vendedor.stock[p], VENTA_MED[p]))
            vendedor.sacar_una(tipo)
            comision = COMISION_VENDEDOR * (
                arbol.mult_comision_red() if arbol else 1.0)
            ganancia = round(VENTA_MED[tipo] * (1 - comision))
            economia.dinero += ganancia
            economia.total_ilegal += ganancia
            vendedor.ventas += 1
            eventos.append(("venta", vendedor, ganancia))
        # El último contacto descubierto presenta al siguiente cuando
        # junta ventas suficientes (de a uno, en orden)
        for i in range(1, len(self.vendedores)):
            vendedor = self.vendedores[i]
            anterior = self.vendedores[i - 1]
            if (not vendedor.descubierto and anterior.descubierto
                    and anterior.ventas >= VENTAS_PARA_CONTACTO):
                vendedor.descubierto = True
                eventos.append(("contacto", vendedor, 0))
                break
        return eventos

    def a_dict(self):
        return {"ventas_parque": self.ventas_parque, "paso": self.paso,
                "guardias_muertas": sorted(self.guardias_muertas),
                "vulnerables": [[z, round(t, 1)]
                                for z, t in sorted(self.vulnerables.items())],
                "perdidas": sorted(self.perdidas),
                "clausura": round(self.clausura, 1),
                "vendedores": [v.a_dict() for v in self.vendedores]}

    @classmethod
    def desde_dict(cls, datos):
        red = cls()
        if not datos:
            return red
        red.ventas_parque = datos.get("ventas_parque", 0)
        red.paso = datos.get("paso", 0)
        red.guardias_muertas = set(datos.get("guardias_muertas", []))
        red.vulnerables = {z: t for z, t in datos.get("vulnerables", [])}
        red.perdidas = set(datos.get("perdidas", []))
        red.clausura = datos.get("clausura", 0.0)
        guardados = datos.get("vendedores", [])
        for i, v_datos in enumerate(guardados[:len(red.vendedores)]):
            red.vendedores[i] = Vendedor.desde_dict(v_datos)
        return red


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

    def __init__(self, reloj, lugares_permitidos=None, tipos_permitidos=None):
        self.comprador_nombre = random.choice(_NOMBRES_COMPRADOR)
        # Solo proponen encuentros en zonas que la red ya maneja
        if lugares_permitidos:
            self.lugar_idx = random.choice(lugares_permitidos)
        else:
            self.lugar_idx = random.randrange(len(LUGARES_VENTA))
        # El cliente pide del catálogo de la app Ventas
        # (AppSalesManager.pedibles): solo tiers investigados Y
        # marcados a la venta. main no crea tratos con lista vacía.
        opciones = (list(tipos_permitidos) if tipos_permitidos
                    else ["med_nat", "med_quim"])
        self.tipo = random.choice(opciones)
        self.cantidad = random.randint(2, 5)
        self.precio_unit = round(VENTA_MED[self.tipo]
                                 * random.uniform(*BONUS_TRATO))
        self.minuto_cita = reloj.en_minutos(random.randint(*MINUTOS_CITA))
        self.minuto_expira = reloj.en_minutos(
            random.randint(*MINUTOS_EXPIRA_OFERTA))
        self.estado = "oferta"
        self.vip = False   # PedidoVIP (events.py) lo pisa

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
                "estado": self.estado, "vip": self.vip}

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
