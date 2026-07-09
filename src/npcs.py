# =========================================================
# FAST EMPIRE — NPCs  [Fase 4]
#
# - ClienteLocal: entra al local, hace fila frente al
#   mostrador, Walter lo atiende con E, se va a comer a un
#   costado y sale. Si la fila no avanza se cansa y se va.
# - CompradorIlegal: aparece en el borde del punto ilegal,
#   camina hasta Walter, compra un medicamento y desaparece.
#
# Los dos caminan en línea recta (el local y los puntos son
# áreas abiertas); la geometría del local se resuelve con
# waypoints (puerta → fila → mesa → puerta).
# =========================================================

import random

import pygame

from .sprites import paleta_peaton, paleta_encapuchado, dibujar_personaje

VELOCIDAD_PEATON = 85        # px/s, más lento que Walter
SEGUNDOS_COMIENDO = 5.0
PACIENCIA_FILA = 30.0        # segundos antes de irse sin comprar
DISTANCIA_COMPRA = 24        # px al jugador para concretar la compra
VIDA_COMPRADOR = 30.0        # red de seguridad para despawnear

# Ropa variada para que no parezcan clones
COLORES_ROPA = [
    (60, 76, 110),   # azul
    (92, 92, 96),    # gris
    (70, 100, 70),   # verde
    (122, 100, 58),  # mostaza
    (100, 62, 92),   # violeta
]
COLOR_PIEL = (196, 164, 120)
COLOR_CAPUCHA = (58, 58, 64)   # compradores ilegales, bajo perfil
COLOR_PLATO = (235, 235, 230)


class _Peaton:
    """Base con movimiento simple hacia un objetivo."""

    def __init__(self, x, y, color_ropa):
        self.pos = pygame.Vector2(x, y)
        self.rect = pygame.Rect(int(x), int(y), 18, 24)
        self.color_ropa = color_ropa
        self.paleta = paleta_peaton(color_ropa)
        self.terminado = False  # marcado para eliminar

    def _avanzar_hacia(self, destino, dt):
        """Da un paso hacia el destino y devuelve la distancia restante."""
        hacia = pygame.Vector2(destino) - pygame.Vector2(self.rect.center)
        distancia = hacia.length()
        if distancia > 1:
            self.pos += hacia.normalize() * VELOCIDAD_PEATON * dt
            self.rect.topleft = (round(self.pos.x), round(self.pos.y))
        return distancia

    def _dibujar_cuerpo(self, superficie, r, color_cabeza=COLOR_PIEL):
        pygame.draw.rect(superficie, self.color_ropa,
                         (r.x, r.y + 7, r.width, r.height - 7))
        pygame.draw.rect(superficie, color_cabeza,
                         (r.x + 4, r.y, r.width - 8, 9))


class ClienteLocal(_Peaton):
    """Cliente del local de comidas. Estados:
    entrando → cola → comiendo → saliendo."""

    def __init__(self, entrada, puerta):
        super().__init__(*entrada, random.choice(COLORES_ROPA))
        self.puerta = pygame.Vector2(puerta)
        self.salida = pygame.Vector2(entrada)   # se va por donde vino
        # Punto en la vereda alineado con la puerta: entrar y salir
        # derecho por el vano en vez de cortar camino por la pared
        self.frente_puerta = pygame.Vector2(puerta[0], entrada[1])
        self.estado = "entrando"
        self.objetivo = None       # su lugar en la fila (lo asigna main.py)
        self.paciencia = PACIENCIA_FILA
        self.timer_comer = 0.0
        self.lugar = None          # dónde come

    def actualizar(self, dt):
        """Devuelve "harto" en el frame en que se cansó de esperar."""
        if self.estado == "entrando":
            if self._avanzar_hacia(self.frente_puerta, dt) < 10:
                self.estado = "cruzando"
        elif self.estado == "cruzando":
            if self._avanzar_hacia(self.puerta, dt) < 10:
                self.estado = "cola"

        elif self.estado == "cola":
            if self.objetivo is not None:
                self._avanzar_hacia(self.objetivo, dt)
            self.paciencia -= dt
            if self.paciencia <= 0:
                self.irse()
                return "harto"

        elif self.estado == "comiendo":
            if self._avanzar_hacia(self.lugar, dt) < 6:
                self.timer_comer -= dt
                if self.timer_comer <= 0:
                    self.irse()

        elif self.estado == "saliendo":  # hacia la puerta desde adentro
            if self._avanzar_hacia(self.puerta, dt) < 12:
                self.estado = "yendose"
        elif self.estado == "yendose":   # cruzar el vano hacia la vereda
            if self._avanzar_hacia(self.frente_puerta, dt) < 10:
                self.estado = "yendose2"
        else:  # yendose2: por la calle hasta desaparecer
            if self._avanzar_hacia(self.salida, dt) < 10:
                self.terminado = True
        return None

    def listo_para_atender(self, posicion_frente):
        """True si está primero en la fila, quieto frente al mostrador."""
        return (self.estado == "cola" and
                pygame.Vector2(self.rect.center).distance_to(posicion_frente) < 24)

    def servir(self, lugar):
        """Fue atendido: se va a comer al lugar indicado."""
        self.estado = "comiendo"
        self.lugar = pygame.Vector2(lugar)
        self.timer_comer = SEGUNDOS_COMIENDO

    def irse(self):
        if self.estado not in ("saliendo", "yendose", "yendose2"):
            self.estado = "saliendo"

    def dibujar(self, superficie, camara):
        r = camara.aplicar(self.rect)
        dibujar_personaje(superficie, r, self.paleta, self)
        # Platito en la mano mientras come
        if self.estado == "comiendo":
            pygame.draw.rect(superficie, COLOR_PLATO,
                             (r.x + 1, r.y + 12, 9, 4))


class Proveedor(_Peaton):
    """El contacto del mercado negro. Aparece en la puerta del local
    cuando el negocio legal despega, espera a que Walter le hable (E)
    y después se va caminando hacia el sur."""

    COLOR_ABRIGO = (46, 40, 52)   # sobretodo oscuro con dejo violeta

    def __init__(self, x, y):
        super().__init__(x, y, self.COLOR_ABRIGO)
        self.paleta = paleta_encapuchado(self.COLOR_ABRIGO)
        self.estado = "esperando"  # esperando | yendose
        self.timer_salida = 10.0   # se esfuma aunque no llegue a destino

    def irse(self):
        self.estado = "yendose"

    def actualizar(self, dt):
        if self.estado == "yendose":
            # Camina hacia el sur por la calle y desaparece
            self._avanzar_hacia((self.rect.centerx, self.rect.centery + 400), dt)
            self.timer_salida -= dt
            if self.timer_salida <= 0:
                self.terminado = True

    def dibujar(self, superficie, camara):
        dibujar_personaje(superficie, camara.aplicar(self.rect),
                          self.paleta, self)


class CompradorIlegal(_Peaton):
    """Comprador del punto ilegal. Prefiere un tipo de medicamento,
    pero si no hay se lleva el otro (eso lo decide main.py)."""

    def __init__(self, x, y):
        super().__init__(x, y, COLOR_CAPUCHA)
        self.paleta = paleta_encapuchado(COLOR_CAPUCHA)
        self.origen = pygame.Vector2(x, y)
        self.tipo_preferido = random.choice(("med_nat", "med_quim"))
        self.estado = "acercando"  # acercando | saliendo
        self.vida = VIDA_COMPRADOR

    def actualizar(self, dt, rect_jugador):
        """Devuelve "compra" en el frame en que llega hasta el jugador."""
        self.vida -= dt
        if self.vida <= 0:
            self.terminado = True
            return None

        if self.estado == "acercando":
            if self._avanzar_hacia(rect_jugador.center, dt) < DISTANCIA_COMPRA:
                return "compra"
        else:  # saliendo
            if self._avanzar_hacia(self.origen, dt) < 6:
                self.terminado = True
        return None

    def irse(self):
        self.estado = "saliendo"

    def dibujar(self, superficie, camara):
        dibujar_personaje(superficie, camara.aplicar(self.rect),
                          self.paleta, self)
