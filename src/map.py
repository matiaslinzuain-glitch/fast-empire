# =========================================================
# FAST EMPIRE — Mapa y colisiones  [Fase 4]
# El mapa (60x45 tiles = 1920x1440 px) se arma concatenando
# piezas con nombre: cada fila valida que mida 60 caracteres,
# así editar una manzana no puede desalinear las colisiones.
#
# Leyenda:
#   X = edificio / pared (sólido)
#   H = casa con techo de tejas (sólida)
#   A = árbol (sólido)
#   C = cocina de Walter (sólida, interactuable con E)
#   M = mostrador del local (sólido; se atiende desde atrás con E)
#   F = teléfono del local (sólido, interactuable: pedidos)
#   T = almacén del barrio (sólido, interactuable: armas/curas)
#   p = piso de madera del local (transitable)
#   . = calle de asfalto (transitable)
#   , = pasto (transitable)
#   ~ = camino de tierra (portones al campo, transitable)
#
# Distribución: el local de Walter arriba a la izquierda, un
# parque al norte, manzanas de casas, dos baldíos, la terminal
# vieja al sur y el campo al este (muro con dos portones).
# El punto de venta ilegal NO es un tile: rota entre lugares
# candidatos definidos en economy.py.
# =========================================================

import pygame

from .settings import (
    TILE,
    COLOR_CALLE, COLOR_CALLE_LINEA,
    COLOR_PASTO, COLOR_PASTO_DET,
    COLOR_TIERRA,
    COLOR_EDIFICIO, COLOR_EDIFICIO_TOP,
    COLOR_CASA, COLOR_CASA_TECHO,
    COLOR_ARBOL, COLOR_ARBOL_LUZ,
    COLOR_COCINA, COLOR_COCINA_TOP,
    COLOR_TIENDA, COLOR_TIENDA_TOLDO,
    COLOR_PISO_LOCAL, COLOR_PISO_LINEA,
    COLOR_MOSTRADOR, COLOR_MOSTRADOR_TOP,
    COLOR_TELEFONO, COLOR_TELEFONO_LUZ,
    COLOR_AGUA, COLOR_AGUA_LUZ,
    COLOR_BANCO, COLOR_BANCO_FRANJA,
    COLOR_HOSPITAL, COLOR_HOSPITAL_CRUZ,
)

# --- Piezas de la ciudad (columnas 1 a 44 de cada fila) ---
_C2 = ".."                      # calle vertical de 2 tiles
_CALLE44 = "." * 44             # calle horizontal completa
_CASAS14 = ".HHHH...HHHH.."     # manzana de casas (bloque oeste)
_CASAS12 = ".HHHH..HHHH."       # manzana de casas (bloques del medio)
_EDIF12 = ".XXXXXXXXXX."        # edificio comercial
_EDIF14 = ".XXXXXXXXXXXX."      # edificio grande del oeste
_BALDIO12 = "," * 12            # baldío (pasto dentro de la ciudad)

# Bandas de manzanas: [P]ar de casas, fila con [T]rees, [W]alkway
_P1 = _CASAS14 + _C2 + _CASAS12 + _C2 + _CASAS12 + _C2   # casas x3
_P2 = _CASAS14 + _C2 + _BALDIO12 + _C2 + _EDIF12 + _C2   # casas/baldío/edificio
_P2T = "." * 14 + _C2 + ",,,,AA,,,,,," + _C2 + _EDIF12 + _C2
_W2 = "." * 14 + _C2 + _BALDIO12 + _C2 + "." * 12 + _C2
_P3 = _EDIF14 + _C2 + _CASAS12 + _C2 + _CASAS12 + _C2    # edificio/casas/casas
_W3 = _EDIF14 + _C2 + "." * 12 + _C2 + "." * 12 + _C2
_P4 = _CASAS14 + _C2 + _EDIF12 + _C2 + _BALDIO12 + _C2   # casas/edificio/baldío sur
_P4T = _CASAS14 + _C2 + _EDIF12 + _C2 + ",,,AA,,,,,,," + _C2
_W4 = "." * 14 + _C2 + _EDIF12 + _C2 + _BALDIO12 + _C2
_W4B = "." * 14 + _C2 + "." * 12 + _C2 + _BALDIO12 + _C2
_TIENDA44 = "." * 19 + "TT" + "." * 23                   # almacén sobre la calle

# El local de Walter (cols 1-14) + calle + parque del norte (cols 17-44)
_PARQUE28 = "," * 28


def _local(interior, parque=_PARQUE28):
    return interior + _C2 + parque


# --- Campo y costanera (columnas 46 a 74, 29 caracteres) ---
# El arroyo (ww) baja de norte a sur por las columnas 66-67; se
# cruza por los puentes (~~) de las filas 22-23 y la avenida sur.
# Del otro lado queda la Costanera (columnas 68-74).
_CAMPO29 = "," * 20 + "ww" + "," * 7
_CAMPO_A1 = ",,,,AA,,,,,,,,,,,,,," + "ww" + ",,AA,,,"     # filas 2-3
_CAMPO_COSTA = "," * 20 + "ww" + ",,,AA,,"                # filas 8-9
_CAMPO_A2 = ",,,AA,,,,,,,,,,,,,,," + "ww" + "," * 7       # fila 15
_CAMPO_PUENTE = ",,,,,,,,AA,,,,,,,,,," + "~~" + "," * 7   # filas 22-23
_CAMPO_A4 = ",,,,,AA,,,,,,,,,,,,," + "ww" + "," * 7       # fila 37


def _fila(ciudad, divisor="X", campo=_CAMPO29):
    """Arma una fila del norte: borde + ciudad(44) + muro/portón +
    campo y costanera(29) + borde. El assert evita colisiones corridas."""
    fila = "X" + ciudad + divisor + campo + "X"
    assert len(fila) == 76, f"Fila de {len(fila)} caracteres (≠76): {fila!r}"
    return fila


# --- Distrito Sur (filas 44-56, contenido de 74 columnas) ---
# Avenida que rodea el muro, kioscos de servicios (Banco, Clínica,
# segundo almacén), galpones industriales y el puerto junto al arroyo.
_SUR_AVENIDA = "." * 65 + "~~" + "." * 7                  # cruza el arroyo
_SUR_KIOSCOS = (".BB" + "." * 10 + "SS" + "." * 9 + "TT" + "." * 4
                + "." * 4 + "," * 31 + "ww" + "," * 7)
_SUR_CALLE = "." * 34 + "," * 31 + "ww" + "," * 7
_SUR_GALPONES = (".XXXXXXXX..XXXXXXXX..XXXXXXXX." + "." * 4
                 + "," * 31 + "ww" + "," * 7)
_SUR_PRADERA = "," * 65 + "ww" + "," * 7


def _fila_sur(contenido):
    fila = "X" + contenido + "X"
    assert len(fila) == 76, f"Fila sur de {len(fila)} caracteres (≠76)"
    return fila


MAPA = [
    "X" * 76,
    # --- Local de Walter (filas 1-8) y parque del norte ---
    _fila(_local("XXXXXXXXXXXXXX")),
    _fila(_local("XpCCppppppFppX", ",,,AA,,,,,,,,,,,,,,AA,,,,,,,"),
          campo=_CAMPO_A1),
    _fila(_local("XppppppppppppX"), campo=_CAMPO_A1),
    _fila(_local("XpMMMMMMMMpppX")),
    _fila(_local("XppppppppppppX")),
    _fila(_local("XppppppppppppX", ",,,,,,,,AA,,,,,,,,,,,,,,,,,,")),
    _fila(_local("XppppppppppppX")),
    _fila(_local("XXXXppXXXXXXXX"), campo=_CAMPO_COSTA),   # puerta en (5-6, 8)
    # --- Avenida norte (filas 9-10) ---
    _fila(_CALLE44, campo=_CAMPO_COSTA),
    _fila(_CALLE44),
    # --- Manzanas residenciales (filas 11-16), portón en 14-16 ---
    _fila(_P1),
    _fila(_P1),
    _fila(_CALLE44),
    _fila(_P1, divisor="~"),
    _fila(_P1, divisor="~", campo=_CAMPO_A2),
    _fila(_CALLE44, divisor="~"),
    # --- Calle (filas 17-18) ---
    _fila(_CALLE44),
    _fila(_CALLE44),
    # --- Baldío del mercado + edificio (filas 19-24) ---
    _fila(_P2),
    _fila(_P2),
    _fila(_P2T),
    _fila(_P2, campo=_CAMPO_PUENTE),
    _fila(_P2, campo=_CAMPO_PUENTE),
    _fila(_W2),
    # --- Calle con el almacén (filas 25-26) ---
    _fila(_CALLE44),
    _fila(_TIENDA44),
    # --- Edificio oeste + casas (filas 27-32), portón en 30-32 ---
    _fila(_P3),
    _fila(_P3),
    _fila(_W3),
    _fila(_P3, divisor="~"),
    _fila(_P3, divisor="~"),
    _fila(_CALLE44, divisor="~"),
    # --- Calle (filas 33-34) ---
    _fila(_CALLE44),
    _fila(_CALLE44),
    # --- Casas + edificio + baldío sur (filas 35-40) ---
    _fila(_P4),
    _fila(_P4),
    _fila(_W4, campo=_CAMPO_A4),
    _fila(_P4T),
    _fila(_P4),
    _fila(_W4B),
    # --- Terminal vieja (filas 41-43) ---
    _fila(_CALLE44),
    _fila(_CALLE44),
    _fila(_CALLE44),
    # --- Distrito Sur (filas 44-56) ---
    _fila_sur(_SUR_AVENIDA),     # la avenida rodea el muro del campo
    _fila_sur(_SUR_AVENIDA),
    _fila_sur(_SUR_KIOSCOS),     # Banco (2-3), Clínica (14-15), almacén (25-26)
    _fila_sur(_SUR_CALLE),
    _fila_sur(_SUR_GALPONES),
    _fila_sur(_SUR_GALPONES),
    _fila_sur(_SUR_GALPONES),
    _fila_sur(_SUR_GALPONES),
    _fila_sur(_SUR_GALPONES),
    _fila_sur(_SUR_CALLE),
    _fila_sur(_SUR_CALLE),
    _fila_sur(_SUR_PRADERA),
    _fila_sur(_SUR_PRADERA),
    "X" * 76,
]

TILES_SOLIDOS = ("X", "H", "A", "C", "T", "M", "F", "w", "B", "S")

# --- Puntos de referencia del local (en píxeles de mundo) ---
PUNTO_PUERTA = (5.5 * TILE, 8.5 * TILE)       # vano de la puerta
PUNTO_ENTREGA = (4.6 * TILE, 9.4 * TILE)      # donde caen las cajas (vereda)
POSICIONES_FILA = [                            # la fila frente al mostrador
    (4.6 * TILE, 5.2 * TILE),
    (4.6 * TILE, 6.0 * TILE),
    (4.6 * TILE, 6.8 * TILE),
    (5.0 * TILE, 7.5 * TILE),
    (5.8 * TILE, 7.7 * TILE),
]
LUGARES_COMER = [                              # dónde se paran a comer
    (9.4 * TILE, 5.3 * TILE),
    (10.7 * TILE, 5.7 * TILE),
    (11.9 * TILE, 5.2 * TILE),
    (9.7 * TILE, 6.7 * TILE),
    (11.3 * TILE, 6.9 * TILE),
]
ENTRADAS_CLIENTES = [                          # por dónde llegan caminando
    (2.0 * TILE, 9.6 * TILE),
    (11.5 * TILE, 9.6 * TILE),
]


class Mapa:
    """Carga la grilla, genera los rects de colisión y se dibuja
    en pantalla aplicando el offset de la cámara."""

    def __init__(self):
        # Validación: todas las filas deben medir lo mismo,
        # si no las colisiones quedan corridas.
        anchos = {len(fila) for fila in MAPA}
        assert len(anchos) == 1, f"Filas del mapa con anchos distintos: {anchos}"

        self.filas = len(MAPA)
        self.columnas = len(MAPA[0])
        self.ancho_px = self.columnas * TILE
        self.alto_px = self.filas * TILE

        self.paredes = []
        # Tiles interactuables (main.py chequea proximidad + tecla E)
        self.tiles_cocina = []
        self.tiles_tienda = []
        self.tiles_mostrador = []
        self.tiles_telefono = []
        self.tiles_banco = []
        self.tiles_hospital = []

        for fila, linea in enumerate(MAPA):
            for col, tile in enumerate(linea):
                if tile not in TILES_SOLIDOS:
                    continue
                rect = pygame.Rect(col * TILE, fila * TILE, TILE, TILE)
                self.paredes.append(rect)
                if tile == "C":
                    self.tiles_cocina.append(rect)
                elif tile == "T":
                    self.tiles_tienda.append(rect)
                elif tile == "M":
                    self.tiles_mostrador.append(rect)
                elif tile == "F":
                    self.tiles_telefono.append(rect)
                elif tile == "B":
                    self.tiles_banco.append(rect)
                elif tile == "S":
                    self.tiles_hospital.append(rect)

    def es_solido_en(self, x, y):
        """True si el punto (px de mundo) cae sobre un tile sólido.
        Consulta O(1) contra la grilla: la usan las líneas de visión
        de los enemigos y las balas, que chequean muchos puntos por
        frame (recorrer self.paredes sería carísimo)."""
        col = int(x) // TILE
        fila = int(y) // TILE
        if not (0 <= fila < self.filas and 0 <= col < self.columnas):
            return True  # fuera del mapa cuenta como pared
        return MAPA[fila][col] in TILES_SOLIDOS

    def paredes_cerca(self, rect, margen=2):
        """Rects sólidos en un entorno de `margen` tiles alrededor del
        rect. Con el mapa grande conviene chequear colisiones contra
        esta lista corta y no contra las ~800 paredes totales."""
        col_min = max(0, rect.left // TILE - margen)
        col_max = min(self.columnas - 1, rect.right // TILE + margen)
        fila_min = max(0, rect.top // TILE - margen)
        fila_max = min(self.filas - 1, rect.bottom // TILE + margen)
        cercanas = []
        for fila in range(fila_min, fila_max + 1):
            for col in range(col_min, col_max + 1):
                if MAPA[fila][col] in TILES_SOLIDOS:
                    cercanas.append(pygame.Rect(col * TILE, fila * TILE, TILE, TILE))
        return cercanas

    def dibujar(self, superficie, camara):
        """Dibuja solo los tiles visibles en pantalla (culling)."""
        col_inicio = max(0, int(camara.offset.x) // TILE)
        col_fin = min(self.columnas, (int(camara.offset.x) + superficie.get_width()) // TILE + 2)
        fila_inicio = max(0, int(camara.offset.y) // TILE)
        fila_fin = min(self.filas, (int(camara.offset.y) + superficie.get_height()) // TILE + 2)

        for fila in range(fila_inicio, fila_fin):
            for col in range(col_inicio, col_fin):
                tile = MAPA[fila][col]
                rect = camara.aplicar(pygame.Rect(col * TILE, fila * TILE, TILE, TILE))
                self._dibujar_tile(superficie, tile, rect)

    def _dibujar_tile(self, superficie, tile, rect):
        """Dibuja un tile con detalles simples para dar textura pixel art."""
        if tile == "X":
            pygame.draw.rect(superficie, COLOR_EDIFICIO, rect)
            pygame.draw.rect(superficie, COLOR_EDIFICIO_TOP,
                             (rect.x, rect.y, rect.width, 6))
        elif tile == "H":
            # Casa: pared beige con techo de tejas y ventanita
            pygame.draw.rect(superficie, COLOR_CASA, rect)
            pygame.draw.rect(superficie, COLOR_CASA_TECHO,
                             (rect.x, rect.y, rect.width, 10))
            pygame.draw.rect(superficie, COLOR_EDIFICIO_TOP,
                             (rect.x + 11, rect.y + 17, 10, 8))
        elif tile == "A":
            pygame.draw.rect(superficie, COLOR_PASTO, rect)
            pygame.draw.rect(superficie, COLOR_ARBOL, rect.inflate(-6, -6))
            pygame.draw.rect(superficie, COLOR_ARBOL_LUZ,
                             (rect.x + 8, rect.y + 8, 8, 8))
        elif tile == "C":
            # Cocina del local: acero con hornallas calientes
            pygame.draw.rect(superficie, COLOR_PISO_LOCAL, rect)
            pygame.draw.rect(superficie, COLOR_COCINA, rect.inflate(-4, -4))
            pygame.draw.rect(superficie, COLOR_COCINA_TOP,
                             (rect.x + 4, rect.y + 4, rect.width - 8, 9))
        elif tile == "M":
            # Mostrador: madera con tapa clara
            pygame.draw.rect(superficie, COLOR_PISO_LOCAL, rect)
            pygame.draw.rect(superficie, COLOR_MOSTRADOR,
                             (rect.x, rect.y + 6, rect.width, rect.height - 6))
            pygame.draw.rect(superficie, COLOR_MOSTRADOR_TOP,
                             (rect.x, rect.y, rect.width, 8))
        elif tile == "F":
            # Teléfono/computadora de pedidos: pantalla encendida
            pygame.draw.rect(superficie, COLOR_PISO_LOCAL, rect)
            pygame.draw.rect(superficie, COLOR_TELEFONO, rect.inflate(-8, -8))
            pygame.draw.rect(superficie, COLOR_TELEFONO_LUZ,
                             (rect.x + 12, rect.y + 12, 8, 6))
        elif tile == "T":
            # Almacén del barrio con toldo rojo
            pygame.draw.rect(superficie, COLOR_CALLE, rect)
            pygame.draw.rect(superficie, COLOR_TIENDA, rect.inflate(-4, -4))
            pygame.draw.rect(superficie, COLOR_TIENDA_TOLDO,
                             (rect.x + 2, rect.y + 2, rect.width - 4, 9))
        elif tile == "B":
            # Banco: piedra con franja dorada
            pygame.draw.rect(superficie, COLOR_CALLE, rect)
            pygame.draw.rect(superficie, COLOR_BANCO, rect.inflate(-4, -4))
            pygame.draw.rect(superficie, COLOR_BANCO_FRANJA,
                             (rect.x + 2, rect.y + 10, rect.width - 4, 6))
        elif tile == "S":
            # Clínica: blanca con cruz roja
            pygame.draw.rect(superficie, COLOR_CALLE, rect)
            pygame.draw.rect(superficie, COLOR_HOSPITAL, rect.inflate(-4, -4))
            pygame.draw.rect(superficie, COLOR_HOSPITAL_CRUZ,
                             (rect.centerx - 2, rect.y + 7, 4, 18))
            pygame.draw.rect(superficie, COLOR_HOSPITAL_CRUZ,
                             (rect.x + 9, rect.centery - 2, 14, 4))
        elif tile == "w":
            # Arroyo: agua con reflejos desfasados
            pygame.draw.rect(superficie, COLOR_AGUA, rect)
            if (rect.x // TILE + rect.y // TILE) % 2 == 0:
                pygame.draw.rect(superficie, COLOR_AGUA_LUZ,
                                 (rect.x + 6, rect.y + 14, 12, 3))
        elif tile == "p":
            # Piso de madera del local
            pygame.draw.rect(superficie, COLOR_PISO_LOCAL, rect)
            if (rect.x // TILE) % 2 == 0:
                pygame.draw.rect(superficie, COLOR_PISO_LINEA,
                                 (rect.x, rect.y, 2, rect.height))
        elif tile == ",":
            pygame.draw.rect(superficie, COLOR_PASTO, rect)
            if (rect.x // TILE + rect.y // TILE) % 3 == 0:
                pygame.draw.rect(superficie, COLOR_PASTO_DET,
                                 (rect.x + 12, rect.y + 14, 4, 4))
        elif tile == "~":
            pygame.draw.rect(superficie, COLOR_TIERRA, rect)
        else:  # "." calle
            pygame.draw.rect(superficie, COLOR_CALLE, rect)
            if (rect.x // TILE) % 4 == 0:
                pygame.draw.rect(superficie, COLOR_CALLE_LINEA,
                                 (rect.x, rect.y, 2, rect.height))
