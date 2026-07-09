# =========================================================
# FAST EMPIRE — Jugador (Walter)  [Fase 3]
# Movimiento con WASD + colisiones, vida, y apuntado con el
# mouse: `direccion_mira` la actualiza main.py cada frame
# (necesita la cámara para pasar el mouse a coordenadas de
# mundo). Apuntar con click derecho frena el paso y achica la
# dispersión de la pistola.
#
# Pendiente para fases futuras: animaciones por sprite (F5) y
# modificadores del árbol de habilidades (F4).
# =========================================================

import pygame

from .settings import (
    VELOCIDAD_JUGADOR, TAM_JUGADOR, VIDA_JUGADOR, FRENO_APUNTADO,
    COLOR_MIRA,
)
from .sprites import PALETA_WALTER, dibujar_personaje


def mover_con_colisiones(pos, rect, direccion, velocidad, dt, paredes):
    """Movimiento con resolución de colisiones eje por eje: al chocar
    se pega al borde del muro, así se puede deslizar contra paredes.
    Modifica `pos` (Vector2, floats) y `rect` (enteros) in place.
    La comparten el jugador y los enemigos."""
    pos.x += direccion.x * velocidad * dt
    rect.x = round(pos.x)
    for pared in paredes:
        if rect.colliderect(pared):
            if direccion.x > 0:    # iba a la derecha
                rect.right = pared.left
            elif direccion.x < 0:  # iba a la izquierda
                rect.left = pared.right
            pos.x = rect.x

    pos.y += direccion.y * velocidad * dt
    rect.y = round(pos.y)
    for pared in paredes:
        if rect.colliderect(pared):
            if direccion.y > 0:    # iba hacia abajo
                rect.bottom = pared.top
            elif direccion.y < 0:  # iba hacia arriba
                rect.top = pared.bottom
            pos.y = rect.y


class Jugador:
    def __init__(self, x, y):
        # Posición en floats para movimiento suave; el rect (enteros)
        # se usa para colisiones y dibujo.
        self.pos = pygame.Vector2(x, y)
        self.rect = pygame.Rect(x, y, *TAM_JUGADOR)
        self.velocidad = VELOCIDAD_JUGADOR
        self.direccion = pygame.Vector2(0, 0)

        # Combate
        self.vida_max = VIDA_JUGADOR
        self.vida = VIDA_JUGADOR
        self.apuntando = False                       # click derecho sostenido
        self.direccion_mira = pygame.Vector2(1, 0)   # hacia el mouse (mundo)
        self.cooldown_disparo = 0.0
        self.cooldown_golpe = 0.0

    def manejar_input(self):
        """Lee WASD y arma el vector de dirección."""
        teclas = pygame.key.get_pressed()
        self.direccion.x = int(teclas[pygame.K_d]) - int(teclas[pygame.K_a])
        self.direccion.y = int(teclas[pygame.K_s]) - int(teclas[pygame.K_w])

        # Normalizar para que en diagonal no se mueva más rápido
        if self.direccion.length_squared() > 0:
            self.direccion = self.direccion.normalize()

    def actualizar(self, dt, paredes):
        """Mueve al jugador y baja los cooldowns. dt en segundos."""
        self.cooldown_disparo = max(0.0, self.cooldown_disparo - dt)
        self.cooldown_golpe = max(0.0, self.cooldown_golpe - dt)

        self.manejar_input()
        velocidad = self.velocidad * (FRENO_APUNTADO if self.apuntando else 1.0)
        mover_con_colisiones(self.pos, self.rect, self.direccion,
                             velocidad, dt, paredes)

    def recibir_dano(self, dano):
        """Devuelve True si Walter murió con este golpe."""
        self.vida -= dano
        return self.vida <= 0

    def reaparecer(self, x, y):
        """Vuelve al punto de partida con la vida completa
        (tras un arresto o una muerte)."""
        self.pos.update(x, y)
        self.rect.topleft = (x, y)
        self.vida = self.vida_max
        self.apuntando = False

    def dibujar(self, superficie, camara):
        """Sprite pixel art de Walter con caminata animada. La línea
        larga es la mira (solo al apuntar); la corta, el brazo/arma."""
        r = camara.aplicar(self.rect)
        centro = pygame.Vector2(r.center)

        if self.apuntando:
            pygame.draw.line(superficie, COLOR_MIRA, centro,
                             centro + self.direccion_mira * 95, 1)

        dibujar_personaje(superficie, r, PALETA_WALTER, self,
                          mirando_izq=self.direccion_mira.x < 0)
        # Brazo/arma hacia donde apunta el mouse
        pygame.draw.line(superficie, (40, 40, 44), centro,
                         centro + self.direccion_mira * 14, 3)
