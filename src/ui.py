# =========================================================
# FAST EMPIRE — Interfaz de usuario  [Fase 11]
#
# - HUD repartido por la pantalla (ya no hay panelón): vida y
#   plata arriba a la izquierda, reloj arriba al centro,
#   búsqueda a la derecha y el INVENTARIO RÁPIDO de 9 módulos
#   abajo al centro. TAB lo esconde casi todo.
# - PantallaInventario (tecla O): todo lo que llevás, en una
#   grilla grande con descripciones.
# - PantallaCelular (tecla C o el teléfono del local): un
#   celular de verdad con tres apps — Pedidos (compras),
#   Mapa (el mapa del juego) y Mensajes (los tratos).
# - Menús con soporte de MOUSE: mover el mouse resalta la
#   opción y el click izquierdo la confirma; el teclado
#   (W/S + E/Enter) sigue funcionando igual.
# =========================================================

import math

import pygame
from pathlib import Path

from .settings import (
    ANCHO_VENTANA, ALTO_VENTANA, TILE, ESCALA_MUNDO,
    COLOR_FONDO, COLOR_TEXTO, COLOR_TEXTO_SUAVE,
    COLOR_ORO, COLOR_DINERO, COLOR_TARJETA, COLOR_ERROR,
    COLOR_VIDA, COLOR_VIDA_FONDO,
    COLOR_MED_NAT, COLOR_MED_QUIM, COLOR_PUNTO,
    COLOR_CELULAR, COLOR_CELULAR_BORDE, COLOR_PANTALLA_CEL,
    COLOR_APP_ACTIVA, COLOR_SLOT, COLOR_SLOT_BORDE, COLOR_SLOT_SEL,
    COLOR_PASTO, COLOR_CALLE, COLOR_EDIFICIO, COLOR_CASA,
    COLOR_AGUA, COLOR_TIERRA, COLOR_PISO_LOCAL, COLOR_ARBOL,
    COLOR_TIENDA_TOLDO, COLOR_HOSPITAL, COLOR_BANCO,
)
from .economy import (
    PEDIDOS, TIEMPO_ENTREGA, RECETAS,
    PRECIO_PISTOLA, PRECIO_BALAS, BALAS_POR_PACK,
    PRECIO_SANGUCHE, CURA_SANGUCHE, MAX_SANGUCHES,
    VENTAS_PARA_CONTACTO, COMISION_VENDEDOR,
    NOMBRE_MED, NOMBRE_ITEM, VEHICULOS, ITEMS_SIEMPRE_ENCIMA, MUEBLES,
    PRECIO_MOZO, PRECIO_CHEF, PRECIO_REPOSITOR,
    COMISION_MOZO, SUELDO_CHEF, SUELDO_REPOSITOR,
    PRECIO_CONSEGUIDOR, PRECIO_QUIMICO, PRECIO_EMPAQUETADOR,
    SUELDO_CONSEGUIDOR, SUELDO_QUIMICO, SUELDO_EMPAQUETADOR,
)
from .crafting import receta_texto
from .inventory import mover as mover_stack
from .skills import ARBOL
from .skilltree import NODOS, PRODUCTOS
from .sprites import dibujar_vehiculo


# ---------------------------------------------------------
# Íconos PNG: carga lazy, caché por (id, tamaño)
# ---------------------------------------------------------
_ICONOS_CACHE = {}   # (id_item, tam) -> Surface  ó  None si falta el archivo

_MAPA_PNG = {
    "arma":        "icono_arma.png",
    "punos":       "icono_punos.png",
    "balas":       "icono_balas.png",
    "ingredientes":"icono_ingredientes.png",
    "sanguche":    "icono_sanguche.png",
    "med_nat":     "icono_med_nat.png",
    "med_quim":    "icono_med_quim.png",
    "celular":     "icono_celular.png",
    "receta":      "icono_receta.png",
    "comida":      "icono_comida.png",
    "efectivo":    "icono_efectivo.png",
    "banco":       "icono_banco.png",
}

_DIR_SPRITES = Path(__file__).resolve().parent.parent / "assets" / "sprites"


def _obtener_icono(id_item, tam):
    """Devuelve el ícono PNG escalado a tam×tam, o None si no existe."""
    clave = (id_item, tam)
    if clave in _ICONOS_CACHE:
        return _ICONOS_CACHE[clave]
    nombre = _MAPA_PNG.get(id_item)
    resultado = None
    if nombre:
        ruta = _DIR_SPRITES / nombre
        if ruta.exists():
            try:
                img = pygame.image.load(str(ruta)).convert_alpha()
                resultado = pygame.transform.smoothscale(img, (tam, tam))
            except Exception:
                pass
    _ICONOS_CACHE[clave] = resultado
    return resultado


def _panel(ancho, alto, alpha=175):
    """Superficie oscura semitransparente para fondos de HUD/menús."""
    s = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    s.fill((10, 10, 14, alpha))
    return s


# ---------------------------------------------------------
# Texto nítido: el mundo se dibuja en el lienzo lógico de
# 960x540 y se estira a la ventana, pero el TEXTO se renderiza
# aparte a la resolución real del monitor (así en pantalla
# completa queda fino en vez de pixelado).
# - FuenteUI reemplaza a pygame.font.Font en la interfaz:
#   render() devuelve un TextoUI que MIDE en píxeles lógicos
#   (el layout de siempre no se entera) pero guarda la imagen
#   renderizada al tamaño nativo.
# - SuperficieUI envuelve el lienzo: las formas y paneles van
#   a .raw como siempre; los TextoUI quedan en una cola y
#   volcar() los dibuja nítidos sobre la ventana real, después
#   de estirar el lienzo.
# - aplanar() es la barrera para los menús que se dibujan
#   ENCIMA del juego: baja al lienzo el texto ya encolado para
#   que el velo del menú lo tape como corresponde.
# ---------------------------------------------------------
_ESCALA = 1.0      # ventana real / resolución lógica (1.0 en ventana)
_FUENTES = {}      # tamaño en px -> Font (lógicas y nativas comparten)


def fijar_escala(escala):
    """La llama main.py al crear la ventana o alternar fullscreen."""
    global _ESCALA
    _ESCALA = escala


def _fuente_px(px):
    fuente = _FUENTES.get(px)
    if fuente is None:
        fuente = pygame.font.Font(None, px)
        _FUENTES[px] = fuente
    return fuente


class TextoUI:
    """Texto renderizado al tamaño nativo que "mide" en píxeles
    lógicos, para que el layout de los menús no cambie."""

    def __init__(self, tam, texto, antialias, color):
        self.tam = tam
        self.texto = texto
        self.antialias = antialias
        self.color = color
        self.alpha = None
        self.nativa = _fuente_px(max(1, round(tam * _ESCALA))).render(
            texto, antialias, color)
        if _ESCALA == 1.0:
            self._wl, self._hl = self.nativa.get_size()
        else:
            self._wl, self._hl = _fuente_px(tam).size(texto)

    def get_width(self):
        return self._wl

    def get_height(self):
        return self._hl

    def get_size(self):
        return (self._wl, self._hl)

    def get_rect(self, **kwargs):
        rect = pygame.Rect(0, 0, self._wl, self._hl)
        for clave, valor in kwargs.items():
            setattr(rect, clave, valor)
        return rect

    def set_alpha(self, alpha):
        self.alpha = alpha

    def dibujar_logico(self, destino, x, y):
        """Versión al tamaño lógico, para aplanar sobre el lienzo."""
        if _ESCALA == 1.0:
            img = self.nativa
        else:
            img = _fuente_px(self.tam).render(
                self.texto, self.antialias, self.color)
        if self.alpha is not None:
            img.set_alpha(self.alpha)
        destino.blit(img, (round(x), round(y)))

    def dibujar_nativo(self, destino, x, y, escala, dx, dy):
        if self.alpha is not None:
            self.nativa.set_alpha(self.alpha)
        destino.blit(self.nativa,
                     (dx + round(x * escala), dy + round(y * escala)))


class FuenteUI:
    """Cara compatible con pygame.font.Font para la interfaz."""

    def __init__(self, tam):
        self.tam = tam

    def render(self, texto, antialias=True, color=(255, 255, 255)):
        return TextoUI(self.tam, texto, antialias, color)

    def size(self, texto):
        return _fuente_px(self.tam).size(texto)

    def get_height(self):
        return _fuente_px(self.tam).get_height()


class SuperficieUI:
    """Envuelve el lienzo lógico. Las formas se dibujan en .raw;
    los textos (TextoUI) se encolan y se vuelcan nítidos al final
    del frame sobre la ventana real."""

    def __init__(self, lienzo):
        self.raw = lienzo
        self.textos = []   # (TextoUI, x lógico, y lógico)

    def blit(self, img, pos):
        if isinstance(img, TextoUI):
            if isinstance(pos, pygame.Rect):
                x, y = pos.x, pos.y
            else:
                x, y = pos[0], pos[1]
            self.textos.append((img, x, y))
        else:
            self.raw.blit(img, pos)

    def fill(self, color):
        self.raw.fill(color)

    def get_width(self):
        return self.raw.get_width()

    def get_height(self):
        return self.raw.get_height()

    def get_size(self):
        return self.raw.get_size()

    def get_rect(self):
        return self.raw.get_rect()

    def aplanar(self):
        """Baja el texto encolado al lienzo (al tamaño lógico), para
        que lo que se dibuje después lo tape como corresponde."""
        # En macOS nuevos el lienzo tiene canal alfa real y los paneles
        # semitransparentes dejan alfa 0: el blit del texto ahí copia
        # crudo (bloques sólidos). Se fuerza alfa opaco antes del texto.
        # OJO: solo en lienzos opacos — la capa de la UI es SRCALPHA
        # de verdad (transparente sobre el mundo) y este relleno la
        # volvería negra opaca.
        if not (self.raw.get_flags() & pygame.SRCALPHA):
            self.raw.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MAX)
        for texto, x, y in self.textos:
            texto.dibujar_logico(self.raw, x, y)
        self.textos.clear()

    def volcar(self, destino, escala, dx=0, dy=0):
        """Dibuja el texto encolado sobre la ventana real, nítido.
        Recorta al área del juego: el texto nunca pisa las franjas
        negras de la pantalla completa."""
        clip_previo = destino.get_clip()
        destino.set_clip((dx, dy, round(ANCHO_VENTANA * escala),
                          round(ALTO_VENTANA * escala)))
        for texto, x, y in self.textos:
            texto.dibujar_nativo(destino, x, y, escala, dx, dy)
        destino.set_clip(clip_previo)
        self.textos.clear()


# ---------------------------------------------------------
# Textos flotantes (viven en coordenadas de mundo)
# ---------------------------------------------------------
class TextoFlotante:
    def __init__(self, x, y, texto, color=COLOR_TEXTO):
        self.pos = pygame.Vector2(x, y)
        self.texto = texto
        self.color = color
        self.vida = 1.2  # segundos

    def actualizar(self, dt):
        self.pos.y -= 52 * dt   # px de MUNDO por segundo
        self.vida -= dt

    def dibujar(self, superficie, camara, fuente):
        """El texto vive en px de mundo pero se dibuja en la capa de
        la UI (que es ESCALA_MUNDO más chica que el lienzo del mundo)."""
        img = fuente.render(self.texto, True, self.color)
        img.set_alpha(max(0, min(255, int(self.vida * 400))))
        r = camara.aplicar(pygame.Rect(int(self.pos.x), int(self.pos.y), 1, 1))
        superficie.blit(img, (r.x / ESCALA_MUNDO - img.get_width() // 2,
                              r.y / ESCALA_MUNDO))


# ---------------------------------------------------------
# Íconos del inventario
# ---------------------------------------------------------
def dibujar_icono(superficie, id_item, rect, economia=None):
    """Dibuja el ícono del ítem en rect. Usa el PNG si existe, si no
    cae al dibujo procedural."""
    tam = min(rect.width, rect.height) - 8
    png = _obtener_icono(id_item, tam)
    if png is not None:
        superficie.blit(png, (rect.centerx - tam // 2, rect.centery - tam // 2))
        return

    cx, cy = rect.center
    if id_item == "arma":
        color = COLOR_TEXTO if (economia and economia.tiene_pistola) \
            else (70, 70, 76)
        pygame.draw.rect(superficie.raw, color, (cx - 9, cy - 4, 16, 5))   # caño
        pygame.draw.rect(superficie.raw, color, (cx - 7, cy - 1, 5, 9))    # culata
    elif id_item == "punos":
        pygame.draw.rect(superficie.raw, (196, 164, 120), (cx - 8, cy - 4, 7, 8))
        pygame.draw.rect(superficie.raw, (196, 164, 120), (cx + 1, cy - 4, 7, 8))
    elif id_item == "balas":
        for i in range(3):
            x = cx - 9 + i * 7
            pygame.draw.rect(superficie.raw, COLOR_ORO, (x, cy - 5, 4, 8))
            pygame.draw.rect(superficie.raw, (150, 110, 40), (x, cy + 3, 4, 3))
    elif id_item == "comida":
        pygame.draw.circle(superficie.raw, (235, 235, 230), (cx, cy), 9)   # plato
        pygame.draw.circle(superficie.raw, (214, 128, 52), (cx, cy), 5)    # guiso
    elif id_item == "ingredientes":
        pygame.draw.rect(superficie.raw, (150, 110, 66), (cx - 8, cy - 5, 16, 12))
        pygame.draw.rect(superficie.raw, (196, 172, 120), (cx - 1, cy - 5, 3, 12))
    elif id_item == "sanguche":
        pygame.draw.rect(superficie.raw, (222, 186, 120), (cx - 9, cy - 5, 18, 4))
        pygame.draw.rect(superficie.raw, (120, 180, 90), (cx - 8, cy - 1, 16, 2))
        pygame.draw.rect(superficie.raw, (190, 90, 70), (cx - 8, cy + 1, 16, 2))
        pygame.draw.rect(superficie.raw, (222, 186, 120), (cx - 9, cy + 3, 18, 4))
    elif id_item == "med_nat":
        pygame.draw.rect(superficie.raw, COLOR_MED_NAT, (cx - 7, cy - 4, 14, 9))
        pygame.draw.rect(superficie.raw, (80, 130, 80), (cx - 7, cy - 4, 14, 3))
    elif id_item == "med_quim":
        pygame.draw.rect(superficie.raw, COLOR_MED_QUIM, (cx - 4, cy - 8, 8, 16))
        pygame.draw.rect(superficie.raw, (120, 80, 160), (cx - 4, cy - 8, 8, 6))
    elif id_item == "efectivo":
        pygame.draw.rect(superficie.raw, COLOR_DINERO, (cx - 10, cy - 6, 20, 12))
        pygame.draw.circle(superficie.raw, (60, 110, 60), (cx, cy), 4)
    elif id_item == "celular":
        pygame.draw.rect(superficie.raw, COLOR_CELULAR_BORDE, (cx - 6, cy - 9, 12, 18))
        pygame.draw.rect(superficie.raw, (120, 200, 160), (cx - 4, cy - 7, 8, 12))
    elif id_item == "banco":
        pygame.draw.rect(superficie.raw, COLOR_BANCO, (cx - 9, cy - 6, 18, 13))
        pygame.draw.rect(superficie.raw, COLOR_ORO, (cx - 9, cy - 1, 18, 3))
    elif id_item == "puntos":
        pygame.draw.circle(superficie.raw, COLOR_ORO, (cx, cy), 8)
        pygame.draw.circle(superficie.raw, (150, 115, 45), (cx, cy), 8, 2)
    elif id_item == "receta":
        pygame.draw.rect(superficie.raw, (230, 224, 200), (cx - 7, cy - 9, 14, 18))
        for i in range(3):
            pygame.draw.rect(superficie.raw, (140, 130, 110),
                             (cx - 4, cy - 5 + i * 5, 8, 2))
    elif id_item == "ziploc":
        # Bolsita transparente con cierre
        pygame.draw.rect(superficie.raw, (188, 200, 210), (cx - 7, cy - 8, 14, 16))
        pygame.draw.rect(superficie.raw, (120, 140, 160), (cx - 7, cy - 8, 14, 16), 1)
        pygame.draw.rect(superficie.raw, (240, 210, 80), (cx - 7, cy - 8, 14, 3))
    elif id_item == "semillas":
        for dx, dy in ((-5, -3), (1, -5), (4, 2), (-3, 4), (0, 0)):
            pygame.draw.circle(superficie.raw, (170, 140, 70),
                               (cx + dx, cy + dy), 2)
    elif id_item == "compuestos":
        # Frasco de laboratorio con líquido
        pygame.draw.rect(superficie.raw, (200, 210, 220), (cx - 5, cy - 9, 10, 5))
        pygame.draw.polygon(superficie.raw, (200, 210, 220),
                            [(cx - 5, cy - 4), (cx + 5, cy - 4),
                             (cx + 9, cy + 8), (cx - 9, cy + 8)])
        pygame.draw.polygon(superficie.raw, (150, 90, 190),
                            [(cx - 7, cy + 2), (cx + 7, cy + 2),
                             (cx + 9, cy + 8), (cx - 9, cy + 8)])
    elif id_item == "comp_antiviral":
        # Frasco premium: líquido celeste y tapa dorada
        pygame.draw.rect(superficie.raw, (240, 210, 80), (cx - 5, cy - 9, 10, 5))
        pygame.draw.polygon(superficie.raw, (200, 210, 220),
                            [(cx - 5, cy - 4), (cx + 5, cy - 4),
                             (cx + 9, cy + 8), (cx - 9, cy + 8)])
        pygame.draw.polygon(superficie.raw, (80, 200, 230),
                            [(cx - 7, cy + 2), (cx + 7, cy + 2),
                             (cx + 9, cy + 8), (cx - 9, cy + 8)])
    elif id_item == "comp_suero":
        # Frasco top: líquido rojo intenso y tapa dorada
        pygame.draw.rect(superficie.raw, (240, 210, 80), (cx - 5, cy - 9, 10, 5))
        pygame.draw.polygon(superficie.raw, (200, 210, 220),
                            [(cx - 5, cy - 4), (cx + 5, cy - 4),
                             (cx + 9, cy + 8), (cx - 9, cy + 8)])
        pygame.draw.polygon(superficie.raw, (235, 80, 90),
                            [(cx - 7, cy + 2), (cx + 7, cy + 2),
                             (cx + 9, cy + 8), (cx - 9, cy + 8)])
    elif id_item == "planta":
        # Mata verde en maceta chica
        pygame.draw.rect(superficie.raw, (140, 84, 50), (cx - 5, cy + 2, 10, 7))
        for dx in (-5, 0, 5):
            pygame.draw.line(superficie.raw, (90, 170, 90),
                             (cx, cy + 2), (cx + dx, cy - 8), 2)
        pygame.draw.circle(superficie.raw, (110, 200, 110), (cx, cy - 8), 3)
    elif id_item == "quimico_crudo":
        # Cristal violeta cocido, sin empaquetar (aún no vendible)
        pygame.draw.polygon(superficie.raw, (150, 90, 190),
                            [(cx, cy - 9), (cx + 8, cy - 2),
                             (cx + 5, cy + 8), (cx - 5, cy + 8),
                             (cx - 8, cy - 2)])
        pygame.draw.polygon(superficie.raw, (200, 160, 235),
                            [(cx, cy - 9), (cx + 8, cy - 2), (cx, cy)])
        pygame.draw.line(superficie.raw, (110, 60, 150),
                         (cx, cy - 9), (cx, cy + 8), 1)
    elif id_item == "maceta":
        # Maceta vacía de la mueblería (mueble colocable)
        pygame.draw.polygon(superficie.raw, (150, 88, 52),
                            [(cx - 8, cy - 4), (cx + 8, cy - 4),
                             (cx + 5, cy + 8), (cx - 5, cy + 8)])
        pygame.draw.rect(superficie.raw, (70, 50, 34),
                         (cx - 6, cy - 4, 12, 3))
    elif id_item == "mesa_lab":
        # Mesa de laboratorio con frascos (mueble colocable)
        pygame.draw.rect(superficie.raw, (88, 92, 104),
                         (cx - 9, cy - 1, 18, 8))
        pygame.draw.rect(superficie.raw, (150, 90, 190),
                         (cx - 6, cy - 8, 4, 7))
        pygame.draw.rect(superficie.raw, (120, 70, 160),
                         (cx + 2, cy - 6, 4, 5))


# ---------------------------------------------------------
# HUD del juego (Fase 14: hotbar DINÁMICA con stacks)
# ---------------------------------------------------------
# Ya no hay slots fijos: la barra rápida muestra los stacks del
# inventario en el orden en que se recogieron (teclas 1-9). La
# plata no va acá: se muestra arriba a la izquierda con la vida.
MAX_HOTBAR = 9      # cuántos stacks entran en la barra
_SLOT = 44          # tamaño de cada módulo en px
_SLOT_SEP = 4


class HUD:
    def __init__(self):
        self.fuente = FuenteUI(24)
        self.fuente_chica = FuenteUI(20)
        self.fuente_reloj = FuenteUI(30)
        self.fuente_aviso = FuenteUI(68)

    def dibujar(self, superficie, jugador, economia, produccion,
                reloj, trato_activo, pista, busqueda, pedidos, fps,
                mostrar_panel=True, mision=None, sin_leer=0,
                montado=False):
        # Vida + plata: arriba a la izquierda, compactos
        self._vida_y_plata(superficie, jugador, economia, mostrar_panel)

        if mostrar_panel:
            self._reloj(superficie, reloj)
            self._hotbar(superficie, economia, sin_leer)
            if produccion.en_curso:
                self._barra_coccion(superficie, produccion)
            if pedidos:
                self._pedidos_en_camino(superficie, pedidos)
            if trato_activo is not None:
                self._banner_trato(superficie, trato_activo, reloj)
            if mision is not None:
                self._banner_mision(superficie, mision, trato_activo)

        if pista:
            self._pista(superficie, pista)
        if busqueda.nivel > 0:
            self._nivel_busqueda(superficie, busqueda)
        if economia.vehiculo:
            self._vehiculo_hud(superficie, economia, montado)
        img = self.fuente_chica.render(f"{fps} FPS", True, COLOR_TEXTO_SUAVE)
        superficie.blit(img, (ANCHO_VENTANA - img.get_width() - 8,
                              ALTO_VENTANA - img.get_height() - 6))

    def _vehiculo_hud(self, superficie, economia, montado=False):
        """Chip del vehículo equipado, esquina inferior derecha."""
        datos = VEHICULOS[economia.vehiculo]
        texto = (f"{datos['nombre']} · al volante" if montado
                 else f"{datos['nombre']} [F]")
        img = self.fuente_chica.render(texto, True,
                                       COLOR_ORO if montado else COLOR_TEXTO)
        ancho = 52 + img.get_width()
        x = ANCHO_VENTANA - ancho - 8
        y = ALTO_VENTANA - 56
        superficie.blit(_panel(ancho, 32), (x, y))
        dibujar_vehiculo(superficie.raw, economia.vehiculo,
                         x + 24, y + 28, ancho_max=36)
        superficie.blit(img, (x + 44, y_centrado(img, y, 32)))

    def _vida_y_plata(self, superficie, jugador, economia, mostrar_panel):
        superficie.blit(_panel(190, 70 if mostrar_panel else 24), (8, 8))
        pygame.draw.rect(superficie.raw, COLOR_VIDA_FONDO, (16, 14, 174, 10))
        relleno = int(174 * max(0, jugador.vida) / jugador.vida_max)
        pygame.draw.rect(superficie.raw, COLOR_VIDA, (16, 14, relleno, 10))
        if mostrar_panel:
            # Efectivo (billetes) y plata del banco (tarjeta)
            icono = _obtener_icono("efectivo", 18)
            if icono is not None:
                superficie.blit(icono, (14, 28))
            img = self.fuente.render(f"$ {economia.dinero}", True, COLOR_DINERO)
            superficie.blit(img, (38, 30))

            icono = _obtener_icono("banco", 18)
            if icono is not None:
                superficie.blit(icono, (14, 50))
            img = self.fuente.render(f"$ {economia.banco}", True,
                                     COLOR_TARJETA)
            superficie.blit(img, (38, 52))

            pts = self.fuente_chica.render(
                f"{economia.puntos} pts [T]", True, COLOR_ORO)
            superficie.blit(pts, (190 - pts.get_width(), 52))

    def _reloj(self, superficie, reloj):
        img = self.fuente_reloj.render(reloj.texto(), True, COLOR_TEXTO)
        ancho = img.get_width() + 24
        x = (ANCHO_VENTANA - ancho) // 2
        superficie.blit(_panel(ancho, 30), (x, 8))
        superficie.blit(img, (x + 12, y_centrado(img, 8, 30)))

    def _hotbar(self, superficie, economia, sin_leer):
        """La barra rápida dinámica: los stacks del inventario en
        orden de llegada, cada uno con su "xN" abajo a la derecha.
        Ningún slot está reservado — al vaciarse un stack, los de
        la derecha corren un lugar. Al final se suma un slot de
        SOLO LECTURA con la comida cocinada del mostrador (sin
        número de tecla: no es un ítem que se "use")."""
        stacks = economia.inventario.stacks[:MAX_HOTBAR]
        hay_comida = economia.producto > 0
        cajas = len(stacks) + (1 if hay_comida else 0)
        if not cajas:
            return
        total = cajas * _SLOT + (cajas - 1) * _SLOT_SEP
        x = (ANCHO_VENTANA - total) // 2
        y = ALTO_VENTANA - _SLOT - 10
        for i, (id_item, cantidad) in enumerate(stacks):
            rect = pygame.Rect(x + i * (_SLOT + _SLOT_SEP), y, _SLOT, _SLOT)
            caja = pygame.Surface(rect.size, pygame.SRCALPHA)
            caja.fill((*COLOR_SLOT[:3], 200))
            superficie.blit(caja, rect)
            # El arma resalta si está equipada
            equipada = id_item == "arma" and economia.arma_equipada \
                and economia.tiene_pistola
            borde = COLOR_SLOT_SEL if equipada else COLOR_SLOT_BORDE
            pygame.draw.rect(superficie.raw, borde, rect, 2 if equipada else 1)

            # El slot del arma muestra a QUÉ cambiarías al usarla
            icono = id_item
            if id_item == "arma":
                icono = "punos" if economia.arma_equipada else "arma"
            dibujar_icono(superficie, icono, rect, economia)

            # Número de tecla (arriba izq.) y stack (abajo der.)
            num = self.fuente_chica.render(str(i + 1), True, COLOR_TEXTO_SUAVE)
            superficie.blit(num, (rect.x + 3, rect.y + 1))
            if cantidad > 1:
                img = self.fuente_chica.render(f"x{cantidad}", True,
                                               COLOR_TEXTO)
                superficie.blit(img, (rect.right - img.get_width() - 3,
                                      rect.bottom - img.get_height() - 2))
            # Mensajes sin leer sobre el celular
            if id_item == "celular" and sin_leer:
                pygame.draw.circle(superficie.raw, COLOR_ERROR,
                                   (rect.right - 6, rect.y + 7), 7)
                aviso = self.fuente_chica.render(str(sin_leer), True, COLOR_TEXTO)
                superficie.blit(aviso, (rect.right - 6 - aviso.get_width() // 2,
                                        rect.y + 1))

        # Slot informativo de la comida lista (siempre a la derecha)
        if hay_comida:
            rect = pygame.Rect(x + len(stacks) * (_SLOT + _SLOT_SEP), y,
                               _SLOT, _SLOT)
            caja = pygame.Surface(rect.size, pygame.SRCALPHA)
            caja.fill((*COLOR_SLOT[:3], 200))
            superficie.blit(caja, rect)
            pygame.draw.rect(superficie.raw, COLOR_ORO, rect, 1)
            dibujar_icono(superficie, "comida", rect, economia)
            img = self.fuente_chica.render(f"x{economia.producto}", True,
                                           COLOR_TEXTO)
            superficie.blit(img, (rect.right - img.get_width() - 3,
                                  rect.bottom - img.get_height() - 2))

    def _barra_coccion(self, superficie, produccion):
        ancho, alto = 220, 16
        x = (ANCHO_VENTANA - ancho) // 2
        y = ALTO_VENTANA - _SLOT - 34
        superficie.blit(_panel(ancho, alto), (x, y))
        relleno = int((ancho - 4) * min(1.0, produccion.progreso))
        pygame.draw.rect(superficie.raw, COLOR_ORO, (x + 2, y + 2, relleno, alto - 4))
        img = self.fuente_chica.render("Cocinando…", True, COLOR_FONDO)
        superficie.blit(img, (x + 8, y + 1))

    def _pedidos_en_camino(self, superficie, pedidos):
        faltan = int(min(p["timer"] for p in pedidos)) + 1
        texto = f"Pedido en camino: {faltan}s"
        if len(pedidos) > 1:
            texto += f" (+{len(pedidos) - 1})"
        img = self.fuente_chica.render(texto, True, COLOR_TEXTO_SUAVE)
        superficie.blit(_panel(img.get_width() + 16, 24),
                        (8, ALTO_VENTANA - 34))
        superficie.blit(img, (16, ALTO_VENTANA - 29))

    def _banner_trato(self, superficie, trato, reloj):
        """El próximo trato acordado, debajo del reloj."""
        if trato.estado == "encuentro":
            texto = (f"TRATO: {trato.comprador_nombre} te espera en "
                     f"{trato.nombre_lugar} — {trato.cantidad} "
                     f"{NOMBRE_MED[trato.tipo]} por ${trato.total}")
            color = COLOR_PUNTO
        else:
            texto = (f"Trato: {trato.nombre_lugar} a las "
                     f"{reloj.texto_hora(trato.minuto_cita)} — "
                     f"{trato.cantidad} {NOMBRE_MED[trato.tipo]} "
                     f"(${trato.total})")
            color = COLOR_TEXTO
        img = self.fuente_chica.render(texto, True, color)
        ancho = img.get_width() + 20
        x = (ANCHO_VENTANA - ancho) // 2
        superficie.blit(_panel(ancho, 24), (x, 42))
        superficie.blit(img, (x + 10, 47))

    def _banner_mision(self, superficie, mision, trato_activo):
        """Misión activa del Proveedor: objetivo, progreso y reloj."""
        texto = (f"MISIÓN: {mision['desc']} — "
                 f"{mision['progreso']}/{mision['objetivo']} — "
                 f"{int(mision['timer']) + 1}s")
        img = self.fuente_chica.render(texto, True, COLOR_ORO)
        ancho = img.get_width() + 20
        x = (ANCHO_VENTANA - ancho) // 2
        y = 70 if trato_activo is not None else 42
        superficie.blit(_panel(ancho, 24), (x, y))
        superficie.blit(img, (x + 10, y + 5))

    def _nivel_busqueda(self, superficie, busqueda):
        ancho_panel = 5 * 18 + 16
        x = ANCHO_VENTANA - ancho_panel - 8
        superficie.blit(_panel(ancho_panel, 44), (x, 8))
        etiqueta = self.fuente_chica.render("BÚSQUEDA", True, COLOR_TEXTO_SUAVE)
        superficie.blit(etiqueta, (x + 8, 13))
        for i in range(5):
            casilla = pygame.Rect(x + 8 + i * 18, 30, 14, 14)
            if i < busqueda.nivel:
                pygame.draw.rect(superficie.raw, COLOR_VIDA, casilla)
            else:
                pygame.draw.rect(superficie.raw, COLOR_VIDA_FONDO, casilla, 1)

    def _pista(self, superficie, pista):
        img = self.fuente.render(pista, True, COLOR_TEXTO)
        ancho = img.get_width() + 28
        x = (ANCHO_VENTANA - ancho) // 2
        y = ALTO_VENTANA - _SLOT - 52
        superficie.blit(_panel(ancho, 30), (x, y))
        superficie.blit(img, (x + 14, y + 6))

    def dibujar_aviso(self, superficie, titulo, detalle):
        superficie.blit(_panel(ANCHO_VENTANA, 130, alpha=200),
                        (0, ALTO_VENTANA // 2 - 65))
        img = self.fuente_aviso.render(titulo, True, COLOR_ERROR)
        superficie.blit(img, ((ANCHO_VENTANA - img.get_width()) // 2,
                              ALTO_VENTANA // 2 - 52))
        sub = self.fuente.render(detalle, True, COLOR_TEXTO)
        superficie.blit(sub, ((ANCHO_VENTANA - sub.get_width()) // 2,
                              ALTO_VENTANA // 2 + 18))


def y_centrado(img, y, alto):
    """Y para centrar verticalmente una imagen en una franja."""
    return y + (alto - img.get_height()) // 2


# ---------------------------------------------------------
# Base para menús verticales: teclado (W/S + E/Enter) y MOUSE
# (mover para resaltar, click izquierdo para confirmar)
# ---------------------------------------------------------
class _MenuVertical:
    def __init__(self, opciones):
        self.opciones = opciones
        self.seleccion = 0
        self.fuente = FuenteUI(40)
        self._rects = []  # zonas clickeables, se regeneran al dibujar

    def _indice_en(self, pos):
        for i, rect in enumerate(self._rects):
            if rect.collidepoint(pos):
                return i
        return None

    def _navegar(self, evento):
        """Devuelve el ÍNDICE de la opción confirmada, o None."""
        if evento.type == pygame.MOUSEMOTION:
            i = self._indice_en(evento.pos)
            if i is not None:
                self.seleccion = i
            return None
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            i = self._indice_en(evento.pos)
            if i is not None:
                self.seleccion = i
                return i
            return None
        if evento.type != pygame.KEYDOWN:
            return None
        if evento.key in (pygame.K_w, pygame.K_UP):
            self.seleccion = (self.seleccion - 1) % len(self.opciones)
        elif evento.key in (pygame.K_s, pygame.K_DOWN):
            self.seleccion = (self.seleccion + 1) % len(self.opciones)
        elif evento.key in (pygame.K_RETURN, pygame.K_e, pygame.K_SPACE):
            return self.seleccion
        return None

    def _dibujar_opciones(self, superficie, y, interlinea=46):
        self._rects = []
        for i, opcion in enumerate(self.opciones):
            elegida = i == self.seleccion
            color = COLOR_ORO if elegida else COLOR_TEXTO
            texto = f"»  {opcion}  «" if elegida else opcion
            img = self.fuente.render(texto, True, color)
            x = (ANCHO_VENTANA - img.get_width()) // 2
            superficie.blit(img, (x, y))
            self._rects.append(pygame.Rect(x, y, img.get_width(),
                                           img.get_height()).inflate(24, 8))
            y += interlinea


# ---------------------------------------------------------
# Menú principal
# ---------------------------------------------------------
class MenuPrincipal(_MenuVertical):
    ACCIONES = ["nueva", "cargar", "Opciones", "debug", "Salir"]

    def __init__(self):
        super().__init__(["Nueva partida", "Cargar partida (vacío)",
                          "Opciones", "Modo debug: no", "Salir"])
        self.fuente_titulo = FuenteUI(100)
        self.fuente_sub = FuenteUI(26)

    def refrescar_debug(self, activo):
        self.opciones[3] = f"Modo debug: {'sí' if activo else 'no'}"

    def refrescar_guardado(self, cantidad):
        self.opciones[1] = (f"Cargar partida ({cantidad}/5)" if cantidad
                            else "Cargar partida (vacío)")

    def manejar_evento(self, evento):
        """Devuelve "nueva"/"cargar"/"Opciones"/"debug"/"Salir"/None."""
        i = self._navegar(evento)
        return None if i is None else self.ACCIONES[i]

    def dibujar(self, superficie):
        superficie.fill(COLOR_FONDO)
        titulo = self.fuente_titulo.render("FAST EMPIRE", True, COLOR_ORO)
        superficie.blit(titulo, ((ANCHO_VENTANA - titulo.get_width()) // 2, 100))
        sub = self.fuente_sub.render(
            "Un local de comidas al frente. Un imperio por detrás.",
            True, COLOR_TEXTO_SUAVE)
        superficie.blit(sub, ((ANCHO_VENTANA - sub.get_width()) // 2, 180))
        self._dibujar_opciones(superficie, 235)
        pie = self.fuente_sub.render(
            "Mouse o W/S + ENTER", True, COLOR_TEXTO_SUAVE)
        superficie.blit(pie, ((ANCHO_VENTANA - pie.get_width()) // 2, ALTO_VENTANA - 50))


# ---------------------------------------------------------
# Nueva partida: escribir el nombre del slot
# ---------------------------------------------------------
class PantallaNombre:
    LARGO_MAXIMO = 16

    def __init__(self):
        self.fuente_titulo = FuenteUI(64)
        self.fuente = FuenteUI(40)
        self.fuente_chica = FuenteUI(25)
        self.texto = ""
        self.mensaje = ""

    def abrir(self):
        self.texto = ""
        self.mensaje = ""

    def manejar_evento(self, evento):
        """Devuelve "cancelar", ("crear", nombre) o None."""
        if evento.type != pygame.KEYDOWN:
            return None
        if evento.key == pygame.K_ESCAPE:
            return "cancelar"
        if evento.key == pygame.K_RETURN:
            nombre = self.texto.strip()
            if nombre:
                return ("crear", nombre)
            self.mensaje = "Poné un nombre."
            return None
        if evento.key == pygame.K_BACKSPACE:
            self.texto = self.texto[:-1]
            return None
        caracter = evento.unicode
        if (caracter and caracter.isprintable()
                and len(self.texto) < self.LARGO_MAXIMO):
            self.texto += caracter
        return None

    def dibujar(self, superficie, pisa_existente, hay_espacio):
        superficie.fill(COLOR_FONDO)
        titulo = self.fuente_titulo.render("NUEVA PARTIDA", True, COLOR_ORO)
        superficie.blit(titulo, ((ANCHO_VENTANA - titulo.get_width()) // 2, 120))
        etiqueta = self.fuente_chica.render(
            "Nombre de la partida:", True, COLOR_TEXTO_SUAVE)
        superficie.blit(etiqueta, ((ANCHO_VENTANA - etiqueta.get_width()) // 2, 210))

        # Caja de texto con cursor titilante
        caja = pygame.Rect(ANCHO_VENTANA // 2 - 170, 245, 340, 48)
        pygame.draw.rect(superficie.raw, (24, 24, 30), caja)
        pygame.draw.rect(superficie.raw, COLOR_ORO, caja, 2)
        cursor = "|" if (pygame.time.get_ticks() // 450) % 2 == 0 else " "
        img = self.fuente.render(self.texto + cursor, True, COLOR_TEXTO)
        superficie.blit(img, (caja.x + 12, caja.y + 10))

        # Avisos según el nombre elegido
        if self.texto.strip() and pisa_existente:
            aviso = "Ya existe una partida con ese nombre: se va a pisar."
            color = COLOR_ORO
        elif not hay_espacio:
            aviso = "Máximo 5 partidas — borrá una desde \"Cargar partida\"."
            color = COLOR_ERROR
        else:
            aviso = self.mensaje
            color = COLOR_ERROR
        if aviso:
            img = self.fuente_chica.render(aviso, True, color)
            superficie.blit(img, ((ANCHO_VENTANA - img.get_width()) // 2, 315))

        pie = self.fuente_chica.render(
            "ENTER — crear  ·  ESC — volver", True, COLOR_TEXTO_SUAVE)
        superficie.blit(pie, ((ANCHO_VENTANA - pie.get_width()) // 2, ALTO_VENTANA - 60))


# ---------------------------------------------------------
# Cargar partida: listado de slots (cargar o borrar)
# ---------------------------------------------------------
class PantallaPartidas(_MenuVertical):
    def __init__(self):
        super().__init__(["(no hay partidas guardadas)"])
        self.fuente = FuenteUI(34)
        self.fuente_titulo = FuenteUI(64)
        self.fuente_chica = FuenteUI(25)
        self.entradas = []
        self.confirmar = None   # índice esperando segundo X
        self.mensaje = ""

    def abrir(self, entradas):
        self.entradas = entradas
        if entradas:
            self.opciones[:] = [
                f"{e['nombre']}  —  ${e['dinero']}  —  {e['fecha']}"
                for e in entradas]
        else:
            self.opciones[:] = ["(no hay partidas guardadas)"]
        self.seleccion = 0
        self.confirmar = None
        self.mensaje = ""

    def manejar_evento(self, evento):
        """Devuelve "cerrar", ("cargar", i), ("borrar", i) o None."""
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
            return "cerrar"

        # Borrar: tecla X o click derecho sobre una entrada
        indice_borrar = None
        if (evento.type == pygame.KEYDOWN and evento.key == pygame.K_x
                and self.entradas):
            indice_borrar = self.seleccion
        elif (evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 3
                and self.entradas):
            indice_borrar = self._indice_en(evento.pos)
        if indice_borrar is not None:
            self.seleccion = indice_borrar
            if self.confirmar == indice_borrar:
                self.confirmar = None
                return ("borrar", indice_borrar)
            self.confirmar = indice_borrar
            nombre = self.entradas[indice_borrar]["nombre"]
            self.mensaje = f"¿Borrar '{nombre}'? Apretá X de nuevo."
            return None

        seleccion_previa = self.seleccion
        i = self._navegar(evento)
        if self.seleccion != seleccion_previa:
            self.confirmar = None
            self.mensaje = ""
        if i is None:
            return None
        if not self.entradas:
            return "cerrar"
        return ("cargar", i)

    def dibujar(self, superficie):
        superficie.fill(COLOR_FONDO)
        titulo = self.fuente_titulo.render("CARGAR PARTIDA", True, COLOR_ORO)
        superficie.blit(titulo, ((ANCHO_VENTANA - titulo.get_width()) // 2, 70))
        info = self.fuente_chica.render(
            f"{len(self.entradas)}/5 partidas guardadas", True, COLOR_TEXTO_SUAVE)
        superficie.blit(info, ((ANCHO_VENTANA - info.get_width()) // 2, 135))
        self._dibujar_opciones(superficie, 190, interlinea=52)
        if self.mensaje:
            img = self.fuente_chica.render(self.mensaje, True, COLOR_ERROR)
            superficie.blit(img, ((ANCHO_VENTANA - img.get_width()) // 2, 470))
        pie = self.fuente_chica.render(
            "ENTER/click — cargar  ·  X o click derecho — borrar  ·  ESC — volver",
            True, COLOR_TEXTO_SUAVE)
        superficie.blit(pie, ((ANCHO_VENTANA - pie.get_width()) // 2, ALTO_VENTANA - 55))


# ---------------------------------------------------------
# Pantalla de opciones: volumen, música y pantalla completa
# ---------------------------------------------------------
class PantallaOpciones(_MenuVertical):
    ACCIONES = ["sonido", "musica", "fullscreen", "volver"]
    CONTROLES = [
        "W A S D — moverse   ·   Mouse — apuntar   ·   Click izq. — atacar",
        "Click der. (sostener) — mira   ·   E — interactuar",
        "C — celular (pedidos, mapa, mensajes)   ·   O — inventario",
        "1-8 — inventario rápido   ·   T — habilidades   ·   R — medicamentos",
        "TAB — ocultar HUD   ·   F11 o Cmd+F — pantalla completa",
        "F5 — guardar   ·   ESC — pausa",
    ]

    def __init__(self):
        super().__init__(["Sonido: 80%", "Música: sí",
                          "Pantalla completa: no", "Volver"])
        self.fuente = FuenteUI(38)
        self.fuente_titulo = FuenteUI(64)
        self.fuente_chica = FuenteUI(25)

    def refrescar(self, audio, pantalla_completa):
        """Actualiza las etiquetas con el estado real."""
        self.opciones[0] = f"Sonido: {round(audio.volumen * 100)}%"
        self.opciones[1] = f"Música: {'sí' if audio.musica_on else 'no'}"
        self.opciones[2] = ("Pantalla completa: "
                            + ("sí" if pantalla_completa else "no"))

    def manejar_evento(self, evento):
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
            return "volver"
        i = self._navegar(evento)
        return None if i is None else self.ACCIONES[i]

    def dibujar(self, superficie):
        superficie.fill(COLOR_FONDO)
        titulo = self.fuente_titulo.render("OPCIONES", True, COLOR_ORO)
        superficie.blit(titulo, ((ANCHO_VENTANA - titulo.get_width()) // 2, 40))
        y = 108
        for texto in self.CONTROLES:
            img = self.fuente_chica.render(texto, True, COLOR_TEXTO_SUAVE)
            superficie.blit(img, ((ANCHO_VENTANA - img.get_width()) // 2, y))
            y += 24
        self._dibujar_opciones(superficie, 278, interlinea=48)
        pie = self.fuente_chica.render(
            "Mouse o W/S + ENTER  ·  ESC volver", True, COLOR_TEXTO_SUAVE)
        superficie.blit(pie, ((ANCHO_VENTANA - pie.get_width()) // 2, ALTO_VENTANA - 35))


# ---------------------------------------------------------
# Menú de pausa (se dibuja sobre el juego congelado)
# ---------------------------------------------------------
class MenuPausa(_MenuVertical):
    ACCIONES = ["Continuar", "guardar", "Opciones", "Pantalla completa",
                "debug", "Menú principal"]

    def __init__(self):
        super().__init__(["Continuar", "Guardar partida", "Opciones",
                          "Pantalla completa", "Modo debug: no",
                          "Menú principal"])
        self.fuente_titulo = FuenteUI(72)
        self.fuente_chica = FuenteUI(24)
        self.mensaje = ""

    def refrescar_debug(self, activo):
        self.opciones[4] = f"Modo debug: {'sí' if activo else 'no'}"

    def manejar_evento(self, evento):
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
            return "Continuar"
        i = self._navegar(evento)
        return None if i is None else self.ACCIONES[i]

    def dibujar(self, superficie):
        velo = _panel(ANCHO_VENTANA, ALTO_VENTANA, alpha=150)
        superficie.blit(velo, (0, 0))
        titulo = self.fuente_titulo.render("PAUSA", True, COLOR_ORO)
        superficie.blit(titulo, ((ANCHO_VENTANA - titulo.get_width()) // 2, 145))
        self._dibujar_opciones(superficie, 235)
        if self.mensaje:
            img = self.fuente_chica.render(self.mensaje, True, COLOR_DINERO)
            superficie.blit(img, ((ANCHO_VENTANA - img.get_width()) // 2, 480))


# ---------------------------------------------------------
# Almacén del barrio: armas y curación
# ---------------------------------------------------------
class PantallaTienda(_MenuVertical):
    ITEMS = [
        ("pistola", f"Pistola — ${PRECIO_PISTOLA}"),
        ("balas", f"Balas x{BALAS_POR_PACK} — ${PRECIO_BALAS}"),
        ("sanguche",
         f"Sanguche casero (+{CURA_SANGUCHE} vida, al inventario) "
         f"— ${PRECIO_SANGUCHE}"),
        ("charlar", "Charlar con Don Aldo"),
        ("salir", "Salir"),
    ]

    def __init__(self):
        super().__init__([etiqueta for _, etiqueta in self.ITEMS])
        self.fuente = FuenteUI(34)
        self.fuente_titulo = FuenteUI(56)
        self.fuente_chica = FuenteUI(24)
        self.mensaje = ""
        self.color_mensaje = COLOR_TEXTO

    def abrir(self):
        self.seleccion = 0
        self.mensaje = ""

    def manejar_evento(self, evento, economia, jugador):
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
            return "cerrar"
        i = self._navegar(evento)
        if i is None:
            return None
        return self._comprar(self.ITEMS[i][0], economia, jugador)

    def _comprar(self, id_item, economia, jugador):
        if id_item == "salir":
            return "cerrar"
        if id_item == "charlar":
            return "charlar"  # main.py abre el diálogo con Don Aldo
        if id_item == "pistola":
            if economia.tiene_pistola:
                self._mensaje_error("Ya tenés la pistola.")
            elif economia.pagar(PRECIO_PISTOLA):
                economia.tiene_pistola = True
                economia.arma_equipada = True
                # El arma ocupa su lugar en la hotbar dinámica
                economia.inventario.agregar("arma")
                self._feedback(True, "Pistola comprada. Comprá balas.")
            else:
                self._feedback(False, "")
        elif id_item == "balas":
            if not economia.tiene_pistola:
                self._mensaje_error("Primero comprá la pistola.")
            elif economia.pagar(PRECIO_BALAS):
                economia.balas += BALAS_POR_PACK
                self._feedback(True, f"+{BALAS_POR_PACK} balas.")
            else:
                self._feedback(False, "")
        elif id_item == "sanguche":
            if economia.sanguches >= MAX_SANGUCHES:
                self._mensaje_error(
                    f"Ya llevás {MAX_SANGUCHES} sanguches encima.")
            elif economia.pagar(PRECIO_SANGUCHE):
                economia.sanguches += 1
                self._feedback(True, "Sanguche al inventario (se come con 5).")
            else:
                self._feedback(False, "")
        return None

    def _feedback(self, ok, mensaje_ok):
        if ok:
            self.mensaje = mensaje_ok
            self.color_mensaje = COLOR_DINERO
        else:
            self.mensaje = "No te alcanza la plata."
            self.color_mensaje = COLOR_ERROR

    def _mensaje_error(self, texto):
        self.mensaje = texto
        self.color_mensaje = COLOR_ERROR

    def dibujar(self, superficie, economia, jugador):
        velo = _panel(ANCHO_VENTANA, ALTO_VENTANA, alpha=170)
        superficie.blit(velo, (0, 0))
        titulo = self.fuente_titulo.render("ALMACÉN DEL BARRIO", True, COLOR_ORO)
        superficie.blit(titulo, ((ANCHO_VENTANA - titulo.get_width()) // 2, 80))
        info = self.fuente_chica.render(
            f"$ {economia.dinero}  ·  vida {max(0, jugador.vida)}/{jugador.vida_max}",
            True, COLOR_TEXTO_SUAVE)
        superficie.blit(info, ((ANCHO_VENTANA - info.get_width()) // 2, 145))
        self._dibujar_opciones(superficie, 210, interlinea=44)
        if self.mensaje:
            img = self.fuente_chica.render(self.mensaje, True, self.color_mensaje)
            superficie.blit(img, ((ANCHO_VENTANA - img.get_width()) // 2, 420))
        pie = self.fuente_chica.render(
            "Mouse o W/S + ENTER  ·  ESC salir", True, COLOR_TEXTO_SUAVE)
        superficie.blit(pie, ((ANCHO_VENTANA - pie.get_width()) // 2, ALTO_VENTANA - 60))


# ---------------------------------------------------------
# La mueblería: vende macetas y mesas de laboratorio. Van al
# INVENTARIO como ítems: con la tecla del hotbar se colocan en
# el tile al que apuntás, y X frente a un mueble vacío lo
# levanta de vuelta (la lógica vive en main.py).
# ---------------------------------------------------------
class PantallaMuebleria(_MenuVertical):
    def __init__(self):
        super().__init__([])
        self.fuente_titulo = FuenteUI(56)
        self.fuente_chica = FuenteUI(24)
        self._ids = []
        self.mensaje = ""
        self.color_mensaje = COLOR_TEXTO

    def abrir(self):
        self.seleccion = 0
        self.mensaje = ""

    def _armar_opciones(self, economia):
        self._ids, self.opciones = [], []
        for id_m, datos in MUEBLES.items():
            encima = economia.inventario.cantidad(id_m)
            etiqueta = f"{datos['nombre']} — ${datos['precio']}"
            if encima:
                etiqueta += f"  (llevás {encima})"
            self._ids.append(id_m)
            self.opciones.append(etiqueta)
        self._ids.append("salir")
        self.opciones.append("Salir")

    def manejar_evento(self, evento, economia):
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
            return "cerrar"
        self._armar_opciones(economia)
        i = self._navegar(evento)
        if i is None:
            return None
        id_m = self._ids[i]
        if id_m == "salir":
            return "cerrar"
        datos = MUEBLES[id_m]
        if economia.pagar(datos["precio"]):
            economia.inventario.agregar(id_m)
            self.mensaje = (f"{datos['nombre']} al inventario — colocala "
                            f"con su tecla del hotbar.")
            self.color_mensaje = COLOR_DINERO
        else:
            self.mensaje = "No te alcanza la plata."
            self.color_mensaje = COLOR_ERROR
        return None

    def dibujar(self, superficie, economia):
        self._armar_opciones(economia)
        velo = _panel(ANCHO_VENTANA, ALTO_VENTANA, alpha=170)
        superficie.blit(velo, (0, 0))
        titulo = self.fuente_titulo.render("MUEBLERÍA", True, COLOR_ORO)
        superficie.blit(titulo, ((ANCHO_VENTANA - titulo.get_width()) // 2, 80))
        info = self.fuente_chica.render(
            f"$ {economia.dinero} en mano", True, COLOR_TEXTO_SUAVE)
        superficie.blit(info, ((ANCHO_VENTANA - info.get_width()) // 2, 145))
        self._dibujar_opciones(superficie, 210, interlinea=48)

        # Ficha del mueble seleccionado
        sel_id = self._ids[self.seleccion]
        if sel_id in MUEBLES:
            desc = self.fuente_chica.render(
                MUEBLES[sel_id]["desc"], True, COLOR_TEXTO)
            superficie.blit(desc,
                            ((ANCHO_VENTANA - desc.get_width()) // 2, 400))
        if self.mensaje:
            img = self.fuente_chica.render(self.mensaje, True,
                                           self.color_mensaje)
            superficie.blit(img, ((ANCHO_VENTANA - img.get_width()) // 2, 430))
        pie = self.fuente_chica.render(
            "Mouse o W/S + ENTER  ·  ESC salir", True, COLOR_TEXTO_SUAVE)
        superficie.blit(pie, ((ANCHO_VENTANA - pie.get_width()) // 2,
                              ALTO_VENTANA - 60))


# ---------------------------------------------------------
# La concesionaria del Playón: un vehículo a la vez. Comprar
# otro entrega el actual al 50%; E sobre el equipado lo vende.
# ---------------------------------------------------------
class PantallaConcesionaria(_MenuVertical):
    def __init__(self):
        super().__init__([])
        self.fuente_titulo = FuenteUI(56)
        self.fuente_chica = FuenteUI(24)
        self._ids = []
        self.mensaje = ""
        self.color_mensaje = COLOR_TEXTO

    def abrir(self):
        self.seleccion = 0
        self.mensaje = ""

    def _armar_opciones(self, economia):
        """Etiquetas dinámicas: el equipado muestra la reventa y los
        demás el precio (con la parte de pago si entregás el tuyo)."""
        self._ids, self.opciones = [], []
        for id_v, datos in VEHICULOS.items():
            if economia.vehiculo == id_v:
                etiqueta = (f"{datos['nombre']} — EQUIPADO "
                            f"(vender: ${economia.reventa_vehiculo()})")
            elif economia.vehiculo:
                neto = datos["precio"] - economia.reventa_vehiculo()
                etiqueta = (f"{datos['nombre']} — ${datos['precio']}"
                            f"  (con la entrega: ${neto})")
            else:
                etiqueta = f"{datos['nombre']} — ${datos['precio']}"
            self._ids.append(id_v)
            self.opciones.append(etiqueta)
        self._ids.append("salir")
        self.opciones.append("Salir")

    def manejar_evento(self, evento, economia):
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
            return "cerrar"
        self._armar_opciones(economia)
        i = self._navegar(evento)
        if i is None:
            return None
        id_v = self._ids[i]
        if id_v == "salir":
            return "cerrar"
        if economia.vehiculo == id_v:
            ok, mensaje = economia.vender_vehiculo()
        else:
            ok, mensaje = economia.comprar_vehiculo(id_v)
        self.mensaje = mensaje
        self.color_mensaje = COLOR_DINERO if ok else COLOR_ERROR
        return None

    def dibujar(self, superficie, economia):
        self._armar_opciones(economia)
        velo = _panel(ANCHO_VENTANA, ALTO_VENTANA, alpha=170)
        superficie.blit(velo, (0, 0))
        titulo = self.fuente_titulo.render("CONCESIONARIA DEL PLAYÓN",
                                           True, COLOR_ORO)
        superficie.blit(titulo, ((ANCHO_VENTANA - titulo.get_width()) // 2, 80))
        actual = (VEHICULOS[economia.vehiculo]["nombre"]
                  if economia.vehiculo else "a pata")
        info = self.fuente_chica.render(
            f"$ {economia.dinero} en mano  ·  andás {actual}",
            True, COLOR_TEXTO_SUAVE)
        superficie.blit(info, ((ANCHO_VENTANA - info.get_width()) // 2, 145))

        self._dibujar_opciones(superficie, 200, interlinea=52)
        # El sprite de cada modelo, a la izquierda de su opción
        for i, rect in enumerate(self._rects):
            if self._ids[i] in VEHICULOS:
                dibujar_vehiculo(superficie.raw, self._ids[i],
                                 rect.x - 34, rect.bottom - 10)

        # Ficha del modelo seleccionado
        sel_id = self._ids[self.seleccion]
        if sel_id in VEHICULOS:
            datos = VEHICULOS[sel_id]
            desc = self.fuente_chica.render(datos["desc"], True, COLOR_TEXTO)
            superficie.blit(desc,
                            ((ANCHO_VENTANA - desc.get_width()) // 2, 418))
        if self.mensaje:
            img = self.fuente_chica.render(self.mensaje, True,
                                           self.color_mensaje)
            superficie.blit(img, ((ANCHO_VENTANA - img.get_width()) // 2, 448))
        pie = self.fuente_chica.render(
            "Mouse o W/S + ENTER  ·  ESC salir  ·  solo efectivo",
            True, COLOR_TEXTO_SUAVE)
        superficie.blit(pie, ((ANCHO_VENTANA - pie.get_width()) // 2,
                              ALTO_VENTANA - 60))


# ---------------------------------------------------------
# EL CELULAR: cuatro apps —
#   0 Comidas (pedidos de ingredientes con delivery)
#   1 Ilegales (meds, bloqueada hasta desbloquear)
#   2 Mapa  → gira a PAISAJE para ver el mapa completo
#   3 Mensajes (ofertas de tratos del mercado negro)
# C o E en el teléfono del local lo abre/cierra.
# ---------------------------------------------------------
class PantallaCelular:
    APPS = ["Comidas", "Insumos", "Mapa", "Mensajes", "Red", "Ventas",
            "Personal", "Equipo"]
    IDS_COMIDA    = ["ing6", "ing12"]
    # Ya no se compran medicamentos hechos: se compran los insumos
    # y se fabrica en el sótano del local
    IDS_ILEGALES  = ["ziploc10", "semillas4", "comp4",
                     "compant2", "compsue1"]
    # Cada insumo aparece en la app recién cuando el árbol de I+D
    # enseñó el medicamento que lo usa (ziploc: siempre).
    REQ_INSUMO = {"semillas4": "med_nat",   "comp4": "med_quim",
                  "compant2":  "med_quim2", "compsue1": "med_quim3"}

    # Portrait (apps 0, 1, 3)
    ANCHO_TEL = 300
    ALTO_TEL  = 512
    # Landscape (app Mapa)
    ANCHO_LAND = 524
    ALTO_LAND  = 318

    # Colores y datos de la home screen de cada app
    _APP_INFO = [
        # (nombre, color_fondo)
        ("Comidas",  (210, 100, 30)),
        ("Insumos",  (120,  35, 35)),
        ("Mapa",     ( 35,  90, 160)),
        ("Mensajes", ( 30, 140,  75)),
        ("Red",      (110,  60, 150)),
        ("Ventas",   (170, 130, 30)),
        ("Personal", ( 55, 110, 85)),
        ("Equipo",   ( 90,  45, 120)),   # el personal del laboratorio
    ]

    def __init__(self):
        self.fuente       = FuenteUI(24)
        self.fuente_chica = FuenteUI(20)
        self.fuente_titulo= FuenteUI(30)
        self.fuente_mini  = FuenteUI(16)
        self.app = 0
        self.seleccion = 0
        self.en_home = True         # True = pantalla de inicio con íconos
        self.mensaje = ""
        self.color_mensaje = COLOR_TEXTO
        self._minimapa = None       # prerenderizado al primer uso
        self._rects_items = []
        self._rects_home  = []      # rects de los íconos en la home screen

    def abrir(self, app=None):
        if app is not None:
            self.app = app
            self.en_home = False
        else:
            self.en_home = True
        self.seleccion = 0
        self.mensaje = ""

    @property
    def es_paisaje(self):
        """El mapa (app 2) gira el celular a horizontal."""
        return (not self.en_home) and self.app == 2

    def ids_insumos(self, arbol):
        """Los insumos comprables según lo investigado en el árbol."""
        return [i for i in self.IDS_ILEGALES
                if self.REQ_INSUMO.get(i) is None
                or (arbol is not None
                    and arbol.desbloqueado(self.REQ_INSUMO[i]))]

    # ── eventos ────────────────────────────────────────────
    def manejar_evento(self, evento, economia, tratos, reloj, red,
                       gestor, arbol=None, app_ventas=None):
        """→ "cerrar" | ("pedido", id) | ("aceptar", t) |
           ("rechazar", t) | ("pagar_soborno", ev) |
           ("contratar_mozo",) | ("contratar_chef",) |
           ("contratar_repositor",) | None"""
        if evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_c:
                return "cerrar"                  # C siempre cierra
            if self.en_home:
                return self._ev_home_teclado(evento)
            if evento.key == pygame.K_ESCAPE:
                self.en_home = True              # ESC dentro de app → vuelve al home
                self.seleccion = 0
                return None
            # Las apps SOLO se cambian desde el home (como un celular
            # de verdad): acá adentro no hay atajos de navegación
            if self.app == 0:
                return self._ev_lista(evento, economia,
                                      self.IDS_COMIDA, es_comida=True)
            elif self.app == 1:
                return self._ev_lista(evento, economia,
                                      self.ids_insumos(arbol),
                                      es_comida=False)
            elif self.app == 3:
                return self._ev_mensajes(evento, tratos, gestor)
            elif self.app == 4:
                return self._ev_red(evento, economia, red)
            elif self.app == 5:
                return self._ev_ventas(evento, arbol, app_ventas)
            elif self.app == 6:
                return self._ev_personal(evento, economia)
            elif self.app == 7:
                return self._ev_equipo(evento, economia)
        elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            if self.en_home:
                for i, r in enumerate(self._rects_home):
                    if r.collidepoint(evento.pos):
                        self.seleccion = i
                        self.app = i
                        self.en_home = False
                        self.mensaje = ""
                        return None
                return None
            for i, r in enumerate(self._rects_items):
                if r.collidepoint(evento.pos):
                    self.seleccion = i
                    if self.app == 0:
                        return self._comprar(economia,
                                             self.IDS_COMIDA, True)
                    if self.app == 1:
                        return self._comprar(economia,
                                             self.ids_insumos(arbol),
                                             False)
                    if self.app == 3:
                        return self._activar_mensaje(tratos, gestor)
                    if self.app == 4:
                        self._colocar_vendedor(economia, red)
                    elif self.app == 5:
                        self._alternar_venta(arbol, app_ventas)
                    elif self.app == 6:
                        return self._contratar(economia)
                    elif self.app == 7:
                        return self._contratar_equipo(economia)
        elif evento.type == pygame.MOUSEMOTION:
            if self.en_home:
                for i, r in enumerate(self._rects_home):
                    if r.collidepoint(evento.pos):
                        self.seleccion = i
            else:
                for i, r in enumerate(self._rects_items):
                    if r.collidepoint(evento.pos):
                        self.seleccion = i
        return None

    def _ev_home_teclado(self, evento):
        """Navegación de la grilla de íconos en la home screen."""
        n = len(self.APPS)
        if evento.key in (pygame.K_ESCAPE,):
            return "cerrar"
        if evento.key in (pygame.K_a, pygame.K_LEFT):
            self.seleccion = (self.seleccion - 1) % n
        elif evento.key in (pygame.K_d, pygame.K_RIGHT):
            self.seleccion = (self.seleccion + 1) % n
        elif evento.key in (pygame.K_w, pygame.K_UP):
            self.seleccion = (self.seleccion - 2) % n
        elif evento.key in (pygame.K_s, pygame.K_DOWN):
            self.seleccion = (self.seleccion + 2) % n
        elif evento.key in (pygame.K_RETURN, pygame.K_e, pygame.K_SPACE):
            self.app = self.seleccion
            self.en_home = False
            self.mensaje = ""
        return None

    def _vendedores_visibles(self, red):
        return [v for v in red.vendedores if v.descubierto]

    def _ev_red(self, evento, economia, red):
        """App Red: W/S elige vendedor, E lo coloca en su zona.
        La mercadería NO se entrega por acá: hay que ir en persona
        hasta el NPC del vendedor (E de cerca)."""
        visibles = self._vendedores_visibles(red)
        if not visibles:
            return None
        n = len(visibles)
        self.seleccion %= n
        if evento.key in (pygame.K_w, pygame.K_UP):
            self.seleccion = (self.seleccion - 1) % n
        elif evento.key in (pygame.K_s, pygame.K_DOWN):
            self.seleccion = (self.seleccion + 1) % n
        elif evento.key in (pygame.K_RETURN, pygame.K_e, pygame.K_SPACE):
            self._colocar_vendedor(economia, red)
        return None

    def _colocar_vendedor(self, economia, red):
        visibles = self._vendedores_visibles(red)
        if not visibles:
            return
        vendedor = visibles[self.seleccion % len(visibles)]
        if vendedor.colocado:
            self.mensaje = f"{vendedor.nombre} ya está trabajando ahí."
            self.color_mensaje = COLOR_TEXTO_SUAVE
        elif red.colocar(vendedor):
            self.mensaje = f"{vendedor.nombre} vende en {vendedor.nombre_zona}."
            self.color_mensaje = COLOR_DINERO
        else:
            self.mensaje = ("Todavía no es tuya esa zona — "
                            "eliminá a sus matones.")
            self.color_mensaje = COLOR_ERROR

    def _ev_ventas(self, evento, arbol, app_ventas):
        """App Ventas: W/S elige un medicamento investigado,
        E/Enter alterna su casilla "a la venta". Los clientes del
        celular solo piden lo que esté prendido."""
        if arbol is None or app_ventas is None:
            return None
        catalogo = app_ventas.catalogo(arbol)
        if not catalogo:
            return None
        n = len(catalogo)
        self.seleccion %= n
        if evento.key in (pygame.K_w, pygame.K_UP):
            self.seleccion = (self.seleccion - 1) % n
        elif evento.key in (pygame.K_s, pygame.K_DOWN):
            self.seleccion = (self.seleccion + 1) % n
        elif evento.key in (pygame.K_RETURN, pygame.K_e, pygame.K_SPACE):
            self._alternar_venta(arbol, app_ventas)
        return None

    def _alternar_venta(self, arbol, app_ventas):
        if arbol is None or app_ventas is None:
            return
        catalogo = app_ventas.catalogo(arbol)
        if not catalogo:
            return
        producto = catalogo[self.seleccion % len(catalogo)][0]
        prendido = app_ventas.alternar(producto, arbol)
        nombre = PRODUCTOS[producto]["nombre"]
        if prendido:
            self.mensaje = f"{nombre}: A LA VENTA."
            self.color_mensaje = COLOR_DINERO
        else:
            self.mensaje = f"{nombre}: retirado del catálogo."
            self.color_mensaje = COLOR_TEXTO_SUAVE

    def _ev_personal(self, evento, economia):
        """App Personal: W/S elige empleado, E/Enter lo contrata.
        El pago real lo hace main.py al recibir la acción."""
        n = 3
        self.seleccion %= n
        if evento.key in (pygame.K_w, pygame.K_UP):
            self.seleccion = (self.seleccion - 1) % n
        elif evento.key in (pygame.K_s, pygame.K_DOWN):
            self.seleccion = (self.seleccion + 1) % n
        elif evento.key in (pygame.K_RETURN, pygame.K_e, pygame.K_SPACE):
            return self._contratar(economia)
        return None

    def _contratar(self, economia):
        """Valida la contratación del empleado elegido. Devuelve
        ("contratar_mozo",) / ("contratar_chef",) /
        ("contratar_repositor",) o None con mensaje."""
        # (nombre, ya contratado, requisito cumplido, mensaje si
        # falta el requisito, precio, acción)
        puestos = [
            ("mozo", economia.tiene_mozo, True, "",
             PRECIO_MOZO, ("contratar_mozo",)),
            ("chef", economia.tiene_chef, economia.tiene_mozo,
             "Primero contratá al mozo.",
             PRECIO_CHEF, ("contratar_chef",)),
            ("repositor", economia.tiene_repositor, economia.tiene_chef,
             "Primero contratá al chef.",
             PRECIO_REPOSITOR, ("contratar_repositor",)),
        ]
        (nombre, contratado, habilitado, falta,
         precio, accion) = puestos[self.seleccion % len(puestos)]
        if not habilitado:
            self.mensaje = falta
            self.color_mensaje = COLOR_ERROR
        elif contratado:
            self.mensaje = f"El {nombre} ya trabaja para vos."
            self.color_mensaje = COLOR_TEXTO_SUAVE
        elif economia.dinero < precio:
            self.mensaje = "No te alcanza."
            self.color_mensaje = COLOR_ERROR
        else:
            self.mensaje = f"¡{nombre.capitalize()} contratado!"
            self.color_mensaje = COLOR_DINERO
            return accion
        return None

    def _ev_equipo(self, evento, economia):
        """App Equipo: el personal del laboratorio (sótano)."""
        n = 3
        self.seleccion %= n
        if evento.key in (pygame.K_w, pygame.K_UP):
            self.seleccion = (self.seleccion - 1) % n
        elif evento.key in (pygame.K_s, pygame.K_DOWN):
            self.seleccion = (self.seleccion + 1) % n
        elif evento.key in (pygame.K_RETURN, pygame.K_e, pygame.K_SPACE):
            return self._contratar_equipo(economia)
        return None

    def _contratar_equipo(self, economia):
        """Valida la contratación del equipo del laboratorio.
        Devuelve ("contratar_conseguidor",) / ("contratar_quimico",)
        / ("contratar_empaquetador",) o None con mensaje."""
        if not economia.meds_desbloqueados:
            self.mensaje = "Número fuera de servicio."
            self.color_mensaje = COLOR_ERROR
            return None
        puestos = [
            ("conseguidor", economia.tiene_conseguidor, True, "",
             PRECIO_CONSEGUIDOR, ("contratar_conseguidor",)),
            ("químico", economia.tiene_quimico,
             economia.tiene_conseguidor,
             "Primero contratá al conseguidor.",
             PRECIO_QUIMICO, ("contratar_quimico",)),
            ("empaquetador", economia.tiene_empaquetador,
             economia.tiene_quimico,
             "Primero contratá al químico.",
             PRECIO_EMPAQUETADOR, ("contratar_empaquetador",)),
        ]
        (nombre, contratado, habilitado, falta,
         precio, accion) = puestos[self.seleccion % len(puestos)]
        if not habilitado:
            self.mensaje = falta
            self.color_mensaje = COLOR_ERROR
        elif contratado:
            self.mensaje = f"El {nombre} ya trabaja para vos."
            self.color_mensaje = COLOR_TEXTO_SUAVE
        elif economia.dinero < precio:
            self.mensaje = "No te alcanza."
            self.color_mensaje = COLOR_ERROR
        else:
            self.mensaje = f"¡{nombre.capitalize()} contratado!"
            self.color_mensaje = COLOR_DINERO
            return accion
        return None

    def _ev_lista(self, evento, economia, ids, es_comida):
        n = max(1, len(ids))
        if evento.key in (pygame.K_w, pygame.K_UP):
            self.seleccion = (self.seleccion - 1) % n
        elif evento.key in (pygame.K_s, pygame.K_DOWN):
            self.seleccion = (self.seleccion + 1) % n
        elif evento.key in (pygame.K_RETURN, pygame.K_e, pygame.K_SPACE):
            return self._comprar(economia, ids, es_comida)
        return None

    def _ev_mensajes(self, evento, tratos, gestor):
        """Mensajes del jefe: primero las alertas del GestorEventos
        (soborno pagable, flash informativo) y después las ofertas."""
        alertas = list(gestor.eventos)
        ofertas = [t for t in tratos if t.estado == "oferta"]
        n = len(alertas) + len(ofertas)
        if not n:
            return None
        self.seleccion %= n
        if evento.key in (pygame.K_w, pygame.K_UP):
            self.seleccion = (self.seleccion - 1) % n
        elif evento.key in (pygame.K_s, pygame.K_DOWN):
            self.seleccion = (self.seleccion + 1) % n
        elif evento.key in (pygame.K_RETURN, pygame.K_e, pygame.K_SPACE):
            return self._activar_mensaje(tratos, gestor)
        elif evento.key == pygame.K_x:
            idx = self.seleccion - len(alertas)
            if 0 <= idx < len(ofertas):
                return ("rechazar", ofertas[idx])
        return None

    def _activar_mensaje(self, tratos, gestor):
        """E sobre un mensaje: pagar el soborno, ver la oferta flash
        o aceptar un trato."""
        alertas = list(gestor.eventos)
        ofertas = [t for t in tratos if t.estado == "oferta"]
        i = self.seleccion
        if i < len(alertas):
            evento = alertas[i]
            if evento.tipo_evento == "soborno":
                return ("pagar_soborno", evento)
            self.mensaje = (f"¡Corré a {evento.nombre_zona}!"
                            f" Quedan {int(evento.timer)}s.")
            self.color_mensaje = COLOR_ORO
            return None
        i -= len(alertas)
        if i < len(ofertas):
            return ("aceptar", ofertas[i])
        return None

    def _comprar(self, economia, ids, es_comida):
        if self.seleccion >= len(ids):
            return None
        id_pedido = ids[self.seleccion]
        if not es_comida and not economia.meds_desbloqueados:
            self.mensaje = "Número fuera de servicio."; self.color_mensaje = COLOR_ERROR
            return None
        _, _, costo = PEDIDOS[id_pedido]
        if economia.pagar(costo):
            self.mensaje = f"En camino (~{int(TIEMPO_ENTREGA)}s a la puerta)."
            self.color_mensaje = COLOR_DINERO
            return ("pedido", id_pedido)
        self.mensaje = "No te alcanza la plata."; self.color_mensaje = COLOR_ERROR
        return None

    # ── dibujo principal ───────────────────────────────────
    def dibujar(self, superficie, economia, tratos, reloj, mapa,
                jugador, red, gestor, arbol=None, app_ventas=None):
        velo = _panel(ANCHO_VENTANA, ALTO_VENTANA, alpha=150)
        superficie.blit(velo, (0, 0))

        if self.es_paisaje:
            aw, ah = self.ANCHO_LAND, self.ALTO_LAND
        else:
            aw, ah = self.ANCHO_TEL, self.ALTO_TEL
        x = (ANCHO_VENTANA - aw) // 2
        y = (ALTO_VENTANA - ah) // 2

        pygame.draw.rect(superficie.raw, COLOR_CELULAR,
                         (x, y, aw, ah), border_radius=24)
        pygame.draw.rect(superficie.raw, COLOR_CELULAR_BORDE,
                         (x, y, aw, ah), 2, border_radius=24)

        if self.en_home:
            self._home_screen(superficie, x, y, aw, ah, tratos, reloj,
                              gestor)
        elif self.es_paisaje:
            self._frame_land(superficie, x, y, aw, ah,
                             mapa, jugador, tratos, red, reloj, gestor)
        else:
            self._frame_port(superficie, x, y, aw, ah,
                             economia, tratos, reloj, red, gestor,
                             arbol, app_ventas)

        pie_txt = ("WASD — nav  ·  ENTER — abrir  ·  C — cerrar"
                   if self.en_home else
                   "ESC — volver al home  ·  C — cerrar")
        pie = self.fuente_chica.render(pie_txt, True, COLOR_TEXTO_SUAVE)
        # Clampeado: que el pie nunca quede cortado por el borde de
        # abajo (con el teléfono vertical y+ah+6 se pasaba de 540)
        py = min(y + ah + 6, ALTO_VENTANA - pie.get_height() - 2)
        superficie.blit(pie, ((ANCHO_VENTANA - pie.get_width()) // 2, py))

    # ── Home screen (grilla 2×2 de apps) ──────────────────
    def _home_screen(self, sup, x, y, aw, ah, tratos, reloj,
                     gestor=None):
        """Pantalla de inicio con íconos de las apps."""
        pygame.draw.rect(sup.raw, (10, 10, 12),
                         (x + aw // 2 - 28, y + 10, 56, 13), border_radius=7)
        pant = pygame.Rect(x + 10, y + 32, aw - 20, ah - 52)
        pygame.draw.rect(sup.raw, COLOR_PANTALLA_CEL, pant, border_radius=8)
        self._status_bar(sup, pant, reloj)

        lbl = self.fuente_chica.render("Fast Empire OS", True, COLOR_ORO)
        sup.blit(lbl, (pant.centerx - lbl.get_width() // 2, pant.y + 28))

        TAM = 64
        GAP = 16
        etq_h = 16
        bloque_h = TAM + GAP + etq_h
        filas = (len(self._APP_INFO) + 1) // 2
        total_w = TAM * 2 + GAP
        total_h = bloque_h * filas - GAP
        ox = pant.centerx - total_w // 2
        oy = pant.centery - total_h // 2 + 16

        self._rects_home = []
        ofertas = sum(1 for t in tratos if t.estado == "oferta")
        if gestor is not None:
            ofertas += len(gestor.eventos)   # alertas sin atender

        for i, (nombre, color) in enumerate(self._APP_INFO):
            col = i % 2
            fila = i // 2
            rx = ox + col * (TAM + GAP)
            ry = oy + fila * bloque_h
            rect = pygame.Rect(rx, ry, TAM, TAM)
            self._rects_home.append(rect)

            pygame.draw.rect(sup.raw, color, rect, border_radius=14)
            if i == self.seleccion:
                pygame.draw.rect(sup.raw, COLOR_ORO, rect, 2, border_radius=14)

            cx, cy = rect.centerx, rect.centery

            if i == 0:  # Comidas: bowl con vapor
                bowl = pygame.Rect(cx - 16, cy - 2, 32, 16)
                pygame.draw.ellipse(sup.raw, (255, 200, 80), bowl)
                pygame.draw.ellipse(sup.raw, (200, 140, 40), bowl, 2)
                for vx in (cx - 8, cx, cx + 8):
                    for dy in range(3):
                        pygame.draw.circle(sup.raw, (255, 255, 255),
                                           (vx, cy - 8 - dy * 4), 1)
            elif i == 1:  # Ilegales: pastilla bicolor
                left = pygame.Rect(cx - 18, cy - 9, 18, 18)
                right = pygame.Rect(cx, cy - 9, 18, 18)
                pygame.draw.ellipse(sup.raw, (200, 60, 60), left)
                pygame.draw.ellipse(sup.raw, (200, 200, 200), right)
                pygame.draw.ellipse(sup.raw, (160, 160, 160),
                                    pygame.Rect(cx - 18, cy - 9, 36, 18), 2)
                pygame.draw.line(sup.raw, (120, 120, 120),
                                 (cx, cy - 9), (cx, cy + 9), 2)
            elif i == 2:  # Mapa: pin de localización
                pygame.draw.circle(sup.raw, (200, 220, 255), (cx, cy - 10), 12)
                pygame.draw.circle(sup.raw, color, (cx, cy - 10), 5)
                pts = [(cx, cy + 18), (cx - 8, cy - 2), (cx + 8, cy - 2)]
                pygame.draw.polygon(sup.raw, (200, 220, 255), pts)
            elif i == 3:  # Mensajes: burbuja de chat
                bub = pygame.Rect(cx - 18, cy - 14, 36, 24)
                pygame.draw.rect(sup.raw, (200, 240, 220), bub, border_radius=7)
                pts = [(cx - 6, cy + 10), (cx - 16, cy + 20), (cx + 4, cy + 10)]
                pygame.draw.polygon(sup.raw, (200, 240, 220), pts)
                for dy_off in (-8, -2, 4):
                    pygame.draw.line(sup.raw, (80, 160, 110),
                                     (cx - 12, cy + dy_off),
                                     (cx + 12, cy + dy_off), 1)
                if ofertas > 0:
                    bpos = (rect.right - 9, rect.top + 9)
                    pygame.draw.circle(sup.raw, (220, 40, 40), bpos, 10)
                    badge = self.fuente_mini.render(str(ofertas), True, (255, 255, 255))
                    sup.blit(badge, (bpos[0] - badge.get_width() // 2,
                                    bpos[1] - badge.get_height() // 2))
            elif i == 4:  # Red: nodos conectados (la organización)
                nodos = [(cx, cy - 12), (cx - 13, cy + 9), (cx + 13, cy + 9)]
                for na in nodos:
                    for nb in nodos:
                        pygame.draw.line(sup.raw, (200, 170, 230), na, nb, 2)
                for n_pos in nodos:
                    pygame.draw.circle(sup.raw, (230, 210, 250), n_pos, 6)
                    pygame.draw.circle(sup.raw, color, n_pos, 3)
            elif i == 5:  # Ventas: etiqueta de precio con $
                pts = [(cx - 17, cy - 11), (cx + 5, cy - 11), (cx + 17, cy),
                       (cx + 5, cy + 11), (cx - 17, cy + 11)]
                pygame.draw.polygon(sup.raw, (250, 232, 190), pts)
                pygame.draw.polygon(sup.raw, (150, 115, 30), pts, 2)
                pygame.draw.circle(sup.raw, (150, 115, 30), (cx - 11, cy), 2)
                dolar = self.fuente_chica.render("$", True, (90, 65, 15))
                sup.blit(dolar, (cx - dolar.get_width() // 2 + 3,
                                 cy - dolar.get_height() // 2))
            elif i == 6:  # Personal: empleado con delantal
                pygame.draw.circle(sup.raw, (235, 220, 200), (cx, cy - 10), 7)
                torso = pygame.Rect(cx - 10, cy - 1, 20, 18)
                pygame.draw.rect(sup.raw, (235, 220, 200), torso,
                                 border_radius=6)
                pygame.draw.rect(sup.raw, (210, 165, 80),
                                 (cx - 5, cy + 3, 10, 14), border_radius=3)
            elif i == 7:  # Equipo: frasco de laboratorio burbujeante
                pygame.draw.rect(sup.raw, (220, 230, 240),
                                 (cx - 4, cy - 14, 8, 6))
                pygame.draw.polygon(sup.raw, (220, 230, 240),
                                    [(cx - 4, cy - 8), (cx + 4, cy - 8),
                                     (cx + 12, cy + 12), (cx - 12, cy + 12)])
                pygame.draw.polygon(sup.raw, (190, 140, 255),
                                    [(cx - 8, cy + 2), (cx + 8, cy + 2),
                                     (cx + 12, cy + 12), (cx - 12, cy + 12)])
                for bx, by in ((cx - 3, cy - 2), (cx + 4, cy - 5)):
                    pygame.draw.circle(sup.raw, (230, 200, 255), (bx, by), 2)

            etq = self.fuente_chica.render(nombre, True, COLOR_TEXTO)
            sup.blit(etq, (rect.centerx - etq.get_width() // 2, rect.bottom + 4))

    # ── Portrait (apps 0, 1, 3, 4, 5) ──────────────────────
    def _frame_port(self, sup, x, y, aw, ah, economia, tratos, reloj,
                    red, gestor, arbol=None, app_ventas=None):
        # Notch + pantalla (toda la altura: no hay barra de apps,
        # se vuelve al home con ESC para cambiar de app)
        pygame.draw.rect(sup.raw, (10, 10, 12),
                         (x + aw // 2 - 28, y + 10, 56, 13), border_radius=7)
        pant = pygame.Rect(x + 10, y + 32, aw - 20, ah - 52)
        pygame.draw.rect(sup.raw, COLOR_PANTALLA_CEL, pant, border_radius=8)
        self._status_bar(sup, pant, reloj)
        cont = pygame.Rect(pant.x, pant.y + 24, pant.width, pant.height - 24)
        if self.app == 0:
            self._app_lista(sup, cont, economia,
                            "Comidas", self.IDS_COMIDA, True)
        elif self.app == 1:
            self._app_lista(sup, cont, economia,
                            "Insumos", self.ids_insumos(arbol), False)
        elif self.app == 4:
            self._app_red(sup, cont, economia, red)
        elif self.app == 5:
            self._app_ventas(sup, cont, economia, arbol, app_ventas)
        elif self.app == 6:
            self._app_personal(sup, cont, economia)
        elif self.app == 7:
            self._app_equipo(sup, cont, economia)
        else:
            self._app_mensajes(sup, cont, tratos, reloj, gestor)

    def _status_bar(self, sup, pant, reloj):
        hora = self.fuente_chica.render(
            f"{reloj.hora:02d}:{reloj.minuto:02d}", True, COLOR_TEXTO)
        sup.blit(hora, (pant.x + 8, pant.y + 5))
        for i in range(4):
            hb = 3 + i * 2
            pygame.draw.rect(sup.raw, COLOR_TEXTO_SUAVE,
                             (pant.right - 66 + i * 6,
                              pant.y + 14 - hb, 4, hb))
        pygame.draw.rect(sup.raw, COLOR_TEXTO_SUAVE,
                         (pant.right - 34, pant.y + 5, 22, 10), 1)
        pygame.draw.rect(sup.raw, COLOR_DINERO,
                         (pant.right - 32, pant.y + 7, 14, 6))

    # ── Landscape (app Mapa) ───────────────────────────────
    def _frame_land(self, sup, x, y, aw, ah,
                    mapa, jugador, tratos, red, reloj, gestor):
        # Notch en lado izquierdo
        pygame.draw.rect(sup.raw, (10, 10, 12),
                         (x + 10, y + ah // 2 - 20, 13, 40), border_radius=7)
        # Pantalla: margen izq=32, der=40, top=10, bot=12
        pant = pygame.Rect(x + 32, y + 10, aw - 72, ah - 22)
        pygame.draw.rect(sup.raw, COLOR_PANTALLA_CEL, pant, border_radius=8)
        # Título dentro de la pantalla
        lbl = self.fuente_chica.render(
            f"{reloj.hora:02d}:{reloj.minuto:02d}  —  Mapa de la ciudad",
            True, COLOR_ORO)
        sup.blit(lbl, (pant.centerx - lbl.get_width() // 2, pant.y + 5))
        # Zona del mapa (a lo ancho: sin barra de apps, se vuelve
        # al home con ESC para cambiar de app)
        zona = pygame.Rect(pant.x, pant.y + 22, pant.width, pant.height - 22)
        self._app_mapa_land(sup, zona, mapa, jugador, tratos, red, gestor)

    # ── Apps ───────────────────────────────────────────────
    def _app_lista(self, sup, zona, economia, titulo, ids, es_comida):
        sup.blit(self.fuente_titulo.render(titulo, True, COLOR_ORO),
                 (zona.x + 10, zona.y + 4))
        plata = self.fuente_chica.render(f"$ {economia.dinero}", True, COLOR_DINERO)
        sup.blit(plata, (zona.right - plata.get_width() - 10, zona.y + 10))

        if not es_comida and not economia.meds_desbloqueados:
            m1 = self.fuente.render("App bloqueada", True, (100, 100, 110))
            m2 = self.fuente_chica.render(
                "Hacé más ventas para desbloquear.", True, COLOR_TEXTO_SUAVE)
            sup.blit(m1, (zona.centerx - m1.get_width() // 2, zona.centery - 20))
            sup.blit(m2, (zona.centerx - m2.get_width() // 2, zona.centery + 10))
            self._rects_items = []
            return

        self._rects_items = []
        y = zona.y + 38
        for i, id_p in enumerate(ids):
            nombre_p, _, precio = PEDIDOS[id_p]
            r = pygame.Rect(zona.x + 6, y, zona.width - 12, 42)
            self._rects_items.append(r)
            elegido = i == self.seleccion
            pygame.draw.rect(sup.raw, (36, 38, 48) if elegido else (24, 26, 34),
                             r, border_radius=6)
            if elegido:
                pygame.draw.rect(sup.raw, COLOR_APP_ACTIVA, r, 1, border_radius=6)
            sup.blit(self.fuente_chica.render(nombre_p, True, COLOR_TEXTO),
                     (r.x + 8, r.y + 6))
            sup.blit(self.fuente_chica.render(f"${precio}", True, COLOR_DINERO),
                     (r.x + 8, r.y + 23))
            y += 46

        if self.mensaje:
            sup.blit(self.fuente_chica.render(
                self.mensaje, True, self.color_mensaje), (zona.x + 8, zona.bottom - 24))

    def _prerender_minimapa(self, mapa):
        """El plano del celular muestra SOLO la ciudad: el subsuelo
        (la instancia del sótano) no sale en los planos."""
        from .map import MAPA, FILAS_CIUDAD
        escala = 2
        sup = pygame.Surface((mapa.columnas * escala,
                              FILAS_CIUDAD * escala))
        colores = {
            "X": COLOR_EDIFICIO, "H": COLOR_CASA, "A": COLOR_ARBOL,
            "k": COLOR_TIENDA_TOLDO, "C": COLOR_PISO_LOCAL,
            "M": COLOR_PISO_LOCAL, "F": COLOR_PISO_LOCAL,
            "p": COLOR_PISO_LOCAL, "T": COLOR_TIENDA_TOLDO,
            "B": COLOR_BANCO,  "S": COLOR_HOSPITAL, "w": COLOR_AGUA,
            ".": COLOR_CALLE,  ",": COLOR_PASTO,    "~": COLOR_TIERRA,
            "D": COLOR_PISO_LOCAL,
        }
        for fila, linea in enumerate(MAPA[:FILAS_CIUDAD]):
            for col, tile in enumerate(linea):
                sup.fill(colores.get(tile, COLOR_CALLE),
                         (col * escala, fila * escala, escala, escala))
        return sup

    def _app_mapa_land(self, sup, zona, mapa, jugador, tratos, red,
                       gestor=None):
        """Mapa en horizontal: mapa a la izquierda + leyenda a la derecha."""
        from .economy import LUGARES_VENTA
        from .map import FILAS_CIUDAD, Y_SUBSUELO
        if self._minimapa is None:
            self._minimapa = self._prerender_minimapa(mapa)
        mm = self._minimapa            # 240×200 px (2px/tile)

        ANCHO_LEY = 172
        zona_mm_w = zona.width - ANCHO_LEY - 6

        # Escalar mapa para que quepa en la sección izquierda
        esc = min(zona_mm_w / mm.get_width(), zona.height / mm.get_height())
        mw = int(mm.get_width()  * esc)
        mh = int(mm.get_height() * esc)
        mm_s = pygame.transform.scale(mm, (mw, mh))
        mx = zona.x + (zona_mm_w - mw) // 2
        my = zona.y + (zona.height - mh) // 2
        sup.blit(mm_s, (mx, my))
        pygame.draw.rect(sup.raw, COLOR_CELULAR_BORDE,
                         (mx - 1, my - 1, mw + 2, mh + 2), 1)

        def pt(col_t, fil_t):          # tile → pantalla (solo ciudad)
            return (mx + col_t * mw // mapa.columnas,
                    my + fil_t * mh // FILAS_CIUDAD)

        def pt_px(pos_px):             # pixel mundo → pantalla
            return (mx + int(pos_px[0] / mapa.ancho_px * mw),
                    my + min(mh, int(pos_px[1] / Y_SUBSUELO * mh)))

        # Local principal (dorado)
        p_loc = pt(4, 4)
        pygame.draw.circle(sup.raw, COLOR_ORO, p_loc, 5)
        lbl_loc = self.fuente_mini.render("Local", True, COLOR_ORO)
        sup.blit(lbl_loc, (p_loc[0] + 6, p_loc[1] - 5))

        # Zonas de venta, coloreadas por estado de la Red:
        # verde = asegurada · naranja = limpiada SIN proteger ·
        # rojo = en disputa (matones) · gris = bloqueada
        VERDE, ROJO, GRIS = (110, 220, 110), (235, 80, 70), (110, 110, 118)
        NARANJA = (240, 175, 60)
        conquistadas = set(red.zonas_conquistadas())
        disputa = set(red.zonas_en_disputa())
        ticks_mapa = pygame.time.get_ticks()
        for idx, (_, (col, fil, aw, af)) in enumerate(LUGARES_VENTA):
            px = pt(col + aw // 2, fil + af // 2)
            if idx in red.vulnerables:
                # Parpadea: el reloj de reconquista está corriendo
                color_z = (NARANJA if (ticks_mapa // 400) % 2 == 0
                           else (160, 110, 35))
            elif idx == 0 or idx in conquistadas:
                color_z = VERDE
            elif idx in disputa:
                # Parpadea: ahí hay matones esperándote
                color_z = ROJO if (ticks_mapa // 400) % 2 == 0 else (150, 50, 45)
            else:
                color_z = GRIS
            pygame.draw.circle(sup.raw, color_z, px, 4)
            num = self.fuente_mini.render(str(idx + 1), True, (15, 15, 15))
            sup.blit(num, (px[0] - num.get_width() // 2,
                           px[1] - num.get_height() // 2))

        # Tratos
        ticks = pygame.time.get_ticks()
        for trato in tratos:
            if trato.estado in ("aceptado", "encuentro"):
                p = pt_px(trato.rect.center)
                if trato.estado == "encuentro" and (ticks // 400) % 2 == 0:
                    pygame.draw.circle(sup.raw, COLOR_PUNTO, p, 5)
                else:
                    pygame.draw.circle(sup.raw, COLOR_PUNTO, p, 4, 1)

        # Cargamento flash: dorado, parpadeo urgente
        flash = gestor.flash_activo() if gestor is not None else None
        if flash is not None and (ticks // 250) % 2 == 0:
            pygame.draw.circle(sup.raw, COLOR_ORO, pt_px(flash.punto()), 6, 2)

        # Walter (parpadea)
        if (ticks // 300) % 2 == 0:
            pygame.draw.circle(sup.raw, COLOR_TEXTO, pt_px(jugador.rect.center), 4)

        # ── Leyenda ──
        lx = zona.x + zona_mm_w + 6
        ly = zona.y + 2
        pygame.draw.rect(sup.raw, (16, 16, 22),
                         (lx - 2, ly, ANCHO_LEY + 2, zona.height))
        for color, etq in [(COLOR_TEXTO,  "Vos"),
                           (COLOR_ORO,    "Tu local"),
                           (VERDE,        "Zonas de la Red"),
                           (NARANJA,      "¡Sin proteger!"),
                           (ROJO,         "En disputa (matones)"),
                           (GRIS,         "Bloqueadas"),
                           (COLOR_PUNTO,  "Tratos pendientes")]:
            pygame.draw.circle(sup.raw, color, (lx + 5, ly + 7), 4)
            img = self.fuente_mini.render(etq, True, COLOR_TEXTO_SUAVE)
            sup.blit(img, (lx + 14, ly))
            ly += 16
        ly += 4
        for idx, (nombre, _) in enumerate(LUGARES_VENTA):
            if ly + 13 > zona.bottom:
                break
            img = self.fuente_mini.render(
                f"{idx + 1}. {nombre}", True, COLOR_TEXTO)
            sup.blit(img, (lx, ly))
            ly += 13
        self._rects_items = []

    def _app_red(self, sup, zona, economia, red):
        """La organización: contactos, dónde trabajan, su stock y
        cuánto falta para el próximo contacto."""
        sup.blit(self.fuente_titulo.render("La Red", True, COLOR_ORO),
                 (zona.x + 10, zona.y + 4))
        plata = self.fuente_chica.render(
            f"N:{economia.med_nat} Q:{economia.med_quim}", True, COLOR_DINERO)
        sup.blit(plata, (zona.right - plata.get_width() - 10, zona.y + 10))

        self._rects_items = []
        y = zona.y + 36
        visibles = self._vendedores_visibles(red)

        if not visibles:
            faltan = max(0, VENTAS_PARA_CONTACTO - red.ventas_parque)
            lineas = ["Todavía no tenés contactos.",
                      "Vendé en el Parque del Norte para",
                      "ganarte la confianza del barrio:",
                      f"ventas {red.ventas_parque}/{VENTAS_PARA_CONTACTO}"
                      f"  (faltan {faltan})"]
            for txt in lineas:
                sup.blit(self.fuente_chica.render(txt, True, COLOR_TEXTO_SUAVE),
                         (zona.x + 10, y))
                y += 22
            return

        for i, vendedor in enumerate(visibles):
            r = pygame.Rect(zona.x + 6, y, zona.width - 12, 58)
            self._rects_items.append(r)
            elegido = i == (self.seleccion % len(visibles))
            pygame.draw.rect(sup.raw, (36, 38, 48) if elegido else (24, 26, 34),
                             r, border_radius=8)
            if elegido:
                pygame.draw.rect(sup.raw, COLOR_APP_ACTIVA, r, 1, border_radius=8)
            titulo = f"{vendedor.nombre} — {vendedor.nombre_zona}"
            sup.blit(self.fuente_chica.render(titulo, True, COLOR_PUNTO),
                     (r.x + 8, r.y + 5))
            if vendedor.colocado:
                estado = (f"Stock N:{vendedor.stock_nat} Q:{vendedor.stock_quim}"
                          f"  ·  ventas {vendedor.ventas}")
                color_e = (COLOR_DINERO if vendedor.stock_total
                           else COLOR_ERROR)
                if not vendedor.stock_total:
                    estado += "  ·  ¡SIN STOCK!"
            elif vendedor.zona_idx in red.zonas_conquistadas():
                estado = "Listo para trabajar — E lo coloca"
                if vendedor.zona_idx in red.vulnerables:
                    segundos = int(red.vulnerables[vendedor.zona_idx])
                    estado += f"  ·  ¡{segundos}s o la perdés!"
                color_e = COLOR_ORO
            elif vendedor.zona_idx in red.vulnerables:
                segundos = int(red.vulnerables[vendedor.zona_idx])
                estado = (f"Zona limpiada — completá el grupo "
                          f"(¡{segundos}s!)")
                color_e = COLOR_ORO
            else:
                estado = "Esperando que limpies su zona…"
                color_e = COLOR_TEXTO_SUAVE
            sup.blit(self.fuente_chica.render(estado, True, color_e),
                     (r.x + 8, r.y + 24))
            # ¿Este es el que destraba al próximo contacto?
            if (i == len(visibles) - 1
                    and len(visibles) < len(red.vendedores)):
                progreso = min(vendedor.ventas, VENTAS_PARA_CONTACTO)
                sup.blit(self.fuente_mini.render(
                    f"Próximo contacto: {progreso}/{VENTAS_PARA_CONTACTO} ventas",
                    True, COLOR_TEXTO_SUAVE), (r.x + 8, r.y + 42))
            y += 62

        sup.blit(self.fuente_mini.render(
            f"E — colocar  ·  mercadería: llevásela EN PERSONA  ·  "
            f"comisión {int(COMISION_VENDEDOR * 100)}%",
            True, COLOR_TEXTO_SUAVE),
            (zona.x + 8, zona.bottom - 36))
        if self.mensaje:
            sup.blit(self.fuente_chica.render(
                self.mensaje, True, self.color_mensaje),
                (zona.x + 8, zona.bottom - 20))

    def _app_ventas(self, sup, zona, economia, arbol=None,
                    app_ventas=None):
        """App Ventas: una casilla por medicamento investigado.
        Lo prendido es lo ÚNICO que piden los clientes del celular
        (¿sin stock de un tier? apagalo y piden lo demás)."""
        sup.blit(self.fuente_titulo.render("Ventas", True, COLOR_ORO),
                 (zona.x + 10, zona.y + 4))
        self._rects_items = []
        if arbol is None or app_ventas is None:
            return
        catalogo = app_ventas.catalogo(arbol)
        if not catalogo:
            y = zona.centery - 40
            for txt in ("Catálogo vacío.", "",
                        "Investigá medicamentos en el",
                        "árbol de I+D (tecla R)."):
                img = self.fuente_chica.render(txt, True, COLOR_TEXTO_SUAVE)
                sup.blit(img, (zona.centerx - img.get_width() // 2, y))
                y += 22
            return

        y = zona.y + 38
        for i, (producto, prendido) in enumerate(catalogo):
            datos = PRODUCTOS[producto]
            r = pygame.Rect(zona.x + 6, y, zona.width - 12, 52)
            self._rects_items.append(r)
            elegido = i == self.seleccion
            pygame.draw.rect(sup.raw,
                             (36, 38, 48) if elegido else (24, 26, 34),
                             r, border_radius=8)
            if elegido:
                pygame.draw.rect(sup.raw, COLOR_APP_ACTIVA, r, 1,
                                 border_radius=8)
            # La casilla de "a la venta"
            caja = pygame.Rect(r.x + 8, r.centery - 8, 16, 16)
            pygame.draw.rect(sup.raw, (18, 20, 26), caja, border_radius=4)
            pygame.draw.rect(sup.raw,
                             COLOR_DINERO if prendido else COLOR_TEXTO_SUAVE,
                             caja, 1, border_radius=4)
            if prendido:
                pygame.draw.line(sup.raw, COLOR_DINERO,
                                 (caja.x + 3, caja.centery),
                                 (caja.centerx - 1, caja.bottom - 4), 2)
                pygame.draw.line(sup.raw, COLOR_DINERO,
                                 (caja.centerx - 1, caja.bottom - 4),
                                 (caja.right - 3, caja.y + 3), 2)
            color_n = COLOR_TEXTO if prendido else COLOR_TEXTO_SUAVE
            sup.blit(self.fuente_chica.render(
                f"{datos['nombre']}  (T{datos['tier']})", True, color_n),
                (r.x + 32, r.y + 7))
            stock = economia.stock_med(producto)
            sup.blit(self.fuente_mini.render(
                f"${datos['precio']} c/u  ·  stock encima: {stock}", True,
                COLOR_DINERO if prendido else COLOR_TEXTO_SUAVE),
                (r.x + 32, r.y + 28))
            y += 56

        sup.blit(self.fuente_mini.render(
            "E — a la venta sí/no  ·  los clientes piden solo lo prendido",
            True, COLOR_TEXTO_SUAVE), (zona.x + 8, zona.bottom - 36))
        if self.mensaje:
            sup.blit(self.fuente_chica.render(
                self.mensaje, True, self.color_mensaje),
                (zona.x + 8, zona.bottom - 20))

    def _app_personal(self, sup, zona, economia):
        """App Personal: contratar al personal del local. Cada
        puesto se desbloquea con el anterior trabajando:
        Mozo → Chef → Repositor."""
        sup.blit(self.fuente_titulo.render("Personal del local",
                                           True, COLOR_ORO),
                 (zona.x + 10, zona.y + 4))
        plata = self.fuente_chica.render(f"$ {economia.dinero}",
                                         True, COLOR_DINERO)
        sup.blit(plata, (zona.right - plata.get_width() - 10,
                         zona.bottom - 24))

        empleados = [
            ("Mozo", PRECIO_MOZO, economia.tiene_mozo, True,
             "Atiende la fila solo",
             f"Comisión: {round(COMISION_MOZO * 100)}% de cada venta",
             ""),
            ("Chef", PRECIO_CHEF, economia.tiene_chef,
             economia.tiene_mozo,
             "Cocina cuando hay fila",
             f"Sueldo: ${SUELDO_CHEF}/tanda",
             "Requiere Mozo"),
            ("Repositor", PRECIO_REPOSITOR, economia.tiene_repositor,
             economia.tiene_chef,
             "Lleva los ingredientes al chef",
             f"Sueldo: ${SUELDO_REPOSITOR}/caja",
             "Requiere Chef"),
        ]
        self._rects_items = []
        y = zona.y + 44
        for i, (nombre, precio, contratado, disponible,
                desc, sueldo, requisito) in enumerate(empleados):
            r = pygame.Rect(zona.x + 6, y, zona.width - 12, 92)
            self._rects_items.append(r)
            elegido = i == self.seleccion % len(empleados)
            pygame.draw.rect(sup.raw,
                             (36, 38, 48) if elegido else (24, 26, 34),
                             r, border_radius=8)
            if elegido:
                pygame.draw.rect(sup.raw, COLOR_APP_ACTIVA, r, 1,
                                 border_radius=8)
            # La casilla de contratado ([✓] / [►] / [ ])
            caja = pygame.Rect(r.x + 8, r.y + 8, 16, 16)
            pygame.draw.rect(sup.raw, (18, 20, 26), caja, border_radius=4)
            pygame.draw.rect(sup.raw,
                             COLOR_DINERO if contratado else COLOR_TEXTO_SUAVE,
                             caja, 1, border_radius=4)
            if contratado:
                pygame.draw.line(sup.raw, COLOR_DINERO,
                                 (caja.x + 3, caja.centery),
                                 (caja.centerx - 1, caja.bottom - 4), 2)
                pygame.draw.line(sup.raw, COLOR_DINERO,
                                 (caja.centerx - 1, caja.bottom - 4),
                                 (caja.right - 3, caja.y + 3), 2)
            elif disponible:
                pygame.draw.polygon(sup.raw, COLOR_ORO,
                                    [(caja.x + 5, caja.y + 4),
                                     (caja.x + 11, caja.centery),
                                     (caja.x + 5, caja.bottom - 4)])
            color_n = (COLOR_TEXTO if contratado or disponible
                       else COLOR_TEXTO_SUAVE)
            sup.blit(self.fuente_chica.render(nombre, True, color_n),
                     (r.x + 32, r.y + 7))
            if contratado:
                etq = self.fuente_chica.render("ACTIVO", True, COLOR_DINERO)
            else:
                etq = self.fuente_chica.render(
                    f"${precio}", True,
                    COLOR_DINERO if disponible else COLOR_TEXTO_SUAVE)
            sup.blit(etq, (r.right - etq.get_width() - 10, r.y + 7))
            color_d = (COLOR_TEXTO_SUAVE if contratado or disponible
                       else (100, 100, 110))
            sup.blit(self.fuente_chica.render(desc, True, color_d),
                     (r.x + 32, r.y + 30))
            sup.blit(self.fuente_chica.render(sueldo, True, color_d),
                     (r.x + 32, r.y + 50))
            if not contratado and not disponible:
                sup.blit(self.fuente_mini.render(
                    requisito, True, COLOR_ERROR),
                    (r.x + 32, r.y + 72))
            y += 98

        sup.blit(self.fuente_mini.render(
            "E — contratar  ·  si matan al empleado, perdés la contratación",
            True, COLOR_TEXTO_SUAVE), (zona.x + 8, zona.bottom - 40))
        if self.mensaje:
            sup.blit(self.fuente_chica.render(
                self.mensaje, True, self.color_mensaje),
                (zona.x + 8, zona.bottom - 24))

    def _app_equipo(self, sup, zona, economia):
        """App Equipo: el personal del LABORATORIO. Trabajan solo
        con el estante del sótano, en cadena:
        Conseguidor → Químico → Empaquetador."""
        sup.blit(self.fuente_titulo.render("Equipo del laboratorio",
                                           True, COLOR_ORO),
                 (zona.x + 10, zona.y + 4))
        plata = self.fuente_chica.render(f"$ {economia.dinero}",
                                         True, COLOR_DINERO)
        sup.blit(plata, (zona.right - plata.get_width() - 10,
                         zona.bottom - 24))

        if not economia.meds_desbloqueados:
            sup.blit(self.fuente_chica.render(
                "Número fuera de servicio.", True, COLOR_TEXTO_SUAVE),
                (zona.x + 10, zona.y + 48))
            return

        empleados = [
            ("Conseguidor", PRECIO_CONSEGUIDOR,
             economia.tiene_conseguidor, True,
             "Compra insumos y los deja en el estante",
             f"Comisión: ${SUELDO_CONSEGUIDOR}/viaje + el pedido",
             ""),
            ("Químico", PRECIO_QUIMICO, economia.tiene_quimico,
             economia.tiene_conseguidor,
             "Cocina compuestos del estante → crudo",
             f"Sueldo: ${SUELDO_QUIMICO}/tanda",
             "Requiere Conseguidor"),
            ("Empaquetador", PRECIO_EMPAQUETADOR,
             economia.tiene_empaquetador, economia.tiene_quimico,
             "Embolsa lo del estante en la mesa",
             f"Sueldo: ${SUELDO_EMPAQUETADOR}/unidad",
             "Requiere Químico"),
        ]
        self._rects_items = []
        y = zona.y + 44
        for i, (nombre, precio, contratado, disponible,
                desc, sueldo, requisito) in enumerate(empleados):
            r = pygame.Rect(zona.x + 6, y, zona.width - 12, 92)
            self._rects_items.append(r)
            elegido = i == self.seleccion % len(empleados)
            pygame.draw.rect(sup.raw,
                             (40, 32, 52) if elegido else (26, 22, 34),
                             r, border_radius=8)
            if elegido:
                pygame.draw.rect(sup.raw, COLOR_APP_ACTIVA, r, 1,
                                 border_radius=8)
            caja = pygame.Rect(r.x + 8, r.y + 8, 16, 16)
            pygame.draw.rect(sup.raw, (18, 20, 26), caja, border_radius=4)
            pygame.draw.rect(sup.raw,
                             COLOR_DINERO if contratado else COLOR_TEXTO_SUAVE,
                             caja, 1, border_radius=4)
            if contratado:
                pygame.draw.line(sup.raw, COLOR_DINERO,
                                 (caja.x + 3, caja.centery),
                                 (caja.centerx - 1, caja.bottom - 4), 2)
                pygame.draw.line(sup.raw, COLOR_DINERO,
                                 (caja.centerx - 1, caja.bottom - 4),
                                 (caja.right - 3, caja.y + 3), 2)
            elif disponible:
                pygame.draw.polygon(sup.raw, COLOR_ORO,
                                    [(caja.x + 5, caja.y + 4),
                                     (caja.x + 11, caja.centery),
                                     (caja.x + 5, caja.bottom - 4)])
            color_n = (COLOR_TEXTO if contratado or disponible
                       else COLOR_TEXTO_SUAVE)
            sup.blit(self.fuente_chica.render(nombre, True, color_n),
                     (r.x + 32, r.y + 7))
            if contratado:
                etq = self.fuente_chica.render("ACTIVO", True, COLOR_DINERO)
            else:
                etq = self.fuente_chica.render(
                    f"${precio}", True,
                    COLOR_DINERO if disponible else COLOR_TEXTO_SUAVE)
            sup.blit(etq, (r.right - etq.get_width() - 10, r.y + 7))
            color_d = (COLOR_TEXTO_SUAVE if contratado or disponible
                       else (100, 100, 110))
            sup.blit(self.fuente_chica.render(desc, True, color_d),
                     (r.x + 32, r.y + 30))
            sup.blit(self.fuente_chica.render(sueldo, True, color_d),
                     (r.x + 32, r.y + 50))
            if not contratado and not disponible:
                sup.blit(self.fuente_mini.render(
                    requisito, True, COLOR_ERROR),
                    (r.x + 32, r.y + 72))
            y += 98

        sup.blit(self.fuente_mini.render(
            "E — contratar  ·  trabajan con el ESTANTE del sótano",
            True, COLOR_TEXTO_SUAVE), (zona.x + 8, zona.bottom - 40))
        if self.mensaje:
            sup.blit(self.fuente_chica.render(
                self.mensaje, True, self.color_mensaje),
                (zona.x + 8, zona.bottom - 24))

    def _app_mensajes(self, sup, zona, tratos, reloj, gestor=None):
        sup.blit(self.fuente_titulo.render("Mensajes", True, COLOR_ORO),
                 (zona.x + 10, zona.y + 4))
        alertas   = list(gestor.eventos) if gestor is not None else []
        ofertas   = [t for t in tratos if t.estado == "oferta"]
        aceptados = [t for t in tratos if t.estado in ("aceptado", "encuentro")]
        self._rects_items = []
        y = zona.y + 36

        if not alertas and not ofertas and not aceptados:
            for txt in ("No hay mensajes nuevos.",
                        "Los contactos escriben solos…"):
                sup.blit(self.fuente_chica.render(txt, True, COLOR_TEXTO_SUAVE),
                         (zona.x + 10, y)); y += 22
            return

        # Alertas del jefe: soborno (se paga con E) y oferta flash
        for i, ev in enumerate(alertas):
            r = pygame.Rect(zona.x + 6, y, zona.width - 12, 74)
            self._rects_items.append(r)
            elegido = i == self.seleccion
            pygame.draw.rect(sup.raw, (44, 34, 34) if elegido else (32, 24, 24),
                             r, border_radius=8)
            es_soborno = ev.tipo_evento == "soborno"
            borde = COLOR_ERROR if es_soborno else COLOR_ORO
            pygame.draw.rect(sup.raw, borde, r, 1, border_radius=8)
            titulo_ev = ("POLICÍA — ¡PAGÁ O CIERRAN TODO!" if es_soborno
                         else "OFERTA FLASH — ¡CORRÉ!")
            sup.blit(self.fuente_chica.render(
                f"{titulo_ev}  ({int(ev.timer)}s)", True, borde),
                (r.x + 8, r.y + 5))
            for j, linea in enumerate(_envolver_lineas(
                    self.fuente_chica, ev.mensaje(reloj), r.width - 16)[:2]):
                sup.blit(self.fuente_chica.render(linea, True, COLOR_TEXTO),
                         (r.x + 8, r.y + 23 + j * 17))
            sup.blit(self.fuente_mini.render(
                "E — pagar ahora" if es_soborno else "andá al punto dorado"
                " del mapa", True, COLOR_TEXTO_SUAVE),
                (r.x + 8, r.y + 58))
            y += 80

        for i, trato in enumerate(ofertas):
            r = pygame.Rect(zona.x + 6, y, zona.width - 12, 74)
            self._rects_items.append(r)
            elegido = len(alertas) + i == self.seleccion
            pygame.draw.rect(sup.raw, (36, 38, 48) if elegido else (24, 26, 34),
                             r, border_radius=8)
            if elegido:
                pygame.draw.rect(sup.raw, COLOR_APP_ACTIVA, r, 1, border_radius=8)
            quien = trato.comprador_nombre + (" · VIP" if trato.vip else "")
            sup.blit(self.fuente_chica.render(
                quien, True, COLOR_ORO if trato.vip else COLOR_PUNTO),
                (r.x + 8, r.y + 5))
            for j, linea in enumerate(
                    _envolver_lineas(self.fuente_chica,
                                     trato.mensaje(reloj), r.width - 16)):
                sup.blit(self.fuente_chica.render(linea, True, COLOR_TEXTO),
                         (r.x + 8, r.y + 23 + j * 17))
            y += 80

        if ofertas:
            sup.blit(self.fuente_chica.render(
                "E — aceptar  ·  X — rechazar", True, COLOR_TEXTO_SUAVE),
                (zona.x + 10, y + 2)); y += 22

        for trato in aceptados:
            estado = ("TE ESPERA" if trato.estado == "encuentro"
                      else reloj.texto_hora(trato.minuto_cita))
            sup.blit(self.fuente_chica.render(
                f"✓ {trato.nombre_lugar} — {estado} — ${trato.total}",
                True, COLOR_DINERO), (zona.x + 10, y + 4))
            y += 20

        if self.mensaje:
            sup.blit(self.fuente_chica.render(
                self.mensaje, True, self.color_mensaje),
                (zona.x + 8, zona.bottom - 20))


def _envolver_lineas(fuente, texto, ancho_max):
    """Corta texto en renglones que entren en el ancho dado."""
    renglones, actual = [], ""
    for palabra in texto.split(" "):
        prueba = f"{actual} {palabra}".strip()
        if fuente.size(prueba)[0] <= ancho_max:
            actual = prueba
        else:
            renglones.append(actual)
            actual = palabra
    if actual:
        renglones.append(actual)
    return renglones


# ---------------------------------------------------------
# Banco del distrito sur: la plata depositada queda a salvo
# de multas por arresto y pérdidas por muerte
# ---------------------------------------------------------
class PantallaBanco(_MenuVertical):
    ITEMS = [
        ("dep100", "Depositar $100"),
        ("depTodo", "Depositar todo"),
        ("ret100", "Retirar $100"),
        ("retTodo", "Retirar todo"),
        ("salir", "Salir"),
    ]

    def __init__(self):
        super().__init__([etiqueta for _, etiqueta in self.ITEMS])
        self.fuente = FuenteUI(34)
        self.fuente_titulo = FuenteUI(56)
        self.fuente_chica = FuenteUI(24)
        self.mensaje = ""
        self.color_mensaje = COLOR_TEXTO

    def abrir(self):
        self.seleccion = 0
        self.mensaje = ""

    def manejar_evento(self, evento, economia):
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
            return "cerrar"
        i = self._navegar(evento)
        if i is None:
            return None
        id_item = self.ITEMS[i][0]
        if id_item == "salir":
            return "cerrar"
        if id_item == "dep100":
            movido = economia.depositar(100)
        elif id_item == "depTodo":
            movido = economia.depositar(economia.dinero)
        elif id_item == "ret100":
            movido = economia.retirar(100)
        else:
            movido = economia.retirar(economia.banco)
        if movido > 0:
            entrada = id_item.startswith("dep")
            self.mensaje = (f"Depositaste ${movido}." if entrada
                            else f"Retiraste ${movido}.")
            self.color_mensaje = COLOR_DINERO
        else:
            self.mensaje = "No hay nada para mover."
            self.color_mensaje = COLOR_ERROR
        return None

    def dibujar(self, superficie, economia):
        velo = _panel(ANCHO_VENTANA, ALTO_VENTANA, alpha=170)
        superficie.blit(velo, (0, 0))
        titulo = self.fuente_titulo.render("BANCO DEL SUR", True, COLOR_ORO)
        superficie.blit(titulo, ((ANCHO_VENTANA - titulo.get_width()) // 2, 80))
        info = self.fuente_chica.render(
            f"Efectivo: $ {economia.dinero}   ·   En caja fuerte: $ {economia.banco}",
            True, COLOR_TEXTO)
        superficie.blit(info, ((ANCHO_VENTANA - info.get_width()) // 2, 140))
        nota = self.fuente_chica.render(
            "Lo depositado no se pierde en arrestos ni muertes.",
            True, COLOR_TEXTO_SUAVE)
        superficie.blit(nota, ((ANCHO_VENTANA - nota.get_width()) // 2, 168))
        self._dibujar_opciones(superficie, 215, interlinea=44)
        if self.mensaje:
            img = self.fuente_chica.render(self.mensaje, True, self.color_mensaje)
            superficie.blit(img, ((ANCHO_VENTANA - img.get_width()) // 2, 460))
        pie = self.fuente_chica.render(
            "Mouse o W/S + ENTER  ·  ESC salir", True, COLOR_TEXTO_SUAVE)
        superficie.blit(pie, ((ANCHO_VENTANA - pie.get_width()) // 2, ALTO_VENTANA - 60))


# ---------------------------------------------------------
# Entrega de mercadería a un vendedor de la Red: se abre con
# E al lado del NPC en su zona (no hay entregas por celular)
# ---------------------------------------------------------
class PantallaVendedor(_MenuVertical):
    ITEMS = [
        ("nat1", "Darle 1 natural"),
        ("natTodo", "Darle todos los naturales"),
        ("quim1", "Darle 1 químico"),
        ("quimTodo", "Darle todos los químicos"),
        ("salir", "Salir"),
    ]

    def __init__(self):
        super().__init__([etiqueta for _, etiqueta in self.ITEMS])
        self.fuente = FuenteUI(34)
        self.fuente_titulo = FuenteUI(56)
        self.fuente_chica = FuenteUI(24)
        self.mensaje = ""
        self.color_mensaje = COLOR_TEXTO
        self.vendedor = None   # a quién le estás entregando

    def abrir(self, vendedor):
        self.vendedor = vendedor
        self.seleccion = 0
        self.mensaje = ""

    def manejar_evento(self, evento, economia, red):
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
            return "cerrar"
        i = self._navegar(evento)
        if i is None:
            return None
        id_item = self.ITEMS[i][0]
        if id_item == "salir":
            return "cerrar"
        tipo = "med_nat" if id_item.startswith("nat") else "med_quim"
        cantidad = (1 if id_item.endswith("1")
                    else economia.stock_med(tipo))
        if cantidad <= 0 or not red.depositar(self.vendedor, tipo,
                                              economia, cantidad):
            self.mensaje = f"No tenés {NOMBRE_MED[tipo]} encima."
            self.color_mensaje = COLOR_ERROR
            return None
        self.mensaje = (f"Le diste {cantidad} {NOMBRE_MED[tipo]} "
                        f"a {self.vendedor.nombre}.")
        self.color_mensaje = COLOR_DINERO
        return None

    def dibujar(self, superficie, economia):
        velo = _panel(ANCHO_VENTANA, ALTO_VENTANA, alpha=170)
        superficie.blit(velo, (0, 0))
        v = self.vendedor
        titulo = self.fuente_titulo.render(v.nombre.upper(), True, COLOR_ORO)
        superficie.blit(titulo, ((ANCHO_VENTANA - titulo.get_width()) // 2, 70))
        sub = self.fuente_chica.render(
            f"Trabaja en {v.nombre_zona}  ·  ventas {v.ventas}",
            True, COLOR_TEXTO_SUAVE)
        superficie.blit(sub, ((ANCHO_VENTANA - sub.get_width()) // 2, 122))
        info = self.fuente_chica.render(
            f"Su stock — N: {v.stock_nat}  Q: {v.stock_quim}      "
            f"Tu bolsillo — N: {economia.med_nat}  Q: {economia.med_quim}",
            True, COLOR_TEXTO)
        superficie.blit(info, ((ANCHO_VENTANA - info.get_width()) // 2, 150))
        if not v.stock_total:
            aviso = self.fuente_chica.render(
                "¡Está sin mercadería! Sin stock no vende nada.",
                True, COLOR_ERROR)
            superficie.blit(aviso,
                            ((ANCHO_VENTANA - aviso.get_width()) // 2, 178))
        self._dibujar_opciones(superficie, 215, interlinea=44)
        if self.mensaje:
            img = self.fuente_chica.render(self.mensaje, True,
                                           self.color_mensaje)
            superficie.blit(img, ((ANCHO_VENTANA - img.get_width()) // 2, 460))
        pie = self.fuente_chica.render(
            "Mouse o W/S + ENTER  ·  ESC salir", True, COLOR_TEXTO_SUAVE)
        superficie.blit(pie, ((ANCHO_VENTANA - pie.get_width()) // 2,
                              ALTO_VENTANA - 60))


# ---------------------------------------------------------
# El estante del sótano: la ÚNICA estación con ventana propia
# (guardar/retirar necesita elegir ítems). Las demás — maceta,
# mesa y laboratorio — son props físicos del cuarto y se usan
# directo con E al acercarse (la lógica vive en main.py).
# ---------------------------------------------------------
# ---------------------------------------------------------
# Grillas arrastrables (Fase 15): la base común de todas las
# pantallas de contenedores — inventario del jugador, baúl
# del vehículo, estante del sótano (y cualquier caja futura).
# Cada panel es una grilla de slots del Inventario posicional
# (inventory.py); el mouse agarra un stack (click derecho o
# Shift = media pila), lo arrastra con el ícono pegado al
# cursor y lo suelta en otro slot: mover / apilar / permutar.
# El teclado sigue andando: WASD elige slot, E usa/mueve.
# ---------------------------------------------------------
TAM_SLOT = 52
SEP_SLOT = 8


def _dibujar_caja_slot(superficie, rect, borde=COLOR_SLOT_BORDE,
                       grosor=1, alpha=235):
    caja = pygame.Surface(rect.size, pygame.SRCALPHA)
    caja.fill((*COLOR_SLOT, alpha))
    superficie.blit(caja, rect)
    pygame.draw.rect(superficie.raw, borde, rect, grosor)


class _PanelGrilla:
    """Una grilla visible de un Inventario: título, layout de rects,
    regla de admisión (`acepta(id_item) -> (ok, mensaje)`) y tope
    opcional de unidades (`tope(id_item) -> cuántas entran aún`)."""

    def __init__(self, titulo, inventario, x, y, acepta=None,
                 tope=None, tam=TAM_SLOT):
        self.titulo = titulo
        self.inventario = inventario
        self.x, self.y = x, y
        self.acepta = acepta
        self.tope = tope
        self.tam = tam
        self.rects = []
        cols = inventario.columnas
        for i in range(len(inventario.slots)):
            self.rects.append(pygame.Rect(
                x + (i % cols) * (tam + SEP_SLOT),
                y + (i // cols) * (tam + SEP_SLOT), tam, tam))

    def ancho(self):
        cols = self.inventario.columnas
        return cols * self.tam + (cols - 1) * SEP_SLOT

    def admite(self, id_item):
        return self.acepta(id_item) if self.acepta else (True, "")


class _PantallaGrillas:
    """Base de las pantallas con paneles arrastrables. Las subclases
    arman los paneles en _layout() y definen las acciones de teclado;
    acá vive el drag & drop, la selección y el dibujo de los slots."""

    def __init__(self):
        self.fuente_titulo = FuenteUI(52)
        self.fuente = FuenteUI(26)
        self.fuente_chica = FuenteUI(21)
        self.mensaje = ""
        self.mouse = (ANCHO_VENTANA // 2, ALTO_VENTANA // 2)
        # Drag en curso: {"panel": i, "idx": j, "cantidad": n|None}.
        # El stack NO sale del slot hasta soltarlo (así cancelar es
        # gratis): el origen se dibuja atenuado mientras tanto.
        self.drag = None
        self.sel = 0          # índice dentro de _zonas
        self.paneles = []
        # Zonas seleccionables: slots de los paneles + los contadores
        # fijos de la subclase. {"rect", "panel", "idx", "id", ...}
        self._zonas = []

    def abrir(self):
        self.mensaje = ""
        self.drag = None
        self.sel = 0

    # -- armado (las subclases llenan paneles/zonas cada evento) --
    def _armar_zonas(self, extras=()):
        """Slots de todos los paneles + zonas fijas no arrastrables."""
        self._zonas = []
        for p_i, panel in enumerate(self.paneles):
            for idx, rect in enumerate(panel.rects):
                self._zonas.append({"rect": rect, "panel": p_i,
                                    "idx": idx})
        self._zonas.extend(extras)
        if self._zonas:
            self.sel = min(self.sel, len(self._zonas) - 1)

    def _zona_en(self, pos):
        for i, zona in enumerate(self._zonas):
            if zona["rect"].collidepoint(pos):
                return i
        return None

    def _stack_de(self, zona):
        """El stack del slot de esa zona (None si vacía o si es un
        contador fijo)."""
        if zona.get("panel") is None:
            return None
        return self.paneles[zona["panel"]].inventario.obtener(zona["idx"])

    def _zona_sel(self):
        return self._zonas[self.sel] if self._zonas else None

    # -- drag & drop --
    def _evento_mouse(self, evento):
        """Maneja el mouse del drag & drop. True si consumió el
        evento (para que la subclase no lo procese de nuevo)."""
        if evento.type == pygame.MOUSEMOTION:
            self.mouse = evento.pos
            if self.drag is None:
                lugar = self._zona_en(evento.pos)
                if lugar is not None:
                    self.sel = lugar
            return False
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button in (1, 3):
            self.mouse = evento.pos
            lugar = self._zona_en(evento.pos)
            if lugar is None:
                return False
            zona = self._zonas[lugar]
            self.sel = lugar
            stack = self._stack_de(zona)
            if stack is None:
                return False   # slot vacío o contador fijo: no se agarra
            mitad = (evento.button == 3
                     or pygame.key.get_mods() & pygame.KMOD_SHIFT)
            self.drag = {"panel": zona["panel"], "idx": zona["idx"],
                         "cantidad": max(1, stack[1] // 2) if mitad
                         else None}
            return True
        if evento.type == pygame.MOUSEBUTTONUP and evento.button in (1, 3):
            self.mouse = evento.pos
            if self.drag is not None:
                self._soltar(evento.pos)
                return True
        return False

    def _soltar(self, pos):
        drag, self.drag = self.drag, None
        origen = self.paneles[drag["panel"]]
        stack = origen.inventario.obtener(drag["idx"])
        lugar = self._zona_en(pos)
        if stack is None or lugar is None:
            return   # fuera de todo slot: queda donde estaba
        zona = self._zonas[lugar]
        if zona.get("panel") is None:
            return   # los contadores fijos no reciben ítems
        destino = self.paneles[zona["panel"]]
        if destino is not origen:
            ok, mensaje = destino.admite(stack[0])
            if not ok:
                self.mensaje = mensaje
                return
            if destino.tope is not None:
                # Tope de unidades: entra lo que entra, el resto
                # queda en el origen
                lugar_libre = destino.tope(stack[0])
                if lugar_libre <= 0:
                    self.mensaje = "Ahí no entra más."
                    return
                pedido = drag["cantidad"] or stack[1]
                drag["cantidad"] = min(pedido, lugar_libre)
        if mover_stack(origen.inventario, drag["idx"],
                       destino.inventario, zona["idx"],
                       drag["cantidad"]):
            self.sel = lugar
            self.mensaje = ""

    def _cancelar_drag(self):
        """ESC durante el arrastre: el stack nunca salió del origen."""
        estaba = self.drag is not None
        self.drag = None
        return estaba

    # -- selección con teclado (geométrica: sirve para cualquier
    #    disposición de paneles y contadores) --
    def _mover_sel(self, dx, dy):
        if not self._zonas:
            return
        actual = self._zonas[self.sel]["rect"]
        cx, cy = actual.center
        mejor, mejor_costo = None, None
        for i, zona in enumerate(self._zonas):
            if i == self.sel:
                continue
            ox, oy = zona["rect"].center
            avance = (ox - cx) * dx + (oy - cy) * dy
            if avance <= 0:
                continue   # queda para el otro lado
            desvio = abs((ox - cx) * dy) + abs((oy - cy) * dx)
            costo = avance + desvio * 3
            if mejor_costo is None or costo < mejor_costo:
                mejor, mejor_costo = i, costo
        if mejor is not None:
            self.sel = mejor

    def _evento_teclado_sel(self, evento):
        """Navegación WASD/flechas. True si movió la selección."""
        teclas = {pygame.K_a: (-1, 0), pygame.K_LEFT: (-1, 0),
                  pygame.K_d: (1, 0), pygame.K_RIGHT: (1, 0),
                  pygame.K_w: (0, -1), pygame.K_UP: (0, -1),
                  pygame.K_s: (0, 1), pygame.K_DOWN: (0, 1)}
        if evento.key in teclas:
            self._mover_sel(*teclas[evento.key])
            return True
        return False

    # -- dibujo --
    def _dibujar_paneles(self, superficie, economia):
        hover = self._zona_en(self.mouse) if self.drag is not None else None
        for p_i, panel in enumerate(self.paneles):
            if panel.titulo:
                img = self.fuente_chica.render(panel.titulo, True, COLOR_ORO)
                superficie.blit(img, (panel.x, panel.y - 24))
            for idx, rect in enumerate(panel.rects):
                stack = panel.inventario.obtener(idx)
                self._dibujar_slot(superficie, economia, p_i, idx, rect,
                                   stack, hover)

    def _dibujar_slot(self, superficie, economia, p_i, idx, rect,
                      stack, hover):
        zona_i = self._indice_zona(p_i, idx)
        elegido = zona_i == self.sel and self.drag is None
        es_origen = (self.drag is not None
                     and self.drag["panel"] == p_i
                     and self.drag["idx"] == idx)
        borde, grosor = COLOR_SLOT_BORDE, 1
        if elegido:
            borde, grosor = COLOR_SLOT_SEL, 2
        if self.drag is not None and hover is not None \
                and self._zonas[hover].get("panel") == p_i \
                and self._zonas[hover]["idx"] == idx:
            # Highlight del destino: dorado si el drop vale, rojo si no
            borde, grosor = self._color_destino(p_i), 2
        alpha = 110 if stack is None else 235
        _dibujar_caja_slot(superficie, rect, borde, grosor, alpha)
        if stack is None:
            return
        dibujar_icono(superficie, self._icono_de(stack[0], economia),
                      rect, economia)
        if stack[0] not in ITEMS_SIEMPRE_ENCIMA:
            img = self.fuente_chica.render(str(stack[1]), True, COLOR_TEXTO)
            superficie.blit(img, (rect.right - img.get_width() - 4,
                                  rect.bottom - img.get_height() - 3))
        if es_origen:
            # El stack que se está arrastrando queda atenuado en origen
            velo = pygame.Surface(rect.size, pygame.SRCALPHA)
            velo.fill((*COLOR_SLOT, 170))
            superficie.blit(velo, rect)

    def _color_destino(self, panel_destino):
        drag = self.drag
        origen = self.paneles[drag["panel"]]
        destino = self.paneles[panel_destino]
        stack = origen.inventario.obtener(drag["idx"])
        if stack is not None and destino is not origen:
            ok, _ = destino.admite(stack[0])
            if not ok:
                return COLOR_ERROR
            if destino.tope is not None and destino.tope(stack[0]) <= 0:
                return COLOR_ERROR
        return COLOR_SLOT_SEL

    def _indice_zona(self, p_i, idx):
        for i, zona in enumerate(self._zonas):
            if zona.get("panel") == p_i and zona["idx"] == idx:
                return i
        return None

    @staticmethod
    def _icono_de(id_item, economia):
        return id_item

    def _dibujar_drag(self, superficie, economia):
        """El ícono pegado al mouse, por encima de todo."""
        if self.drag is None:
            return
        stack = self.paneles[self.drag["panel"]].inventario.obtener(
            self.drag["idx"])
        if stack is None:
            self.drag = None
            return
        cantidad = self.drag["cantidad"] or stack[1]
        rect = pygame.Rect(0, 0, TAM_SLOT, TAM_SLOT)
        rect.center = (int(self.mouse[0]), int(self.mouse[1]))
        dibujar_icono(superficie, self._icono_de(stack[0], economia),
                      rect, economia)
        if stack[0] not in ITEMS_SIEMPRE_ENCIMA:
            img = self.fuente_chica.render(str(cantidad), True, COLOR_ORO)
            superficie.blit(img, (rect.right - img.get_width() - 2,
                                  rect.bottom - img.get_height() - 2))


class PantallaEstante(_PantallaGrillas):
    """El estante del sótano: dos grillas lado a lado (lo que llevás
    / lo guardado) con drag & drop cruzado. E mueve de a uno, como
    siempre. El Chef sigue leyendo del mismo estante: no le importa
    cómo se acomode."""

    def _layout(self, economia, sotano):
        inv = economia.inventario
        est = sotano.estante
        ancho_inv = (inv.columnas * TAM_SLOT
                     + (inv.columnas - 1) * SEP_SLOT)
        self.paneles = [
            _PanelGrilla("LLEVÁS ENCIMA", inv, 150, 190),
            _PanelGrilla("EN EL ESTANTE", est,
                         ANCHO_VENTANA - 150 - ancho_inv, 190,
                         acepta=self._acepta_estante),
        ]
        self._armar_zonas()

    @staticmethod
    def _acepta_estante(id_item):
        if id_item in ITEMS_SIEMPRE_ENCIMA:
            return False, "Eso va siempre encima."
        return True, ""

    def manejar_evento(self, evento, economia, sotano):
        self._layout(economia, sotano)
        if self._evento_mouse(evento):
            return None
        if evento.type != pygame.KEYDOWN:
            return None
        if evento.key == pygame.K_ESCAPE:
            if self._cancelar_drag():
                return None
            return "cerrar"
        if self._evento_teclado_sel(evento):
            return None
        if evento.key in (pygame.K_RETURN, pygame.K_e, pygame.K_SPACE):
            zona = self._zona_sel()
            stack = self._stack_de(zona) if zona else None
            if stack is None:
                return None
            id_item = stack[0]
            nombre = NOMBRE_ITEM.get(id_item, id_item)
            if zona["panel"] == 0:
                if id_item in ITEMS_SIEMPRE_ENCIMA:
                    self.mensaje = "Eso va siempre encima."
                elif sotano.guardar(economia.inventario, id_item):
                    self.mensaje = f"Guardaste 1 {nombre}."
                else:
                    self.mensaje = "El estante está lleno."
            elif sotano.retirar(economia.inventario, id_item):
                self.mensaje = f"Retiraste 1 {nombre}."
        return None

    def dibujar(self, superficie, economia, sotano):
        self._layout(economia, sotano)
        velo = _panel(ANCHO_VENTANA, ALTO_VENTANA, alpha=185)
        superficie.blit(velo, (0, 0))
        titulo = self.fuente_titulo.render("EL ESTANTE", True, COLOR_ORO)
        superficie.blit(titulo, ((ANCHO_VENTANA - titulo.get_width()) // 2, 46))
        sub = self.fuente_chica.render(
            "Lo guardado queda en el sótano, a salvo de arrestos.",
            True, COLOR_TEXTO_SUAVE)
        superficie.blit(sub, ((ANCHO_VENTANA - sub.get_width()) // 2, 96))

        self._dibujar_paneles(superficie, economia)

        zona = self._zona_sel()
        stack = self._stack_de(zona) if zona else None
        if stack is not None:
            nombre = NOMBRE_ITEM.get(stack[0], stack[0])
            img = self.fuente.render(f"{nombre}  x{stack[1]}",
                                     True, COLOR_TEXTO)
            superficie.blit(img, ((ANCHO_VENTANA - img.get_width()) // 2,
                                  ALTO_VENTANA - 92))
        if self.mensaje:
            img = self.fuente_chica.render(self.mensaje, True, COLOR_DINERO)
            superficie.blit(img, ((ANCHO_VENTANA - img.get_width()) // 2,
                                  ALTO_VENTANA - 60))
        pie = self.fuente_chica.render(
            "Arrastrá con el mouse (click der. — media pila)  ·  "
            "WASD + E — mover 1  ·  ESC — salir",
            True, COLOR_TEXTO_SUAVE)
        superficie.blit(pie, ((ANCHO_VENTANA - pie.get_width()) // 2,
                              ALTO_VENTANA - 30))
        self._dibujar_drag(superficie, economia)


class PantallaContenedor(_PantallaGrillas):
    """Pantalla genérica de dos paneles con drag & drop: lo que
    llevás a la izquierda, un contenedor cualquiera a la derecha.
    Sirve para el contenedor de ingredientes del Chef y para
    cualquier caja/baúl fijo del mapa que se agregue después.
    `solo_items` restringe qué entra; `tope_unidades` limita el
    total (lo que no entra queda en tu mano)."""

    def __init__(self, titulo, subtitulo="", solo_items=None,
                 tope_unidades=None):
        super().__init__()
        self.titulo = titulo
        self.subtitulo = subtitulo
        self.solo_items = solo_items
        self.tope_unidades = tope_unidades
        self._contenedor = None   # lo fija _layout en cada evento

    def _acepta(self, id_item):
        if id_item in ITEMS_SIEMPRE_ENCIMA:
            return False, "Eso va siempre encima."
        if self.solo_items and id_item not in self.solo_items:
            nombres = ", ".join(NOMBRE_ITEM.get(i, i).lower()
                                for i in self.solo_items)
            return False, f"Acá solo van {nombres}."
        return True, ""

    def _tope(self, id_item):
        """Cuántas unidades entran todavía (None = sin tope)."""
        if self.tope_unidades is None:
            return None
        total = sum(s[1] for s in self._contenedor.stacks)
        return self.tope_unidades - total

    def _layout(self, economia, contenedor):
        self._contenedor = contenedor
        inv = economia.inventario
        ancho_inv = (inv.columnas * TAM_SLOT
                     + (inv.columnas - 1) * SEP_SLOT)
        titulo_c = "ADENTRO"
        if self.tope_unidades is not None:
            total = sum(s[1] for s in contenedor.stacks)
            titulo_c += f"  ({total}/{self.tope_unidades})"
        self.paneles = [
            _PanelGrilla("LLEVÁS ENCIMA", inv, 150, 190),
            _PanelGrilla(titulo_c, contenedor,
                         ANCHO_VENTANA - 150 - ancho_inv, 190,
                         acepta=self._acepta,
                         tope=(None if self.tope_unidades is None
                               else self._tope)),
        ]
        self._armar_zonas()

    def manejar_evento(self, evento, economia, contenedor):
        self._layout(economia, contenedor)
        if self._evento_mouse(evento):
            return None
        if evento.type != pygame.KEYDOWN:
            return None
        if evento.key == pygame.K_ESCAPE:
            if self._cancelar_drag():
                return None
            return "cerrar"
        if self._evento_teclado_sel(evento):
            return None
        if evento.key in (pygame.K_RETURN, pygame.K_e, pygame.K_SPACE):
            self._mover_uno(economia, contenedor)
        return None

    def _mover_uno(self, economia, contenedor):
        """E: pasa 1 unidad del stack elegido al otro lado."""
        zona = self._zona_sel()
        stack = self._stack_de(zona) if zona else None
        if stack is None:
            return
        id_item = stack[0]
        nombre = NOMBRE_ITEM.get(id_item, id_item)
        if zona["panel"] == 0:
            ok, mensaje = self._acepta(id_item)
            if not ok:
                self.mensaje = mensaje
                return
            lugar_libre = self._tope(id_item)
            if lugar_libre is not None and lugar_libre <= 0:
                self.mensaje = "Ahí no entra más."
                return
            if contenedor.agregar(id_item, 1):
                economia.inventario.quitar(id_item, 1)
                self.mensaje = f"Dejaste 1 {nombre}."
            else:
                self.mensaje = "No hay lugar."
        elif contenedor.quitar(id_item, 1):
            economia.inventario.agregar(id_item, 1)
            self.mensaje = f"Sacaste 1 {nombre}."

    def dibujar(self, superficie, economia, contenedor):
        self._layout(economia, contenedor)
        velo = _panel(ANCHO_VENTANA, ALTO_VENTANA, alpha=185)
        superficie.blit(velo, (0, 0))
        titulo = self.fuente_titulo.render(self.titulo, True, COLOR_ORO)
        superficie.blit(titulo, ((ANCHO_VENTANA - titulo.get_width()) // 2, 46))
        if self.subtitulo:
            sub = self.fuente_chica.render(self.subtitulo, True,
                                           COLOR_TEXTO_SUAVE)
            superficie.blit(sub, ((ANCHO_VENTANA - sub.get_width()) // 2, 96))

        self._dibujar_paneles(superficie, economia)

        zona = self._zona_sel()
        stack = self._stack_de(zona) if zona else None
        if stack is not None:
            nombre = NOMBRE_ITEM.get(stack[0], stack[0])
            img = self.fuente.render(f"{nombre}  x{stack[1]}",
                                     True, COLOR_TEXTO)
            superficie.blit(img, ((ANCHO_VENTANA - img.get_width()) // 2,
                                  ALTO_VENTANA - 92))
        if self.mensaje:
            img = self.fuente_chica.render(self.mensaje, True, COLOR_DINERO)
            superficie.blit(img, ((ANCHO_VENTANA - img.get_width()) // 2,
                                  ALTO_VENTANA - 60))
        pie = self.fuente_chica.render(
            "Arrastrá con el mouse (click der. — media pila)  ·  "
            "WASD + E — mover 1  ·  ESC — salir",
            True, COLOR_TEXTO_SUAVE)
        superficie.blit(pie, ((ANCHO_VENTANA - pie.get_width()) // 2,
                              ALTO_VENTANA - 30))
        self._dibujar_drag(superficie, economia)


# ---------------------------------------------------------
# La cocina: elegir receta (aparece cuando el Proveedor te
# enseñó la Especial; antes E cocina la Clásica directo)
# ---------------------------------------------------------
class PantallaCocina(_MenuVertical):
    IDS = ["clasica", "especial", "salir"]

    def __init__(self):
        clasica = RECETAS["clasica"]
        especial = RECETAS["especial"]
        super().__init__([
            f"Clásica — {clasica['ingredientes']} ingredientes",
            (f"Especial — {especial['ingredientes']} ingredientes "
             f"+ ${especial['costo_extra']} de especias"),
            "Salir",
        ])
        self.fuente = FuenteUI(34)
        self.fuente_titulo = FuenteUI(56)
        self.fuente_chica = FuenteUI(24)
        self.mensaje = ""
        self.color_mensaje = COLOR_TEXTO

    def abrir(self):
        self.seleccion = 0
        self.mensaje = ""

    def manejar_evento(self, evento, economia):
        """Devuelve "cerrar", ("cocinar", receta) o None."""
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
            return "cerrar"
        i = self._navegar(evento)
        if i is None:
            return None
        id_receta = self.IDS[i]
        if id_receta == "salir":
            return "cerrar"
        datos = RECETAS[id_receta]
        if economia.ingredientes < datos["ingredientes"]:
            self.mensaje = f"Te faltan ingredientes ({datos['ingredientes']})."
            self.color_mensaje = COLOR_ERROR
            return None
        if datos["costo_extra"] > economia.dinero:
            self.mensaje = "No te alcanza para las especias."
            self.color_mensaje = COLOR_ERROR
            return None
        return ("cocinar", id_receta)

    def dibujar(self, superficie, economia):
        velo = _panel(ANCHO_VENTANA, ALTO_VENTANA, alpha=170)
        superficie.blit(velo, (0, 0))
        titulo = self.fuente_titulo.render("¿QUÉ COCINAMOS?", True, COLOR_ORO)
        superficie.blit(titulo, ((ANCHO_VENTANA - titulo.get_width()) // 2, 90))
        info = self.fuente_chica.render(
            f"$ {economia.dinero}  ·  {economia.ingredientes} ingredientes  ·  "
            "la Clásica rinde calidad 60-90%, la Especial 130-160% (premium)",
            True, COLOR_TEXTO_SUAVE)
        superficie.blit(info, ((ANCHO_VENTANA - info.get_width()) // 2, 150))
        self._dibujar_opciones(superficie, 220, interlinea=48)
        if self.mensaje:
            img = self.fuente_chica.render(self.mensaje, True, self.color_mensaje)
            superficie.blit(img, ((ANCHO_VENTANA - img.get_width()) // 2, 420))
        pie = self.fuente_chica.render(
            "Mouse o W/S + ENTER  ·  ESC salir", True, COLOR_TEXTO_SUAVE)
        superficie.blit(pie, ((ANCHO_VENTANA - pie.get_width()) // 2, ALTO_VENTANA - 60))


# ---------------------------------------------------------
# Árbol de habilidades (tecla T): estilo hexagonal inspirado
# en Spider-Man Miles Morales. Cuatro ramas en abanico que
# nacen del centro (cocina arriba-izq, ventas arriba-der,
# combate abajo-izq, sigilo abajo-der), nodos hexagonales
# con glow y panel lateral con el detalle del seleccionado.
# ---------------------------------------------------------
def _hex_pts_en(cx, cy, r):
    """Hexágono pointy-top centrado en (cx, cy)."""
    pts = []
    for i in range(6):
        a = math.radians(30 + 60 * i)
        pts.append((cx + r * math.cos(a), cy - r * math.sin(a)))
    return pts


def _glow_hex_en(superficie, cx, cy, r, color, alpha):
    """Halo hexagonal semitransparente."""
    sz = int(r * 3 + 6)
    s = pygame.Surface((sz, sz), pygame.SRCALPHA)
    c2 = sz // 2
    pts = []
    for i in range(6):
        a = math.radians(30 + 60 * i)
        pts.append((c2 + r * math.cos(a), c2 - r * math.sin(a)))
    pygame.draw.polygon(s, (*color, alpha), pts)
    superficie.blit(s, (cx - c2, cy - c2))


class PantallaHabilidades:
    """El árbol clásico (4 ramas x 4 nodos) con la estética
    hexagonal de Miles Morales. WASD/flechas navegan, E/Enter
    o click compran; el panel derecho detalla el nodo."""

    CENTRO = (345, 285)
    RADIO_HEX = 19
    ANCHO_PANEL = 250

    _C_BG       = (6,   8,  16)
    _C_HEX_GRID = (18,  22,  36)
    _C_LOCKED   = (42,  45,  58)
    _C_LOCK_BRD = (72,  76,  92)

    # Dirección de cada rama (unitaria aprox.): en abanico
    _DIRS = [(-0.94, -0.55), (0.94, -0.55),   # cocina / ventas
             (-0.94,  0.62), (0.94,  0.62)]   # combate / sigilo

    def __init__(self):
        self.fuente_titulo = FuenteUI(38)
        self.fuente       = FuenteUI(24)
        self.fuente_chica = FuenteUI(19)
        self.fuente_desc  = FuenteUI(17)
        self.fuente_mini  = FuenteUI(15)
        self.sel = [0, 0]          # [rama, nivel]
        self.mensaje = ""
        self.color_mensaje = COLOR_TEXTO
        self._cajas = {}           # (rama, nivel) -> rect clickeable
        # Posiciones precalculadas de cada nodo
        cx, cy = self.CENTRO
        self._pos = {}
        for rama, (dx, dy) in enumerate(self._DIRS):
            for nivel in range(4):
                d = 78 + nivel * 72
                self._pos[(rama, nivel)] = (round(cx + dx * d),
                                            round(cy + dy * d))

    def abrir(self):
        self.mensaje = ""

    def manejar_evento(self, evento, economia, habilidades, jugador):
        if evento.type == pygame.KEYDOWN:
            if evento.key in (pygame.K_ESCAPE, pygame.K_t):
                return "cerrar"
            n = len(ARBOL[self.sel[0]]["nodos"])
            if evento.key in (pygame.K_a, pygame.K_LEFT):
                self.sel[0] = (self.sel[0] - 1) % len(ARBOL)
            elif evento.key in (pygame.K_d, pygame.K_RIGHT):
                self.sel[0] = (self.sel[0] + 1) % len(ARBOL)
            elif evento.key in (pygame.K_w, pygame.K_UP):
                self.sel[1] = (self.sel[1] - 1) % n
            elif evento.key in (pygame.K_s, pygame.K_DOWN):
                self.sel[1] = (self.sel[1] + 1) % n
            elif evento.key in (pygame.K_RETURN, pygame.K_e, pygame.K_SPACE):
                self._comprar(economia, habilidades, jugador)
        elif evento.type == pygame.MOUSEMOTION:
            for clave, rect in self._cajas.items():
                if rect.collidepoint(evento.pos):
                    self.sel = list(clave)
        elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            for clave, rect in self._cajas.items():
                if rect.collidepoint(evento.pos):
                    self.sel = list(clave)
                    self._comprar(economia, habilidades, jugador)
        return None

    def _comprar(self, economia, habilidades, jugador):
        rama, nivel = self.sel
        ok, mensaje = habilidades.comprar(rama, nivel, economia)
        self.mensaje = mensaje
        self.color_mensaje = COLOR_DINERO if ok else COLOR_ERROR
        id_nodo = ARBOL[rama]["nodos"][nivel]["id"]
        if ok and id_nodo in ("aguante", "piel"):
            # Aplicar la vida extra al toque
            cura = 40 if id_nodo == "aguante" else 60
            jugador.vida_max = habilidades.vida_max()
            jugador.vida = min(jugador.vida_max, jugador.vida + cura)

    # -- dibujo --

    def _fondo_hex(self, superficie, ancho):
        r = 22
        h = r * math.sqrt(3)
        for col in range(int(ancho / (r * 1.5)) + 3):
            for fila in range(int(ALTO_VENTANA / h) + 3):
                ox = col * r * 1.5
                oy = fila * h + (h / 2 if col % 2 else 0) - h
                pygame.draw.polygon(superficie.raw, self._C_HEX_GRID,
                                    _hex_pts_en(ox, oy, r - 1), 1)

    def dibujar(self, superficie, economia, habilidades):
        ancho_libre = ANCHO_VENTANA - self.ANCHO_PANEL - 20

        pygame.draw.rect(superficie.raw, self._C_BG,
                         (0, 0, ancho_libre, ALTO_VENTANA))
        self._fondo_hex(superficie, ancho_libre)
        pygame.draw.line(superficie.raw, (38, 42, 60),
                         (ancho_libre, 0), (ancho_libre, ALTO_VENTANA), 1)

        self._panel_lateral(superficie, economia, habilidades)

        # Barra superior
        barra = pygame.Surface((ancho_libre, 50), pygame.SRCALPHA)
        barra.fill((8, 10, 20, 225))
        superficie.blit(barra, (0, 0))
        titulo = self.fuente_titulo.render("HABILIDADES", True, COLOR_ORO)
        superficie.blit(titulo,
                        (ancho_libre // 2 - titulo.get_width() // 2, 12))
        pts_img = self.fuente.render(
            f"Puntos: {economia.puntos}", True, COLOR_TEXTO)
        superficie.blit(pts_img, (14, 16))
        plata_img = self.fuente_chica.render(
            f"$ {economia.dinero}", True, COLOR_DINERO)
        superficie.blit(plata_img,
                        (ancho_libre - plata_img.get_width() - 14, 18))

        cx, cy = self.CENTRO
        t = pygame.time.get_ticks() / 1000.0
        parpadeo = 0.5 + 0.5 * math.sin(t * 2.8)

        # Etiquetas de rama en la punta de cada abanico
        for rama, datos in enumerate(ARBOL):
            px, py = self._pos[(rama, 3)]
            dx, dy = self._DIRS[rama]
            lbl = self.fuente_mini.render(datos["nombre"], True,
                                          datos["color"])
            lx = px + dx * 34 - lbl.get_width() // 2
            ly = py + dy * 34 - lbl.get_height() // 2
            lx = max(6, min(lx, ancho_libre - lbl.get_width() - 6))
            superficie.blit(lbl, (lx, ly))

        # Líneas centro → nodo1 → ... → nodo4
        for rama, datos in enumerate(ARBOL):
            color = datos["color"]
            previo = (cx, cy)
            for nivel in range(len(datos["nodos"])):
                px, py = self._pos[(rama, nivel)]
                activa = habilidades.estado(rama, nivel) == "comprada"
                if activa:
                    s = pygame.Surface((ANCHO_VENTANA, ALTO_VENTANA),
                                       pygame.SRCALPHA)
                    pygame.draw.line(s, (*color, 30), previo, (px, py), 8)
                    superficie.blit(s, (0, 0))
                    pygame.draw.line(superficie.raw, color,
                                     previo, (px, py), 3)
                else:
                    pygame.draw.line(superficie.raw, (50, 54, 72),
                                     previo, (px, py), 1)
                previo = (px, py)

        # Nodo central
        pygame.draw.circle(superficie.raw, (30, 32, 48), (cx, cy), 13)
        pygame.draw.circle(superficie.raw, COLOR_ORO, (cx, cy), 13, 2)
        plus = self.fuente_chica.render("+", True, COLOR_ORO)
        superficie.blit(plus, (cx - plus.get_width() // 2,
                               cy - plus.get_height() // 2))

        # Nodos hexagonales
        self._cajas = {}
        r = self.RADIO_HEX
        for rama, datos in enumerate(ARBOL):
            color = datos["color"]
            dim = tuple(max(0, c // 3) for c in color)
            for nivel, nodo in enumerate(datos["nodos"]):
                px, py = self._pos[(rama, nivel)]
                estado = habilidades.estado(rama, nivel)
                pts = _hex_pts_en(px, py, r)

                if estado == "comprada":
                    _glow_hex_en(superficie, px, py, r + 5, color, 45)
                    pygame.draw.polygon(superficie.raw, dim, pts)
                    pygame.draw.polygon(superficie.raw, color, pts, 3)
                    ok_img = self.fuente.render("✓", True, color)
                    superficie.blit(ok_img, (px - ok_img.get_width() // 2,
                                             py - ok_img.get_height() // 2))
                elif estado == "disponible":
                    ag = int(45 + 85 * parpadeo)
                    _glow_hex_en(superficie, px, py, r + 8, color, ag)
                    pygame.draw.polygon(superficie.raw, (12, 14, 24), pts)
                    pygame.draw.polygon(superficie.raw, color, pts, 2)
                    c_img = self.fuente_mini.render(
                        str(nodo["puntos"]), True, color)
                    superficie.blit(c_img, (px - c_img.get_width() // 2,
                                            py - c_img.get_height() // 2))
                else:
                    pygame.draw.polygon(superficie.raw, self._C_LOCKED, pts)
                    pygame.draw.polygon(superficie.raw, self._C_LOCK_BRD,
                                        pts, 1)
                    c_lk = (95, 100, 118)
                    pygame.draw.rect(superficie.raw, c_lk,
                                     pygame.Rect(px - 4, py, 8, 6),
                                     border_radius=1)
                    pygame.draw.arc(superficie.raw, c_lk,
                                    pygame.Rect(px - 3, py - 5, 7, 7),
                                    0, math.pi, 2)

                if self.sel == [rama, nivel]:
                    pygame.draw.polygon(superficie.raw, COLOR_ORO,
                                        _hex_pts_en(px, py, r + 6), 2)

                hit = pygame.Rect(0, 0, (r + 6) * 2, (r + 6) * 2)
                hit.center = (px, py)
                self._cajas[(rama, nivel)] = hit

        if self.mensaje:
            img = self.fuente_chica.render(self.mensaje, True,
                                           self.color_mensaje)
            superficie.blit(img, ((ancho_libre - img.get_width()) // 2,
                                  ALTO_VENTANA - 52))
        pie = self.fuente_mini.render(
            "Mouse o WASD + ENTER comprar  ·  R — I+D medicamentos"
            "  ·  T/ESC cerrar", True, COLOR_TEXTO_SUAVE)
        superficie.blit(pie, ((ancho_libre - pie.get_width()) // 2,
                              ALTO_VENTANA - 24))

    def _panel_lateral(self, superficie, economia, habilidades):
        x = ANCHO_VENTANA - self.ANCHO_PANEL - 10
        panel_bg = pygame.Surface((self.ANCHO_PANEL, ALTO_VENTANA - 20),
                                  pygame.SRCALPHA)
        panel_bg.fill((10, 12, 22, 240))
        superficie.blit(panel_bg, (x, 10))

        rama, nivel = self.sel
        datos = ARBOL[rama]
        nodo = datos["nodos"][nivel]
        color = datos["color"]
        estado = habilidades.estado(rama, nivel)

        barra_h = 50
        barra = pygame.Surface((self.ANCHO_PANEL, barra_h), pygame.SRCALPHA)
        barra.fill((*color, 45))
        superficie.blit(barra, (x, 10))
        pygame.draw.line(superficie.raw, color, (x, 10 + barra_h),
                         (x + self.ANCHO_PANEL, 10 + barra_h), 1)
        etq = self.fuente_mini.render(
            f"{datos['nombre']}  ·  NIVEL {nivel + 1}", True, color)
        superficie.blit(etq, (x + 12, 20))

        y = 10 + barra_h + 14
        for linea in _envolver_lineas(self.fuente, nodo["nombre"],
                                      self.ANCHO_PANEL - 24):
            img = self.fuente.render(linea, True, COLOR_TEXTO)
            superficie.blit(img, (x + 12, y))
            y += 26

        etiqueta = {"comprada": "✓ Comprada", "disponible": "Disponible",
                    "bloqueada": "Bloqueada"}[estado]
        color_etq = {"comprada": COLOR_DINERO, "disponible": COLOR_TEXTO,
                     "bloqueada": COLOR_ERROR}[estado]
        superficie.blit(self.fuente_chica.render(etiqueta, True, color_etq),
                        (x + 12, y + 4))
        y += 30
        if estado != "comprada":
            superficie.blit(self.fuente_chica.render(
                f"Coste: {nodo['puntos']} pts + ${nodo['dinero']}",
                True, COLOR_ORO), (x + 12, y))
            y += 26

        y += 6
        for linea in _envolver_lineas(self.fuente_desc, nodo["desc"],
                                      self.ANCHO_PANEL - 24):
            superficie.blit(self.fuente_desc.render(
                linea, True, COLOR_TEXTO), (x + 12, y))
            y += 22

        if estado == "bloqueada":
            y += 8
            previo = datos["nodos"][nivel - 1]["nombre"]
            superficie.blit(self.fuente_chica.render(
                "Requiere:", True, COLOR_ERROR), (x + 12, y))
            y += 22
            superficie.blit(self.fuente_desc.render(
                f"· {previo}", True, COLOR_TEXTO_SUAVE), (x + 12, y))


# ---------------------------------------------------------
# Árbol de I+D de medicamentos (tecla R): estilo hexagonal
# inspirado en Spider-Man: Miles Morales.
# Dos ramas — natural (izquierda, teal) y sintética (derecha,
# violeta) — nacen del centro. Nodos hexagonales con glow,
# fondo de cuadrícula hexagonal y panel lateral detallado.
# ---------------------------------------------------------

class PantallaArbolMedicamentos:
    """Árbol de I+D estilo Spider-Man Miles Morales: nodos
    hexagonales con glow, cuadrícula de fondo y panel lateral."""

    CENTRO = (345, 300)
    ESCALA = 0.52
    RADIO_TRONCO = 20
    RADIO_CORTA  = 15
    ANCHO_PANEL  = 250
    _ORDEN = list(NODOS.keys())

    # Paleta estilo Miles Morales
    _C_BG       = (6,   8,  16)
    _C_HEX_GRID = (18,  22,  36)
    _C_NAT      = (0,  210, 160)   # teal (naturales)
    _C_NAT_DIM  = (0,   70,  54)
    _C_QUIM     = (170,  90, 255)  # violeta (sintéticos)
    _C_QUIM_DIM = (65,   30, 105)
    _C_LOCKED   = (42,   45,  58)
    _C_LOCK_BRD = (72,   76,  92)
    _C_LINE_OFF = (50,   54,  72)

    def __init__(self):
        self.fuente_titulo = FuenteUI(38)
        self.fuente       = FuenteUI(24)
        self.fuente_chica = FuenteUI(19)
        self.fuente_desc  = FuenteUI(17)
        self.fuente_mini  = FuenteUI(15)
        self.sel = self._ORDEN[0]
        self.mensaje = ""
        self.color_mensaje = COLOR_TEXTO
        self._rects = {}

    def abrir(self):
        self.mensaje = ""

    # -- helpers de posición y color --

    def _punto(self, nodo):
        cx, cy = self.CENTRO
        x, y = nodo.pos
        return cx + x * self.ESCALA, cy + y * self.ESCALA

    _C_MIX     = (255, 200,  60)   # dorado (transversales)
    _C_MIX_DIM = (95,  75,  20)

    def _c_rama(self, rama):
        if rama == "natural":
            return self._C_NAT
        if rama == "sintetico":
            return self._C_QUIM
        return self._C_MIX

    def _c_dim(self, rama):
        if rama == "natural":
            return self._C_NAT_DIM
        if rama == "sintetico":
            return self._C_QUIM_DIM
        return self._C_MIX_DIM

    def _radio(self, nodo):
        return self.RADIO_TRONCO if nodo.tipo == "tronco" else self.RADIO_CORTA

    # -- gráficos auxiliares --

    @staticmethod
    def _hex_pts(cx, cy, r):
        """Hexágono pointy-top."""
        pts = []
        for i in range(6):
            a = math.radians(30 + 60 * i)
            pts.append((cx + r * math.cos(a), cy - r * math.sin(a)))
        return pts

    @staticmethod
    def _glow_hex(superficie, cx, cy, r, color, alpha):
        """Halo hexagonal semitransparente."""
        sz = int(r * 3 + 6)
        s = pygame.Surface((sz, sz), pygame.SRCALPHA)
        cx2, cy2 = sz // 2, sz // 2
        pts_loc = []
        for i in range(6):
            a = math.radians(30 + 60 * i)
            pts_loc.append((cx2 + r * math.cos(a), cy2 - r * math.sin(a)))
        pygame.draw.polygon(s, (*color, alpha), pts_loc)
        superficie.blit(s, (cx - sz // 2, cy - sz // 2))

    @staticmethod
    def _linea_glow(superficie, x1, y1, x2, y2, color, activa):
        x1, y1, x2, y2 = round(x1), round(y1), round(x2), round(y2)
        if activa:
            s = pygame.Surface((ANCHO_VENTANA, ALTO_VENTANA), pygame.SRCALPHA)
            pygame.draw.line(s, (*color, 30), (x1, y1), (x2, y2), 8)
            superficie.blit(s, (0, 0))
            pygame.draw.line(superficie.raw, color, (x1, y1), (x2, y2), 3)
        else:
            pygame.draw.line(superficie.raw, (50, 54, 72),
                             (x1, y1), (x2, y2), 1)

    def _fondo_hex(self, superficie, ancho):
        """Cuadrícula hexagonal sutil de fondo."""
        r = 22
        h = r * math.sqrt(3)
        ncols = int(ancho / (r * 1.5)) + 3
        nrows = int(ALTO_VENTANA / h) + 3
        for col in range(ncols):
            for row in range(nrows):
                ox = col * r * 1.5
                oy = row * h + (h / 2 if col % 2 else 0) - h
                pts = self._hex_pts(ox, oy, r - 1)
                pygame.draw.polygon(superficie.raw, self._C_HEX_GRID, pts, 1)

    # -- lógica de eventos --

    def manejar_evento(self, evento, economia, arbol):
        if evento.type == pygame.KEYDOWN:
            if evento.key in (pygame.K_ESCAPE, pygame.K_r):
                return "cerrar"
            if evento.key in (pygame.K_RETURN, pygame.K_e, pygame.K_SPACE):
                self._investigar(economia, arbol)
            elif evento.key in (pygame.K_a, pygame.K_LEFT,
                                pygame.K_w, pygame.K_UP):
                idx = self._ORDEN.index(self.sel)
                self.sel = self._ORDEN[(idx - 1) % len(self._ORDEN)]
            elif evento.key in (pygame.K_d, pygame.K_RIGHT,
                                pygame.K_s, pygame.K_DOWN, pygame.K_TAB):
                idx = self._ORDEN.index(self.sel)
                self.sel = self._ORDEN[(idx + 1) % len(self._ORDEN)]
        elif evento.type == pygame.MOUSEMOTION:
            for id_nodo, rect in self._rects.items():
                if rect.collidepoint(evento.pos):
                    self.sel = id_nodo
                    break
        elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            for id_nodo, rect in self._rects.items():
                if rect.collidepoint(evento.pos):
                    self.sel = id_nodo
                    self._investigar(economia, arbol)
                    break
        return None

    def _investigar(self, economia, arbol):
        ok, mensaje = arbol.comprar(self.sel, economia)
        if ok and NODOS[self.sel].desbloquea:
            receta = receta_texto(NODOS[self.sel].desbloquea)
            if receta:
                mensaje += f"  ·  Receta: {receta} (mesa del sótano)"
        self.mensaje = mensaje
        self.color_mensaje = COLOR_DINERO if ok else COLOR_ERROR

    # -- dibujo principal --

    def dibujar(self, superficie, economia, arbol):
        ancho_libre = ANCHO_VENTANA - self.ANCHO_PANEL - 20

        # Fondo oscuro + cuadrícula hex
        pygame.draw.rect(superficie.raw, self._C_BG,
                         (0, 0, ancho_libre, ALTO_VENTANA))
        self._fondo_hex(superficie, ancho_libre)

        # Separador panel
        pygame.draw.line(superficie.raw, (38, 42, 60),
                         (ancho_libre, 0), (ancho_libre, ALTO_VENTANA), 1)

        # Panel lateral (se dibuja antes para que los nodos queden encima)
        self._panel_lateral(superficie, economia, arbol)

        # Barra superior
        barra = pygame.Surface((ancho_libre, 50), pygame.SRCALPHA)
        barra.fill((8, 10, 20, 225))
        superficie.blit(barra, (0, 0))
        titulo = self.fuente_titulo.render("I+D — MEDICAMENTOS", True, COLOR_ORO)
        superficie.blit(titulo,
                        (ancho_libre // 2 - titulo.get_width() // 2, 12))
        xp_img = self.fuente.render(f"XP: {economia.puntos}", True, COLOR_TEXTO)
        superficie.blit(xp_img, (14, 16))

        # Etiquetas de rama
        nat_lbl = self.fuente_mini.render("NATURALES", True, self._C_NAT)
        superficie.blit(nat_lbl, (80, 52))
        quim_lbl = self.fuente_mini.render("SINTÉTICOS", True, self._C_QUIM)
        superficie.blit(quim_lbl, (ancho_libre - quim_lbl.get_width() - 80, 52))

        cx, cy = self.CENTRO

        # --- Líneas entre nodos ---
        for nodo in NODOS.values():
            px, py = self._punto(nodo)
            comprado = arbol.tiene(nodo.id)
            c = self._c_rama(nodo.rama)
            if not nodo.padres:
                self._linea_glow(superficie, cx, cy, px, py, c, comprado)
            for id_padre in nodo.padres:
                ppx, ppy = self._punto(NODOS[id_padre])
                activa = comprado and arbol.tiene(id_padre)
                self._linea_glow(superficie, ppx, ppy, px, py, c, activa)

        # Nodo central
        pygame.draw.circle(superficie.raw, (30, 32, 48), (cx, cy), 13)
        pygame.draw.circle(superficie.raw, COLOR_ORO, (cx, cy), 13, 2)
        plus = self.fuente_chica.render("+", True, COLOR_ORO)
        superficie.blit(plus, (cx - plus.get_width() // 2,
                               cy - plus.get_height() // 2))

        # --- Nodos hexagonales ---
        self._rects = {}
        t = pygame.time.get_ticks() / 1000.0
        parpadeo = 0.5 + 0.5 * math.sin(t * 2.8)

        for nodo in NODOS.values():
            px, py = (round(v) for v in self._punto(nodo))
            estado = arbol.estado(nodo.id)
            c_r  = self._c_rama(nodo.rama)
            c_d  = self._c_dim(nodo.rama)
            r    = self._radio(nodo)
            pts  = self._hex_pts(px, py, r)

            if estado == "comprado":
                self._glow_hex(superficie, px, py, r + 5, c_r, 45)
                pygame.draw.polygon(superficie.raw, c_d, pts)
                pygame.draw.polygon(superficie.raw, c_r, pts, 3)
                ok_img = self.fuente.render("✓", True, c_r)
                superficie.blit(ok_img,
                                (px - ok_img.get_width() // 2,
                                 py - ok_img.get_height() // 2))

            elif estado == "disponible":
                ag = int(45 + 85 * parpadeo)
                self._glow_hex(superficie, px, py, r + 8, c_r, ag)
                pygame.draw.polygon(superficie.raw, (12, 14, 24), pts)
                pygame.draw.polygon(superficie.raw, c_r, pts, 2)
                coste_img = self.fuente_mini.render(str(nodo.coste), True, c_r)
                superficie.blit(coste_img,
                                (px - coste_img.get_width() // 2,
                                 py - coste_img.get_height() // 2))

            else:  # bloqueado
                pygame.draw.polygon(superficie.raw, self._C_LOCKED, pts)
                pygame.draw.polygon(superficie.raw, self._C_LOCK_BRD, pts, 1)
                c_lk = (95, 100, 118)
                pygame.draw.rect(superficie.raw, c_lk,
                                 pygame.Rect(px - 4, py, 8, 6),
                                 border_radius=1)
                pygame.draw.arc(superficie.raw, c_lk,
                                pygame.Rect(px - 3, py - 5, 7, 7),
                                0, math.pi, 2)

            # Anillo de selección
            if self.sel == nodo.id:
                pts_sel = self._hex_pts(px, py, r + 6)
                pygame.draw.polygon(superficie.raw, COLOR_ORO, pts_sel, 2)

            hit = pygame.Rect(0, 0, (r + 6) * 2, (r + 6) * 2)
            hit.center = (px, py)
            self._rects[nodo.id] = hit

        # Mensajes y pie
        if self.mensaje:
            img = self.fuente_chica.render(self.mensaje, True, self.color_mensaje)
            superficie.blit(img, ((ancho_libre - img.get_width()) // 2,
                                  ALTO_VENTANA - 52))
        pie = self.fuente_mini.render(
            "Mouse o flechas + ENTER investigar  ·  "
            "T — habilidades  ·  R/ESC cerrar",
            True, COLOR_TEXTO_SUAVE)
        superficie.blit(pie, ((ancho_libre - pie.get_width()) // 2,
                              ALTO_VENTANA - 24))

    def _panel_lateral(self, superficie, economia, arbol):
        x = ANCHO_VENTANA - self.ANCHO_PANEL - 10

        # Fondo del panel
        panel_bg = pygame.Surface((self.ANCHO_PANEL, ALTO_VENTANA - 20),
                                  pygame.SRCALPHA)
        panel_bg.fill((10, 12, 22, 240))
        superficie.blit(panel_bg, (x, 10))

        nodo   = NODOS[self.sel]
        c_rama = self._c_rama(nodo.rama)
        estado = arbol.estado(nodo.id)

        # Franja de color de rama (encabezado)
        barra_h = 50
        barra = pygame.Surface((self.ANCHO_PANEL, barra_h), pygame.SRCALPHA)
        barra.fill((*c_rama, 45))
        superficie.blit(barra, (x, 10))
        pygame.draw.line(superficie.raw, c_rama,
                         (x, 10 + barra_h),
                         (x + self.ANCHO_PANEL, 10 + barra_h), 1)

        rama_lbl = {"natural": "NATURAL", "sintetico": "SINTÉTICO",
                    "mixta": "TRANSVERSAL"}.get(nodo.rama, "?")
        tipo_lbl = ("TRONCO" if nodo.tipo == "tronco" else "MEJORA")
        etq = self.fuente_mini.render(
            f"{rama_lbl}  ·  {tipo_lbl}", True, c_rama)
        superficie.blit(etq, (x + 12, 20))

        # Nombre del nodo
        y = 10 + barra_h + 14
        for linea in _envolver_lineas(self.fuente, nodo.nombre,
                                      self.ANCHO_PANEL - 24):
            l_img = self.fuente.render(linea, True, (228, 230, 238))
            superficie.blit(l_img, (x + 12, y))
            y += self.fuente.get_height() + 2

        # Estado
        y += 8
        etq_est, c_est = {
            "comprado":   ("✓  INVESTIGADO", COLOR_DINERO),
            "disponible": ("DISPONIBLE",     COLOR_TEXTO),
            "bloqueado":  ("⊘  BLOQUEADO",  COLOR_ERROR),
        }[estado]
        superficie.blit(self.fuente_chica.render(etq_est, True, c_est),
                        (x + 12, y))
        y += 28

        # Coste + barra de progreso
        if estado != "comprado":
            superficie.blit(
                self.fuente_chica.render(
                    f"Costo: {nodo.coste} XP", True, COLOR_ORO),
                (x + 12, y))
            y += 24
            bw = self.ANCHO_PANEL - 24
            pygame.draw.rect(superficie.raw, (28, 30, 44),
                             (x + 12, y, bw, 9), border_radius=4)
            progreso = min(1.0, economia.puntos / max(1, nodo.coste))
            pw = int(bw * progreso)
            if pw > 0:
                pygame.draw.rect(superficie.raw, c_rama,
                                 (x + 12, y, pw, 9), border_radius=4)
            pygame.draw.rect(superficie.raw, (65, 70, 92),
                             (x + 12, y, bw, 9), 1, border_radius=4)
            y += 20

        # Separador
        y += 10
        pygame.draw.line(superficie.raw, (38, 42, 60),
                         (x + 12, y), (x + self.ANCHO_PANEL - 12, y), 1)
        y += 12

        # Descripción
        for linea in _envolver_lineas(self.fuente_desc, nodo.desc,
                                      self.ANCHO_PANEL - 24):
            superficie.blit(
                self.fuente_desc.render(linea, True, COLOR_TEXTO_SUAVE),
                (x + 12, y))
            y += 21

        # Producto desbloqueado
        if nodo.desbloquea:
            datos = PRODUCTOS[nodo.desbloquea]
            y += 10
            pygame.draw.line(superficie.raw, (38, 42, 60),
                             (x + 12, y), (x + self.ANCHO_PANEL - 12, y), 1)
            y += 12
            superficie.blit(
                self.fuente_chica.render(
                    f"$ {datos['precio']} / unidad", True, COLOR_DINERO),
                (x + 12, y))
            y += 24
            superficie.blit(
                self.fuente_desc.render(
                    f"+{datos['xp_venta']} XP por venta",
                    True, COLOR_TEXTO_SUAVE),
                (x + 12, y))
            y += 22
            # La receta: que el jugador sepa CÓMO se fabrica
            receta = receta_texto(nodo.desbloquea)
            if receta:
                y += 4
                superficie.blit(
                    self.fuente_desc.render(
                        "RECETA — mesa del sótano:", True, c_rama),
                    (x + 12, y))
                y += 20
                for lin in _envolver_lineas(self.fuente_desc, receta,
                                            self.ANCHO_PANEL - 28):
                    superficie.blit(
                        self.fuente_desc.render(lin, True, COLOR_TEXTO),
                        (x + 16, y))
                    y += 20
                base = ("(la planta sale de la maceta)"
                        if nodo.rama == "natural" else
                        "(el crudo se cocina en el laboratorio)")
                for lin in _envolver_lineas(self.fuente_desc, base,
                                            self.ANCHO_PANEL - 28):
                    superficie.blit(
                        self.fuente_desc.render(lin, True,
                                                COLOR_TEXTO_SUAVE),
                        (x + 16, y))
                    y += 20

        # Requisitos faltantes
        if estado == "bloqueado" and nodo.padres:
            y += 10
            pygame.draw.line(superficie.raw, (38, 42, 60),
                             (x + 12, y), (x + self.ANCHO_PANEL - 12, y), 1)
            y += 12
            superficie.blit(
                self.fuente_desc.render("REQUIERE:", True, COLOR_ERROR),
                (x + 12, y))
            y += 22
            for p_id in nodo.padres:
                if p_id not in arbol.comprados:
                    for lin in _envolver_lineas(
                            self.fuente_desc, f"· {NODOS[p_id].nombre}",
                            self.ANCHO_PANEL - 28):
                        superficie.blit(
                            self.fuente_desc.render(
                                lin, True, COLOR_TEXTO_SUAVE),
                            (x + 16, y))
                        y += 20


# ---------------------------------------------------------
# Inventario grande (tecla O): todo lo que llevás, en una
# grilla de módulos con descripciones. Desde acá también se
# come un sanguche o se cambia de arma (E sobre el ítem).
# ---------------------------------------------------------
class PantallaInventario(_PantallaGrillas):
    """El inventario grande (tecla O): la grilla del jugador con
    drag & drop y, si hay vehículo con baúl, la grilla del baúl al
    lado — se arrastra de una a la otra. Los contadores (comida,
    efectivo, banco, puntos, receta) no son ítems físicos: van en
    una franja fija abajo, seleccionables pero no arrastrables."""

    TAM_CONTADOR = 44

    # Descripción de cada ítem apilable (el arma se arma aparte)
    DESCRIPCIONES = {
        "celular": "Pedidos, mapa y mensajes (tecla C).",
        "balas": "Munición de la pistola. Pack en el almacén.",
        "ingredientes": "Para cocinar tandas. Se piden por el celular.",
        "sanguche": (f"+{CURA_SANGUCHE} de vida — E para comer uno. "
                     f"Máximo {MAX_SANGUCHES}."),
        "med_nat": "Mercadería. Se fabrica en el sótano: planta + ziploc.",
        "med_quim": ("Mercadería premium. Químico crudo + ziploc en "
                     "la mesa (el crudo sale del laboratorio)."),
        "ziploc": "Insumo: para empaquetar mercadería natural y química.",
        "semillas": "Insumo: se plantan en la maceta del sótano.",
        "compuestos": ("Insumo: se cocinan en el laboratorio para "
                       "obtener químico crudo."),
        "planta": "Cosecha de la maceta. Planta + ziploc = med natural.",
        "quimico_crudo": ("Salido del laboratorio. Crudo + ziploc en "
                          "la mesa = med químico (así se vende)."),
        "comp_antiviral": ("Insumo premium (app Insumos). Antiviral = "
                           "compuesto de antiviral + ziploc."),
        "comp_suero": ("Insumo top (app Insumos). Suero = compuesto "
                       "de suero + ziploc."),
        "maceta": ("Mueble: tecla del hotbar para colocarla donde "
                   "apuntás. X frente a ella (vacía) la levanta."),
        "mesa_lab": ("Mueble: tecla del hotbar para colocarla donde "
                     "apuntás. X frente a ella (vacía) la levanta."),
    }

    def _contadores(self, economia):
        """La franja fija de abajo: contadores, no ítems físicos.
        (id, cantidad a mostrar, descripción)."""
        contadores = [
            ("comida", economia.producto,
             f"Comida — platos listos (calidad "
             f"{round(economia.calidad * 100)}%). "
             "Se venden en el mostrador."),
            ("efectivo", economia.dinero,
             "Efectivo — la plata del bolsillo: se pierde en "
             "arrestos y muertes."),
            ("banco", economia.banco,
             "Banco — plata a salvo de multas y pérdidas."),
            ("puntos", economia.puntos,
             "Puntos de habilidad — se gastan en el árbol (T)."),
        ]
        if economia.receta_especial:
            contadores.append(
                ("receta", None,
                 "Receta especial — la del Proveedor: platos premium."))
        return contadores

    def _layout(self, economia, jugador):
        inv = economia.inventario
        ancho_inv = (inv.columnas * TAM_SLOT
                     + (inv.columnas - 1) * SEP_SLOT)
        y0 = 130
        if economia.vehiculo:
            x_inv = 120
            datos_v = VEHICULOS[economia.vehiculo]
            lugares = datos_v["baul"]
            titulo_b = (f"BAÚL — {datos_v['nombre']}"
                        + ("" if lugares else " (la moto no tiene baúl)"))
            ancho_baul = (economia.baul.columnas * TAM_SLOT
                          + (economia.baul.columnas - 1) * SEP_SLOT)
            self.paneles = [
                _PanelGrilla("LLEVÁS ENCIMA", inv, x_inv, y0),
                _PanelGrilla(titulo_b, economia.baul,
                             ANCHO_VENTANA - 120 - ancho_baul, y0,
                             acepta=self._acepta_baul),
            ]
        else:
            x_inv = (ANCHO_VENTANA - ancho_inv) // 2
            self.paneles = [_PanelGrilla("LLEVÁS ENCIMA", inv, x_inv, y0)]

        # Los contadores, en fila debajo de la grilla del jugador
        alto_inv = (inv.filas_visibles() * (TAM_SLOT + SEP_SLOT)
                    - SEP_SLOT)
        extras = []
        y_c = y0 + alto_inv + 18
        for k, (id_item, cuenta, desc) in \
                enumerate(self._contadores(economia)):
            rect = pygame.Rect(
                x_inv + k * (self.TAM_CONTADOR + SEP_SLOT), y_c,
                self.TAM_CONTADOR, self.TAM_CONTADOR)
            extras.append({"rect": rect, "panel": None, "idx": k,
                           "id": id_item, "cuenta": cuenta,
                           "desc": desc})
        self._armar_zonas(extras)

    @staticmethod
    def _acepta_baul(id_item):
        if id_item in ITEMS_SIEMPRE_ENCIMA:
            return False, "Eso va siempre encima."
        return True, ""

    @staticmethod
    def _icono_de(id_item, economia):
        if id_item == "arma" and not economia.tiene_pistola:
            return "punos"
        return id_item

    def _descripcion(self, zona, economia):
        """Nombre + descripción de lo seleccionado (o ""). """
        if zona is None:
            return ""
        if zona.get("panel") is None:
            return zona["desc"]
        stack = self._stack_de(zona)
        if stack is None:
            return ""
        id_item = stack[0]
        if id_item == "arma":
            estado_arma = ("equipada — E para guardarla"
                           if economia.arma_equipada
                           else "guardada — E para equiparla")
            return f"Pistola — tu arma. Está {estado_arma}."
        nombre = NOMBRE_ITEM.get(id_item, id_item.capitalize())
        if zona["panel"] == 1:
            nombre_v = VEHICULOS[economia.vehiculo]["nombre"]
            return (f"{nombre} — en el baúl de tu {nombre_v}. "
                    "B — pasarlo a tu mano.")
        desc = self.DESCRIPCIONES.get(id_item, "")
        return f"{nombre} — {desc}" if desc else nombre

    def manejar_evento(self, evento, economia, jugador):
        """Devuelve "cerrar", ("comer_sanguche",), ("alternar_arma",),
        ("baul_guardar", id), ("baul_sacar", id) o None."""
        self._layout(economia, jugador)
        if self._evento_mouse(evento):
            return None
        if evento.type != pygame.KEYDOWN:
            return None
        if evento.key in (pygame.K_ESCAPE, pygame.K_o):
            if self._cancelar_drag():
                return None
            return "cerrar"
        if self._evento_teclado_sel(evento):
            return None
        zona = self._zona_sel()
        stack = self._stack_de(zona) if zona else None
        if evento.key in (pygame.K_RETURN, pygame.K_e, pygame.K_SPACE):
            if stack is not None and zona["panel"] == 0:
                return self._usar(stack[0])
        elif evento.key == pygame.K_b and stack is not None:
            # B: mover el stack seleccionado hacia/desde el baúl
            if zona["panel"] == 1:
                return ("baul_sacar", stack[0])
            return ("baul_guardar", stack[0])
        return None

    def _usar(self, id_item):
        if id_item == "sanguche":
            return ("comer_sanguche",)
        if id_item == "arma":
            return ("alternar_arma",)
        return None

    def dibujar(self, superficie, economia, jugador):
        self._layout(economia, jugador)
        velo = _panel(ANCHO_VENTANA, ALTO_VENTANA, alpha=185)
        superficie.blit(velo, (0, 0))
        titulo = self.fuente_titulo.render("INVENTARIO", True, COLOR_ORO)
        superficie.blit(titulo, ((ANCHO_VENTANA - titulo.get_width()) // 2, 26))
        vida = self.fuente_chica.render(
            f"Vida {max(0, jugador.vida)}/{jugador.vida_max}",
            True, COLOR_TEXTO_SUAVE)
        superficie.blit(vida, ((ANCHO_VENTANA - vida.get_width()) // 2, 68))

        self._dibujar_paneles(superficie, economia)
        self._dibujar_contadores(superficie, economia)

        # Descripción de lo seleccionado
        desc = self._descripcion(self._zona_sel(), economia)
        if desc:
            img = self.fuente.render(desc, True, COLOR_TEXTO)
            superficie.blit(img, ((ANCHO_VENTANA - img.get_width()) // 2,
                                  ALTO_VENTANA - 84))
        if self.mensaje:
            img = self.fuente_chica.render(self.mensaje, True, COLOR_DINERO)
            superficie.blit(img, ((ANCHO_VENTANA - img.get_width()) // 2,
                                  ALTO_VENTANA - 56))
        ayuda_baul = "  ·  B — al/del baúl" if economia.vehiculo else ""
        pie = self.fuente_chica.render(
            "Arrastrá con el mouse (click der. — media pila)  ·  "
            f"WASD + E — usar{ayuda_baul}  ·  O/ESC — cerrar",
            True, COLOR_TEXTO_SUAVE)
        superficie.blit(pie, ((ANCHO_VENTANA - pie.get_width()) // 2,
                              ALTO_VENTANA - 28))
        self._dibujar_drag(superficie, economia)

    def _dibujar_contadores(self, superficie, economia):
        """La franja de contadores: slots fijos, sin drag."""
        for zona in self._zonas:
            if zona.get("panel") is not None:
                continue
            rect = zona["rect"]
            elegido = (self._zonas[self.sel] is zona
                       and self.drag is None)
            _dibujar_caja_slot(superficie, rect,
                               COLOR_SLOT_SEL if elegido
                               else COLOR_SLOT_BORDE,
                               2 if elegido else 1, alpha=200)
            dibujar_icono(superficie, zona["id"], rect, economia)
            if zona["cuenta"] is not None:
                texto = (f"${zona['cuenta']}"
                         if zona["id"] in ("efectivo", "banco")
                         else str(zona["cuenta"]))
                img = self.fuente_chica.render(texto, True, COLOR_TEXTO)
                superficie.blit(img, (rect.right - img.get_width() - 4,
                                      rect.bottom - img.get_height() - 3))
