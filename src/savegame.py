# =========================================================
# FAST EMPIRE — Guardado de partidas  [Fase 10]
#
# Un slot en partidas/partida.json (la carpeta está en el
# .gitignore: cada jugador tiene su propia partida).
#
# Se guarda lo PERMANENTE: economía completa, habilidades,
# franquicias, progreso con el Proveedor, pedidos en camino,
# cajas en la puerta y la posición de Walter. Lo transitorio
# (persecuciones, clientes, punto ilegal, tanda en el fuego)
# arranca fresco al cargar.
#
# main.py llama: guardar(juego) · cargar() · aplicar(juego, d)
# =========================================================

import json
import time
from pathlib import Path

from .settings import POSICION_INICIAL
from .economy import Caja
from .enemies import crear_rivales

RUTA_PARTIDA = Path(__file__).resolve().parent.parent / "partidas" / "partida.json"

CAMPOS_ECONOMIA = [
    "dinero", "banco", "ingredientes", "producto", "calidad",
    "med_nat", "med_quim", "tiene_pistola", "balas", "puntos",
    "total_ilegal", "total_comida", "meds_desbloqueados",
    "receta_especial", "franquicias",
]


def existe():
    return RUTA_PARTIDA.exists()


def guardar(juego):
    """Vuelca el estado permanente a disco. Devuelve True si pudo."""
    datos = {
        "version": 1,
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
        RUTA_PARTIDA.parent.mkdir(parents=True, exist_ok=True)
        with open(RUTA_PARTIDA, "w", encoding="utf-8") as archivo:
            json.dump(datos, archivo, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


def cargar():
    """Lee la partida guardada. Devuelve el dict o None si no hay
    (o si el archivo está roto)."""
    try:
        with open(RUTA_PARTIDA, encoding="utf-8") as archivo:
            return json.load(archivo)
    except (OSError, json.JSONDecodeError):
        return None


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
