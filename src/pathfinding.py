# =========================================================
# FAST EMPIRE — Pathfinding A*  [Fase 11]
#
# A* sobre la grilla de tiles del mapa. Lo usan los
# inspectores (y los rivales cuando cazan) para rodear
# manzanas en vez de quedarse empujando una pared, que era
# el bug clásico de "la policía se queda quieta".
#
# encontrar_camino() devuelve una lista de waypoints en
# píxeles de mundo (centros de tile), ya suavizada: los
# primeros waypoints con línea de visión directa se saltean.
# Las diagonales solo se permiten si ambos ortogonales están
# libres (para no cortar esquinas contra un muro).
# =========================================================

import heapq

from .settings import TILE

# Presupuesto de nodos por búsqueda: en un mapa de 120x100 una
# búsqueda desbocada podría explorar 12.000 tiles; con esto se
# corta y el enemigo camina derecho (mejor eso que un tirón de FPS)
MAX_NODOS = 2600

_ORTOGONALES = ((1, 0), (-1, 0), (0, 1), (0, -1))
_DIAGONALES = ((1, 1), (1, -1), (-1, 1), (-1, -1))


def _a_tile(px, py):
    return int(px) // TILE, int(py) // TILE


def _centro(col, fila):
    return (col * TILE + TILE // 2, fila * TILE + TILE // 2)


def _vecino_caminable_mas_cercano(mapa, col, fila):
    """Si el destino cae en un tile sólido (p. ej. el jugador pegado
    a una pared), busca el tile libre más cercano en un anillo chico."""
    if not mapa.es_solido_tile(col, fila):
        return col, fila
    for radio in (1, 2):
        for df in range(-radio, radio + 1):
            for dc in range(-radio, radio + 1):
                if not mapa.es_solido_tile(col + dc, fila + df):
                    return col + dc, fila + df
    return None


def encontrar_camino(mapa, origen_px, destino_px):
    """A* de origen a destino (en píxeles de mundo). Devuelve una
    lista de waypoints en píxeles (sin incluir el origen), o [] si
    no hay camino dentro del presupuesto."""
    inicio = _vecino_caminable_mas_cercano(mapa, *_a_tile(*origen_px))
    meta = _vecino_caminable_mas_cercano(mapa, *_a_tile(*destino_px))
    if inicio is None or meta is None:
        return []
    if inicio == meta:
        return [destino_px]

    abiertos = [(0, inicio)]
    de_donde = {inicio: None}
    costo = {inicio: 0.0}
    nodos = 0

    while abiertos:
        _, actual = heapq.heappop(abiertos)
        if actual == meta:
            break
        nodos += 1
        if nodos > MAX_NODOS:
            return []
        col, fila = actual

        vecinos = []
        for dc, df in _ORTOGONALES:
            if not mapa.es_solido_tile(col + dc, fila + df):
                vecinos.append(((col + dc, fila + df), 1.0))
        for dc, df in _DIAGONALES:
            # Diagonal solo si los dos ortogonales están libres
            if (not mapa.es_solido_tile(col + dc, fila + df)
                    and not mapa.es_solido_tile(col + dc, fila)
                    and not mapa.es_solido_tile(col, fila + df)):
                vecinos.append(((col + dc, fila + df), 1.41))

        for vecino, paso in vecinos:
            nuevo = costo[actual] + paso
            if vecino not in costo or nuevo < costo[vecino]:
                costo[vecino] = nuevo
                # Heurística octile (admisible con diagonales)
                dx = abs(vecino[0] - meta[0])
                dy = abs(vecino[1] - meta[1])
                h = max(dx, dy) + 0.41 * min(dx, dy)
                heapq.heappush(abiertos, (nuevo + h, vecino))
                de_donde[vecino] = actual
    else:
        return []

    if meta not in de_donde:
        return []

    # Reconstruir (de la meta al inicio) y dar vuelta
    camino = []
    paso = meta
    while paso is not None and paso != inicio:
        camino.append(_centro(*paso))
        paso = de_donde[paso]
    camino.reverse()
    # El último waypoint es el destino real, no el centro del tile
    if camino:
        camino[-1] = destino_px
    return camino


class Navegante:
    """Estado de navegación reutilizable de un enemigo: pide caminos,
    los sigue waypoint a waypoint, replanea cada tanto y detecta
    atascos (si casi no se movió, recalcula)."""

    REPLAN = 0.9        # segundos entre replaneos hacia blancos móviles
    UMBRAL_ATASCO = 6.0  # px de avance mínimo por chequeo

    def __init__(self):
        self.camino = []
        self.destino = None
        self.timer_replan = 0.0
        self.timer_atasco = 0.0
        self._pos_previa = None

    def limpiar(self):
        self.camino = []
        self.destino = None

    def _replanear(self, mapa, origen, destino):
        self.camino = encontrar_camino(mapa, origen, destino)
        self.destino = destino
        self.timer_replan = self.REPLAN

    def siguiente_paso(self, dt, mapa, entidad, destino, movil=False):
        """Devuelve el punto (px de mundo) hacia el que caminar este
        frame, o None si no hay camino. `movil=True` replanea
        periódicamente (blancos que se mueven)."""
        origen = entidad.rect.center
        destino = (int(destino[0]), int(destino[1]))
        self.timer_replan -= dt

        destino_cambio = (
            self.destino is None
            or abs(destino[0] - self.destino[0]) > TILE
            or abs(destino[1] - self.destino[1]) > TILE)
        if destino_cambio or (movil and self.timer_replan <= 0) or not self.camino:
            self._replanear(mapa, origen, destino)
            if not self.camino:
                return None

        # Detección de atasco: si en ~0.5s casi no avanzó, replanear
        self.timer_atasco += dt
        if self.timer_atasco >= 0.5:
            self.timer_atasco = 0.0
            if self._pos_previa is not None:
                dx = origen[0] - self._pos_previa[0]
                dy = origen[1] - self._pos_previa[1]
                if dx * dx + dy * dy < self.UMBRAL_ATASCO ** 2:
                    self._replanear(mapa, origen, destino)
                    if not self.camino:
                        return None
            self._pos_previa = origen

        # Consumir waypoints alcanzados
        while self.camino:
            wx, wy = self.camino[0]
            dx = wx - origen[0]
            dy = wy - origen[1]
            if dx * dx + dy * dy < (TILE * 0.45) ** 2:
                self.camino.pop(0)
            else:
                break
        if not self.camino:
            return destino
        return self.camino[0]
