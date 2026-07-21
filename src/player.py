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
    COLOR_MIRA, ACEL_JUGADOR, FRICCION_JUGADOR,
)
from .sprites import PALETA_WALTER, dibujar_personaje


def mover_con_colisiones(pos, rect, direccion, velocidad, dt, paredes):
    """Movimiento con resolución de colisiones eje por eje: al chocar
    se pega al borde del muro, así se puede deslizar contra paredes.
    Modifica `pos` (Vector2, floats) y `rect` (enteros) in place.
    Devuelve (chocó_x, chocó_y) para que quien quiera pueda anular la
    velocidad del eje trabado (evita el 'rebote' al despegarse de la
    pared). La comparten el jugador y los enemigos; los enemigos
    ignoran el valor de retorno."""
    choco_x = choco_y = False
    pos.x += direccion.x * velocidad * dt
    rect.x = round(pos.x)
    for pared in paredes:
        if rect.colliderect(pared):
            if direccion.x > 0:    # iba a la derecha
                rect.right = pared.left
            elif direccion.x < 0:  # iba a la izquierda
                rect.left = pared.right
            pos.x = rect.x
            choco_x = True

    pos.y += direccion.y * velocidad * dt
    rect.y = round(pos.y)
    for pared in paredes:
        if rect.colliderect(pared):
            if direccion.y > 0:    # iba hacia abajo
                rect.bottom = pared.top
            elif direccion.y < 0:  # iba hacia arriba
                rect.top = pared.bottom
            pos.y = rect.y
            choco_y = True
    return choco_x, choco_y


class Jugador:
    def __init__(self, x, y):
        # Posición en floats para movimiento suave; el rect (enteros)
        # se usa para colisiones y dibujo.
        self.pos = pygame.Vector2(x, y)
        self.rect = pygame.Rect(x, y, *TAM_JUGADOR)
        self.velocidad = VELOCIDAD_JUGADOR
        self.direccion = pygame.Vector2(0, 0)   # input (sentido deseado)
        self.vel = pygame.Vector2(0, 0)          # velocidad real (px/s)
        self.freno_brusco = False    # bandera de 1 frame: frenó de golpe

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
        """Mueve al jugador con inercia corta y baja los cooldowns.
        dt en segundos."""
        self.cooldown_disparo = max(0.0, self.cooldown_disparo - dt)
        self.cooldown_golpe = max(0.0, self.cooldown_golpe - dt)
        self.freno_brusco = False

        self.manejar_input()

        vel_max = self.velocidad * (FRENO_APUNTADO if self.apuntando else 1.0)

        # Inercia: llevo `vel` hacia el objetivo a paso constante.
        # Truco snappy: si pido el sentido opuesto (o suelto), uso la
        # fricción fuerte, así el giro se siente casi instantáneo aun
        # habiendo inercia lineal.
        objetivo = self.direccion * vel_max
        girando = (self.direccion.length_squared() == 0
                   or self.vel.dot(objetivo) < 0)
        tasa = FRICCION_JUGADOR if girando else ACEL_JUGADOR
        delta = objetivo - self.vel
        dist = delta.length()
        paso = tasa * dt
        vel_previa = self.vel.length()
        if dist <= paso or dist == 0:
            self.vel = pygame.Vector2(objetivo)
        else:
            self.vel += delta * (paso / dist)
        # Frenada notoria (venías rápido y ya casi parás): para polvo.
        if (self.direccion.length_squared() == 0
                and vel_previa > vel_max * 0.55
                and self.vel.length() < vel_max * 0.30):
            self.freno_brusco = True

        # Movimiento real con la velocidad ya integrada.
        if self.vel.length_squared() > 1e-6:
            paso_dir = self.vel.normalize()
            choco_x, choco_y = mover_con_colisiones(
                self.pos, self.rect, paso_dir, self.vel.length(), dt, paredes)
            # Al chocar, mato la velocidad del eje trabado: así se desliza
            # limpio contra la pared y no "salta" al despegarse.
            if choco_x:
                self.vel.x = 0
            if choco_y:
                self.vel.y = 0

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
        self.vel.update(0, 0)
        self.direccion.update(0, 0)

    def dibujar(self, superficie, camara, arma_img=None):
        """Sprite pixel art de Walter con caminata animada. La línea
        larga es la mira (solo al apuntar)."""
        import math
        r = camara.aplicar(self.rect)
        centro = pygame.Vector2(r.center)

        if self.apuntando:
            pygame.draw.line(superficie, COLOR_MIRA, centro,
                             centro + self.direccion_mira * 190, 2)

        # Squash & stretch muy sutil: apenas se estira cuando corre y
        # apenas se achata al frenar de golpe. Casi subliminal.
        rapidez = self.vel.length() / max(1, self.velocidad)
        if self.freno_brusco:
            estira = -0.05                            # frenada: se achata
        else:
            estira = min(0.06, rapidez * 0.06)
        escala = (1.0 - estira * 0.5, 1.0 + estira)

        dibujar_personaje(superficie, r, PALETA_WALTER, self,
                          mirando_izq=self.direccion_mira.x < 0,
                          escala=escala)
        if arma_img is not None:
            angulo = math.degrees(math.atan2(-self.direccion_mira.y,
                                             self.direccion_mira.x))
            img = arma_img
            if self.direccion_mira.x < 0:
                # Espejo vertical al apuntar a la izquierda: si no,
                # la rotación deja la pistola cabeza abajo.
                img = pygame.transform.flip(arma_img, False, True)
            rotada = pygame.transform.rotate(img, angulo)
            pos_arma = centro + self.direccion_mira * 32
            rect_arma = rotada.get_rect(
                center=(int(pos_arma.x), int(pos_arma.y)))
            superficie.blit(rotada, rect_arma)
