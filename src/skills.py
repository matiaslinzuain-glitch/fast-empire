# =========================================================
# FAST EMPIRE — Árbol de habilidades  [Fase 5]
#
# Cuatro ramas de tres nodos. Cada nodo cuesta puntos de
# habilidad (se ganan vendiendo, eliminando rivales y
# escapando) + dinero. Dentro de una rama hay que comprar
# en orden (el nodo 2 pide el 1, etc.).
#
# La clase Habilidades guarda qué nodos tenés y expone los
# stats YA MODIFICADOS (calidad, daño, velocidad...): el
# resto del juego le pregunta a ella en vez de usar las
# constantes crudas, así agregar un nodo nuevo es tocar
# solo este archivo.
# =========================================================

from .settings import DANO_PISTOLA, VIDA_JUGADOR
from .economy import (
    CALIDAD_MINIMA, UNIDADES_POR_TANDA, DURACION_PRODUCCION,
)

# (los colores acompañan a cada rama en la pantalla del árbol)
ARBOL = [
    {"nombre": "COCINA", "color": (214, 128, 52), "nodos": [
        {"id": "recetario", "nombre": "Recetario del abuelo",
         "desc": "La calidad mínima de cada tanda sube de 60% a 70%.",
         "puntos": 3, "dinero": 100},
        {"id": "tandas", "nombre": "Tandas grandes",
         "desc": "Cada cocinada rinde 6 platos en vez de 4.",
         "puntos": 5, "dinero": 250},
        {"id": "fuego", "nombre": "Fuego rápido",
         "desc": "Cocinar tarda 3 segundos en vez de 5.",
         "puntos": 8, "dinero": 500},
    ]},
    {"nombre": "VENTAS", "color": (222, 178, 84), "nodos": [
        {"id": "onda", "nombre": "Atención con onda",
         "desc": "Los platos se cobran un 25% más caros.",
         "puntos": 3, "dinero": 100},
        {"id": "fama", "nombre": "Fama del barrio",
         "desc": "Los clientes del local llegan mucho más seguido.",
         "puntos": 5, "dinero": 250},
        {"id": "fiel", "nombre": "Clientela fiel",
         "desc": "La fila del mostrador admite 8 clientes en vez de 5.",
         "puntos": 8, "dinero": 400},
    ]},
    {"nombre": "COMBATE", "color": (200, 70, 60), "nodos": [
        {"id": "aguante", "nombre": "Aguante",
         "desc": "Vida máxima 140 (te cura +40 al comprarla).",
         "puntos": 3, "dinero": 150},
        {"id": "pulso", "nombre": "Pulso firme",
         "desc": "La pistola dispersa la mitad al disparar.",
         "puntos": 5, "dinero": 300},
        {"id": "balas", "nombre": "Balas caseras",
         "desc": "El daño de la pistola sube de 25 a 40.",
         "puntos": 8, "dinero": 600},
    ]},
    {"nombre": "SIGILO", "color": (130, 170, 230), "nodos": [
        {"id": "perfil", "nombre": "Perfil bajo",
         "desc": "Los inspectores te ven un 25% menos lejos.",
         "puntos": 3, "dinero": 150},
        {"id": "pies", "nombre": "Pies ligeros",
         "desc": "Caminás un 15% más rápido.",
         "puntos": 5, "dinero": 300},
        {"id": "fantasma", "nombre": "Fantasma",
         "desc": "El nivel de búsqueda se enfría el doble de rápido.",
         "puntos": 8, "dinero": 500},
    ]},
]


class Habilidades:
    def __init__(self):
        self.compradas = set()  # ids de nodos comprados

    def tiene(self, id_nodo):
        return id_nodo in self.compradas

    def estado(self, rama, nivel):
        """"comprada" | "disponible" | "bloqueada" (falta la anterior)."""
        nodo = ARBOL[rama]["nodos"][nivel]
        if nodo["id"] in self.compradas:
            return "comprada"
        if nivel > 0 and ARBOL[rama]["nodos"][nivel - 1]["id"] not in self.compradas:
            return "bloqueada"
        return "disponible"

    def comprar(self, rama, nivel, economia):
        """Intenta comprar el nodo. Devuelve (ok, mensaje)."""
        nodo = ARBOL[rama]["nodos"][nivel]
        estado = self.estado(rama, nivel)
        if estado == "comprada":
            return False, "Ya tenés esa habilidad."
        if estado == "bloqueada":
            return False, "Primero comprá la habilidad anterior de la rama."
        if economia.puntos < nodo["puntos"]:
            return False, f"Te faltan puntos ({economia.puntos}/{nodo['puntos']})."
        if economia.dinero < nodo["dinero"]:
            return False, "No te alcanza la plata."
        economia.puntos -= nodo["puntos"]
        economia.dinero -= nodo["dinero"]
        self.compradas.add(nodo["id"])
        return True, f"¡{nodo['nombre']} desbloqueada!"

    # --- Stats modificados (el juego consulta siempre acá) ---

    def calidad_minima(self):
        return 0.70 if self.tiene("recetario") else CALIDAD_MINIMA

    def unidades_por_tanda(self):
        return 6 if self.tiene("tandas") else UNIDADES_POR_TANDA

    def duracion_produccion(self):
        return 3.0 if self.tiene("fuego") else DURACION_PRODUCCION

    def precio_comida_mult(self):
        return 1.25 if self.tiene("onda") else 1.0

    def intervalo_clientes_mult(self):
        return 0.55 if self.tiene("fama") else 1.0

    def max_fila(self):
        return 8 if self.tiene("fiel") else 5

    def vida_max(self):
        return 140 if self.tiene("aguante") else VIDA_JUGADOR

    def dispersion_mult(self):
        return 0.5 if self.tiene("pulso") else 1.0

    def dano_pistola(self):
        return 40 if self.tiene("balas") else DANO_PISTOLA

    def vision_mult(self):
        return 0.75 if self.tiene("perfil") else 1.0

    def velocidad_mult(self):
        return 1.15 if self.tiene("pies") else 1.0

    def calma_mult(self):
        """Multiplica la velocidad a la que decae la búsqueda."""
        return 2.0 if self.tiene("fantasma") else 1.0
