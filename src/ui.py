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
# Íconos del inventario (dibujados a mano, sin archivos)
# ---------------------------------------------------------
def dibujar_icono(superficie, id_item, rect, economia=None):
    """Ícono pixelado de cada ítem, centrado en el rect."""
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
# EL CELULAR (Fase 11): un teléfono de verdad con tres apps —
# Pedidos (compras con delivery), Mapa (el mapa del juego con
# marcadores) y Mensajes (los tratos del mercado negro).
# Se abre con C en cualquier lado o con E en el teléfono del local.
# ---------------------------------------------------------
class PantallaCelular:
    APPS = ["Pedidos", "Mapa", "Mensajes"]
    IDS_PEDIDOS = ["ing6", "ing12", "nat3", "nat6", "quim3", "quim6"]
    MEDS = ("nat3", "nat6", "quim3", "quim6")

    # Geometría del teléfono (centrado en la pantalla)
    ANCHO_TEL = 300
    ALTO_TEL = 512

    def __init__(self):
        self.fuente = pygame.font.Font(None, 24)
        self.fuente_chica = pygame.font.Font(None, 20)
        self.fuente_titulo = pygame.font.Font(None, 30)
        self.app = 0            # índice en APPS
        self.seleccion = 0
        self.mensaje = ""
        self.color_mensaje = COLOR_TEXTO
        self._minimapa = None   # se prerenderiza al primer uso
        self._rects_apps = []
        self._rects_items = []

    def abrir(self, app=None):
        if app is not None:
            self.app = app
        self.seleccion = 0
        self.mensaje = ""

    # --- eventos ---
    def manejar_evento(self, evento, economia, tratos, reloj):
        """Devuelve "cerrar", ("pedido", id), ("aceptar", trato),
        ("rechazar", trato) o None."""
        if evento.type == pygame.KEYDOWN:
            if evento.key in (pygame.K_ESCAPE, pygame.K_c):
                return "cerrar"
            if evento.key in (pygame.K_a, pygame.K_LEFT):
                self.app = (self.app - 1) % len(self.APPS)
                self.seleccion = 0
                self.mensaje = ""
            elif evento.key in (pygame.K_d, pygame.K_RIGHT):
                self.app = (self.app + 1) % len(self.APPS)
                self.seleccion = 0
                self.mensaje = ""
            elif self.app == 0:
                return self._evento_pedidos_teclado(evento, economia)
            elif self.app == 2:
                return self._evento_mensajes_teclado(evento, tratos)
        elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            for i, rect in enumerate(self._rects_apps):
                if rect.collidepoint(evento.pos):
                    self.app = i
                    self.seleccion = 0
                    self.mensaje = ""
                    return None
            for i, rect in enumerate(self._rects_items):
                if rect.collidepoint(evento.pos):
                    self.seleccion = i
                    if self.app == 0:
                        return self._comprar_pedido(economia)
                    if self.app == 2:
                        return self._aceptar_seleccion(tratos)
        elif evento.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(self._rects_items):
                if rect.collidepoint(evento.pos):
                    self.seleccion = i
        return None

    def _evento_pedidos_teclado(self, evento, economia):
        if evento.key in (pygame.K_w, pygame.K_UP):
            self.seleccion = (self.seleccion - 1) % len(self.IDS_PEDIDOS)
        elif evento.key in (pygame.K_s, pygame.K_DOWN):
            self.seleccion = (self.seleccion + 1) % len(self.IDS_PEDIDOS)
        elif evento.key in (pygame.K_RETURN, pygame.K_e, pygame.K_SPACE):
            return self._comprar_pedido(economia)
        return None

    def _evento_mensajes_teclado(self, evento, tratos):
        ofertas = [t for t in tratos if t.estado == "oferta"]
        if not ofertas:
            return None
        if evento.key in (pygame.K_w, pygame.K_UP):
            self.seleccion = (self.seleccion - 1) % len(ofertas)
        elif evento.key in (pygame.K_s, pygame.K_DOWN):
            self.seleccion = (self.seleccion + 1) % len(ofertas)
        elif evento.key in (pygame.K_RETURN, pygame.K_e, pygame.K_SPACE):
            return self._aceptar_seleccion(tratos)
        elif evento.key == pygame.K_x:
            if self.seleccion < len(ofertas):
                return ("rechazar", ofertas[self.seleccion])
        return None

    def _comprar_pedido(self, economia):
        id_pedido = self.IDS_PEDIDOS[self.seleccion]
        if id_pedido in self.MEDS and not economia.meds_desbloqueados:
            self.mensaje = "Nadie contesta ese número… todavía."
            self.color_mensaje = COLOR_ERROR
            return None
        nombre, _, costo = PEDIDOS[id_pedido]
        if economia.pagar(costo):
            self.mensaje = f"En camino (~{int(TIEMPO_ENTREGA)}s a la puerta)."
            self.color_mensaje = COLOR_DINERO
            return ("pedido", id_pedido)
        self.mensaje = "No te alcanza la plata."
        self.color_mensaje = COLOR_ERROR
        return None

    def _aceptar_seleccion(self, tratos):
        ofertas = [t for t in tratos if t.estado == "oferta"]
        if self.seleccion < len(ofertas):
            return ("aceptar", ofertas[self.seleccion])
        return None

    # --- dibujo ---
    def dibujar(self, superficie, economia, tratos, reloj, mapa,
                jugador, franquicias):
        velo = _panel(ANCHO_VENTANA, ALTO_VENTANA, alpha=150)
        superficie.blit(velo, (0, 0))

        x = (ANCHO_VENTANA - self.ANCHO_TEL) // 2
        y = (ALTO_VENTANA - self.ALTO_TEL) // 2
        # Carcasa con bordes redondeados y pantalla
        pygame.draw.rect(superficie, COLOR_CELULAR,
                         (x, y, self.ANCHO_TEL, self.ALTO_TEL),
                         border_radius=24)
        pygame.draw.rect(superficie, COLOR_CELULAR_BORDE,
                         (x, y, self.ANCHO_TEL, self.ALTO_TEL), 2,
                         border_radius=24)
        pantalla = pygame.Rect(x + 10, y + 32, self.ANCHO_TEL - 20,
                               self.ALTO_TEL - 92)
        pygame.draw.rect(superficie, COLOR_PANTALLA_CEL, pantalla,
                         border_radius=8)
        # Notch + parlante
        pygame.draw.rect(superficie, (10, 10, 12),
                         (x + self.ANCHO_TEL // 2 - 30, y + 10, 60, 14),
                         border_radius=7)

        # Barra de estado: hora, señal y batería
        hora = self.fuente_chica.render(
            f"{reloj.hora:02d}:{reloj.minuto:02d}", True, COLOR_TEXTO)
        superficie.blit(hora, (pantalla.x + 8, pantalla.y + 5))
        for i in range(4):
            alto_barra = 3 + i * 2
            pygame.draw.rect(superficie, COLOR_TEXTO_SUAVE,
                             (pantalla.right - 66 + i * 6,
                              pantalla.y + 14 - alto_barra, 4, alto_barra))
        pygame.draw.rect(superficie, COLOR_TEXTO_SUAVE,
                         (pantalla.right - 34, pantalla.y + 5, 22, 10), 1)
        pygame.draw.rect(superficie, COLOR_DINERO,
                         (pantalla.right - 32, pantalla.y + 7, 14, 6))

        contenido = pygame.Rect(pantalla.x, pantalla.y + 24,
                                pantalla.width, pantalla.height - 24)
        if self.app == 0:
            self._app_pedidos(superficie, contenido, economia)
        elif self.app == 1:
            self._app_mapa(superficie, contenido, mapa, jugador,
                           tratos, franquicias)
        else:
            self._app_mensajes(superficie, contenido, tratos, reloj)

        # Barra de apps (abajo del teléfono)
        self._rects_apps = []
        ancho_app = (self.ANCHO_TEL - 40) // 3
        ofertas = sum(1 for t in tratos if t.estado == "oferta")
        for i, nombre in enumerate(self.APPS):
            rx = x + 20 + i * ancho_app
            rect = pygame.Rect(rx, y + self.ALTO_TEL - 52, ancho_app - 6, 40)
            self._rects_apps.append(rect)
            activa = i == self.app
            color = COLOR_APP_ACTIVA if activa else (40, 40, 48)
            pygame.draw.rect(superficie, color, rect, border_radius=9)
            etiqueta = nombre
            if i == 2 and ofertas:
                etiqueta += f" ({ofertas})"
            img = self.fuente_chica.render(
                etiqueta, True, COLOR_FONDO if activa else COLOR_TEXTO)
            superficie.blit(img, (rect.centerx - img.get_width() // 2,
                                  rect.centery - img.get_height() // 2))

        pie = self.fuente_chica.render(
            "A/D — cambiar app  ·  C/ESC — guardar el celu",
            True, COLOR_TEXTO_SUAVE)
        superficie.blit(pie, ((ANCHO_VENTANA - pie.get_width()) // 2,
                              y + self.ALTO_TEL + 4))

    def _app_pedidos(self, superficie, zona, economia):
        titulo = self.fuente_titulo.render("Pedidos", True, COLOR_ORO)
        superficie.blit(titulo, (zona.x + 10, zona.y + 4))
        plata = self.fuente_chica.render(
            f"$ {economia.dinero}", True, COLOR_DINERO)
        superficie.blit(plata, (zona.right - plata.get_width() - 10, zona.y + 10))

        self._rects_items = []
        y = zona.y + 36
        for i, id_pedido in enumerate(self.IDS_PEDIDOS):
            rect = pygame.Rect(zona.x + 6, y, zona.width - 12, 42)
            self._rects_items.append(rect)
            elegido = i == self.seleccion
            bloqueado = (id_pedido in self.MEDS
                         and not economia.meds_desbloqueados)
            fondo = (36, 38, 48) if elegido else (24, 26, 34)
            pygame.draw.rect(superficie, fondo, rect, border_radius=6)
            if elegido:
                pygame.draw.rect(superficie, COLOR_APP_ACTIVA, rect, 1,
                                 border_radius=6)
            if bloqueado:
                nombre, costo = "— línea muerta —", ""
                color = (90, 90, 96)
            else:
                nombre, _, precio = PEDIDOS[id_pedido]
                costo = f"${precio}"
                color = COLOR_TEXTO
            img = self.fuente_chica.render(nombre, True, color)
            superficie.blit(img, (rect.x + 8, rect.y + 6))
            if costo:
                img = self.fuente_chica.render(costo, True, COLOR_DINERO)
                superficie.blit(img, (rect.x + 8, rect.y + 23))
            y += 46

        if self.mensaje:
            img = self.fuente_chica.render(self.mensaje, True,
                                           self.color_mensaje)
            superficie.blit(img, (zona.x + 8, zona.bottom - 24))

    def _prerender_minimapa(self, mapa):
        """Mapa completo a 2 px por tile (se genera una sola vez)."""
        from .map import MAPA
        escala = 2
        superficie = pygame.Surface((mapa.columnas * escala,
                                     mapa.filas * escala))
        colores = {
            "X": COLOR_EDIFICIO, "H": COLOR_CASA, "A": COLOR_ARBOL,
            "k": COLOR_TIENDA_TOLDO, "C": COLOR_PISO_LOCAL,
            "M": COLOR_PISO_LOCAL, "F": COLOR_PISO_LOCAL,
            "p": COLOR_PISO_LOCAL, "T": COLOR_TIENDA_TOLDO,
            "B": COLOR_BANCO, "S": COLOR_HOSPITAL, "w": COLOR_AGUA,
            ".": COLOR_CALLE, ",": COLOR_PASTO, "~": COLOR_TIERRA,
        }
        for fila, linea in enumerate(MAPA):
            for col, tile in enumerate(linea):
                superficie.fill(colores.get(tile, COLOR_CALLE),
                                (col * escala, fila * escala, escala, escala))
        return superficie

    def _app_mapa(self, superficie, zona, mapa, jugador, tratos, franquicias):
        titulo = self.fuente_titulo.render("Mapa", True, COLOR_ORO)
        superficie.blit(titulo, (zona.x + 10, zona.y + 4))
        if self._minimapa is None:
            self._minimapa = self._prerender_minimapa(mapa)

        mm = self._minimapa
        mx = zona.x + (zona.width - mm.get_width()) // 2
        my = zona.y + 36
        superficie.blit(mm, (mx, my))
        pygame.draw.rect(superficie, COLOR_CELULAR_BORDE,
                         (mx - 1, my - 1, mm.get_width() + 2,
                          mm.get_height() + 2), 1)

        escala = mm.get_width() / mapa.ancho_px

        def punto(pos_px):
            return (mx + int(pos_px[0] * escala), my + int(pos_px[1] * escala))

        # Local (dorado), franquicias compradas (doradas chicas)
        pygame.draw.rect(superficie, COLOR_ORO, (*punto((4 * TILE, 4 * TILE)), 5, 5))
        for franquicia in franquicias:
            if franquicia.comprada:
                pygame.draw.rect(superficie, COLOR_ORO,
                                 (*punto(franquicia.rect.center), 3, 3))
        # Tratos: aceptados (violeta), encuentro activo (parpadea)
        for trato in tratos:
            if trato.estado == "aceptado":
                pygame.draw.circle(superficie, COLOR_PUNTO,
                                   punto(trato.rect.center), 4, 1)
            elif trato.estado == "encuentro":
                if (pygame.time.get_ticks() // 400) % 2 == 0:
                    pygame.draw.circle(superficie, COLOR_PUNTO,
                                       punto(trato.rect.center), 5)
        # Walter (blanco, parpadea)
        if (pygame.time.get_ticks() // 300) % 2 == 0:
            pygame.draw.rect(superficie, COLOR_TEXTO,
                             (*punto(jugador.rect.center), 4, 4))

        leyenda = [("Vos", COLOR_TEXTO), ("Local/franquicias", COLOR_ORO),
                   ("Tratos", COLOR_PUNTO)]
        y = my + mm.get_height() + 8
        x = zona.x + 10
        for texto, color in leyenda:
            pygame.draw.rect(superficie, color, (x, y + 4, 8, 8))
            img = self.fuente_chica.render(texto, True, COLOR_TEXTO_SUAVE)
            superficie.blit(img, (x + 12, y))
            x += img.get_width() + 30
        self._rects_items = []

    def _app_mensajes(self, superficie, zona, tratos, reloj):
        titulo = self.fuente_titulo.render("Mensajes", True, COLOR_ORO)
        superficie.blit(titulo, (zona.x + 10, zona.y + 4))

        ofertas = [t for t in tratos if t.estado == "oferta"]
        aceptados = [t for t in tratos if t.estado in ("aceptado", "encuentro")]
        self._rects_items = []
        y = zona.y + 36

        if not ofertas and not aceptados:
            img = self.fuente_chica.render(
                "No hay mensajes nuevos.", True, COLOR_TEXTO_SUAVE)
            superficie.blit(img, (zona.x + 10, y))
            img = self.fuente_chica.render(
                "Los compradores escriben solos…", True, COLOR_TEXTO_SUAVE)
            superficie.blit(img, (zona.x + 10, y + 22))
            return

        for i, trato in enumerate(ofertas):
            alto = 74
            rect = pygame.Rect(zona.x + 6, y, zona.width - 12, alto)
            self._rects_items.append(rect)
            elegido = i == self.seleccion
            fondo = (36, 38, 48) if elegido else (24, 26, 34)
            pygame.draw.rect(superficie, fondo, rect, border_radius=8)
            if elegido:
                pygame.draw.rect(superficie, COLOR_APP_ACTIVA, rect, 1,
                                 border_radius=8)
            quien = self.fuente_chica.render(
                trato.comprador_nombre, True, COLOR_PUNTO)
            superficie.blit(quien, (rect.x + 8, rect.y + 5))
            for j, linea in enumerate(
                    _envolver_lineas(self.fuente_chica, trato.mensaje(reloj),
                                     rect.width - 16)):
                img = self.fuente_chica.render(linea, True, COLOR_TEXTO)
                superficie.blit(img, (rect.x + 8, rect.y + 23 + j * 17))
            y += alto + 6

        if ofertas:
            img = self.fuente_chica.render(
                "E — aceptar  ·  X — rechazar", True, COLOR_TEXTO_SUAVE)
            superficie.blit(img, (zona.x + 10, y + 2))
            y += 22

        for trato in aceptados:
            estado = ("TE ESPERA" if trato.estado == "encuentro"
                      else reloj.texto_hora(trato.minuto_cita))
            img = self.fuente_chica.render(
                f"✓ {trato.nombre_lugar} — {estado} — ${trato.total}",
                True, COLOR_DINERO)
            superficie.blit(img, (zona.x + 10, y + 4))
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
