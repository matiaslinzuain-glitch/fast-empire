# =========================================================
# FAST EMPIRE — Enemigos e IA  [Fase 11]
#
# - Busqueda: nivel global 0–5 estilo "estrellas". Sube por
#   infracciones vistas (vender, disparar, agredir) y decae
#   con el tiempo si nadie te persigue. A más nivel, los
#   inspectores ven más lejos y corren más rápido.
#
# - InspectorSanitario: patrulla en ruta fija con cono de
#   visión. Estados: patrullar → investigar (escuchó un tiro)
#   → perseguir (te vio en falta) → buscar (te perdió).
#   Desde la Fase 11 persigue con pathfinding A*: rodea las
#   manzanas en vez de quedarse empujando la pared, y al
#   buscarte recorre la zona en serio.
#
# - RivalGastronomico ("contrabandistas"): competidores del
#   mercado negro. Mucho más duros desde la Fase 11: más
#   vida, más daño, y te cazan con pathfinding.
#
# - Proyectil: bala genérica (del jugador o de rivales).
# =========================================================

import random

import pygame

from .settings import (
    TILE,
    COLOR_INSPECTOR, COLOR_INSPECTOR_GORRA,
    COLOR_RIVAL, COLOR_RIVAL_BANDANA,
    COLOR_BALA, COLOR_VIDA, COLOR_VIDA_FONDO,
)
from .player import mover_con_colisiones
from .pathfinding import Navegante
from .sprites import PALETA_INSPECTOR, PALETA_RIVAL, dibujar_personaje

COLOR_PIEL = (196, 164, 120)


def hay_linea_de_vision(mapa, origen, destino):
    """True si no hay paredes entre ambos puntos (muestreo cada ~14px
    sobre la grilla del mapa, que es una consulta O(1) por punto)."""
    origen = pygame.Vector2(origen)
    destino = pygame.Vector2(destino)
    distancia = origen.distance_to(destino)
    pasos = int(distancia // 14) + 1
    for i in range(1, pasos):
        punto = origen.lerp(destino, i / pasos)
        if mapa.es_solido_en(punto.x, punto.y):
            return False
    return True


# ---------------------------------------------------------
# Nivel de búsqueda global (0 a 5)
# ---------------------------------------------------------
NIVEL_MAXIMO = 5
SEGUNDOS_DECAIMIENTO = 18  # sin infracciones ni persecución, baja 1 nivel


class Busqueda:
    def __init__(self):
        self.nivel = 0
        self._cooldowns = {}      # anti-spam: un reporte por tipo cada X seg
        self._timer_calma = 0.0

    def reportar(self, tipo, cantidad, cooldown=5.0):
        """Sube el nivel por una infracción, salvo que ese tipo de
        infracción ya se haya reportado hace poco."""
        if self._cooldowns.get(tipo, 0.0) > 0.0:
            return
        self._cooldowns[tipo] = cooldown
        self.nivel = min(NIVEL_MAXIMO, self.nivel + cantidad)
        self._timer_calma = 0.0

    def maximo(self):
        """Infracción imperdonable (eliminar un inspector)."""
        self.nivel = NIVEL_MAXIMO
        self._timer_calma = 0.0

    def reiniciar(self):
        self.nivel = 0
        self._cooldowns.clear()
        self._timer_calma = 0.0

    def actualizar(self, dt, persecucion_activa, calma_mult=1.0):
        """`calma_mult` > 1 (habilidad Fantasma) enfría más rápido."""
        for tipo in list(self._cooldowns):
            self._cooldowns[tipo] = max(0.0, self._cooldowns[tipo] - dt)
        if self.nivel > 0 and not persecucion_activa:
            self._timer_calma += dt * calma_mult
            if self._timer_calma >= SEGUNDOS_DECAIMIENTO:
                self.nivel -= 1
                self._timer_calma = 0.0
        elif persecucion_activa:
            self._timer_calma = 0.0


# ---------------------------------------------------------
# Proyectil (balas del jugador y de los rivales)
# ---------------------------------------------------------
class Proyectil:
    def __init__(self, x, y, direccion, velocidad, dano, del_jugador):
        self.pos = pygame.Vector2(x, y)
        self.direccion = pygame.Vector2(direccion).normalize()
        self.velocidad = velocidad
        self.dano = dano
        self.del_jugador = del_jugador
        self.vida = 1.4  # segundos de vuelo máximo (alcance)
        self.muerto = False

    def actualizar(self, dt, mapa):
        self.pos += self.direccion * self.velocidad * dt
        self.vida -= dt
        if self.vida <= 0 or mapa.es_solido_en(self.pos.x, self.pos.y):
            self.muerto = True

    def dibujar(self, superficie, camara):
        r = camara.aplicar(pygame.Rect(int(self.pos.x) - 2, int(self.pos.y) - 2, 4, 4))
        pygame.draw.rect(superficie, COLOR_BALA, r)


# ---------------------------------------------------------
# Base común de enemigos
# ---------------------------------------------------------
class Enemigo:
    TAM = (20, 24)

    def __init__(self, x, y, vida, velocidad):
        self.pos = pygame.Vector2(x, y)
        self.rect = pygame.Rect(round(x), round(y), *self.TAM)
        self.vida_max = vida
        self.vida = vida
        self.velocidad = velocidad
        self.mirando = pygame.Vector2(1, 0)  # hacia dónde mira (para el cono)
        self.muerto = False
        self.navegante = Navegante()

    def recibir_dano(self, dano):
        """Devuelve True si este golpe lo mató."""
        self.vida -= dano
        if self.vida <= 0:
            self.muerto = True
        return self.muerto

    def _ir_hacia(self, destino, dt, paredes, velocidad=None):
        """Camina en línea recta hacia el destino (con colisiones).
        Devuelve la distancia que faltaba antes de moverse."""
        hacia = pygame.Vector2(destino) - pygame.Vector2(self.rect.center)
        distancia = hacia.length()
        if distancia > 2:
            direccion = hacia.normalize()
            self.mirando = direccion
            mover_con_colisiones(self.pos, self.rect, direccion,
                                 velocidad or self.velocidad, dt, paredes)
        return distancia

    def _navegar_hacia(self, destino, dt, mapa, paredes, velocidad=None,
                       movil=False):
        """Camina hacia el destino siguiendo un camino A* (rodea las
        manzanas). Si hay línea de visión directa va derecho, que es
        más natural. Devuelve la distancia REAL al destino final."""
        centro = pygame.Vector2(self.rect.center)
        distancia = centro.distance_to(destino)
        if distancia <= 2:
            return distancia
        if hay_linea_de_vision(mapa, self.rect.center, destino):
            self.navegante.limpiar()
            self._ir_hacia(destino, dt, paredes, velocidad)
            return distancia
        paso = self.navegante.siguiente_paso(dt, mapa, self, destino, movil)
        if paso is None:
            # Sin camino: al menos empujar en línea recta (caso raro)
            self._ir_hacia(destino, dt, paredes, velocidad)
        else:
            self._ir_hacia(paso, dt, paredes, velocidad)
        return distancia

    def _dibujar_cuerpo(self, superficie, r, color_ropa, color_cabeza):
        pygame.draw.rect(superficie, color_ropa,
                         (r.x, r.y + 7, r.width, r.height - 7))
        pygame.draw.rect(superficie, color_cabeza,
                         (r.x + 4, r.y, r.width - 8, 9))

    def _dibujar_barra_vida(self, superficie, r):
        """Barrita sobre la cabeza, solo si está lastimado."""
        if self.vida >= self.vida_max:
            return
        ancho = r.width
        relleno = max(0, int(ancho * self.vida / self.vida_max))
        pygame.draw.rect(superficie, COLOR_VIDA_FONDO, (r.x, r.y - 6, ancho, 3))
        pygame.draw.rect(superficie, COLOR_VIDA, (r.x, r.y - 6, relleno, 3))


# ---------------------------------------------------------
# Inspector sanitario
# ---------------------------------------------------------
class InspectorSanitario(Enemigo):
    VIDA = 80
    VELOCIDAD = 150
    VISION = 190            # px base; crece con el nivel de búsqueda
    MEDIO_ANGULO = 50       # apertura del cono a cada lado (grados)
    SEGUNDOS_PERDIDA = 4.5  # sin verte mientras persigue → pasa a buscar
    SEGUNDOS_BUSQUEDA = 12.0
    RADIO_RASTRILLAJE = 6   # tiles alrededor de la última posición vista

    def __init__(self, ruta_tiles):
        self.ruta_tiles = ruta_tiles  # se guarda para el respawn
        self.ruta = [(c * TILE, f * TILE) for c, f in ruta_tiles]
        super().__init__(*self.ruta[0], self.VIDA, self.VELOCIDAD)
        self.indice = 0
        self.estado = "patrullar"  # patrullar | investigar | perseguir | buscar
        self.ultima_vista = None       # última posición conocida del jugador
        self.objetivo_investigar = None
        self.timer_perdida = 0.0
        self.timer_busqueda = 0.0
        self.timer_mirar = 0.0
        self.objetivo_deambulo = None
        self.vision_actual = self.VISION  # para dibujar el cono

    # --- Percepción ---
    def ve_al_jugador(self, jugador, mapa):
        """Cono de visión + línea de visión. Persiguiendo ve en todas
        direcciones y un poco más lejos (está alerta)."""
        hacia = pygame.Vector2(jugador.rect.center) - pygame.Vector2(self.rect.center)
        distancia = hacia.length()
        alerta = self.estado == "perseguir"
        alcance = self.vision_actual * (1.25 if alerta else 1.0)
        if distancia > alcance:
            return False
        if not alerta and distancia > 1:
            # Ángulo entre hacia-dónde-mira y hacia-el-jugador
            desvio = abs(self.mirando.angle_to(hacia))
            desvio = min(desvio, 360 - desvio)
            if desvio > self.MEDIO_ANGULO:
                return False
        return hay_linea_de_vision(mapa, self.rect.center, jugador.rect.center)

    def alertar(self, posicion):
        """Escuchó un disparo: va a investigar (si no está persiguiendo)."""
        if self.estado in ("patrullar", "investigar", "buscar"):
            self.objetivo_investigar = pygame.Vector2(posicion)
            self.estado = "investigar"

    def puntos_cono(self, camara):
        """Polígono del cono de visión en coordenadas de pantalla."""
        centro = pygame.Vector2(camara.aplicar(self.rect).center)
        puntos = [centro]
        for angulo in range(-self.MEDIO_ANGULO, self.MEDIO_ANGULO + 1, 25):
            puntos.append(centro + self.mirando.rotate(angulo) * self.vision_actual)
        return puntos

    # --- Lógica ---
    def actualizar(self, dt, jugador, mapa, paredes, vendiendo, busqueda,
                   vision_mult=1.0):
        """Devuelve "arresto" si atrapó al jugador; None si no.
        `vision_mult` < 1 (habilidad Perfil bajo) les acorta la vista."""
        # La búsqueda alta los vuelve más rápidos y con mejor vista
        multiplicador = 1 + 0.09 * busqueda.nivel
        self.vision_actual = (self.VISION + 22 * busqueda.nivel) * vision_mult
        ve = self.ve_al_jugador(jugador, mapa)
        # Solo reaccionan si te ven EN FALTA: vendiendo, o con nivel
        # de búsqueda activo (ya te tienen fichado)
        en_falta = vendiendo or busqueda.nivel >= 1

        if self.estado == "perseguir":
            if ve:
                self.ultima_vista = pygame.Vector2(jugador.rect.center)
                self.timer_perdida = 0.0
            else:
                self.timer_perdida += dt
            self._navegar_hacia(self.ultima_vista, dt, mapa, paredes,
                                self.velocidad * multiplicador, movil=ve)
            if self.rect.colliderect(jugador.rect.inflate(8, 8)):
                return "arresto"
            if self.timer_perdida > self.SEGUNDOS_PERDIDA:
                self.estado = "buscar"
                self.timer_busqueda = self.SEGUNDOS_BUSQUEDA
                self.objetivo_deambulo = None

        elif self.estado == "buscar":
            if ve and en_falta:
                self._empezar_persecucion(jugador, vendiendo, busqueda)
            else:
                self._rastrillar_zona(dt, mapa, paredes)
                self.timer_busqueda -= dt
                if self.timer_busqueda <= 0:
                    self.estado = "patrullar"
                    self.navegante.limpiar()

        elif self.estado == "investigar":
            if ve and en_falta:
                self._empezar_persecucion(jugador, vendiendo, busqueda)
            elif self._navegar_hacia(self.objetivo_investigar, dt, mapa,
                                     paredes) < 10:
                self.timer_mirar += dt
                if self.timer_mirar > 2.0:  # miró alrededor y no vio nada
                    self.timer_mirar = 0.0
                    self.estado = "patrullar"

        else:  # patrullar
            if ve and en_falta:
                self._empezar_persecucion(jugador, vendiendo, busqueda)
            elif self._navegar_hacia(self.ruta[self.indice], dt, mapa,
                                     paredes) < 8:
                self.indice = (self.indice + 1) % len(self.ruta)

        return None

    def _empezar_persecucion(self, jugador, vendiendo, busqueda):
        self.estado = "perseguir"
        self.ultima_vista = pygame.Vector2(jugador.rect.center)
        self.timer_perdida = 0.0
        self.navegante.limpiar()
        if vendiendo:
            busqueda.reportar("venta", 1, cooldown=6.0)

    def _rastrillar_zona(self, dt, mapa, paredes):
        """Rastrilla la zona: primero va a la última posición vista y
        después patea tiles caminables al azar alrededor (con A*, así
        revisa de verdad en vez de frotarse contra una pared)."""
        if self.ultima_vista is not None:
            if self._navegar_hacia(self.ultima_vista, dt, mapa, paredes) < 14:
                self.objetivo_deambulo = None
                self.ancla_busqueda = pygame.Vector2(self.ultima_vista)
                self.ultima_vista = None
            return
        ancla = getattr(self, "ancla_busqueda", None) \
            or pygame.Vector2(self.rect.center)
        if self.objetivo_deambulo is None or \
                self._navegar_hacia(self.objetivo_deambulo, dt, mapa,
                                    paredes) < 12:
            # Elegir un tile caminable al azar cerca del ancla
            for _ in range(8):
                col = int(ancla.x // TILE) + random.randint(
                    -self.RADIO_RASTRILLAJE, self.RADIO_RASTRILLAJE)
                fila = int(ancla.y // TILE) + random.randint(
                    -self.RADIO_RASTRILLAJE, self.RADIO_RASTRILLAJE)
                if not mapa.es_solido_tile(col, fila):
                    self.objetivo_deambulo = pygame.Vector2(
                        col * TILE + TILE // 2, fila * TILE + TILE // 2)
                    break

    def dibujar(self, superficie, camara):
        r = camara.aplicar(self.rect)
        dibujar_personaje(superficie, r, PALETA_INSPECTOR, self)
        self._dibujar_barra_vida(superficie, r)


# ---------------------------------------------------------
# Rival gastronómico
# ---------------------------------------------------------
class RivalGastronomico(Enemigo):
    """Los contrabandistas de la competencia. Desde la Fase 11 son
    hueso duro: el triple de vida, pegan más fuerte, se mueven de
    costado mientras tirotean y te cazan con pathfinding."""
    VIDA = 150
    VELOCIDAD = 150
    RANGO_VISTA = 280       # ve en todas direcciones (conoce su territorio)
    RANGO_DISPARO = 250
    DISTANCIA_COMODA = 170  # no se acerca más que esto para tirotear
    CADENCIA = 1.1
    DANO_BALA = 14
    VELOCIDAD_BALA = 400
    SEGUNDOS_CAZA = 9.0

    def __init__(self, x, y, radio_hogar, zona_id=None):
        super().__init__(x, y, self.VIDA, self.VELOCIDAD)
        self.hogar = pygame.Vector2(x, y)    # centro de su territorio
        self.radio_hogar = radio_hogar
        self.zona_id = zona_id               # ata al rival con su franquicia
        self.estado = "deambular"  # deambular | atacar | cazar
        self.cooldown_disparo = 0.0
        self.timer_caza = 0.0
        self.objetivo_deambulo = None
        self.ultima_vista = None
        self.lado_strafe = random.choice((-1, 1))
        self.timer_strafe = random.uniform(1.0, 2.0)

    def ve_al_jugador(self, jugador, mapa):
        distancia = pygame.Vector2(self.rect.center).distance_to(jugador.rect.center)
        return distancia < self.RANGO_VISTA and \
            hay_linea_de_vision(mapa, self.rect.center, jugador.rect.center)

    def actualizar(self, dt, jugador, mapa, paredes, es_amenaza):
        """`es_amenaza` = el jugador ya vendió lo suficiente para que lo
        conozcan. Devuelve un Proyectil si disparó; None si no."""
        self.cooldown_disparo = max(0.0, self.cooldown_disparo - dt)

        # Si no te conocen, cada uno atiende su negocio
        if not es_amenaza:
            self._deambular(dt, paredes)
            return None

        ve = self.ve_al_jugador(jugador, mapa)

        if self.estado == "atacar":
            if ve:
                self.ultima_vista = pygame.Vector2(jugador.rect.center)
                return self._combatir(dt, jugador, paredes)
            self.estado = "cazar"
            self.timer_caza = self.SEGUNDOS_CAZA

        elif self.estado == "cazar":
            if ve:
                self.estado = "atacar"
            else:
                # Va a la última posición conocida (rodeando manzanas)
                # y agota la paciencia
                self._navegar_hacia(self.ultima_vista, dt, mapa, paredes)
                self.timer_caza -= dt
                if self.timer_caza <= 0:
                    self.estado = "deambular"
                    self.navegante.limpiar()

        else:  # deambular
            if ve:
                self.estado = "atacar"
            else:
                self._deambular(dt, paredes)

        return None

    def _combatir(self, dt, jugador, paredes):
        """Mantiene distancia de tiroteo, se mueve de costado para
        ser difícil de acertar, y dispara con dispersión."""
        hacia = pygame.Vector2(jugador.rect.center) - pygame.Vector2(self.rect.center)
        distancia = hacia.length()
        if distancia > 1:
            self.mirando = hacia.normalize()

        if distancia > self.DISTANCIA_COMODA:
            self._ir_hacia(jugador.rect.center, dt, paredes)
        else:
            # Strafe lateral: cambia de lado cada 1-2 segundos
            self.timer_strafe -= dt
            if self.timer_strafe <= 0:
                self.timer_strafe = random.uniform(1.0, 2.0)
                self.lado_strafe = -self.lado_strafe
            lateral = self.mirando.rotate(90 * self.lado_strafe)
            mover_con_colisiones(self.pos, self.rect, lateral,
                                 self.velocidad * 0.7, dt, paredes)

        if distancia < self.RANGO_DISPARO and self.cooldown_disparo <= 0:
            self.cooldown_disparo = self.CADENCIA
            direccion = self.mirando.rotate(random.uniform(-5, 5))
            return Proyectil(*self.rect.center, direccion,
                             self.VELOCIDAD_BALA, self.DANO_BALA,
                             del_jugador=False)
        return None

    def _deambular(self, dt, paredes):
        """Pasea por su territorio eligiendo puntos al azar."""
        if self.objetivo_deambulo is None or \
                self._ir_hacia(self.objetivo_deambulo, dt, paredes,
                               self.velocidad * 0.5) < 8:
            angulo = random.uniform(0, 360)
            radio = random.uniform(0, self.radio_hogar)
            self.objetivo_deambulo = self.hogar + pygame.Vector2(radio, 0).rotate(angulo)

    def dibujar(self, superficie, camara):
        r = camara.aplicar(self.rect)
        dibujar_personaje(superficie, r, PALETA_RIVAL, self)
        self._dibujar_barra_vida(superficie, r)


# ---------------------------------------------------------
# Plantillas del mapa actual
# ---------------------------------------------------------
# Rutas de patrulla disponibles (en tiles). Desde la Fase 5 los
# inspectores NO viven en el mapa: llegan cuando hay denuncias y
# se retiran cuando la búsqueda vuelve a cero. Con el mapa de la
# Fase 11 hay rutas también en el Barrio Este y la Zona Sur.
RUTAS_INSPECTORES = [
    [(2, 9), (29, 9), (29, 18), (2, 18)],      # avenida norte
    [(15, 17), (43, 17), (43, 26), (15, 26)],  # centro / almacén
    [(1, 25), (43, 25), (43, 34), (1, 34)],    # anillo del centro-sur
    [(1, 33), (43, 33), (43, 42), (1, 42)],    # sur / terminal vieja
    [(1, 47), (33, 47), (33, 53), (1, 53)],    # distrito sur / galpones
    [(76, 9), (110, 9), (110, 25), (76, 25)],  # barrio este norte
    [(76, 33), (117, 33), (117, 51), (76, 51)],  # barrio este sur
    [(2, 58), (100, 58), (100, 65), (2, 65)],  # feria del sur
    [(2, 75), (110, 75), (110, 88), (2, 88)],  # industrial / barrio bajo
    [(2, 93), (115, 93), (115, 94), (2, 94)],  # muelle nuevo
]


def crear_inspectores(cantidad=None, cerca_de=None):
    """Crea inspectores sobre las rutas de patrulla. Si se indica
    `cerca_de` (px de mundo), prioriza las rutas más cercanas a la
    denuncia; `cantidad` limita cuántos llegan."""
    rutas = list(RUTAS_INSPECTORES)
    if cerca_de is not None:
        objetivo = pygame.Vector2(cerca_de)

        def distancia(ruta):
            centro = pygame.Vector2(
                sum(c for c, _ in ruta) / len(ruta) * TILE,
                sum(f for _, f in ruta) / len(ruta) * TILE)
            return centro.distance_to(objetivo)

        rutas.sort(key=distancia)
    if cantidad is not None:
        rutas = rutas[:cantidad]
    return [InspectorSanitario(ruta) for ruta in rutas]


def crear_matones(indices_zona):
    """Los matones que custodian las zonas de venta del paso en
    disputa (sistema de la Red: zona_id = índice de LUGARES_VENTA).
    Cada uno ronda el centro de su zona y NO respawnea: eliminarlo
    es progreso permanente de la conquista."""
    from .economy import LUGARES_VENTA
    matones = []
    for indice in indices_zona:
        col, fila, ancho, alto = LUGARES_VENTA[indice][1]
        cx = int((col + ancho / 2) * TILE)
        cy = int((fila + alto / 2) * TILE)
        radio = max(ancho, alto) * TILE // 2 + TILE
        matones.append(RivalGastronomico(cx, cy, radio_hogar=radio,
                                         zona_id=indice))
    return matones
