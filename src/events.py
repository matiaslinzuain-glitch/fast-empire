# =========================================================
# FAST EMPIRE — Eventos del jefe  [Fase 13]
#
# Con El Flaco desbloqueado, Walter deja el menudeo: las
# ventas de calle las hacen los vendedores de la Red. Su
# celular pasa a recibir EVENTOS de jefe, que genera el
# GestorEventos con un cooldown por tipo:
#
# - PedidoVIP (frecuente): un pesado quiere MUCHA mercadería
#   de una, paga sobreprecio, no acepta entregas parciales,
#   espera poco… y a veces la cita es una emboscada.
# - EventoFlash (raro): un contacto liquida un cargamento
#   baratísimo en los muelles por tiempo real limitado. Hay
#   que correr hasta el punto antes de que se esfume.
# - EventoSoborno (raro): la policía exige su tajada por
#   dejar operar la Red. Es UN pago global pero exponencial
#   en la cantidad de zonas controladas. No pagar = operativo:
#   los vendedores desaparecen un rato y pierden TODO el
#   stock que tenían encima.
# =========================================================

import random

from .economy import (
    Trato, LUGARES_VENTA, VENTA_MED, NOMBRE_MED, PEDIDOS,
    MAX_TRATOS_ACTIVOS,
)

# --- Balance de los eventos (todo junto para ajustar fácil) ---
FREC_VIP = (60.0, 110.0)        # seg reales entre pedidos VIP
FREC_FLASH = (240.0, 420.0)     # seg reales entre ofertas flash
FREC_SOBORNO = (300.0, 480.0)   # seg reales entre aprietes policiales

# Pedido VIP
VIP_CANTIDAD = (8, 14)
VIP_BONUS = (1.6, 2.1)          # sobreprecio sobre VENTA_MED
VIP_MINUTOS_CITA = (60, 150)    # el pesado no da cita para mañana
VIP_MINUTOS_ESPERA = 15         # …ni te espera: ventana estricta
PROB_EMBOSCADA = 0.35           # chance de que la cita sea una trampa
EMBOSCADORES = 2                # cuántos matones te saltan encima

# Oferta flash (por unidad sale ~la mitad que el pedido mayorista)
ZONAS_FLASH = [4, 5, 12]        # Terminal Vieja, Puerto Sur, Muelle Nuevo
FLASH_CANTIDAD = (9, 15)
FLASH_DESCUENTO = 0.55          # fracción del costo mayorista por unidad
SEGUNDOS_FLASH = (90.0, 150.0)  # tiempo real para llegar al punto

# Soborno policial: costo = BASE * FACTOR ** zonas_controladas
SOBORNO_BASE = 60
SOBORNO_FACTOR = 1.45
SEGUNDOS_SOBORNO = 150.0        # tiempo real para pagar
SEGUNDOS_CLAUSURA = 90.0        # cuánto dura el operativo si no pagás

# Costo de fabricar una unidad con insumos de la tienda (la flash
# liquida mercadería YA HECHA: te ahorra insumos y horas de sótano)
_COSTO_UNIT = {
    "med_nat": (PEDIDOS["semillas4"][2] / 4
                + PEDIDOS["ziploc10"][2] / 10),
    "med_quim": PEDIDOS["comp4"][2] / 4,
}


def calcular_soborno(zonas_controladas):
    """La tajada policial crece EXPONENCIALMENTE con tu imperio."""
    monto = SOBORNO_BASE * SOBORNO_FACTOR ** zonas_controladas
    return int(round(monto / 10) * 10)


class PedidoVIP(Trato):
    """Un pedido al por mayor: mismo circuito que un trato común
    (aceptar → cita → entregar con E) pero en grande. Todo o nada,
    ventana corta y riesgo de emboscada al cobrar."""

    def __init__(self, reloj, lugares_permitidos=None):
        super().__init__(reloj, lugares_permitidos)
        self.vip = True
        self.cantidad = random.randint(*VIP_CANTIDAD)
        self.precio_unit = round(VENTA_MED[self.tipo]
                                 * random.uniform(*VIP_BONUS))
        self.minuto_cita = reloj.en_minutos(
            random.randint(*VIP_MINUTOS_CITA))

    def hora_limite(self):
        return self.minuto_cita + VIP_MINUTOS_ESPERA

    def mensaje(self, reloj):
        return (f"PEDIDO GRANDE: {self.cantidad} {NOMBRE_MED[self.tipo]}"
                f" JUNTOS. {self.nombre_lugar}, "
                f"{reloj.texto_hora(self.minuto_cita)} EN PUNTO. "
                f"Pago ${self.total}. Sin vueltas.")


class EventoFlash:
    """Un cargamento a precio de liquidación esperando en el muelle.
    Timer REAL: si no llegás antes, se lo lleva otro."""

    tipo_evento = "flash"

    def __init__(self):
        self.zona_idx = random.choice(ZONAS_FLASH)
        self.tipo = random.choice(("med_nat", "med_quim"))
        self.cantidad = random.randint(*FLASH_CANTIDAD)
        self.precio_total = int(round(
            self.cantidad * _COSTO_UNIT[self.tipo] * FLASH_DESCUENTO))
        self.timer = random.uniform(*SEGUNDOS_FLASH)

    @property
    def nombre_zona(self):
        return LUGARES_VENTA[self.zona_idx][0]

    def punto(self):
        """Dónde espera el contacto (centro de la zona, en píxeles)."""
        from .settings import TILE
        col, fila, ancho, alto = LUGARES_VENTA[self.zona_idx][1]
        return (int((col + ancho / 2) * TILE),
                int((fila + alto / 2) * TILE))

    def mensaje(self, reloj):
        return (f"LIQUIDO YA: {self.cantidad} {NOMBRE_MED[self.tipo]}"
                f" por ${self.precio_total}. {self.nombre_zona}."
                f" Tenés {int(self.timer)}s y me borro.")


class EventoSoborno:
    """La policía quiere su parte por 'no ver' a tus vendedores.
    Pago único global, pero exponencial en zonas controladas."""

    tipo_evento = "soborno"

    def __init__(self, zonas_controladas):
        self.zonas = zonas_controladas
        self.monto = calcular_soborno(zonas_controladas)
        self.timer = SEGUNDOS_SOBORNO

    def mensaje(self, reloj):
        return (f"Sabemos de tus {self.zonas} esquinas. "
                f"${self.monto} y seguimos sin ver nada. "
                f"Tenés {int(self.timer)}s. — un amigo de azul")


class GestorEventos:
    """El manager central: decide CUÁNDO disparar cada evento según
    su frecuencia, mantiene los activos (que la app Mensajes lista)
    y aplica el castigo del soborno impago.

    Los PedidoVIP van a la lista `tratos` de siempre (usan el mismo
    circuito de citas); los flash/soborno viven en `self.eventos`.
    main.py traduce lo que devuelve `actualizar` a mundo: NPCs,
    avisos y sonidos."""

    def __init__(self):
        self.eventos = []           # EventoFlash / EventoSoborno activos
        self.timer_vip = random.uniform(*FREC_VIP)
        self.timer_flash = random.uniform(*FREC_FLASH)
        self.timer_soborno = random.uniform(*FREC_SOBORNO)

    # -- consultas --
    def flash_activo(self):
        return next((e for e in self.eventos
                     if e.tipo_evento == "flash"), None)

    def soborno_activo(self):
        return next((e for e in self.eventos
                     if e.tipo_evento == "soborno"), None)

    # -- ciclo --
    def actualizar(self, dt, economia, red, reloj, tratos):
        """Devuelve avisos para main: [("vip", trato), ("flash", ev),
        ("flash_vencido", ev), ("soborno", ev), ("castigo", ev)]."""
        if not red.flaco_desbloqueado:
            return []               # todavía sos vendedor de calle
        avisos = []

        # A) Pedidos VIP — frecuencia alta
        self.timer_vip -= dt
        if self.timer_vip <= 0:
            self.timer_vip = random.uniform(*FREC_VIP)
            activos = sum(1 for t in tratos
                          if t.estado in ("aceptado", "encuentro"))
            hay_oferta_vip = any(t.estado == "oferta" for t in tratos)
            if not hay_oferta_vip and activos < MAX_TRATOS_ACTIVOS:
                trato = PedidoVIP(reloj, red.lugares_para_tratos())
                tratos.append(trato)
                avisos.append(("vip", trato))

        # B) Ofertas flash — raras, de a una
        self.timer_flash -= dt
        if self.timer_flash <= 0:
            self.timer_flash = random.uniform(*FREC_FLASH)
            if self.flash_activo() is None:
                evento = EventoFlash()
                self.eventos.append(evento)
                avisos.append(("flash", evento))

        # C) Sobornos — raros, solo si hay imperio que apretar
        self.timer_soborno -= dt
        if self.timer_soborno <= 0:
            self.timer_soborno = random.uniform(*FREC_SOBORNO)
            zonas = len(red.zonas_conquistadas())
            if zonas > 0 and self.soborno_activo() is None:
                evento = EventoSoborno(zonas)
                self.eventos.append(evento)
                avisos.append(("soborno", evento))

        # Relojes de los activos
        for evento in list(self.eventos):
            evento.timer -= dt
            if evento.timer > 0:
                continue
            self.eventos.remove(evento)
            if evento.tipo_evento == "flash":
                avisos.append(("flash_vencido", evento))
            else:
                # No pagaste: operativo policial sobre toda la Red
                red.limpiar_inventarios()
                red.deshabilitar_vendedores(SEGUNDOS_CLAUSURA)
                avisos.append(("castigo", evento))
        return avisos

    # -- acciones del jugador --
    def pagar_soborno(self, economia):
        """Paga desde la app Mensajes. Devuelve True si se resolvió."""
        evento = self.soborno_activo()
        if evento is None or not economia.pagar(evento.monto):
            return False
        self.eventos.remove(evento)
        return True

    def comprar_flash(self, economia):
        """Compra el cargamento (Walter ya llegó al punto)."""
        evento = self.flash_activo()
        if evento is None or not economia.pagar(evento.precio_total):
            return None
        if evento.tipo == "med_nat":
            economia.med_nat += evento.cantidad
        else:
            economia.med_quim += evento.cantidad
        self.eventos.remove(evento)
        return evento

    # -- guardado (solo lo que importa: el soborno no se esquiva
    # cerrando el juego; el flash se pierde, mala suerte) --
    def a_dict(self):
        soborno = self.soborno_activo()
        return {"soborno": ({"zonas": soborno.zonas,
                             "monto": soborno.monto,
                             "timer": round(soborno.timer, 1)}
                            if soborno else None)}

    @classmethod
    def desde_dict(cls, datos):
        gestor = cls()
        if datos and datos.get("soborno"):
            guardado = datos["soborno"]
            evento = EventoSoborno(guardado["zonas"])
            evento.monto = guardado["monto"]
            evento.timer = guardado["timer"]
            gestor.eventos.append(evento)
        return gestor
