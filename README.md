# Fast Empire

Juego top-down de gestión criminal hecho en **Python + Pygame**.

Walter, cocinero escolar de toda la vida, descubre que tiene una enfermedad
terminal. Con lo único que sabe hacer —cocinar— monta un local de comidas
como fachada y construye un imperio desde cero, operando en los límites de
la ley. Inspirado narrativamente en Breaking Bad, ambientado en el mundo de
la gastronomía y el mercado negro.

## Cómo ejecutar

```bash
git clone https://github.com/matiaslinzuain-glitch/fast-empire.git
cd fast-empire
pip install pygame
python3 main.py
```

## Controles

| Tecla | Acción |
|---|---|
| W A S D | Mover a Walter |
| Mouse | Apuntar |
| Click izquierdo | Disparar (con pistola) / golpear (sin arma) |
| Click derecho (sostener) | Apuntar con mira: menos dispersión, camina más lento |
| E | Atender clientes, cocinar, teléfono, levantar cajas, almacén |
| T | Árbol de habilidades |
| TAB | Mostrar/ocultar el panel de recursos |
| F5 | Guardar la partida (también desde el menú de pausa) |
| Cmd+F o F11 | Pantalla completa / ventana (también en Pausa y Opciones) |
| ESC | Pausa (en el juego) / volver (en menús) |
| Mouse o W/S + ENTER | Navegar y confirmar en todos los menús |

## Cómo se juega

El negocio tiene dos caras:

### El local de comidas (legal)

1. **Pedí ingredientes por teléfono** (el aparato con pantallita, al fondo del
   local): el pedido llega a los ~25 segundos en **cajas** a la puerta.
   Levantalas con E.
2. **Cociná** en la cocina del local (E): la receta **Clásica** usa 3
   ingredientes → 4 platos con calidad 60–90%. Cumplida tu primera misión
   del Proveedor, él te enseña la **Receta Especial** (5 ingredientes +
   $15 de especias → platos premium con calidad 130–160%, que se cobran
   al doble o más); desde ahí E abre el menú para elegir receta.
3. **Atendé la fila**: los vecinos entran solos, hacen cola frente al
   mostrador y esperan (¡se cansan a los 30 segundos!). Parado detrás del
   mostrador, E atiende al primero: paga, se va a comer a un costado y se
   retira. Acá los inspectores no te molestan.

### Los medicamentos (ilegal — se desbloquean jugando)

4. El juego arranca **solo con la comida rápida**. Cuando el local factura
   $200, **el Proveedor te espera en persona en la puerta** (encapuchado, con
   un "!"). Hablale con E: al terminar la charla se habilitan los
   **medicamentos naturales** (baratos) y **químicos** (caros) en el
   teléfono, con packs x3 y x6 mayoristas. No se venden en el mostrador.
5. Se revenden en el **punto ilegal**, marcado en violeta en el mapa (una
   flechita en el borde de la pantalla te guía). Compradores encapuchados se
   acercan de a poco: pocos por tanda, pero pagan mucho más que un plato.
6. **El punto se muda** cuando se agota la demanda o pasa el tiempo — el HUD
   siempre muestra dónde está hoy.
7. **La policía no vive en el mapa**: cada venta ilegal, tiro o muerte genera
   denuncias de los vecinos. Con la primera denuncia llegan 2–4 inspectores a
   investigar la zona; si un inspector te ve en el punto con mercadería, te
   persigue. Arresto = multa del 25% + medicamentos confiscados. Cuando la
   **BÚSQUEDA** (0–5) vuelve a cero y pasan unos segundos, se retiran.
8. **Los rivales** (bandana roja) rondan los puntos de venta. Te ignoran
   hasta que facturás $150 en negro; después te atacan a tiros. La pistola,
   las balas y el sanguche curativo se compran en el **almacén** (toldo rojo,
   en el centro del mapa).

### Las franquicias (territorio)

9. Hay **4 puestos en venta**: Mercado ($400), Campo ($550), Sur ($700) y el
   Depósito del Puerto ($850) — justo en las zonas que vigilan los rivales.
   Para comprar uno (E sobre el puesto) hay que **eliminar al rival de esa
   zona y cerrar el trato antes de que llegue su reemplazo** (60 segundos de
   ventana). Una vez tuyo: el rival no vuelve nunca más y el puesto paga
   **+$20 cada 30 segundos**, solo. Don Aldo, el almacenero, te cuenta el
   negocio si charlás con él (opción en el almacén).

### Las misiones del Proveedor

Con el negocio ilegal abierto, el Proveedor **vuelve cada tanto a la puerta
del local con un trabajo** (si lo ignorás ~35 segundos, se va y tarda más en
volver). Hablarle asigna una misión con tiempo límite, visible en un banner:

- **Reparto**: vendé 3–5 medicamentos en el punto ($30 y 1 punto por unidad).
- **Pedido exigente**: vendé 2–4 **químicos** ($55 y 2 puntos por unidad).
- **Limpieza**: eliminá al rival de una zona puntual ($200 y 8 puntos).

Fallar no castiga, pero el próximo trabajo tarda más. **La primera misión
cumplida paga distinto**: el Proveedor vuelve en persona a enseñarte su
Receta Especial.

### El Distrito Sur (servicios)

10. Al sur de la terminal vieja se abre el distrito industrial: el **Banco**
    (franja dorada) — lo que depositás **no se pierde en arrestos ni
    muertes**, que solo tocan tu efectivo —, la **Clínica** (cruz roja) con
    curación completa por $50, un **segundo almacén**, y los galpones del
    puerto. El **arroyo** cruza el este del mapa con dos puentes; del otro
    lado, la Costanera.

## Guardado de partidas

- **Menú principal**: "Nueva partida" arranca de cero; "Cargar partida"
  retoma la guardada (dice "(vacío)" si no hay ninguna).
- **Se guarda solo**: cada 60 segundos jugando, al volver al menú principal
  y al cerrar la ventana. **Manual**: F5 o "Guardar partida" en la pausa.
- Se guarda lo permanente (plata, banco, inventario, habilidades,
  franquicias con sus rivales eliminados, receta, misiones cumplidas,
  pedidos en camino, cajas y tu posición). Lo transitorio (persecuciones,
  clientes, punto ilegal) arranca fresco al cargar.
- El archivo vive en `partidas/partida.json` (un slot; una partida nueva lo
  pisa en el primer guardado). La carpeta está en el `.gitignore`: cada
  jugador tiene su propia partida.

## Modo debug

**F1** en cualquier momento, o las opciones **"Modo debug: no/sí"** del menú
principal y del menú de pausa, activan el noclip: Walter atraviesa paredes,
edificios y el arroyo (sin salirse del mapa). Mientras está activo se ve
`DEBUG · atravesás paredes` abajo a la izquierda. El ajuste sobrevive a las
partidas nuevas hasta que lo apagues.

## Estructura del proyecto

```
/fast_empire
  main.py            → clase Juego: máquina de estados y game loop
  /src
    settings.py      → constantes globales: ventana, colores, combate
    map.py           → mapa 60x45 por piezas validadas, local, colisiones
    player.py        → Walter: WASD, vida, mira, física compartida
    camera.py        → cámara que sigue al jugador, clampeada al mapa
    economy.py       → dinero, producción, pedidos, cajas, punto ilegal
    npcs.py          → clientes del local (fila/comer) y compradores ilegales
    sprites.py       → pixel art procedural: plantillas de texto + paletas
    audio.py         → efectos y música sintetizados (sin archivos)
    ui.py            → HUD, menús con mouse, almacén, teléfono y árbol
    enemies.py       → inspectores (convocables), rivales, búsqueda, balas
    skills.py        → árbol de habilidades: 4 ramas x 3 nodos
    dialogue.py      → diálogos como datos + caja con máquina de escribir
  /assets
    /sprites /sounds /music → (vacíos) para el pulido final
```

## Estado actual

### Fase 1 ✅ — Base jugable
Ventana 800x600 @ 60 FPS, WASD con colisiones eje por eje, cámara con clamp.

### Fase 2 ✅ — Economía y UI
Máquina de estados (menú/juego/pausa/tienda), producción con calidad,
clientes NPC, HUD y textos flotantes.

### Fase 3 ✅ — Enemigos, IA y combate
Inspectores con cono de visión y nivel de búsqueda 0–5, rivales con
territorio, combate con mouse (mira/disparo/golpe), arresto y muerte con
consecuencias, respawns.

### Fase 4 ✅ — El local y el contrabando
- **Mapa expandido a 60x45** (2.3x): manzanas de casas con tejas, grilla de
  calles, parque, dos baldíos, terminal vieja y campo con portones. Filas
  construidas por piezas con `assert` (imposible desalinear colisiones) y
  colisiones optimizadas por vecindad (`paredes_cerca`).
- **Local de Walter**: cocina, teléfono, mostrador y salón. Clientes que
  entran por la puerta, hacen fila, se atienden con E, comen y se van (o se
  cansan de esperar).
- **Delivery**: pedidos por teléfono que llegan en cajas a la puerta.
- **Medicamentos naturales y químicos**: compra por teléfono, reventa en el
  **punto ilegal rotativo** (5 ubicaciones candidatas, demanda limitada,
  flechita indicadora). La fama ilegal (`total_ilegal`) es lo que activa a
  los rivales, y el arresto ahora confisca la mercadería, no la comida.
- 4 inspectores cubriendo la ciudad, 3 rivales rondando los puntos.

### Fase 5 ✅ — Progresión y calidad de vida

- **Árbol de habilidades** (tecla T): Cocina, Ventas, Combate y Sigilo, 3
  nodos por rama comprados en orden con puntos + dinero. Los efectos
  (calidad, tandas de 6, precios +25%, más clientes, vida 140, menos
  dispersión, más daño, menos visión enemiga, velocidad, búsqueda que se
  enfría al doble) se consultan siempre vía `Habilidades`, así que agregar
  nodos nuevos es tocar solo `skills.py`.
- **Arranque 100% legal**: los medicamentos quedan bloqueados ("línea
  muerta" en el teléfono) hasta facturar $200 con el local; ahí aparece el
  aviso del proveedor y se habilita todo el lado ilegal (punto, flechita,
  HUD).
- **Policía dinámica**: el mapa arranca sin inspectores. Las infracciones
  generan denuncias que convocan 2–4 (según la búsqueda) sobre las rutas más
  cercanas al hecho; llegan investigando y se retiran tras ~8 segundos con
  búsqueda en cero. El arresto cierra el caso (se van todos).
- **Panel de recursos ocultable con TAB** (queda solo la barrita de vida).
- **Mouse en todos los menús**: hover resalta, click confirma (menú
  principal, pausa, almacén, teléfono y árbol).

### Fase 6 ✅ — Mundo vivo

- **Sistema de diálogos** (`dialogue.py`, último esqueleto completado): caja
  inferior con efecto máquina de escribir, nombre coloreado por personaje,
  avance con E/click (primera vez completa la línea, segunda avanza) y ESC
  para saltear. Las conversaciones son datos: agregar historia no toca lógica.
- **El Proveedor es un NPC**: al facturar $200 viene a la puerta del local y
  espera con un "!"; el lado ilegal se desbloquea al TERMINAR su charla (ya
  no por umbral automático). Después se va caminando.
- **Franquicias**: 3 puestos comprables en las zonas de los rivales.
  Requisito: rival eliminado + comprar dentro de la ventana de 60s antes del
  reemplazo. Comprado: el rival de esa zona no respawnea más e ingresa
  +$20/30s pasivo (línea propia en el HUD).
- **Don Aldo**: opción "Charlar" en el almacén, con pistas del negocio.
- **Packs mayoristas** de medicamentos (x6 con descuento) en el teléfono.

### Fase 7 ✅ — Pantalla completa y el Distrito Sur

- **F11**: pantalla completa/ventana en cualquier momento (modo SCALED de
  pygame: la resolución lógica sigue siendo 800x600 y el mouse se traduce
  solo, así que nada del juego cambia).
- **Mapa ampliado a 76x58** (2432x1856 px, ~2.4x): distrito sur industrial
  con avenida que rodea el muro del campo, galpones, arroyo norte-sur con
  dos puentes y la Costanera del otro lado.
- **Banco**: depositar/retirar (pantalla propia con mouse). El efectivo
  sufre multas (25%) y muertes (40%); la caja fuerte no. Línea en el HUD.
- **Clínica**: curación completa por $50 con E.
- **Segundo almacén** en el distrito sur.
- **2 candidatos nuevos** para el punto ilegal (Puerto Sur, La Costanera —
  7 en total), **4ta franquicia** (Depósito del Puerto, $850) con su **4to
  rival**, y **5ta ruta de inspectores** (ahora pueden llegar hasta 5).

### Fase 8 ✅ — Pulido: sprites, sonido y pantalla completa

- **Pantalla completa arreglada para macOS**: Cmd+F o F11, más opciones
  clickeables en Pausa y en Opciones. El método recrea la ventana
  (SCALED+FULLSCREEN) en vez del toggle frágil de pygame, con degradación
  si un modo no está disponible.
- **Sprites pixel art procedurales** (`sprites.py`): personajes de 12x16
  "píxeles" definidos como plantillas de texto, escalados x2, con caminata
  animada de 2 pasos y giro según dirección. Paletas por rol: Walter canoso
  con delantal, inspectores con gorra blanca, rivales con bandana,
  compradores y Proveedor encapuchados, vecinos con ropa aleatoria.
- **Audio sintetizado** (`audio.py`, sin archivos): 12 efectos (disparo,
  golpe, caja registradora, tanda lista, timbre del delivery, sirena,
  daño, arresto/muerte, mudanza del punto, blips de menú y diálogo) y un
  loop de música ambiente (bajos en Am-F-C-G). Si el mixer falla, el juego
  sigue en silencio.
- **Opciones reales**: volumen en pasos de 20%, música sí/no y pantalla
  completa, todo con mouse o teclado.
- **Balance**: clientes del local cada 5–9.5s (antes 6–11) y botín de
  rivales $50–100 (antes $40–80).

### Fase 9 ✅ — Misiones del Proveedor y la Receta Especial

- **Misiones con tiempo límite**: el Proveedor visita el local cada 50–120s
  cuando no hay misión activa (con timeout si lo ignorás). Tres tipos
  (reparto / químicos / limpieza de zona) generados según el estado del
  mundo, con banner de progreso en el HUD, recompensas en $ y puntos, y
  sonidos de éxito/fracaso.
- **Receta Especial**: recompensa narrativa de la primera misión (el
  Proveedor vuelve a enseñártela con su propio diálogo). La cocina pasa a
  tener menú de recetas (`PantallaCocina`): Clásica de siempre o Especial
  (5 ingredientes + $15 → calidad 130–160%, precio del plato multiplicado).
  Las habilidades de Cocina aplican a ambas (tandas de 6, cocción rápida).

## Roadmap

- **Próximo**: lo que salga de jugarlo — más misiones (entregas a domicilio,
  encargos de Don Aldo), sprites para los tiles del mapa, un jefe rival, o
  balance fino según cómo se sienta.
