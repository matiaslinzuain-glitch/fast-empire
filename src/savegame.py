# =========================================================
# FAST EMPIRE — Guardado de partidas  [Fase 10]
#
# Hasta MAX_PARTIDAS slots con nombre, cada uno en su archivo
# partidas/<nombre>.json (carpeta en el .gitignore: cada
# jugador tiene sus propias partidas).
#
# Se guarda lo PERMANENTE: economía completa, habilidades,
# franquicias, progreso con el Proveedor, pedidos en camino,
# cajas en la puerta y la posición de Walter. Lo transitorio
# (persecuciones, clientes, punto ilegal, tanda en el fuego)
# arranca fresco al cargar.
#
# main.py llama: listar() · guardar(juego) · cargar(ruta) ·
# aplicar(juego, datos) · borrar(ruta) · hay_espacio(nombre)
# =========================================================

import json
import time
import unicodedata
from pathlib import Path

from .settings import POSICION_INICIAL
from .economy import Caja
from .enemies import crear_rivales

RUTA_CARPETA = Path(__file__).resolve().parent.parent / "partidas"
MAX_PARTIDAS = 5

CAMPOS_ECONOMIA = [
    "dinero", "banco", "ingredientes", "producto", "calidad",
    "med_nat", "med_quim", "tiene_pistola", "balas", "puntos",
    "total_ilegal", "total_comida", "meds_desbloqueados",
    "receta_especial", "franquicias",
]


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
        "version": 2,
        "nombre": juego.nombre_partida,
        "fecha": time.strftime("%Y-%m-%d %H:%M"),
        "economia": {campo: getattr(juego.economia, campo)
                     for campo in CAMPOS_ECONOMIA},
        "habilidades": sorted(juego.habilidades.compradas),
        "jugador": {
            "pos": [juego.jugador.rect.x, juego.jugador.rect.y],
            "vida": juego.jugador.vida,
        },
        "franquicias_compradas": [f.id_zona for f in juego.franquicias
                                  if f.comprada],
        "proveedor_visito": juego.proveedor_visito,
        "misiones_cumplidas": juego.misiones_cumplidas,
        "timer_oferta": juego.timer_oferta,
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

    # Franquicias tuyas: sus rivales no existen más
    compradas = set(datos.get("franquicias_compradas", []))
    for franquicia in juego.franquicias:
        franquicia.comprada = franquicia.id_zona in compradas
    economia.franquicias = len(compradas)
    juego.rivales = [r for r in crear_rivales() if r.zona_id not in compradas]

    juego.proveedor_visito = datos.get("proveedor_visito", False)
    juego.misiones_cumplidas = datos.get("misiones_cumplidas", 0)
    juego.timer_oferta = datos.get("timer_oferta", 45.0)

    juego.pedidos = [{"id": p["id"], "timer": p["timer"]}
                     for p in datos.get("pedidos", [])]
    juego.cajas = [Caja(c["x"], c["y"], c["contenido"], c["nombre"])
                   for c in datos.get("cajas", [])]
    juego.camara.actualizar(juego.jugador.rect)
