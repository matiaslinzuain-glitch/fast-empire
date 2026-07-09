# =========================================================
# FAST EMPIRE — Cámara
# Cámara top-down que sigue al jugador y queda clampeada a
# los bordes del mapa (nunca muestra "afuera" del mundo).
#
# Uso:
#   camara = Camara(mapa.ancho_px, mapa.alto_px)
#   camara.actualizar(jugador.rect)          # una vez por frame
#   rect_en_pantalla = camara.aplicar(rect)  # al dibujar cualquier cosa
# =========================================================

import pygame

from .settings import ANCHO_VENTANA, ALTO_VENTANA


class Camara:
    def __init__(self, ancho_mapa, alto_mapa):
        self.ancho_mapa = ancho_mapa
        self.alto_mapa = alto_mapa
        # Offset = esquina superior izquierda de la "ventana" sobre el mundo
        self.offset = pygame.Vector2(0, 0)

    def actualizar(self, rect_objetivo):
        """Centra la cámara en el objetivo (normalmente el jugador)."""
        self.offset.x = rect_objetivo.centerx - ANCHO_VENTANA // 2
        self.offset.y = rect_objetivo.centery - ALTO_VENTANA // 2

        # Clamp: no mostrar más allá de los bordes del mapa
        self.offset.x = max(0, min(self.offset.x, self.ancho_mapa - ANCHO_VENTANA))
        self.offset.y = max(0, min(self.offset.y, self.alto_mapa - ALTO_VENTANA))

    def aplicar(self, rect):
        """Convierte un rect en coordenadas de mundo a coordenadas
        de pantalla. Devuelve un rect nuevo (no modifica el original)."""
        return rect.move(-round(self.offset.x), -round(self.offset.y))
