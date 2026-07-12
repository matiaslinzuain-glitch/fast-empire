# =========================================================
# FAST EMPIRE — Mapa y colisiones  [Fase 12: Tiled]
# El mapa ahora se carga desde Tiled (assets/map/ciudad.tmx,
# vía pytmx). Qué es sólido y qué es interactuable sale de las
# propiedades personalizadas del tileset (solido, tipo, char):
# nada de eso queda hardcodeado en el código.
#
# La vieja grilla ASCII de 120x118 sigue acá abajo como LEGACY:
# la usan tools/exportar_a_tiled.py (para regenerar el tileset)
# y el minimapa de ui.py (hasta el Paso 5 de la migración).
# Cuando ambos migren, todo el bloque ASCII se borra y el .tmx
# queda como única fuente de verdad.
#
# Leyenda (de la grilla legacy):
#   X = edificio / pared (sólido)
#   H = casa con techo de tejas (sólida)
#   A = árbol (sólido)
#   k = kiosco de feria (sólido)
#   C = cocina de Walter (sólida, interactuable con E)
#   M = mostrador del local (sólido; se atiende desde atrás con E)
#   F = teléfono del local (sólido, interactuable: abre el celular)
#   T = almacén (sólido, interactuable: armas/curas)
#   D = trampilla del local (sólida, interactuable: TELETRANSPORTA
#       al sótano — una habitación real bajo la ciudad)
#   B = banco  ·  S = clínica  ·  w = agua
#   --- el sótano (filas 100-117, instancia aislada) ---
#   N = vacío del subsuelo (negro sólido, rodea al cuarto)
#   s = piso del sótano (transitable)
#   U = escalera de subida (sólida, interactuable: vuelve al local)
#   m = maceta  ·  b = mesa de armado  ·  l = laboratorio
#   e = estante (todos sólidos, interactuables por proximidad)
#   p = piso de madera del local (transitable)
#   . = calle de asfalto (transitable)
#   , = pasto (transitable)
#   ~ = camino de tierra / puente (transitable)
#   --- tiles SOLO del tileset (no aparecen en la grilla ASCII:
#       se pintan a mano en Tiled) ---
#   G = pared de cristal (sólida)
#   Q = mueblería (sólida, interactuable: comprar macetas y
#       mesas de laboratorio)
#   t = techo de tejas · c = techo de chapa · g = techo de
#       cristal (los tres para la capa "techos": se dibujan por
#       encima y se atenúan cuando tapan al jugador)
# =========================================================

from pathlib import Path

import pygame

from .settings import (
    TILE, TECHO_ALPHA_OCULTO, TECHO_VEL_FADE,
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
    COLOR_FERIA,
)

ANCHO_MAPA = 120   # tiles
FILAS_CIUDAD = 100     # la ciudad ocupa las filas 0-99
ALTO_MAPA = 118        # + 18 filas de subsuelo (el sótano y su vacío)

# --- Piezas de la ciudad original (columnas 1 a 44 de cada fila) ---
_C2 = ".."                      # calle vertical de 2 tiles
_CALLE44 = "." * 44             # calle horizontal completa
_CASAS14 = ".HHHH...HHHH.."     # manzana de casas (bloque oeste)
_CASAS12 = ".HHHH..HHHH."       # manzana de casas (bloques del medio)
_EDIF12 = ".XXXXXXXXXX."        # edificio comercial
_EDIF14 = ".XXXXXXXXXXXX."      # edificio grande del oeste
_BALDIO12 = "," * 12            # baldío (pasto dentro de la ciudad)

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
# El arroyo (ww) baja por las columnas 66-67; se cruza por los
# puentes (~~). El campo ahora tiene granjas, un granero y una
# huerta para que no sea puro pasto.
_CAMPO29 = "," * 20 + "ww" + "," * 7
_CAMPO_A1 = ",,,,AA,,,,,,,,,,,,,," + "ww" + ",,AA,,,"     # filas 2-3
_CAMPO_GRANJA = ",,,,,,,,HHH,,,,,,,,," + "ww" + ",,AA,,,"  # filas 5-6
_CAMPO_COSTA = "," * 20 + "ww" + ",,,AA,,"                # filas 8-9
_CAMPO_A2 = ",,,AA,,,,,,,,,,,,,,," + "ww" + "," * 7       # fila 15
_CAMPO_PUENTE = ",,,,,,,,AA,,,,,,,,,," + "~~" + "," * 7   # filas 22-23
_CAMPO_GRANERO = ",,,,,,,,,XXX,,,,,,,," + "ww" + "," * 7  # filas 35-36
_CAMPO_A4 = ",,,,,AA,,,,,,,,,,,,," + "ww" + "," * 7       # fila 37
_CAMPO_HUERTA = ",,AA,,AA,,AA,,,,,,,," + "ww" + "," * 7   # filas 39-40

for _pieza in (_CAMPO29, _CAMPO_A1, _CAMPO_GRANJA, _CAMPO_COSTA, _CAMPO_A2,
               _CAMPO_PUENTE, _CAMPO_GRANERO, _CAMPO_A4, _CAMPO_HUERTA):
    assert len(_pieza) == 29, f"Pieza de campo de {len(_pieza)} (≠29)"


def _fila(ciudad, divisor="X", campo=_CAMPO29):
    """Fila de la ciudad original: borde + ciudad(44) + muro/portón +
    campo(29). El borde este de la fila lo agrega el Barrio Este."""
    fila = "X" + ciudad + divisor + campo
    assert len(fila) == 75, f"Fila de {len(fila)} caracteres (≠75): {fila!r}"
    return fila


# --- Distrito Sur original (filas 44-56, contenido de 74 columnas) ---
_SUR_AVENIDA = "." * 65 + "~~" + "." * 7                  # cruza el arroyo
_SUR_KIOSCOS = (".BB" + "." * 10 + "SS" + "." * 9 + "TT" + "." * 4
                + "." * 4 + "," * 31 + "ww" + "," * 7)
_SUR_CALLE = "." * 34 + "," * 31 + "ww" + "," * 7
_SUR_GALPONES = (".XXXXXXXX..XXXXXXXX..XXXXXXXX." + "." * 4
                 + "," * 31 + "ww" + "," * 7)
_SUR_PRADERA = "," * 65 + "ww" + "," * 7


def _fila_sur(contenido):
    fila = "X" + contenido
    assert len(fila) == 75, f"Fila sur de {len(fila)} caracteres (≠75)"
    return fila


# La ciudad original, SIN el borde este (75 columnas): el Barrio
# Este se pega a la derecha de cada fila.
_MAPA_OESTE = [
    "X" * 75,
    # --- Local de Walter (filas 1-8) y parque del norte ---
    _fila(_local("XXXXXXXXXXXXXX")),
    _fila(_local("XpCCppppppFppX", ",,,AA,,,,,,,,,,,,,,AA,,,,,,,"),
          campo=_CAMPO_A1),
    _fila(_local("XppppppppppppX"), campo=_CAMPO_A1),
    _fila(_local("XpMMMMMMMMpppX")),
    _fila(_local("XppppppppppppX"), campo=_CAMPO_GRANJA),
    _fila(_local("XppppppppppppX", ",,,,,,,,AA,,,,,,,,,,,,,,,,,,"),
          campo=_CAMPO_GRANJA),
    _fila(_local("XDpppppppppppX")),                       # D: sótano
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
    _fila(_P4, campo=_CAMPO_GRANERO),
    _fila(_P4, campo=_CAMPO_GRANERO),
    _fila(_W4, campo=_CAMPO_A4),
    _fila(_P4T),
    _fila(_P4, campo=_CAMPO_HUERTA),
    _fila(_W4B, campo=_CAMPO_HUERTA),
    # --- Terminal vieja (filas 41-43) ---
    _fila(_CALLE44),
    _fila(_CALLE44),
    _fila(_CALLE44),
    # --- Distrito Sur (filas 44-56) ---
    _fila_sur(_SUR_AVENIDA),
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
]
assert len(_MAPA_OESTE) == 57  # filas 0-56; la 57 es el empalme con el sur


# --- Barrio Este (columnas 75-119, 45 caracteres por fila) ---
# Calles verticales en 75-76, 89-90, 103-104 y 117-118; tres
# bloques de 12 en el medio; borde en la 119.
_B_CASAS = ".HHHH.HHHH.."
_B_EDIF = ".XXXXXXXXXX."
_B_PLAZA = "," * 12
_B_PLAZA_A = ",,AA,,,,AA,,"
_B_CALLE = "." * 12
for _pieza in (_B_CASAS, _B_EDIF, _B_PLAZA, _B_PLAZA_A, _B_CALLE):
    assert len(_pieza) == 12


def _este(b1, b2, b3):
    fila = ".." + b1 + ".." + b2 + ".." + b3 + "..X"
    assert len(fila) == 45
    return fila


_E_CALLE = "." * 44 + "X"
_E_ALMACEN = _este(".TT.........", _B_CALLE, _B_CALLE)  # almacén en (78-79)

# Fila (1-56) → contenido del Barrio Este
_ESTE = {}
for _f in (3, 6, 9, 10, 13, 16, 17, 18, 21, 24, 25, 29, 32, 33, 34,
           37, 40, 41, 42, 43, 44, 45, 48, 51, 54, 55, 56):
    _ESTE[_f] = _E_CALLE
_ESTE[26] = _E_ALMACEN
for _f in (1, 2):
    _ESTE[_f] = _este(_B_CASAS, _B_CASAS, _B_EDIF)
for _f in (4, 5):
    _ESTE[_f] = _este(_B_EDIF, _B_PLAZA, _B_CASAS)      # Plaza Este
for _f in (7, 8):
    _ESTE[_f] = _este(_B_CASAS, _B_PLAZA, _B_EDIF)      # Plaza Este
for _f in (11, 12):
    _ESTE[_f] = _este(_B_EDIF, _B_CASAS, _B_CASAS)
for _f in (14, 15):
    _ESTE[_f] = _este(_B_CASAS, _B_EDIF, _B_CASAS)
for _f in (19, 20):
    _ESTE[_f] = _este(_B_EDIF, _B_EDIF, _B_EDIF)
for _f in (22, 23):
    _ESTE[_f] = _este(_B_EDIF, _B_PLAZA, _B_EDIF)       # Galería Muerta
for _f in (27, 28):
    _ESTE[_f] = _este(_B_CASAS, _B_EDIF, _B_CASAS)
for _f in (30, 31):
    _ESTE[_f] = _este(_B_EDIF, _B_CASAS, _B_EDIF)
for _f in (35, 36):
    _ESTE[_f] = _este(_B_CASAS, _B_CASAS, _B_PLAZA_A)
for _f in (38, 39):
    _ESTE[_f] = _este(_B_EDIF, _B_CASAS, _B_CASAS)
for _f in (46, 47):
    _ESTE[_f] = _este(_B_EDIF, _B_EDIF, _B_CASAS)
for _f in (49, 50):
    _ESTE[_f] = _este(_B_CASAS, _B_EDIF, _B_EDIF)
for _f in (52, 53):
    _ESTE[_f] = _este(_B_EDIF, _B_CASAS, _B_CASAS)


# --- Zona Sur Nueva (filas 57-99, 120 columnas) ---
def _fila_ancha(contenido):
    """Borde + 118 columnas de contenido + borde."""
    fila = "X" + contenido + "X"
    assert len(fila) == 120, f"Fila ancha de {len(fila)} (≠120)"
    return fila


def _empalme():
    """Fila 57: el viejo muro sur, ahora con portones hacia la zona
    nueva (y el arroyo que sigue de largo)."""
    fila = list("X" * 120)
    aberturas = [(10, 16, "."), (30, 36, "."), (50, 56, ","),
                 (66, 68, "w"), (75, 77, "."), (89, 91, "."), (103, 105, ".")]
    for desde, hasta, tile in aberturas:
        for col in range(desde, hasta):
            fila[col] = tile
    return "".join(fila)


# Piezas del sur (oeste 65 cols / arroyo 2 / este 51 cols)
_S_AVENIDA = "." * 65 + "~~" + "." * 51          # avenida con puente
_S_CALLE_W = "." * 65 + "ww" + "." * 51          # calle cortada por el arroyo
_S_FERIA = ".kk." * 10 + "." * 25 + "ww" + ".HHH." * 10 + "."
_S_FERIA_P = "." * 40 + "." * 25 + "ww" + "." * 51           # pasillo feria
_S_INDUS = ".XXXXXXXX." * 5 + ",,XXXXXXXXXXX,," + "ww" + ".XXXXXX..." * 5 + "."
_S_INDUS_C = "." * 50 + "," * 15 + "ww" + "." * 51           # calle interna
_S_PLAYON = (".XXXXXXXX." + "." * 30 + ".XXXXXXXX."          # Playón Industrial
             + "," * 15 + "ww" + ".HHH." * 10 + ".")
# La fila de abajo del galpón este del Playón es la CONCESIONARIA:
# fachada con toldo azul, puerta y tres vehículos en vitrina (V)
_S_PLAYON_CONCES = (".XXXXXXXX." + "." * 30 + ".VVVVVVVV."
                    + "," * 15 + "ww" + ".HHH." * 10 + ".")
_S_BAJO = ".HHH." * 13 + "ww" + ".HHH." * 10 + "."
_S_BAJO_CALLE = "." * 65 + "ww" + "." * 51
_S_BAJO_POCKET = (".HHH." * 13 + "ww"                        # Callejón del Bajo
                  + ".HHH." * 4 + "." * 11 + ".HHH." * 4)
_S_DEPOSITOS = ".XXXXXXXX." * 5 + "." * 15 + "ww" + ".XXXXXX..." * 5 + "."
_S_MUELLE = "." * 65 + "ww" + "." * 51
_S_AGUA = "w" * 118

for _pieza in (_S_AVENIDA, _S_CALLE_W, _S_FERIA, _S_FERIA_P, _S_INDUS,
               _S_INDUS_C, _S_PLAYON, _S_PLAYON_CONCES, _S_BAJO,
               _S_BAJO_CALLE, _S_BAJO_POCKET, _S_DEPOSITOS, _S_MUELLE,
               _S_AGUA):
    assert len(_pieza) == 118, f"Pieza sur de {len(_pieza)} (≠118)"

_SUR_NUEVO = (
    [_empalme()]                                  # fila 57
    + [_fila_ancha(_S_AVENIDA)] * 2               # 58-59 avenida
    + [_fila_ancha(_S_FERIA)] * 2                 # 60-61 feria + barrio este
    + [_fila_ancha(_S_FERIA_P)]                   # 62 pasillo
    + [_fila_ancha(_S_FERIA)] * 2                 # 63-64
    + [_fila_ancha(_S_CALLE_W)]                   # 65 calle
    + [_fila_ancha(_S_INDUS)] * 4                 # 66-69 galpones
    + [_fila_ancha(_S_INDUS_C)]                   # 70 calle interna
    + [_fila_ancha(_S_PLAYON)] * 3                # 71-73 Playón Industrial
    + [_fila_ancha(_S_PLAYON_CONCES)]             # 74 concesionaria
    + [_fila_ancha(_S_AVENIDA)] * 2               # 75-76 avenida
    + [_fila_ancha(_S_BAJO)] * 2                  # 77-78 barrio bajo
    + [_fila_ancha(_S_BAJO_CALLE)]                # 79
    + [_fila_ancha(_S_BAJO_POCKET)] * 2           # 80-81 callejón
    + [_fila_ancha(_S_BAJO_CALLE)]                # 82
    + [_fila_ancha(_S_BAJO_POCKET)] * 2           # 83-84
    + [_fila_ancha(_S_BAJO_CALLE)]                # 85
    + [_fila_ancha(_S_BAJO)] * 2                  # 86-87
    + [_fila_ancha(_S_AVENIDA)] * 2               # 88-89 avenida del puerto
    + [_fila_ancha(_S_DEPOSITOS)] * 3             # 90-92 depósitos
    + [_fila_ancha(_S_MUELLE)]                    # 93 calle del muelle
    + [_fila_ancha(_S_MUELLE)] * 2                # 94-95 muelle
    + [_fila_ancha(_S_AGUA)] * 3                  # 96-98 el mar
    + ["X" * 120]                                 # 99 borde
)
assert len(_SUR_NUEVO) == 43  # filas 57-99

MAPA = [_MAPA_OESTE[f] + _ESTE.get(f, "X" * 45) for f in range(57)] + _SUR_NUEVO

# --- El sótano (filas 100-117): una INSTANCIA aislada ---
# No es un menú: es un cuarto real en el subsuelo del mapa. Todo lo
# que lo rodea es vacío negro sólido (tile N) y hay filas de colchón
# arriba y abajo para que la cámara — que en el subsuelo usa SUS
# propios límites (ver camera.py) — jamás alcance a mostrar la
# ciudad. La trampilla del local (D) y la escalera de acá (U) se
# teletransportan mutuamente (main.py mueve las coordenadas del
# jugador: misma grilla, instancia visualmente separada).
_SOTANO_INTERIOR = [
    "NNNNNNNNNNNN",
    "NUssssssssmN",     # U: escalera de subida · m: maceta
    "NssssssssssN",
    "NbsssssssslN",     # b: mesa de armado · l: laboratorio
    "NssssssssssN",
    "NsssseessssN",     # e: el estante de guardado
    "NNNNNNNNNNNN",
]
_COL_SOTANO = 2         # esquina izquierda del cuarto
_FILA_SOTANO = 105      # fila del techo del cuarto (5 de colchón)
_VACIO = "N" * ANCHO_MAPA
MAPA.extend([_VACIO] * (_FILA_SOTANO - FILAS_CIUDAD))
for _linea in _SOTANO_INTERIOR:
    MAPA.append("N" * _COL_SOTANO + _linea
                + "N" * (ANCHO_MAPA - _COL_SOTANO - len(_linea)))
MAPA.extend([_VACIO] * (ALTO_MAPA - len(MAPA)))

assert len(MAPA) == ALTO_MAPA
assert {len(f) for f in MAPA} == {ANCHO_MAPA}, "Filas con anchos distintos"

TILES_SOLIDOS = ("X", "H", "A", "C", "T", "M", "F", "w", "B", "S", "k",
                 "D", "N", "U", "m", "b", "l", "e", "V", "G", "Q")

# --- Concesionaria del Playón (fachada V en la fila 74) ---
# Columna donde arranca la fachada y qué muestra cada tile:
# vitrinas con los tres modelos y la puerta de entrada.
COL_CONCESIONARIA = 42
_CONCES_EXHIBICION = {1: "moto", 4: "auto", 6: "camioneta"}  # col relativa
_CONCES_PUERTA = 3
# Donde te espera el vehículo recién comprado (frente a la puerta)
PUNTO_CONCESIONARIA = ((COL_CONCESIONARIA + _CONCES_PUERTA + 0.5) * TILE,
                       75.6 * TILE)

# Frontera vertical ciudad/subsuelo (para la cámara por zonas)
Y_SUBSUELO = FILAS_CIUDAD * TILE

# Puntos del teletransporte local ↔ sótano (píxeles de mundo):
# al bajar aparecés al lado de la escalera; al subir, junto a la
# trampilla del local
PUNTO_SOTANO = (4.3 * TILE, (_FILA_SOTANO + 1.2) * TILE)
PUNTO_TRAMPILLA = (3.2 * TILE, 6.8 * TILE)

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
# El contenedor de ingredientes del Chef: piso libre a la derecha
# del bloque de cocina (que en el .tmx ocupa las cols 2-3 de la
# fila 1 — OJO: no coincide con la grilla ASCII legacy). No es un
# tile del mapa ni tiene colisión: solo un punto de interacción.
PUNTO_CONTENEDOR = (6, 1)                      # (col, fila)
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


# Ruta por defecto del mapa exportado por Tiled
RUTA_MAPA_TMX = Path(__file__).resolve().parent.parent / "assets" / "map" / "ciudad.tmx"


class Mapa:
    """Mapa cargado desde Tiled (.tmx vía pytmx).

    La geometría vive en la capa de tiles "suelo". Las colisiones y
    los interactuables NO están hardcodeados: cada tile del tileset
    trae propiedades personalizadas —
      solido (bool)  → genera rect de colisión,
      tipo (string)  → a qué lista de interactuables va (cocina,
                       banco, concesionaria, ...),
      char (string)  → el carácter ASCII original (minimapa/debug).
    """

    def __init__(self, ruta=None):
        # Import diferido: pytmx convierte las imágenes al formato
        # del display, así que solo puede cargarse con la ventana ya
        # creada (main.py llama _crear_ventana() antes de Mapa()).
        from pytmx.util_pygame import load_pygame

        self.tmx = load_pygame(str(ruta or RUTA_MAPA_TMX))
        if self.tmx.tilewidth != TILE or self.tmx.tileheight != TILE:
            raise ValueError(
                f"El .tmx usa tiles de {self.tmx.tilewidth}px "
                f"y el juego espera {TILE}px")
        self.columnas = self.tmx.width
        self.filas = self.tmx.height
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
        self.tiles_sotano = []       # la trampilla del local (D)
        # Props físicos del sótano (interactuables por proximidad)
        self.tiles_subida = []       # la escalera de vuelta (U)
        self.tiles_maceta = []
        self.tiles_mesa = []
        self.tiles_laboratorio = []
        self.tiles_estante = []
        self.tiles_concesionaria = []  # la fachada con vitrina (V)
        self.tiles_muebleria = []      # la tienda de muebles (Q)

        # Propiedad "tipo" del tileset → lista de interactuables
        listas_por_tipo = {
            "cocina": self.tiles_cocina,
            "tienda": self.tiles_tienda,
            "mostrador": self.tiles_mostrador,
            "telefono": self.tiles_telefono,
            "banco": self.tiles_banco,
            "hospital": self.tiles_hospital,
            "sotano": self.tiles_sotano,
            "subida": self.tiles_subida,
            "maceta": self.tiles_maceta,
            "mesa": self.tiles_mesa,
            "laboratorio": self.tiles_laboratorio,
            "estante": self.tiles_estante,
            "concesionaria": self.tiles_concesionaria,
            "muebleria": self.tiles_muebleria,
        }

        # Grillas derivadas para consultas O(1) por celda
        self._solido = [[False] * self.columnas for _ in range(self.filas)]
        self._imagen = [[None] * self.columnas for _ in range(self.filas)]
        chars = [["."] * self.columnas for _ in range(self.filas)]
        # char → primera imagen vista con ese char (para reemplazar
        # un prop por piso cuando se convierte en mueble colocable)
        self._imagen_por_char = {}

        capa = self.tmx.get_layer_by_name("suelo")
        props_por_gid = {}
        for col, fila, gid in capa:
            if not gid:
                continue
            imagen = self.tmx.get_tile_image_by_gid(gid)
            self._imagen[fila][col] = imagen
            props = props_por_gid.get(gid)
            if props is None:
                props = self.tmx.get_tile_properties_by_gid(gid) or {}
                props_por_gid[gid] = props
            chars[fila][col] = props.get("char", ".")
            self._imagen_por_char.setdefault(props.get("char", "."), imagen)
            if not props.get("solido"):
                continue
            self._solido[fila][col] = True
            rect = pygame.Rect(col * TILE, fila * TILE, TILE, TILE)
            self.paredes.append(rect)
            lista = listas_por_tipo.get(props.get("tipo"))
            if lista is not None:
                lista.append(rect)

        # Espejo ASCII de la grilla (mismo formato que el viejo MAPA;
        # lo usa el minimapa y sirve para debuggear)
        self.chars = ["".join(fila) for fila in chars]

        # --- Capas "por encima" (techos, copas, toldos) ---
        # Cualquier capa de TILES del .tmx que no sea "suelo" se
        # dibuja DESPUÉS de las entidades (ver dibujar_techos). Cada
        # capa es un dict {(col, fila): imagen} solo con sus celdas
        # pintadas. Las capas ocultadas en Tiled (ojito) se ignoran.
        self.capas_techo = []
        for otra in self.tmx.visible_layers:
            if otra.name == "suelo" or not hasattr(otra, "data"):
                continue  # el suelo ya está cargado; los objetos no van
            celdas = {}
            for col, fila, gid in otra:
                if gid:
                    celdas[(col, fila)] = self.tmx.get_tile_image_by_gid(gid)
            if celdas:
                self.capas_techo.append(celdas)
        # Estado del fundido de los techos (255 = opacidad plena)
        self._alpha_techos = 255.0
        self._techos_scratch = None
        self._techos_tick = None

    def reemplazar_por_piso(self, col, fila, char_piso="s"):
        """Cambia la IMAGEN de una celda por la del piso indicado
        (por defecto el del sótano). La usan las estaciones pintadas
        en el .tmx (maceta / laboratorio) al convertirse en muebles
        colocables: el mueble se dibuja aparte sobre este piso. La
        solidez no se toca acá (el mueble la conserva hasta que lo
        levantan con fijar_solido)."""
        img = self._imagen_por_char.get(char_piso)
        if img is not None and 0 <= fila < self.filas \
                and 0 <= col < self.columnas:
            self._imagen[fila][col] = img

    def fijar_solido(self, col, fila, solido):
        """Prende/apaga la solidez de una celda en runtime: lo usan
        los muebles colocables (maceta / mesa de laboratorio). Toca
        solo la grilla _solido — colisiones, pathfinding y líneas de
        visión consultan ahí."""
        if 0 <= fila < self.filas and 0 <= col < self.columnas:
            self._solido[fila][col] = solido

    def es_solido_en(self, x, y):
        """True si el punto (px de mundo) cae sobre un tile sólido.
        Consulta O(1) contra la grilla: la usan las líneas de visión
        de los enemigos, las balas y el pathfinding."""
        col = int(x) // TILE
        fila = int(y) // TILE
        if not (0 <= fila < self.filas and 0 <= col < self.columnas):
            return True  # fuera del mapa cuenta como pared
        return self._solido[fila][col]

    def es_solido_tile(self, col, fila):
        """Como es_solido_en pero en coordenadas de tile (pathfinding)."""
        if not (0 <= fila < self.filas and 0 <= col < self.columnas):
            return True
        return self._solido[fila][col]

    def paredes_cerca(self, rect, margen=2):
        """Rects sólidos en un entorno de `margen` tiles alrededor del
        rect. Con el mapa grande conviene chequear colisiones contra
        esta lista corta y no contra las miles de paredes totales."""
        col_min = max(0, rect.left // TILE - margen)
        col_max = min(self.columnas - 1, rect.right // TILE + margen)
        fila_min = max(0, rect.top // TILE - margen)
        fila_max = min(self.filas - 1, rect.bottom // TILE + margen)
        cercanas = []
        for fila in range(fila_min, fila_max + 1):
            for col in range(col_min, col_max + 1):
                if self._solido[fila][col]:
                    cercanas.append(pygame.Rect(col * TILE, fila * TILE, TILE, TILE))
        return cercanas

    def dibujar(self, superficie, camara):
        """Blitea solo los tiles visibles en pantalla (culling)."""
        ox = round(camara.offset.x)
        oy = round(camara.offset.y)
        col_inicio = max(0, ox // TILE)
        col_fin = min(self.columnas,
                      (ox + superficie.get_width()) // TILE + 2)
        fila_inicio = max(0, oy // TILE)
        fila_fin = min(self.filas,
                       (oy + superficie.get_height()) // TILE + 2)

        for fila in range(fila_inicio, fila_fin):
            fila_img = self._imagen[fila]
            y = fila * TILE - oy
            for col in range(col_inicio, col_fin):
                img = fila_img[col]
                if img is not None:
                    superficie.blit(img, (col * TILE - ox, y))

    def hay_techo_sobre(self, rect):
        """True si alguna celda de las capas de techo cubre el rect
        (en px de mundo; sirve para el jugador a pie o al volante)."""
        if not self.capas_techo:
            return False
        col_min = rect.left // TILE
        col_max = rect.right // TILE
        fila_min = rect.top // TILE
        fila_max = rect.bottom // TILE
        for celdas in self.capas_techo:
            for fila in range(fila_min, fila_max + 1):
                for col in range(col_min, col_max + 1):
                    if (col, fila) in celdas:
                        return True
        return False

    def dibujar_techos(self, superficie, camara, rect_jugador):
        """Dibuja las capas de techo POR ENCIMA de las entidades.
        Mientras alguna celda tape al jugador la opacidad baja a
        TECHO_ALPHA_OCULTO con un fundido suave, y vuelve a plena
        al salir. El fundido lleva su propio reloj: no necesita el
        dt del loop principal."""
        if not self.capas_techo:
            return

        ticks = pygame.time.get_ticks()
        dt = (0.0 if self._techos_tick is None
              else min(0.1, (ticks - self._techos_tick) / 1000.0))
        self._techos_tick = ticks
        objetivo = (TECHO_ALPHA_OCULTO if self.hay_techo_sobre(rect_jugador)
                    else 255.0)
        self._alpha_techos += ((objetivo - self._alpha_techos)
                               * min(1.0, TECHO_VEL_FADE * dt))
        alpha = int(self._alpha_techos)

        # Con opacidad plena se blitea directo; atenuado, los tiles
        # van a una superficie intermedia transparente que se pega
        # entera con set_alpha (así el fundido es parejo aunque los
        # tiles se solapen).
        destino = superficie
        if alpha < 254:
            if (self._techos_scratch is None
                    or self._techos_scratch.get_size() != superficie.get_size()):
                self._techos_scratch = pygame.Surface(superficie.get_size(),
                                                      pygame.SRCALPHA)
            destino = self._techos_scratch
            destino.fill((0, 0, 0, 0))

        ox = round(camara.offset.x)
        oy = round(camara.offset.y)
        col_inicio = max(0, ox // TILE)
        col_fin = min(self.columnas,
                      (ox + superficie.get_width()) // TILE + 2)
        fila_inicio = max(0, oy // TILE)
        fila_fin = min(self.filas,
                       (oy + superficie.get_height()) // TILE + 2)
        for celdas in self.capas_techo:
            for fila in range(fila_inicio, fila_fin):
                y = fila * TILE - oy
                for col in range(col_inicio, col_fin):
                    img = celdas.get((col, fila))
                    if img is not None:
                        destino.blit(img, (col * TILE - ox, y))

        if destino is not superficie:
            destino.set_alpha(alpha)
            superficie.blit(destino, (0, 0))


class _DibujanteAscii:
    """LEGACY — el dibujado procedural de la vieja grilla ASCII.
    Ya no se usa en el juego: tools/exportar_a_tiled.py lo invoca
    para renderizar cada tile del tileset.png. Se borra junto con
    la grilla ASCII cuando termine la migración a Tiled."""

    def _dibujar_tile(self, superficie, tile, rect, col=0):
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
        elif tile == "k":
            # Kiosco de la feria: puesto de madera con lona
            pygame.draw.rect(superficie, COLOR_CALLE, rect)
            pygame.draw.rect(superficie, COLOR_FERIA, rect.inflate(-4, -4))
            pygame.draw.rect(superficie, COLOR_TIENDA_TOLDO,
                             (rect.x + 2, rect.y + 2, rect.width - 4, 7))
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
        elif tile == "D":
            # Trampilla del local: madera con escalones hacia abajo
            pygame.draw.rect(superficie, COLOR_PISO_LOCAL, rect)
            pygame.draw.rect(superficie, (52, 40, 30), rect.inflate(-4, -4))
            for i in range(3):
                pygame.draw.rect(superficie, (30, 22, 16),
                                 (rect.x + 6, rect.y + 7 + i * 7,
                                  rect.width - 12, 4))
        elif tile == "N":
            # El vacío del subsuelo: negro sólido, sin detalles
            pygame.draw.rect(superficie, (0, 0, 0), rect)
        elif tile == "s":
            # Piso del sótano: cemento oscuro con juntas
            pygame.draw.rect(superficie, (40, 36, 44), rect)
            pygame.draw.rect(superficie, (33, 30, 37),
                             (rect.x, rect.y, rect.width, 2))
            pygame.draw.rect(superficie, (33, 30, 37),
                             (rect.x, rect.y, 2, rect.height))
        elif tile == "U":
            # Escalera de subida: escalones cada vez más claros
            pygame.draw.rect(superficie, (40, 36, 44), rect)
            for i in range(4):
                gris = 60 + i * 22
                pygame.draw.rect(superficie, (gris, gris - 6, gris - 14),
                                 (rect.x + 3, rect.bottom - 7 - i * 7,
                                  rect.width - 6, 6))
        elif tile == "m":
            # La maceta: terracota con tierra (la planta se dibuja
            # encima desde main.py según el estado del cultivo)
            pygame.draw.rect(superficie, (40, 36, 44), rect)
            pygame.draw.polygon(superficie, (150, 88, 52),
                                [(rect.x + 6, rect.y + 12),
                                 (rect.right - 6, rect.y + 12),
                                 (rect.right - 10, rect.bottom - 4),
                                 (rect.x + 10, rect.bottom - 4)])
            pygame.draw.rect(superficie, (70, 50, 34),
                             (rect.x + 8, rect.y + 12, rect.width - 16, 5))
        elif tile == "b":
            # Mesa de armado: madera con una bolsita arriba
            pygame.draw.rect(superficie, (40, 36, 44), rect)
            pygame.draw.rect(superficie, (110, 78, 48),
                             (rect.x + 2, rect.y + 8, rect.width - 4,
                              rect.height - 12))
            pygame.draw.rect(superficie, (134, 96, 60),
                             (rect.x + 2, rect.y + 8, rect.width - 4, 6))
            pygame.draw.rect(superficie, (190, 200, 210),
                             (rect.x + 8, rect.y + 11, 9, 7))
        elif tile == "l":
            # Laboratorio: mesada metálica con frascos violetas
            pygame.draw.rect(superficie, (40, 36, 44), rect)
            pygame.draw.rect(superficie, (88, 92, 104),
                             (rect.x + 2, rect.y + 10, rect.width - 4,
                              rect.height - 14))
            pygame.draw.rect(superficie, (150, 90, 190),
                             (rect.x + 7, rect.y + 4, 6, 10))
            pygame.draw.rect(superficie, (120, 70, 160),
                             (rect.x + 18, rect.y + 6, 6, 8))
        elif tile == "e":
            # El estante: repisas con cajitas
            pygame.draw.rect(superficie, (40, 36, 44), rect)
            pygame.draw.rect(superficie, (76, 56, 38), rect.inflate(-4, -2))
            for i in range(3):
                y_rep = rect.y + 5 + i * 9
                pygame.draw.rect(superficie, (120, 92, 60),
                                 (rect.x + 4, y_rep, rect.width - 8, 3))
                pygame.draw.rect(superficie, (170, 150, 110),
                                 (rect.x + 7 + (i * 5) % 10, y_rep - 4, 6, 4))
        elif tile == "T":
            # Almacén del barrio con toldo rojo
            pygame.draw.rect(superficie, COLOR_CALLE, rect)
            pygame.draw.rect(superficie, COLOR_TIENDA, rect.inflate(-4, -4))
            pygame.draw.rect(superficie, COLOR_TIENDA_TOLDO,
                             (rect.x + 2, rect.y + 2, rect.width - 4, 9))
        elif tile == "V":
            # Concesionaria: toldo azul a rayas + vitrina con los
            # tres modelos en exhibición y la puerta de entrada
            from .sprites import dibujar_vehiculo
            rel = col - COL_CONCESIONARIA
            pygame.draw.rect(superficie, (60, 62, 70), rect)      # muro
            if rel == _CONCES_PUERTA:
                # Puerta vidriada de entrada
                pygame.draw.rect(superficie, (30, 36, 48),
                                 (rect.x + 6, rect.y + 11,
                                  rect.width - 12, rect.height - 11))
                pygame.draw.rect(superficie, (120, 160, 210),
                                 (rect.x + 8, rect.y + 13,
                                  rect.width - 16, rect.height - 17), 1)
                pygame.draw.rect(superficie, (222, 178, 84),
                                 (rect.x + 21, rect.centery + 4, 3, 5))
            else:
                # Vitrina: vidrio oscuro con reflejo
                pygame.draw.rect(superficie, (22, 30, 44),
                                 (rect.x + 2, rect.y + 11,
                                  rect.width - 4, rect.height - 13))
                pygame.draw.line(superficie, (58, 74, 100),
                                 (rect.x + 4, rect.y + 13),
                                 (rect.x + 12, rect.y + 13))
                tipo = _CONCES_EXHIBICION.get(rel)
                if tipo is not None:
                    dibujar_vehiculo(superficie, tipo, rect.centerx,
                                     rect.bottom - 3, ancho_max=26)
            # Toldo azul con rayas claras (por encima de todo)
            pygame.draw.rect(superficie, (44, 92, 170),
                             (rect.x, rect.y, rect.width, 10))
            for i in range(2):
                pygame.draw.rect(superficie, (150, 185, 230),
                                 (rect.x + 6 + i * 16, rect.y, 6, 10))
        elif tile == "G":
            # Pared de cristal: marco metálico, vidrio celeste con
            # reflejo diagonal y parteluz al medio
            pygame.draw.rect(superficie, (70, 74, 82), rect)
            vidrio = rect.inflate(-6, -6)
            pygame.draw.rect(superficie, (104, 156, 196), vidrio)
            pygame.draw.line(superficie, (160, 205, 238),
                             (vidrio.x + 3, vidrio.y + 10),
                             (vidrio.x + 10, vidrio.y + 3), 2)
            pygame.draw.line(superficie, (140, 190, 226),
                             (vidrio.x + 8, vidrio.bottom - 4),
                             (vidrio.right - 4, vidrio.y + 8), 1)
            pygame.draw.rect(superficie, (70, 74, 82),
                             (rect.centerx - 1, rect.y, 2, rect.height))
        elif tile == "t":
            # Techo de tejas: hileras desfasadas (capa "techos")
            pygame.draw.rect(superficie, COLOR_CASA_TECHO, rect)
            for i in range(4):
                y_h = rect.y + i * 8
                pygame.draw.rect(superficie, (118, 56, 44),
                                 (rect.x, y_h + 6, rect.width, 2))
                for j in range(4):
                    x_t = rect.x + j * 8 + (4 if i % 2 else 0)
                    if x_t + 3 <= rect.right:
                        pygame.draw.rect(superficie, (176, 96, 74),
                                         (x_t, y_h + 1, 3, 2))
        elif tile == "c":
            # Techo de chapa: acanalado gris con costura y remaches
            pygame.draw.rect(superficie, (118, 122, 128), rect)
            for x_c in range(rect.x + 3, rect.right, 6):
                pygame.draw.rect(superficie, (98, 102, 108),
                                 (x_c, rect.y, 2, rect.height))
            pygame.draw.rect(superficie, (88, 92, 98),
                             (rect.x, rect.centery - 1, rect.width, 2))
            for x_c in range(rect.x + 4, rect.right, 12):
                pygame.draw.rect(superficie, (150, 154, 160),
                                 (x_c, rect.centery - 3, 2, 2))
        elif tile == "g":
            # Techo de cristal (invernadero): reja de marcos con
            # paños de vidrio y brillo diagonal
            pygame.draw.rect(superficie, (96, 142, 176), rect)
            pygame.draw.line(superficie, (150, 195, 228),
                             (rect.x + 4, rect.y + 12),
                             (rect.x + 12, rect.y + 4), 2)
            pygame.draw.line(superficie, (135, 182, 218),
                             (rect.x + 14, rect.bottom - 6),
                             (rect.right - 6, rect.y + 14), 1)
            pygame.draw.rect(superficie, (70, 74, 82), rect, 2)
            pygame.draw.rect(superficie, (70, 74, 82),
                             (rect.centerx - 1, rect.y, 2, rect.height))
            pygame.draw.rect(superficie, (70, 74, 82),
                             (rect.x, rect.centery - 1, rect.width, 2))
        elif tile == "Q":
            # Mueblería: toldo verde a rayas y vidriera con una
            # mesita y una maceta en exhibición
            pygame.draw.rect(superficie, COLOR_CALLE, rect)
            pygame.draw.rect(superficie, (96, 78, 58), rect.inflate(-4, -4))
            # Vidriera
            pygame.draw.rect(superficie, (34, 42, 54),
                             (rect.x + 5, rect.y + 13,
                              rect.width - 10, rect.height - 18))
            # La mesita (tapa + patas)
            pygame.draw.rect(superficie, (168, 136, 96),
                             (rect.x + 7, rect.y + 19, 11, 3))
            pygame.draw.rect(superficie, (128, 100, 68),
                             (rect.x + 8, rect.y + 22, 2, 5))
            pygame.draw.rect(superficie, (128, 100, 68),
                             (rect.x + 15, rect.y + 22, 2, 5))
            # La maceta con su plantita
            pygame.draw.polygon(superficie, (150, 88, 52),
                                [(rect.x + 21, rect.y + 21),
                                 (rect.x + 27, rect.y + 21),
                                 (rect.x + 26, rect.y + 26),
                                 (rect.x + 22, rect.y + 26)])
            pygame.draw.rect(superficie, (74, 130, 68),
                             (rect.x + 23, rect.y + 17, 2, 4))
            # Toldo verde con rayas claras
            pygame.draw.rect(superficie, (58, 108, 62),
                             (rect.x, rect.y, rect.width, 10))
            for i in range(2):
                pygame.draw.rect(superficie, (150, 200, 150),
                                 (rect.x + 6 + i * 16, rect.y, 6, 10))
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
            # Agua: arroyo y mar con reflejos desfasados
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
