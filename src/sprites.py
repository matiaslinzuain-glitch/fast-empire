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

import math
import os

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


# ---------------------------------------------------------
# Vehículos (Fase 16): sprites top-down estilo GTA 1/2, PNGs
# de alta resolución en assets/. La imagen base mira a la
# DERECHA (ángulo 0 de la física) y se escala al tamaño de
# juego al cargar. Se ven en la vitrina de la concesionaria,
# en el HUD, estacionados y conduciendo (rotados).
# ---------------------------------------------------------
_cache_vehiculos = {}

_ARCHIVOS_VEHICULOS = {
    "moto": "moto.png",
    "auto": "auto.png",
    "camioneta": "pickup.png",
}
# Largo en píxeles de juego (TILE=32): la moto ~1.3 tiles, el
# auto ~2 y la camioneta ~2.5, como los vehículos del GTA 1.
ANCHO_VEHICULO = {"moto": 42, "auto": 68, "camioneta": 80}


def _imagen_vehiculo(tipo):
    """PNG original recortado a su contenido (cacheado). El
    recorte saca el margen transparente del lienzo para que el
    escalado y el centrado trabajen sobre el vehículo real."""
    clave = (tipo, "png")
    if clave not in _cache_vehiculos:
        ruta = os.path.join("assets", "sprites", "movimiento",
                            "vehiculos", _ARCHIVOS_VEHICULOS[tipo])
        img = pygame.image.load(ruta).convert_alpha()
        img = img.subsurface(img.get_bounding_rect()).copy()
        _cache_vehiculos[clave] = img
    return _cache_vehiculos[clave]


def sprite_vehiculo(tipo, ancho_max=None, mirando_izq=False):
    """Superficie del vehículo a tamaño de juego (cacheada).
    `ancho_max` lo achica proporcionalmente (p. ej. para entrar
    en un tile)."""
    clave = (tipo, ancho_max, mirando_izq)
    if clave not in _cache_vehiculos:
        img = _imagen_vehiculo(tipo)
        ancho = ANCHO_VEHICULO[tipo]
        if ancho_max is not None:
            ancho = min(ancho, ancho_max)
        alto = max(1, round(img.get_height() * ancho / img.get_width()))
        s = pygame.transform.smoothscale(img, (ancho, alto))
        if mirando_izq:
            s = pygame.transform.flip(s, True, False)
        _cache_vehiculos[clave] = s
    return _cache_vehiculos[clave]


def hitbox_vehiculo(tipo):
    """Lado de la hitbox cuadrada al conducir. Un rect que no
    rota no puede calzar exacto con la textura en todos los
    ángulos: el promedio entre largo y ancho del sprite la sigue
    de cerca tanto derecho como en diagonal."""
    largo, ancho = sprite_vehiculo(tipo).get_size()
    return (largo + ancho) // 2


def dibujar_vehiculo(superficie, tipo, centro_x, base_y,
                     ancho_max=None, mirando_izq=False):
    """Blitea el vehículo anclado al piso (centro-abajo)."""
    img = sprite_vehiculo(tipo, ancho_max, mirando_izq)
    superficie.blit(img, (centro_x - img.get_width() // 2,
                          base_y - img.get_height()))


# Conduciendo el sprite rota hacia la trompa. La rotación va en
# pasos de 15° (24 direcciones, como los sprites pre-rotados del
# GTA original) así el caché queda chico y el pixel art no "vibra".
GRADOS_POR_PASO = 15


def sprite_vehiculo_conduciendo(tipo, angulo):
    """Sprite rotado hacia `angulo` (radianes de pantalla: 0 =
    derecha, positivo = horario). Cacheado por paso de rotación."""
    paso = round(math.degrees(angulo) / GRADOS_POR_PASO) % (360 // GRADOS_POR_PASO)
    clave = (tipo, "conduciendo", paso)
    if clave not in _cache_vehiculos:
        grados = paso * GRADOS_POR_PASO
        # El sprite top-down rota completo sin espejarse (visto
        # desde arriba no hay "patas arriba", a diferencia del
        # perfil). pygame rota antihorario; el ángulo de pantalla
        # es horario.
        img = sprite_vehiculo(tipo)
        _cache_vehiculos[clave] = pygame.transform.rotate(img, -grados)
    return _cache_vehiculos[clave]


def dibujar_vehiculo_conduciendo(superficie, tipo, centro, angulo):
    """Blitea el vehículo en marcha, centrado en el jugador."""
    img = sprite_vehiculo_conduciendo(tipo, angulo)
    superficie.blit(img, (centro[0] - img.get_width() // 2,
                          centro[1] - img.get_height() // 2))


def dibujar_mueble(superficie, tipo, rect):
    """Una maceta o mesa de laboratorio COLOCADA en el mundo: el
    mismo pixel art de los tiles del sótano pero sin fondo propio
    (se apoya sobre el piso que haya debajo). rect en píxeles de
    pantalla, del tamaño de un tile."""
    if tipo == "maceta":
        # Terracota con tierra (la planta la dibuja main.py encima
        # según el estado del cultivo, igual que en el sótano)
        pygame.draw.polygon(superficie, (150, 88, 52),
                            [(rect.x + 6, rect.y + 12),
                             (rect.right - 6, rect.y + 12),
                             (rect.right - 10, rect.bottom - 4),
                             (rect.x + 10, rect.bottom - 4)])
        pygame.draw.rect(superficie, (70, 50, 34),
                         (rect.x + 8, rect.y + 12, rect.width - 16, 5))
    else:  # mesa_lab
        # Mesada metálica con frascos violetas (como el tile l)
        pygame.draw.rect(superficie, (88, 92, 104),
                         (rect.x + 2, rect.y + 10, rect.width - 4,
                          rect.height - 14))
        pygame.draw.rect(superficie, (150, 90, 190),
                         (rect.x + 7, rect.y + 4, 6, 10))
        pygame.draw.rect(superficie, (120, 70, 160),
                         (rect.x + 18, rect.y + 6, 6, 8))


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
