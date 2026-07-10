# =========================================================
# FAST EMPIRE — Audio sintetizado  [Fase 8]
#
# Todos los sonidos y la música se generan por código al
# arrancar (ondas seno/cuadradas y ruido en 16-bit mono):
# no hay archivos en /assets todavía. Si el mixer no puede
# inicializarse, el juego sigue andando en silencio.
#
# main.py llama a reproducir("nombre") en cada evento del
# juego, y las Opciones controlan volumen y música.
# =========================================================

import math
import random
import struct

import pygame

FRECUENCIA = 22050  # Hz, mono, 16 bits (ver pre_init en main.py)


def _muestras_a_sonido(muestras):
    """Convierte una lista de floats [-1, 1] en un Sound."""
    datos = bytearray()
    for muestra in muestras:
        valor = int(max(-1.0, min(1.0, muestra)) * 32000)
        datos += struct.pack("<h", valor)
    return pygame.mixer.Sound(buffer=bytes(datos))


def _tono(freq, dur, volumen=0.5, forma="seno", decae=True):
    total = int(FRECUENCIA * dur)
    muestras = []
    for i in range(total):
        t = i / FRECUENCIA
        fase = math.sin(2 * math.pi * freq * t)
        if forma == "cuadrada":
            fase = 1.0 if fase >= 0 else -1.0
        envolvente = (1 - i / total) if decae else 1.0
        muestras.append(fase * volumen * envolvente)
    return muestras


def _ruido(dur, volumen=0.5):
    total = int(FRECUENCIA * dur)
    return [random.uniform(-1, 1) * volumen * (1 - i / total)
            for i in range(total)]


def _secuencia(*partes):
    muestras = []
    for parte in partes:
        muestras.extend(parte)
    return muestras


class Audio:
    # Volumen propio de cada efecto (se multiplica por el general)
    BASE = {
        "click": 0.7, "hablar": 0.5, "venta": 0.8, "cocinado": 0.8,
        "disparo": 0.6, "golpe": 0.7, "dano": 0.7, "caida": 0.9,
        "pedido": 0.8, "sirena": 0.8, "mudanza": 0.7, "error": 0.6,
    }

    def __init__(self):
        self.activo = pygame.mixer.get_init() is not None
        self.volumen = 0.8       # general (Opciones: pasos de 20%)
        self.musica_on = True
        self.sfx = {}
        self.musica = None
        if not self.activo:
            return
        try:
            self._generar_sfx()
            self._generar_musica()
        except pygame.error:
            self.activo = False

    # --- Generación ---
    def _generar_sfx(self):
        self.sfx = {
            "click": _muestras_a_sonido(_tono(880, 0.05, 0.4, "cuadrada")),
            "hablar": _muestras_a_sonido(_tono(440, 0.04, 0.4)),
            "venta": _muestras_a_sonido(_secuencia(
                _tono(660, 0.07, 0.5), _tono(990, 0.10, 0.5))),
            "cocinado": _muestras_a_sonido(_secuencia(
                _tono(1175, 0.09, 0.5), _tono(1568, 0.16, 0.5))),
            "disparo": _muestras_a_sonido(_ruido(0.09, 0.8)),
            "golpe": _muestras_a_sonido(_tono(120, 0.07, 0.8, "cuadrada")),
            "dano": _muestras_a_sonido(_tono(196, 0.12, 0.7, "cuadrada")),
            "caida": _muestras_a_sonido(_secuencia(
                _tono(392, 0.16, 0.6), _tono(294, 0.16, 0.6),
                _tono(196, 0.30, 0.6))),
            "pedido": _muestras_a_sonido(_secuencia(
                _tono(784, 0.14, 0.5), _tono(659, 0.20, 0.5))),
            "sirena": _muestras_a_sonido(_secuencia(
                _tono(700, 0.14, 0.5), _tono(500, 0.14, 0.5),
                _tono(700, 0.14, 0.5), _tono(500, 0.14, 0.5))),
            "mudanza": _muestras_a_sonido(_secuencia(
                _tono(523, 0.10, 0.5), _tono(415, 0.18, 0.5))),
            "error": _muestras_a_sonido(_tono(175, 0.10, 0.5, "cuadrada")),
        }

    def _generar_musica(self):
        """Loop ambiente o carga de música personalizada."""
        import os
        ruta = os.path.join("assets", "music", "Neon Driftline.mp3")
        if os.path.exists(ruta):
            try:
                pygame.mixer.music.load(ruta)
                class _MusicaWrapper:
                    def set_volume(self, vol):
                        pygame.mixer.music.set_volume(vol)
                    def play(self, loops=-1):
                        pygame.mixer.music.play(loops=loops)
                    def stop(self):
                        pygame.mixer.music.stop()
                self.musica = _MusicaWrapper()
                return
            except pygame.error as e:
                print("Error al cargar mp3:", e)
        
        progresion = [110.0, 87.31, 130.81, 98.0]  # A2, F2, C3, G2
        dur_acorde = 4.0
        muestras = []
        for freq in progresion:
            total = int(FRECUENCIA * dur_acorde)
            for i in range(total):
                t = i / FRECUENCIA
                onda = (0.6 * math.sin(2 * math.pi * freq * t)
                        + 0.25 * math.sin(2 * math.pi * freq * 1.5 * t))
                # Fundido en los bordes del acorde para que no haga clic
                borde = min(i, total - i) / (FRECUENCIA * 0.08)
                muestras.append(onda * 0.5 * min(1.0, borde))
        self.musica = _muestras_a_sonido(muestras)

    # --- Reproducción ---
    def reproducir(self, nombre):
        if self.activo and nombre in self.sfx:
            sonido = self.sfx[nombre]
            sonido.set_volume(self.volumen * self.BASE[nombre])
            sonido.play()

    def iniciar_musica(self):
        if self.activo and self.musica is not None and self.musica_on:
            self.musica.set_volume(self.volumen * 0.30)
            self.musica.play(loops=-1)

    def ciclar_volumen(self):
        """0% → 20% → ... → 100% → 0% (para el menú de Opciones)."""
        self.volumen = round((self.volumen + 0.2) % 1.2, 1)
        if self.volumen > 1.0:
            self.volumen = 0.0
        if self.activo and self.musica is not None:
            self.musica.set_volume(self.volumen * 0.30 if self.musica_on else 0)
        self.reproducir("click")

    def alternar_musica(self):
        self.musica_on = not self.musica_on
        if not self.activo or self.musica is None:
            return
        if self.musica_on:
            self.iniciar_musica()
        else:
            self.musica.stop()
