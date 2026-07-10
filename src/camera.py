# =========================================================
# FAST EMPIRE — Cámara
# Cámara top-down que sigue al jugador y queda clampeada a
# los bordes del mapa (nunca muestra "afuera" del mundo).
#
# Con `y_subsuelo` el mundo se parte en DOS instancias
# verticales aisladas: la ciudad (arriba) y el sótano
# (abajo). La cámara elige sus límites según dónde esté el
# jugador, así desde el sótano jamás se ve la ciudad ni al
# revés — cada zona se comporta como una escena separada.
#
# Uso:
#   camara = Camara(mapa.ancho_px, mapa.alto_px, Y_SUBSUELO)
#   camara.actualizar(jugador.rect)          # una vez por frame
#   rect_en_pantalla = camara.aplicar(rect)  # al dibujar cualquier cosa
# =========================================================

import pygame

from .settings import ANCHO_VENTANA, ALTO_VENTANA


class Camara:
    def __init__(self, ancho_mapa, alto_mapa, y_subsuelo=None):
        self.ancho_mapa = ancho_mapa
        self.alto_mapa = alto_mapa
        # Frontera vertical entre la ciudad y el subsuelo (px de
        # mundo). None = un solo mundo, sin zonas.
        self.y_subsuelo = y_subsuelo
        # Offset = esquina superior izquierda de la "ventana" sobre el mundo
        self.offset = pygame.Vector2(0, 0)

    def actualizar(self, rect_objetivo):
        """Centra la cámara en el objetivo (normalmente el jugador),
        clampeada a los límites de SU zona (ciudad o subsuelo)."""
        self.offset.x = rect_objetivo.centerx - ANCHO_VENTANA // 2
        self.offset.y = rect_objetivo.centery - ALTO_VENTANA // 2

        if self.y_subsuelo is None:
            y_min, y_max = 0, self.alto_mapa
        elif rect_objetivo.centery >= self.y_subsuelo:
            # Instancia sótano: los límites de la ciudad se ignoran
            y_min, y_max = self.y_subsuelo, self.alto_mapa
        else:
            # La ciudad: la cámara nunca baja al subsuelo
            y_min, y_max = 0, self.y_subsuelo

        # Clamp: no mostrar más allá de los bordes de la zona
        self.offset.x = max(0, min(self.offset.x, self.ancho_mapa - ANCHO_VENTANA))
        self.offset.y = max(y_min, min(self.offset.y, y_max - ALTO_VENTANA))

    def aplicar(self, rect):
        """Convierte un rect en coordenadas de mundo a coordenadas
        de pantalla. Devuelve un rect nuevo (no modifica el original)."""
        return rect.move(-round(self.offset.x), -round(self.offset.y))
