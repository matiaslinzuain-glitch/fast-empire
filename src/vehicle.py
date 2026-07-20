# =========================================================
# FAST EMPIRE — Física de manejo (estilo GTA 1/2)
#
# El vehículo NO va hacia donde apretás la tecla: W aplica
# empuje hacia la TROMPA (self.angulo) y A/D giran el volante.
# La velocidad real en el mundo (self.velocidad) es un vector
# aparte que "persigue" a la trompa según el agarre del modelo:
# la diferencia entre ambos es el derrape en las curvas.
#
# Los números base viven en settings.py y el carácter de cada
# modelo (acel/giro/agarre) en VEHICULOS (economy.py).
# =========================================================

import math

import pygame

from .settings import (
    ACEL_VEHICULO, FRENO_VEHICULO, ROCE_VEHICULO, GIRO_VEHICULO,
    REVERSA_VEHICULO, CHOQUE_VEHICULO,
    CAMARA_ADELANTO, CAMARA_ADELANTO_MAX,
)


class FisicaVehiculo:
    def __init__(self):
        self.angulo = 0.0                   # radianes; 0 = derecha
        self.rapidez = 0.0                  # px/s sobre la trompa (con signo)
        self.velocidad = pygame.Vector2()   # vector real en el mundo

    def montar(self, mirando_izq):
        """Arranca detenido, con la trompa hacia donde quedó el sprite
        estacionado."""
        self.angulo = math.pi if mirando_izq else 0.0
        self.rapidez = 0.0
        self.velocidad.update(0, 0)

    @property
    def mirando_izq(self):
        return math.cos(self.angulo) < 0

    def adelanto_camara(self):
        """Cuánto conviene adelantar la cámara en la dirección de
        marcha, para ver venir las esquinas a alta velocidad."""
        v = self.velocidad * CAMARA_ADELANTO
        if v.length() > CAMARA_ADELANTO_MAX:
            v.scale_to_length(CAMARA_ADELANTO_MAX)
        return v

    def actualizar(self, dt, jugador, paredes, vel_max, datos):
        """Un paso de simulación: lee el teclado y mueve `jugador`
        (pos + rect, in place). `datos` es la entrada del modelo en
        VEHICULOS; `vel_max` ya viene con todos los multiplicadores."""
        teclas = pygame.key.get_pressed()
        acelerar = teclas[pygame.K_w] or teclas[pygame.K_UP]
        frenar = teclas[pygame.K_s] or teclas[pygame.K_DOWN]
        izquierda = teclas[pygame.K_a] or teclas[pygame.K_LEFT]
        derecha = teclas[pygame.K_d] or teclas[pygame.K_RIGHT]

        # Motor, freno y rozamiento. S primero frena y después mete
        # reversa (que tiene su propio tope, más lento que avanzar).
        acel = ACEL_VEHICULO * datos.get("acel", 1.0)
        if acelerar:
            self.rapidez = min(self.rapidez + acel * dt, vel_max)
        elif frenar:
            self.rapidez = max(self.rapidez - FRENO_VEHICULO * dt,
                               -vel_max * REVERSA_VEHICULO)
        elif self.rapidez > 0:
            self.rapidez = max(self.rapidez - ROCE_VEHICULO * dt, 0.0)
        else:
            self.rapidez = min(self.rapidez + ROCE_VEHICULO * dt, 0.0)

        # Doblar: parado no gira, despacio dobla menos (el volante
        # "agarra" con velocidad) y en reversa se invierte, como al
        # estacionar de verdad.
        if abs(self.rapidez) > 10:
            factor = min(1.0, abs(self.rapidez) / (0.35 * vel_max))
            giro = GIRO_VEHICULO * datos.get("giro", 1.0) * factor * dt
            sentido = 1.0 if self.rapidez >= 0 else -1.0
            if izquierda:
                self.angulo -= giro * sentido
            if derecha:
                self.angulo += giro * sentido

        # El derrape: la velocidad real persigue a la "ideal" (la que
        # marca la trompa). Agarre alto = tarda más en alcanzarla =
        # el vehículo sigue de largo en la curva. Elevar el agarre a
        # dt*60 hace la mezcla independiente del framerate.
        adelante = pygame.Vector2(math.cos(self.angulo),
                                  math.sin(self.angulo)) * self.rapidez
        mezcla = datos.get("agarre", 0.90) ** (dt * 60)
        self.velocidad = self.velocidad * mezcla + adelante * (1 - mezcla)

        # Mover eje por eje (mismo esquema que a pie): chocar corta
        # la velocidad en ese eje y el golpe frena el motor.
        pos, rect = jugador.pos, jugador.rect
        pos.x += self.velocidad.x * dt
        rect.x = round(pos.x)
        for pared in paredes:
            if rect.colliderect(pared):
                if self.velocidad.x > 0:
                    rect.right = pared.left
                elif self.velocidad.x < 0:
                    rect.left = pared.right
                pos.x = rect.x
                self.velocidad.x = 0.0
                self.rapidez *= CHOQUE_VEHICULO

        pos.y += self.velocidad.y * dt
        rect.y = round(pos.y)
        for pared in paredes:
            if rect.colliderect(pared):
                if self.velocidad.y > 0:
                    rect.bottom = pared.top
                elif self.velocidad.y < 0:
                    rect.top = pared.bottom
                pos.y = rect.y
                self.velocidad.y = 0.0
                self.rapidez *= CHOQUE_VEHICULO
