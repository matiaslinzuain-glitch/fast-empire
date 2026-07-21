# =========================================================
# FAST EMPIRE — Efectos de partículas (juice)
# Polvo liviano para arranques y frenadas. Nada de
# física fina: cada partícula es un puntito que se infla un
# poco, se frena y se desvanece. Se dibujan en el lienzo de
# mundo, así que respetan la cámara (y su temblor).
# =========================================================

import math
import random

import pygame

COLOR_POLVO = (200, 192, 176)   # tierra/asfalto levantado


class Particula:
    __slots__ = ("pos", "vel", "radio", "crece", "vida", "vida_max", "color")

    def __init__(self, x, y, vel, radio, vida, color):
        self.pos = pygame.Vector2(x, y)
        self.vel = vel
        self.radio = radio
        self.crece = radio * 1.4          # radio final
        self.vida = vida
        self.vida_max = vida
        self.color = color

    def actualizar(self, dt):
        self.vida -= dt
        self.pos += self.vel * dt
        self.vel *= 0.86                  # se frena en seco (arrastre)

    def dibujar(self, superficie, camara):
        t = max(0.0, self.vida / self.vida_max)
        ox, oy = camara.desplazamiento()
        radio = self.radio + (self.crece - self.radio) * (1 - t)
        if radio < 0.5:
            return
        x = round(self.pos.x - ox)
        y = round(self.pos.y - oy)
        alfa = int(150 * t)
        d = max(1, round(radio))
        cap = pygame.Surface((d * 2, d * 2), pygame.SRCALPHA)
        pygame.draw.circle(cap, (*self.color, alfa), (d, d), d)
        superficie.blit(cap, (x - d, y - d))


def polvo(lista, x, y, cantidad, fuerza=90, color=COLOR_POLVO, base_dir=None):
    """Suma una tanda de partículas a `lista`. `base_dir` (Vector2)
    sesga la salida hacia atrás del movimiento; sin él, salen radiales."""
    for _ in range(cantidad):
        ang = random.uniform(0, 6.283)
        dir_ = pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
        if base_dir is not None and base_dir.length_squared() > 0:
            dir_ = -base_dir.normalize() + dir_ * 0.6
        else:
            dir_ = pygame.Vector2(math.cos(ang), math.sin(ang))
        if dir_.length_squared() == 0:
            continue
        vel = dir_.normalize() * random.uniform(fuerza * 0.4, fuerza)
        lista.append(Particula(
            x + random.uniform(-6, 6), y + random.uniform(-4, 4),
            vel, random.uniform(2.5, 5.0), random.uniform(0.28, 0.5), color))
