"""
Generador de Reportes y Trazas de Simulación.
Universidad José Antonio Páez - Parcial III Simulación.

Genera salidas formateadas por consola y exporta el archivo oficial de texto
'reporte_simulacion_parcial3.txt' con trazas, métricas cuantitativas y dictamen de IA.
"""

import os
import datetime
from typing import Dict, Any, List, Optional
from core.models import DiscreteTrace, ContinuousDataPoint


class SimulationReporter:
    """
    Genera y exporta reportes detallados de simulación en consola y en archivo .txt.
    """

    DEFAULT_REPORT_FILENAME = "reporte_simulacion_parcial3.txt"

    @classmethod
    def get_report_filepath(cls, custom_path: Optional[str] = None) -> str:
        """Obtiene la ruta absoluta para guardar el reporte."""
        if custom_path:
            return os.path.abspath(custom_path)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, cls.DEFAULT_REPORT_FILENAME)

    @classmethod
    def print_discrete_summary(cls, metrics: Dict[str, Any], ai_text: Optional[str] = None):
        """Imprime por consola el resumen estructurado del Problema 1."""
        print("\n" + "=" * 76)
        print("  UNIVERSIDAD JOSÉ ANTONIO PÁEZ - FACULTAD DE INGENIERÍA")
        print("  PARCIAL III: SIMULACIÓN DE EVENTOS DISCRETOS (FÁBRICA DE LAPTOPS)")
        print("=" * 76)
        print(f" Tiempo Simulado: {metrics.get('duracion_horas')} horas ({metrics.get('tiempo_simulado_min')} minutos)")
        print(f" Parámetros: lambda = {metrics.get('tasa_llegada_lambda_h')} ord/h | mu medio = {metrics.get('tiempo_servicio_medio_min')} min/laptop")
        print(f" Política Inventario: Umbral crítico s = {metrics.get('umbral_inventario')} uds | Lote Q = {metrics.get('tamano_lote')} uds (Lead: 15 min)")
        print("-" * 76)
        print(" 1. MÉTRICAS DE PRODUCCIÓN Y COLA:")
        print(f"    - Total Órdenes Recibidas:          {metrics.get('total_ordenes_arribadas')} laptops")
        print(f"    - Total Órdenes Completadas:         {metrics.get('total_ordenes_completadas')} laptops")
        print(f"    - Órdenes en Cola al Cierre:         {metrics.get('ordenes_en_cola_final')} laptops")
        print(f"    - Tiempo Promedio de Espera (Wq):    {metrics.get('tiempo_espera_promedio_min')} min ({metrics.get('tiempo_espera_promedio_horas')} h)")
        print(f"    - Tiempo Promedio en Sistema (W):    {metrics.get('tiempo_sistema_promedio_min')} min")
        print(f"    - Tiempo Máximo de Espera en Cola:   {metrics.get('tiempo_espera_maximo_min')} min")
        print(f"    - Utilización de la Estación (rho):  {metrics.get('utilizacion_estacion_pct')}%")
        print("-" * 76)
        print(" 2. MÉTRICAS DE INVENTARIO Y DESPACHO DE LOTES:")
        print(f"    - Lotes Reabastecidos por Proveedor: {metrics.get('lotes_solicitados')} pedidos")
        print(f"    - Lotes Completamente Despachados:   {metrics.get('lotes_despachados_completos')} lotes")
        print(f"    - Tiempo Promedio Despacho de Lote:  {metrics.get('tiempo_promedio_despacho_lote_horas')} horas ({metrics.get('tiempo_promedio_despacho_lote_min')} min)")
        print(f"    - Tiempo de Ciclo de Vida de Lote:   {metrics.get('tiempo_promedio_ciclo_lote_min')} min")
        print(f"    - Stock Final de Procesadores:       {metrics.get('stock_final_procesadores')} unidades")
        print("-" * 76)
        print(" 3. DETENCIONES DE LÍNEA Y EFICIENCIA EN REABASTECIMIENTO:")
        print(f"    - Número de Paradas de Línea:        {metrics.get('numero_detenciones_linea')} veces (Stockout)")
        print(f"    - Tiempo Total de Línea Detenida:    {metrics.get('tiempo_total_detencion_min')} min ({metrics.get('porcentaje_tiempo_detenido')}% del tiempo)")
        print(f"    - Órdenes Retrasadas por Stock:      {metrics.get('ordenes_retrasadas_por_stock')} ({metrics.get('porcentaje_ordenes_retrasadas')}%)")
        print(f"    - Eficiencia en Reabastecimiento:    {metrics.get('eficiencia_reabastecimiento_pct')}%")
        print(f"    - Disponibilidad de Stock:           {metrics.get('disponibilidad_stock_pct')}%")
        print("=" * 76)

        if ai_text:
            print("\n" + ai_text + "\n")

    @classmethod
    def print_continuous_summary(cls, metrics: Dict[str, Any], ai_text: Optional[str] = None):
        """Imprime por consola el resumen estructurado del Problema 2."""
        print("\n" + "=" * 76)
        print("  UNIVERSIDAD JOSÉ ANTONIO PÁEZ - FACULTAD DE INGENIERÍA")
        print("  PARCIAL III: SIMULACIÓN CONTINUA (CLÚSTER TÉRMICO DE SERVIDORES)")
        print("=" * 76)
        print(f" Tiempo Simulado: {metrics.get('duracion_horas')} horas ({metrics.get('tiempo_simulado_segundos')} segundos)")
        print(f" Perfil de Tráfico: Normal(mu={metrics.get('trafico_medio_nominal_gbps')} Gbps, sigma={metrics.get('trafico_desv_std_gbps')} Gbps) en rango {metrics.get('rango_trafico_gbps')}")
        print(f" Diseño Térmico: Equilibrio a {metrics.get('temperatura_diseno_c')}°C | Ambiente: {metrics.get('temperatura_ambiente_c')}°C | Eficiencia Base: 90%")
        print("-" * 76)
        print(" 1. MÉTRICAS DE RENDIMIENTO Y THROUGHPUT:")
        print(f"    - Total Tráfico Entrante Recibido:   {metrics.get('total_datos_recibidos_tb')} TB")
        print(f"    - Total Datos Procesados con Éxito:  {metrics.get('total_datos_procesados_tb')} TB")
        print(f"    - Eficiencia Global del Clúster:     {metrics.get('eficiencia_global_pct')}%")
        print("-" * 76)
        print(" 2. COMPORTAMIENTO TÉRMICO Y BALANCE DIFERENCIAL (dT/dt):")
        print(f"    - Temperatura Media del Servidor:    {metrics.get('temperatura_promedio_c')} °C")
        print(f"    - Variabilidad Térmica (Desv. Std):  ±{metrics.get('variabilidad_temperatura_std_c')} °C")
        print(f"    - Temperatura Mínima Registrada:     {metrics.get('temperatura_minima_c')} °C")
        print(f"    - Temperatura Máxima Alcanzada:      {metrics.get('temperatura_maxima_c')} °C")
        print(f"    - Estabilidad Térmica del Sistema:   {metrics.get('estabilidad_termica')}")
        print("-" * 76)
        print(" 3. ESTRANGULAMIENTO TÉRMICO (THERMAL THROTTLING):")
        print(f"    - Tiempo Acumulado en Throttling:    {metrics.get('tiempo_en_throttling_horas')} horas")
        print(f"    - Porcentaje de Tiempo en Throttling:{metrics.get('porcentaje_tiempo_throttling')} %")
        print(f"    - Diagnóstico de Viabilidad:         {metrics.get('diagnostico_viabilidad')}")
        print("=" * 76)

        if ai_text:
            print("\n" + ai_text + "\n")

    @classmethod
    def save_report_to_file(
        cls,
        problem_title: str,
        metrics: Dict[str, Any],
        ai_analysis: str,
        traces: Optional[List[Any]] = None,
        filepath: Optional[str] = None
    ) -> str:
        """
        Escribe un archivo de texto exhaustivo con el informe oficial de la simulación,
        trazas cronológicas de muestra, métricas y conclusión automatizada por IA.
        """
        target_path = cls.get_report_filepath(filepath)
        now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        lines = [
            "================================================================================",
            "  UNIVERSIDAD JOSÉ ANTONIO PÁEZ (UJAP)",
            "  FACULTAD DE INGENIERÍA - ESCUELA DE INGENIERÍA EN COMPUTACIÓN",
            "  PARCIAL III: SIMULACIÓN - TRABAJO PRÁCTICO (POO & INTELIGENCIA ARTIFICIAL)",
            "================================================================================",
            f" Fecha y Hora de Generación: {now_str}",
            f" Módulo Evaluado: {problem_title}",
            f" Archivo Destino: {os.path.basename(target_path)}",
            "================================================================================\n",
            "--------------------------------------------------------------------------------",
            "1. RESUMEN DE PARÁMETROS Y CONFIGURACIÓN INICIAL",
            "--------------------------------------------------------------------------------"
        ]

        for k, v in metrics.items():
            k_fmt = k.replace("_", " ").capitalize()
            lines.append(f"  * {k_fmt:<35}: {v}")

        lines.extend([
            "\n--------------------------------------------------------------------------------",
            "2. MUESTRA CRONOLÓGICA DE TRAZAS DEL SISTEMA (EVENTOS / MUESTREOS REGISTRADOS)",
            "--------------------------------------------------------------------------------"
        ])

        if traces:
            total_traces = len(traces)
            # Muestra representativa: primeras 25 trazas y últimas 25 trazas
            if total_traces <= 50:
                for t in traces:
                    lines.append("  " + t.formatted_line())
            else:
                lines.append(f"  [Mostrando primeras 25 trazas de un total de {total_traces} registradas]")
                for t in traces[:25]:
                    lines.append("  " + t.formatted_line())
                lines.append(f"\n  ... [{total_traces - 50} trazas intermedias omitidas en el reporte impreso] ...\n")
                lines.append(f"  [Mostrando últimas 25 trazas registradas]")
                for t in traces[-25:]:
                    lines.append("  " + t.formatted_line())
        else:
            lines.append("  (No se registraron trazas para este proceso)")

        lines.extend([
            "\n--------------------------------------------------------------------------------",
            "3. ANÁLISIS, CONCLUSIÓN Y RECOMENDACIONES DE INTELIGENCIA ARTIFICIAL",
            "--------------------------------------------------------------------------------",
            ai_analysis,
            "\n================================================================================",
            "  FIN DEL REPORTE OFICIAL DE SIMULACIÓN - UJAP PARCIAL III",
            "================================================================================\n"
        ])

        content = "\n".join(lines)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"[REPORTE] Archivo de texto guardado exitosamente en: {target_path}")
        return target_path
