# =========================================================
# FAST EMPIRE — Interfaz de usuario  [Fase 5]
#
# - HUD: panel de recursos ocultable con TAB, búsqueda (solo
#   cuando hay lío), punto ilegal (solo si está desbloqueado).
# - Menús con soporte de MOUSE: mover el mouse resalta la
#   opción y el click izquierdo la confirma; el teclado
#   (W/S + E/Enter) sigue funcionando igual.
# - Pantallas: MenuPrincipal, PantallaOpciones, MenuPausa,
#   PantallaTienda, PantallaPedidos (los medicamentos
#   aparecen bloqueados hasta conocer al proveedor) y
#   PantallaHabilidades (árbol de la Fase 5, tecla T).
# =========================================================

import pygame

from .settings import (
    ANCHO_VENTANA, ALTO_VENTANA,
    COLOR_FONDO, COLOR_TEXTO, COLOR_TEXTO_SUAVE,
    COLOR_ORO, COLOR_DINERO, COLOR_ERROR,
    COLOR_VIDA, COLOR_VIDA_FONDO,
    COLOR_MED_NAT, COLOR_MED_QUIM, COLOR_PUNTO,
)
from .economy import (
    PEDIDOS, TIEMPO_ENTREGA, RECETAS,
    PRECIO_PISTOLA, PRECIO_BALAS, BALAS_POR_PACK,
    PRECIO_SANGUCHE, CURA_SANGUCHE,
    INGRESO_FRANQUICIA, INTERVALO_FRANQUICIA,
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
# HUD del juego
# ---------------------------------------------------------
class HUD:
    def __init__(self):
        self.fuente = pygame.font.Font(None, 24)
        self.fuente_chica = pygame.font.Font(None, 20)
        self.fuente_aviso = pygame.font.Font(None, 68)

    def dibujar(self, superficie, jugador, economia, produccion,
                punto, en_punto, pista, busqueda, pedidos, fps,
                mostrar_panel=True, mision=None):
        if mostrar_panel:
            self._panel_recursos(superficie, jugador, economia, pedidos)
            if produccion.en_curso:
                self._barra_coccion(superficie, produccion)
        else:
            # Panel oculto (TAB): queda solo la vida, que es vital
            pygame.draw.rect(superficie, COLOR_VIDA_FONDO, (8, 8, 160, 8))
            relleno = int(160 * max(0, jugador.vida) / jugador.vida_max)
            pygame.draw.rect(superficie, COLOR_VIDA, (8, 8, relleno, 8))

        if economia.meds_desbloqueados:
            if en_punto:
                self._banner_punto(superficie, punto)
            self._ubicacion_punto(superficie, punto, busqueda)
        if mision is not None:
            self._banner_mision(superficie, mision, en_punto)
        if pista:
            self._pista(superficie, pista)
        if busqueda.nivel > 0:
            self._nivel_busqueda(superficie, busqueda)
        img = self.fuente_chica.render(f"{fps} FPS", True, COLOR_TEXTO_SUAVE)
        superficie.blit(img, (ANCHO_VENTANA - img.get_width() - 8,
                              ALTO_VENTANA - img.get_height() - 6))

    def _panel_recursos(self, superficie, jugador, economia, pedidos):
        lineas = [
            (f"$ {economia.dinero}", COLOR_DINERO),
            (f"Ingredientes: {economia.ingredientes}", COLOR_TEXTO),
        ]
        comida = f"Comida: {economia.producto}"
        if economia.producto:
            comida += f"  (calidad {round(economia.calidad * 100)}%)"
        lineas.append((comida, COLOR_TEXTO))
        if economia.meds_desbloqueados:
            lineas.append((
                f"Meds: {economia.med_nat} naturales · {economia.med_quim} químicos",
                COLOR_MED_QUIM if economia.med_quim else COLOR_MED_NAT))
        if economia.tiene_pistola:
            lineas.append((f"Pistola — {economia.balas} balas", COLOR_TEXTO))
        if economia.banco:
            lineas.append((f"Banco: $ {economia.banco} (a salvo)", COLOR_DINERO))
        if economia.franquicias:
            ganancia = economia.franquicias * INGRESO_FRANQUICIA
            lineas.append((
                f"Franquicias: {economia.franquicias}  "
                f"(+${ganancia} cada {int(INTERVALO_FRANQUICIA)}s)",
                COLOR_DINERO))
        lineas.append((f"Puntos de habilidad: {economia.puntos}  [T]", COLOR_ORO))
        if pedidos:
            faltan = int(min(p["timer"] for p in pedidos)) + 1
            texto = f"Pedido en camino: {faltan}s"
            if len(pedidos) > 1:
                texto += f"  (+{len(pedidos) - 1} más)"
            lineas.append((texto, COLOR_TEXTO_SUAVE))

        alto = 44 + len(lineas) * 20
        superficie.blit(_panel(250, alto), (8, 8))
        pygame.draw.rect(superficie, COLOR_VIDA_FONDO, (18, 18, 230, 12))
        relleno = int(230 * max(0, jugador.vida) / jugador.vida_max)
        pygame.draw.rect(superficie, COLOR_VIDA, (18, 18, relleno, 12))
        y = 36
        for texto, color in lineas:
            superficie.blit(self.fuente.render(texto, True, color), (18, y))
            y += 20

    def _barra_coccion(self, superficie, produccion):
        x, y, ancho, alto = 8, 212, 250, 18
        superficie.blit(_panel(ancho, alto), (x, y))
        relleno = int((ancho - 4) * min(1.0, produccion.progreso))
        pygame.draw.rect(superficie, COLOR_ORO, (x + 2, y + 2, relleno, alto - 4))
        img = self.fuente_chica.render("Cocinando…", True, COLOR_FONDO)
        superficie.blit(img, (x + 8, y + 2))

    def _banner_punto(self, superficie, punto):
        texto = (f"{punto.nombre} — quedan {punto.restantes} compradores — "
                 f"se muda en {int(punto.timer_vida) + 1}s")
        img = self.fuente.render(texto, True, COLOR_PUNTO)
        ancho = max(img.get_width() + 24, 300)
        x = (ANCHO_VENTANA - ancho) // 2
        superficie.blit(_panel(ancho, 40), (x, 8))
        superficie.blit(img, ((ANCHO_VENTANA - img.get_width()) // 2, 14))
        proporcion = punto.restantes / max(1, punto.demanda)
        relleno = int((ancho - 16) * max(0.0, min(1.0, proporcion)))
        pygame.draw.rect(superficie, COLOR_PUNTO, (x + 8, 36, relleno, 5))

    def _banner_mision(self, superficie, mision, en_punto):
        """Misión activa del Proveedor: objetivo, progreso y reloj.
        Si el banner del punto está visible, se corre abajo."""
        texto = (f"MISIÓN: {mision['desc']} — "
                 f"{mision['progreso']}/{mision['objetivo']} — "
                 f"{int(mision['timer']) + 1}s")
        img = self.fuente.render(texto, True, COLOR_ORO)
        ancho = img.get_width() + 24
        x = (ANCHO_VENTANA - ancho) // 2
        y = 52 if en_punto else 8
        superficie.blit(_panel(ancho, 30), (x, y))
        superficie.blit(img, (x + 12, y + 6))

    def _ubicacion_punto(self, superficie, punto, busqueda):
        y = 56 if busqueda.nivel > 0 else 8
        img = self.fuente_chica.render(f"Punto: {punto.nombre}", True, COLOR_PUNTO)
        ancho = img.get_width() + 16
        x = ANCHO_VENTANA - ancho - 8
        superficie.blit(_panel(ancho, 26), (x, y))
        superficie.blit(img, (x + 8, y + 5))

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
        y = ALTO_VENTANA - 52
        superficie.blit(_panel(ancho, 34), (x, y))
        superficie.blit(img, (x + 14, y + 8))

    def dibujar_aviso(self, superficie, titulo, detalle):
        superficie.blit(_panel(ANCHO_VENTANA, 130, alpha=200),
                        (0, ALTO_VENTANA // 2 - 65))
        img = self.fuente_aviso.render(titulo, True, COLOR_ERROR)
        superficie.blit(img, ((ANCHO_VENTANA - img.get_width()) // 2,
                              ALTO_VENTANA // 2 - 52))
        sub = self.fuente.render(detalle, True, COLOR_TEXTO)
        superficie.blit(sub, ((ANCHO_VENTANA - sub.get_width()) // 2,
                              ALTO_VENTANA // 2 + 18))


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
        "W A S D — moverse   ·   Mouse — apuntar",
        "Click izq. — disparar/golpear   ·   Click der. (sostener) — mira",
        "E — atender, cocinar, teléfono, cajas, almacén, banco",
        "T — habilidades   ·   TAB — ocultar panel   ·   ESC — pausa",
        "Cmd+F o F11 — pantalla completa",
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
        superficie.blit(titulo, ((ANCHO_VENTANA - titulo.get_width()) // 2, 45))
        y = 125
        for texto in self.CONTROLES:
            img = self.fuente_chica.render(texto, True, COLOR_TEXTO_SUAVE)
            superficie.blit(img, ((ANCHO_VENTANA - img.get_width()) // 2, y))
            y += 30
        self._dibujar_opciones(superficie, 315, interlinea=50)
        pie = self.fuente_chica.render(
            "Mouse o W/S + ENTER  ·  ESC volver", True, COLOR_TEXTO_SUAVE)
        superficie.blit(pie, ((ANCHO_VENTANA - pie.get_width()) // 2, ALTO_VENTANA - 45))


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
        ("sanguche", f"Sanguche casero (+{CURA_SANGUCHE} vida) — ${PRECIO_SANGUCHE}"),
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
            if jugador.vida >= jugador.vida_max:
                self._mensaje_error("Estás al 100% de vida.")
            elif economia.pagar(PRECIO_SANGUCHE):
                jugador.vida = min(jugador.vida_max, jugador.vida + CURA_SANGUCHE)
                self._feedback(True, "¡Qué sanguche! Vida recuperada.")
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
# Teléfono del local: pedidos con delivery en cajas
# ---------------------------------------------------------
class PantallaPedidos(_MenuVertical):
    # ids en el mismo orden en que se muestran
    IDS = ["ing6", "ing12", "nat3", "nat6", "quim3", "quim6", "salir"]
    MEDS = ("nat3", "nat6", "quim3", "quim6")

    def __init__(self):
        super().__init__(self._etiquetas(meds_ok=False))
        self.fuente = pygame.font.Font(None, 34)
        self.fuente_titulo = pygame.font.Font(None, 56)
        self.fuente_chica = pygame.font.Font(None, 24)
        self.mensaje = ""
        self.color_mensaje = COLOR_TEXTO

    def _etiquetas(self, meds_ok):
        etiquetas = []
        for id_pedido in self.IDS[:-1]:
            if id_pedido in self.MEDS and not meds_ok:
                etiquetas.append("— línea muerta —")
            else:
                nombre, _, costo = PEDIDOS[id_pedido]
                etiquetas.append(f"{nombre} — ${costo}")
        etiquetas.append("Colgar")
        return etiquetas

    def abrir(self):
        self.seleccion = 0
        self.mensaje = ""

    def manejar_evento(self, evento, economia):
        """Devuelve "cerrar", ("pedido", id) si compró, o None."""
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
            return "cerrar"
        i = self._navegar(evento)
        if i is None:
            return None
        id_pedido = self.IDS[i]
        if id_pedido == "salir":
            return "cerrar"
        if id_pedido in self.MEDS and not economia.meds_desbloqueados:
            self.mensaje = "Nadie contesta en ese número… todavía."
            self.color_mensaje = COLOR_ERROR
            return None
        nombre, _, costo = PEDIDOS[id_pedido]
        if economia.pagar(costo):
            self.mensaje = f"{nombre}: llega en ~{int(TIEMPO_ENTREGA)}s a la puerta."
            self.color_mensaje = COLOR_DINERO
            return ("pedido", id_pedido)
        self.mensaje = "No te alcanza la plata."
        self.color_mensaje = COLOR_ERROR
        return None

    def dibujar(self, superficie, economia):
        # Refrescar etiquetas según si el proveedor ya te contactó
        self.opciones[:] = self._etiquetas(economia.meds_desbloqueados)
        velo = _panel(ANCHO_VENTANA, ALTO_VENTANA, alpha=170)
        superficie.blit(velo, (0, 0))
        titulo = self.fuente_titulo.render("PEDIDOS POR TELÉFONO", True, COLOR_ORO)
        superficie.blit(titulo, ((ANCHO_VENTANA - titulo.get_width()) // 2, 80))
        if economia.meds_desbloqueados:
            aviso = "los medicamentos se venden en el punto ilegal, no en el mostrador"
        else:
            aviso = "por ahora solo ingredientes — hacé crecer el local"
        info = self.fuente_chica.render(
            f"$ {economia.dinero}  ·  {aviso}", True, COLOR_TEXTO_SUAVE)
        superficie.blit(info, ((ANCHO_VENTANA - info.get_width()) // 2, 145))
        self._dibujar_opciones(superficie, 200, interlinea=44)
        if self.mensaje:
            img = self.fuente_chica.render(self.mensaje, True, self.color_mensaje)
            superficie.blit(img, ((ANCHO_VENTANA - img.get_width()) // 2, 440))
        pie = self.fuente_chica.render(
            "Mouse o W/S + ENTER  ·  ESC colgar", True, COLOR_TEXTO_SUAVE)
        superficie.blit(pie, ((ANCHO_VENTANA - pie.get_width()) // 2, ALTO_VENTANA - 60))


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
            superficie.blit(img, ((ANCHO_VENTANA - img.get_width()) // 2, 480))
        pie = self.fuente_chica.render(
            "Mouse o WASD + ENTER comprar  ·  T/ESC cerrar", True, COLOR_TEXTO_SUAVE)
        superficie.blit(pie, ((ANCHO_VENTANA - pie.get_width()) // 2, ALTO_VENTANA - 44))
