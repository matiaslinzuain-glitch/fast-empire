# =========================================================
# FAST EMPIRE — Punto de entrada  [Fase 5]
# Progresión y calidad de vida sobre la Fase 4:
# - Arrancás SOLO con la comida rápida: los medicamentos se
#   desbloquean cuando el local factura lo suficiente y "un
#   proveedor" te contacta.
# - Los inspectores ya no viven en el mapa: llegan cuando hay
#   denuncias (vender ilegal, tiros, muertes) y se retiran
#   cuando la búsqueda vuelve a cero.
# - Árbol de habilidades (tecla T): 4 ramas, puntos + dinero.
# - El panel de recursos se oculta/muestra con TAB.
# - Todos los menús se manejan también con el mouse.
#
# Estados: menu · opciones · jugando · pausa · tienda ·
#          pedidos · habilidades
#
# Ejecutar desde esta carpeta:  python3 main.py
# =========================================================

import random

import pygame

from src.settings import (
    ANCHO_VENTANA, ALTO_VENTANA, FPS, TITULO, TILE,
    POSICION_INICIAL, VELOCIDAD_JUGADOR, COLOR_FONDO,
    COLOR_ORO, COLOR_DINERO, COLOR_ERROR,
    COLOR_PUNTO, COLOR_CONO, COLOR_CONO_ALERTA,
    CADENCIA_PISTOLA, VELOCIDAD_BALA,
    DANO_GOLPE, ALCANCE_GOLPE, CADENCIA_GOLPE,
    DISPERSION_CADERA, DISPERSION_APUNTADO,
)
from src.map import (
    Mapa, PUNTO_PUERTA, PUNTO_ENTREGA, POSICIONES_FILA,
    LUGARES_COMER, ENTRADAS_CLIENTES,
)
from src.player import Jugador
from src.camera import Camara
from src.economy import (
    Economia, Produccion, Caja, PuntoIlegal, crear_franquicias,
    PEDIDOS, TIEMPO_ENTREGA, INGREDIENTES_POR_TANDA, NOMBRE_MED,
    PUNTOS_POR_RIVAL, PUNTOS_POR_ESCAPE, UMBRAL_DESBLOQUEO_MEDS,
    INGRESO_FRANQUICIA, INTERVALO_FRANQUICIA, PRECIO_CURACION,
    DATOS_FRANQUICIAS,
)
from src.npcs import ClienteLocal, CompradorIlegal, Proveedor
from src.dialogue import CajaDialogo
from src.audio import Audio
from src.enemies import (
    Busqueda, Proyectil, RivalGastronomico,
    crear_inspectores, crear_rivales,
)
from src.skills import Habilidades
from src.ui import (
    HUD, TextoFlotante,
    MenuPrincipal, PantallaOpciones, MenuPausa,
    PantallaTienda, PantallaPedidos, PantallaHabilidades, PantallaBanco,
    PantallaCocina,
)

# Nombres legibles de las zonas (para las misiones de limpieza)
NOMBRES_ZONA = {datos[0]: datos[1] for datos in DATOS_FRANQUICIAS}

# Radio (en píxeles) para interactuar con E
RADIO_INTERACCION = TILE * 2
# Distancia a la que los inspectores escuchan un disparo
ALCANCE_RUIDO_DISPARO = 340
RESPAWN_RIVAL = 60
DURACION_AVISO = 2.6
MAX_COMPRADORES = 3       # compradores simultáneos en el punto
SEGUNDOS_RETIRADA = 8.0   # con búsqueda en 0, los inspectores se van


class Juego:
    def __init__(self):
        # El mixer se configura ANTES de pygame.init (16-bit mono)
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        self.pantalla_completa = False
        # SCALED mantiene la resolución lógica 800x600 y la estira a la
        # pantalla; el mouse se traduce solo. Fallback por si no existe.
        try:
            self.pantalla = pygame.display.set_mode(
                (ANCHO_VENTANA, ALTO_VENTANA), pygame.SCALED)
        except pygame.error:
            self.pantalla = pygame.display.set_mode((ANCHO_VENTANA, ALTO_VENTANA))
        pygame.display.set_caption(TITULO)
        self.audio = Audio()
        self.audio.iniciar_musica()
        self.reloj = pygame.time.Clock()
        self.corriendo = True
        self.estado = "menu"

        # Pantallas de UI (viven todo el juego)
        self.menu = MenuPrincipal()
        self.opciones = PantallaOpciones()
        self.pausa = MenuPausa()
        self.tienda = PantallaTienda()
        self.telefono = PantallaPedidos()
        self.arbol = PantallaHabilidades()
        self.dialogo = CajaDialogo()
        self.banco_ui = PantallaBanco()
        self.cocina_ui = PantallaCocina()
        self.hud = HUD()
        self.fuente_mundo = pygame.font.Font(None, 22)
        self.capa_conos = pygame.Surface((ANCHO_VENTANA, ALTO_VENTANA), pygame.SRCALPHA)
        self.mostrar_panel = True   # TAB lo alterna
        # Modo debug (menú principal): atravesar paredes.
        # Vive en Juego, no en nueva_partida: sobrevive a las partidas.
        self.debug = False

        self.nueva_partida()

    # -----------------------------------------------------
    # Ciclo de vida
    # -----------------------------------------------------
    def nueva_partida(self):
        """Crea (o recrea) el mundo desde cero."""
        self.mapa = Mapa()
        self.jugador = Jugador(*POSICION_INICIAL)
        self.camara = Camara(self.mapa.ancho_px, self.mapa.alto_px)
        self.economia = Economia()
        self.produccion = Produccion()
        self.habilidades = Habilidades()
        self.textos = []

        # El local
        self.fila = []                # ClienteLocal esperando (en orden)
        self.comensales = []          # ClienteLocal comiendo o saliendo
        self.timer_cliente = 4.0
        self.pedidos = []             # {"id", "timer"} en camino
        self.cajas = []               # Caja esperando en la puerta

        # El negocio ilegal (dormido hasta charlar con el Proveedor)
        self.punto = PuntoIlegal()
        self.compradores = []
        self.proveedor = None          # el NPC, cuando viene de visita
        self.proveedor_visito = False  # ya apareció alguna vez
        self.proveedor_motivo = "intro"  # o "mision"

        # Misiones del Proveedor
        self.mision = None             # la activa (dict) o None
        self.misiones_cumplidas = 0
        self.timer_oferta = 45.0       # próxima visita con trabajo

        # Franquicias (territorio con ingreso pasivo)
        self.franquicias = crear_franquicias()
        self.timer_franquicia = INTERVALO_FRANQUICIA

        # Ley y competencia: SIN inspectores hasta que haya denuncias
        self.busqueda = Busqueda()
        self.inspectores = []
        self.timer_retirada = 0.0
        self.pos_infraccion = None    # dónde fue la última denuncia
        self.rivales = crear_rivales()
        self.proyectiles = []
        self.respawns = []            # solo rivales
        self.habia_persecucion = False
        self.aviso = None
        self.aviso_timer = 0.0

    def ejecutar(self):
        while self.corriendo:
            dt = self.reloj.tick(FPS) / 1000.0
            for evento in pygame.event.get():
                self._manejar_evento(evento)
            if self.estado == "jugando":
                self._actualizar_jugando(dt)
            elif self.estado == "dialogo":
                self.dialogo.actualizar(dt)  # efecto máquina de escribir
            self._dibujar()
            pygame.display.flip()
        pygame.quit()

    # -----------------------------------------------------
    # Eventos (según estado)
    # -----------------------------------------------------
    def _manejar_evento(self, evento):
        if evento.type == pygame.QUIT:
            self.corriendo = False
            return
        # Pantalla completa desde cualquier estado: Cmd+F (Mac) o F11.
        # En macOS F11 suele estar tomado por el sistema, por eso Cmd+F
        # y las opciones en los menús de pausa y Opciones.
        if evento.type == pygame.KEYDOWN and (
                evento.key == pygame.K_F11
                or (evento.key == pygame.K_f and evento.mod & pygame.KMOD_META)):
            self._alternar_pantalla_completa()
            return
        # F1: modo debug desde cualquier lado (también está en los menús)
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_F1:
            self._alternar_debug()
            return

        # Sonidos de interfaz: click en menús, blip en diálogos
        if self.estado != "jugando" and (
                (evento.type == pygame.KEYDOWN and evento.key in (
                    pygame.K_RETURN, pygame.K_e, pygame.K_SPACE))
                or (evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1)):
            self.audio.reproducir(
                "hablar" if self.estado == "dialogo" else "click")

        if self.estado == "menu":
            accion = self.menu.manejar_evento(evento)
            if accion == "Jugar":
                self.nueva_partida()
                self.estado = "jugando"
            elif accion == "Opciones":
                self.opciones.refrescar(self.audio, self.pantalla_completa)
                self.estado = "opciones"
            elif accion == "debug":
                self._alternar_debug()
            elif accion == "Salir":
                self.corriendo = False

        elif self.estado == "opciones":
            accion = self.opciones.manejar_evento(evento)
            if accion == "volver":
                self.estado = "menu"
            elif accion == "sonido":
                self.audio.ciclar_volumen()
            elif accion == "musica":
                self.audio.alternar_musica()
            elif accion == "fullscreen":
                self._alternar_pantalla_completa()
            if accion in ("sonido", "musica", "fullscreen"):
                self.opciones.refrescar(self.audio, self.pantalla_completa)

        elif self.estado == "jugando":
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    self.estado = "pausa"
                elif evento.key == pygame.K_e:
                    self._interactuar()
                elif evento.key == pygame.K_t:
                    self.arbol.abrir()
                    self.estado = "habilidades"
                elif evento.key == pygame.K_TAB:
                    self.mostrar_panel = not self.mostrar_panel
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                self._atacar()

        elif self.estado == "pausa":
            accion = self.pausa.manejar_evento(evento)
            if accion == "Continuar":
                self.estado = "jugando"
            elif accion == "Pantalla completa":
                self._alternar_pantalla_completa()
            elif accion == "debug":
                self._alternar_debug()
            elif accion == "Menú principal":
                self.estado = "menu"

        elif self.estado == "tienda":
            accion = self.tienda.manejar_evento(evento, self.economia, self.jugador)
            if accion == "cerrar":
                self.estado = "jugando"
            elif accion == "charlar":
                self.dialogo.abrir("almacenero")
                self.estado = "dialogo"

        elif self.estado == "pedidos":
            accion = self.telefono.manejar_evento(evento, self.economia)
            if accion == "cerrar":
                self.estado = "jugando"
            elif isinstance(accion, tuple) and accion[0] == "pedido":
                self.pedidos.append({"id": accion[1], "timer": TIEMPO_ENTREGA})

        elif self.estado == "habilidades":
            accion = self.arbol.manejar_evento(
                evento, self.economia, self.habilidades, self.jugador)
            if accion == "cerrar":
                self.estado = "jugando"

        elif self.estado == "dialogo":
            if self.dialogo.manejar_evento(evento) == "fin":
                self.estado = "jugando"
                self._fin_dialogo(self.dialogo.id_actual)

        elif self.estado == "banco":
            if self.banco_ui.manejar_evento(evento, self.economia) == "cerrar":
                self.estado = "jugando"

        elif self.estado == "cocina":
            accion = self.cocina_ui.manejar_evento(evento, self.economia)
            if accion == "cerrar":
                self.estado = "jugando"
            elif isinstance(accion, tuple) and accion[0] == "cocinar":
                if self.produccion.iniciar(self.economia, accion[1]):
                    self.estado = "jugando"

    def _alternar_debug(self):
        """Prende/apaga el noclip y sincroniza las etiquetas de los
        menús. Se llama desde F1, el menú principal y la pausa."""
        self.debug = not self.debug
        self.menu.refrescar_debug(self.debug)
        self.pausa.refrescar_debug(self.debug)
        if self.estado == "jugando":
            self._texto_sobre_jugador(
                "Debug " + ("ACTIVADO" if self.debug else "desactivado"),
                COLOR_ERROR if self.debug else COLOR_ORO)

    def _alternar_pantalla_completa(self):
        """Recrea la ventana con o sin FULLSCREEN. Más confiable que
        toggle_fullscreen(), sobre todo en macOS. Si algún modo no
        está disponible, degrada hasta la ventana simple."""
        self.pantalla_completa = not self.pantalla_completa
        flags = pygame.SCALED | (pygame.FULLSCREEN if self.pantalla_completa else 0)
        try:
            self.pantalla = pygame.display.set_mode(
                (ANCHO_VENTANA, ALTO_VENTANA), flags)
        except pygame.error:
            self.pantalla_completa = False
            try:
                self.pantalla = pygame.display.set_mode(
                    (ANCHO_VENTANA, ALTO_VENTANA), pygame.SCALED)
            except pygame.error:
                self.pantalla = pygame.display.set_mode(
                    (ANCHO_VENTANA, ALTO_VENTANA))

    def _fin_dialogo(self, id_dialogo):
        """Efectos al cerrar cada conversación."""
        if id_dialogo == "proveedor_intro":
            self.economia.meds_desbloqueados = True
            self.aviso = ("NEGOCIO ABIERTO",
                          "Medicamentos en el teléfono — seguí la marca violeta")
            self.aviso_timer = 3.2
            if self.proveedor is not None:
                self.proveedor.irse()
        elif id_dialogo == "proveedor_mision":
            self.mision = self._generar_mision()
            self.aviso = ("MISIÓN", self.mision["desc"]
                          + f" — recompensa ${self.mision['recompensa']}")
            self.aviso_timer = 3.2
            if self.proveedor is not None:
                self.proveedor.irse()
        elif id_dialogo == "proveedor_receta":
            self.economia.receta_especial = True
            self.aviso = ("RECETA ESPECIAL",
                          "Nueva receta en la cocina: platos premium")
            self.aviso_timer = 3.5
            if self.proveedor is not None:
                self.proveedor.irse()

    # -----------------------------------------------------
    # Misiones del Proveedor
    # -----------------------------------------------------
    def _generar_mision(self):
        """Arma una misión al azar según el estado del mundo."""
        tipos = ["reparto", "quimicos"]
        zonas_vivas = [r.zona_id for r in self.rivales if r.zona_id]
        if zonas_vivas:
            tipos.append("limpieza")
        tipo = random.choice(tipos)
        if tipo == "reparto":
            n = random.randint(3, 5)
            return {"tipo": tipo, "objetivo": n, "progreso": 0,
                    "timer": 60 + 30 * n, "recompensa": 30 * n, "puntos": n,
                    "desc": f"Vendé {n} medicamentos en el punto"}
        if tipo == "quimicos":
            n = random.randint(2, 4)
            return {"tipo": tipo, "objetivo": n, "progreso": 0,
                    "timer": 60 + 35 * n, "recompensa": 55 * n, "puntos": 2 * n,
                    "desc": f"Vendé {n} medicamentos QUÍMICOS"}
        zona = random.choice(zonas_vivas)
        return {"tipo": "limpieza", "zona": zona, "objetivo": 1, "progreso": 0,
                "timer": 120, "recompensa": 200, "puntos": 8,
                "desc": f"Eliminá al rival de {NOMBRES_ZONA[zona]}"}

    def _avanzar_mision(self, cantidad=1):
        """Suma progreso y resuelve la misión si se completó."""
        self.mision["progreso"] += cantidad
        if self.mision["progreso"] < self.mision["objetivo"]:
            return
        mision = self.mision
        self.mision = None
        self.timer_oferta = random.uniform(50.0, 90.0)
        self.misiones_cumplidas += 1
        self.economia.dinero += mision["recompensa"]
        self.economia.puntos += mision["puntos"]
        self.audio.reproducir("cocinado")
        self.aviso = ("MISIÓN CUMPLIDA",
                      f"+${mision['recompensa']} y +{mision['puntos']} puntos")
        self.aviso_timer = 3.0
        # La primera misión cumplida paga con la Receta Especial:
        # el Proveedor vuelve en persona a enseñártela
        if self.misiones_cumplidas == 1 and not self.economia.receta_especial:
            self.proveedor = Proveedor(8.5 * TILE, 9.4 * TILE)
            self.proveedor_motivo = "receta"
            self._texto_sobre_jugador(
                "El Proveedor te espera en la puerta con algo…", COLOR_PUNTO)

    def _actualizar_mision(self, dt):
        """Reloj de la misión activa y visitas del Proveedor."""
        if self.mision is not None:
            self.mision["timer"] -= dt
            if self.mision["timer"] <= 0:
                self.mision = None
                self.timer_oferta = random.uniform(80.0, 120.0)
                self.audio.reproducir("error")
                self._texto_sobre_jugador(
                    "Misión fallida — el Proveedor no está contento",
                    COLOR_ERROR)
            return
        # Sin misión activa: cada tanto vuelve con un trabajo
        if (self.economia.meds_desbloqueados and self.proveedor is None):
            self.timer_oferta -= dt
            if self.timer_oferta <= 0:
                self.proveedor = Proveedor(8.5 * TILE, 9.4 * TILE)
                self.proveedor.timer_espera_oferta = 35.0
                self.proveedor_motivo = "mision"
                self._texto_sobre_jugador(
                    "El Proveedor volvió — tiene un trabajo", COLOR_PUNTO)

    # -----------------------------------------------------
    # Interacción con E (en orden de prioridad)
    # -----------------------------------------------------
    def _interactuar(self):
        if self._proveedor_cerca():
            self.dialogo.abrir({"intro": "proveedor_intro",
                                "mision": "proveedor_mision",
                                "receta": "proveedor_receta"}[self.proveedor_motivo])
            self.estado = "dialogo"
            return
        if self._cerca_de(self.mapa.tiles_tienda):
            self.tienda.abrir()
            self.estado = "tienda"
            return
        if self._cerca_de(self.mapa.tiles_banco):
            self.banco_ui.abrir()
            self.estado = "banco"
            return
        if self._cerca_de(self.mapa.tiles_hospital):
            self._curarse_en_clinica()
            return
        if self._cerca_de(self.mapa.tiles_telefono):
            self.telefono.abrir()
            self.estado = "pedidos"
            return
        caja = self._caja_cerca()
        if caja is not None:
            self.economia.recibir_pedido(caja.contenido)
            self.cajas.remove(caja)
            self._texto_sobre_jugador(f"Recibiste: {caja.nombre}", COLOR_DINERO)
            return
        franquicia = self._franquicia_cerca()
        if franquicia is not None and not franquicia.comprada:
            self._comprar_franquicia(franquicia)
            return
        if self._cliente_para_atender() is not None:
            self._atender_cliente()
            return
        if self._cerca_de(self.mapa.tiles_cocina):
            if self.produccion.en_curso:
                return
            if self.economia.receta_especial:
                # Con dos recetas se elige en el menú de la cocina
                self.cocina_ui.abrir()
                self.estado = "cocina"
            elif not self.produccion.iniciar(self.economia):
                self._texto_sobre_jugador(
                    f"Faltan ingredientes (necesitás {INGREDIENTES_POR_TANDA})",
                    COLOR_ERROR)

    def _cerca_de(self, rects):
        alcance = self.jugador.rect.inflate(RADIO_INTERACCION, RADIO_INTERACCION)
        return any(alcance.colliderect(r) for r in rects)

    def _caja_cerca(self):
        alcance = self.jugador.rect.inflate(RADIO_INTERACCION, RADIO_INTERACCION)
        for caja in self.cajas:
            if alcance.colliderect(caja.rect):
                return caja
        return None

    def _proveedor_cerca(self):
        return (self.proveedor is not None
                and self.proveedor.estado == "esperando"
                and self.jugador.rect.inflate(RADIO_INTERACCION, RADIO_INTERACCION)
                .colliderect(self.proveedor.rect))

    def _franquicia_cerca(self):
        alcance = self.jugador.rect.inflate(RADIO_INTERACCION, RADIO_INTERACCION)
        for franquicia in self.franquicias:
            if alcance.colliderect(franquicia.rect):
                return franquicia
        return None

    def _rival_de_zona_vivo(self, id_zona):
        return any(r.zona_id == id_zona for r in self.rivales)

    def _curarse_en_clinica(self):
        if self.jugador.vida >= self.jugador.vida_max:
            self._texto_sobre_jugador("Estás perfecto de salud", COLOR_DINERO)
        elif self.economia.pagar(PRECIO_CURACION):
            self.jugador.vida = self.jugador.vida_max
            self._texto_sobre_jugador(
                f"Curación completa (-${PRECIO_CURACION})", COLOR_DINERO)
        else:
            self._texto_sobre_jugador("No te alcanza la plata", COLOR_ERROR)

    def _comprar_franquicia(self, franquicia):
        """Solo se puede comprar con el rival de la zona eliminado
        (y antes de que llegue su reemplazo)."""
        if self._rival_de_zona_vivo(franquicia.id_zona):
            self._texto_sobre_jugador(
                "La zona sigue tomada — sacá de circulación al rival",
                COLOR_ERROR)
            return
        if not self.economia.pagar(franquicia.precio):
            self._texto_sobre_jugador("No te alcanza la plata", COLOR_ERROR)
            return
        franquicia.comprada = True
        self.economia.franquicias += 1
        # Zona conquistada: el reemplazo del rival no viene más
        self.respawns = [r for r in self.respawns
                         if r.get("zona") != franquicia.id_zona]
        self._texto_sobre_jugador(
            f"¡{franquicia.nombre} es tuyo! +${INGRESO_FRANQUICIA} "
            f"cada {int(INTERVALO_FRANQUICIA)}s", COLOR_ORO)

    def _cliente_para_atender(self):
        if not self.fila or not self._cerca_de(self.mapa.tiles_mostrador):
            return None
        primero = self.fila[0]
        if primero.listo_para_atender(POSICIONES_FILA[0]):
            return primero
        return None

    def _atender_cliente(self):
        cliente = self._cliente_para_atender()
        if self.economia.producto <= 0:
            self._texto_sobre_jugador("Sin comida lista — andá a cocinar",
                                      COLOR_ERROR)
            return
        precio = self.economia.vender_comida(self.habilidades.precio_comida_mult())
        ocupados = {tuple(c.lugar) for c in self.comensales
                    if c.estado == "comiendo" and c.lugar is not None}
        lugar = next((l for l in LUGARES_COMER if tuple(pygame.Vector2(l)) not in ocupados),
                     LUGARES_COMER[0])
        cliente.servir(lugar)
        self.fila.pop(0)
        self.comensales.append(cliente)
        self.audio.reproducir("venta")
        self.textos.append(TextoFlotante(
            cliente.rect.centerx, cliente.rect.top - 10, f"+${precio}", COLOR_DINERO))

    # -----------------------------------------------------
    # Denuncias y presencia policial dinámica
    # -----------------------------------------------------
    def _reportar_infraccion(self, tipo, cantidad, cooldown, posicion):
        """Toda infracción genera denuncias de vecinos: sube la búsqueda
        y guarda dónde pasó, para que los inspectores lleguen ahí."""
        self.busqueda.reportar(tipo, cantidad, cooldown)
        self.pos_infraccion = pygame.Vector2(posicion)

    def _actualizar_presencia_policial(self, dt):
        """Convoca inspectores cuando hay búsqueda activa y los retira
        cuando la zona se enfría."""
        if self.busqueda.nivel >= 1 and not self.inspectores:
            cantidad = min(2 + self.busqueda.nivel // 2, 5)
            self.inspectores = crear_inspectores(cantidad, self.pos_infraccion)
            if self.pos_infraccion is not None:
                for inspector in self.inspectores:
                    inspector.alertar(self.pos_infraccion)
            self.timer_retirada = 0.0
            self.audio.reproducir("sirena")
            self._texto_sobre_jugador(
                "¡Hubo denuncias! Llegaron inspectores", COLOR_ERROR)
        elif self.busqueda.nivel == 0 and self.inspectores:
            self.timer_retirada += dt
            if self.timer_retirada >= SEGUNDOS_RETIRADA:
                self.inspectores = []
                self._texto_sobre_jugador(
                    "La zona se enfrió: los inspectores se retiraron", COLOR_ORO)
        else:
            self.timer_retirada = 0.0

    # -----------------------------------------------------
    # Combate
    # -----------------------------------------------------
    def _atacar(self):
        if self.economia.tiene_pistola:
            if self.jugador.cooldown_disparo > 0:
                return
            if self.economia.balas <= 0:
                self._texto_sobre_jugador("Sin balas — compralas en el almacén",
                                          COLOR_ERROR)
                return
            self.jugador.cooldown_disparo = CADENCIA_PISTOLA
            self.economia.balas -= 1
            dispersion = (DISPERSION_APUNTADO if self.jugador.apuntando
                          else DISPERSION_CADERA) * self.habilidades.dispersion_mult()
            direccion = self.jugador.direccion_mira.rotate(
                random.uniform(-dispersion, dispersion))
            self.proyectiles.append(Proyectil(
                *self.jugador.rect.center, direccion,
                VELOCIDAD_BALA, self.habilidades.dano_pistola(),
                del_jugador=True))
            self.audio.reproducir("disparo")
            self._alertar_disparo()
        else:
            self._golpear()

    def _golpear(self):
        if self.jugador.cooldown_golpe > 0:
            return
        self.jugador.cooldown_golpe = CADENCIA_GOLPE
        self.audio.reproducir("golpe")
        punto = (pygame.Vector2(self.jugador.rect.center)
                 + self.jugador.direccion_mira * 26)
        for enemigo in self.inspectores + self.rivales:
            if punto.distance_to(enemigo.rect.center) < ALCANCE_GOLPE:
                if enemigo in self.inspectores:
                    self._reportar_infraccion("agresion", 2, 3.0,
                                              self.jugador.rect.center)
                self._danar_enemigo(enemigo, DANO_GOLPE)

    def _alertar_disparo(self):
        """Los tiros generan denuncias siempre, y los inspectores que
        andan cerca van a investigar el lugar."""
        centro = self.jugador.rect.center
        self._reportar_infraccion("disparo", 1, 6.0, centro)
        for inspector in self.inspectores:
            if pygame.Vector2(inspector.rect.center).distance_to(centro) \
                    < ALCANCE_RUIDO_DISPARO:
                inspector.alertar(centro)

    def _danar_enemigo(self, enemigo, dano):
        self.textos.append(TextoFlotante(
            enemigo.rect.centerx, enemigo.rect.top - 8, f"-{dano}", COLOR_ERROR))
        if not enemigo.recibir_dano(dano):
            return
        if enemigo in self.rivales:
            self._matar_rival(enemigo)
        else:
            self._matar_inspector(enemigo)

    def _matar_rival(self, rival):
        botin = random.randint(50, 100)
        self.economia.dinero += botin
        self.economia.puntos += PUNTOS_POR_RIVAL
        self._reportar_infraccion("homicidio", 1, 2.0, rival.rect.center)
        self.textos.append(TextoFlotante(
            rival.rect.centerx, rival.rect.top - 8,
            f"Rival eliminado: +${botin}, +{PUNTOS_POR_RIVAL} pts", COLOR_ORO))
        # Progreso de misiones de limpieza
        if (self.mision is not None and self.mision["tipo"] == "limpieza"
                and rival.zona_id == self.mision["zona"]):
            self._avanzar_mision()
        # Si la zona ya es tuya (franquicia comprada), no viene reemplazo
        zona_tuya = any(f.comprada and f.id_zona == rival.zona_id
                        for f in self.franquicias)
        if not zona_tuya:
            self.respawns.append({
                "timer": RESPAWN_RIVAL, "zona": rival.zona_id,
                "dato": (rival.hogar.x, rival.hogar.y, rival.radio_hogar,
                         rival.zona_id),
            })

    def _matar_inspector(self, inspector):
        self.busqueda.maximo()
        self.pos_infraccion = pygame.Vector2(inspector.rect.center)
        self.textos.append(TextoFlotante(
            inspector.rect.centerx, inspector.rect.top - 8,
            "¡Eliminaste a un inspector! Búsqueda máxima", COLOR_ERROR))

    # -----------------------------------------------------
    # Consecuencias
    # -----------------------------------------------------
    def _arrestar(self):
        multa, confiscados = self.economia.arresto()
        detalle = f"Multa de ${multa}"
        if confiscados:
            detalle += f" y te confiscaron {confiscados} medicamentos"
        self._caer("¡TE ARRESTARON!", detalle)

    def _morir(self):
        perdido, tirados = self.economia.muerte()
        detalle = f"Perdiste ${perdido}"
        if tirados:
            detalle += f" y {tirados} medicamentos"
        self._caer("MORISTE", detalle)

    def _caer(self, titulo, detalle):
        """Reset compartido de arresto/muerte: Walter reaparece en el
        local, la búsqueda se limpia y los inspectores se van (caso
        cerrado). Los rivales siguen donde estaban."""
        self.jugador.reaparecer(*POSICION_INICIAL)
        self.jugador.vida_max = self.habilidades.vida_max()
        self.jugador.vida = self.jugador.vida_max
        self.busqueda.reiniciar()
        self.inspectores = []
        self.timer_retirada = 0.0
        self.proyectiles.clear()
        for comprador in self.compradores:
            comprador.irse()
        self.habia_persecucion = False
        self.audio.reproducir("caida")
        self.aviso = (titulo, detalle)
        self.aviso_timer = DURACION_AVISO

    # -----------------------------------------------------
    # Lógica del estado "jugando"
    # -----------------------------------------------------
    def _actualizar_jugando(self, dt):
        # Apuntado con mouse (pasado a coordenadas de mundo)
        mouse = pygame.Vector2(pygame.mouse.get_pos()) + self.camara.offset
        mira = mouse - pygame.Vector2(self.jugador.rect.center)
        if mira.length_squared() > 0:
            self.jugador.direccion_mira = mira.normalize()
        self.jugador.apuntando = (pygame.mouse.get_pressed()[2]
                                  and self.economia.tiene_pistola)

        # Habilidad "Pies ligeros"
        self.jugador.velocidad = VELOCIDAD_JUGADOR * self.habilidades.velocidad_mult()
        # Modo debug: sin paredes para Walter (pero sin salirse del mapa)
        paredes_jugador = [] if self.debug \
            else self.mapa.paredes_cerca(self.jugador.rect)
        self.jugador.actualizar(dt, paredes_jugador)
        if self.debug:
            self.jugador.pos.x = max(0, min(self.jugador.pos.x,
                                            self.mapa.ancho_px - self.jugador.rect.w))
            self.jugador.pos.y = max(0, min(self.jugador.pos.y,
                                            self.mapa.alto_px - self.jugador.rect.h))
            self.jugador.rect.topleft = (round(self.jugador.pos.x),
                                         round(self.jugador.pos.y))

        # Producción (mejorada por la rama Cocina)
        calidad = self.produccion.actualizar(dt, self.economia, self.habilidades)
        if calidad is not None:
            self.audio.reproducir("cocinado")
            self._texto_sobre_jugador(
                f"¡Tanda lista! Calidad {round(calidad * 100)}%", COLOR_ORO)

        self._actualizar_local(dt)
        self._actualizar_pedidos(dt)

        # Cuando el local factura lo suficiente, el Proveedor viene
        # en persona a esperarte a la puerta (hablarle con E)
        if (not self.proveedor_visito
                and self.economia.total_comida >= UMBRAL_DESBLOQUEO_MEDS):
            self.proveedor_visito = True
            self.proveedor = Proveedor(8.5 * TILE, 9.4 * TILE)
            self.proveedor_motivo = "intro"
            self._texto_sobre_jugador(
                "Hay alguien esperándote en la puerta del local…", COLOR_PUNTO)
        if self.proveedor is not None:
            self.proveedor.actualizar(dt)
            # Si vino a ofrecer un trabajo y lo ignorás, se cansa
            if (self.proveedor.estado == "esperando"
                    and hasattr(self.proveedor, "timer_espera_oferta")):
                self.proveedor.timer_espera_oferta -= dt
                if self.proveedor.timer_espera_oferta <= 0:
                    self.proveedor.irse()
                    self.timer_oferta = random.uniform(60.0, 100.0)
            if self.proveedor.terminado:
                self.proveedor = None

        self._actualizar_mision(dt)

        # Ingreso pasivo de las franquicias
        self.timer_franquicia -= dt
        if self.timer_franquicia <= 0:
            self.timer_franquicia = INTERVALO_FRANQUICIA
            if self.economia.franquicias:
                ganancia = self.economia.franquicias * INGRESO_FRANQUICIA
                self.economia.dinero += ganancia
                self._texto_sobre_jugador(
                    f"+${ganancia} de tus franquicias", COLOR_DINERO)

        vendiendo_ilegal = self._actualizar_punto(dt)

        # Inspectores (si es que hay): la infracción es el punto ilegal
        for inspector in self.inspectores:
            resultado = inspector.actualizar(
                dt, self.jugador, self.mapa,
                self.mapa.paredes_cerca(inspector.rect),
                vendiendo_ilegal, self.busqueda,
                self.habilidades.vision_mult())
            if resultado == "arresto":
                self._arrestar()
                return

        # Rivales
        es_amenaza = self.economia.es_amenaza()
        for rival in self.rivales:
            bala = rival.actualizar(dt, self.jugador, self.mapa,
                                    self.mapa.paredes_cerca(rival.rect),
                                    es_amenaza)
            if bala is not None:
                self.proyectiles.append(bala)

        # Proyectiles
        for bala in self.proyectiles:
            bala.actualizar(dt, self.mapa)
            if bala.muerto:
                continue
            if bala.del_jugador:
                for enemigo in self.inspectores + self.rivales:
                    if enemigo.rect.collidepoint(bala.pos):
                        bala.muerto = True
                        if enemigo in self.inspectores:
                            self._reportar_infraccion(
                                "agresion", 2, 3.0, self.jugador.rect.center)
                        self._danar_enemigo(enemigo, bala.dano)
                        break
            elif self.jugador.rect.collidepoint(bala.pos):
                bala.muerto = True
                self.audio.reproducir("dano")
                self.textos.append(TextoFlotante(
                    self.jugador.rect.centerx, self.jugador.rect.top - 10,
                    f"-{bala.dano}", COLOR_ERROR))
                if self.jugador.recibir_dano(bala.dano):
                    self._morir()
                    return
        self.proyectiles = [b for b in self.proyectiles if not b.muerto]
        self.inspectores = [i for i in self.inspectores if not i.muerto]
        self.rivales = [r for r in self.rivales if not r.muerto]

        self._actualizar_respawns(dt)

        # Búsqueda: decae más rápido con "Fantasma"
        persiguiendo = any(i.estado in ("perseguir", "buscar")
                           for i in self.inspectores)
        self.busqueda.actualizar(dt, persiguiendo, self.habilidades.calma_mult())
        self._actualizar_presencia_policial(dt)
        if self.habia_persecucion and not persiguiendo:
            self.economia.puntos += PUNTOS_POR_ESCAPE
            self._texto_sobre_jugador(
                f"Los perdiste: +{PUNTOS_POR_ESCAPE} pts", COLOR_ORO)
        self.habia_persecucion = persiguiendo

        for texto in self.textos:
            texto.actualizar(dt)
        self.textos = [t for t in self.textos if t.vida > 0]
        if self.aviso:
            self.aviso_timer -= dt
            if self.aviso_timer <= 0:
                self.aviso = None

        self.camara.actualizar(self.jugador.rect)

    def _actualizar_local(self, dt):
        """Clientes del local: llegan, hacen fila, comen y se van."""
        self.timer_cliente -= dt
        if self.timer_cliente <= 0:
            self.timer_cliente = (random.uniform(5.0, 9.5)
                                  * self.habilidades.intervalo_clientes_mult())
            if len(self.fila) < self.habilidades.max_fila():
                entrada = random.choice(ENTRADAS_CLIENTES)
                self.fila.append(ClienteLocal(entrada, PUNTO_PUERTA))

        for i, cliente in enumerate(self.fila):
            cliente.objetivo = POSICIONES_FILA[min(i, len(POSICIONES_FILA) - 1)]

        hartos = []
        for cliente in self.fila:
            if cliente.actualizar(dt) == "harto":
                hartos.append(cliente)
                self.textos.append(TextoFlotante(
                    cliente.rect.centerx, cliente.rect.top - 10,
                    "Se fue sin comer…", COLOR_ERROR))
        for cliente in hartos:
            self.fila.remove(cliente)
            self.comensales.append(cliente)

        for cliente in self.comensales:
            cliente.actualizar(dt)
        self.comensales = [c for c in self.comensales if not c.terminado]

    def _actualizar_pedidos(self, dt):
        """Deliveries en camino → cajas en la puerta."""
        pendientes = []
        for pedido in self.pedidos:
            pedido["timer"] -= dt
            if pedido["timer"] > 0:
                pendientes.append(pedido)
                continue
            nombre, contenido, _ = PEDIDOS[pedido["id"]]
            x = PUNTO_ENTREGA[0] + (len(self.cajas) % 4) * 28
            self.cajas.append(Caja(x, PUNTO_ENTREGA[1], contenido, nombre))
            self.audio.reproducir("pedido")
            self.textos.append(TextoFlotante(
                x + 10, PUNTO_ENTREGA[1] - 12, "¡Llegó tu pedido!", COLOR_ORO))
        self.pedidos = pendientes

    def _actualizar_punto(self, dt):
        """Punto ilegal y sus compradores (solo con el proveedor
        desbloqueado). Devuelve si estás vendiendo (infracción)."""
        if not self.economia.meds_desbloqueados:
            return False
        vendiendo = (self.punto.contiene(self.jugador.rect)
                     and self.economia.tiene_meds())
        evento = self.punto.actualizar(dt, vendiendo)
        if evento == "mudanza":
            for comprador in self.compradores:
                comprador.irse()
            self.audio.reproducir("mudanza")
            self._texto_sobre_jugador(
                f"El punto se mudó: {self.punto.nombre}", COLOR_PUNTO)
        elif evento == "spawn":
            activos = sum(1 for c in self.compradores if c.estado == "acercando")
            if activos < MAX_COMPRADORES:
                x, y = self.punto.punto_spawn()
                self.compradores.append(CompradorIlegal(x, y))

        for comprador in self.compradores:
            if comprador.estado == "acercando" and not vendiendo:
                comprador.irse()
            if comprador.actualizar(dt, self.jugador.rect) == "compra":
                self._vender_med_a(comprador)
                comprador.irse()
        self.compradores = [c for c in self.compradores if not c.terminado]
        return vendiendo

    def _vender_med_a(self, comprador):
        """Le vende el tipo que prefiere; si no hay, el otro. Cada venta
        genera denuncias de vecinos (así llega la policía)."""
        tipo = comprador.tipo_preferido
        stock = {"med_nat": self.economia.med_nat,
                 "med_quim": self.economia.med_quim}
        if stock[tipo] == 0:
            tipo = "med_quim" if tipo == "med_nat" else "med_nat"
        if stock[tipo] == 0:
            return
        precio = self.economia.vender_med(tipo)
        self.punto.registrar_venta()
        self.audio.reproducir("venta")
        self._reportar_infraccion("venta_ilegal", 1, 15.0,
                                  comprador.rect.center)
        self.textos.append(TextoFlotante(
            comprador.rect.centerx, comprador.rect.top - 10,
            f"+${precio} ({NOMBRE_MED[tipo]})", COLOR_DINERO))
        # Progreso de misiones de venta
        if self.mision is not None:
            if self.mision["tipo"] == "reparto":
                self._avanzar_mision()
            elif self.mision["tipo"] == "quimicos" and tipo == "med_quim":
                self._avanzar_mision()

    def _actualizar_respawns(self, dt):
        """Los rivales eliminados vuelven con gente nueva."""
        pendientes = []
        for respawn in self.respawns:
            respawn["timer"] -= dt
            if respawn["timer"] > 0:
                pendientes.append(respawn)
            else:
                x, y, radio, zona = respawn["dato"]
                self.rivales.append(RivalGastronomico(x, y, radio, zona))
        self.respawns = pendientes

    def _texto_sobre_jugador(self, texto, color):
        self.textos.append(TextoFlotante(
            self.jugador.rect.centerx, self.jugador.rect.top - 14, texto, color))

    def _pista_interaccion(self):
        if self._proveedor_cerca():
            return "E — Hablar con el desconocido"
        franquicia = self._franquicia_cerca()
        if franquicia is not None:
            if franquicia.comprada:
                return f"{franquicia.nombre}: tuyo (+${INGRESO_FRANQUICIA}/{int(INTERVALO_FRANQUICIA)}s)"
            if self._rival_de_zona_vivo(franquicia.id_zona):
                return (f"{franquicia.nombre} (${franquicia.precio}) — "
                        "la zona sigue tomada por un rival")
            return f"E — Comprar {franquicia.nombre} (${franquicia.precio})"
        if self._cerca_de(self.mapa.tiles_tienda):
            return "E — Almacén (armas y curas)"
        if self._cerca_de(self.mapa.tiles_banco):
            return "E — Banco: guardá plata a salvo de multas"
        if self._cerca_de(self.mapa.tiles_hospital):
            if self.jugador.vida < self.jugador.vida_max:
                return f"E — Clínica: curación completa (${PRECIO_CURACION})"
            return "La clínica del barrio (estás sano)"
        if self._cerca_de(self.mapa.tiles_telefono):
            return "E — Hacer un pedido por teléfono"
        caja = self._caja_cerca()
        if caja is not None:
            return f"E — Levantar caja: {caja.nombre}"
        if self._cliente_para_atender() is not None:
            if self.economia.producto > 0:
                return "E — Atender al cliente"
            return "El cliente espera… ¡cociná algo! (E en la cocina)"
        if self._cerca_de(self.mapa.tiles_cocina):
            if self.produccion.en_curso:
                return "La tanda ya está en el fuego…"
            if self.economia.receta_especial:
                return "E — Cocinar (elegí la receta)"
            return f"E — Cocinar tanda ({INGREDIENTES_POR_TANDA} ingredientes)"
        if self.economia.meds_desbloqueados and \
                self.punto.contiene(self.jugador.rect) and \
                not self.economia.tiene_meds():
            return "Acá se venden medicamentos — pedilos por teléfono"
        return None

    # -----------------------------------------------------
    # Dibujo (según estado)
    # -----------------------------------------------------
    def _dibujar(self):
        if self.estado == "menu":
            self.menu.dibujar(self.pantalla)
        elif self.estado == "opciones":
            self.opciones.dibujar(self.pantalla)
        else:
            self._dibujar_mundo()
            if self.estado == "pausa":
                self.pausa.dibujar(self.pantalla)
            elif self.estado == "tienda":
                self.tienda.dibujar(self.pantalla, self.economia, self.jugador)
            elif self.estado == "pedidos":
                self.telefono.dibujar(self.pantalla, self.economia)
            elif self.estado == "habilidades":
                self.arbol.dibujar(self.pantalla, self.economia, self.habilidades)
            elif self.estado == "dialogo":
                self.dialogo.dibujar(self.pantalla)
            elif self.estado == "banco":
                self.banco_ui.dibujar(self.pantalla, self.economia)
            elif self.estado == "cocina":
                self.cocina_ui.dibujar(self.pantalla, self.economia)

    def _dibujar_mundo(self):
        self.pantalla.fill(COLOR_FONDO)
        self.mapa.dibujar(self.pantalla, self.camara)
        meds_ok = self.economia.meds_desbloqueados
        if meds_ok:
            self._dibujar_punto()
        self._dibujar_conos()
        for franquicia in self.franquicias:
            franquicia.dibujar(self.pantalla, self.camara)
        for caja in self.cajas:
            caja.dibujar(self.pantalla, self.camara)
        for cliente in self.fila + self.comensales:
            cliente.dibujar(self.pantalla, self.camara)
        if self.proveedor is not None:
            self.proveedor.dibujar(self.pantalla, self.camara)
            if self.proveedor.estado == "esperando":
                self._signo(self.proveedor, "!", COLOR_PUNTO)
        for comprador in self.compradores:
            comprador.dibujar(self.pantalla, self.camara)
        for enemigo in self.inspectores + self.rivales:
            enemigo.dibujar(self.pantalla, self.camara)
        self.jugador.dibujar(self.pantalla, self.camara)
        for bala in self.proyectiles:
            bala.dibujar(self.pantalla, self.camara)
        for texto in self.textos:
            texto.dibujar(self.pantalla, self.camara, self.fuente_mundo)
        self._dibujar_alertas_enemigos()
        if meds_ok:
            self._dibujar_flecha_punto()
        self.hud.dibujar(
            self.pantalla, self.jugador, self.economia, self.produccion,
            self.punto, self.punto.contiene(self.jugador.rect),
            self._pista_interaccion(), self.busqueda, self.pedidos,
            round(self.reloj.get_fps()), self.mostrar_panel, self.mision)
        if self.aviso:
            self.hud.dibujar_aviso(self.pantalla, *self.aviso)
        if self.debug:
            etiqueta = self.fuente_mundo.render(
                "DEBUG · atravesás paredes", True, COLOR_ERROR)
            self.pantalla.blit(etiqueta, (8, ALTO_VENTANA - 24))

    def _dibujar_punto(self):
        rect = self.camara.aplicar(self.punto.rect)
        if not rect.colliderect(self.pantalla.get_rect()):
            return
        velo = pygame.Surface(rect.size, pygame.SRCALPHA)
        velo.fill((*COLOR_PUNTO, 22))
        self.pantalla.blit(velo, rect)
        pygame.draw.rect(self.pantalla, COLOR_PUNTO, rect, 1)
        etiqueta = self.fuente_mundo.render(self.punto.nombre, True, COLOR_PUNTO)
        self.pantalla.blit(etiqueta, (rect.x + 5, rect.y + 4))

    def _dibujar_flecha_punto(self):
        centro_pantalla = pygame.Vector2(ANCHO_VENTANA / 2, ALTO_VENTANA / 2)
        destino = pygame.Vector2(self.punto.rect.center) - self.camara.offset
        if self.pantalla.get_rect().collidepoint(destino):
            return
        direccion = destino - centro_pantalla
        if direccion.length_squared() == 0:
            return
        direccion = direccion.normalize()
        pos = centro_pantalla + direccion * 1000
        pos.x = max(24, min(ANCHO_VENTANA - 24, pos.x))
        pos.y = max(70, min(ALTO_VENTANA - 24, pos.y))
        lado = direccion.rotate(90) * 7
        puntos = [pos + direccion * 12, pos - direccion * 4 + lado,
                  pos - direccion * 4 - lado]
        pygame.draw.polygon(self.pantalla, COLOR_PUNTO, puntos)

    def _dibujar_conos(self):
        if not self.inspectores:
            return
        self.capa_conos.fill((0, 0, 0, 0))
        for inspector in self.inspectores:
            alerta = inspector.estado == "perseguir"
            color = COLOR_CONO_ALERTA if alerta else COLOR_CONO
            pygame.draw.polygon(self.capa_conos, (*color, 30),
                                inspector.puntos_cono(self.camara))
        self.pantalla.blit(self.capa_conos, (0, 0))

    def _dibujar_alertas_enemigos(self):
        for inspector in self.inspectores:
            if inspector.estado == "perseguir":
                self._signo(inspector, "!", COLOR_ERROR)
            elif inspector.estado in ("buscar", "investigar"):
                self._signo(inspector, "?", COLOR_ORO)
        for rival in self.rivales:
            if rival.estado == "atacar":
                self._signo(rival, "!", COLOR_ERROR)
            elif rival.estado == "cazar":
                self._signo(rival, "?", COLOR_ORO)

    def _signo(self, enemigo, caracter, color):
        r = self.camara.aplicar(enemigo.rect)
        img = self.fuente_mundo.render(caracter, True, color)
        self.pantalla.blit(img, (r.centerx - img.get_width() // 2, r.y - 22))


def main():
    Juego().ejecutar()


if __name__ == "__main__":
    main()
