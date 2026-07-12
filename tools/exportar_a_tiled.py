# =========================================================
# FAST EMPIRE — Exportador one-shot ASCII → Tiled
#
# Genera, a partir de la vieja grilla ASCII de src/map.py:
#   assets/map/tileset.png  la imagen del tileset (tiles 32x32,
#                           renderizados con el MISMO código de
#                           dibujado procedural del juego)
#   assets/map/tileset.tsx  el tileset de Tiled con las propiedades
#                           personalizadas de cada tile:
#                             solido (bool), tipo (string), char (string)
#   assets/map/ciudad.tmx   el mapa completo: la capa de tiles
#                           "suelo" (la ciudad + el sótano, idénticos
#                           al ASCII) y la capa de objetos "objetos"
#                           con las zonas de venta y los puntos fijos
#                           que hoy viven hardcodeados en el código.
#
# USO:  python tools/exportar_a_tiled.py
#       python tools/exportar_a_tiled.py --solo-tileset
#
# ¡Correr UNA sola vez sin flags! Después de ese export, ciudad.tmx
# se edita a mano en Tiled y pasa a ser la única fuente de verdad
# del mapa. Re-correr el script completo PISA los tres archivos y
# borra cualquier edición hecha en Tiled.
#
# --solo-tileset regenera SOLO tileset.png y tileset.tsx (ciudad.tmx
# no se toca): es la forma segura de sumar tiles nuevos al final del
# CATALOGO — los ids existentes no cambian, así que el .tmx editado
# en Tiled sigue siendo válido.
# =========================================================

import os
import sys
from pathlib import Path
from xml.sax.saxutils import quoteattr

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

# Sin ventana: el driver dummy alcanza para renderizar Surfaces
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((64, 64))

from src.settings import TILE  # noqa: E402
from src.map import (  # noqa: E402
    MAPA, TILES_SOLIDOS, COL_CONCESIONARIA,
    _CONCES_EXHIBICION, _CONCES_PUERTA, _DibujanteAscii,
    PUNTO_PUERTA, PUNTO_ENTREGA, PUNTO_SOTANO, PUNTO_TRAMPILLA,
    PUNTO_CONCESIONARIA, POSICIONES_FILA, LUGARES_COMER,
    ENTRADAS_CLIENTES,
)
from src.economy import LUGARES_VENTA  # noqa: E402

DESTINO = RAIZ / "assets" / "map"
COLUMNAS_TS = 8          # tiles por fila en la imagen del tileset

# La propiedad "tipo" de cada char interactuable (debe coincidir con
# listas_por_tipo en src/map.py → Mapa.__init__)
TIPOS = {
    "C": "cocina", "T": "tienda", "M": "mostrador", "F": "telefono",
    "B": "banco", "S": "hospital", "D": "sotano", "U": "subida",
    "m": "maceta", "b": "mesa", "l": "laboratorio", "e": "estante",
    "V": "concesionaria", "Q": "muebleria",
}

# Catálogo del tileset: (nombre, char, vx, vy, rel_conces)
#  - vx/vy: posición (en tiles) del rect al renderizar. El dibujado
#    procedural elige detalles según la posición (la línea de la
#    calle cada 4 columnas, el reflejo del agua alternado, etc.),
#    así que cada VARIANTE se hornea como un tile distinto.
#  - rel_conces: para "V", la columna relativa dentro de la fachada
#    de la concesionaria (elige puerta / vitrina / vehículo).
CATALOGO = [
    ("calle",           ".", 1, 0, None),
    ("calle_linea",     ".", 0, 0, None),   # col % 4 == 0
    ("pasto",           ",", 1, 0, None),
    ("pasto_detalle",   ",", 0, 0, None),   # (col+fila) % 3 == 0
    ("tierra",          "~", 0, 0, None),
    ("agua",            "w", 1, 0, None),
    ("agua_luz",        "w", 0, 0, None),   # (col+fila) % 2 == 0
    ("piso_local",      "p", 1, 0, None),
    ("piso_linea",      "p", 0, 0, None),   # col % 2 == 0
    ("edificio",        "X", 0, 0, None),
    ("casa",            "H", 0, 0, None),
    ("arbol",           "A", 0, 0, None),
    ("kiosco",          "k", 0, 0, None),
    ("cocina",          "C", 0, 0, None),
    ("mostrador",       "M", 0, 0, None),
    ("telefono",        "F", 0, 0, None),
    ("trampilla",       "D", 0, 0, None),
    ("almacen",         "T", 0, 0, None),
    ("banco",           "B", 0, 0, None),
    ("clinica",         "S", 0, 0, None),
    ("vacio",           "N", 0, 0, None),
    ("sotano_piso",     "s", 0, 0, None),
    ("escalera",        "U", 0, 0, None),
    ("maceta",          "m", 0, 0, None),
    ("mesa_armado",     "b", 0, 0, None),
    ("laboratorio",     "l", 0, 0, None),
    ("estante",         "e", 0, 0, None),
    ("conces_vitrina",   "V", 0, 0, 0),
    ("conces_moto",      "V", 0, 0, 1),
    ("conces_puerta",    "V", 0, 0, _CONCES_PUERTA),
    ("conces_auto",      "V", 0, 0, 4),
    ("conces_camioneta", "V", 0, 0, 6),
    # --- Tiles nuevos (solo del tileset: se pintan a mano en Tiled).
    # SIEMPRE agregar al FINAL: los ids existentes no deben moverse.
    ("cristal",          "G", 0, 0, None),
    ("techo_tejas",      "t", 0, 0, None),
    ("techo_chapa",      "c", 0, 0, None),
    ("techo_cristal",    "g", 0, 0, None),
    ("muebleria",        "Q", 0, 0, None),
]

ID = {nombre: i for i, (nombre, *_resto) in enumerate(CATALOGO)}
# char → nombre base (para los chars sin variantes)
NOMBRE_POR_CHAR = {}
for _nombre, _char, *_r in CATALOGO:
    NOMBRE_POR_CHAR.setdefault(_char, _nombre)

_VEHICULO_POR_REL = {v: f"conces_{v}" for v in ("moto", "auto", "camioneta")}


def gid_para(char, col, fila):
    """El gid (id de tileset + 1) que corresponde a una celda del
    ASCII, replicando las fórmulas de variantes del dibujado viejo
    pero ancladas a la posición de MUNDO (quedan estables; antes se
    calculaban sobre coordenadas de pantalla y se corrían con la
    cámara)."""
    if char == ".":
        nombre = "calle_linea" if col % 4 == 0 else "calle"
    elif char == ",":
        nombre = "pasto_detalle" if (col + fila) % 3 == 0 else "pasto"
    elif char == "w":
        nombre = "agua_luz" if (col + fila) % 2 == 0 else "agua"
    elif char == "p":
        nombre = "piso_linea" if col % 2 == 0 else "piso_local"
    elif char == "V":
        rel = col - COL_CONCESIONARIA
        if rel == _CONCES_PUERTA:
            nombre = "conces_puerta"
        else:
            tipo = _CONCES_EXHIBICION.get(rel)
            nombre = _VEHICULO_POR_REL.get(tipo, "conces_vitrina")
    else:
        nombre = NOMBRE_POR_CHAR[char]
    return ID[nombre] + 1


def generar_tileset_png():
    filas_ts = -(-len(CATALOGO) // COLUMNAS_TS)   # ceil
    tileset = pygame.Surface((COLUMNAS_TS * TILE, filas_ts * TILE))
    dibujante = _DibujanteAscii()
    scratch = pygame.Surface((4 * TILE, 4 * TILE))
    for i, (nombre, char, vx, vy, rel) in enumerate(CATALOGO):
        scratch.fill((0, 0, 0))
        rect = pygame.Rect(vx * TILE, vy * TILE, TILE, TILE)
        col_arg = COL_CONCESIONARIA + rel if rel is not None else 0
        dibujante._dibujar_tile(scratch, char, rect, col_arg)
        destino = ((i % COLUMNAS_TS) * TILE, (i // COLUMNAS_TS) * TILE)
        tileset.blit(scratch, destino, rect)
    ruta = DESTINO / "tileset.png"
    pygame.image.save(tileset, str(ruta))
    print(f"OK  {ruta}  ({tileset.get_width()}x{tileset.get_height()} px, "
          f"{len(CATALOGO)} tiles)")
    return tileset.get_size()


def generar_tsx(tam_imagen):
    lineas = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<tileset version="1.10" tiledversion="1.11.2" name="fast_empire" '
        f'tilewidth="{TILE}" tileheight="{TILE}" '
        f'tilecount="{len(CATALOGO)}" columns="{COLUMNAS_TS}">',
        f' <image source="tileset.png" width="{tam_imagen[0]}" '
        f'height="{tam_imagen[1]}"/>',
    ]
    for i, (nombre, char, _vx, _vy, _rel) in enumerate(CATALOGO):
        solido = "true" if char in TILES_SOLIDOS else "false"
        lineas.append(f' <tile id="{i}">')
        lineas.append('  <properties>')
        lineas.append(f'   <property name="char" value={quoteattr(char)}/>')
        lineas.append(f'   <property name="nombre" value={quoteattr(nombre)}/>')
        lineas.append(f'   <property name="solido" type="bool" value="{solido}"/>')
        tipo = TIPOS.get(char)
        if tipo:
            lineas.append(f'   <property name="tipo" value={quoteattr(tipo)}/>')
        lineas.append('  </properties>')
        lineas.append(' </tile>')
    lineas.append('</tileset>')
    ruta = DESTINO / "tileset.tsx"
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"OK  {ruta}  ({len(CATALOGO)} tiles con propiedades)")


def _objetos():
    """La capa de objetos: todo lo que hoy está hardcodeado en el
    código pasa a vivir en el .tmx (zonas de venta, puntos fijos).
    El código Python los leerá por nombre/tipo en los Pasos 3 y 4."""
    objs = []
    oid = 1

    def rect_obj(nombre, tipo, x, y, w, h):
        nonlocal oid
        objs.append(f'  <object id="{oid}" name={quoteattr(nombre)} '
                    f'type={quoteattr(tipo)} x="{x}" y="{y}" '
                    f'width="{w}" height="{h}"/>')
        oid += 1

    def punto_obj(nombre, tipo, pos, props=None):
        nonlocal oid
        x = round(pos[0], 2)
        y = round(pos[1], 2)
        cuerpo = ""
        if props:
            cuerpo = "<properties>" + "".join(
                f'<property name={quoteattr(k)} type="int" value="{v}"/>'
                for k, v in props.items()) + "</properties>"
        objs.append(f'  <object id="{oid}" name={quoteattr(nombre)} '
                    f'type={quoteattr(tipo)} x="{x}" y="{y}">'
                    f'{cuerpo}<point/></object>')
        oid += 1

    # Zonas de venta (rects en tiles → px). El orden importa: la Red
    # de ventas usa el índice como zona_id, así que llevan "orden".
    for idx, (nombre, (col, fila, ancho, alto)) in enumerate(LUGARES_VENTA):
        objs.append(f'  <object id="{oid}" name={quoteattr(nombre)} '
                    f'type="ZonaVenta" x="{col * TILE}" y="{fila * TILE}" '
                    f'width="{ancho * TILE}" height="{alto * TILE}">'
                    f'<properties><property name="orden" type="int" '
                    f'value="{idx}"/></properties></object>')
        oid += 1

    # Puntos fijos del local / sótano / concesionaria
    punto_obj("PuntoPuerta", "Punto", PUNTO_PUERTA)
    punto_obj("PuntoEntrega", "Punto", PUNTO_ENTREGA)
    punto_obj("PuntoSotano", "Punto", PUNTO_SOTANO)
    punto_obj("PuntoTrampilla", "Punto", PUNTO_TRAMPILLA)
    punto_obj("PuntoConcesionaria", "Punto", PUNTO_CONCESIONARIA)
    for i, pos in enumerate(POSICIONES_FILA):
        punto_obj(f"Fila_{i}", "PosicionFila", pos, {"orden": i})
    for i, pos in enumerate(LUGARES_COMER):
        punto_obj(f"LugarComer_{i}", "LugarComer", pos)
    for i, pos in enumerate(ENTRADAS_CLIENTES):
        punto_obj(f"EntradaCliente_{i}", "EntradaCliente", pos)
    return objs, oid


def generar_tmx():
    columnas = len(MAPA[0])
    filas = len(MAPA)
    # La capa "suelo": el ASCII completo, celda por celda, como CSV
    filas_csv = []
    for f in range(filas):
        filas_csv.append(",".join(
            str(gid_para(MAPA[f][c], c, f)) for c in range(columnas)))
    csv = ",\n".join(filas_csv)

    # La capa "techos" nace vacía: se pinta a mano en Tiled. El motor
    # dibuja toda capa de tiles != "suelo" por encima de las entidades
    # y la atenúa cuando tapa al jugador (Mapa.dibujar_techos).
    csv_techos = ",\n".join(",".join("0" for _ in range(columnas))
                            for _ in range(filas))
    objetos, prox_oid = _objetos()
    lineas = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<map version="1.10" tiledversion="1.11.2" orientation="orthogonal" '
        f'renderorder="right-down" width="{columnas}" height="{filas}" '
        f'tilewidth="{TILE}" tileheight="{TILE}" infinite="0" '
        f'nextlayerid="4" nextobjectid="{prox_oid}">',
        ' <tileset firstgid="1" source="tileset.tsx"/>',
        f' <layer id="1" name="suelo" width="{columnas}" height="{filas}">',
        '  <data encoding="csv">',
        csv,
        '  </data>',
        ' </layer>',
        f' <layer id="3" name="techos" width="{columnas}" height="{filas}">',
        '  <data encoding="csv">',
        csv_techos,
        '  </data>',
        ' </layer>',
        ' <objectgroup id="2" name="objetos">',
        *objetos,
        ' </objectgroup>',
        '</map>',
    ]
    ruta = DESTINO / "ciudad.tmx"
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"OK  {ruta}  ({columnas}x{filas} tiles, "
          f"{len(objetos)} objetos)")


if __name__ == "__main__":
    DESTINO.mkdir(parents=True, exist_ok=True)
    tam = generar_tileset_png()
    generar_tsx(tam)
    if "--solo-tileset" in sys.argv:
        print("\nListo (solo tileset). ciudad.tmx quedó como estaba.")
    else:
        generar_tmx()
        print("\nListo. Abrí assets/map/ciudad.tmx en Tiled Map Editor.")
