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

from .settings import ANCHO_LIENZO, ALTO_LIENZO, CAMARA_SUAVIZADO


class Camara:
    def __init__(self, ancho_mapa, alto_mapa, y_subsuelo=None):
        self.ancho_mapa = ancho_mapa
        self.alto_mapa = alto_mapa
        # Frontera vertical entre la ciudad y el subsuelo (px de
        # mundo). None = un solo mundo, sin zonas.
        self.y_subsuelo = y_subsuelo
        # Offset = esquina superior izquierda de la "ventana" sobre el mundo
        self.offset = pygame.Vector2(0, 0)

    def actualizar(self, rect_objetivo, dt=None, adelanto=(0, 0)):
        """Sigue al objetivo (normalmente el jugador), clampeada a los
        límites de SU zona (ciudad o subsuelo). Con `dt` el seguimiento
        es suave (lerp, estilo GTA); sin `dt` salta seco — es lo que
        quieren los teleports. `adelanto` corre el punto de mira, p.ej.
        hacia donde viaja el auto para ver venir las esquinas."""
        destino_x = rect_objetivo.centerx + adelanto[0] - ANCHO_LIENZO // 2
        destino_y = rect_objetivo.centery + adelanto[1] - ALTO_LIENZO // 2

        if self.y_subsuelo is None:
            y_min, y_max = 0, self.alto_mapa
        elif rect_objetivo.centery >= self.y_subsuelo:
            # Instancia sótano: los límites de la ciudad se ignoran
            y_min, y_max = self.y_subsuelo, self.alto_mapa
        else:
            # La ciudad: la cámara nunca baja al subsuelo
            y_min, y_max = 0, self.y_subsuelo

        # Clamp: no mostrar más allá de los bordes de la zona
        destino_x = max(0, min(destino_x, self.ancho_mapa - ANCHO_LIENZO))
        destino_y = max(y_min, min(destino_y, y_max - ALTO_LIENZO))

        # Un destino a más de una pantalla es un teleport (sótano,
        # reaparición): ahí el lerp haría un paneo larguísimo por
        # todo el mapa, mejor saltar seco.
        salto = (abs(destino_x - self.offset.x) > ANCHO_LIENZO
                 or abs(destino_y - self.offset.y) > ALTO_LIENZO)
        if dt is None or salto:
            self.offset.update(destino_x, destino_y)
        else:
            t = 1 - CAMARA_SUAVIZADO ** dt
            self.offset.x += (destino_x - self.offset.x) * t
            self.offset.y += (destino_y - self.offset.y) * t

    def aplicar(self, rect):
        """Convierte un rect en coordenadas de mundo a coordenadas
        de pantalla. Devuelve un rect nuevo (no modifica el original)."""
        return rect.move(-round(self.offset.x), -round(self.offset.y))
