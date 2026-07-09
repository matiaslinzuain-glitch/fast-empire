# =========================================================
# FAST EMPIRE — Sprites pixel art procedurales  [Fase 8]
#
# Los personajes se dibujan desde plantillas de texto de
# 12x16 "píxeles" (cada letra es un color de la paleta) y se
# escalan x2. Sin archivos externos: cambiar el look de un
# personaje es editar su paleta o la plantilla.
#
# Frames: quieto, paso y paso espejado (la caminata alterna
# ambos). El helper dibujar_personaje() decide solo si la
# entidad está caminando (comparando su posición de mundo
# entre frames) y hacia dónde mira.
# =========================================================

import pygame

# Leyenda de la plantilla: h pelo/gorra · f piel · o ojos ·
# c ropa · m mangas · p pantalón · s zapatos · . transparente
PLANTILLA_QUIETO = [
    "....hhhh....",
    "...hhhhhh...",
    "...hffffh...",
    "...foffof...",
    "...ffffff...",
    "....ffff....",
    "...cccccc...",
    "..cccccccc..",
    ".mccccccccm.",
    ".mccccccccm.",
    "..cccccccc..",
    "...pppppp...",
    "...pp..pp...",
    "...pp..pp...",
    "...ss..ss...",
    "............",
]
PLANTILLA_PASO = PLANTILLA_QUIETO[:11] + [
    "...pppppp...",
    "..pp...pp...",
    ".pp.....pp..",
    ".ss.....ss..",
    "............",
]

ESCALA = 2
ANCHO_SPRITE = 12 * ESCALA   # 24
ALTO_SPRITE = 16 * ESCALA    # 32
MS_POR_PASO = 160            # velocidad de la caminata

COLOR_OJOS = (18, 16, 18)
PIEL = (196, 164, 120)

_cache = {}  # clave de paleta -> (frames, frames_espejados)


def paleta_peaton(color_ropa, pelo=(52, 40, 30)):
    """Paleta estándar de un vecino: solo cambia la ropa."""
    return {
        "h": pelo, "f": PIEL, "o": COLOR_OJOS,
        "c": color_ropa,
        "m": tuple(max(0, c - 25) for c in color_ropa),
        "p": (48, 48, 54), "s": (32, 32, 34),
    }


def paleta_encapuchado(color_abrigo):
    """Capucha y abrigo del mismo color; apenas se ve la cara."""
    paleta = paleta_peaton(color_abrigo, pelo=color_abrigo)
    paleta["p"] = tuple(max(0, c - 12) for c in color_abrigo)
    return paleta


PALETA_WALTER = {
    "h": (170, 170, 172),          # canoso: años de escuela
    "f": PIEL, "o": COLOR_OJOS,
    "c": (120, 40, 40),            # el delantal bordó
    "m": (96, 32, 32),
    "p": (52, 50, 56), "s": (36, 34, 36),
}
PALETA_INSPECTOR = {
    "h": (240, 244, 248),          # gorra sanitaria blanca
    "f": PIEL, "o": COLOR_OJOS,
    "c": (205, 210, 215), "m": (180, 185, 192),
    "p": (120, 124, 130), "s": (60, 62, 66),
}
PALETA_RIVAL = {
    "h": (172, 52, 46),            # bandana roja
    "f": PIEL, "o": COLOR_OJOS,
    "c": (44, 44, 50), "m": (36, 36, 42),
    "p": (38, 38, 42), "s": (28, 28, 30),
}


def _renderizar(plantilla, paleta):
    superficie = pygame.Surface((12, 16), pygame.SRCALPHA)
    for y, fila in enumerate(plantilla):
        for x, letra in enumerate(fila):
            if letra != ".":
                superficie.set_at((x, y), paleta[letra])
    return pygame.transform.scale(superficie, (ANCHO_SPRITE, ALTO_SPRITE))


def _frames(paleta):
    clave = tuple(sorted(paleta.items()))
    if clave not in _cache:
        quieto = _renderizar(PLANTILLA_QUIETO, paleta)
        paso = _renderizar(PLANTILLA_PASO, paleta)
        frames = [quieto, paso, pygame.transform.flip(paso, True, False)]
        espejados = [pygame.transform.flip(f, True, False) for f in frames]
        _cache[clave] = (frames, espejados)
    return _cache[clave]


def dibujar_personaje(superficie, rect_pantalla, paleta, entidad,
                      mirando_izq=None):
    """Dibuja el sprite anclado al pie del hitbox. Detecta solo si la
    entidad caminó desde el último frame (posición de mundo) y, si no
    se lo indican, hacia qué lado mira."""
    centro = entidad.rect.center
    anterior = getattr(entidad, "_sprite_prev", centro)
    entidad._sprite_prev = centro
    caminando = centro != anterior
    if mirando_izq is None:
        if centro[0] != anterior[0]:
            entidad._sprite_izq = centro[0] < anterior[0]
        mirando_izq = getattr(entidad, "_sprite_izq", False)

    frames, espejados = _frames(paleta)
    if caminando:
        frame = 1 + (pygame.time.get_ticks() // MS_POR_PASO) % 2
    else:
        frame = 0
    imagen = (espejados if mirando_izq else frames)[frame]
    superficie.blit(imagen, (rect_pantalla.centerx - ANCHO_SPRITE // 2,
                             rect_pantalla.bottom - ALTO_SPRITE))
