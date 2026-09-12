"""
Launcher Principal y Punto de Entrada - Parcial III: Simulación.
Universidad José Antonio Páez - Facultad de Ingeniería - Escuela de Ingeniería en Computación.

Autor: Estudiante UJAP
Asignatura: Simulación de Sistemas
"""

import sys
import os
import argparse

# Asegurar que la carpeta raíz del parcial esté en PYTHONPATH
PARCIAL_DIR = os.path.dirname(os.path.abspath(__file__))
if PARCIAL_DIR not in sys.path:
    sys.path.insert(0, PARCIAL_DIR)

from core.discrete_sim import LaptopFactorySimulator
from core.continuous_sim import ThermalClusterSimulator
from services.ai_service import AISimulationService
from services.reporter import SimulationReporter
from ui.console_menu import ConsoleMenu


def run_cli_headless(args):
    """Ejecución no interactiva por línea de comandos (ideal para scripts y pruebas automatizadas)."""
    ai_service = AISimulationService(provider=args.ai)
    hours = args.hours if args.hours is not None else (8.0 if args.problem == 1 else 4.0)

    if args.problem == 1:
        print(f"\n[CLI] Ejecutando Problema 1: Simulación de Eventos Discretos ({hours} horas)...")
        sim = LaptopFactorySimulator(simulation_hours=hours, seed=args.seed)
        metrics = sim.run()
        sample_traces = [t.formatted_line() for t in sim.traces[:20]]
        ai_res = ai_service.analyze_metrics("Fábrica de Laptops", metrics, sample_traces)
        SimulationReporter.print_discrete_summary(metrics, ai_res)
        if args.export:
            SimulationReporter.save_report_to_file(
                "Problema 1: Fábrica de Laptops", metrics, ai_res, sim.traces
            )

    elif args.problem == 2:
        print(f"\n[CLI] Ejecutando Problema 2: Simulación Continua ({hours} horas)...")
        sim = ThermalClusterSimulator(simulation_hours=hours, seed=args.seed)
        metrics = sim.run()
        sample_traces = [t.formatted_line() for t in sim.traces[:20]]
        ai_res = ai_service.analyze_metrics("Clúster Térmico", metrics, sample_traces)
        SimulationReporter.print_continuous_summary(metrics, ai_res)
        if args.export:
            SimulationReporter.save_report_to_file(
                "Problema 2: Clúster Térmico de Servidores", metrics, ai_res, sim.traces
            )
    else:
        print("\n[CLI] Ejecutando ambos problemas secuencialmente...")
        sim1 = LaptopFactorySimulator(simulation_hours=hours, seed=args.seed)
        m1 = sim1.run()
        ai1 = ai_service.analyze_metrics("Fábrica de Laptops", m1, [t.formatted_line() for t in sim1.traces[:15]])
        SimulationReporter.print_discrete_summary(m1, ai1)

        sim2 = ThermalClusterSimulator(simulation_hours=hours, seed=args.seed)
        m2 = sim2.run()
        ai2 = ai_service.analyze_metrics("Clúster Térmico", m2, [t.formatted_line() for t in sim2.traces[:15]])
        SimulationReporter.print_continuous_summary(m2, ai2)

        if args.export:
            combined_m = {"PROBLEMA_1_DISCRETO": m1, "PROBLEMA_2_CONTINUO": m2}
            combined_ai = f"{ai1}\n\n{'='*70}\n\n{ai2}"
            SimulationReporter.save_report_to_file(
                "Parcial III Completo: Simulación Discreta y Continua",
                combined_m,
                combined_ai,
                sim1.traces[:20] + sim2.traces[:20]
            )


def main():
    parser = argparse.ArgumentParser(
        description="UJAP - Parcial III: Simulación de Eventos Discretos, Simulación Continua, IA y Pygame"
    )
    parser.add_argument("--cli", action="store_true", help="Ejecutar en modo consola directa")
    parser.add_argument("--pygame", action="store_true", help="Iniciar directamente la animación interactiva en Pygame")
    parser.add_argument("--problem", type=int, choices=[1, 2], help="Seleccionar problema específico (1: Discreto, 2: Continuo)")
    parser.add_argument("--hours", type=float, help="Duración de la simulación en horas")
    parser.add_argument("--seed", type=int, default=42, help="Semilla aleatoria para reproducibilidad (defecto: 42)")
    parser.add_argument("--ai", type=str, choices=["GEMINI", "OPENAI", "OLLAMA", "LOCAL"], default="GEMINI", help="Proveedor de IA")
    parser.add_argument("--export", action="store_true", default=True, help="Exportar automáticamente reporte_simulacion_parcial3.txt")

    args = parser.parse_args()

    # Si se especificó explícitamente modo CLI o un problema numérico por flags
    if args.cli or args.problem is not None:
        run_cli_headless(args)
        return

    # Modo por defecto: Interfaz Gráfica Completa (Pygame)
    if "DISPLAY" in os.environ or sys.platform.startswith("win") or sys.platform == "darwin":
        try:
            print("[INFO] Iniciando la Interfaz Gráfica Completa (Pygame)...")
            from ui.pygame_app import PygameBonusVisualizer
            app = PygameBonusVisualizer()
            app.run()
            return
        except Exception as e:
            print(f"[Aviso] No se pudo iniciar el modo gráfico ({e}). Pasando al menú de consola interactivo.")

    # Fallback si no hay display o ocurrió un error al inicializar la ventana
    menu = ConsoleMenu()
    menu.start()


if __name__ == "__main__":
    main()
