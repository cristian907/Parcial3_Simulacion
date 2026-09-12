"""
Aplicacion Grafica Interactiva en Pygame - Parcial III: Simulacion.
Universidad Jose Antonio Paez - Facultad de Ingenieria.

Caracteristicas:
1. Configuracion separada e independiente para cada ejercicio (Fabrica de Laptops y Cluster Termico).
2. Barra de progreso dinamica para la Simulacion 1 (Progreso global y ensamble de orden actual).
3. 100% compatible con Linux (Sin emojis Unicode ni glifos faltantes, con iconos vectoriales y texto limpio).
4. Integracion exclusiva con Google Gemini mediante API Key en .env.
5. Visor de dictamen de IA integrado en pantalla con scroll y exportador .txt.
"""

import sys
import os
import math
import threading
import numpy as np
import pygame
from typing import Optional, List, Dict, Any

from core.discrete_sim import LaptopFactorySimulator
from core.continuous_sim import ThermalClusterSimulator
from core.models import StationStatus
from services.ai_service import AISimulationService
from services.reporter import SimulationReporter
from ui.components import UIButton, UIStepper


def draw_vector_bolt(surface: pygame.Surface, color: tuple, center: tuple, scale: float = 1.0):
    """Dibuja un rayo vectorial nitido para evitar emojis rotos en Linux."""
    cx, cy = center
    pts = [
        (cx - int(4 * scale), cy - int(20 * scale)),
        (cx + int(8 * scale), cy - int(20 * scale)),
        (cx + int(1 * scale), cy - int(2 * scale)),
        (cx + int(12 * scale), cy - int(2 * scale)),
        (cx - int(10 * scale), cy + int(22 * scale)),
        (cx - int(2 * scale), cy + int(3 * scale)),
        (cx - int(12 * scale), cy + int(3 * scale))
    ]
    pygame.draw.polygon(surface, color, pts)


def draw_vector_check(surface: pygame.Surface, color: tuple, center: tuple, scale: float = 1.0):
    """Dibuja una marca de verificacion vectorial OK."""
    cx, cy = center
    pts = [
        (cx - int(14 * scale), cy - int(2 * scale)),
        (cx - int(4 * scale), cy + int(10 * scale)),
        (cx + int(14 * scale), cy - int(12 * scale))
    ]
    pygame.draw.lines(surface, color, False, pts, int(4 * scale))


def draw_vector_stop(surface: pygame.Surface, color: tuple, center: tuple, scale: float = 1.0):
    """Dibuja un octagono de STOP vectorial para paradas de linea."""
    cx, cy = center
    r = int(22 * scale)
    pts = []
    for i in range(8):
        ang = math.radians(22.5 + i * 45)
        pts.append((cx + int(r * math.cos(ang)), cy + int(r * math.sin(ang))))
    pygame.draw.polygon(surface, color, pts)
    pygame.draw.line(surface, (255, 255, 255), (cx - int(12 * scale), cy), (cx + int(12 * scale), cy), int(5 * scale))


class PygameBonusVisualizer:
    """
    Controlador maestro de la Interfaz Grafica de Usuario (GUI) en Pygame.
    """

    WIDTH = 1180
    HEIGHT = 720
    FPS = 60

    # Estados de pantalla
    STATE_MENU = "MENU"
    STATE_SIMULATION = "SIMULATION"
    STATE_AI_REPORT = "AI_REPORT"

    # Paleta de colores Dark UI moderna
    BG_DARK = (15, 23, 42)          # Slate 900
    PANEL_BG = (30, 41, 59)         # Slate 800
    PANEL_BORDER = (51, 65, 85)     # Slate 700
    TEXT_MAIN = (241, 245, 249)     # Slate 100
    TEXT_MUTED = (148, 163, 184)    # Slate 400
    ACCENT_BLUE = (59, 130, 246)    # Blue 500
    ACCENT_CYAN = (6, 182, 212)     # Cyan 500
    COLOR_GREEN = (16, 185, 129)    # Emerald 500
    COLOR_AMBER = (245, 158, 11)    # Amber 500
    COLOR_RED = (239, 68, 68)       # Red 500

    def __init__(self):
        pygame.init()
        pygame.font.init()

        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("UJAP - Parcial III: Simulacion de Sistemas")
        self.clock = pygame.time.Clock()

        # Fuentes sin dependencias de glifos unicode
        self.font_big_title = pygame.font.SysFont("Arial", 25, bold=True)
        self.font_title = pygame.font.SysFont("Arial", 18, bold=True)
        self.font_bold = pygame.font.SysFont("Arial", 15, bold=True)
        self.font_regular = pygame.font.SysFont("Arial", 14)
        self.font_small = pygame.font.SysFont("Arial", 12)
        self.font_big = pygame.font.SysFont("Arial", 26, bold=True)
        self.font_huge = pygame.font.SysFont("Arial", 36, bold=True)

        # Estado de navegacion
        self.app_state = self.STATE_MENU
        self.menu_config_tab = 1  # 1: Ejercicio 1 (Laptops), 2: Ejercicio 2 (Cluster)
        self.current_sim_tab = 1  # 1: Laptops, 2: Cluster
        self.results_view_tab = 1  # 1: Ejercicio 1 en Menu de Resultados, 2: Ejercicio 2
        self.is_paused = False
        self.speed_multiplier = 1.0
        self.blink_counter = 0

        # Servicio de IA exclusivo Google Gemini 2.5 Flash (.env)
        self.ai_service = AISimulationService(provider="GEMINI")
        self.ai_loading = False
        self.ai_report_text = ""
        self.ai_report_ex1 = ""
        self.ai_report_ex2 = ""
        self.ai_status_msg = ""
        self.report_scroll_y = 0
        self.max_report_scroll = 0

        # Pestañas de seleccion de ejercicio en Menu Principal
        self.btn_tab_menu_ex1 = UIButton(pygame.Rect(50, 155, 260, 42), "EJERCICIO 1: FABRICA LAPTOPS", callback=lambda: self._set_menu_tab(1), bg_color=self.ACCENT_BLUE)
        self.btn_tab_menu_ex2 = UIButton(pygame.Rect(325, 155, 260, 42), "EJERCICIO 2: CLUSTER TERMICO", callback=lambda: self._set_menu_tab(2), bg_color=(51, 65, 85))
        self.btn_tab_menu_results = UIButton(pygame.Rect(600, 155, 290, 42), "VER RESULTADOS Y ANALISIS IA", callback=self._go_to_ai_report, bg_color=(124, 58, 237), hover_color=(109, 40, 217))

        # Configuracion Ejercicio 1: Fabrica de Laptops (Modo Infinito)
        self.stepper_lambda = UIStepper(pygame.Rect(70, 285, 480, 42), "Tasa Llegadas Poisson (Lambda)", 10.0, step=1.0, min_val=1.0, max_val=60.0, is_float=True, unit="ord/h")
        self.stepper_mu = UIStepper(pygame.Rect(70, 350, 480, 42), "Tiempo Ensamble Medio (Mu)", 5.0, step=0.5, min_val=1.0, max_val=30.0, is_float=True, unit="min")
        self.stepper_threshold = UIStepper(pygame.Rect(70, 415, 480, 42), "Umbral Critico de Reorden (s)", 10, step=1, min_val=1, max_val=40, is_float=False, unit="uds")
        self.stepper_batch = UIStepper(pygame.Rect(70, 480, 480, 42), "Tamano Lote Proveedor (Q)", 50, step=5, min_val=10, max_val=100, is_float=False, unit="uds")
        self.btn_start_sim1 = UIButton(pygame.Rect(70, 540, 480, 46), "> INICIAR SIMULACION 1: FABRICA", callback=lambda: self._on_start_simulation(tab=1), bg_color=self.ACCENT_BLUE, hover_color=(37, 99, 235), font_size=16)

        # Configuracion Ejercicio 2: Cluster Termico (Modo Infinito)
        self.stepper_mean_traffic = UIStepper(pygame.Rect(70, 285, 480, 42), "Trafico Medio Nominal (Mu)", 3.0, step=0.2, min_val=1.0, max_val=5.0, is_float=True, unit="Gbps")
        self.stepper_std_traffic = UIStepper(pygame.Rect(70, 350, 480, 42), "Desviacion Estandar (Sigma)", 1.0, step=0.1, min_val=0.1, max_val=2.0, is_float=True, unit="Gbps")
        self.stepper_target_temp = UIStepper(pygame.Rect(70, 415, 480, 42), "Temperatura de Diseno", 70.0, step=1.0, min_val=50.0, max_val=85.0, is_float=True, unit="C")
        self.stepper_amb_temp = UIStepper(pygame.Rect(70, 480, 480, 42), "Temperatura Ambiente", 25.0, step=1.0, min_val=10.0, max_val=40.0, is_float=True, unit="C")
        self.btn_start_sim2 = UIButton(pygame.Rect(70, 540, 480, 46), "> INICIAR SIMULACION 2: CLUSTER", callback=lambda: self._on_start_simulation(tab=2), bg_color=self.ACCENT_BLUE, hover_color=(37, 99, 235), font_size=16)

        # Botones de Barra Superior en Simulacion (Con boton de acelerar)
        self.btn_nav_menu = UIButton(pygame.Rect(15, 10, 95, 35), "< Menú", callback=self._go_to_menu, bg_color=(51, 65, 85))
        self.btn_nav_tab1 = UIButton(pygame.Rect(118, 10, 165, 35), "[1] Fábrica Laptops", callback=lambda: self._set_sim_tab(1), bg_color=self.ACCENT_BLUE)
        self.btn_nav_tab2 = UIButton(pygame.Rect(291, 10, 165, 35), "[2] Clúster Térmico", callback=lambda: self._set_sim_tab(2), bg_color=(51, 65, 85))
        self.btn_nav_ai_report = UIButton(pygame.Rect(464, 10, 175, 35), "[Resultados & IA]", callback=self._go_to_ai_report, bg_color=(124, 58, 237))
        self.btn_sim_speed = UIButton(pygame.Rect(647, 10, 120, 35), ">> Vel: 1x", callback=self._cycle_speed, bg_color=(51, 65, 85), hover_color=(37, 99, 235))
        self.btn_sim_pause = UIButton(pygame.Rect(775, 10, 85, 35), "Pausar", callback=self._toggle_pause, bg_color=(51, 65, 85))
        self.btn_sim_reset = UIButton(pygame.Rect(868, 10, 75, 35), "Reset", callback=self.reset_simulators, bg_color=(51, 65, 85))
        self.btn_sim_ask_ai = UIButton(pygame.Rect(951, 10, 214, 35), "[IA] Gemini 2.5 Flash", callback=self._trigger_ai_analysis, bg_color=self.COLOR_GREEN, hover_color=(5, 150, 105))

        # Botones de la Pantalla / Menu de Resultados y Analisis de IA
        self.btn_results_back_sim = UIButton(pygame.Rect(25, 12, 170, 40), "< Volver a Simulación", callback=self._go_to_simulation, bg_color=(51, 65, 85))
        self.btn_results_back_menu = UIButton(pygame.Rect(205, 12, 135, 40), "< Menú Principal", callback=self._go_to_menu, bg_color=(51, 65, 85))
        self.btn_results_tab_ex1 = UIButton(pygame.Rect(350, 12, 185, 40), "[1] Fábrica Laptops", callback=lambda: self._set_results_tab(1), bg_color=self.ACCENT_BLUE)
        self.btn_results_tab_ex2 = UIButton(pygame.Rect(545, 12, 185, 40), "[2] Clúster Térmico", callback=lambda: self._set_results_tab(2), bg_color=(51, 65, 85))
        self.btn_results_export = UIButton(pygame.Rect(740, 12, 180, 40), "[TXT] Guardar Reporte", callback=self._export_report_txt, bg_color=self.COLOR_GREEN, hover_color=(5, 150, 105))
        self.btn_results_run_ai = UIButton(pygame.Rect(930, 12, 225, 40), "[IA] Gemini 2.5 Flash", callback=self._trigger_ai_analysis, bg_color=self.COLOR_GREEN, hover_color=(5, 150, 105))
        self.btn_results_inline_ai = UIButton(pygame.Rect(650, 320, 430, 48), "> GENERAR ANALISIS CON GEMINI 2.5 FLASH", callback=self._trigger_ai_analysis, bg_color=self.ACCENT_BLUE, hover_color=(37, 99, 235), font_size=15)

        # Instancias de simulacion (Ambas son infinitas)
        self.discrete_sim = LaptopFactorySimulator(simulation_hours=float('inf'), seed=42)
        self.continuous_sim = ThermalClusterSimulator(simulation_hours=float('inf'), seed=42)

        # Historial para graficas continuas
        self.realtime_temp_history: List[float] = [70.0]
        self.realtime_traffic_history: List[float] = [3.0]
        self.realtime_throughput_history: List[float] = [2.7]
        self.max_history_points = 200

        self.toast_msg = ""
        self.toast_timer = 0

    def _set_menu_tab(self, tab: int):
        self.menu_config_tab = tab
        self.btn_tab_menu_ex1.bg_color = self.ACCENT_BLUE if tab == 1 else (51, 65, 85)
        self.btn_tab_menu_ex2.bg_color = self.ACCENT_BLUE if tab == 2 else (51, 65, 85)

    def _show_toast(self, msg: str):
        self.toast_msg = msg
        self.toast_timer = 180

    def _set_sim_tab(self, tab: int):
        self.current_sim_tab = tab
        self.btn_nav_tab1.bg_color = self.ACCENT_BLUE if tab == 1 else (51, 65, 85)
        self.btn_nav_tab2.bg_color = self.ACCENT_BLUE if tab == 2 else (51, 65, 85)

    def _go_to_menu(self):
        self.app_state = self.STATE_MENU

    def _go_to_simulation(self):
        self.app_state = self.STATE_SIMULATION

    def _go_to_ai_report(self):
        self.app_state = self.STATE_AI_REPORT
        self.results_view_tab = self.current_sim_tab
        self.report_scroll_y = 0
        self._sync_results_tab_buttons()

    def _set_results_tab(self, tab: int):
        self.results_view_tab = tab
        self.report_scroll_y = 0
        self._sync_results_tab_buttons()

    def _sync_results_tab_buttons(self):
        self.btn_results_tab_ex1.bg_color = self.ACCENT_BLUE if self.results_view_tab == 1 else (51, 65, 85)
        self.btn_results_tab_ex2.bg_color = self.ACCENT_BLUE if self.results_view_tab == 2 else (51, 65, 85)

    def _cycle_speed(self):
        """Alterna ciclicamente la velocidad de simulacion: 1x -> 2x -> 5x -> 10x -> 20x -> 1x."""
        speeds = [1.0, 2.0, 5.0, 10.0, 20.0]
        try:
            cur_idx = speeds.index(self.speed_multiplier)
            next_idx = (cur_idx + 1) % len(speeds)
        except ValueError:
            next_idx = 0
        self.speed_multiplier = speeds[next_idx]
        self._update_speed_btn_text()
        self._show_toast(f"Velocidad de simulacion acelerada: {int(self.speed_multiplier)}x")

    def _update_speed_btn_text(self):
        self.btn_sim_speed.text = f">> Vel: {int(self.speed_multiplier)}x"
        if self.speed_multiplier > 1.0:
            self.btn_sim_speed.bg_color = (37, 99, 235)
        else:
            self.btn_sim_speed.bg_color = (51, 65, 85)

    def _toggle_pause(self):
        self.is_paused = not self.is_paused
        self.btn_sim_pause.text = "Reanudar" if self.is_paused else "Pausar"

    def _init_discrete_sim(self):
        """Inicializa la simulacion de la Fabrica de Laptops con los valores actuales de los steppers."""
        lam = self.stepper_lambda.value
        mu_srv = self.stepper_mu.value
        thresh = int(self.stepper_threshold.value)
        batch = int(self.stepper_batch.value)
        self.discrete_sim = LaptopFactorySimulator(
            simulation_hours=float('inf'),
            arrival_rate_h=lam,
            service_mean_min=mu_srv,
            reorder_threshold=thresh,
            batch_size=batch,
            seed=42
        )

    def _init_continuous_sim(self):
        """Inicializa la simulacion del Cluster Termico con los valores actuales de los steppers."""
        mean_tr = self.stepper_mean_traffic.value
        std_tr = self.stepper_std_traffic.value
        tgt_t = self.stepper_target_temp.value
        amb_t = self.stepper_amb_temp.value
        self.continuous_sim = ThermalClusterSimulator(
            simulation_hours=float('inf'),
            mean_traffic_gbps=mean_tr,
            std_traffic_gbps=std_tr,
            target_temp_c=tgt_t,
            ambient_temp_c=amb_t,
            seed=42
        )
        self.realtime_temp_history = [tgt_t]
        self.realtime_traffic_history = [mean_tr]
        self.realtime_throughput_history = [mean_tr * 0.9]

    def _on_start_simulation(self, tab: Optional[int] = None):
        """Inicializa las simulaciones de forma independiente segun el ejercicio seleccionado."""
        if tab == 1:
            self._init_discrete_sim()
            self._set_sim_tab(1)
            self._show_toast("Fábrica de Laptops iniciada (Modo Infinito)")
        elif tab == 2:
            self._init_continuous_sim()
            self._set_sim_tab(2)
            self._show_toast("Clúster Térmico iniciado (Modo Infinito)")
        else:
            self._init_discrete_sim()
            self._init_continuous_sim()
            if tab is not None:
                self._set_sim_tab(tab)
            self._show_toast("Simulaciones iniciadas correctamente")

        self.app_state = self.STATE_SIMULATION

    def reset_simulators(self):
        """Reinicia unicamente la simulacion actualmente activa en pantalla."""
        if self.current_sim_tab == 1:
            self._init_discrete_sim()
            self._show_toast("Fábrica de Laptops reiniciada")
        else:
            self._init_continuous_sim()
            self._show_toast("Clúster Térmico reiniciado")

    def _trigger_ai_analysis(self):
        """Peticion a Google Gemini 2.5 Flash en segundo plano (thread) para mantener 60 FPS."""
        if self.ai_loading:
            return

        target_tab = self.results_view_tab if self.app_state == self.STATE_AI_REPORT else self.current_sim_tab
        self.ai_loading = True
        self.ai_status_msg = f"Consultando Google Gemini 2.5 Flash (Ejercicio {target_tab})..."
        self._show_toast(f"Consultando Gemini 2.5 Flash para Ejercicio {target_tab}...")

        def _worker():
            try:
                if target_tab == 1:
                    m = dict(self.discrete_sim.get_metrics())
                    traces_list = list(self.discrete_sim.traces)
                    traces_fmt = [t.formatted_line() for t in traces_list[:25]]
                    prob_name = "Simulación de Eventos Discretos: Fábrica de Laptops"
                    ai_res = self.ai_service.analyze_metrics(prob_name, m, traces_fmt)
                    self.ai_report_ex1 = ai_res
                    self.ai_report_text = ai_res
                    SimulationReporter.save_report_to_file(prob_name, m, ai_res, traces_list)
                    SimulationReporter.save_report_to_file(prob_name, m, ai_res, traces_list, filepath="reporte_simulacion_parcial3_problema1.txt")
                    SimulationReporter.save_report_to_file(prob_name, m, ai_res, traces_list, filepath="reporte_simulacion_parcial3p1.txt")
                else:
                    m = dict(self.continuous_sim.get_metrics())
                    traces_list = list(self.continuous_sim.traces)
                    traces_fmt = [t.formatted_line() for t in traces_list[:25]]
                    prob_name = "Simulación Continua: Clúster Térmico de Servidores"
                    ai_res = self.ai_service.analyze_metrics(prob_name, m, traces_fmt)
                    self.ai_report_ex2 = ai_res
                    self.ai_report_text = ai_res
                    SimulationReporter.save_report_to_file(prob_name, m, ai_res, traces_list)
                    SimulationReporter.save_report_to_file(prob_name, m, ai_res, traces_list, filepath="reporte_simulacion_parcial3_problema2.txt")
                    SimulationReporter.save_report_to_file(prob_name, m, ai_res, traces_list, filepath="reporte_simulacion_parcial3p2.txt")

                self.ai_status_msg = f"Dictamen Gemini 2.5 Flash (Ej. {target_tab}) completado con éxito"
                self._show_toast(f"Gemini 2.5 Flash: Dictamen de Ejercicio {target_tab} listo y guardado")
            except Exception as e:
                self.ai_status_msg = f"Error al consultar Gemini 2.5 Flash: {e}"
                self._show_toast(f"Error Gemini: {e}")
            finally:
                self.ai_loading = False

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def _export_report_txt(self):
        target_tab = self.results_view_tab if self.app_state == self.STATE_AI_REPORT else self.current_sim_tab
        report = self.ai_report_ex1 if target_tab == 1 else self.ai_report_ex2
        if not report:
            report = self.ai_report_text
        if not report:
            self._show_toast("Aviso: Primero consulte Gemini 2.5 Flash antes de exportar.")
            return

        prob_name = "Simulación de Eventos Discretos: Fábrica de Laptops" if target_tab == 1 else "Simulación Continua: Clúster Térmico de Servidores"
        m = dict(self.discrete_sim.get_metrics() if target_tab == 1 else self.continuous_sim.get_metrics())
        traces = list(self.discrete_sim.traces if target_tab == 1 else self.continuous_sim.traces)

        path = SimulationReporter.save_report_to_file(prob_name, m, report, traces)
        SimulationReporter.save_report_to_file(prob_name, m, report, traces, filepath=f"reporte_simulacion_parcial3_problema{target_tab}.txt")
        SimulationReporter.save_report_to_file(prob_name, m, report, traces, filepath=f"reporte_simulacion_parcial3p{target_tab}.txt")
        self._show_toast(f"Reporte exportado en: {os.path.basename(path)}")

    def run(self):
        """Bucle principal de la aplicacion."""
        running = True
        while running:
            dt = self.clock.tick(self.FPS) / 1000.0
            self.blink_counter = (self.blink_counter + 1) % 60
            if self.toast_timer > 0:
                self.toast_timer -= 1

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.app_state == self.STATE_AI_REPORT:
                            self.app_state = self.STATE_SIMULATION
                        elif self.app_state == self.STATE_SIMULATION:
                            self.app_state = self.STATE_MENU
                        else:
                            running = False
                    elif event.key == pygame.K_SPACE and self.app_state == self.STATE_SIMULATION:
                        self._toggle_pause()
                    elif event.key == pygame.K_1 and self.app_state == self.STATE_SIMULATION:
                        self._set_sim_tab(1)
                    elif event.key == pygame.K_2 and self.app_state == self.STATE_SIMULATION:
                        self._set_sim_tab(2)
                    elif event.key == pygame.K_UP and self.app_state == self.STATE_SIMULATION:
                        speeds = [1.0, 2.0, 5.0, 10.0, 20.0]
                        cur = self.speed_multiplier
                        idx = speeds.index(cur) if cur in speeds else 0
                        self.speed_multiplier = speeds[min(len(speeds) - 1, idx + 1)]
                        self._update_speed_btn_text()
                        self._show_toast(f"Velocidad: {int(self.speed_multiplier)}x")
                    elif event.key == pygame.K_DOWN and self.app_state == self.STATE_SIMULATION:
                        speeds = [1.0, 2.0, 5.0, 10.0, 20.0]
                        cur = self.speed_multiplier
                        idx = speeds.index(cur) if cur in speeds else 0
                        self.speed_multiplier = speeds[max(0, idx - 1)]
                        self._update_speed_btn_text()
                        self._show_toast(f"Velocidad: {int(self.speed_multiplier)}x")

                elif event.type == pygame.MOUSEWHEEL and self.app_state == self.STATE_AI_REPORT:
                    self.report_scroll_y = max(0, min(self.max_report_scroll, self.report_scroll_y - event.y * 30))

                # Gestion de eventos de UI
                if self.app_state == self.STATE_MENU:
                    self.btn_tab_menu_ex1.handle_event(event)
                    self.btn_tab_menu_ex2.handle_event(event)
                    self.btn_tab_menu_results.handle_event(event)

                    if self.menu_config_tab == 1:
                        self.stepper_lambda.handle_event(event)
                        self.stepper_mu.handle_event(event)
                        self.stepper_threshold.handle_event(event)
                        self.stepper_batch.handle_event(event)
                        self.btn_start_sim1.handle_event(event)
                    else:
                        self.stepper_mean_traffic.handle_event(event)
                        self.stepper_std_traffic.handle_event(event)
                        self.stepper_target_temp.handle_event(event)
                        self.stepper_amb_temp.handle_event(event)
                        self.btn_start_sim2.handle_event(event)

                elif self.app_state == self.STATE_SIMULATION:
                    self.btn_nav_menu.handle_event(event)
                    self.btn_nav_tab1.handle_event(event)
                    self.btn_nav_tab2.handle_event(event)
                    self.btn_nav_ai_report.handle_event(event)
                    self.btn_sim_speed.handle_event(event)
                    self.btn_sim_pause.handle_event(event)
                    self.btn_sim_reset.handle_event(event)
                    self.btn_sim_ask_ai.handle_event(event)

                elif self.app_state == self.STATE_AI_REPORT:
                    self.btn_results_back_sim.handle_event(event)
                    self.btn_results_back_menu.handle_event(event)
                    self.btn_results_tab_ex1.handle_event(event)
                    self.btn_results_tab_ex2.handle_event(event)
                    self.btn_results_export.handle_event(event)
                    self.btn_results_run_ai.handle_event(event)
                    self.btn_results_inline_ai.handle_event(event)

            # Logica de actualizacion continua sincronizada
            if self.app_state == self.STATE_SIMULATION and not self.is_paused:
                # Problema 1: dt_disc en minutos (2.0 min/s en tiempo real = 120 s/s simulados)
                dt_disc = (dt * 2.0) * self.speed_multiplier
                self.discrete_sim.step(dt_disc)

                # Problema 2: dt_cont en segundos (120.0 s/s en tiempo real = 2.0 min/s simulados)
                dt_cont = (dt * 120.0) * self.speed_multiplier
                self.continuous_sim.step(dt_cont)

                self.realtime_temp_history.append(self.continuous_sim.current_temperature_c)
                self.realtime_traffic_history.append(self.continuous_sim.current_traffic_gbps)
                self.realtime_throughput_history.append(self.continuous_sim.current_throughput_gbps)
                if len(self.realtime_temp_history) > self.max_history_points:
                    self.realtime_temp_history.pop(0)
                    self.realtime_traffic_history.pop(0)
                    self.realtime_throughput_history.pop(0)

            # Dibujado
            if self.app_state == self.STATE_MENU:
                self._draw_menu_screen()
            elif self.app_state == self.STATE_SIMULATION:
                self._draw_simulation_screen()
            elif self.app_state == self.STATE_AI_REPORT:
                self._draw_ai_report_screen()

            if self.toast_timer > 0 and self.toast_msg:
                self._draw_toast()

            pygame.display.flip()

        pygame.quit()

    def _draw_toast(self):
        toast_surf = self.font_bold.render(self.toast_msg, True, (255, 255, 255))
        tw = toast_surf.get_width() + 30
        th = 38
        tr = pygame.Rect((self.WIDTH - tw) // 2, self.HEIGHT - 65, tw, th)
        pygame.draw.rect(self.screen, (16, 185, 129), tr, border_radius=19)
        pygame.draw.rect(self.screen, (255, 255, 255), tr, width=1, border_radius=19)
        self.screen.blit(toast_surf, (tr.x + 15, tr.y + 10))

    # =========================================================================
    # PANTALLA 1: MENU CON CONFIGURACION SEPARADA POR EJERCICIO
    # =========================================================================
    def _draw_menu_screen(self):
        self.screen.fill(self.BG_DARK)

        # Encabezado
        header_rect = pygame.Rect(40, 20, self.WIDTH - 80, 105)
        pygame.draw.rect(self.screen, self.PANEL_BG, header_rect, border_radius=12)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, header_rect, width=1, border_radius=12)

        u_title = self.font_big_title.render("UNIVERSIDAD JOSE ANTONIO PAEZ - FACULTAD DE INGENIERIA", True, self.TEXT_MAIN)
        self.screen.blit(u_title, (header_rect.x + 25, header_rect.y + 15))

        sub_title = self.font_title.render("Simulador Grafico de Sistemas: Eventos Discretos, Continuo e Inteligencia Artificial", True, self.ACCENT_CYAN)
        self.screen.blit(sub_title, (header_rect.x + 25, header_rect.y + 48))

        eval_txt = self.font_small.render("Parcial III - Trabajo Practico | Programacion Orientada a Objetos, Simulacion Dinamica e IA", True, self.TEXT_MUTED)
        # Pestañas de separacion de configuracion y acceso a resultados
        self.btn_tab_menu_ex1.draw(self.screen, self.font_bold)
        self.btn_tab_menu_ex2.draw(self.screen, self.font_bold)
        self.btn_tab_menu_results.draw(self.screen, self.font_bold)

        if self.menu_config_tab == 1:
            self._draw_menu_tab_exercise_1()
        else:
            self._draw_menu_tab_exercise_2()

    def _draw_menu_tab_exercise_1(self):
        """Configuracion separada para el Ejercicio 1 (Fabrica de Laptops)."""
        # Panel Izquierdo: Parametros de Laptops
        p_cfg = pygame.Rect(50, 210, 520, 480)
        pygame.draw.rect(self.screen, self.PANEL_BG, p_cfg, border_radius=12)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, p_cfg, width=1, border_radius=12)

        title = self.font_title.render("PARAMETROS: FABRICA DE LAPTOPS", True, self.ACCENT_BLUE)
        self.screen.blit(title, (p_cfg.x + 25, p_cfg.y + 15))

        desc = self.font_small.render("Ajuste los valores con [+] y [-] o use los valores estandar de la prueba:", True, self.TEXT_MUTED)
        self.screen.blit(desc, (p_cfg.x + 25, p_cfg.y + 42))

        self.stepper_lambda.draw(self.screen, self.font_regular, self.font_bold)
        self.stepper_mu.draw(self.screen, self.font_regular, self.font_bold)
        self.stepper_threshold.draw(self.screen, self.font_regular, self.font_bold)
        self.stepper_batch.draw(self.screen, self.font_regular, self.font_bold)
        self.btn_start_sim1.draw(self.screen, self.font_title)

        # Banner Informativo de Modo Infinito
        inf_card = pygame.Rect(p_cfg.x + 20, 600, 480, 72)
        pygame.draw.rect(self.screen, (15, 25, 40), inf_card, border_radius=8)
        pygame.draw.rect(self.screen, (30, 60, 90), inf_card, width=1, border_radius=8)
        pygame.draw.circle(self.screen, self.COLOR_GREEN, (inf_card.x + 18, inf_card.y + 22), 5)
        self.screen.blit(self.font_bold.render("MODO DE SIMULACION: CONTINUA INFINITA", True, self.COLOR_GREEN), (inf_card.x + 32, inf_card.y + 13))
        self.screen.blit(self.font_small.render("Ejecucion en tiempo real sin limite de tiempo preestablecido.", True, self.TEXT_MAIN), (inf_card.x + 18, inf_card.y + 36))
        self.screen.blit(self.font_small.render("El proceso corre continuamente hasta pausarlo, reiniciarlo o salir.", True, self.TEXT_MUTED), (inf_card.x + 18, inf_card.y + 53))

        # Panel Derecho: Descripcion del Modelo y Conexion Gemini
        p_info = pygame.Rect(590, 210, 540, 480)
        pygame.draw.rect(self.screen, self.PANEL_BG, p_info, border_radius=12)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, p_info, width=1, border_radius=12)

        self.screen.blit(self.font_title.render("DETALLES DEL MODELO: EVENTOS DISCRETOS", True, self.ACCENT_CYAN), (p_info.x + 25, p_info.y + 15))

        card = pygame.Rect(p_info.x + 20, p_info.y + 48, 500, 195)
        pygame.draw.rect(self.screen, (20, 30, 45), card, border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, card, width=1, border_radius=8)

        self.screen.blit(self.font_bold.render("Especificaciones de la Linea de Produccion:", True, self.COLOR_GREEN), (card.x + 15, card.y + 12))
        self.screen.blit(self.font_small.render("- Arribo de peticiones: Proceso de Poisson a 10 ordenes/hora.", True, self.TEXT_MAIN), (card.x + 15, card.y + 35))
        self.screen.blit(self.font_small.render("- Estacion de ensamble: Tiempo exponencial con media de 5.0 min/laptop.", True, self.TEXT_MAIN), (card.x + 15, card.y + 55))
        self.screen.blit(self.font_small.render("- Gestion de inventario: Cada laptop requiere 1 procesador de gama alta.", True, self.TEXT_MAIN), (card.x + 15, card.y + 75))
        self.screen.blit(self.font_small.render("- Umbral de reorden: Pedido automatico al caer por debajo de 10 unidades.", True, self.TEXT_MAIN), (card.x + 15, card.y + 95))
        self.screen.blit(self.font_small.render("- Proveedor: Lote de 50 procesadores con entrega en 15 minutos.", True, self.TEXT_MAIN), (card.x + 15, card.y + 115))
        self.screen.blit(self.font_small.render("- Detencion de linea: Starvation si stock = 0 al requerir ensamble.", True, self.COLOR_AMBER), (card.x + 15, card.y + 135))
        self.screen.blit(self.font_small.render("- Metricas: Tiempo espera promedio, despacho de lote y paradas de linea.", True, self.ACCENT_CYAN), (card.x + 15, card.y + 158))

        # Tarjeta Google Gemini
        card_ai = pygame.Rect(p_info.x + 20, p_info.y + 258, 500, 200)
        pygame.draw.rect(self.screen, (20, 30, 45), card_ai, border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, card_ai, width=1, border_radius=8)

        self.screen.blit(self.font_bold.render("INTELIGENCIA ARTIFICIAL (GOOGLE GEMINI):", True, self.ACCENT_CYAN), (card_ai.x + 15, card_ai.y + 15))
        pygame.draw.circle(self.screen, self.COLOR_GREEN, (card_ai.x + 22, card_ai.y + 46), 5)
        self.screen.blit(self.font_small.render("Conexion Activa: API de Google Gemini (Key cargada desde .env)", True, self.COLOR_GREEN), (card_ai.x + 35, card_ai.y + 39))

        self.screen.blit(self.font_small.render(f"- Modelo de IA: {self.ai_service.gemini_model}", True, self.TEXT_MAIN), (card_ai.x + 15, card_ai.y + 68))
        self.screen.blit(self.font_small.render("- Analisis post-simulacion: Diagnostico de utilizacion, colas y cuellos de botella.", True, self.TEXT_MAIN), (card_ai.x + 15, card_ai.y + 92))
        self.screen.blit(self.font_small.render("- Genera 3 recomendaciones de optimizacion formalmente cuantificadas.", True, self.TEXT_MAIN), (card_ai.x + 15, card_ai.y + 115))
        self.screen.blit(self.font_small.render("- Guardado oficial directo en: reporte_simulacion_parcial3.txt", True, self.ACCENT_BLUE), (card_ai.x + 15, card_ai.y + 140))

    def _draw_menu_tab_exercise_2(self):
        """Configuracion separada para el Ejercicio 2 (Cluster Termico)."""
        # Panel Izquierdo: Parametros de Cluster
        p_cfg = pygame.Rect(50, 210, 520, 480)
        pygame.draw.rect(self.screen, self.PANEL_BG, p_cfg, border_radius=12)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, p_cfg, width=1, border_radius=12)

        title = self.font_title.render("PARAMETROS: CLUSTER TERMICO", True, self.ACCENT_BLUE)
        self.screen.blit(title, (p_cfg.x + 25, p_cfg.y + 15))

        desc = self.font_small.render("Ajuste los valores con [+] y [-] o use los valores estandar de la prueba:", True, self.TEXT_MUTED)
        self.screen.blit(desc, (p_cfg.x + 25, p_cfg.y + 42))

        self.stepper_mean_traffic.draw(self.screen, self.font_regular, self.font_bold)
        self.stepper_std_traffic.draw(self.screen, self.font_regular, self.font_bold)
        self.stepper_target_temp.draw(self.screen, self.font_regular, self.font_bold)
        self.stepper_amb_temp.draw(self.screen, self.font_regular, self.font_bold)
        self.btn_start_sim2.draw(self.screen, self.font_title)

        # Banner Informativo de Modo Infinito
        inf_card = pygame.Rect(p_cfg.x + 20, 600, 480, 72)
        pygame.draw.rect(self.screen, (15, 25, 40), inf_card, border_radius=8)
        pygame.draw.rect(self.screen, (30, 60, 90), inf_card, width=1, border_radius=8)
        pygame.draw.circle(self.screen, self.COLOR_GREEN, (inf_card.x + 18, inf_card.y + 22), 5)
        self.screen.blit(self.font_bold.render("MODO DE SIMULACION: CONTINUA INFINITA (RK4)", True, self.COLOR_GREEN), (inf_card.x + 32, inf_card.y + 13))
        self.screen.blit(self.font_small.render("Integracion diferencial continua en tiempo real sin fin preestablecido.", True, self.TEXT_MAIN), (inf_card.x + 18, inf_card.y + 36))
        self.screen.blit(self.font_small.render("Balance termico y throttling monitoreados en ejecucion permanente.", True, self.TEXT_MUTED), (inf_card.x + 18, inf_card.y + 53))

        # Panel Derecho: Descripcion del Modelo y Conexion Gemini
        p_info = pygame.Rect(590, 210, 540, 480)
        pygame.draw.rect(self.screen, self.PANEL_BG, p_info, border_radius=12)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, p_info, width=1, border_radius=12)

        self.screen.blit(self.font_title.render("DETALLES DEL MODELO: SIMULACION CONTINUA", True, self.ACCENT_CYAN), (p_info.x + 25, p_info.y + 15))

        card = pygame.Rect(p_info.x + 20, p_info.y + 48, 500, 195)
        pygame.draw.rect(self.screen, (20, 30, 45), card, border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, card, width=1, border_radius=8)

        self.screen.blit(self.font_bold.render("Especificaciones Termicas y Throughput:", True, self.COLOR_AMBER), (card.x + 15, card.y + 12))
        self.screen.blit(self.font_small.render("- Trafico de entrada: Normal(mu=3.0, sigma=1.0) Gbps en rango [1, 5] Gbps.", True, self.TEXT_MAIN), (card.x + 15, card.y + 35))
        self.screen.blit(self.font_small.render("- Balance termico: Ecuacion diferencial de 1er orden (dT/dt = Q_gen - Q_dis).", True, self.TEXT_MAIN), (card.x + 15, card.y + 55))
        self.screen.blit(self.font_small.render("- Integrador numerico: Runge-Kutta de 4to Orden (RK4) continuo.", True, self.TEXT_MAIN), (card.x + 15, card.y + 75))
        self.screen.blit(self.font_small.render("- Equilibrio de diseno: 70 C para trafico nominal con 90% de eficiencia.", True, self.TEXT_MAIN), (card.x + 15, card.y + 95))
        self.screen.blit(self.font_small.render("- Thermal Throttling: Se activa cuando T > 70 C degradando el Throughput.", True, self.COLOR_RED), (card.x + 15, card.y + 115))
        self.screen.blit(self.font_small.render("- Evaluacion de viabilidad: Comprobar estabilidad termica sin descontrol.", True, self.ACCENT_CYAN), (card.x + 15, card.y + 138))
        self.screen.blit(self.font_small.render("- Metricas: Terabytes totales, variabilidad de temperatura y % en throttling.", True, self.TEXT_MUTED), (card.x + 15, card.y + 158))

        # Tarjeta Google Gemini
        card_ai = pygame.Rect(p_info.x + 20, p_info.y + 258, 500, 200)
        pygame.draw.rect(self.screen, (20, 30, 45), card_ai, border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, card_ai, width=1, border_radius=8)

        self.screen.blit(self.font_bold.render("INTELIGENCIA ARTIFICIAL (GOOGLE GEMINI):", True, self.ACCENT_CYAN), (card_ai.x + 15, card_ai.y + 15))
        pygame.draw.circle(self.screen, self.COLOR_GREEN, (card_ai.x + 22, card_ai.y + 46), 5)
        self.screen.blit(self.font_small.render("Conexion Activa: API de Google Gemini (Key cargada desde .env)", True, self.COLOR_GREEN), (card_ai.x + 35, card_ai.y + 39))

        self.screen.blit(self.font_small.render(f"- Modelo de IA: {self.ai_service.gemini_model}", True, self.TEXT_MAIN), (card_ai.x + 15, card_ai.y + 68))
        self.screen.blit(self.font_small.render("- Analisis termodinamico: Perdida por estrangulamiento y deficit en TB.", True, self.TEXT_MAIN), (card_ai.x + 15, card_ai.y + 92))
        self.screen.blit(self.font_small.render("- Emite 3 recomendaciones (Control predictivo, HVAC y traffic shaping).", True, self.TEXT_MAIN), (card_ai.x + 15, card_ai.y + 115))
        self.screen.blit(self.font_small.render("- Guardado oficial directo en: reporte_simulacion_parcial3.txt", True, self.ACCENT_BLUE), (card_ai.x + 15, card_ai.y + 140))

    # =========================================================================
    # PANTALLA 2: SIMULACION INTERACTIVA EN TIEMPO REAL
    # =========================================================================
    def _draw_simulation_screen(self):
        self.screen.fill(self.BG_DARK)

        # Barra Superior
        top_bar = pygame.Rect(0, 0, self.WIDTH, 55)
        pygame.draw.rect(self.screen, self.PANEL_BG, top_bar)
        pygame.draw.line(self.screen, self.PANEL_BORDER, (0, 55), (self.WIDTH, 55), 2)

        self.btn_nav_menu.draw(self.screen, self.font_bold)
        self.btn_nav_tab1.draw(self.screen, self.font_bold)
        self.btn_nav_tab2.draw(self.screen, self.font_bold)
        self.btn_nav_ai_report.draw(self.screen, self.font_bold)
        self.btn_sim_speed.draw(self.screen, self.font_bold)

        self.btn_sim_pause.draw(self.screen, self.font_bold)
        self.btn_sim_reset.draw(self.screen, self.font_bold)

        if self.ai_loading:
            self.btn_sim_ask_ai.text = "[...] Gemini 2.5 Flash"
            self.btn_sim_ask_ai.bg_color = self.COLOR_AMBER
        else:
            self.btn_sim_ask_ai.text = "[IA] Gemini 2.5 Flash"
            self.btn_sim_ask_ai.bg_color = self.COLOR_GREEN
        self.btn_sim_ask_ai.draw(self.screen, self.font_bold)

        if self.current_sim_tab == 1:
            self._draw_discrete_simulation_view()
        else:
            self._draw_continuous_simulation_view()

    def _draw_discrete_simulation_view(self):
        """Vista grafica del Problema 1 en Modo Infinito Continuo en Tiempo Real."""
        sim = self.discrete_sim

        # =====================================================================
        # PANEL DE ESTADO EN TIEMPO REAL (MODO INFINITO CONTINUO)
        # =====================================================================
        prog_panel = pygame.Rect(25, 65, 1130, 45)
        pygame.draw.rect(self.screen, self.PANEL_BG, prog_panel, border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, prog_panel, width=1, border_radius=8)

        # Indicador de estado activo (pulsante)
        pulse = (self.blink_counter // 20) % 2 == 0
        dot_col = self.COLOR_GREEN if (not self.is_paused and pulse) else (30, 150, 80)
        if self.is_paused:
            dot_col = self.COLOR_AMBER
        pygame.draw.circle(self.screen, dot_col, (prog_panel.x + 22, prog_panel.centery), 6)

        mode_str = "MODO INFINITO EN VIVO" if not self.is_paused else "SIMULACION PAUSADA"
        mode_col = self.COLOR_GREEN if not self.is_paused else self.COLOR_AMBER
        self.screen.blit(self.font_bold.render(mode_str, True, mode_col), (prog_panel.x + 36, prog_panel.y + 13))

        # Tiempo transcurrido formateado
        elapsed_min = sim.current_time_min
        h_el = int(elapsed_min // 60)
        m_el = int(elapsed_min % 60)
        s_el = int((elapsed_min * 60) % 60)
        time_txt = f"Tiempo Transcurrido: {h_el:02d}h {m_el:02d}m {s_el:02d}s ({elapsed_min:.1f} min)"
        t_surf = self.font_bold.render(time_txt, True, self.ACCENT_CYAN)
        self.screen.blit(t_surf, (prog_panel.x + 270, prog_panel.y + 13))

        # Metricas clave en barra superior
        completed_count = len(sim.completed_orders)
        stats_txt = f"Completadas: {completed_count} | En Cola: {len(sim.order_queue)} | Stock: {sim.stock_level} uds"
        s_surf = self.font_small.render(stats_txt, True, self.TEXT_MAIN)
        self.screen.blit(s_surf, (prog_panel.right - s_surf.get_width() - 20, prog_panel.y + 14))

        # Barra sutil animada de actividad en el borde inferior
        if not self.is_paused:
            scan_pos = int((self.blink_counter * 6) % (prog_panel.width - 80))
            pygame.draw.line(self.screen, self.ACCENT_BLUE, (prog_panel.x + scan_pos, prog_panel.bottom - 2), (prog_panel.x + scan_pos + 80, prog_panel.bottom - 2), 2)

        # =====================================================================
        # 1. Panel Izquierdo: Cola de Ordenes
        # =====================================================================
        p_queue = pygame.Rect(25, 120, 340, 415)
        pygame.draw.rect(self.screen, self.PANEL_BG, p_queue, border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, p_queue, width=1, border_radius=8)

        self.screen.blit(self.font_bold.render("COLA DE ORDENES EN ESPERA", True, self.ACCENT_CYAN), (p_queue.x + 20, p_queue.y + 15))
        q_len = len(sim.order_queue)
        self.screen.blit(self.font_small.render(f"En cola: {q_len} laptops | Poisson(Lambda={sim.arrival_rate_h:.0f} ord/h)", True, self.TEXT_MUTED), (p_queue.x + 20, p_queue.y + 38))

        start_y = p_queue.y + 68
        for i, o in enumerate(sim.order_queue[:7]):
            box = pygame.Rect(p_queue.x + 15, start_y + i * 44, 310, 36)
            b_col = self.COLOR_RED if o.delayed_by_stockout else (20, 35, 55)
            pygame.draw.rect(self.screen, b_col, box, border_radius=6)
            pygame.draw.rect(self.screen, self.PANEL_BORDER, box, width=1, border_radius=6)

            tag = " [DEMORADA S/STOCK]" if o.delayed_by_stockout else ""
            txt = self.font_small.render(f"Orden #{o.order_id:03d} (Arribo: {o.arrival_time_min:.1f}m){tag}", True, self.TEXT_MAIN)
            self.screen.blit(txt, (box.x + 10, box.y + 10))

        if q_len > 7:
            self.screen.blit(self.font_small.render(f"... y {q_len - 7} ordenes mas en cola", True, self.TEXT_MUTED), (p_queue.x + 20, start_y + 7 * 44 + 5))
        elif q_len == 0:
            self.screen.blit(self.font_regular.render("Sin ordenes en cola (Al dia)", True, self.TEXT_MUTED), (p_queue.x + 30, start_y + 40))

        # =====================================================================
        # 2. Panel Central: Estacion de Ensamble con Iconos Vectoriales
        # =====================================================================
        p_station = pygame.Rect(380, 120, 420, 415)
        pygame.draw.rect(self.screen, self.PANEL_BG, p_station, border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, p_station, width=1, border_radius=8)

        self.screen.blit(self.font_bold.render("ESTACION PRINCIPAL DE ENSAMBLAJE", True, self.ACCENT_CYAN), (p_station.x + 20, p_station.y + 15))

        st = sim.station_status
        if st == StationStatus.IDLE:
            st_col = self.COLOR_GREEN
            st_title = "ESTACION DISPONIBLE (LIBRE)"
            st_desc = "Esperando que arribe una nueva orden"
        elif st == StationStatus.BUSY:
            st_col = self.COLOR_AMBER
            st_title = "ENSAMBLANDO LAPTOP"
            st_desc = f"Procesando Orden #{sim.current_order.order_id if sim.current_order else '?'}"
        else:
            st_col = self.COLOR_RED if (self.blink_counter // 15) % 2 == 0 else (120, 20, 20)
            st_title = "PARADA DE LINEA: SIN PROCESADORES"
            st_desc = "Linea detenida esperando reabastecimiento (Starvation)"

        cx = p_station.centerx
        cy = p_station.y + 160
        pygame.draw.circle(self.screen, st_col, (cx, cy), 72)
        pygame.draw.circle(self.screen, self.BG_DARK, (cx, cy), 58)

        # DIBUJO VECTORIAL SEGURO EN LINUX (Sin emojis rotos)
        if st == StationStatus.BUSY:
            draw_vector_bolt(self.screen, st_col, (cx, cy), scale=1.1)
        elif st == StationStatus.STARVED:
            draw_vector_stop(self.screen, st_col, (cx, cy), scale=1.0)
        else:
            draw_vector_check(self.screen, st_col, (cx, cy), scale=1.0)

        t_surf = self.font_bold.render(st_title, True, st_col)
        self.screen.blit(t_surf, (cx - t_surf.get_width() // 2, cy + 85))

        d_surf = self.font_small.render(st_desc, True, self.TEXT_MAIN)
        self.screen.blit(d_surf, (cx - d_surf.get_width() // 2, cy + 110))

        # BARRA DE PROGRESO DE LA ORDEN ACTUAL EN ENSAMBLE
        bar_ord = pygame.Rect(p_station.x + 35, cy + 140, 350, 18)
        pygame.draw.rect(self.screen, self.BG_DARK, bar_ord, border_radius=5)

        if st == StationStatus.BUSY and sim.current_order:
            srv_dur = max(0.1, sim.current_order.service_duration_min)
            srv_el = max(0.0, sim.current_time_min - (sim.current_order.service_start_time_min or sim.current_time_min))
            ord_ratio = np.clip(srv_el / srv_dur, 0.0, 1.0)
            pygame.draw.rect(self.screen, self.COLOR_AMBER, (bar_ord.x, bar_ord.y, int(bar_ord.width * ord_ratio), bar_ord.height), border_radius=5)
            lbl_o = self.font_small.render(f"Ensamble en progreso: {ord_ratio*100:.0f}% ({srv_el:.1f}m / {srv_dur:.1f}m)", True, (255, 255, 255))
            self.screen.blit(lbl_o, (bar_ord.centerx - lbl_o.get_width() // 2, bar_ord.y + 2))
        elif st == StationStatus.STARVED:
            pygame.draw.rect(self.screen, self.COLOR_RED, bar_ord, border_radius=5)
            lbl_o = self.font_small.render("Línea detenida: Stock = 0 unidades", True, (255, 255, 255))
            self.screen.blit(lbl_o, (bar_ord.centerx - lbl_o.get_width() // 2, bar_ord.y + 2))
        else:
            lbl_o = self.font_small.render("Estación libre - Sin trabajo activo", True, self.TEXT_MUTED)
            self.screen.blit(lbl_o, (bar_ord.centerx - lbl_o.get_width() // 2, bar_ord.y + 2))

        # =====================================================================
        # 3. Panel Derecho: Inventario de Procesadores
        # =====================================================================
        p_inv = pygame.Rect(815, 120, 340, 415)
        pygame.draw.rect(self.screen, self.PANEL_BG, p_inv, border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, p_inv, width=1, border_radius=8)

        self.screen.blit(self.font_bold.render("INVENTARIO DE PROCESADORES", True, self.ACCENT_CYAN), (p_inv.x + 20, p_inv.y + 15))

        stock = sim.stock_level
        stock_col = self.COLOR_GREEN if stock >= 15 else (self.COLOR_AMBER if stock >= 10 else self.COLOR_RED)
        s_num = self.font_big.render(f"{stock} unidades en stock", True, stock_col)
        self.screen.blit(s_num, (p_inv.x + 20, p_inv.y + 45))

        g_bg = pygame.Rect(p_inv.x + 20, p_inv.y + 85, 300, 24)
        pygame.draw.rect(self.screen, self.BG_DARK, g_bg, border_radius=6)
        fill_pct = min(1.0, max(0.0, stock / 50.0))
        g_fill = pygame.Rect(p_inv.x + 20, p_inv.y + 85, int(300 * fill_pct), 24)
        pygame.draw.rect(self.screen, stock_col, g_fill, border_radius=6)

        mark_x = p_inv.x + 20 + int(300 * (sim.reorder_threshold / 50.0))
        pygame.draw.line(self.screen, self.COLOR_RED, (mark_x, p_inv.y + 80), (mark_x, p_inv.y + 112), 3)
        self.screen.blit(self.font_small.render(f"Umbral critico: {sim.reorder_threshold}", True, self.COLOR_RED), (p_inv.x + 20, p_inv.y + 115))

        reord_box = pygame.Rect(p_inv.x + 20, p_inv.y + 150, 300, 105)
        pygame.draw.rect(self.screen, (20, 30, 45), reord_box, border_radius=8)

        if sim.is_reorder_in_progress:
            t_col = self.COLOR_AMBER
            msg_t = "[PROVEEDOR] PEDIDO EN TRANSITO"
            desc_t = f"Lote de {sim.batch_size} procesadores en camino.\nTiempo de entrega: {sim.reorder_lead_time_min:.0f} minutos."
        else:
            t_col = self.TEXT_MUTED
            msg_t = "REABASTECIMIENTO EN ESPERA"
            desc_t = "Stock por encima del umbral critico.\nNo hay pedidos activos al proveedor."

        self.screen.blit(self.font_bold.render(msg_t, True, t_col), (reord_box.x + 12, reord_box.y + 12))
        for line_i, line in enumerate(desc_t.split("\n")):
            self.screen.blit(self.font_small.render(line, True, self.TEXT_MAIN), (reord_box.x + 12, reord_box.y + 40 + line_i * 18))

        self.screen.blit(self.font_small.render(f"Lotes solicitados: {sim.batch_id_counter} | Despachados: {len(sim.completed_batches)}", True, self.TEXT_MUTED), (p_inv.x + 20, p_inv.y + 275))
        self.screen.blit(self.font_small.render(f"Paradas de linea: {sim.line_stops_count} veces", True, self.COLOR_RED if sim.line_stops_count > 0 else self.COLOR_GREEN), (p_inv.x + 20, p_inv.y + 300))

        # =====================================================================
        # 4. Panel Inferior: HUD Discreto
        # =====================================================================
        m = sim.get_metrics()
        hud = pygame.Rect(25, 545, 1130, 155)
        pygame.draw.rect(self.screen, self.PANEL_BG, hud, border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, hud, width=1, border_radius=8)

        self.screen.blit(self.font_bold.render("METRICAS DEL SISTEMA EN TIEMPO REAL (DES)", True, self.TEXT_MAIN), (hud.x + 20, hud.y + 12))

        hh = int(sim.current_time_min // 60)
        mm = int(sim.current_time_min % 60)

        col_w = 270
        self.screen.blit(self.font_small.render(f"Tiempo Simulado: {hh:02d}h {mm:02d}m ({sim.current_time_min:.1f} min)", True, self.ACCENT_CYAN), (hud.x + 20, hud.y + 42))
        self.screen.blit(self.font_small.render(f"Laptops Ensambladas: {m['total_ordenes_completadas']}", True, self.TEXT_MAIN), (hud.x + 20, hud.y + 68))
        self.screen.blit(self.font_small.render(f"Total Ordenes Arribadas: {m['total_ordenes_arribadas']}", True, self.TEXT_MAIN), (hud.x + 20, hud.y + 94))
        self.screen.blit(self.font_small.render(f"Utilizacion Estacion: {m['utilizacion_estacion_pct']}%", True, self.TEXT_MAIN), (hud.x + 20, hud.y + 120))

        self.screen.blit(self.font_small.render(f"Espera Media (Wq): {m['tiempo_espera_promedio_min']} min", True, self.ACCENT_CYAN), (hud.x + 20 + col_w, hud.y + 42))
        self.screen.blit(self.font_small.render(f"Tiempo Medio Sistema: {m['tiempo_sistema_promedio_min']} min", True, self.TEXT_MAIN), (hud.x + 20 + col_w, hud.y + 68))
        self.screen.blit(self.font_small.render(f"Espera Maxima: {m['tiempo_espera_maximo_min']} min", True, self.TEXT_MAIN), (hud.x + 20 + col_w, hud.y + 94))
        self.screen.blit(self.font_small.render(f"Ordenes en Cola Actual: {m['ordenes_en_cola_final']}", True, self.TEXT_MAIN), (hud.x + 20 + col_w, hud.y + 120))

        self.screen.blit(self.font_small.render(f"Despacho Lote: {m['tiempo_promedio_despacho_lote_horas']} h", True, self.ACCENT_CYAN), (hud.x + 20 + col_w * 2, hud.y + 42))
        self.screen.blit(self.font_small.render(f"Ciclo Medio Lote: {m['tiempo_promedio_ciclo_lote_min']} min", True, self.TEXT_MAIN), (hud.x + 20 + col_w * 2, hud.y + 68))
        self.screen.blit(self.font_small.render(f"Stock Procesadores: {m['stock_final_procesadores']} uds", True, self.TEXT_MAIN), (hud.x + 20 + col_w * 2, hud.y + 94))
        self.screen.blit(self.font_small.render(f"Lotes Despachados: {m['lotes_despachados_completos']}", True, self.TEXT_MAIN), (hud.x + 20 + col_w * 2, hud.y + 120))

        self.screen.blit(self.font_small.render(f"Paradas Linea: {m['numero_detenciones_linea']} veces", True, self.COLOR_RED if m['numero_detenciones_linea'] > 0 else self.COLOR_GREEN), (hud.x + 20 + col_w * 3, hud.y + 42))
        self.screen.blit(self.font_small.render(f"Ordenes Demoradas: {m['ordenes_retrasadas_por_stock']}", True, self.TEXT_MAIN), (hud.x + 20 + col_w * 3, hud.y + 68))
        self.screen.blit(self.font_small.render(f"Efic. Reabastecimiento: {m['eficiencia_reabastecimiento_pct']}%", True, self.COLOR_GREEN), (hud.x + 20 + col_w * 3, hud.y + 94))
        self.screen.blit(self.font_small.render(f"Disponibilidad Stock: {m['disponibilidad_stock_pct']}%", True, self.COLOR_GREEN), (hud.x + 20 + col_w * 3, hud.y + 120))

    def _draw_continuous_simulation_view(self):
        """Vista grafica del Problema 2: Cluster Termico de Servidores en Modo Infinito."""
        sim = self.continuous_sim

        # =====================================================================
        # PANEL DE ESTADO EN TIEMPO REAL (SIMULACION CONTINUA INFINITA - RK4)
        # =====================================================================
        prog_panel = pygame.Rect(25, 65, 1130, 45)
        pygame.draw.rect(self.screen, self.PANEL_BG, prog_panel, border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, prog_panel, width=1, border_radius=8)

        # Indicador de estado activo (pulsante)
        pulse = (self.blink_counter // 20) % 2 == 0
        dot_col = self.COLOR_GREEN if (not self.is_paused and pulse) else (30, 150, 80)
        if self.is_paused:
            dot_col = self.COLOR_AMBER
        pygame.draw.circle(self.screen, dot_col, (prog_panel.x + 22, prog_panel.centery), 6)

        mode_str = "MODO INFINITO EN VIVO" if not self.is_paused else "SIMULACION PAUSADA"
        mode_col = self.COLOR_GREEN if not self.is_paused else self.COLOR_AMBER
        self.screen.blit(self.font_bold.render(mode_str, True, mode_col), (prog_panel.x + 36, prog_panel.y + 13))

        # Tiempo transcurrido formateado en horas, minutos y segundos
        elapsed_s = sim.current_time_s
        hh = int(elapsed_s // 3600)
        mm = int((elapsed_s % 3600) // 60)
        ss = int(elapsed_s % 60)
        time_txt = f"Tiempo Transcurrido: {hh:02d}h {mm:02d}m {ss:02d}s ({elapsed_s/3600.0:.2f} h)"
        t_surf = self.font_bold.render(time_txt, True, self.ACCENT_CYAN)
        self.screen.blit(t_surf, (prog_panel.x + 270, prog_panel.y + 13))

        # Metricas clave en barra superior
        cum_tb = sim.total_processed_gigabits / 8000.0
        st_state = "THROTTLING" if sim.is_throttling_active else "NORMAL"
        stats_txt = f"Temp: {sim.current_temperature_c:.1f}°C [{st_state}] | Tráfico: {sim.current_traffic_gbps:.2f} Gbps | Datos: {cum_tb:.2f} TB"
        s_surf = self.font_small.render(stats_txt, True, self.TEXT_MAIN)
        self.screen.blit(s_surf, (prog_panel.right - s_surf.get_width() - 20, prog_panel.y + 14))

        # Barra sutil animada de actividad en el borde inferior
        if not self.is_paused:
            scan_pos = int((self.blink_counter * 6) % (prog_panel.width - 80))
            pygame.draw.line(self.screen, self.ACCENT_CYAN, (prog_panel.x + scan_pos, prog_panel.bottom - 2), (prog_panel.x + scan_pos + 80, prog_panel.bottom - 2), 2)

        # Panel Izquierdo: Servidores y Trafico
        p_srv = pygame.Rect(25, 120, 360, 415)
        pygame.draw.rect(self.screen, self.PANEL_BG, p_srv, border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, p_srv, width=1, border_radius=8)

        self.screen.blit(self.font_bold.render("NODO SERVIDOR DE ALTO RENDIMIENTO", True, self.ACCENT_CYAN), (p_srv.x + 20, p_srv.y + 15))

        rack = pygame.Rect(p_srv.x + 25, p_srv.y + 45, 310, 150)
        pygame.draw.rect(self.screen, self.BG_DARK, rack, border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, rack, width=2, border_radius=8)

        for u in range(4):
            uy = rack.y + 8 + u * 35
            ur = pygame.Rect(rack.x + 12, uy, 286, 26)
            pygame.draw.rect(self.screen, (20, 35, 50), ur, border_radius=4)

            led_rate = max(5, int(15 / max(1.0, sim.current_traffic_gbps)))
            led_on = (self.blink_counter // led_rate) % 2 == 0
            pygame.draw.circle(self.screen, self.ACCENT_CYAN if led_on else (10, 50, 70), (ur.x + 18, ur.centery), 5)
            pygame.draw.circle(self.screen, self.COLOR_GREEN, (ur.x + 36, ur.centery), 4)
            pygame.draw.line(self.screen, self.PANEL_BORDER, (ur.x + 55, ur.centery), (ur.right - 15, ur.centery), 2)

        self.screen.blit(self.font_bold.render("TRAFICO DE ENTRADA (NORMAL):", True, self.TEXT_MAIN), (p_srv.x + 25, p_srv.y + 210))
        self.screen.blit(self.font_big.render(f"{sim.current_traffic_gbps:.2f} Gbps", True, self.ACCENT_CYAN), (p_srv.x + 25, p_srv.y + 232))

        self.screen.blit(self.font_bold.render("THROUGHPUT EFECTIVO:", True, self.TEXT_MAIN), (p_srv.x + 25, p_srv.y + 280))
        th_c = self.COLOR_GREEN if not sim.is_throttling_active else self.COLOR_AMBER
        self.screen.blit(self.font_big.render(f"{sim.current_throughput_gbps:.2f} Gbps", True, th_c), (p_srv.x + 25, p_srv.y + 302))
        self.screen.blit(self.font_small.render(f"Eficiencia actual: {sim.current_efficiency * 100:.1f}%", True, self.TEXT_MAIN), (p_srv.x + 25, p_srv.y + 355))

        # Panel Central: Termometro y Throttling
        p_th = pygame.Rect(400, 120, 340, 415)
        pygame.draw.rect(self.screen, self.PANEL_BG, p_th, border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, p_th, width=1, border_radius=8)

        self.screen.blit(self.font_bold.render("BALANCE TERMICO Y CONTROL", True, self.ACCENT_CYAN), (p_th.x + 20, p_th.y + 15))

        temp = sim.current_temperature_c
        if temp <= 65.0:
            t_col = self.ACCENT_BLUE
        elif temp <= 70.0:
            t_col = self.COLOR_GREEN
        elif temp <= 75.0:
            t_col = self.COLOR_AMBER
        else:
            t_col = self.COLOR_RED

        th_bg = pygame.Rect(p_th.x + 35, p_th.y + 50, 38, 230)
        pygame.draw.rect(self.screen, self.BG_DARK, th_bg, border_radius=18)

        min_s = 40.0
        max_s = 90.0
        fill_r = np.clip((temp - min_s) / (max_s - min_s), 0.05, 1.0)
        fill_h = int(th_bg.height * fill_r)
        th_fill = pygame.Rect(th_bg.x, th_bg.bottom - fill_h, th_bg.width, fill_h)
        pygame.draw.rect(self.screen, t_col, th_fill, border_radius=18)
        pygame.draw.circle(self.screen, t_col, (th_bg.centerx, th_bg.bottom + 6), 26)

        sp_r = (70.0 - min_s) / (max_s - min_s)
        sp_y = th_bg.bottom - int(th_bg.height * sp_r)
        pygame.draw.line(self.screen, self.TEXT_MAIN, (th_bg.x - 5, sp_y), (th_bg.right + 20, sp_y), 3)
        self.screen.blit(self.font_small.render("Diseno: 70 C", True, self.TEXT_MAIN), (th_bg.right + 25, sp_y - 8))

        self.screen.blit(self.font_big.render(f"{temp:.2f} C", True, t_col), (p_th.x + 140, p_th.y + 90))

        st_card = pygame.Rect(p_th.x + 20, p_th.y + 325, 300, 72)
        if sim.is_throttling_active:
            c_bg = self.COLOR_RED if (self.blink_counter // 20) % 2 == 0 else (130, 20, 20)
            pygame.draw.rect(self.screen, c_bg, st_card, border_radius=8)
            self.screen.blit(self.font_bold.render("[ALERTA] THERMAL THROTTLING", True, (255, 255, 255)), (st_card.x + 12, st_card.y + 12))
            self.screen.blit(self.font_small.render(f"Temp > 70 C. Efic reducida al {sim.current_efficiency*100:.1f}%", True, (255, 255, 255)), (st_card.x + 12, st_card.y + 38))
        else:
            pygame.draw.rect(self.screen, (10, 40, 30), st_card, border_radius=8)
            pygame.draw.rect(self.screen, self.COLOR_GREEN, st_card, width=1, border_radius=8)
            self.screen.blit(self.font_bold.render("[OK] TEMPERATURA CONTROLADA", True, self.COLOR_GREEN), (st_card.x + 12, st_card.y + 12))
            self.screen.blit(self.font_small.render("T <= 70 C | Eficiencia nominal: 90.0%", True, self.TEXT_MAIN), (st_card.x + 12, st_card.y + 38))

        # Panel Derecho: Grafica en Tiempo Real
        p_chart = pygame.Rect(755, 120, 400, 415)
        pygame.draw.rect(self.screen, self.PANEL_BG, p_chart, border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, p_chart, width=1, border_radius=8)

        self.screen.blit(self.font_bold.render("DINAMICA CONTINUA: TEMP Y THROUGHPUT", True, self.ACCENT_CYAN), (p_chart.x + 20, p_chart.y + 15))

        c_box = pygame.Rect(p_chart.x + 20, p_chart.y + 45, 360, 240)
        pygame.draw.rect(self.screen, self.BG_DARK, c_box, border_radius=6)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, c_box, width=1, border_radius=6)

        r_y = c_box.bottom - int(c_box.height * ((70.0 - 55.0) / 30.0))
        pygame.draw.line(self.screen, (70, 70, 70), (c_box.x, r_y), (c_box.right, r_y), 1)
        self.screen.blit(self.font_small.render("70 C", True, self.TEXT_MUTED), (c_box.x + 5, r_y - 14))

        if len(self.realtime_temp_history) > 1:
            pts_t, pts_th = [], []
            n = len(self.realtime_temp_history)
            step_x = c_box.width / max(1, self.max_history_points - 1)
            off = self.max_history_points - n

            for idx in range(n):
                px = c_box.x + int((off + idx) * step_x)
                t_val = self.realtime_temp_history[idx]
                norm_t = np.clip((t_val - 55.0) / 30.0, 0.0, 1.0)
                pts_t.append((px, c_box.bottom - int(norm_t * c_box.height)))

                th_val = self.realtime_throughput_history[idx]
                norm_th = np.clip(th_val / 5.0, 0.0, 1.0)
                pts_th.append((px, c_box.bottom - int(norm_th * c_box.height)))

            if len(pts_th) >= 2:
                pygame.draw.lines(self.screen, self.ACCENT_CYAN, False, pts_th, 2)
            if len(pts_t) >= 2:
                pygame.draw.lines(self.screen, self.COLOR_AMBER, False, pts_t, 2)

        leg = pygame.Rect(p_chart.x + 20, p_chart.y + 300, 360, 95)
        pygame.draw.rect(self.screen, self.BG_DARK, leg, border_radius=6)
        pygame.draw.line(self.screen, self.COLOR_AMBER, (leg.x + 15, leg.y + 22), (leg.x + 45, leg.y + 22), 3)
        self.screen.blit(self.font_small.render("Temperatura Servidor (C)", True, self.TEXT_MAIN), (leg.x + 55, leg.y + 14))
        pygame.draw.line(self.screen, self.ACCENT_CYAN, (leg.x + 15, leg.y + 50), (leg.x + 45, leg.y + 50), 3)
        self.screen.blit(self.font_small.render("Throughput Efectivo (Gbps)", True, self.TEXT_MAIN), (leg.x + 55, leg.y + 42))
        pygame.draw.line(self.screen, (70, 70, 70), (leg.x + 15, leg.y + 76), (leg.x + 45, leg.y + 76), 1)
        self.screen.blit(self.font_small.render("Limite Thermal Throttling (70 C)", True, self.TEXT_MUTED), (leg.x + 55, leg.y + 68))

        # Panel Inferior: HUD Continuo
        m = sim.get_metrics()
        hud = pygame.Rect(25, 545, 1130, 150)
        pygame.draw.rect(self.screen, self.PANEL_BG, hud, border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, hud, width=1, border_radius=8)

        pygame.draw.circle(self.screen, self.COLOR_GREEN, (hud.x + 22, hud.y + 20), 5)
        self.screen.blit(self.font_bold.render("METRICAS DEL SISTEMA EN TIEMPO REAL (MODO CONTINUO INFINITO - RK4)", True, self.COLOR_GREEN), (hud.x + 35, hud.y + 12))

        col_w = 270
        self.screen.blit(self.font_small.render(f"Tiempo Simulado: {m['tiempo_simulado_horas']} h ({m['tiempo_simulado_segundos']:.0f} s) [Infinito]", True, self.ACCENT_CYAN), (hud.x + 20, hud.y + 42))
        self.screen.blit(self.font_small.render(f"Datos Procesados: {m['total_datos_procesados_tb']} TB", True, self.TEXT_MAIN), (hud.x + 20, hud.y + 68))
        self.screen.blit(self.font_small.render(f"Datos Recibidos: {m['total_datos_recibidos_tb']} TB", True, self.TEXT_MAIN), (hud.x + 20, hud.y + 94))
        self.screen.blit(self.font_small.render(f"Eficiencia Global: {m['eficiencia_global_pct']}%", True, self.COLOR_GREEN if m['eficiencia_global_pct'] > 85 else self.COLOR_AMBER), (hud.x + 20, hud.y + 120))

        self.screen.blit(self.font_small.render(f"Temp Media: {m['temperatura_promedio_c']} C", True, self.ACCENT_CYAN), (hud.x + 20 + col_w, hud.y + 42))
        self.screen.blit(self.font_small.render(f"Variabilidad (Std): +/-{m['variabilidad_temperatura_std_c']} C", True, self.TEXT_MAIN), (hud.x + 20 + col_w, hud.y + 68))
        self.screen.blit(self.font_small.render(f"Temp Minima: {m['temperatura_minima_c']} C", True, self.TEXT_MAIN), (hud.x + 20 + col_w, hud.y + 94))
        self.screen.blit(self.font_small.render(f"Temp Maxima: {m['temperatura_maxima_c']} C", True, self.TEXT_MAIN), (hud.x + 20 + col_w, hud.y + 120))

        self.screen.blit(self.font_small.render(f"Tiempo Throttling: {m['tiempo_en_throttling_horas']} h", True, self.ACCENT_CYAN), (hud.x + 20 + col_w * 2, hud.y + 42))
        self.screen.blit(self.font_small.render(f"% Tiempo Throttling: {m['porcentaje_tiempo_throttling']}%", True, self.COLOR_RED if m['porcentaje_tiempo_throttling'] > 30 else self.TEXT_MAIN), (hud.x + 20 + col_w * 2, hud.y + 68))
        self.screen.blit(self.font_small.render(f"Estabilidad: {m['estabilidad_termica']}", True, self.COLOR_GREEN), (hud.x + 20 + col_w * 2, hud.y + 94))
        self.screen.blit(self.font_small.render(f"Trazas Muestreadas: {m['total_trazas_registradas']}", True, self.TEXT_MAIN), (hud.x + 20 + col_w * 2, hud.y + 120))

        diag = m['diagnostico_viabilidad'][:45] + "..."
        self.screen.blit(self.font_small.render(f"Diagnostico Viabilidad: {diag}", True, self.TEXT_MUTED), (hud.x + 20 + col_w * 3, hud.y + 42))

    # =========================================================================
    # PANTALLA 3: LECTURA EN PANTALLA DEL REPORTE DE IA
    # =========================================================================
    # =========================================================================
    # PANTALLA 3: MENU DE RESULTADOS Y ANALISIS DE IA (GEMINI 2.5 FLASH)
    # =========================================================================
    def _draw_ai_report_screen(self):
        self.screen.fill(self.BG_DARK)

        # Barra Superior de Navegacion
        top_bar = pygame.Rect(0, 0, self.WIDTH, 62)
        pygame.draw.rect(self.screen, self.PANEL_BG, top_bar)
        pygame.draw.line(self.screen, self.PANEL_BORDER, (0, 62), (self.WIDTH, 62), 2)

        self.btn_results_back_sim.draw(self.screen, self.font_bold)
        self.btn_results_back_menu.draw(self.screen, self.font_bold)
        self.btn_results_tab_ex1.draw(self.screen, self.font_bold)
        self.btn_results_tab_ex2.draw(self.screen, self.font_bold)
        self.btn_results_export.draw(self.screen, self.font_bold)

        if self.ai_loading:
            self.btn_results_run_ai.text = "[...] Gemini 2.5 Flash"
            self.btn_results_run_ai.bg_color = self.COLOR_AMBER
        else:
            self.btn_results_run_ai.text = "[IA] Gemini 2.5 Flash"
            self.btn_results_run_ai.bg_color = self.COLOR_GREEN
        self.btn_results_run_ai.draw(self.screen, self.font_bold)

        # ---------------------------------------------------------------------
        # COLUMNA IZQUIERDA: METRICAS CUANTITATIVAS DEL SISTEMA
        # ---------------------------------------------------------------------
        p_res = pygame.Rect(20, 70, 545, 635)
        pygame.draw.rect(self.screen, self.PANEL_BG, p_res, border_radius=10)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, p_res, width=1, border_radius=10)

        # Titulo de Columna
        sub_title = "EJERCICIO 1: FABRICA DE LAPTOPS (DES)" if self.results_view_tab == 1 else "EJERCICIO 2: CLUSTER TERMICO (RK4)"
        self.screen.blit(self.font_title.render("RESULTADOS CUANTITATIVOS", True, self.ACCENT_CYAN), (p_res.x + 20, p_res.y + 12))
        self.screen.blit(self.font_small.render(sub_title, True, self.TEXT_MUTED), (p_res.x + 20, p_res.y + 36))

        if self.results_view_tab == 1:
            self._draw_results_metrics_exercise_1(p_res)
        else:
            self._draw_results_metrics_exercise_2(p_res)

        # ---------------------------------------------------------------------
        # COLUMNA DERECHA: DICTAMEN DE GOOGLE GEMINI 2.5 FLASH
        # ---------------------------------------------------------------------
        p_ai = pygame.Rect(575, 70, 585, 635)
        pygame.draw.rect(self.screen, self.PANEL_BG, p_ai, border_radius=10)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, p_ai, width=1, border_radius=10)

        self.screen.blit(self.font_title.render("DICTAMEN: GOOGLE GEMINI 2.5 FLASH", True, self.ACCENT_CYAN), (p_ai.x + 20, p_ai.y + 12))

        # Badge de conexion Gemini
        badge_rect = pygame.Rect(p_ai.right - 235, p_ai.y + 12, 215, 26)
        pygame.draw.rect(self.screen, (20, 35, 50), badge_rect, border_radius=6)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, badge_rect, width=1, border_radius=6)
        pygame.draw.circle(self.screen, self.COLOR_GREEN, (badge_rect.x + 12, badge_rect.centery), 4)
        self.screen.blit(self.font_small.render("Modelo: gemini-2.5-flash", True, self.COLOR_GREEN), (badge_rect.x + 22, badge_rect.y + 5))

        self.screen.blit(self.font_small.render("Diagnostico formal y 3 recomendaciones cuantitativas de optimizacion:", True, self.TEXT_MUTED), (p_ai.x + 20, p_ai.y + 36))

        # Cuadro de texto desplazable
        box = pygame.Rect(p_ai.x + 15, p_ai.y + 58, p_ai.width - 30, p_ai.height - 70)
        pygame.draw.rect(self.screen, self.BG_DARK, box, border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, box, width=1, border_radius=8)

        report_to_show = self.ai_report_ex1 if self.results_view_tab == 1 else self.ai_report_ex2
        if not report_to_show and self.ai_report_text:
            report_to_show = self.ai_report_text

        if self.ai_loading:
            # Estado cargando
            load_box = pygame.Rect(box.x + 30, box.y + 80, box.width - 60, 160)
            pygame.draw.rect(self.screen, (20, 35, 55), load_box, border_radius=8)
            pygame.draw.rect(self.screen, self.ACCENT_CYAN, load_box, width=1, border_radius=8)
            self.screen.blit(self.font_bold.render("CONSULTANDO GOOGLE GEMINI 2.5 FLASH...", True, self.ACCENT_CYAN), (load_box.x + 20, load_box.y + 25))
            self.screen.blit(self.font_regular.render("Enviando metricas formalmente estructuradas a la API remota.", True, self.TEXT_MAIN), (load_box.x + 20, load_box.y + 60))
            self.screen.blit(self.font_small.render("Por favor espere mientras el modelo genera el dictamen tecnico...", True, self.TEXT_MUTED), (load_box.x + 20, load_box.y + 90))
            return

        if not report_to_show:
            # Estado sin reporte aun
            no_rep_box = pygame.Rect(box.x + 20, box.y + 50, box.width - 40, 270)
            pygame.draw.rect(self.screen, (20, 30, 48), no_rep_box, border_radius=8)
            pygame.draw.rect(self.screen, self.PANEL_BORDER, no_rep_box, width=1, border_radius=8)

            t_nr = self.font_bold.render(f"Dictamen de Gemini 2.5 Flash Pendiente (Ejercicio {self.results_view_tab})", True, self.COLOR_AMBER)
            self.screen.blit(t_nr, (no_rep_box.x + 20, no_rep_box.y + 25))

            d1 = self.font_regular.render("Aun no se ha consultado a la IA para este ejercicio especifico.", True, self.TEXT_MAIN)
            self.screen.blit(d1, (no_rep_box.x + 20, no_rep_box.y + 60))

            d2 = self.font_small.render("Al pulsar el boton, Gemini 2.5 Flash analizara las metricas actuales,", True, self.TEXT_MUTED)
            d3 = self.font_small.render("evaluara la viabilidad/estabilidad y emitira 3 recomendaciones cuantificadas.", True, self.TEXT_MUTED)
            self.screen.blit(d2, (no_rep_box.x + 20, no_rep_box.y + 90))
            self.screen.blit(d3, (no_rep_box.x + 20, no_rep_box.y + 110))

            self.btn_results_inline_ai.draw(self.screen, self.font_bold)
            return

        # Renderizado de texto con scroll y ajuste de linea por palabras (Word Wrap)
        max_text_width = box.width - 45
        wrapped_items = self._format_and_wrap_report_lines(report_to_show, max_text_width)
        line_height = 20
        total_text_height = len(wrapped_items) * line_height
        self.max_report_scroll = max(0, total_text_height - (box.height - 35))

        clip_rect = pygame.Rect(box.x + 15, box.y + 10, box.width - 30, box.height - 25)
        self.screen.set_clip(clip_rect)

        curr_y = box.y + 15 - self.report_scroll_y
        for line_str, style in wrapped_items:
            if style == "empty":
                curr_y += line_height // 2
                continue

            if style == "header":
                surf = self.font_bold.render(line_str, True, self.ACCENT_CYAN)
            elif style == "title":
                surf = self.font_bold.render(line_str, True, self.COLOR_GREEN)
            elif style == "divider":
                surf = self.font_small.render(line_str, True, (80, 95, 115))
            elif style == "bullet":
                surf = self.font_regular.render(line_str, True, self.TEXT_MAIN)
            else:
                surf = self.font_regular.render(line_str, True, (203, 213, 225))

            self.screen.blit(surf, (box.x + 20, curr_y))
            curr_y += line_height

        self.screen.set_clip(None)

        # Scrollbar visual interactivo
        if self.max_report_scroll > 0:
            track_h = box.height - 30
            thumb_h = max(25, int(track_h * (box.height / max(1, total_text_height))))
            thumb_y = box.y + 15 + int((track_h - thumb_h) * (self.report_scroll_y / max(1, self.max_report_scroll)))
            pygame.draw.rect(self.screen, (40, 50, 65), (box.right - 10, box.y + 15, 6, track_h), border_radius=3)
            pygame.draw.rect(self.screen, self.ACCENT_CYAN, (box.right - 10, thumb_y, 6, thumb_h), border_radius=3)

        hint = self.font_small.render("Desplazar con Rueda del Raton (Scroll)", True, self.TEXT_MUTED)
        self.screen.blit(hint, (box.right - hint.get_width() - 25, box.bottom - 20))

    def _format_and_wrap_report_lines(self, text: str, max_width: int) -> List[tuple]:
        """
        Formatea y divide el texto en lineas ajustadas al ancho visual de la caja,
        retornando una lista de tuplas: (texto_linea, estilo).
        Estilos: 'header', 'title', 'bullet', 'divider', 'regular', 'empty'
        """
        result = []
        for raw_p in text.split("\n"):
            p = raw_p.strip()
            if not p:
                result.append(("", "empty"))
                continue

            if p.startswith("=") or p.startswith("---") or p.startswith("___"):
                result.append(("----------------------------------------------------------------", "divider"))
                continue

            style = "regular"
            indent_prefix = ""
            if p.startswith("###") or p.startswith("##") or p.startswith("#"):
                p = p.lstrip("#").strip()
                style = "title"
            elif "DICTAMEN" in p.upper() or "RECOMENDACIONES" in p.upper() or "CONCLUSION" in p.upper() or "ANALISIS" in p.upper():
                style = "header"
            elif p.startswith("*   ") or p.startswith("- ") or p.startswith("• "):
                p = p[2:].strip() if not p.startswith("*   ") else p[4:].strip()
                indent_prefix = "  • "
                style = "bullet"
            elif len(p) > 2 and p[0].isdigit() and p[1] in (".", ")"):
                style = "bullet"

            # Limpiar marcas de negrita markdown **texto** y comillas invertidas
            clean_text = p.replace("**", "").replace("`", "")
            font_to_use = self.font_bold if style in ("header", "title") else self.font_regular
            words = clean_text.split(" ")
            current_line = indent_prefix

            for word in words:
                if not word:
                    continue
                test_line = f"{current_line} {word}".strip() if current_line else word
                if font_to_use.size(test_line)[0] <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        result.append((current_line, style))
                    current_line = f"    {word}" if indent_prefix else word
            if current_line:
                result.append((current_line, style))
        return result

    def _draw_results_metrics_exercise_1(self, p_res: pygame.Rect):
        """Dibuja tarjetas de metricas cuantificadas para la Fabrica de Laptops."""
        m = self.discrete_sim.get_metrics()
        top_y = p_res.y + 60
        w = p_res.width - 30
        h_card = 132

        # 1. Tarjeta Produccion
        c1 = pygame.Rect(p_res.x + 15, top_y, w, h_card)
        pygame.draw.rect(self.screen, (20, 30, 45), c1, border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, c1, width=1, border_radius=8)
        self.screen.blit(self.font_bold.render("1. PRODUCCION Y ENSAMBLAJE", True, self.ACCENT_BLUE), (c1.x + 15, c1.y + 10))
        self.screen.blit(self.font_small.render(f"Laptops Ensambladas: {m['total_ordenes_completadas']} unidades", True, self.COLOR_GREEN), (c1.x + 15, c1.y + 35))
        self.screen.blit(self.font_small.render(f"Total Ordenes Arribadas: {m['total_ordenes_arribadas']} ordenes (Poisson)", True, self.TEXT_MAIN), (c1.x + 15, c1.y + 57))
        self.screen.blit(self.font_small.render(f"Utilizacion de la Estacion: {m['utilizacion_estacion_pct']}% (Rho teorico: 83.3%)", True, self.ACCENT_CYAN), (c1.x + 15, c1.y + 79))
        self.screen.blit(self.font_small.render(f"Tiempo Simulado Total: {m['tiempo_simulado_min']/60.0:.1f} h ({m['tiempo_simulado_min']:.0f} min)", True, self.TEXT_MUTED), (c1.x + 15, c1.y + 101))

        # 2. Tarjeta Tiempos de Espera
        c2 = pygame.Rect(p_res.x + 15, top_y + 142, w, h_card)
        pygame.draw.rect(self.screen, (20, 30, 45), c2, border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, c2, width=1, border_radius=8)
        self.screen.blit(self.font_bold.render("2. TIEMPOS DE ESPERA Y SISTEMA (M/M/1)", True, self.ACCENT_CYAN), (c2.x + 15, c2.y + 10))
        self.screen.blit(self.font_small.render(f"Tiempo Espera Medio en Cola (Wq): {m['tiempo_espera_promedio_min']} min", True, self.COLOR_AMBER), (c2.x + 15, c2.y + 35))
        self.screen.blit(self.font_small.render(f"Tiempo Total Medio en Sistema (W): {m['tiempo_sistema_promedio_min']} min", True, self.TEXT_MAIN), (c2.x + 15, c2.y + 57))
        self.screen.blit(self.font_small.render(f"Tiempo de Espera Maximo: {m['tiempo_espera_maximo_min']} min", True, self.TEXT_MAIN), (c2.x + 15, c2.y + 79))
        self.screen.blit(self.font_small.render(f"Ordenes en Cola Final: {m['ordenes_en_cola_final']} laptops en espera", True, self.TEXT_MUTED), (c2.x + 15, c2.y + 101))

        # 3. Tarjeta Inventario
        c3 = pygame.Rect(p_res.x + 15, top_y + 284, w, h_card)
        pygame.draw.rect(self.screen, (20, 30, 45), c3, border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, c3, width=1, border_radius=8)
        self.screen.blit(self.font_bold.render("3. GESTION DE INVENTARIO Y LOTES (s, Q)", True, self.ACCENT_BLUE), (c3.x + 15, c3.y + 10))
        self.screen.blit(self.font_small.render(f"Stock Actual: {m['stock_final_procesadores']} uds | Umbral critico (s): {m['umbral_inventario']} uds", True, self.TEXT_MAIN), (c3.x + 15, c3.y + 35))
        self.screen.blit(self.font_small.render(f"Tamano Lote Proveedor (Q): {m['tamano_lote']} unidades", True, self.TEXT_MAIN), (c3.x + 15, c3.y + 57))
        self.screen.blit(self.font_small.render(f"Despacho Medio por Lote: {m['tiempo_promedio_despacho_lote_horas']} h ({m['tiempo_promedio_ciclo_lote_min']} min)", True, self.ACCENT_CYAN), (c3.x + 15, c3.y + 79))
        self.screen.blit(self.font_small.render(f"Lotes Despachados: {m['lotes_despachados_completos']} pedidos completados", True, self.TEXT_MUTED), (c3.x + 15, c3.y + 101))

        # 4. Tarjeta Paradas de Linea
        c4 = pygame.Rect(p_res.x + 15, top_y + 426, w, h_card)
        pygame.draw.rect(self.screen, (20, 30, 45), c4, border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, c4, width=1, border_radius=8)
        st_col = self.COLOR_GREEN if m['numero_detenciones_linea'] == 0 else self.COLOR_RED
        self.screen.blit(self.font_bold.render("4. CONTINUIDAD OPERATIVA Y DESABASTECIMIENTO", True, st_col), (c4.x + 15, c4.y + 10))
        self.screen.blit(self.font_small.render(f"Paradas de Linea por Falta de Stock: {m['numero_detenciones_linea']} veces", True, st_col), (c4.x + 15, c4.y + 35))
        self.screen.blit(self.font_small.render(f"Ordenes Demoradas por Stock: {m['ordenes_retrasadas_por_stock']}", True, self.TEXT_MAIN), (c4.x + 15, c4.y + 57))
        self.screen.blit(self.font_small.render(f"Disponibilidad de Stock: {m['disponibilidad_stock_pct']}%", True, self.COLOR_GREEN), (c4.x + 15, c4.y + 79))
        self.screen.blit(self.font_small.render(f"Eficiencia Reabastecimiento: {m['eficiencia_reabastecimiento_pct']}%", True, self.COLOR_GREEN), (c4.x + 15, c4.y + 101))

    def _draw_results_metrics_exercise_2(self, p_res: pygame.Rect):
        """Dibuja tarjetas de metricas cuantificadas para el Cluster Termico."""
        m = self.continuous_sim.get_metrics()
        top_y = p_res.y + 60
        w = p_res.width - 30
        h_card = 132

        # Calculo de Throughput medio y deficit en GB
        t_sec = max(1.0, m['tiempo_simulado_segundos'])
        th_avg = (m['total_datos_procesados_tb'] * 8000.0) / t_sec
        lost_gb = max(0.0, (m['total_datos_recibidos_tb'] - m['total_datos_procesados_tb']) * 1000.0)

        # 1. Tarjeta Trafico
        c1 = pygame.Rect(p_res.x + 15, top_y, w, h_card)
        pygame.draw.rect(self.screen, (20, 30, 45), c1, border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, c1, width=1, border_radius=8)
        self.screen.blit(self.font_bold.render("1. TRAFICO Y RENDIMIENTO DE TRANSMISION", True, self.ACCENT_BLUE), (c1.x + 15, c1.y + 10))
        self.screen.blit(self.font_small.render(f"Tiempo Simulado Total: {m['tiempo_simulado_horas']:.2f} h ({m['tiempo_simulado_segundos']:.0f} s)", True, self.ACCENT_CYAN), (c1.x + 15, c1.y + 35))
        self.screen.blit(self.font_small.render(f"Trafico Entrada: {m['trafico_medio_nominal_gbps']:.2f} Gbps | Throughput Efectivo: {th_avg:.2f} Gbps", True, self.TEXT_MAIN), (c1.x + 15, c1.y + 57))
        self.screen.blit(self.font_small.render(f"Datos Procesados: {m['total_datos_procesados_tb']} TB de {m['total_datos_recibidos_tb']} TB recibidos", True, self.COLOR_GREEN), (c1.x + 15, c1.y + 79))
        self.screen.blit(self.font_small.render(f"Deficit por Throttling: {lost_gb:.2f} GB no procesados", True, self.COLOR_AMBER), (c1.x + 15, c1.y + 101))

        # 2. Tarjeta Termica
        c2 = pygame.Rect(p_res.x + 15, top_y + 142, w, h_card)
        pygame.draw.rect(self.screen, (20, 30, 45), c2, border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, c2, width=1, border_radius=8)
        self.screen.blit(self.font_bold.render("2. DINAMICA TERMODINAMICA (RK4)", True, self.ACCENT_CYAN), (c2.x + 15, c2.y + 10))
        self.screen.blit(self.font_small.render(f"Temperatura Promedio Servidor: {m['temperatura_promedio_c']} C", True, self.ACCENT_CYAN), (c2.x + 15, c2.y + 35))
        self.screen.blit(self.font_small.render(f"Variabilidad Termica: +/-{m['variabilidad_temperatura_std_c']} C", True, self.TEXT_MAIN), (c2.x + 15, c2.y + 57))
        self.screen.blit(self.font_small.render(f"Rango Observado: [{m['temperatura_minima_c']} C - {m['temperatura_maxima_c']} C]", True, self.TEXT_MAIN), (c2.x + 15, c2.y + 79))
        self.screen.blit(self.font_small.render(f"Punto de Diseno Nominal: {m['temperatura_diseno_c']} C", True, self.TEXT_MUTED), (c2.x + 15, c2.y + 101))

        # 3. Tarjeta Throttling
        c3 = pygame.Rect(p_res.x + 15, top_y + 284, w, h_card)
        pygame.draw.rect(self.screen, (20, 30, 45), c3, border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, c3, width=1, border_radius=8)
        th_pct = m['porcentaje_tiempo_throttling']
        th_col = self.COLOR_RED if th_pct > 30 else self.COLOR_AMBER
        self.screen.blit(self.font_bold.render("3. IMPACTO DE THERMAL THROTTLING", True, th_col), (c3.x + 15, c3.y + 10))
        self.screen.blit(self.font_small.render(f"Tiempo en Throttling: {m['tiempo_en_throttling_horas']} h ({m['tiempo_en_throttling_horas']*3600.0:.0f} s)", True, th_col), (c3.x + 15, c3.y + 35))
        self.screen.blit(self.font_small.render(f"Porcentaje del Tiempo en Throttling: {th_pct}%", True, th_col), (c3.x + 15, c3.y + 57))
        self.screen.blit(self.font_small.render("Eficiencia durante Throttling: 60.0% (Nominal: 90.0%)", True, self.TEXT_MAIN), (c3.x + 15, c3.y + 79))
        self.screen.blit(self.font_small.render(f"Umbral de Activacion: T > {m['temperatura_diseno_c']} C", True, self.TEXT_MUTED), (c3.x + 15, c3.y + 101))

        # 4. Tarjeta Viabilidad
        c4 = pygame.Rect(p_res.x + 15, top_y + 426, w, h_card)
        pygame.draw.rect(self.screen, (20, 30, 45), c4, border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, c4, width=1, border_radius=8)
        self.screen.blit(self.font_bold.render("4. EVALUACION DE VIABILIDAD OPERATIVA", True, self.COLOR_GREEN), (c4.x + 15, c4.y + 10))
        self.screen.blit(self.font_small.render(f"Estabilidad Termica (Runge-Kutta 4): {m['estabilidad_termica']}", True, self.COLOR_GREEN), (c4.x + 15, c4.y + 35))
        self.screen.blit(self.font_small.render(f"Eficiencia Global del Sistema: {m['eficiencia_global_pct']}%", True, self.COLOR_GREEN if m['eficiencia_global_pct'] > 85 else self.COLOR_AMBER), (c4.x + 15, c4.y + 57))
        diag_short = m['diagnostico_viabilidad'][:56]
        self.screen.blit(self.font_small.render(f"Diagnostico: {diag_short}", True, self.TEXT_MAIN), (c4.x + 15, c4.y + 79))
        self.screen.blit(self.font_small.render(f"Total de Puntos Integrados RK4: {m['total_trazas_registradas']}", True, self.TEXT_MUTED), (c4.x + 15, c4.y + 101))
