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

import pygame
from pathlib import Path

from .settings import (
    ANCHO_VENTANA, ALTO_VENTANA, TILE,
    COLOR_FONDO, COLOR_TEXTO, COLOR_TEXTO_SUAVE,
    COLOR_ORO, COLOR_DINERO, COLOR_ERROR,
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
    INGRESO_FRANQUICIA, INTERVALO_FRANQUICIA,
    NOMBRE_MED,
)
from .skills import ARBOL


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
    "franquicias": "icono_franquicias.png",
    "receta":      "icono_receta.png",
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
# Textos flotantes (viven en coordenadas de mundo)
# ---------------------------------------------------------
class TextoFlotante:
    def __init__(self, x, y, texto, color=COLOR_TEXTO):
        self.pos = pygame.Vector2(x, y)
        self.texto = texto
        self.color = color
        self.vida = 1.2  # segundos

    def actualizar(self, dt):
        self.pos.y -= 26 * dt
        self.vida -= dt

    def dibujar(self, superficie, camara, fuente):
        img = fuente.render(self.texto, True, self.color)
        img.set_alpha(max(0, min(255, int(self.vida * 400))))
        r = camara.aplicar(pygame.Rect(int(self.pos.x), int(self.pos.y), 1, 1))
        superficie.blit(img, (r.x - img.get_width() // 2, r.y))


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
        pygame.draw.rect(superficie, color, (cx - 9, cy - 4, 16, 5))   # caño
        pygame.draw.rect(superficie, color, (cx - 7, cy - 1, 5, 9))    # culata
    elif id_item == "punos":
        pygame.draw.rect(superficie, (196, 164, 120), (cx - 8, cy - 4, 7, 8))
        pygame.draw.rect(superficie, (196, 164, 120), (cx + 1, cy - 4, 7, 8))
    elif id_item == "balas":
        for i in range(3):
            x = cx - 9 + i * 7
            pygame.draw.rect(superficie, COLOR_ORO, (x, cy - 5, 4, 8))
            pygame.draw.rect(superficie, (150, 110, 40), (x, cy + 3, 4, 3))
    elif id_item == "comida":
        pygame.draw.circle(superficie, (235, 235, 230), (cx, cy), 9)   # plato
        pygame.draw.circle(superficie, (214, 128, 52), (cx, cy), 5)    # guiso
    elif id_item == "ingredientes":
        pygame.draw.rect(superficie, (150, 110, 66), (cx - 8, cy - 5, 16, 12))
        pygame.draw.rect(superficie, (196, 172, 120), (cx - 1, cy - 5, 3, 12))
    elif id_item == "sanguche":
        pygame.draw.rect(superficie, (222, 186, 120), (cx - 9, cy - 5, 18, 4))
        pygame.draw.rect(superficie, (120, 180, 90), (cx - 8, cy - 1, 16, 2))
        pygame.draw.rect(superficie, (190, 90, 70), (cx - 8, cy + 1, 16, 2))
        pygame.draw.rect(superficie, (222, 186, 120), (cx - 9, cy + 3, 18, 4))
    elif id_item == "med_nat":
        pygame.draw.rect(superficie, COLOR_MED_NAT, (cx - 7, cy - 4, 14, 9))
        pygame.draw.rect(superficie, (80, 130, 80), (cx - 7, cy - 4, 14, 3))
    elif id_item == "med_quim":
        pygame.draw.rect(superficie, COLOR_MED_QUIM, (cx - 4, cy - 8, 8, 16))
        pygame.draw.rect(superficie, (120, 80, 160), (cx - 4, cy - 8, 8, 6))
    elif id_item == "efectivo":
        pygame.draw.rect(superficie, COLOR_DINERO, (cx - 10, cy - 6, 20, 12))
        pygame.draw.circle(superficie, (60, 110, 60), (cx, cy), 4)
    elif id_item == "celular":
        pygame.draw.rect(superficie, COLOR_CELULAR_BORDE, (cx - 6, cy - 9, 12, 18))
        pygame.draw.rect(superficie, (120, 200, 160), (cx - 4, cy - 7, 8, 12))
    elif id_item == "banco":
        pygame.draw.rect(superficie, COLOR_BANCO, (cx - 9, cy - 6, 18, 13))
        pygame.draw.rect(superficie, COLOR_ORO, (cx - 9, cy - 1, 18, 3))
    elif id_item == "franquicias":
        pygame.draw.rect(superficie, (104, 72, 48), (cx - 8, cy - 3, 16, 10))
        pygame.draw.rect(superficie, COLOR_ORO, (cx - 10, cy - 7, 20, 5))
    elif id_item == "puntos":
        pygame.draw.circle(superficie, COLOR_ORO, (cx, cy), 8)
        pygame.draw.circle(superficie, (150, 115, 45), (cx, cy), 8, 2)
    elif id_item == "receta":
        pygame.draw.rect(superficie, (230, 224, 200), (cx - 7, cy - 9, 14, 18))
        for i in range(3):
            pygame.draw.rect(superficie, (140, 130, 110),
                             (cx - 4, cy - 5 + i * 5, 8, 2))


# ---------------------------------------------------------
# HUD del juego (Fase 11: repartido, con inventario rápido)
# ---------------------------------------------------------
# Los 9 módulos del inventario rápido, en orden (teclas 1-9)
HOTBAR = ["arma", "balas", "comida", "ingredientes", "sanguche",
          "med_nat", "med_quim", "efectivo", "celular"]
_SLOT = 44          # tamaño de cada módulo en px
_SLOT_SEP = 4


class HUD:
    def __init__(self):
        self.fuente = pygame.font.Font(None, 24)
        self.fuente_chica = pygame.font.Font(None, 20)
        self.fuente_reloj = pygame.font.Font(None, 30)
        self.fuente_aviso = pygame.font.Font(None, 68)

    def dibujar(self, superficie, jugador, economia, produccion,
                reloj, trato_activo, pista, busqueda, pedidos, fps,
                mostrar_panel=True, mision=None, sin_leer=0):
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
        img = self.fuente_chica.render(f"{fps} FPS", True, COLOR_TEXTO_SUAVE)
        superficie.blit(img, (ANCHO_VENTANA - img.get_width() - 8,
                              ALTO_VENTANA - img.get_height() - 6))

    def _vida_y_plata(self, superficie, jugador, economia, mostrar_panel):
        superficie.blit(_panel(190, 46 if mostrar_panel else 24), (8, 8))
        pygame.draw.rect(superficie, COLOR_VIDA_FONDO, (16, 14, 174, 10))
        relleno = int(174 * max(0, jugador.vida) / jugador.vida_max)
        pygame.draw.rect(superficie, COLOR_VIDA, (16, 14, relleno, 10))
        if mostrar_panel:
            img = self.fuente.render(f"$ {economia.dinero}", True, COLOR_DINERO)
            superficie.blit(img, (16, 30))
            pts = self.fuente_chica.render(
                f"{economia.puntos} pts [T]", True, COLOR_ORO)
            superficie.blit(pts, (190 - pts.get_width(), 33))

    def _reloj(self, superficie, reloj):
        img = self.fuente_reloj.render(reloj.texto(), True, COLOR_TEXTO)
        ancho = img.get_width() + 24
        x = (ANCHO_VENTANA - ancho) // 2
        superficie.blit(_panel(ancho, 30), (x, 8))
        superficie.blit(img, (x + 12, y_centrado(img, 8, 30)))

    def _hotbar(self, superficie, economia, sin_leer):
        """Los 9 módulos del inventario rápido, abajo al centro."""
        cuentas = {
            "arma": None,
            "balas": economia.balas if economia.tiene_pistola else None,
            "comida": economia.producto,
            "ingredientes": economia.ingredientes,
            "sanguche": economia.sanguches,
            "med_nat": economia.med_nat,
            "med_quim": economia.med_quim,
            "efectivo": economia.dinero,
            "celular": None,
        }
        total = len(HOTBAR) * _SLOT + (len(HOTBAR) - 1) * _SLOT_SEP
        x = (ANCHO_VENTANA - total) // 2
        y = ALTO_VENTANA - _SLOT - 10
        for i, id_item in enumerate(HOTBAR):
            rect = pygame.Rect(x + i * (_SLOT + _SLOT_SEP), y, _SLOT, _SLOT)
            caja = pygame.Surface(rect.size, pygame.SRCALPHA)
            caja.fill((*COLOR_SLOT[:3], 200))
            superficie.blit(caja, rect)
            # El arma resalta si está equipada
            equipada = id_item == "arma" and economia.arma_equipada \
                and economia.tiene_pistola
            borde = COLOR_SLOT_SEL if equipada else COLOR_SLOT_BORDE
            pygame.draw.rect(superficie, borde, rect, 2 if equipada else 1)

            icono = id_item
            if id_item == "arma" and not (economia.tiene_pistola
                                          and economia.arma_equipada):
                icono = "arma" if economia.tiene_pistola else "punos"
            dibujar_icono(superficie, icono, rect, economia)

            # Número de tecla (arriba izq.) y cantidad (abajo der.)
            num = self.fuente_chica.render(str(i + 1), True, COLOR_TEXTO_SUAVE)
            superficie.blit(num, (rect.x + 3, rect.y + 1))
            cuenta = cuentas[id_item]
            if cuenta is not None:
                texto = f"${cuenta}" if id_item == "efectivo" else str(cuenta)
                color = COLOR_DINERO if id_item == "efectivo" else COLOR_TEXTO
                img = self.fuente_chica.render(texto, True, color)
                superficie.blit(img, (rect.right - img.get_width() - 3,
                                      rect.bottom - img.get_height() - 2))
            # Mensajes sin leer sobre el celular
            if id_item == "celular" and sin_leer:
                pygame.draw.circle(superficie, COLOR_ERROR,
                                   (rect.right - 6, rect.y + 7), 7)
                aviso = self.fuente_chica.render(str(sin_leer), True, COLOR_TEXTO)
                superficie.blit(aviso, (rect.right - 6 - aviso.get_width() // 2,
                                        rect.y + 1))

    def _barra_coccion(self, superficie, produccion):
        ancho, alto = 220, 16
        x = (ANCHO_VENTANA - ancho) // 2
        y = ALTO_VENTANA - _SLOT - 34
        superficie.blit(_panel(ancho, alto), (x, y))
        relleno = int((ancho - 4) * min(1.0, produccion.progreso))
        pygame.draw.rect(superficie, COLOR_ORO, (x + 2, y + 2, relleno, alto - 4))
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
                pygame.draw.rect(superficie, COLOR_VIDA, casilla)
            else:
                pygame.draw.rect(superficie, COLOR_VIDA_FONDO, casilla, 1)

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
        self.fuente = pygame.font.Font(None, 40)
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
        self.fuente_titulo = pygame.font.Font(None, 100)
        self.fuente_sub = pygame.font.Font(None, 26)

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
        self.fuente_titulo = pygame.font.Font(None, 64)
        self.fuente = pygame.font.Font(None, 40)
        self.fuente_chica = pygame.font.Font(None, 25)
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
        pygame.draw.rect(superficie, (24, 24, 30), caja)
        pygame.draw.rect(superficie, COLOR_ORO, caja, 2)
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
        self.fuente = pygame.font.Font(None, 34)
        self.fuente_titulo = pygame.font.Font(None, 64)
        self.fuente_chica = pygame.font.Font(None, 25)
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
        "1-9 — inventario rápido   ·   T — habilidades   ·   TAB — ocultar HUD",
        "F11 o Cmd+F — pantalla completa   ·   F5 — guardar   ·   ESC — pausa",
    ]

    def __init__(self):
        super().__init__(["Sonido: 80%", "Música: sí",
                          "Pantalla completa: no", "Volver"])
        self.fuente = pygame.font.Font(None, 38)
        self.fuente_titulo = pygame.font.Font(None, 64)
        self.fuente_chica = pygame.font.Font(None, 25)

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
        y = 112
        for texto in self.CONTROLES:
            img = self.fuente_chica.render(texto, True, COLOR_TEXTO_SUAVE)
            superficie.blit(img, ((ANCHO_VENTANA - img.get_width()) // 2, y))
            y += 27
        self._dibujar_opciones(superficie, 275, interlinea=48)
        pie = self.fuente_chica.render(
            "Mouse o W/S + ENTER  ·  ESC volver", True, COLOR_TEXTO_SUAVE)
        superficie.blit(pie, ((ANCHO_VENTANA - pie.get_width()) // 2, ALTO_VENTANA - 35))


# ---------------------------------------------------------
# Menú de pausa (se dibuja sobre el juego congelado)
# ---------------------------------------------------------
class MenuPausa(_MenuVertical):
    ACCIONES = ["Continuar", "guardar", "Pantalla completa",
                "debug", "Menú principal"]

    def __init__(self):
        super().__init__(["Continuar", "Guardar partida", "Pantalla completa",
                          "Modo debug: no", "Menú principal"])
        self.fuente_titulo = pygame.font.Font(None, 72)
        self.fuente_chica = pygame.font.Font(None, 24)
        self.mensaje = ""

    def refrescar_debug(self, activo):
        self.opciones[3] = f"Modo debug: {'sí' if activo else 'no'}"

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
        self.fuente = pygame.font.Font(None, 34)
        self.fuente_titulo = pygame.font.Font(None, 56)
        self.fuente_chica = pygame.font.Font(None, 24)
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
# EL CELULAR: cuatro apps —
#   0 Comidas (pedidos de ingredientes con delivery)
#   1 Ilegales (meds, bloqueada hasta desbloquear)
#   2 Mapa  → gira a PAISAJE para ver el mapa completo
#   3 Mensajes (ofertas de tratos del mercado negro)
# C o E en el teléfono del local lo abre/cierra.
# ---------------------------------------------------------
class PantallaCelular:
    APPS = ["Comidas", "Ilegales", "Mapa", "Mensajes"]
    IDS_COMIDA    = ["ing6", "ing12"]
    IDS_ILEGALES  = ["nat3", "nat6", "quim3", "quim6"]

    # Portrait (apps 0, 1, 3)
    ANCHO_TEL = 300
    ALTO_TEL  = 512
    # Landscape (app Mapa)
    ANCHO_LAND = 524
    ALTO_LAND  = 318

    def __init__(self):
        self.fuente       = pygame.font.Font(None, 24)
        self.fuente_chica = pygame.font.Font(None, 20)
        self.fuente_titulo= pygame.font.Font(None, 30)
        self.fuente_mini  = pygame.font.Font(None, 16)
        self.app = 0
        self.seleccion = 0
        self.mensaje = ""
        self.color_mensaje = COLOR_TEXTO
        self._minimapa = None       # prerenderizado al primer uso
        self._rects_apps  = []
        self._rects_items = []

    def abrir(self, app=None):
        if app is not None:
            self.app = app
        self.seleccion = 0
        self.mensaje = ""

    @property
    def es_paisaje(self):
        """El mapa (app 2) gira el celular a horizontal."""
        return self.app == 2

    # ── eventos ────────────────────────────────────────────
    def manejar_evento(self, evento, economia, tratos, reloj):
        """→ "cerrar" | ("pedido", id) | ("aceptar", t) |
           ("rechazar", t) | None"""
        if evento.type == pygame.KEYDOWN:
            if evento.key in (pygame.K_ESCAPE, pygame.K_c):
                return "cerrar"
            if evento.key in (pygame.K_a, pygame.K_LEFT):
                self.app = (self.app - 1) % len(self.APPS)
                self.seleccion = 0; self.mensaje = ""
            elif evento.key in (pygame.K_d, pygame.K_RIGHT):
                self.app = (self.app + 1) % len(self.APPS)
                self.seleccion = 0; self.mensaje = ""
            elif self.app == 0:
                return self._ev_lista(evento, economia,
                                      self.IDS_COMIDA, es_comida=True)
            elif self.app == 1:
                return self._ev_lista(evento, economia,
                                      self.IDS_ILEGALES, es_comida=False)
            elif self.app == 3:
                return self._ev_mensajes(evento, tratos)
        elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            for i, r in enumerate(self._rects_apps):
                if r.collidepoint(evento.pos):
                    self.app = i; self.seleccion = 0; self.mensaje = ""
                    return None
            for i, r in enumerate(self._rects_items):
                if r.collidepoint(evento.pos):
                    self.seleccion = i
                    if self.app == 0:
                        return self._comprar(economia,
                                             self.IDS_COMIDA, True)
                    if self.app == 1:
                        return self._comprar(economia,
                                             self.IDS_ILEGALES, False)
                    if self.app == 3:
                        return self._aceptar(tratos)
        elif evento.type == pygame.MOUSEMOTION:
            for i, r in enumerate(self._rects_items):
                if r.collidepoint(evento.pos):
                    self.seleccion = i
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

    def _ev_mensajes(self, evento, tratos):
        ofertas = [t for t in tratos if t.estado == "oferta"]
        if not ofertas:
            return None
        n = len(ofertas)
        if evento.key in (pygame.K_w, pygame.K_UP):
            self.seleccion = (self.seleccion - 1) % n
        elif evento.key in (pygame.K_s, pygame.K_DOWN):
            self.seleccion = (self.seleccion + 1) % n
        elif evento.key in (pygame.K_RETURN, pygame.K_e, pygame.K_SPACE):
            return self._aceptar(tratos)
        elif evento.key == pygame.K_x and self.seleccion < n:
            return ("rechazar", ofertas[self.seleccion])
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

    def _aceptar(self, tratos):
        ofertas = [t for t in tratos if t.estado == "oferta"]
        if self.seleccion < len(ofertas):
            return ("aceptar", ofertas[self.seleccion])
        return None

    # ── dibujo principal ───────────────────────────────────
    def dibujar(self, superficie, economia, tratos, reloj, mapa,
                jugador, franquicias):
        velo = _panel(ANCHO_VENTANA, ALTO_VENTANA, alpha=150)
        superficie.blit(velo, (0, 0))

        if self.es_paisaje:
            aw, ah = self.ANCHO_LAND, self.ALTO_LAND
        else:
            aw, ah = self.ANCHO_TEL, self.ALTO_TEL
        x = (ANCHO_VENTANA - aw) // 2
        y = (ALTO_VENTANA - ah) // 2

        pygame.draw.rect(superficie, COLOR_CELULAR,
                         (x, y, aw, ah), border_radius=24)
        pygame.draw.rect(superficie, COLOR_CELULAR_BORDE,
                         (x, y, aw, ah), 2, border_radius=24)

        if self.es_paisaje:
            self._frame_land(superficie, x, y, aw, ah,
                             mapa, jugador, tratos, franquicias, reloj)
        else:
            self._frame_port(superficie, x, y, aw, ah,
                             economia, tratos, reloj)

        pie = self.fuente_chica.render(
            "A/D — app  ·  C/ESC — cerrar", True, COLOR_TEXTO_SUAVE)
        superficie.blit(pie, ((ANCHO_VENTANA - pie.get_width()) // 2,
                              y + ah + 6))

    # ── Portrait (apps 0, 1, 3) ────────────────────────────
    def _frame_port(self, sup, x, y, aw, ah, economia, tratos, reloj):
        # Notch + pantalla
        pygame.draw.rect(sup, (10, 10, 12),
                         (x + aw // 2 - 28, y + 10, 56, 13), border_radius=7)
        pant = pygame.Rect(x + 10, y + 32, aw - 20, ah - 92)
        pygame.draw.rect(sup, COLOR_PANTALLA_CEL, pant, border_radius=8)
        self._status_bar(sup, pant, reloj)
        cont = pygame.Rect(pant.x, pant.y + 24, pant.width, pant.height - 24)
        if self.app == 0:
            self._app_lista(sup, cont, economia,
                            "Comidas", self.IDS_COMIDA, True)
        elif self.app == 1:
            self._app_lista(sup, cont, economia,
                            "Ilegales", self.IDS_ILEGALES, False)
        else:
            self._app_mensajes(sup, cont, tratos, reloj)
        # Barra de apps abajo — 4 slots
        self._rects_apps = []
        ofertas = sum(1 for t in tratos if t.estado == "oferta")
        sw = (aw - 20) // 4
        etiquetas = ["Comidas", "Ilegal", "Mapa",
                     f"Msj({ofertas})" if ofertas else "Msj"]
        for i, etq in enumerate(etiquetas):
            r = pygame.Rect(x + 10 + i * sw, y + ah - 52, sw - 4, 40)
            self._rects_apps.append(r)
            bg = COLOR_APP_ACTIVA if i == self.app else (40, 40, 48)
            pygame.draw.rect(sup, bg, r, border_radius=8)
            img = self.fuente_chica.render(
                etq, True, COLOR_FONDO if i == self.app else COLOR_TEXTO)
            sup.blit(img, (r.centerx - img.get_width() // 2,
                           r.centery - img.get_height() // 2))

    def _status_bar(self, sup, pant, reloj):
        hora = self.fuente_chica.render(
            f"{reloj.hora:02d}:{reloj.minuto:02d}", True, COLOR_TEXTO)
        sup.blit(hora, (pant.x + 8, pant.y + 5))
        for i in range(4):
            hb = 3 + i * 2
            pygame.draw.rect(sup, COLOR_TEXTO_SUAVE,
                             (pant.right - 66 + i * 6,
                              pant.y + 14 - hb, 4, hb))
        pygame.draw.rect(sup, COLOR_TEXTO_SUAVE,
                         (pant.right - 34, pant.y + 5, 22, 10), 1)
        pygame.draw.rect(sup, COLOR_DINERO,
                         (pant.right - 32, pant.y + 7, 14, 6))

    # ── Landscape (app Mapa) ───────────────────────────────
    def _frame_land(self, sup, x, y, aw, ah,
                    mapa, jugador, tratos, franquicias, reloj):
        # Notch en lado izquierdo
        pygame.draw.rect(sup, (10, 10, 12),
                         (x + 10, y + ah // 2 - 20, 13, 40), border_radius=7)
        # Pantalla: margen izq=32, der=40, top=10, bot=12
        pant = pygame.Rect(x + 32, y + 10, aw - 72, ah - 22)
        pygame.draw.rect(sup, COLOR_PANTALLA_CEL, pant, border_radius=8)
        # Título dentro de la pantalla
        lbl = self.fuente_chica.render(
            f"{reloj.hora:02d}:{reloj.minuto:02d}  —  Mapa de la ciudad",
            True, COLOR_ORO)
        sup.blit(lbl, (pant.centerx - lbl.get_width() // 2, pant.y + 5))
        # Zona del mapa
        zona = pygame.Rect(pant.x, pant.y + 22, pant.width, pant.height - 22)
        self._app_mapa_land(sup, zona, mapa, jugador, tratos, franquicias)
        # Barra de apps: franja derecha del celular horizontal
        self._rects_apps = []
        ofertas = sum(1 for t in tratos if t.estado == "oferta")
        sh = (ah - 20) // 4
        ini = ["C", "I", "M", f"M({ofertas})" if ofertas else "M"]
        for i, lbl_a in enumerate(ini):
            r = pygame.Rect(x + aw - 38, y + 10 + i * sh, 30, sh - 4)
            self._rects_apps.append(r)
            bg = COLOR_APP_ACTIVA if i == self.app else (40, 40, 48)
            pygame.draw.rect(sup, bg, r, border_radius=6)
            img = self.fuente_chica.render(
                lbl_a, True, COLOR_FONDO if i == self.app else COLOR_TEXTO)
            sup.blit(img, (r.centerx - img.get_width() // 2,
                           r.centery - img.get_height() // 2))

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
            pygame.draw.rect(sup, (36, 38, 48) if elegido else (24, 26, 34),
                             r, border_radius=6)
            if elegido:
                pygame.draw.rect(sup, COLOR_APP_ACTIVA, r, 1, border_radius=6)
            sup.blit(self.fuente_chica.render(nombre_p, True, COLOR_TEXTO),
                     (r.x + 8, r.y + 6))
            sup.blit(self.fuente_chica.render(f"${precio}", True, COLOR_DINERO),
                     (r.x + 8, r.y + 23))
            y += 46

        if self.mensaje:
            sup.blit(self.fuente_chica.render(
                self.mensaje, True, self.color_mensaje), (zona.x + 8, zona.bottom - 24))

    def _prerender_minimapa(self, mapa):
        from .map import MAPA
        escala = 2
        sup = pygame.Surface((mapa.columnas * escala, mapa.filas * escala))
        colores = {
            "X": COLOR_EDIFICIO, "H": COLOR_CASA, "A": COLOR_ARBOL,
            "k": COLOR_TIENDA_TOLDO, "C": COLOR_PISO_LOCAL,
            "M": COLOR_PISO_LOCAL, "F": COLOR_PISO_LOCAL,
            "p": COLOR_PISO_LOCAL, "T": COLOR_TIENDA_TOLDO,
            "B": COLOR_BANCO,  "S": COLOR_HOSPITAL, "w": COLOR_AGUA,
            ".": COLOR_CALLE,  ",": COLOR_PASTO,    "~": COLOR_TIERRA,
        }
        for fila, linea in enumerate(MAPA):
            for col, tile in enumerate(linea):
                sup.fill(colores.get(tile, COLOR_CALLE),
                         (col * escala, fila * escala, escala, escala))
        return sup

    def _app_mapa_land(self, sup, zona, mapa, jugador, tratos, franquicias):
        """Mapa en horizontal: mapa a la izquierda + leyenda a la derecha."""
        from .economy import LUGARES_VENTA
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
        pygame.draw.rect(sup, COLOR_CELULAR_BORDE,
                         (mx - 1, my - 1, mw + 2, mh + 2), 1)

        def pt(col_t, fil_t):          # tile → pantalla
            return (mx + col_t * mw // mapa.columnas,
                    my + fil_t * mh // mapa.filas)

        def pt_px(pos_px):             # pixel mundo → pantalla
            return (mx + int(pos_px[0] / mapa.ancho_px * mw),
                    my + int(pos_px[1] / mapa.alto_px * mh))

        # Local principal (dorado)
        p_loc = pt(4, 4)
        pygame.draw.circle(sup, COLOR_ORO, p_loc, 5)
        lbl_loc = self.fuente_mini.render("Local", True, COLOR_ORO)
        sup.blit(lbl_loc, (p_loc[0] + 6, p_loc[1] - 5))

        # Zonas de venta: número amarillo
        AMARILLO = (255, 220, 40)
        for idx, (_, (col, fil, aw, af)) in enumerate(LUGARES_VENTA):
            px = pt(col + aw // 2, fil + af // 2)
            pygame.draw.circle(sup, AMARILLO, px, 4)
            num = self.fuente_mini.render(str(idx + 1), True, (15, 15, 15))
            sup.blit(num, (px[0] - num.get_width() // 2,
                           px[1] - num.get_height() // 2))

        # Franquicias compradas
        for fr in franquicias:
            if fr.comprada:
                pygame.draw.rect(sup, COLOR_ORO, (*pt_px(fr.rect.center), 3, 3))

        # Tratos
        ticks = pygame.time.get_ticks()
        for trato in tratos:
            if trato.estado in ("aceptado", "encuentro"):
                p = pt_px(trato.rect.center)
                if trato.estado == "encuentro" and (ticks // 400) % 2 == 0:
                    pygame.draw.circle(sup, COLOR_PUNTO, p, 5)
                else:
                    pygame.draw.circle(sup, COLOR_PUNTO, p, 4, 1)

        # Walter (parpadea)
        if (ticks // 300) % 2 == 0:
            pygame.draw.circle(sup, COLOR_TEXTO, pt_px(jugador.rect.center), 4)

        # ── Leyenda ──
        lx = zona.x + zona_mm_w + 6
        ly = zona.y + 2
        pygame.draw.rect(sup, (16, 16, 22),
                         (lx - 2, ly, ANCHO_LEY + 2, zona.height))
        for color, etq in [(COLOR_TEXTO,  "Vos"),
                           (COLOR_ORO,    "Local / franquicias"),
                           (AMARILLO,     "Zonas de venta"),
                           (COLOR_PUNTO,  "Tratos pendientes")]:
            pygame.draw.circle(sup, color, (lx + 5, ly + 7), 4)
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

    def _app_mensajes(self, sup, zona, tratos, reloj):
        sup.blit(self.fuente_titulo.render("Mensajes", True, COLOR_ORO),
                 (zona.x + 10, zona.y + 4))
        ofertas   = [t for t in tratos if t.estado == "oferta"]
        aceptados = [t for t in tratos if t.estado in ("aceptado", "encuentro")]
        self._rects_items = []
        y = zona.y + 36

        if not ofertas and not aceptados:
            for txt in ("No hay mensajes nuevos.",
                        "Los compradores escriben solos…"):
                sup.blit(self.fuente_chica.render(txt, True, COLOR_TEXTO_SUAVE),
                         (zona.x + 10, y)); y += 22
            return

        for i, trato in enumerate(ofertas):
            r = pygame.Rect(zona.x + 6, y, zona.width - 12, 74)
            self._rects_items.append(r)
            elegido = i == self.seleccion
            pygame.draw.rect(sup, (36, 38, 48) if elegido else (24, 26, 34),
                             r, border_radius=8)
            if elegido:
                pygame.draw.rect(sup, COLOR_APP_ACTIVA, r, 1, border_radius=8)
            sup.blit(self.fuente_chica.render(
                trato.comprador_nombre, True, COLOR_PUNTO), (r.x + 8, r.y + 5))
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
        self.fuente = pygame.font.Font(None, 34)
        self.fuente_titulo = pygame.font.Font(None, 56)
        self.fuente_chica = pygame.font.Font(None, 24)
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
        self.fuente = pygame.font.Font(None, 34)
        self.fuente_titulo = pygame.font.Font(None, 56)
        self.fuente_chica = pygame.font.Font(None, 24)
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
# Árbol de habilidades (tecla T)
# ---------------------------------------------------------
class PantallaHabilidades:
    """Grilla de 4 ramas x 3 nodos. Se navega con WASD/flechas o
    directamente con el mouse; E/Enter o click compran."""

    def __init__(self):
        self.fuente_titulo = pygame.font.Font(None, 56)
        self.fuente = pygame.font.Font(None, 26)
        self.fuente_chica = pygame.font.Font(None, 21)
        self.sel = [0, 0]          # [rama, nivel]
        self.mensaje = ""
        self.color_mensaje = COLOR_TEXTO
        self._cajas = {}           # (rama, nivel) -> rect clickeable

    def abrir(self):
        self.mensaje = ""

    def manejar_evento(self, evento, economia, habilidades, jugador):
        if evento.type == pygame.KEYDOWN:
            if evento.key in (pygame.K_ESCAPE, pygame.K_t):
                return "cerrar"
            if evento.key in (pygame.K_a, pygame.K_LEFT):
                self.sel[0] = (self.sel[0] - 1) % len(ARBOL)
            elif evento.key in (pygame.K_d, pygame.K_RIGHT):
                self.sel[0] = (self.sel[0] + 1) % len(ARBOL)
            elif evento.key in (pygame.K_w, pygame.K_UP):
                self.sel[1] = (self.sel[1] - 1) % 3
            elif evento.key in (pygame.K_s, pygame.K_DOWN):
                self.sel[1] = (self.sel[1] + 1) % 3
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
        if ok and ARBOL[rama]["nodos"][nivel]["id"] == "aguante":
            # Aplicar la vida extra al toque
            jugador.vida_max = habilidades.vida_max()
            jugador.vida = min(jugador.vida_max, jugador.vida + 40)

    def dibujar(self, superficie, economia, habilidades):
        velo = _panel(ANCHO_VENTANA, ALTO_VENTANA, alpha=185)
        superficie.blit(velo, (0, 0))
        titulo = self.fuente_titulo.render("HABILIDADES", True, COLOR_ORO)
        superficie.blit(titulo, ((ANCHO_VENTANA - titulo.get_width()) // 2, 26))
        recursos = self.fuente.render(
            f"Puntos: {economia.puntos}   ·   $ {economia.dinero}",
            True, COLOR_TEXTO)
        superficie.blit(recursos, ((ANCHO_VENTANA - recursos.get_width()) // 2, 72))

        self._cajas = {}
        ancho_caja, alto_caja = 180, 86
        margen_x = (ANCHO_VENTANA - 4 * ancho_caja - 3 * 12) // 2
        for rama, datos in enumerate(ARBOL):
            x = margen_x + rama * (ancho_caja + 12)
            encabezado = self.fuente.render(datos["nombre"], True, datos["color"])
            superficie.blit(encabezado, (x + (ancho_caja - encabezado.get_width()) // 2, 104))
            for nivel, nodo in enumerate(datos["nodos"]):
                y = 132 + nivel * (alto_caja + 10)
                rect = pygame.Rect(x, y, ancho_caja, alto_caja)
                self._cajas[(rama, nivel)] = rect
                estado = habilidades.estado(rama, nivel)
                elegida = [rama, nivel] == self.sel

                if estado == "comprada":
                    fondo, borde = (38, 34, 22, 235), datos["color"]
                elif estado == "disponible":
                    fondo, borde = (22, 22, 28, 235), COLOR_TEXTO_SUAVE
                else:
                    fondo, borde = (14, 14, 16, 235), (60, 60, 64)
                caja = pygame.Surface(rect.size, pygame.SRCALPHA)
                caja.fill(fondo)
                superficie.blit(caja, rect)
                pygame.draw.rect(superficie, COLOR_ORO if elegida else borde,
                                 rect, 2 if elegida else 1)

                color_nombre = datos["color"] if estado != "bloqueada" else (110, 110, 114)
                img = self.fuente_chica.render(nodo["nombre"], True, color_nombre)
                superficie.blit(img, (rect.x + 8, rect.y + 8))
                if estado == "comprada":
                    detalle, color_det = "✓ comprada", datos["color"]
                elif estado == "bloqueada":
                    detalle, color_det = "bloqueada", (110, 110, 114)
                else:
                    detalle = f"{nodo['puntos']} pts + ${nodo['dinero']}"
                    color_det = COLOR_TEXTO
                img = self.fuente_chica.render(detalle, True, color_det)
                superficie.blit(img, (rect.x + 8, rect.y + 32))

        # Descripción del nodo seleccionado + feedback
        nodo = ARBOL[self.sel[0]]["nodos"][self.sel[1]]
        desc = self.fuente.render(nodo["desc"], True, COLOR_TEXTO)
        superficie.blit(desc, ((ANCHO_VENTANA - desc.get_width()) // 2, 448))
        if self.mensaje:
            img = self.fuente_chica.render(self.mensaje, True, self.color_mensaje)
            superficie.blit(img, ((ANCHO_VENTANA - img.get_width()) // 2, 476))
        pie = self.fuente_chica.render(
            "Mouse o WASD + ENTER comprar  ·  T/ESC cerrar", True, COLOR_TEXTO_SUAVE)
        superficie.blit(pie, ((ANCHO_VENTANA - pie.get_width()) // 2, ALTO_VENTANA - 26))


# ---------------------------------------------------------
# Inventario grande (tecla O): todo lo que llevás, en una
# grilla de módulos con descripciones. Desde acá también se
# come un sanguche o se cambia de arma (E sobre el ítem).
# ---------------------------------------------------------
class PantallaInventario:
    COLUMNAS = 5
    FILAS = 3
    TAM = 64

    def __init__(self):
        self.fuente_titulo = pygame.font.Font(None, 52)
        self.fuente = pygame.font.Font(None, 26)
        self.fuente_chica = pygame.font.Font(None, 21)
        self.sel = 0
        self.mensaje = ""
        self._rects = []

    def abrir(self):
        self.mensaje = ""

    def _items(self, economia, jugador):
        """Los módulos del inventario: (id, nombre, cantidad, descripción)."""
        arma = ("Pistola" if economia.tiene_pistola else "Puños")
        if economia.tiene_pistola:
            estado_arma = ("equipada — E para guardarla"
                           if economia.arma_equipada
                           else "guardada — E para equiparla")
        else:
            estado_arma = "se compra en el almacén"
        items = [
            ("arma", arma, None, f"Tu arma. {estado_arma}."),
            ("balas", "Balas", economia.balas if economia.tiene_pistola else 0,
             "Munición de la pistola. Pack en el almacén."),
            ("comida", "Comida", economia.producto,
             f"Platos listos (calidad {round(economia.calidad * 100)}%). "
             "Se venden en el mostrador."),
            ("ingredientes", "Ingredientes", economia.ingredientes,
             "Para cocinar tandas. Se piden por el celular."),
            ("sanguche", "Sanguches", economia.sanguches,
             f"+{CURA_SANGUCHE} de vida — E para comer uno. "
             f"Máximo {MAX_SANGUCHES}."),
            ("med_nat", "Med. naturales", economia.med_nat,
             "Mercadería. Se vende en tratos por el celular."),
            ("med_quim", "Med. químicos", economia.med_quim,
             "Mercadería premium. Se vende en tratos por el celular."),
            ("efectivo", "Efectivo", economia.dinero,
             "La plata del bolsillo: se pierde en arrestos y muertes."),
            ("banco", "Banco", economia.banco,
             "Plata a salvo de multas y pérdidas."),
            ("franquicias", "Franquicias", economia.franquicias,
             f"Puestos comprados: +${INGRESO_FRANQUICIA} cada "
             f"{int(INTERVALO_FRANQUICIA)}s cada uno."),
            ("puntos", "Puntos", economia.puntos,
             "Puntos de habilidad — se gastan en el árbol (T)."),
            ("celular", "Celular", None,
             "Pedidos, mapa y mensajes (tecla C)."),
        ]
        if economia.receta_especial:
            items.append(("receta", "Receta especial", None,
                          "La receta del Proveedor: platos premium."))
        return items

    def manejar_evento(self, evento, economia, jugador):
        """Devuelve "cerrar", ("comer_sanguche",), ("alternar_arma",)
        o None."""
        items = self._items(economia, jugador)
        if evento.type == pygame.KEYDOWN:
            if evento.key in (pygame.K_ESCAPE, pygame.K_o):
                return "cerrar"
            if evento.key in (pygame.K_a, pygame.K_LEFT):
                self.sel = (self.sel - 1) % len(items)
            elif evento.key in (pygame.K_d, pygame.K_RIGHT):
                self.sel = (self.sel + 1) % len(items)
            elif evento.key in (pygame.K_w, pygame.K_UP):
                self.sel = (self.sel - self.COLUMNAS) % len(items)
            elif evento.key in (pygame.K_s, pygame.K_DOWN):
                self.sel = (self.sel + self.COLUMNAS) % len(items)
            elif evento.key in (pygame.K_RETURN, pygame.K_e, pygame.K_SPACE):
                return self._usar(items[self.sel][0])
        elif evento.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(self._rects):
                if rect.collidepoint(evento.pos):
                    self.sel = i
        elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            for i, rect in enumerate(self._rects):
                if rect.collidepoint(evento.pos):
                    self.sel = i
                    return self._usar(items[i][0])
        return None

    def _usar(self, id_item):
        if id_item == "sanguche":
            return ("comer_sanguche",)
        if id_item == "arma":
            return ("alternar_arma",)
        return None

    def dibujar(self, superficie, economia, jugador):
        velo = _panel(ANCHO_VENTANA, ALTO_VENTANA, alpha=185)
        superficie.blit(velo, (0, 0))
        titulo = self.fuente_titulo.render("INVENTARIO", True, COLOR_ORO)
        superficie.blit(titulo, ((ANCHO_VENTANA - titulo.get_width()) // 2, 26))
        vida = self.fuente_chica.render(
            f"Vida {max(0, jugador.vida)}/{jugador.vida_max}",
            True, COLOR_TEXTO_SUAVE)
        superficie.blit(vida, ((ANCHO_VENTANA - vida.get_width()) // 2, 68))

        items = self._items(economia, jugador)
        self.sel = min(self.sel, len(items) - 1)
        self._rects = []
        sep = 10
        ancho_total = self.COLUMNAS * self.TAM + (self.COLUMNAS - 1) * sep
        x0 = (ANCHO_VENTANA - ancho_total) // 2
        y0 = 96
        for i, (id_item, nombre, cuenta, _) in enumerate(items):
            col = i % self.COLUMNAS
            fila = i // self.COLUMNAS
            rect = pygame.Rect(x0 + col * (self.TAM + sep),
                               y0 + fila * (self.TAM + sep + 16),
                               self.TAM, self.TAM)
            self._rects.append(rect)
            elegido = i == self.sel
            caja = pygame.Surface(rect.size, pygame.SRCALPHA)
            caja.fill((*COLOR_SLOT, 235))
            superficie.blit(caja, rect)
            pygame.draw.rect(superficie,
                             COLOR_SLOT_SEL if elegido else COLOR_SLOT_BORDE,
                             rect, 2 if elegido else 1)
            icono = id_item
            if id_item == "arma" and not economia.tiene_pistola:
                icono = "punos"
            dibujar_icono(superficie, icono, rect, economia)
            if cuenta is not None:
                texto = f"${cuenta}" if id_item in ("efectivo", "banco") \
                    else str(cuenta)
                img = self.fuente_chica.render(texto, True, COLOR_TEXTO)
                superficie.blit(img, (rect.right - img.get_width() - 4,
                                      rect.bottom - img.get_height() - 3))
            # Nombre debajo del módulo
            img = self.fuente_chica.render(nombre, True,
                                           COLOR_ORO if elegido else COLOR_TEXTO_SUAVE)
            superficie.blit(img, (rect.centerx - img.get_width() // 2,
                                  rect.bottom + 2))

        # Descripción del ítem seleccionado
        desc = items[self.sel][3]
        img = self.fuente.render(desc, True, COLOR_TEXTO)
        superficie.blit(img, ((ANCHO_VENTANA - img.get_width()) // 2,
                              ALTO_VENTANA - 84))
        if self.mensaje:
            img = self.fuente_chica.render(self.mensaje, True, COLOR_DINERO)
            superficie.blit(img, ((ANCHO_VENTANA - img.get_width()) // 2,
                                  ALTO_VENTANA - 56))
        pie = self.fuente_chica.render(
            "Mouse o WASD  ·  E — usar  ·  O/ESC — cerrar",
            True, COLOR_TEXTO_SUAVE)
        superficie.blit(pie, ((ANCHO_VENTANA - pie.get_width()) // 2,
                              ALTO_VENTANA - 28))
