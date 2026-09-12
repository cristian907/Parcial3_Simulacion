"""
Menú de Consola Interactivo con Validaciones Rigurosas y Valores por Defecto.
Universidad José Antonio Páez - Parcial III Simulación.
"""

import sys
import os
from typing import Optional, Dict, Any

from core.discrete_sim import LaptopFactorySimulator
from core.continuous_sim import ThermalClusterSimulator
from services.ai_service import AISimulationService
from services.reporter import SimulationReporter


class ConsoleMenu:
    """
    Gestor del menú principal por consola.
    Implementa validaciones completas de datos de entrada y valores por defecto para pruebas inmediatas.
    """

    def __init__(self):
        self.ai_service = AISimulationService()
        self.default_discrete_hours = 8.0
        self.default_continuous_hours = 4.0
        self.active_seed: Optional[int] = 42  # Semilla por defecto para pruebas reproducibles

    @staticmethod
    def prompt_float(prompt_text: str, default_val: float, min_val: float = 0.01, max_val: float = 10000.0) -> float:
        """
        Solicita un número decimal validado.
        Si el usuario presiona Enter sin escribir, retorna el valor por defecto.
        """
        while True:
            try:
                raw = input(f"{prompt_text} [Defecto: {default_val}]: ").strip()
                if not raw:
                    return default_val
                val = float(raw)
                if val < min_val:
                    print(f"  [Error] El valor debe ser mayor o igual a {min_val}.")
                    continue
                if val > max_val:
                    print(f"  [Error] El valor no debe superar {max_val}.")
                    continue
                return val
            except ValueError:
                print("  [Error] Debe ingresar un número válido (ej. 8, 4.5, 12).")

    @staticmethod
    def prompt_int(prompt_text: str, default_val: int, min_val: int = 1, max_val: int = 100000) -> int:
        """Solicita un número entero validado con valor por defecto."""
        while True:
            try:
                raw = input(f"{prompt_text} [Defecto: {default_val}]: ").strip()
                if not raw:
                    return default_val
                val = int(raw)
                if val < min_val or val > max_val:
                    print(f"  [Error] El número debe estar en el rango [{min_val}, {max_val}].")
                    continue
                return val
            except ValueError:
                print("  [Error] Debe ingresar un número entero válido (ej. 10, 50).")

    def run_problem_1(self):
        """Ejecuta el Problema 1: Simulación de Eventos Discretos (Fábrica de Laptops)."""
        print("\n" + "=" * 70)
        print("  PROBLEMA 1: SIMULACIÓN DE EVENTOS DISCRETOS - FÁBRICA DE LAPTOPS")
        print("=" * 70)
        print("  Parámetros del problema:")
        print("  - Llegada de órdenes: Poisson (promedio 10 órdenes/hora)")
        print("  - Ensamble: Exponencial (media 5 min/laptop)")
        print("  - Inventario: Umbral < 10 procesadores -> Pedido lote 50 (Lead: 15 min)\n")

        hours = self.prompt_float("Ingrese las horas de simulación", self.default_discrete_hours, min_val=0.1, max_val=720.0)

        use_custom = input("¿Desea modificar parámetros avanzados (lambda, mu, umbral)? (s/N): ").strip().lower() == 's'
        if use_custom:
            lambd = self.prompt_float("Tasa de llegada lambda (órdenes/hora)", 10.0)
            mu_srv = self.prompt_float("Tiempo medio de ensamble (minutos)", 5.0)
            threshold = self.prompt_int("Umbral crítico de stock para reorden", 10)
            batch = self.prompt_int("Tamaño de lote entregado", 50)
            lead_time = self.prompt_float("Tiempo de entrega del proveedor (minutos)", 15.0)
        else:
            lambd = 10.0
            mu_srv = 5.0
            threshold = 10
            batch = 50
            lead_time = 15.0

        print(f"\n[SIMULADOR] Ejecutando simulación de eventos discretos por {hours} horas...")
        sim = LaptopFactorySimulator(
            simulation_hours=hours,
            arrival_rate_h=lambd,
            service_mean_min=mu_srv,
            reorder_threshold=threshold,
            reorder_lead_time_min=lead_time,
            batch_size=batch,
            seed=self.active_seed
        )

        metrics = sim.run()

        # Obtener muestra de trazas formateadas
        sample_traces = [t.formatted_line() for t in sim.traces[:20]]

        # Consultar API de IA
        print("\n[IA] Solicitando análisis y dictamen automatizado a la API de Inteligencia Artificial...")
        ai_analysis = self.ai_service.analyze_metrics(
            problem_type="Simulación de Eventos Discretos (Fábrica de Laptops)",
            metrics=metrics,
            sample_traces=sample_traces
        )

        # Imprimir resumen
        SimulationReporter.print_discrete_summary(metrics, ai_analysis)

        # Guardar en archivo
        SimulationReporter.save_report_to_file(
            problem_title="Problema 1: Simulación de Eventos Discretos (Fábrica de Laptops)",
            metrics=metrics,
            ai_analysis=ai_analysis,
            traces=sim.traces
        )

        input("\nPresione Enter para regresar al menú principal...")

    def run_problem_2(self):
        """Ejecuta el Problema 2: Simulación Continua (Clúster Térmico de Servidores)."""
        print("\n" + "=" * 70)
        print("  PROBLEMA 2: SIMULACIÓN CONTINUA - CLÚSTER TÉRMICO DE SERVIDORES")
        print("=" * 70)
        print("  Parámetros del problema:")
        print("  - Tráfico de entrada: Normal(mu=3 Gbps, sigma=1 Gbps) en rango [1, 5] Gbps")
        print("  - Ecuación diferencial térmica: dT/dt = Q_gen - Q_dis")
        print("  - Equilibrio térmico diseñado a 70°C con eficiencia nominal del 90%")
        print("  - Thermal Throttling: Se activa cuando T > 70°C degradando el rendimiento\n")

        hours = self.prompt_float("Ingrese las horas de simulación continua", self.default_continuous_hours, min_val=0.1, max_val=168.0)

        use_custom = input("¿Desea modificar parámetros avanzados (tráfico medio, desv, temp diseño)? (s/N): ").strip().lower() == 's'
        if use_custom:
            mean_tr = self.prompt_float("Tráfico medio (Gbps)", 3.0)
            std_tr = self.prompt_float("Desviación estándar de tráfico (Gbps)", 1.0)
            target_t = self.prompt_float("Temperatura de diseño (°C)", 70.0)
            amb_t = self.prompt_float("Temperatura ambiente (°C)", 25.0)
        else:
            mean_tr = 3.0
            std_tr = 1.0
            target_t = 70.0
            amb_t = 25.0

        print(f"\n[SIMULADOR] Ejecutando simulación continua por {hours} horas mediante Runge-Kutta 4...")
        sim = ThermalClusterSimulator(
            simulation_hours=hours,
            mean_traffic_gbps=mean_tr,
            std_traffic_gbps=std_tr,
            target_temp_c=target_t,
            ambient_temp_c=amb_t,
            seed=self.active_seed
        )

        metrics = sim.run()

        # Muestra de trazas continuas
        sample_traces = [t.formatted_line() for t in sim.traces[:20]]

        # Consultar API de IA
        print("\n[IA] Solicitando análisis y dictamen automatizado a la API de Inteligencia Artificial...")
        ai_analysis = self.ai_service.analyze_metrics(
            problem_type="Simulación Continua (Clúster Térmico de Servidores)",
            metrics=metrics,
            sample_traces=sample_traces
        )

        # Imprimir resumen
        SimulationReporter.print_continuous_summary(metrics, ai_analysis)

        # Guardar en archivo
        SimulationReporter.save_report_to_file(
            problem_title="Problema 2: Simulación Continua (Clúster Térmico de Servidores)",
            metrics=metrics,
            ai_analysis=ai_analysis,
            traces=sim.traces
        )

        input("\nPresione Enter para regresar al menú principal...")

    def run_both_problems(self):
        """Ejecuta ambos problemas de forma secuencial y genera un informe unificado."""
        print("\n" + "=" * 70)
        print("  EJECUCIÓN INTEGRADA: PROBLEMA 1 (DISCRETO) + PROBLEMA 2 (CONTINUO)")
        print("=" * 70)

        # 1. Problema 1
        hours_1 = self.prompt_float("Horas de simulación para Fábrica de Laptops", 8.0)
        sim1 = LaptopFactorySimulator(simulation_hours=hours_1, seed=self.active_seed)
        m1 = sim1.run()
        ai1 = self.ai_service.analyze_metrics("Fábrica de Laptops", m1, [t.formatted_line() for t in sim1.traces[:15]])
        SimulationReporter.print_discrete_summary(m1, ai1)

        # 2. Problema 2
        hours_2 = self.prompt_float("Horas de simulación para Clúster Térmico", 4.0)
        sim2 = ThermalClusterSimulator(simulation_hours=hours_2, seed=self.active_seed)
        m2 = sim2.run()
        ai2 = self.ai_service.analyze_metrics("Clúster Térmico", m2, [t.formatted_line() for t in sim2.traces[:15]])
        SimulationReporter.print_continuous_summary(m2, ai2)

        # Guardar ambos reportes
        combined_metrics = {"PROBLEMA_1_DISCRETO": m1, "PROBLEMA_2_CONTINUO": m2}
        combined_ai = f"{ai1}\n\n{'='*70}\n\n{ai2}"
        SimulationReporter.save_report_to_file(
            problem_title="Parcial III Completo: Simulación Discreta y Continua",
            metrics=combined_metrics,
            ai_analysis=combined_ai,
            traces=sim1.traces[:20] + sim2.traces[:20]
        )

        input("\nPresione Enter para regresar al menú principal...")

    def launch_pygame_bonus(self):
        """Inicia la interfaz gráfica interactiva en Pygame."""
        try:
            from ui.pygame_app import PygameBonusVisualizer
            print("\n[PYGAME] Iniciando ventana gráfica interactiva...")
            app = PygameBonusVisualizer()
            app.run()
        except Exception as e:
            print(f"\n[ERROR PYGAME] No se pudo abrir la interfaz gráfica: {e}")
            print("Verifique que tenga un entorno gráfico (X11/Wayland) activo.")
            input("Presione Enter para continuar...")

    def configure_settings(self):
        """Permite configurar la semilla estocástica del sistema."""
        print("\n" + "=" * 60)
        print("  CONFIGURACIÓN DEL SISTEMA")
        print("=" * 60)
        print(f" Proveedor de IA: Google Gemini API (clave de .env: {self.ai_service.gemini_model})")
        print(f" Semilla aleatoria actual: {self.active_seed if self.active_seed is not None else 'Aleatoria pura'}")
        print("-" * 60)
        raw = input(" Ingrese nueva semilla entera (o deje vacío para aleatorio puro): ").strip()
        if raw:
            try:
                self.active_seed = int(raw)
                print(f" [OK] Semilla fijada en: {self.active_seed}")
            except ValueError:
                print(" [Error] Semilla inválida.")
        else:
            self.active_seed = None
            print(" [OK] Semilla fijada en modo totalmente aleatorio.")

    def start(self):
        """Bucle principal de ejecución del menú interactivo."""
        while True:
            print("\n" + "=" * 76)
            print("  UNIVERSIDAD JOSÉ ANTONIO PÁEZ - FACULTAD DE INGENIERÍA")
            print("  ESCUELA DE INGENIERÍA EN COMPUTACIÓN | CÁTEDRA DE SIMULACIÓN")
            print("  PARCIAL III: TRABAJO PRÁCTICO (SIMULACIÓN DISCRETA, CONTINUA & IA)")
            print("=" * 76)
            print("  1. Simulación de Eventos Discretos: Fábrica de Laptops")
            print("  2. Simulación Continua: Clúster Térmico de Servidores")
            print("  3. Ejecutar Ambos Problemas y Generar Reporte Consolidado")
            print("  4. Interfaz Gráfica Interactiva en Pygame")
            print("  5. Configuración de Semilla Aleatoria")
            print("  6. Salir")
            print("=" * 76)

            choice = input("  Seleccione una opción [1-6] (Defecto: 1): ").strip()
            if not choice:
                choice = "1"

            if choice == "1":
                self.run_problem_1()
            elif choice == "2":
                self.run_problem_2()
            elif choice == "3":
                self.run_both_problems()
            elif choice == "4":
                self.launch_pygame_bonus()
            elif choice == "5":
                self.configure_settings()
            elif choice == "6":
                print("\n¡Gracias por utilizar el Simulador UJAP! Saliendo...")
                break
            else:
                print("\n  [Opción Inválida] Por favor ingrese un número del 1 al 6.")
