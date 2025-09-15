from enum import Enum
from typing import Any, Optional


class EventType(Enum):
    # Tipos de eventos del simulador
    FRAME_ARRIVAL = "frame_arrival"
    CKSUM_ERR = "cksum_err"
    TIMEOUT = "timeout"
    ACK_TIMEOUT = "ack_timeout"
    NETWORK_LAYER_READY = "network_layer_ready"


class Event:
    def __init__(self, event_type: EventType, timestamp: float, machine_id: str, data: Optional[Any] = None):
        # Validaciones básicas
        if timestamp < 0:
            raise ValueError("Timestamp debe ser no negativo")
        if not machine_id.strip():
            raise ValueError("Machine ID no puede estar vacío")

        self.event_type = event_type
        self.timestamp = timestamp  # Momento en que ocurre el evento
        self.machine_id = machine_id  # Máquina destino
        self.data = data  # Datos adicionales del evento

    def __lt__(self, other: 'Event') -> bool:
        # Comparación para ordenar eventos por tiempo
        return self.timestamp < other.timestamp

    def __str__(self) -> str:
        # Representación legible del evento
        data_info = f", data={type(self.data).__name__}" if self.data is not None else ""
        return f"Event({self.event_type.value}, t={self.timestamp:.2f}, machine={self.machine_id}{data_info})"