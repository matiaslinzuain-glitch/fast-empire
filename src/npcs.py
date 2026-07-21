# =========================================================
# FAST EMPIRE — NPCs  [Fase 11]
#
# - ClienteLocal: entra al local, hace fila frente al
#   mostrador, Walter lo atiende con E, se va a comer a un
#   costado y sale. Si la fila no avanza se cansa y se va.
# - CompradorIlegal: desde la Fase 11 NO aparece de la nada:
#   te contacta por el celular, acuerdan lugar y hora, y a
#   esa hora te espera en el punto acordado.
# - Todos los NPCs tienen vida y se pueden matar. Matar a un
#   civil es homicidio: búsqueda máxima y la policía te
#   rastrea activamente (eso lo maneja main.py). Los NPCs
#   que ven violencia salen corriendo.
# =========================================================

import random

import pygame

import math

from .economy import INGREDIENTES_POR_TANDA, MAX_CONTENEDOR
from .map import POSICIONES_FILA
from .settings import COLOR_CAJA, COLOR_CAJA_CINTA, TILE
from .sprites import (paleta_peaton, paleta_encapuchado, dibujar_personaje,
                      dibujar_vehiculo_conduciendo)

VELOCIDAD_PEATON = 170       # px/s, más lento que Walter
VELOCIDAD_PANICO = 300      # px/s huyendo
SEGUNDOS_COMIENDO = 5.0
PACIENCIA_FILA = 30.0        # segundos antes de irse sin comprar
DISTANCIA_COMPRA = 60       # px al comprador para concretar el trato
VIDA_NPC = 30                # puntos de vida de un civil

# Ropa variada para que no parezcan clones
COLORES_ROPA = [
    (60, 76, 110),   # azul
    (92, 92, 96),    # gris
    (70, 100, 70),   # verde
    (122, 100, 58),  # mostaza
    (100, 62, 92),   # violeta
]
COLOR_PIEL = (196, 164, 120)
COLOR_CAPUCHA = (58, 58, 64)   # compradores ilegales, bajo perfil
COLOR_PLATO = (235, 235, 230)


class _Peaton:
    """Base con movimiento simple hacia un objetivo, vida y pánico."""

    def __init__(self, x, y, color_ropa):
        self.pos = pygame.Vector2(x, y)
        self.rect = pygame.Rect(int(x), int(y), 36, 48)
        self.color_ropa = color_ropa
        self.paleta = paleta_peaton(color_ropa)
        self.terminado = False  # marcado para eliminar
        self.hp = VIDA_NPC
        self.muerto = False

    def recibir_dano(self, dano):
        """Devuelve True si este golpe lo mató."""
        self.hp -= dano
        if self.hp <= 0:
            self.muerto = True
            self.terminado = True
        return self.muerto

    def _avanzar_hacia(self, destino, dt, velocidad=VELOCIDAD_PEATON):
        """Da un paso hacia el destino y devuelve la distancia
        restante. El paso nunca se pasa de largo (con un frame
        largo, oscilaría alrededor del objetivo sin llegar)."""
        hacia = pygame.Vector2(destino) - pygame.Vector2(self.rect.center)
        distancia = hacia.length()
        if distancia > 1:
            paso = min(velocidad * dt, distancia)
            self.pos += hacia.normalize() * paso
            self.rect.topleft = (round(self.pos.x), round(self.pos.y))
        return distancia

    def _dibujar_cuerpo(self, superficie, r, color_cabeza=COLOR_PIEL):
        pygame.draw.rect(superficie, self.color_ropa,
                         (r.x, r.y + 14, r.width, r.height - 14))
        pygame.draw.rect(superficie, color_cabeza,
                         (r.x + 8, r.y, r.width - 16, 18))


class ClienteLocal(_Peaton):
    """Cliente del local de comidas. Estados:
    entrando → cola → comiendo → saliendo (o huyendo, si vio tiros)."""

    def __init__(self, entrada, puerta):
        super().__init__(*entrada, random.choice(COLORES_ROPA))
        self.puerta = pygame.Vector2(puerta)
        self.salida = pygame.Vector2(entrada)   # se va por donde vino
        # Punto en la vereda alineado con la puerta: entrar y salir
        # derecho por el vano en vez de cortar camino por la pared
        self.frente_puerta = pygame.Vector2(puerta[0], entrada[1])
        self.estado = "entrando"
        self.objetivo = None       # su lugar en la fila (lo asigna main.py)
        self.paciencia = PACIENCIA_FILA
        self.timer_comer = 0.0
        self.lugar = None          # dónde come

    def entrar_en_panico(self):
        """Vio violencia: suelta todo y corre hacia la salida."""
        if self.estado != "huyendo":
            self.estado = "huyendo"

    def actualizar(self, dt):
        """Devuelve "harto" en el frame en que se cansó de esperar."""
        if self.estado == "huyendo":
            # Corre directo a su punto de entrada y desaparece
            if self._avanzar_hacia(self.salida, dt, VELOCIDAD_PANICO) < 24:
                self.terminado = True
            return None

        if self.estado == "entrando":
            if self._avanzar_hacia(self.frente_puerta, dt) < 20:
                self.estado = "cruzando"
        elif self.estado == "cruzando":
            if self._avanzar_hacia(self.puerta, dt) < 20:
                self.estado = "cola"

        elif self.estado == "cola":
            if self.objetivo is not None:
                self._avanzar_hacia(self.objetivo, dt)
            self.paciencia -= dt
            if self.paciencia <= 0:
                self.irse()
                return "harto"

        elif self.estado == "comiendo":
            if self._avanzar_hacia(self.lugar, dt) < 12:
                self.timer_comer -= dt
                if self.timer_comer <= 0:
                    self.irse()

        elif self.estado == "saliendo":  # hacia la puerta desde adentro
            if self._avanzar_hacia(self.puerta, dt) < 24:
                self.estado = "yendose"
        elif self.estado == "yendose":   # cruzar el vano hacia la vereda
            if self._avanzar_hacia(self.frente_puerta, dt) < 20:
                self.estado = "yendose2"
        else:  # yendose2: por la calle hasta desaparecer
            if self._avanzar_hacia(self.salida, dt) < 20:
                self.terminado = True
        return None

    def listo_para_atender(self, posicion_frente):
        """True si está primero en la fila, quieto frente al mostrador."""
        return (self.estado == "cola" and
                pygame.Vector2(self.rect.center).distance_to(posicion_frente) < 48)

    def servir(self, lugar):
        """Fue atendido: se va a comer al lugar indicado."""
        self.estado = "comiendo"
        self.lugar = pygame.Vector2(lugar)
        self.timer_comer = SEGUNDOS_COMIENDO

    def irse(self):
        if self.estado not in ("saliendo", "yendose", "yendose2", "huyendo"):
            self.estado = "saliendo"

    def dibujar(self, superficie, camara):
        r = camara.aplicar(self.rect)
        dibujar_personaje(superficie, r, self.paleta, self)
        # Platito en la mano mientras come
        if self.estado == "comiendo":
            pygame.draw.rect(superficie, COLOR_PLATO,
                             (r.x + 2, r.y + 24, 18, 8))


class Proveedor(_Peaton):
    """El contacto del mercado negro. Aparece en la puerta del local
    cuando el negocio legal despega, espera a que Walter le hable (E)
    y después se va caminando hacia el sur."""

    COLOR_ABRIGO = (46, 40, 52)   # sobretodo oscuro con dejo violeta

    def __init__(self, x, y):
        super().__init__(x, y, self.COLOR_ABRIGO)
        self.paleta = paleta_encapuchado(self.COLOR_ABRIGO)
        self.estado = "esperando"  # esperando | yendose
        self.timer_salida = 10.0   # se esfuma aunque no llegue a destino

    def irse(self):
        self.estado = "yendose"

    def actualizar(self, dt):
        if self.estado == "yendose":
            # Camina hacia el sur por la calle y desaparece
            self._avanzar_hacia((self.rect.centerx, self.rect.centery + 800), dt)
            self.timer_salida -= dt
            if self.timer_salida <= 0:
                self.terminado = True

    def dibujar(self, superficie, camara):
        dibujar_personaje(superficie, camara.aplicar(self.rect),
                          self.paleta, self)


class VendedorZona(_Peaton):
    """Un vendedor de la Red en su puesto de trabajo. NO tiene rutina
    de movimiento: se queda parado en el punto de su base, esperando
    que Walter le traiga mercadería (E de cerca abre la entrega).
    El Flaco administra el Parque del Norte Y el Baldío del Mercado,
    pero físicamente solo se lo ve en el Baldío (su zona asignada)."""

    COLOR_CAMPERA = (38, 62, 58)   # verde petróleo, perfil bajo

    def __init__(self, x, y, vendedor):
        super().__init__(x, y, self.COLOR_CAMPERA)
        self.paleta = paleta_encapuchado(self.COLOR_CAMPERA)
        self.vendedor = vendedor   # el Vendedor (economy) que encarna
        self.estado = "trabajando"

    def actualizar(self, dt):
        pass   # estático: sin rutina entre zonas ni deambulo

    def puede_recibir(self, rect_jugador):
        """True si Walter está lo bastante cerca para entregarle."""
        return (pygame.Vector2(self.rect.center)
                .distance_to(rect_jugador.center) < DISTANCIA_COMPRA * 2)

    def dibujar(self, superficie, camara):
        dibujar_personaje(superficie, camara.aplicar(self.rect),
                          self.paleta, self)


class ContactoFlash(_Peaton):
    """El contacto de una oferta flash: espera parado en el punto
    con el cargamento hasta que Walter llegue (E para comprar) o se
    le acabe la paciencia (el timer lo maneja el GestorEventos)."""

    COLOR_CAMPERA = (96, 74, 40)   # marrón portuario

    def __init__(self, x, y):
        super().__init__(x, y, self.COLOR_CAMPERA)
        self.paleta = paleta_encapuchado(self.COLOR_CAMPERA)
        self.estado = "esperando"

    def actualizar(self, dt):
        pass   # clavado al lado de su cargamento

    def puede_vender(self, rect_jugador):
        return (pygame.Vector2(self.rect.center)
                .distance_to(rect_jugador.center) < DISTANCIA_COMPRA * 2)

    def dibujar(self, superficie, camara):
        dibujar_personaje(superficie, camara.aplicar(self.rect),
                          self.paleta, self)


class CompradorIlegal(_Peaton):
    """El comprador de un trato acordado por celular. Entra caminando
    al lugar de encuentro, espera ahí parado, y si Walter se le acerca
    con la mercadería el trato se cierra (tecla E). Si lo hacés
    esperar demasiado o hay lío, se va."""

    def __init__(self, x, y, punto_espera):
        super().__init__(x, y, COLOR_CAPUCHA)
        self.paleta = paleta_encapuchado(COLOR_CAPUCHA)
        self.origen = pygame.Vector2(x, y)
        self.punto_espera = pygame.Vector2(punto_espera)
        self.estado = "acercando"  # acercando | esperando | saliendo
        self.timer_seguridad = 420.0  # red de seguridad para despawnear

    def actualizar(self, dt):
        self.timer_seguridad -= dt
        if self.timer_seguridad <= 0:
            self.terminado = True
            return

        if self.estado == "acercando":
            if self._avanzar_hacia(self.punto_espera, dt) < 16:
                self.estado = "esperando"
        elif self.estado == "saliendo":
            if self._avanzar_hacia(self.origen, dt) < 12:
                self.terminado = True
        # "esperando": se queda parado mirando el reloj

    def puede_comprar(self, rect_jugador):
        """True si está esperando y Walter llegó hasta él."""
        return (self.estado == "esperando"
                and pygame.Vector2(self.rect.center)
                .distance_to(rect_jugador.center) < DISTANCIA_COMPRA * 2)

    def irse(self):
        if self.estado != "saliendo":
            self.estado = "saliendo"

    def dibujar(self, superficie, camara):
        dibujar_personaje(superficie, camara.aplicar(self.rect),
                          self.paleta, self)


class MozoNPC(_Peaton):
    """El empleado del mostrador (se contrata en la app Personal).
    Vive clavado detrás del mostrador y atiende la fila solo: cuando
    el primero de la cola llega a su lugar y hay comida lista, tras
    un momento devuelve "servido" y main.py concreta la venta
    (y le descuenta el sueldo a Walter)."""

    COLOR_DELANTAL = (210, 165, 80)   # amarillo mostaza
    SEGUNDOS_SERVIR = 1.2             # delay visual antes de servir

    def __init__(self):
        super().__init__(0, 0, self.COLOR_DELANTAL)
        # Su puesto: el frente de la fila, corrido detrás del
        # mostrador (que no parezca un cliente más)
        self.rect.center = (round(POSICIONES_FILA[0][0] - 40),
                            round(POSICIONES_FILA[0][1]))
        self.pos.update(self.rect.topleft)
        self.estado = "parado"   # parado | sirviendo
        self._timer_servir = 0.0

    def irse(self):
        pass   # un empleado no abandona el puesto (ni herido)

    def actualizar(self, dt, fila, producto_disponible):
        """Devuelve "servido" en el frame en que atendió al primero
        de la fila; si no hay a quién o qué servir, espera parado."""
        if (fila and producto_disponible > 0
                and fila[0].listo_para_atender(POSICIONES_FILA[0])):
            self.estado = "sirviendo"
            self._timer_servir += dt
            if self._timer_servir >= self.SEGUNDOS_SERVIR:
                self._timer_servir = 0.0
                return "servido"
        else:
            self.estado = "parado"
            self._timer_servir = 0.0
        return None

    def dibujar(self, superficie, camara):
        dibujar_personaje(superficie, camara.aplicar(self.rect),
                          self.paleta, self)


class ChefNPC(_Peaton):
    """El cocinero del local (requiere Mozo). Se para al lado de los
    hornos y, cuando hay fila y el contenedor tiene ingredientes,
    pone una tanda CLÁSICA al fuego (la receta especial es solo de
    Walter). Nunca toca el inventario de Walter: cocina únicamente
    con lo que haya en el contenedor."""

    COLOR_DELANTAL = (200, 90, 60)    # rojo ladrillo
    SEGUNDOS_VAIVEN = 0.8             # vaivén cosmético de ±6 px

    def __init__(self, x, y):
        super().__init__(x, y, self.COLOR_DELANTAL)
        self.rect.center = (round(x), round(y))
        self.pos.update(self.rect.topleft)
        self.estado = "idle"   # idle | cocinando
        self._timer_vaiven = 0.0
        self._vaiven_abajo = False

    def irse(self):
        pass   # clavado a sus hornos

    def actualizar(self, dt, produccion, economia, len_fila):
        """Devuelve "inicio_cocina" en el frame en que puso una tanda
        al fuego (los ingredientes salen del contenedor acá mismo)."""
        self._timer_vaiven += dt
        if self._timer_vaiven >= self.SEGUNDOS_VAIVEN:
            self._timer_vaiven = 0.0
            self._vaiven_abajo = not self._vaiven_abajo
        if produccion.en_curso:
            self.estado = "cocinando"
            return None
        self.estado = "idle"
        if (economia.contenedor_ing >= INGREDIENTES_POR_TANDA
                and len_fila > 0):
            economia.contenedor_ing -= INGREDIENTES_POR_TANDA
            produccion.iniciar_chef()
            return "inicio_cocina"
        return None

    def dibujar(self, superficie, camara):
        r = camara.aplicar(self.rect).move(
            0, 6 if self._vaiven_abajo else 0)
        dibujar_personaje(superficie, r, self.paleta, self)
        if self.estado == "cocinando":
            # Burbuja de vapor sobre la olla
            vapor = pygame.Surface((16, 16), pygame.SRCALPHA)
            vapor.fill((255, 255, 255, 178))
            superficie.blit(vapor, (r.centerx - 8, r.y - 20))


class RepositorNPC(_Peaton):
    """El repositor del local (requiere Chef). Espera al lado del
    contenedor y, cuando llega a la puerta una caja de SOLO
    ingredientes, sale a buscarla y la vuelca en el contenedor del
    Chef. Las cajas con insumos químicos (ziploc, semillas,
    compuestos) no las toca: esas son cosa de Walter. Entra y sale
    siempre por la puerta, como los clientes. Cobra por caja."""

    COLOR_DELANTAL = (80, 125, 170)   # celeste de repartidor

    def __init__(self, puesto, puerta):
        super().__init__(puesto[0], puesto[1], self.COLOR_DELANTAL)
        self.rect.center = (round(puesto[0]), round(puesto[1]))
        self.pos.update(self.rect.topleft)
        self.puesto = pygame.Vector2(puesto)
        self.puerta = pygame.Vector2(puerta)
        # esperando | yendo (a la caja) | volviendo (al contenedor)
        # | descargando (volcando lo que traía, si el contenedor
        # se llenó espera parado a que el Chef haga lugar)
        self.estado = "esperando"
        self.caja = None       # la caja que fue a buscar
        self.carga = 0         # ingredientes en brazos
        self._cruzo_puerta = False

    def irse(self):
        pass   # empleado: no abandona el puesto

    @staticmethod
    def _es_de_ingredientes(caja):
        return set(caja.contenido) == {"ingredientes"}

    def _elegir_caja(self, cajas, economia):
        """La primera caja de ingredientes cuyo contenido entra
        ENTERO en el contenedor (así nunca se pierde nada)."""
        for caja in cajas:
            if not self._es_de_ingredientes(caja):
                continue
            total = sum(caja.contenido.values())
            if economia.contenedor_ing + total <= MAX_CONTENEDOR:
                return caja
        return None

    def actualizar(self, dt, cajas, economia):
        """Devuelve "entrega" en el frame en que llega al contenedor
        con una caja (main.py le paga el sueldo ahí)."""
        if self.estado == "esperando":
            self.caja = self._elegir_caja(cajas, economia)
            if self.caja is not None:
                self.estado = "yendo"
                self._cruzo_puerta = False

        elif self.estado == "yendo":
            if self.caja not in cajas:
                # Walter la levantó primero: media vuelta
                self.caja = None
                self.estado = "volviendo"
                self._cruzo_puerta = False
            elif not self._cruzo_puerta:
                if self._avanzar_hacia(self.puerta, dt) < 20:
                    self._cruzo_puerta = True
            elif self._avanzar_hacia(self.caja.rect.center, dt) < 24:
                self.carga = sum(self.caja.contenido.values())
                cajas.remove(self.caja)
                self.caja = None
                self.estado = "volviendo"
                self._cruzo_puerta = False

        elif self.estado == "volviendo":
            if not self._cruzo_puerta:
                if self._avanzar_hacia(self.puerta, dt) < 20:
                    self._cruzo_puerta = True
            elif self._avanzar_hacia(self.puesto, dt) < 16:
                if self.carga > 0:
                    self.estado = "descargando"
                    return "entrega"
                self.estado = "esperando"

        elif self.estado == "descargando":
            lugar = MAX_CONTENEDOR - economia.contenedor_ing
            puesto = min(lugar, self.carga)
            economia.contenedor_ing += puesto
            self.carga -= puesto
            if self.carga <= 0:
                self.estado = "esperando"
        return None

    def dibujar(self, superficie, camara):
        r = camara.aplicar(self.rect)
        dibujar_personaje(superficie, r, self.paleta, self)
        # La caja en brazos mientras la lleva
        if self.carga > 0:
            caja = pygame.Rect(r.x + 2, r.y + 18, 32, 22)
            pygame.draw.rect(superficie, COLOR_CAJA, caja)
            pygame.draw.rect(superficie, COLOR_CAJA_CINTA,
                             (caja.centerx - 2, caja.y, 6, caja.height))


# ---------------------------------------------------------
# Ciudadanos: los vecinos que le dan vida a la ciudad
# ---------------------------------------------------------
class Ciudadano(_Peaton):
    """Vecino que pasea las 24hs por calles y caminos (tile a tile:
    jamás pisa un edificio). Se le puede OFRECER mercadería con E:
    decide si compra (paga más caro que un trato), si pasa de largo
    o si llama a la policía — esa resolución vive en main.py, acá
    solo está el paseo, el pánico y la marca de "ya le ofrecí"."""

    def __init__(self, col, fila):
        super().__init__(col * TILE + 8, fila * TILE + 4,
                         random.choice(COLORES_ROPA))
        self.estado = "pasear"          # pasear | huyendo
        self.tile = (col, fila)
        self.objetivo = None            # centro del próximo tile (px)
        self.direccion = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
        self.ya_ofrecido = False        # una sola oferta por persona
        self.timer_huida = 0.0

    def entrar_en_panico(self):
        if self.estado != "huyendo":
            self.estado = "huyendo"
            self.timer_huida = 4.0

    def _tile_caminable(self, mapa, col, fila):
        return (not mapa.es_solido_tile(col, fila)
                and mapa.chars[fila][col] in ".,")

    def _elegir_proximo(self, mapa):
        """El próximo tile del paseo: prefiere seguir derecho, evita
        pegar la vuelta (parece caminata de verdad, no ruido)."""
        col, fila = self.tile
        opciones, pesos = [], []
        reversa = (-self.direccion[0], -self.direccion[1])
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if not self._tile_caminable(mapa, col + d[0], fila + d[1]):
                continue
            opciones.append(d)
            pesos.append(6 if d == self.direccion
                         else (0.3 if d == reversa else 1.5))
        if not opciones:
            self.direccion = reversa
            return
        self.direccion = random.choices(opciones, weights=pesos)[0]
        c, f = col + self.direccion[0], fila + self.direccion[1]
        self.objetivo = pygame.Vector2(c * TILE + TILE // 2,
                                       f * TILE + TILE // 2)

    def actualizar(self, dt, mapa):
        if self.estado == "huyendo":
            self.timer_huida -= dt
            velocidad = VELOCIDAD_PANICO
            if self.timer_huida <= 0:
                self.estado = "pasear"
        else:
            velocidad = VELOCIDAD_PEATON * 0.75
        if self.objetivo is None:
            self._elegir_proximo(mapa)
            return
        # El hitbox camina con su CENTRO hacia el centro del tile
        hacia = self.objetivo - pygame.Vector2(self.rect.center)
        if hacia.length() < 8:
            self.tile = (int(self.objetivo.x) // TILE,
                         int(self.objetivo.y) // TILE)
            self.objetivo = None
            return
        paso = hacia.normalize() * velocidad * dt
        self.pos += paso
        self.rect.topleft = (round(self.pos.x), round(self.pos.y))

    def dibujar(self, superficie, camara):
        r = camara.aplicar(self.rect)
        dibujar_personaje(superficie, r, self.paleta, self)


def crear_ciudadanos(mapa, cantidad, lejos_de=None, radio_px=400):
    """Puebla la ciudad: ciudadanos en tiles exteriores al azar."""
    gente = []
    intentos = 0
    while len(gente) < cantidad and intentos < 600:
        intentos += 1
        col = random.randrange(mapa.columnas)
        fila = random.randrange(mapa.filas)
        if mapa.es_solido_tile(col, fila) or mapa.chars[fila][col] not in ".,":
            continue
        pos = (col * TILE, fila * TILE)
        if (lejos_de is not None and
                pygame.Vector2(pos).distance_to(lejos_de) < radio_px):
            continue
        gente.append(Ciudadano(col, fila))
    return gente


# ---------------------------------------------------------
# Tránsito: vehículos civiles que circulan por las calles
# ---------------------------------------------------------
class AutoNPC:
    """Vehículo civil: maneja por los tiles de CALLE ('.'), dobla al
    azar en las intersecciones y frena si Walter (o su vehículo) se
    le cruza adelante. Decorativo pero vivo — no atropella."""

    VELOCIDAD = 350
    DISTANCIA_FRENO = 116   # px: frena si el jugador está a menos

    def __init__(self, col, fila, tipo):
        self.tipo = tipo                       # "moto" | "auto" | "camioneta"
        self.pos = pygame.Vector2(col * TILE + TILE // 2,
                                  fila * TILE + TILE // 2)
        self.rect = pygame.Rect(0, 0, 68, 52)
        self.rect.center = self.pos
        self.direccion = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
        self.objetivo = None
        self.frenado = False

    @property
    def angulo(self):
        """Radianes de pantalla (0 = derecha, horario positivo)."""
        return math.atan2(self.direccion[1], self.direccion[0])

    def _es_calle(self, mapa, col, fila):
        return (not mapa.es_solido_tile(col, fila)
                and mapa.chars[fila][col] == ".")

    def _decidir_en_cruce(self, mapa):
        """Al entrar a un tile: sigue derecho casi siempre; en los
        cruces a veces dobla (nunca marcha atrás salvo sin salida)."""
        col = int(self.pos.x) // TILE
        fila = int(self.pos.y) // TILE
        reversa = (-self.direccion[0], -self.direccion[1])
        salidas = [d for d in ((1, 0), (-1, 0), (0, 1), (0, -1))
                   if d != reversa and self._es_calle(mapa, col + d[0],
                                                      fila + d[1])]
        if not salidas:
            self.direccion = reversa
        elif self.direccion in salidas and random.random() < 0.78:
            pass                                # sigue derecho
        else:
            self.direccion = random.choice(salidas)
        c, f = col + self.direccion[0], fila + self.direccion[1]
        self.objetivo = pygame.Vector2(c * TILE + TILE // 2,
                                       f * TILE + TILE // 2)

    def actualizar(self, dt, mapa, rect_jugador):
        if self.objetivo is None:
            self._decidir_en_cruce(mapa)
            if self.objetivo is None:
                return
        # Freno de cortesía: el jugador está adelante y cerca
        hacia_jugador = (pygame.Vector2(rect_jugador.center) - self.pos)
        self.frenado = (hacia_jugador.length() < self.DISTANCIA_FRENO
                        and hacia_jugador.dot(self.direccion) > 0)
        if self.frenado:
            return
        hacia = self.objetivo - self.pos
        if hacia.length() < 10:
            self._decidir_en_cruce(mapa)
            return
        self.pos += hacia.normalize() * self.VELOCIDAD * dt
        self.rect.center = (round(self.pos.x), round(self.pos.y))

    def dibujar(self, superficie, camara):
        r = camara.aplicar(self.rect)
        dibujar_vehiculo_conduciendo(superficie, self.tipo, r.center,
                                     self.angulo)


def crear_transito(mapa, cantidad, lejos_de=None, radio_px=500):
    """Los vehículos civiles, repartidos por las calles."""
    autos = []
    tipos = ["auto", "auto", "moto", "camioneta"]  # más autos que el resto
    intentos = 0
    while len(autos) < cantidad and intentos < 600:
        intentos += 1
        col = random.randrange(mapa.columnas)
        fila = random.randrange(mapa.filas)
        if mapa.es_solido_tile(col, fila) or mapa.chars[fila][col] != ".":
            continue
        pos = (col * TILE, fila * TILE)
        if (lejos_de is not None and
                pygame.Vector2(pos).distance_to(lejos_de) < radio_px):
            continue
        autos.append(AutoNPC(col, fila, random.choice(tipos)))
    return autos


# ---------------------------------------------------------
# El equipo del laboratorio (app Equipo del celular): la
# cadena clandestina del sótano. Los tres trabajan SOLO con
# el ESTANTE — jamás tocan el inventario de Walter.
# ---------------------------------------------------------
from .economy import (SUELDO_CONSEGUIDOR, SUELDO_QUIMICO,
                      SUELDO_EMPAQUETADOR)
from .crafting import (RECETAS_MESA, Sotano, SEGUNDOS_LABORATORIO,
                       SEGUNDOS_PLANTA)


class ConseguidorNPC(_Peaton):
    """El conseguidor: vigila el estante del sótano y cuando falta
    un insumo de medicamentos sale por la escalera, lo compra (paga
    el pedido + su comisión con la plata de Walter) y lo deja en el
    estante. Solo insumos del negocio: ziploc, semillas, compuestos."""

    COLOR_CAMPERA = (140, 110, 60)
    SEGUNDOS_COMPRA = 16.0    # cuánto tarda "afuera" comprando
    # (item a vigilar, mínimo, contenido que trae, costo, requiere)
    LISTA_COMPRAS = [
        ("compuestos", 4, {"compuestos": 4}, 120, "med_quim"),
        ("ziploc", 6, {"ziploc": 10}, 40, None),
        ("semillas", 4, {"semillas": 4}, 70, "med_nat"),
    ]

    def __init__(self, puesto, escalera):
        super().__init__(puesto[0], puesto[1], self.COLOR_CAMPERA)
        self.rect.center = (round(puesto[0]), round(puesto[1]))
        self.pos.update(self.rect.topleft)
        self.puesto = pygame.Vector2(puesto)
        self.escalera = pygame.Vector2(escalera)
        # esperando | saliendo | comprando | volviendo
        self.estado = "esperando"
        self.compra = None      # entrada de LISTA_COMPRAS en curso
        self.timer = 0.0

    def irse(self):
        pass   # empleado: no abandona el puesto

    def entrar_en_panico(self):
        pass   # ya vive al margen de la ley: no se asusta

    def _que_falta(self, estante, arbol):
        for item, minimo, contenido, costo, requiere in self.LISTA_COMPRAS:
            if requiere is not None and not arbol.desbloqueado(requiere):
                continue
            if estante.cantidad(item) < minimo:
                return (item, minimo, contenido, costo, requiere)
        return None

    def actualizar(self, dt, estante, economia, arbol):
        """Devuelve ("compra", item, costo) al pagar el pedido, o
        ("repuesto", item) al dejarlo en el estante; None si no."""
        if self.estado == "esperando":
            compra = self._que_falta(estante, arbol)
            if compra is None:
                return None
            costo = compra[3] + SUELDO_CONSEGUIDOR
            if not economia.pagar(costo):
                return None      # sin plata: sigue esperando
            self.compra = compra
            self.estado = "saliendo"
            return ("compra", compra[0], costo)

        elif self.estado == "saliendo":
            if self._avanzar_hacia(self.escalera, dt) < 20:
                self.estado = "comprando"
                self.timer = self.SEGUNDOS_COMPRA

        elif self.estado == "comprando":
            self.timer -= dt
            if self.timer <= 0:
                self.estado = "volviendo"

        elif self.estado == "volviendo":
            if self._avanzar_hacia(self.puesto, dt) < 16:
                item = self.compra[0]
                for id_item, n in self.compra[2].items():
                    estante.agregar(id_item, n)
                self.compra = None
                self.estado = "esperando"
                return ("repuesto", item)
        return None

    def dibujar(self, superficie, camara):
        r = camara.aplicar(self.rect)
        dibujar_personaje(superficie, r, self.paleta, self)
        if self.estado == "volviendo":
            caja = pygame.Rect(r.x + 2, r.y + 18, 32, 22)
            pygame.draw.rect(superficie, COLOR_CAJA, caja)
            pygame.draw.rect(superficie, COLOR_CAJA_CINTA,
                             (caja.centerx - 2, caja.y, 6, caja.height))


class QuimicoNPC(_Peaton):
    """El químico: se lleva TODO lo producible del estante de una
    sola vez y pone CADA COSA EN SU LUGAR — siembra las semillas en
    la maceta, carga los compuestos en la hornalla — y no se queda
    parado mirando la olla: vuelve a su puesto junto al estante
    mientras las estaciones trabajan solas. Cuando el lote entero
    terminó, pasa a RECOGER por cada estación y deja toda la
    producción junta en el estante. Sufre y goza los mismos efectos
    del árbol que el laboratorio (velocidad, tandas falladas,
    insumo perdonado, Fertilizante)."""

    COLOR_DELANTAL = (120, 70, 160)   # violeta de químico

    def __init__(self, puesto, puesto_lab, puesto_maceta=None):
        super().__init__(puesto[0], puesto[1], self.COLOR_DELANTAL)
        self.rect.center = (round(puesto[0]), round(puesto[1]))
        self.pos.update(self.rect.topleft)
        self.puesto = pygame.Vector2(puesto)
        self.puesto_lab = pygame.Vector2(puesto_lab)
        self.puesto_maceta = pygame.Vector2(puesto_maceta or puesto_lab)
        # esperando | sembrando | cargando | aguardando |
        # recoger_maceta | recoger_lab | volviendo
        self.estado = "esperando"
        self.timer_lab = None      # None = la hornalla está vacía
        self.timer_maceta = None   # None = la maceta está vacía
        self.lote_compuestos = 0   # compuestos que se llevó
        self.lote_semillas = 0     # semillas que se llevó
        self.devolver = 0          # compuestos perdonados (Purificador)
        self.crudos = 0            # resultado del lote
        self.fallos = 0
        self.en_brazos = False     # ya recogió (para el dibujito)

    def irse(self):
        pass

    def entrar_en_panico(self):
        pass

    def actualizar(self, dt, estante, economia, arbol):
        """Devuelve ("lote", crudos, fallos, plantas) al volcar el
        lote terminado en el estante; None si no pasó nada."""
        # Las estaciones trabajan SOLAS, camine él donde camine
        if self.timer_maceta is not None and self.timer_maceta > 0:
            self.timer_maceta = max(0.0, self.timer_maceta - dt)
        if self.timer_lab is not None and self.timer_lab > 0:
            self.timer_lab = max(0.0, self.timer_lab - dt)

        if self.estado == "esperando":
            if economia.dinero < SUELDO_QUIMICO:
                return None
            comp = (estante.cantidad("compuestos")
                    if arbol.desbloqueado("med_quim") else 0)
            sem = estante.cantidad("semillas")
            if comp == 0 and sem == 0:
                return None
            # Se lleva TODO de una: nada de viajar de a uno
            if comp:
                estante.quitar("compuestos", comp)
            if sem:
                estante.quitar("semillas", sem)
            self.lote_compuestos = comp
            self.lote_semillas = sem
            # El Purificador de Mermas perdona algunos compuestos:
            # esos vuelven al estante junto con el lote
            self.devolver = sum(
                1 for _ in range(comp)
                if random.random() < arbol.prob_insumos_gratis("med_quim"))
            self.en_brazos = True     # sale cargado de insumos
            self.estado = "sembrando" if sem else "cargando"

        elif self.estado == "sembrando":
            # Primera parada: las semillas a la maceta
            if self._avanzar_hacia(self.puesto_maceta, dt) < 16:
                self.timer_maceta = (SEGUNDOS_PLANTA
                                     * arbol.mult_tiempo_maceta())
                self.estado = ("cargando" if self.lote_compuestos
                               else "aguardando")
                if self.estado == "aguardando":
                    self.en_brazos = False

        elif self.estado == "cargando":
            # Segunda parada: los compuestos a la hornalla
            if self._avanzar_hacia(self.puesto_lab, dt) < 16:
                self.timer_lab = (SEGUNDOS_LABORATORIO
                                  * arbol.mult_tiempo_lab())
                # Cada compuesto corre su propio riesgo de fallar
                self.fallos = sum(
                    1 for _ in range(self.lote_compuestos)
                    if random.random() < arbol.prob_fallo_lab())
                self.crudos = self.lote_compuestos - self.fallos
                self.en_brazos = False
                self.estado = "aguardando"

        elif self.estado == "aguardando":
            # De vuelta a su puesto MIENTRAS las estaciones trabajan
            self._avanzar_hacia(self.puesto, dt)
            maceta_lista = self.timer_maceta is None or self.timer_maceta <= 0
            lab_listo = self.timer_lab is None or self.timer_lab <= 0
            if maceta_lista and lab_listo:
                if self.timer_maceta is not None:
                    self.estado = "recoger_maceta"
                elif self.timer_lab is not None:
                    self.estado = "recoger_lab"
                else:
                    self.estado = "volviendo"

        elif self.estado == "recoger_maceta":
            # A cosechar las plantas
            if self._avanzar_hacia(self.puesto_maceta, dt) < 16:
                self.timer_maceta = None
                self.en_brazos = True
                self.estado = ("recoger_lab" if self.timer_lab is not None
                               else "volviendo")

        elif self.estado == "recoger_lab":
            # A retirar los crudos de la hornalla
            if self._avanzar_hacia(self.puesto_lab, dt) < 16:
                self.timer_lab = None
                self.en_brazos = True
                self.estado = "volviendo"

        elif self.estado == "volviendo":
            if self._avanzar_hacia(self.puesto, dt) < 16:
                if self.crudos:
                    estante.agregar("quimico_crudo", self.crudos)
                if self.lote_semillas:
                    estante.agregar("planta", self.lote_semillas)
                if self.devolver:
                    estante.agregar("compuestos", self.devolver)
                resultado = ("lote", self.crudos, self.fallos,
                             self.lote_semillas)
                self.lote_compuestos = self.lote_semillas = 0
                self.crudos = self.fallos = self.devolver = 0
                self.en_brazos = False
                self.estado = "esperando"
                economia.dinero -= SUELDO_QUIMICO
                return resultado
        return None

    def dibujar(self, superficie, camara):
        r = camara.aplicar(self.rect)
        dibujar_personaje(superficie, r, self.paleta, self)
        if self.en_brazos:
            # La bandeja con el lote (insumos o producción)
            caja = pygame.Rect(r.x + 2, r.y + 18, 32, 18)
            pygame.draw.rect(superficie, (150, 110, 190), caja)
            pygame.draw.rect(superficie, (100, 70, 140), caja, 2)


class EmpaquetadorNPC(_Peaton):
    """El empaquetador: se lleva del estante TODO lo empaquetable de
    una sola vez (plantas, químico crudo y bolsas ziploc), lo va
    embolsando en la mesa de a uno a medida que sale, y cuando el
    lote entero está listo vuelve con todos los medicamentos
    TERMINADOS al estante. Arma siempre el mejor tier que el estante
    pueda pagar (como la mesa)."""

    COLOR_DELANTAL = (70, 120, 120)   # verde agua de operario
    SEGUNDOS_EMPAQUE = 6.0

    def __init__(self, puesto, puesto_mesa):
        super().__init__(puesto[0], puesto[1], self.COLOR_DELANTAL)
        self.rect.center = (round(puesto[0]), round(puesto[1]))
        self.pos.update(self.rect.topleft)
        self.puesto = pygame.Vector2(puesto)
        self.puesto_mesa = pygame.Vector2(puesto_mesa)
        # esperando | yendo | empaquetando | volviendo
        self.estado = "esperando"
        self.timer = 0.0
        self.cola = []         # productos pendientes del lote
        self.hechos = []       # (producto, unidades) ya embolsados
        self.perdonados = []   # recetas cuyos insumos se perdonaron

    def irse(self):
        pass

    def entrar_en_panico(self):
        pass

    def _armar_cola(self, estante, arbol):
        """Se lleva del estante TODO lo empaquetable de una sola vez:
        va reservando recetas (el mejor tier primero, como la mesa)
        hasta que no queda nada armable. Devuelve la lista de
        productos a empaquetar; los insumos ya salieron del estante
        (con Cultivo Abundante / Purificador algunos se perdonan y
        vuelven al final del viaje)."""
        cola = []
        while len(cola) < 20:      # tope sano por viaje
            for prod, receta in RECETAS_MESA:
                if not arbol.desbloqueado(prod):
                    continue
                if all(estante.tiene(i, n) for i, n in receta.items()):
                    gratis = (random.random()
                              < arbol.prob_insumos_gratis(prod))
                    if not gratis:
                        for i, n in receta.items():
                            estante.quitar(i, n)
                    else:
                        self.perdonados.append(dict(receta))
                    cola.append(prod)
                    break
            else:
                break
        return cola

    def actualizar(self, dt, estante, economia, arbol):
        """Devuelve ("lote", unidades) al volcar el lote terminado
        en el estante; None si no pasó nada."""
        if self.estado == "esperando":
            if economia.dinero < SUELDO_EMPAQUETADOR:
                return None
            self.perdonados = []
            self.cola = self._armar_cola(estante, arbol)
            if not self.cola:
                return None
            self.hechos = []       # productos ya empaquetados
            self.estado = "yendo"

        elif self.estado == "yendo":
            if self._avanzar_hacia(self.puesto_mesa, dt) < 16:
                self.timer = self.SEGUNDOS_EMPAQUE
                self.estado = "empaquetando"

        elif self.estado == "empaquetando":
            # Va embolsando la cola de a uno, a medida que salen
            self.timer -= dt
            if self.timer <= 0:
                prod = self.cola.pop(0)
                doble = random.random() < arbol.prob_unidad_extra(prod)
                self.hechos.append((prod, 2 if doble else 1))
                if self.cola:
                    self.timer = self.SEGUNDOS_EMPAQUE
                else:
                    self.estado = "volviendo"

        elif self.estado == "volviendo":
            if self._avanzar_hacia(self.puesto, dt) < 16:
                unidades = 0
                paquetes = len(self.hechos)
                for prod, n in self.hechos:
                    estante.agregar(prod, n)
                    unidades += n
                # Los insumos perdonados por las habilidades vuelven
                for receta in self.perdonados:
                    for i, n in receta.items():
                        estante.agregar(i, n)
                economia.dinero -= SUELDO_EMPAQUETADOR * paquetes
                self.hechos = []
                self.perdonados = []
                self.estado = "esperando"
                if unidades:
                    return ("lote", unidades, paquetes)
        return None

    def dibujar(self, superficie, camara):
        r = camara.aplicar(self.rect)
        dibujar_personaje(superficie, r, self.paleta, self)
        if self.estado == "empaquetando":
            bolsa = pygame.Rect(r.x + 4, r.y + 16, 22, 26)
            pygame.draw.rect(superficie, (188, 200, 210), bolsa)
            pygame.draw.rect(superficie, (240, 210, 80),
                             (bolsa.x, bolsa.y, bolsa.width, 5))
