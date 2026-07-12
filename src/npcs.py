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

from .economy import INGREDIENTES_POR_TANDA, MAX_CONTENEDOR
from .map import POSICIONES_FILA
from .settings import COLOR_CAJA, COLOR_CAJA_CINTA
from .sprites import paleta_peaton, paleta_encapuchado, dibujar_personaje

VELOCIDAD_PEATON = 85        # px/s, más lento que Walter
VELOCIDAD_PANICO = 150       # px/s huyendo
SEGUNDOS_COMIENDO = 5.0
PACIENCIA_FILA = 30.0        # segundos antes de irse sin comprar
DISTANCIA_COMPRA = 30        # px al comprador para concretar el trato
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
        self.rect = pygame.Rect(int(x), int(y), 18, 24)
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
        """Da un paso hacia el destino y devuelve la distancia restante."""
        hacia = pygame.Vector2(destino) - pygame.Vector2(self.rect.center)
        distancia = hacia.length()
        if distancia > 1:
            self.pos += hacia.normalize() * velocidad * dt
            self.rect.topleft = (round(self.pos.x), round(self.pos.y))
        return distancia

    def _dibujar_cuerpo(self, superficie, r, color_cabeza=COLOR_PIEL):
        pygame.draw.rect(superficie, self.color_ropa,
                         (r.x, r.y + 7, r.width, r.height - 7))
        pygame.draw.rect(superficie, color_cabeza,
                         (r.x + 4, r.y, r.width - 8, 9))


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
            if self._avanzar_hacia(self.salida, dt, VELOCIDAD_PANICO) < 12:
                self.terminado = True
            return None

        if self.estado == "entrando":
            if self._avanzar_hacia(self.frente_puerta, dt) < 10:
                self.estado = "cruzando"
        elif self.estado == "cruzando":
            if self._avanzar_hacia(self.puerta, dt) < 10:
                self.estado = "cola"

        elif self.estado == "cola":
            if self.objetivo is not None:
                self._avanzar_hacia(self.objetivo, dt)
            self.paciencia -= dt
            if self.paciencia <= 0:
                self.irse()
                return "harto"

        elif self.estado == "comiendo":
            if self._avanzar_hacia(self.lugar, dt) < 6:
                self.timer_comer -= dt
                if self.timer_comer <= 0:
                    self.irse()

        elif self.estado == "saliendo":  # hacia la puerta desde adentro
            if self._avanzar_hacia(self.puerta, dt) < 12:
                self.estado = "yendose"
        elif self.estado == "yendose":   # cruzar el vano hacia la vereda
            if self._avanzar_hacia(self.frente_puerta, dt) < 10:
                self.estado = "yendose2"
        else:  # yendose2: por la calle hasta desaparecer
            if self._avanzar_hacia(self.salida, dt) < 10:
                self.terminado = True
        return None

    def listo_para_atender(self, posicion_frente):
        """True si está primero en la fila, quieto frente al mostrador."""
        return (self.estado == "cola" and
                pygame.Vector2(self.rect.center).distance_to(posicion_frente) < 24)

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
                             (r.x + 1, r.y + 12, 9, 4))


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
            self._avanzar_hacia((self.rect.centerx, self.rect.centery + 400), dt)
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
            if self._avanzar_hacia(self.punto_espera, dt) < 8:
                self.estado = "esperando"
        elif self.estado == "saliendo":
            if self._avanzar_hacia(self.origen, dt) < 6:
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
        self.rect.center = (round(POSICIONES_FILA[0][0] - 20),
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
    SEGUNDOS_VAIVEN = 0.8             # vaivén cosmético de ±3 px

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
            0, 3 if self._vaiven_abajo else 0)
        dibujar_personaje(superficie, r, self.paleta, self)
        if self.estado == "cocinando":
            # Burbuja de vapor sobre la olla
            vapor = pygame.Surface((8, 8), pygame.SRCALPHA)
            vapor.fill((255, 255, 255, 178))
            superficie.blit(vapor, (r.centerx - 4, r.y - 10))


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
                if self._avanzar_hacia(self.puerta, dt) < 10:
                    self._cruzo_puerta = True
            elif self._avanzar_hacia(self.caja.rect.center, dt) < 12:
                self.carga = sum(self.caja.contenido.values())
                cajas.remove(self.caja)
                self.caja = None
                self.estado = "volviendo"
                self._cruzo_puerta = False

        elif self.estado == "volviendo":
            if not self._cruzo_puerta:
                if self._avanzar_hacia(self.puerta, dt) < 10:
                    self._cruzo_puerta = True
            elif self._avanzar_hacia(self.puesto, dt) < 8:
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
            caja = pygame.Rect(r.x + 1, r.y + 9, 16, 11)
            pygame.draw.rect(superficie, COLOR_CAJA, caja)
            pygame.draw.rect(superficie, COLOR_CAJA_CINTA,
                             (caja.centerx - 1, caja.y, 3, caja.height))
