# =========================================================
# FAST EMPIRE — Reloj de juego  [Fase 11]
#
# El tiempo del mundo: 1 segundo real = 1 minuto de juego
# (un día completo dura 24 minutos reales). Lo usan el HUD
# (reloj arriba al centro) y los tratos del celular, que se
# acuerdan para una hora concreta ("nos vemos a las 18:30").
#
# La hora se guarda en la partida: minuto_total es el único
# estado (de ahí salen día, hora y minuto).
# =========================================================

from .settings import MINUTOS_POR_SEGUNDO, HORA_INICIAL


class RelojJuego:
    def __init__(self):
        # Minutos de juego acumulados desde el día 1 a las 00:00
        self.minuto_total = float(HORA_INICIAL)

    def actualizar(self, dt):
        self.minuto_total += dt * MINUTOS_POR_SEGUNDO

    @property
    def dia(self):
        return int(self.minuto_total // (24 * 60)) + 1

    @property
    def hora(self):
        return int(self.minuto_total // 60) % 24

    @property
    def minuto(self):
        return int(self.minuto_total) % 60

    def texto(self):
        """"Día 2 · 18:05" para el HUD."""
        return f"Día {self.dia} · {self.hora:02d}:{self.minuto:02d}"

    def texto_hora(self, minuto_total):
        """Formatea un instante futuro: "18:30" (o "mañana 09:00")."""
        hora = int(minuto_total // 60) % 24
        minuto = int(minuto_total) % 60
        etiqueta = f"{hora:02d}:{minuto:02d}"
        if int(minuto_total // (24 * 60)) > int(self.minuto_total // (24 * 60)):
            etiqueta = "mañana " + etiqueta
        return etiqueta

    def en_minutos(self, minutos):
        """Instante (minuto_total) a tantos minutos de juego de ahora."""
        return self.minuto_total + minutos
