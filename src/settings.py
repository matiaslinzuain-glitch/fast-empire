# =========================================================
# FAST EMPIRE — Configuración global
# Todas las constantes del juego viven acá para que
# cualquier ajuste (velocidad, colores, tamaños) se haga
# en un solo lugar.
# =========================================================

# --- Ventana ---
# Resolución lógica de la INTERFAZ (16:9): los menús, el HUD y el
# celular se siguen dibujando en 960x540 y se estiran a la ventana.
ANCHO_VENTANA = 960
ALTO_VENTANA = 540
FPS = 60
TITULO = "Fast Empire — Fase 11"

# --- Mundo ---
# El MUNDO se dibuja en un lienzo del doble de resolución que la
# UI (1920x1080 con tiles de 64), así los edificios y sprites en
# alta resolución muestran su detalle. ESCALA_MUNDO relaciona los
# dos espacios: px de mundo = px de UI * ESCALA_MUNDO.
ESCALA_MUNDO = 2
ANCHO_LIENZO = ANCHO_VENTANA * ESCALA_MUNDO   # 1920
ALTO_LIENZO = ALTO_VENTANA * ESCALA_MUNDO     # 1080
TILE = 64  # tamaño de cada casillero del mapa en píxeles

# Capas "por encima" del mapa de Tiled (techos, copas, toldos):
# cuando una celda de esas capas tapa al jugador, la capa entera se
# atenúa con un fundido para no ocultarlo.
TECHO_ALPHA_OCULTO = 90   # opacidad (0-255) mientras tapa al jugador
TECHO_VEL_FADE = 6.0      # velocidad del fundido (más alto = más rápido)

# --- Jugador ---
# (Los valores en píxeles de mundo son el doble que con TILE=32)
VELOCIDAD_JUGADOR = 440          # píxeles por segundo
TAM_JUGADOR = (44, 52)           # hitbox (ancho, alto), un poco menor al tile
POSICION_INICIAL = (5 * TILE, 3 * TILE)  # detrás del mostrador del local

# --- Paleta de colores (pixel art, tonos realistas) ---
COLOR_FONDO       = (18, 18, 22)     # negro azulado de fondo
COLOR_CALLE       = (52, 52, 56)     # asfalto
COLOR_CALLE_LINEA = (66, 66, 70)     # detalle sutil del asfalto
COLOR_PASTO       = (58, 82, 44)     # verde apagado del campo
COLOR_PASTO_DET   = (66, 92, 50)     # matas de pasto
COLOR_TIERRA      = (110, 86, 56)    # camino de tierra que une ciudad y campo
COLOR_EDIFICIO    = (88, 74, 66)     # ladrillo/cemento envejecido
COLOR_EDIFICIO_TOP= (108, 92, 82)    # borde superior (da sensación de altura)
COLOR_ARBOL       = (38, 60, 34)     # copa de árbol
COLOR_ARBOL_LUZ   = (52, 78, 44)     # brillo de la copa
COLOR_JUGADOR     = (196, 164, 120)  # piel
COLOR_ROPA        = (120, 40, 40)    # delantal/campera bordó de cocinero
COLOR_TEXTO       = (230, 230, 230)  # HUD

# --- Colores Fase 2: HUD, menús, zonas de venta y mobiliario ---
COLOR_TEXTO_SUAVE  = (150, 150, 155)  # textos secundarios
COLOR_ORO          = (222, 178, 84)   # títulos y selección de menú
COLOR_DINERO       = (150, 215, 140)  # plata ganada
COLOR_TARJETA      = (130, 180, 240)  # plata en el banco (tarjeta)
COLOR_ERROR        = (235, 120, 105)  # avisos ("no te alcanza", etc.)
COLOR_ZONA         = (255, 214, 100)  # zona de venta operativa
COLOR_ZONA_FRIA    = (130, 170, 230)  # zona enfriándose
COLOR_COCINA       = (82, 84, 92)     # carrito/cocina de Walter (acero)
COLOR_COCINA_TOP   = (214, 128, 52)   # tapa caliente de la cocina
COLOR_TIENDA       = (104, 72, 48)    # mostrador de madera de la tienda
COLOR_TIENDA_TOLDO = (158, 58, 48)    # toldo rojo de la tienda

# --- Combate (Fase 3) ---
VIDA_JUGADOR = 100
DANO_GOLPE = 15            # ataque cuerpo a cuerpo (sin arma)
ALCANCE_GOLPE = 92         # px desde el centro del jugador
CADENCIA_GOLPE = 0.5       # segundos entre golpes
DANO_PISTOLA = 25
CADENCIA_PISTOLA = 0.35
VELOCIDAD_BALA = 1040      # px/s de las balas del jugador
DISPERSION_CADERA = 7      # grados de error disparando sin apuntar
DISPERSION_APUNTADO = 2    # con la mira (click derecho)
FRENO_APUNTADO = 0.55      # multiplicador de velocidad al apuntar

# --- Colores Fase 4: el local, el delivery y los medicamentos ---
COLOR_CASA          = (146, 124, 98)   # pared de casa
COLOR_CASA_TECHO    = (152, 76, 58)    # tejas
COLOR_PISO_LOCAL    = (112, 88, 60)    # madera del local
COLOR_PISO_LINEA    = (100, 78, 52)    # junta de tablones
COLOR_MOSTRADOR     = (88, 62, 40)     # frente del mostrador
COLOR_MOSTRADOR_TOP = (168, 136, 96)   # tapa del mostrador
COLOR_TELEFONO      = (40, 42, 48)     # aparato
COLOR_TELEFONO_LUZ  = (120, 200, 160)  # pantallita encendida
COLOR_CAJA          = (150, 110, 66)   # cartón
COLOR_CAJA_CINTA    = (196, 172, 120)  # cinta de embalar
COLOR_MED_NAT       = (120, 190, 120)  # medicamentos naturales
COLOR_MED_QUIM      = (170, 120, 220)  # medicamentos químicos
COLOR_PUNTO         = (196, 120, 230)  # marcador del punto ilegal

# --- Colores Fase 7: distrito sur, arroyo y servicios ---
COLOR_AGUA          = (50, 84, 118)    # el arroyo
COLOR_AGUA_LUZ      = (74, 112, 148)   # reflejos del agua
COLOR_BANCO         = (148, 150, 162)  # piedra del banco
COLOR_BANCO_FRANJA  = (222, 178, 84)   # franja dorada
COLOR_HOSPITAL      = (226, 230, 232)  # clínica blanca
COLOR_HOSPITAL_CRUZ = (196, 60, 54)    # cruz roja

# --- Colores Fase 3: combate y enemigos ---
COLOR_VIDA            = (200, 70, 60)    # barra de vida
COLOR_VIDA_FONDO      = (60, 24, 20)
COLOR_INSPECTOR       = (205, 210, 215)  # uniforme sanitario claro
COLOR_INSPECTOR_GORRA = (240, 244, 248)
COLOR_RIVAL           = (44, 44, 50)     # ropa oscura
COLOR_RIVAL_BANDANA   = (172, 52, 46)
COLOR_BALA            = (255, 230, 150)
COLOR_CONO            = (255, 235, 150)  # cono de visión patrullando
COLOR_CONO_ALERTA     = (255, 96, 70)    # cono de visión persiguiendo
COLOR_MIRA            = (235, 235, 235)  # línea de apuntado

# --- Física de manejo (estilo GTA 1/2) ---
# El vehículo tiene trompa: W acelera hacia donde apunta y A/D la
# giran. La velocidad real persigue a la trompa según el "agarre"
# de cada modelo (VEHICULOS en economy.py): esa diferencia es el
# derrape. La simulación vive en src/vehicle.py.
ACEL_VEHICULO = 520        # empuje del motor (px/s²)
FRENO_VEHICULO = 1080      # freno / aceleración de la reversa
ROCE_VEHICULO = 260        # desaceleración natural al soltar todo
GIRO_VEHICULO = 2.6        # radianes/s con el volante a fondo
REVERSA_VEHICULO = 0.45    # vel. máx. marcha atrás (fracción de avance)
CHOQUE_VEHICULO = 0.35     # rapidez que queda tras chocar una pared
# La cámara sigue con un retraso suave y se adelanta hacia donde va
# el auto, para dar tiempo a reaccionar en las esquinas.
CAMARA_SUAVIZADO = 0.002   # resto de distancia tras 1 s (menor = más dura)
CAMARA_ADELANTO = 0.45     # segundos de velocidad que se adelanta
CAMARA_ADELANTO_MAX = 240  # tope del adelanto (px)

# --- Fase 11: reloj de juego ---
# 1 segundo real = 1 minuto de juego (un día dura 24 min reales)
MINUTOS_POR_SEGUNDO = 1.0
HORA_INICIAL = 8 * 60          # la partida arranca a las 08:00 del día 1

# --- Fase 11: celular e inventario ---
COLOR_CELULAR       = (26, 26, 32)     # carcasa del teléfono
COLOR_CELULAR_BORDE = (70, 70, 80)
COLOR_PANTALLA_CEL  = (16, 18, 24)     # fondo de la pantalla
COLOR_APP_ACTIVA    = (222, 178, 84)   # pestaña de app seleccionada
COLOR_SLOT          = (30, 30, 38)     # casillero de inventario
COLOR_SLOT_BORDE    = (78, 78, 88)
COLOR_SLOT_SEL      = (222, 178, 84)   # casillero seleccionado
COLOR_FERIA         = (150, 96, 58)    # kioscos de la feria del sur (tile k)
