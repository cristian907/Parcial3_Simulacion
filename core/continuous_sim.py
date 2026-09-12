"""
Simulación Continua: Clúster de Servidores - Proceso Térmico y Rendimiento.
Universidad José Antonio Páez - Parcial III Simulación.

Modela:
- Flujo continuo de tráfico: Normal(mu=3 Gbps, sigma=1 Gbps), acotado en [1, 5] Gbps.
- Ecuación diferencial de balance térmico de primer orden: dT/dt = Q_gen - Q_dis.
- Sistema de refrigeración líquida equilibrado a 70°C para tráfico nominal.
- Estrangulamiento térmico (Thermal Throttling) cuando T > 70°C.
- Throughput continuo y acumulación de datos en Terabytes procesados.
- Métodos duales: Solución continua completa y paso a paso (dt) para interfaz gráfica.
"""

import math
import numpy as np
from typing import List, Dict, Any, Optional
from .models import ContinuousDataPoint


class ThermalClusterSimulator:
    """
    Simulador POO de Balance Térmico y Rendimiento de Clúster de Servidores.
    Implementa el Problema 2 del Parcial III.
    """

    def __init__(
        self,
        simulation_hours: Optional[float] = None,
        mean_traffic_gbps: float = 3.0,
        std_traffic_gbps: float = 1.0,
        min_traffic_gbps: float = 1.0,
        max_traffic_gbps: float = 5.0,
        target_temp_c: float = 70.0,
        ambient_temp_c: float = 25.0,
        cooling_constant_k: float = 0.02,  # s^-1 (tiempo característico de disipación ~50s)
        base_efficiency: float = 0.90,      # 90% de eficiencia a T <= 70°C
        dt_seconds: float = 1.0,           # Paso de integración temporal
        sample_interval_s: float = 60.0,    # Intervalo de registro de trazas (cada 60s)
        seed: Optional[int] = None
    ):
        """
        Inicializa los parámetros del modelo diferencial térmico.

        :param simulation_hours: Tiempo total de corrida en horas (None o inf para simulación infinita continua).
        :param mean_traffic_gbps: Media de tráfico (3.0 Gbps).
        :param std_traffic_gbps: Desviación estándar (1.0 Gbps).
        :param min_traffic_gbps: Límite inferior de demanda (1.0 Gbps).
        :param max_traffic_gbps: Límite superior de demanda (5.0 Gbps).
        :param target_temp_c: Temperatura nominal de diseño de equilibrio (70.0 °C).
        :param ambient_temp_c: Temperatura ambiente / refrigerante (25.0 °C).
        :param cooling_constant_k: Coeficiente de transferencia térmica por enfriamiento líquido.
        :param base_efficiency: Eficiencia nominal cuando T <= 70°C (0.90 = 90%).
        :param dt_seconds: Paso temporal del integrador numérico.
        :param sample_interval_s: Intervalo entre puntos guardados en trazas.
        :param seed: Semilla aleatoria para reproducibilidad.
        """
        if simulation_hours is None or (isinstance(simulation_hours, (int, float)) and math.isinf(simulation_hours)):
            self.simulation_hours = float('inf')
            self.total_time_s = float('inf')
        else:
            self.simulation_hours = max(0.1, float(simulation_hours))
            self.total_time_s = self.simulation_hours * 3600.0
        self.mean_traffic_gbps = mean_traffic_gbps
        self.std_traffic_gbps = std_traffic_gbps
        self.min_traffic_gbps = min_traffic_gbps
        self.max_traffic_gbps = max_traffic_gbps
        self.target_temp_c = target_temp_c
        self.ambient_temp_c = ambient_temp_c
        self.cooling_k = cooling_constant_k
        self.base_efficiency = base_efficiency
        self.dt_seconds = dt_seconds
        self.sample_interval_s = sample_interval_s
        self.seed = seed

        self.rng = np.random.default_rng(seed)

        # Calibración del sistema térmico:
        # En equilibrio con tráfico nominal (3.0 Gbps), dT/dt = 0
        # Q_gen = alpha * Traffic_nominal = Q_dis = cooling_k * (70 - 25)
        # alpha * 3.0 = cooling_k * 45.0  =>  alpha = 15.0 * cooling_k
        self.heat_gen_alpha = (self.target_temp_c - self.ambient_temp_c) / self.mean_traffic_gbps * self.cooling_k

        # Estado instantáneo del sistema
        self.current_time_s: float = 0.0
        self.current_temperature_c: float = self.target_temp_c
        self.current_traffic_gbps: float = self.mean_traffic_gbps
        self.current_efficiency: float = self.base_efficiency
        self.current_throughput_gbps: float = self.current_traffic_gbps * self.current_efficiency
        self.is_throttling_active: bool = False

        # Acumuladores de métricas
        self.total_incoming_gigabits: float = 0.0
        self.total_processed_gigabits: float = 0.0
        self.total_throttling_time_s: float = 0.0

        # Para análisis estadístico de temperatura
        self.temp_history_sample: List[float] = [self.current_temperature_c]
        self.time_history_sample: List[float] = [0.0]
        self.traffic_history_sample: List[float] = [self.current_traffic_gbps]
        self.throughput_history_sample: List[float] = [self.current_throughput_gbps]
        self.traces: List[ContinuousDataPoint] = []

        self.last_sample_time_s: float = 0.0

        # Registrar traza inicial
        self._record_trace()

    def _generate_instant_traffic(self) -> float:
        """
        Genera la tasa de entrada de tráfico instantánea según distribución Normal(3, 1),
        acotada en el rango [1.0, 5.0] Gbps con cierta inercia temporal estocástica (Ornstein-Uhlenbeck / suavizado).
        """
        # Variación suave del tráfico para simular fluctuación continua realista
        noise = self.rng.normal(0.0, self.std_traffic_gbps)
        target = self.mean_traffic_gbps + noise
        target = np.clip(target, self.min_traffic_gbps, self.max_traffic_gbps)

        # Filtro de primer orden para evitar saltos irreales de nanosegundos (inercia de red de ~10s)
        smooth_factor = min(1.0, self.dt_seconds / 10.0)
        self.current_traffic_gbps = self.current_traffic_gbps + smooth_factor * (target - self.current_traffic_gbps)
        self.current_traffic_gbps = float(np.clip(self.current_traffic_gbps, self.min_traffic_gbps, self.max_traffic_gbps))
        return self.current_traffic_gbps

    def _compute_derivatives(self, temp: float, traffic: float) -> tuple[float, float, float]:
        """
        Calcula las derivadas térmicas: dT/dt = Q_gen - Q_dis.
        Retorna (dT_dt, q_gen, q_dis).
        """
        q_gen = self.heat_gen_alpha * traffic
        q_dis = self.cooling_k * (temp - self.ambient_temp_c)
        dT_dt = q_gen - q_dis
        return dT_dt, q_gen, q_dis

    def _update_efficiency_and_throughput(self):
        """
        Calcula la eficiencia del sistema y el throughput instantáneo.
        - Si T <= 70°C: Eficiencia = 90% (0.90)
        - Si T > 70°C: Thermal Throttling activado. La eficiencia cae fuertemente.
        """
        if self.current_temperature_c <= self.target_temp_c:
            self.is_throttling_active = False
            self.current_efficiency = self.base_efficiency
        else:
            self.is_throttling_active = True
            # Penalización por thermal throttling (estrangulamiento térmico progresivo)
            excess_temp = self.current_temperature_c - self.target_temp_c
            # Eficiencia cae de 0.90 a un mínimo de 0.20
            degraded_eff = self.base_efficiency - 0.035 * excess_temp
            self.current_efficiency = float(np.clip(degraded_eff, 0.20, self.base_efficiency))

        self.current_throughput_gbps = self.current_traffic_gbps * self.current_efficiency

    def _record_trace(self):
        """Registra una traza muestreada con el estado actual."""
        cum_tb = (self.total_processed_gigabits / 8000.0)  # 1 TB = 8000 Gigabits
        dT_dt, q_gen, q_dis = self._compute_derivatives(self.current_temperature_c, self.current_traffic_gbps)

        trace = ContinuousDataPoint(
            time_h=self.current_time_s / 3600.0,
            time_s=self.current_time_s,
            traffic_gbps=self.current_traffic_gbps,
            temperature_c=self.current_temperature_c,
            heat_gen=q_gen,
            heat_dis=q_dis,
            is_throttling=self.is_throttling_active,
            efficiency=self.current_efficiency,
            throughput_gbps=self.current_throughput_gbps,
            cumulative_terabytes=cum_tb
        )
        self.traces.append(trace)
        self.temp_history_sample.append(self.current_temperature_c)
        self.time_history_sample.append(self.current_time_s)
        self.traffic_history_sample.append(self.current_traffic_gbps)
        self.throughput_history_sample.append(self.current_throughput_gbps)

        if len(self.traces) > 10000:
            self.traces.pop(0)
            self.temp_history_sample.pop(0)
            self.time_history_sample.pop(0)
            self.traffic_history_sample.pop(0)
            self.throughput_history_sample.pop(0)

    def step(self, dt_s: float) -> bool:
        """
        Avanza la simulación continua un paso temporal dt_s utilizando integración Runge-Kutta 4 (RK4).
        Utiliza sub-stepping interno (sub_h <= 1.0s) para garantizar máxima estabilidad y precisión
        numérica sin importar la velocidad de aceleración seleccionada.
        Retorna True si continúa, False si se alcanzó el tiempo total.
        """
        if not math.isinf(self.total_time_s) and self.current_time_s >= self.total_time_s:
            return False

        sub_max_h = 1.0
        rem_dt = max(0.001, float(dt_s))
        while rem_dt > 0:
            h = min(sub_max_h, rem_dt)
            rem_dt -= h

            t_curr = self.current_time_s
            temp_curr = self.current_temperature_c
            traffic = self._generate_instant_traffic()

            # Integración RK4 para dT/dt = f(temp, traffic)
            # k1
            dT_dt1, _, _ = self._compute_derivatives(temp_curr, traffic)
            # k2
            dT_dt2, _, _ = self._compute_derivatives(temp_curr + 0.5 * h * dT_dt1, traffic)
            # k3
            dT_dt3, _, _ = self._compute_derivatives(temp_curr + 0.5 * h * dT_dt2, traffic)
            # k4
            dT_dt4, _, _ = self._compute_derivatives(temp_curr + h * dT_dt3, traffic)

            # Actualizar temperatura
            self.current_temperature_c += (h / 6.0) * (dT_dt1 + 2.0 * dT_dt2 + 2.0 * dT_dt3 + dT_dt4)

            # Actualizar throttling y throughput
            self._update_efficiency_and_throughput()

            # Acumular datos transferidos y tiempo en throttling
            incoming_gb = traffic * h
            processed_gb = self.current_throughput_gbps * h
            self.total_incoming_gigabits += incoming_gb
            self.total_processed_gigabits += processed_gb

            if self.is_throttling_active:
                self.total_throttling_time_s += h

            self.current_time_s += h

            # Registrar muestreo para trazas cada sample_interval_s (60s)
            if (self.current_time_s - self.last_sample_time_s) >= self.sample_interval_s:
                self._record_trace()
                self.last_sample_time_s = self.current_time_s

        return True if math.isinf(self.total_time_s) else (self.current_time_s < self.total_time_s)

    def run(self) -> Dict[str, Any]:
        """
        Ejecuta la simulación continua hasta completar el período total en horas indicado por el usuario.
        Retorna el diccionario de métricas calculadas.
        Si está configurada como infinita, simula un período analítico de referencia (4 horas).
        """
        limit_s = 4.0 * 3600.0 if math.isinf(self.total_time_s) else self.total_time_s
        while self.current_time_s < limit_s:
            # Para la simulación analítica rápida usamos un paso dt eficiente
            remaining = limit_s - self.current_time_s
            step_size = min(self.dt_seconds, remaining)
            self.step(step_size)

        # Asegurar traza final
        self._record_trace()
        return self.get_metrics()

    def get_metrics(self) -> Dict[str, Any]:
        """Calcula y consolida todas las métricas solicitadas del clúster de servidores."""
        total_time = max(1.0, self.current_time_s)
        total_incoming_tb = self.total_incoming_gigabits / 8000.0
        total_processed_tb = self.total_processed_gigabits / 8000.0

        # Eficiencia global del sistema (% de datos procesados respecto a los recibidos)
        global_efficiency_pct = (total_processed_tb / total_incoming_tb * 100.0) if total_incoming_tb > 0 else 0.0

        # Estadísticas térmicas
        temps = self.temp_history_sample
        avg_temp = float(np.mean(temps))
        std_temp = float(np.std(temps))
        min_temp = float(np.min(temps))
        max_temp = float(np.max(temps))

        # Tiempo en Throttling
        throttling_time_hours = self.total_throttling_time_s / 3600.0
        throttling_percentage = (self.total_throttling_time_s / total_time) * 100.0

        # Evaluación de viabilidad térmica
        # Se evalúa si el sistema se descontrola (Thermal Runaway) o si se mantiene acotado
        if max_temp > 95.0:
            viabilidad = "CRÍTICA: Peligro de daño por sobrecalentamiento. Requiere ampliar capacidad de disipación."
            estable = False
        elif throttling_percentage > 30.0:
            viabilidad = "PRECARIA: Frecuente degradación por estrangulamiento térmico. Rendimiento penalizado severamente."
            estable = True
        else:
            viabilidad = "VIABLE Y CONTROLADO: La refrigeración líquida absorbe las fluctuaciones de demanda adecuadamente."
            estable = True

        dur_h = "Infinito" if math.isinf(self.simulation_hours) else round(self.simulation_hours, 2)

        return {
            "problema": "Simulación Continua (Clúster de Servidores Térmico)",
            "duracion_horas": dur_h,
            "tiempo_simulado_horas": round(self.current_time_s / 3600.0, 2),
            "tiempo_simulado_segundos": round(self.current_time_s, 1),
            "trafico_medio_nominal_gbps": self.mean_traffic_gbps,
            "trafico_desv_std_gbps": self.std_traffic_gbps,
            "rango_trafico_gbps": f"[{self.min_traffic_gbps}, {self.max_traffic_gbps}]",
            "temperatura_diseno_c": self.target_temp_c,
            "temperatura_ambiente_c": self.ambient_temp_c,
            "total_datos_recibidos_tb": round(total_incoming_tb, 3),
            "total_datos_procesados_tb": round(total_processed_tb, 3),
            "eficiencia_global_pct": round(global_efficiency_pct, 2),
            "temperatura_promedio_c": round(avg_temp, 2),
            "variabilidad_temperatura_std_c": round(std_temp, 2),
            "temperatura_minima_c": round(min_temp, 2),
            "temperatura_maxima_c": round(max_temp, 2),
            "tiempo_en_throttling_horas": round(throttling_time_hours, 3),
            "porcentaje_tiempo_throttling": round(throttling_percentage, 2),
            "estabilidad_termica": "ESTABLE (Acotado)" if estable else "INESTABLE (Descontrol térmico)",
            "diagnostico_viabilidad": viabilidad,
            "total_trazas_registradas": len(self.traces)
        }
