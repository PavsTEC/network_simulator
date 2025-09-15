from enum import Enum


class EventType(Enum):
    # Tipos de eventos del simulador
    FRAME_ARRIVAL = "frame_arrival"
    CKSUM_ERR = "cksum_err"
    TIMEOUT = "timeout"
    ACK_TIMEOUT = "ack_timeout"
    NETWORK_LAYER_READY = "network_layer_ready"


class Event:
    def __init__(self, event_type: EventType, timestamp: float, machine_id: str, data = None):
        self.event_type = event_type
        self.timestamp = timestamp
        self.machine_id = machine_id
        self.data = data

    def __lt__(self, other: 'Event') -> bool:
        # Comparación para ordenar eventos por tiempo
        return self.timestamp < other.timestamp

    def __str__(self) -> str:
        # Representación legible del evento
        data_info = f", data={type(self.data).__name__}" if self.data is not None else ""
        return f"Event({self.event_type.value}, t={self.timestamp:.2f}, machine={self.machine_id}{data_info})"