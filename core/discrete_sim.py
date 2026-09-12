"""
Simulación de Eventos Discretos: Fábrica de Ensamblaje de Laptops.
Universidad José Antonio Páez - Parcial III Simulación.

Modela:
- Llegadas de órdenes: Proceso de Poisson (tasa promedio 10 órdenes/hora).
- Servicio de ensamblaje: Distribución exponencial (media de 5 minutos/laptop).
- Gestión de inventario: Reabastecimiento de lotes de 50 procesadores cuando stock < 10.
- Tiempo de entrega de proveedor: 15 minutos determinista.
- Detención de línea (Starvation) y demoras por falta de componentes.
- Soporte dual: Ejecución analítica instantánea y ejecución paso a paso (dt) para Pygame.
"""

import heapq
import math
import numpy as np
from typing import List, Dict, Any, Optional
from .models import LaptopOrder, ReplenishmentBatch, DiscreteTrace, StationStatus


class FactoryEvent:
    """Evento del calendario de simulación discreta."""
    TYPE_ARRIVAL = 1
    TYPE_SERVICE_END = 2
    TYPE_REPLENISHMENT = 3

    def __init__(self, time_min: float, event_type: int, payload: Any = None):
        self.time_min = time_min
        self.event_type = event_type
        self.payload = payload

    def __lt__(self, other: 'FactoryEvent') -> bool:
        return self.time_min < other.time_min


class LaptopFactorySimulator:
    """
    Simulador de Eventos Discretos (DES) para la Fábrica de Laptops.
    """

    def __init__(
        self,
        simulation_hours: Optional[float] = None,
        arrival_rate_h: float = 10.0,
        service_mean_min: float = 5.0,
        reorder_threshold: int = 10,
        reorder_lead_time_min: float = 15.0,
        batch_size: int = 50,
        initial_stock: int = 50,
        seed: Optional[int] = None
    ):
        """
        Inicializa los parámetros del sistema de eventos discretos.

        :param simulation_hours: Duración en horas (None o inf para simulación infinita continua).
        :param arrival_rate_h: Tasa media de llegada lambda (10 órdenes/hora).
        :param service_mean_min: Tiempo medio de ensamble (5 min).
        :param reorder_threshold: Umbral crítico de stock para pedir lote (< 10).
        :param reorder_lead_time_min: Tiempo de entrega del proveedor (15 min).
        :param batch_size: Tamaño de lote entregado (50 unidades).
        :param initial_stock: Nivel de stock de procesadores inicial (50 unidades).
        :param seed: Semilla para reproducibilidad estocástica.
        """
        if simulation_hours is None or (isinstance(simulation_hours, (int, float)) and math.isinf(simulation_hours)):
            self.simulation_hours = float('inf')
            self.total_time_min = float('inf')
        else:
            self.simulation_hours = max(0.1, float(simulation_hours))
            self.total_time_min = self.simulation_hours * 60.0

        self.arrival_rate_h = arrival_rate_h
        self.arrival_rate_min = arrival_rate_h / 60.0  # 10 / 60 = 0.1667 orden/min
        self.service_mean_min = service_mean_min        # 5.0 min
        self.reorder_threshold = reorder_threshold      # 10 unidades
        self.reorder_lead_time_min = reorder_lead_time_min  # 15.0 min
        self.batch_size = batch_size                    # 50 unidades
        self.initial_stock = initial_stock              # 50 unidades
        self.seed = seed

        self.rng = np.random.default_rng(seed)

        # Estado del sistema
        self.current_time_min: float = 0.0
        self.stock_level: int = self.initial_stock
        self.station_status: StationStatus = StationStatus.IDLE
        self.current_order: Optional[LaptopOrder] = None
        self.is_reorder_in_progress: bool = False

        # Estructuras de datos
        self.event_queue: List[FactoryEvent] = []
        self.order_queue: List[LaptopOrder] = []
        self.completed_orders: List[LaptopOrder] = []
        self.active_batches: List[ReplenishmentBatch] = []
        self.completed_batches: List[ReplenishmentBatch] = []
        self.traces: List[DiscreteTrace] = []

        # Contadores y Métricas acumuladas
        self.order_id_counter: int = 0
        self.batch_id_counter: int = 0
        self.line_stops_count: int = 0
        self.total_starvation_time_min: float = 0.0
        self.starvation_start_time_min: Optional[float] = None
        self.orders_delayed_by_stock: int = 0
        self.total_busy_time_min: float = 0.0
        self.last_busy_start_min: Optional[float] = None

        # Seguimiento del lote inicial
        initial_batch = ReplenishmentBatch(
            batch_id=0,
            requested_time_min=0.0,
            arrived_time_min=0.0,
            quantity=self.initial_stock,
            units_remaining=self.initial_stock
        )
        self.active_batches.append(initial_batch)

        # Programar primer arribo
        self._schedule_next_arrival()

        # Registrar traza inicial
        self._log_trace(
            "INICIO_SIMULACION",
            f"Fábrica inicia simulación por {self.simulation_hours:.1f}h ({self.total_time_min:.0f} min). "
            f"Stock inicial: {self.stock_level} procesadores."
        )

    def _schedule_next_arrival(self):
        """Programa la llegada de la siguiente orden según proceso de Poisson."""
        interarrival = self.rng.exponential(scale=1.0 / self.arrival_rate_min)
        arr_time = self.current_time_min + interarrival
        if arr_time <= self.total_time_min:
            self.order_id_counter += 1
            order = LaptopOrder(
                order_id=self.order_id_counter,
                arrival_time_min=arr_time
            )
            event = FactoryEvent(arr_time, FactoryEvent.TYPE_ARRIVAL, order)
            heapq.heappush(self.event_queue, event)

    def _log_trace(self, event_type: str, description: str, order_id: Optional[int] = None):
        """Crea y almacena una traza detallada del estado actual."""
        trace = DiscreteTrace(
            time_min=self.current_time_min,
            event_type=event_type,
            description=description,
            queue_length=len(self.order_queue),
            stock_level=self.stock_level,
            station_state=self.station_status,
            order_id=order_id
        )
        self.traces.append(trace)
        if len(self.traces) > 10000:
            self.traces.pop(0)

    def _check_and_trigger_replenishment(self):
        """Verifica si el stock cayó por debajo de 10 y dispara la orden de reabastecimiento."""
        if self.stock_level < self.reorder_threshold and not self.is_reorder_in_progress:
            self.is_reorder_in_progress = True
            self.batch_id_counter += 1
            arrive_time = self.current_time_min + self.reorder_lead_time_min
            batch = ReplenishmentBatch(
                batch_id=self.batch_id_counter,
                requested_time_min=self.current_time_min,
                arrived_time_min=arrive_time,
                quantity=self.batch_size,
                units_remaining=self.batch_size
            )
            # Programar arribo del proveedor en 15 min
            event = FactoryEvent(arrive_time, FactoryEvent.TYPE_REPLENISHMENT, batch)
            heapq.heappush(self.event_queue, event)
            self._log_trace(
                "PEDIDO_PROVEEDOR",
                f"Stock crítico ({self.stock_level} < {self.reorder_threshold}). "
                f"Pedido de Lote #{batch.batch_id} (50 unidades) emitido. Llegada estimada en 15 min."
            )

    def _consume_processor_from_batch(self):
        """Descuenta 1 procesador del lote activo y controla el tiempo de despacho del lote."""
        self.stock_level -= 1
        for batch in self.active_batches:
            if batch.units_remaining > 0:
                batch.units_remaining -= 1
                if batch.units_remaining == 0:
                    batch.fully_consumed_time_min = self.current_time_min
                    self.completed_batches.append(batch)
                break
        # Limpiar lotes completados de la lista activa
        self.active_batches = [b for b in self.active_batches if b.units_remaining > 0]
        # Verificar si requiere reabastecimiento tras el consumo
        self._check_and_trigger_replenishment()

    def _try_start_next_assembly(self):
        """Intenta iniciar el ensamble de la siguiente orden en cola si la estación está disponible."""
        if self.station_status != StationStatus.BUSY and self.order_queue:
            if self.stock_level > 0:
                # Si estaba en parada de línea, finalizar el tiempo de starvation
                if self.station_status == StationStatus.STARVED:
                    if self.starvation_start_time_min is not None:
                        starvation_duration = self.current_time_min - self.starvation_start_time_min
                        self.total_starvation_time_min += starvation_duration
                        self.starvation_start_time_min = None
                    self._log_trace(
                        "REANUDACION_LINEA",
                        f"Línea reanudada con stock disponible ({self.stock_level} unidades)."
                    )

                next_order = self.order_queue.pop(0)
                self.current_order = next_order
                self.station_status = StationStatus.BUSY
                self.last_busy_start_min = self.current_time_min

                # Consumir procesador
                self._consume_processor_from_batch()

                # Generar tiempo de ensamble exponencial con media 5 min
                service_duration = self.rng.exponential(scale=self.service_mean_min)
                next_order.service_duration_min = service_duration
                next_order.service_start_time_min = self.current_time_min
                next_order.status = "ENSAMBLANDO"

                end_time = self.current_time_min + service_duration
                event = FactoryEvent(end_time, FactoryEvent.TYPE_SERVICE_END, next_order)
                heapq.heappush(self.event_queue, event)

                self._log_trace(
                    "INICIO_ENSAMBLE",
                    f"Iniciando ensamble Orden #{next_order.order_id}. "
                    f"Duración estimada: {service_duration:.2f} min. Stock restante: {self.stock_level}.",
                    order_id=next_order.order_id
                )
            else:
                # Stockout: No hay procesadores. Línea se detiene por falta de componentes.
                if self.station_status != StationStatus.STARVED:
                    self.station_status = StationStatus.STARVED
                    self.line_stops_count += 1
                    self.starvation_start_time_min = self.current_time_min
                    # Marcar la orden pendiente como retrasada por falta de inventario
                    top_order = self.order_queue[0]
                    if not top_order.delayed_by_stockout:
                        top_order.delayed_by_stockout = True
                        top_order.status = "ESPERANDO_STOCK"
                        self.orders_delayed_by_stock += 1

                    self._log_trace(
                        "PARADA_LINEA_STOCKOUT",
                        f"¡ALERTA! Línea detenida por falta de procesadores (Stock = 0). "
                        f"Orden #{top_order.order_id} retrasada esperando reabastecimiento.",
                        order_id=top_order.order_id
                    )

    def run(self) -> Dict[str, Any]:
        """
        Ejecuta la simulación completa hasta alcanzar el tiempo límite.
        Retorna el diccionario consolidado de métricas.
        """
        while self.event_queue:
            event = heapq.heappop(self.event_queue)
            if event.time_min > self.total_time_min:
                self.current_time_min = self.total_time_min
                break

            self.current_time_min = event.time_min

            if event.event_type == FactoryEvent.TYPE_ARRIVAL:
                order: LaptopOrder = event.payload
                self.order_queue.append(order)
                self._log_trace(
                    "LLEGADA_ORDEN",
                    f"Orden #{order.order_id} recibida en recepción. Longitud de cola: {len(self.order_queue)}.",
                    order_id=order.order_id
                )
                self._schedule_next_arrival()
                self._try_start_next_assembly()

            elif event.event_type == FactoryEvent.TYPE_SERVICE_END:
                order: LaptopOrder = event.payload
                order.completion_time_min = self.current_time_min
                order.status = "COMPLETADA"
                self.completed_orders.append(order)
                self.current_order = None
                self.station_status = StationStatus.IDLE

                if self.last_busy_start_min is not None:
                    self.total_busy_time_min += (self.current_time_min - self.last_busy_start_min)
                    self.last_busy_start_min = None

                self._log_trace(
                    "FIN_ENSAMBLE",
                    f"Orden #{order.order_id} ensamblada exitosamente. "
                    f"Tiempo en sistema: {order.total_system_time_min:.2f} min (Espera: {order.wait_time_min:.2f} min).",
                    order_id=order.order_id
                )
                self._try_start_next_assembly()

            elif event.event_type == FactoryEvent.TYPE_REPLENISHMENT:
                batch: ReplenishmentBatch = event.payload
                self.stock_level += batch.quantity
                self.active_batches.append(batch)
                self.is_reorder_in_progress = False

                self._log_trace(
                    "LLEGADA_LOTE",
                    f"Entrega de proveedor recibida. Lote #{batch.batch_id} (+{batch.quantity} procesadores). "
                    f"Nuevo Stock: {self.stock_level}."
                )
                self._try_start_next_assembly()

        # Ajuste de cierre de simulación
        self._finalize_simulation()
        return self.get_metrics()

    def step(self, dt_min: float) -> bool:
        """
        Avanza la simulación un paso temporal dt_min (utilizado por la animación interactiva de Pygame).
        Retorna True si la simulación continúa, o False si alcanzó el tiempo máximo.
        En modo infinito, continúa indefinidamente.
        """
        if math.isinf(self.total_time_min):
            target_time = self.current_time_min + dt_min
        else:
            target_time = min(self.total_time_min, self.current_time_min + dt_min)

        while self.event_queue and self.event_queue[0].time_min <= target_time:
            event = heapq.heappop(self.event_queue)
            self.current_time_min = event.time_min

            if event.event_type == FactoryEvent.TYPE_ARRIVAL:
                order: LaptopOrder = event.payload
                self.order_queue.append(order)
                self._log_trace(
                    "LLEGADA_ORDEN",
                    f"Orden #{order.order_id} recibida. Cola: {len(self.order_queue)}.",
                    order_id=order.order_id
                )
                self._schedule_next_arrival()
                self._try_start_next_assembly()

            elif event.event_type == FactoryEvent.TYPE_SERVICE_END:
                order: LaptopOrder = event.payload
                order.completion_time_min = self.current_time_min
                order.status = "COMPLETADA"
                self.completed_orders.append(order)
                if len(self.completed_orders) > 10000:
                    self.completed_orders.pop(0)
                self.current_order = None
                self.station_status = StationStatus.IDLE

                if self.last_busy_start_min is not None:
                    self.total_busy_time_min += (self.current_time_min - self.last_busy_start_min)
                    self.last_busy_start_min = None

                self._log_trace(
                    "FIN_ENSAMBLE",
                    f"Orden #{order.order_id} ensamblada. Tiempo: {order.total_system_time_min:.2f} min.",
                    order_id=order.order_id
                )
                self._try_start_next_assembly()

            elif event.event_type == FactoryEvent.TYPE_REPLENISHMENT:
                batch: ReplenishmentBatch = event.payload
                self.stock_level += batch.quantity
                self.active_batches.append(batch)
                self.is_reorder_in_progress = False

                self._log_trace(
                    "LLEGADA_LOTE",
                    f"Lote #{batch.batch_id} entregado (+{batch.quantity} procesadores). Stock: {self.stock_level}."
                )
                self._try_start_next_assembly()

        self.current_time_min = target_time
        if not math.isinf(self.total_time_min) and self.current_time_min >= self.total_time_min:
            self._finalize_simulation()
            return False
        return True

    def _finalize_simulation(self):
        """Cierra acumuladores si la simulación termina con eventos pendientes."""
        if self.station_status == StationStatus.BUSY and self.last_busy_start_min is not None:
            self.total_busy_time_min += (self.total_time_min - self.last_busy_start_min)
            self.last_busy_start_min = None
        elif self.station_status == StationStatus.STARVED and self.starvation_start_time_min is not None:
            self.total_starvation_time_min += (self.total_time_min - self.starvation_start_time_min)
            self.starvation_start_time_min = None

    def get_metrics(self) -> Dict[str, Any]:
        """Calcula y retorna todas las métricas clave solicitadas en el enunciado."""
        total_orders_arrived = self.order_id_counter
        total_orders_completed = len(self.completed_orders)
        orders_in_queue = len(self.order_queue)

        # 1. Tiempos de espera
        if self.completed_orders:
            avg_wait_time_min = float(np.mean([o.wait_time_min for o in self.completed_orders]))
            avg_system_time_min = float(np.mean([o.total_system_time_min for o in self.completed_orders]))
            max_wait_time_min = float(max([o.wait_time_min for o in self.completed_orders]))
        else:
            avg_wait_time_min = 0.0
            avg_system_time_min = 0.0
            max_wait_time_min = 0.0

        # 2. Tiempo total para despachar un lote
        dispatched_batch_times = [b.dispatch_time_min for b in self.completed_batches if b.dispatch_time_min is not None]
        avg_batch_dispatch_time_min = float(np.mean(dispatched_batch_times)) if dispatched_batch_times else 0.0
        avg_batch_cycle_time_min = float(np.mean([b.total_cycle_time_min for b in self.completed_batches if b.total_cycle_time_min is not None])) if dispatched_batch_times else 0.0

        # 3. Métricas de inventario y paradas de línea
        total_sim_time = max(0.01, self.current_time_min)

        live_busy = self.total_busy_time_min
        if self.station_status == StationStatus.BUSY and self.last_busy_start_min is not None:
            live_busy += (self.current_time_min - self.last_busy_start_min)
        station_utilization = (live_busy / total_sim_time) * 100.0

        live_starvation = self.total_starvation_time_min
        if self.station_status == StationStatus.STARVED and self.starvation_start_time_min is not None:
            live_starvation += (self.current_time_min - self.starvation_start_time_min)
        starvation_percentage = (live_starvation / total_sim_time) * 100.0

        # 4. Eficiencia en el reabastecimiento
        # Porcentaje de disponibilidad del stock y órdenes libres de retraso por componentes
        stock_availability_pct = max(0.0, 100.0 - starvation_percentage)
        orders_delayed_pct = (self.orders_delayed_by_stock / total_orders_arrived * 100.0) if total_orders_arrived > 0 else 0.0
        efficiency_replenishment_pct = max(0.0, 100.0 - orders_delayed_pct)

        dur_h = "Infinito" if math.isinf(self.simulation_hours) else round(self.simulation_hours, 2)

        return {
            "problema": "Simulación de Eventos Discretos (Fábrica de Laptops)",
            "duracion_horas": dur_h,
            "tiempo_simulado_min": round(self.current_time_min, 2),
            "tasa_llegada_lambda_h": self.arrival_rate_h,
            "tiempo_servicio_medio_min": self.service_mean_min,
            "umbral_inventario": self.reorder_threshold,
            "tamano_lote": self.batch_size,
            "tiempo_entrega_proveedor_min": self.reorder_lead_time_min,
            "total_ordenes_arribadas": total_orders_arrived,
            "total_ordenes_completadas": total_orders_completed,
            "ordenes_en_cola_final": orders_in_queue,
            "tiempo_espera_promedio_min": round(avg_wait_time_min, 2),
            "tiempo_espera_promedio_horas": round(avg_wait_time_min / 60.0, 4),
            "tiempo_sistema_promedio_min": round(avg_system_time_min, 2),
            "tiempo_espera_maximo_min": round(max_wait_time_min, 2),
            "tiempo_promedio_despacho_lote_min": round(avg_batch_dispatch_time_min, 2),
            "tiempo_promedio_despacho_lote_horas": round(avg_batch_dispatch_time_min / 60.0, 2),
            "tiempo_promedio_ciclo_lote_min": round(avg_batch_cycle_time_min, 2),
            "lotes_solicitados": self.batch_id_counter,
            "lotes_despachados_completos": len(self.completed_batches),
            "numero_detenciones_linea": self.line_stops_count,
            "tiempo_total_detencion_min": round(self.total_starvation_time_min, 2),
            "porcentaje_tiempo_detenido": round(starvation_percentage, 2),
            "ordenes_retrasadas_por_stock": self.orders_delayed_by_stock,
            "porcentaje_ordenes_retrasadas": round(orders_delayed_pct, 2),
            "eficiencia_reabastecimiento_pct": round(efficiency_replenishment_pct, 2),
            "disponibilidad_stock_pct": round(stock_availability_pct, 2),
            "utilizacion_estacion_pct": round(min(100.0, station_utilization), 2),
            "stock_final_procesadores": self.stock_level,
            "total_trazas_generadas": len(self.traces)
        }
