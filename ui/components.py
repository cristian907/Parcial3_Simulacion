"""
Componentes reutilizables de Interfaz Gráfica para Pygame (Botones, Steppers, Tarjetas).
Universidad José Antonio Páez - Parcial III Simulación.
"""

import pygame
from typing import Tuple, Optional, Callable


class UIButton:
    """Botón interactivo con estados normal, hover y active."""

    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        callback: Optional[Callable] = None,
        bg_color: Tuple[int, int, int] = (59, 130, 246),       # Blue 500
        hover_color: Tuple[int, int, int] = (96, 165, 250),    # Blue 400
        text_color: Tuple[int, int, int] = (255, 255, 255),
        border_color: Tuple[int, int, int] = (51, 65, 85),
        border_radius: int = 8,
        font_size: int = 15
    ):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.border_color = border_color
        self.border_radius = border_radius
        self.font_size = font_size
        self.is_hovered = False
        self.is_active = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.callback:
                    self.callback()
                return True
        return False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        col = self.hover_color if self.is_hovered else self.bg_color
        pygame.draw.rect(surface, col, self.rect, border_radius=self.border_radius)
        
        # Borde
        b_col = (6, 182, 212) if self.is_active else self.border_color
        pygame.draw.rect(surface, b_col, self.rect, width=1, border_radius=self.border_radius)

        txt_surf = font.render(self.text, True, self.text_color)
        t_rect = txt_surf.get_rect(center=self.rect.center)
        surface.blit(txt_surf, t_rect)


class UIStepper:
    """Control de ajuste numérico con botones [-] y [+] para modificar parámetros en la GUI."""

    def __init__(
        self,
        rect: pygame.Rect,
        label: str,
        value: float,
        step: float = 1.0,
        min_val: float = 0.1,
        max_val: float = 1000.0,
        is_float: bool = False,
        unit: str = ""
    ):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.value = value
        self.step = step
        self.min_val = min_val
        self.max_val = max_val
        self.is_float = is_float
        self.unit = unit

        # Botones [-] y [+]
        btn_w = 32
        self.btn_minus = UIButton(
            pygame.Rect(self.rect.right - 2 * btn_w - 6, self.rect.y + 2, btn_w, self.rect.height - 4),
            "-",
            callback=self._decrement,
            bg_color=(51, 65, 85),
            hover_color=(71, 85, 105)
        )
        self.btn_plus = UIButton(
            pygame.Rect(self.rect.right - btn_w, self.rect.y + 2, btn_w, self.rect.height - 4),
            "+",
            callback=self._increment,
            bg_color=(51, 65, 85),
            hover_color=(71, 85, 105)
        )

    def _decrement(self):
        self.value = max(self.min_val, self.value - self.step)
        if not self.is_float:
            self.value = round(self.value)

    def _increment(self):
        self.value = min(self.max_val, self.value + self.step)
        if not self.is_float:
            self.value = round(self.value)

    def handle_event(self, event: pygame.event.Event) -> bool:
        c1 = self.btn_minus.handle_event(event)
        c2 = self.btn_plus.handle_event(event)
        return c1 or c2

    def draw(self, surface: pygame.Surface, font_label: pygame.font.Font, font_val: pygame.font.Font):
        # Fondo del stepper
        pygame.draw.rect(surface, (30, 41, 59), self.rect, border_radius=6)
        pygame.draw.rect(surface, (51, 65, 85), self.rect, width=1, border_radius=6)

        # Etiqueta
        lbl_surf = font_label.render(self.label, True, (241, 245, 249))
        surface.blit(lbl_surf, (self.rect.x + 12, self.rect.y + (self.rect.height - lbl_surf.get_height()) // 2))

        # Valor formateado
        if self.is_float:
            val_str = f"{self.value:.1f} {self.unit}".strip()
        else:
            val_str = f"{int(self.value)} {self.unit}".strip()

        v_surf = font_val.render(val_str, True, (6, 182, 212))
        v_x = self.btn_minus.rect.x - v_surf.get_width() - 15
        surface.blit(v_surf, (v_x, self.rect.y + (self.rect.height - v_surf.get_height()) // 2))

        # Botones
        self.btn_minus.draw(surface, font_label)
        self.btn_plus.draw(surface, font_label)
