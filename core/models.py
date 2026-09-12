"""
Modelos de Dominio y Entidades del Sistema de Simulación.
Universidad José Antonio Páez - Parcial III Simulación.
"""

from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum


class StationStatus(str, Enum):
    """Estados posibles de la estación principal de ensamblaje."""
    IDLE = "LIBRE"
    BUSY = "OCUPADA"
    STARVED = "DETENIDA_POR_STOCK"


@dataclass
class LaptopOrder:
    """
    Representa una orden de producción de laptop en la fábrica.
    Cada orden requiere 1 procesador de gama alta del inventario.
    """
    order_id: int
    arrival_time_min: float
    service_duration_min: float = 0.0
    service_start_time_min: Optional[float] = None
    completion_time_min: Optional[float] = None
    delayed_by_stockout: bool = False
    starvation_delay_min: float = 0.0
    status: str = "EN_COLA"

    @property
    def wait_time_min(self) -> float:
        """Tiempo de espera en cola antes de iniciar ensamblaje."""
        if self.service_start_time_min is not None:
            return max(0.0, self.service_start_time_min - self.arrival_time_min)
        return 0.0

    @property
    def total_system_time_min(self) -> float:
        """Tiempo total transcurrido desde la llegada hasta el despacho final."""
        if self.completion_time_min is not None:
            return max(0.0, self.completion_time_min - self.arrival_time_min)
        return 0.0


@dataclass
class ReplenishmentBatch:
    """
    Lote de reabastecimiento de procesadores entregado por el proveedor.
    Lote estándar de 50 unidades con tiempo de entrega de 15 minutos.
    """
    batch_id: int
    requested_time_min: float
    arrived_time_min: float
    quantity: int = 50
    units_remaining: int = 50
    fully_consumed_time_min: Optional[float] = None

    @property
    def dispatch_time_min(self) -> Optional[float]:
        """Tiempo total que toma despachar el lote (desde que llega hasta que se consume)."""
        if self.fully_consumed_time_min is not None:
            return max(0.0, self.fully_consumed_time_min - self.arrived_time_min)
        return None

    @property
    def total_cycle_time_min(self) -> Optional[float]:
        """Tiempo total de ciclo de vida del lote (desde el pedido al proveedor hasta agotar la última unidad)."""
        if self.fully_consumed_time_min is not None:
            return max(0.0, self.fully_consumed_time_min - self.requested_time_min)
        return None


@dataclass
class DiscreteTrace:
    """Traza estructurada de un evento discreto en la fábrica."""
    time_min: float
    event_type: str
    description: str
    queue_length: int
    stock_level: int
    station_state: StationStatus
    order_id: Optional[int] = None

    def formatted_line(self) -> str:
        """Formatea la traza para visualización en log y archivo de texto."""
        hours = int(self.time_min // 60)
        minutes = int(self.time_min % 60)
        seconds = int((self.time_min * 60) % 60)
        time_str = f"[{hours:02d}:{minutes:02d}:{seconds:02d}]"
        return (
            f"{time_str} | Evento: {self.event_type:<20} | "
            f"Estado: {self.station_state.value:<18} | Cola: {self.queue_length:3d} | "
            f"Stock: {self.stock_level:3d} | {self.description}"
        )


@dataclass
class ContinuousDataPoint:
    """Registro de estado instantáneo de la simulación continua del clúster."""
    time_h: float
    time_s: float
    traffic_gbps: float
    temperature_c: float
    heat_gen: float
    heat_dis: float
    is_throttling: bool
    efficiency: float
    throughput_gbps: float
    cumulative_terabytes: float

    def formatted_line(self) -> str:
        """Formatea el punto continuo para trazas muestreadas."""
        hours = int(self.time_h)
        mins = int((self.time_h * 60) % 60)
        secs = int((self.time_h * 3600) % 60)
        time_str = f"[{hours:02d}:{mins:02d}:{secs:02d}]"
        throttle_tag = "ALERTA: THROTTLING" if self.is_throttling else "NORMAL (Estable)"
        return (
            f"{time_str} | Tráfico: {self.traffic_gbps:4.2f} Gbps | "
            f"Temp: {self.temperature_c:5.2f}°C [{throttle_tag:<18}] | "
            f"Efic: {self.efficiency*100:5.1f}% | "
            f"Throughput: {self.throughput_gbps:4.2f} Gbps | "
            f"Total: {self.cumulative_terabytes:6.2f} TB"
        )
