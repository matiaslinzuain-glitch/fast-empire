# =========================================================
# FAST EMPIRE — Diálogos  [Fase 6]
#
# - DIALOGOS: las conversaciones definidas como datos (lista
#   de líneas {quien, texto}). Escribir historia nueva es
#   agregar entradas acá, sin tocar lógica.
# - CajaDialogo: panel inferior con efecto máquina de
#   escribir. E/Enter/click: si la línea se está tipeando la
#   completa; si ya terminó, pasa a la siguiente. Al agotar
#   las líneas devuelve "fin" (main.py decide qué desbloquea
#   cada diálogo).
# =========================================================

import pygame

from .settings import (
    ANCHO_VENTANA, ALTO_VENTANA,
    COLOR_TEXTO, COLOR_TEXTO_SUAVE, COLOR_ORO, COLOR_PUNTO,
)

VELOCIDAD_TIPEO = 45  # caracteres por segundo

# Color del nombre según el personaje
COLORES_HABLANTE = {
    "Walter": (196, 164, 120),
    "El Proveedor": COLOR_PUNTO,
    "???": COLOR_PUNTO,
    "Don Aldo": (222, 178, 84),
}

DIALOGOS = {
    "proveedor_intro": [
        {"quien": "???",
         "texto": "Lindo local. La gente hace fila, habla bien de tu comida..."},
        {"quien": "Walter",
         "texto": "¿Y usted quién es? Estamos por cerrar."},
        {"quien": "El Proveedor",
         "texto": "Alguien que sabe leer números. Un local así no paga los "
                  "remedios de un hombre enfermo. Ni le deja nada a su familia."},
        {"quien": "El Proveedor",
         "texto": "Yo consigo 'medicamentos'. Naturales y químicos. Vos los "
                  "pedís por tu teléfono y te llegan en cajas, como todo lo demás."},
        {"quien": "El Proveedor",
         "texto": "Se venden donde no mira nadie: el punto va rotando por la "
                  "ciudad y el campo. Seguí la marca violeta. Poca gente, "
                  "mucha plata."},
        {"quien": "El Proveedor",
         "texto": "Ah, y los que ya trabajan esas zonas no van a estar "
                  "contentos. Vos verás cómo lo resolvés."},
        {"quien": "Walter",
         "texto": "...Es por mi familia. Nada más."},
    ],
    "proveedor_mision": [
        {"quien": "El Proveedor",
         "texto": "¿Tenés un minuto? Tengo un trabajito para alguien de "
                  "confianza. Nada del otro mundo... para vos."},
        {"quien": "El Proveedor",
         "texto": "Los detalles quedan entre nosotros. Cumplí en tiempo y "
                  "forma, pagá derecho, y va a haber más."},
        {"quien": "Walter",
         "texto": "Decime qué hay que hacer."},
    ],
    "proveedor_receta": [
        {"quien": "El Proveedor",
         "texto": "Bien hecho. Me gusta la gente que cumple. Tomá: esto no "
                  "es plata... es algo mejor."},
        {"quien": "El Proveedor",
         "texto": "Mi vieja receta. Especias del puerto, fuego bajo, y esa "
                  "cosa que vos ya sabés hacer. Cobrala como se merece."},
        {"quien": "Walter",
         "texto": "...Gracias. Esta la cocino yo."},
    ],
    "almacenero": [
        {"quien": "Don Aldo",
         "texto": "¡Walter! ¿Cómo va ese local? Acá tengo de todo: fierros "
                  "para cuidarte y sanguches para remendarte."},
        {"quien": "Don Aldo",
         "texto": "¿Un consejo gratis? Hay tres puestos en alquiler: en el "
                  "mercado, en el campo y en el baldío del sur. Plata que "
                  "entra sola todas las semanas."},
        {"quien": "Don Aldo",
         "texto": "El tema es que los que 'trabajan' esas zonas no se van a "
                  "ir con un apretón de manos. Si desaparecieran un rato... "
                  "el puesto se compra rápido, ¿me entendés?"},
        {"quien": "Walter",
         "texto": "Le entiendo perfecto, Aldo."},
    ],
}


class CajaDialogo:
    def __init__(self):
        self.fuente_nombre = pygame.font.Font(None, 28)
        self.fuente = pygame.font.Font(None, 26)
        self.fuente_chica = pygame.font.Font(None, 20)
        self.id_actual = None
        self.lineas = []
        self.indice = 0
        self.visibles = 0.0  # caracteres ya "tipeados" de la línea actual

    def abrir(self, id_dialogo):
        self.id_actual = id_dialogo
        self.lineas = DIALOGOS[id_dialogo]
        self.indice = 0
        self.visibles = 0.0

    @property
    def _linea(self):
        return self.lineas[self.indice]

    def actualizar(self, dt):
        self.visibles = min(len(self._linea["texto"]),
                            self.visibles + VELOCIDAD_TIPEO * dt)

    def manejar_evento(self, evento):
        """Devuelve "fin" cuando se agotó el diálogo; None si sigue."""
        avanzar = (
            (evento.type == pygame.KEYDOWN and evento.key in (
                pygame.K_e, pygame.K_RETURN, pygame.K_SPACE))
            or (evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1)
        )
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
            return "fin"  # se puede saltear la charla
        if not avanzar:
            return None
        if self.visibles < len(self._linea["texto"]):
            self.visibles = len(self._linea["texto"])  # completar la línea
            return None
        self.indice += 1
        self.visibles = 0.0
        if self.indice >= len(self.lineas):
            return "fin"
        return None

    def _envolver(self, texto, ancho_max):
        """Corta el texto en renglones que entren en el panel."""
        renglones, actual = [], ""
        for palabra in texto.split(" "):
            prueba = f"{actual} {palabra}".strip()
            if self.fuente.size(prueba)[0] <= ancho_max:
                actual = prueba
            else:
                renglones.append(actual)
                actual = palabra
        if actual:
            renglones.append(actual)
        return renglones

    def dibujar(self, superficie):
        alto = 132
        panel = pygame.Surface((ANCHO_VENTANA - 40, alto), pygame.SRCALPHA)
        panel.fill((10, 10, 14, 235))
        x, y = 20, ALTO_VENTANA - alto - 16
        superficie.blit(panel, (x, y))
        pygame.draw.rect(superficie, (70, 70, 78),
                         (x, y, ANCHO_VENTANA - 40, alto), 1)

        linea = self._linea
        color_nombre = COLORES_HABLANTE.get(linea["quien"], COLOR_TEXTO)
        nombre = self.fuente_nombre.render(linea["quien"], True, color_nombre)
        superficie.blit(nombre, (x + 16, y + 10))

        texto_visible = linea["texto"][:int(self.visibles)]
        ty = y + 40
        for renglon in self._envolver(texto_visible, ANCHO_VENTANA - 92):
            superficie.blit(self.fuente.render(renglon, True, COLOR_TEXTO),
                            (x + 16, ty))
            ty += 26

        completa = self.visibles >= len(linea["texto"])
        pista = "E — siguiente" if completa else "E — completar"
        pista += f"   ·   {self.indice + 1}/{len(self.lineas)}   ·   ESC saltear"
        img = self.fuente_chica.render(pista, True, COLOR_TEXTO_SUAVE)
        superficie.blit(img, (x + ANCHO_VENTANA - 60 - img.get_width(),
                              y + alto - 24))
        if completa:
            pygame.draw.polygon(superficie, COLOR_ORO, [
                (x + 20, y + alto - 22), (x + 32, y + alto - 22),
                (x + 26, y + alto - 12)])
