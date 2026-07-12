# Genera una plantilla PSD con la grilla 4x4 para los sprites del
# personaje top-down: 14 celdas a completar + guías + etiquetas.
# Uso: python tools/generar_psd_personaje.py [tamano_celda]
#   tamano_celda: 64 (default, imagen 256x256) o 128 (imagen 512x512)

import sys

import numpy as np
import pytoshop
from pytoshop import layers
from pytoshop.enums import ColorMode, Compression

CELDA = int(sys.argv[1]) if len(sys.argv) > 1 else 64
COLS, FILAS = 4, 4
ANCHO, ALTO = CELDA * COLS, CELDA * FILAS

# Fila -> (nombre, cantidad de frames usados)
FILAS_INFO = [
    ("abajo", 3),
    ("arriba", 3),
    ("izquierda", 4),
    ("derecha", 4),
]
NOMBRES_FRAME = ["quieto", "paso1", "paso2", "paso3"]


def capa_guia():
    """Capa de fondo con las líneas de grilla + marcas de celdas
    vacías, semitransparente para poder dibujar encima."""
    px = np.zeros((ALTO, ANCHO, 4), dtype=np.uint8)
    LINEA = (255, 60, 200, 130)
    VACIA = (255, 60, 60, 60)

    for c in range(COLS + 1):
        x = min(c * CELDA, ANCHO - 1)
        px[:, x] = LINEA
    for f in range(FILAS + 1):
        y = min(f * CELDA, ALTO - 1)
        px[y, :] = LINEA

    for fi, (_, usados) in enumerate(FILAS_INFO):
        for c in range(usados, COLS):
            y0, y1 = fi * CELDA, (fi + 1) * CELDA
            x0, x1 = c * CELDA, (c + 1) * CELDA
            px[y0:y1, x0:x1] = VACIA

    return px


def canal(img, idx):
    return layers.ChannelImageData(image=img[:, :, idx], compression=Compression.raw)


def main():
    psd = pytoshop.core.PsdFile(num_channels=4, height=ALTO, width=ANCHO,
                                color_mode=ColorMode.rgb)

    lista_capas = []

    # Capas vacías (arriba del todo = última en la lista para pytoshop,
    # que ordena de abajo hacia arriba), una por sprite a completar.
    vacio = np.zeros((CELDA, CELDA, 4), dtype=np.uint8)
    for fi, (nombre_dir, usados) in enumerate(FILAS_INFO):
        for c in range(usados):
            nombre_frame = NOMBRES_FRAME[c]
            top, left = fi * CELDA, c * CELDA
            capa = layers.LayerRecord(
                channels={0: canal(vacio, 0), 1: canal(vacio, 1),
                         2: canal(vacio, 2), -1: canal(vacio, 3)},
                top=top, left=left, bottom=top + CELDA, right=left + CELDA,
                name=f"{nombre_dir}_{nombre_frame}",
                opacity=255, blend_mode=b"norm",
            )
            lista_capas.append(capa)

    # Capa guía al fondo (se puede ocultar/borrar antes de exportar)
    guia_img = capa_guia()
    capa_guia_layer = layers.LayerRecord(
        channels={0: canal(guia_img, 0), 1: canal(guia_img, 1),
                 2: canal(guia_img, 2), -1: canal(guia_img, 3)},
        top=0, left=0, bottom=ALTO, right=ANCHO,
        name="GUIA_grilla (ocultar/borrar antes de exportar)",
        opacity=255, blend_mode=b"norm",
    )
    lista_capas.append(capa_guia_layer)
    lista_capas.reverse()  # pytoshop: primera capa = la de más abajo

    psd.layer_and_mask_info.layer_info.layer_records = lista_capas

    salida = f"assets/sprites/plantilla_personaje_{ANCHO}x{ALTO}.psd"
    with open(salida, "wb") as f:
        psd.write(f)
    print(f"OK -> {salida}  ({ANCHO}x{ALTO}, celda {CELDA}px, "
          f"{len(lista_capas) - 1} capas de sprite + 1 guía)")


if __name__ == "__main__":
    main()
