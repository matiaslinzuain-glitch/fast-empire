# =========================================================
# FAST EMPIRE — Guardado de partidas  [Fase 11]
#
# Hasta MAX_PARTIDAS slots con nombre, cada uno en su archivo
# partidas/<nombre>.json (carpeta en el .gitignore: cada
# jugador tiene sus propias partidas).
#
# Se guarda lo PERMANENTE: economía completa, habilidades,
# la Red (conquista de zonas y vendedores), progreso con el
# Proveedor, pedidos en camino, cajas en la puerta, la
# posición de Walter, el reloj de juego y los tratos del
# celular. Lo transitorio (persecuciones, clientes, tanda
# en el fuego) arranca fresco al cargar.
#
# main.py llama: listar() · guardar(juego) · cargar(ruta) ·
# aplicar(juego, datos) · borrar(ruta) · hay_espacio(nombre)
# =========================================================

import json
import time
import unicodedata
from pathlib import Path

from .settings import POSICION_INICIAL, HORA_INICIAL
from .economy import Caja, Trato, RedVentas, PEDIDOS
from .events import GestorEventos, PedidoVIP
from .inventory import Inventario
from .crafting import Sotano

RUTA_CARPETA = Path(__file__).resolve().parent.parent / "partidas"
MAX_PARTIDAS = 5

# Campos "planos" de la economía. Lo que Walter lleva encima ya no
# va acá: vive en el inventario dinámico (clave "inventario").
CAMPOS_ECONOMIA = [
    "dinero", "banco", "producto", "calidad",
    "tiene_pistola", "arma_equipada", "puntos",
    "total_ilegal", "total_comida", "meds_desbloqueados",
    "receta_especial",
]

# Contadores de partidas viejas que se migran al inventario
_CAMPOS_LEGADO = ["ingredientes", "med_nat", "med_quim",
                  "balas", "sanguches"]


def _slug(nombre):
    """Nombre → nombre de archivo seguro ("Matías 2" → "matias-2")."""
    sin_acentos = unicodedata.normalize("NFKD", nombre)
    sin_acentos = sin_acentos.encode("ascii", "ignore").decode("ascii")
    limpio = "".join(c if c.isalnum() else "-" for c in sin_acentos.lower())
    limpio = "-".join(parte for parte in limpio.split("-") if parte)
    return limpio[:24] or "partida"


def ruta_de(nombre):
    return RUTA_CARPETA / f"{_slug(nombre)}.json"


def listar():
    """Partidas guardadas (más reciente primero). Cada entrada:
    {"nombre", "ruta", "fecha", "dinero"}. Ignora archivos rotos."""
    if not RUTA_CARPETA.exists():
        return []
    entradas = []
    archivos = sorted(RUTA_CARPETA.glob("*.json"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
    for archivo in archivos:
        try:
            with open(archivo, encoding="utf-8") as f:
                datos = json.load(f)
            entradas.append({
                "nombre": datos.get("nombre", archivo.stem),
                "ruta": archivo,
                "fecha": datos.get("fecha", "?"),
                "dinero": datos.get("economia", {}).get("dinero", 0),
            })
        except (OSError, json.JSONDecodeError):
            continue  # archivo roto: no aparece en la lista
    return entradas


def existe_nombre(nombre):
    return ruta_de(nombre).exists()


def hay_espacio(nombre):
    """True si se puede guardar con ese nombre: o ya existe (se pisa
    a sí misma) o todavía no se llegó al máximo de slots."""
    return existe_nombre(nombre) or len(listar()) < MAX_PARTIDAS


def guardar(juego):
    """Vuelca el estado permanente al slot de la partida actual
    (juego.nombre_partida). Devuelve True si pudo."""
    if not getattr(juego, "nombre_partida", None):
        return False
    datos = {
        "version": 4,
        "nombre": juego.nombre_partida,
        "fecha": time.strftime("%Y-%m-%d %H:%M"),
        "economia": {campo: getattr(juego.economia, campo)
                     for campo in CAMPOS_ECONOMIA},
        "inventario": juego.economia.inventario.a_dict(),
        "sotano": juego.sotano.a_dict(),
        "habilidades": sorted(juego.habilidades.compradas),
        "jugador": {
            "pos": [juego.jugador.rect.x, juego.jugador.rect.y],
            "vida": juego.jugador.vida,
        },
        "red": juego.red.a_dict(),
        "eventos": juego.gestor.a_dict(),
        "proveedor_visito": juego.proveedor_visito,
        "misiones_cumplidas": juego.misiones_cumplidas,
        "timer_oferta": juego.timer_oferta,
        "reloj": juego.reloj_juego.minuto_total,
        "tratos": [t.a_dict() for t in juego.tratos],
        "pedidos": [{"id": p["id"], "timer": p["timer"]}
                    for p in juego.pedidos],
        "cajas": [{"x": c.rect.x, "y": c.rect.y,
                   "contenido": c.contenido, "nombre": c.nombre}
                  for c in juego.cajas],
    }
    try:
        RUTA_CARPETA.mkdir(parents=True, exist_ok=True)
        with open(ruta_de(juego.nombre_partida), "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


def cargar(ruta):
    """Lee una partida. Devuelve el dict o None si está rota."""
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def borrar(ruta):
    try:
        Path(ruta).unlink()
        return True
    except OSError:
        return False


def aplicar(juego, datos):
    """Restaura una partida sobre un mundo recién creado
    (main.py llama a nueva_partida() antes)."""
    economia = juego.economia
    for campo in CAMPOS_ECONOMIA:
        if campo in datos["economia"]:
            setattr(economia, campo, datos["economia"][campo])

    # Inventario dinámico (o migración de los contadores viejos)
    if "inventario" in datos:
        economia.inventario = Inventario.desde_dict(datos["inventario"])
    else:
        for campo in _CAMPOS_LEGADO:
            valor = datos["economia"].get(campo, 0)
            if valor:
                setattr(economia, campo, valor)
    # El celular y el arma siempre están donde corresponde
    if not economia.inventario.tiene("celular"):
        economia.inventario.agregar("celular")
    if economia.tiene_pistola and not economia.inventario.tiene("arma"):
        economia.inventario.agregar("arma")
    juego.sotano = Sotano.desde_dict(datos.get("sotano"))

    juego.habilidades.compradas = set(datos.get("habilidades", []))
    juego.jugador.vida_max = juego.habilidades.vida_max()
    juego.jugador.vida = min(datos["jugador"]["vida"], juego.jugador.vida_max)

    # Posición: si quedó dentro de una pared (guardó con el modo
    # debug puesto), reaparece en el local
    x, y = datos["jugador"]["pos"]
    rect = juego.jugador.rect
    if juego.mapa.es_solido_en(x + rect.w / 2, y + rect.h / 2):
        x, y = POSICION_INICIAL
    juego.jugador.pos.update(x, y)
    rect.topleft = (round(x), round(y))

    # La Red: conquista de zonas y vendedores. Los matones del
    # paso en disputa y los NPCs de los vendedores colocados
    # vuelven a su puesto al cargar.
    juego.red = RedVentas.desde_dict(datos.get("red"))
    juego.rivales = []
    juego._sincronizar_matones()
    juego.vendedores_npc = []
    juego._sincronizar_vendedores_npc()

    juego.proveedor_visito = datos.get("proveedor_visito", False)
    juego.misiones_cumplidas = datos.get("misiones_cumplidas", 0)
    juego.timer_oferta = datos.get("timer_oferta", 45.0)

    # Eventos de jefe: el soborno pendiente no se esquiva cerrando
    # el juego (la oferta flash sí se pierde, mala suerte)
    juego.gestor = GestorEventos.desde_dict(datos.get("eventos"))
    juego.contacto_flash = None

    # Reloj de juego y tratos del celular (Fase 11). Los pedidos
    # VIP vuelven con su clase (todo o nada, ventana corta)
    juego.reloj_juego.minuto_total = datos.get("reloj", float(HORA_INICIAL))
    juego.tratos = [
        (PedidoVIP if t.get("vip") else Trato).desde_dict(
            t, juego.reloj_juego)
        for t in datos.get("tratos", [])]

    # Pedidos en camino (los ids que ya no existen — p. ej. los
    # medicamentos hechos de partidas viejas — se descartan)
    juego.pedidos = [{"id": p["id"], "timer": p["timer"]}
                     for p in datos.get("pedidos", [])
                     if p["id"] in PEDIDOS]
    juego.cajas = [Caja(c["x"], c["y"], c["contenido"], c["nombre"])
                   for c in datos.get("cajas", [])]
    juego.camara.actualizar(juego.jugador.rect)
