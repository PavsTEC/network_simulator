from enum import Enum
from dataclasses import dataclass
import time

class EventType(Enum):
    FRAME_ARRIVAL = "frame_arrival"
    CKSUM_ERR = "cksum_err"
    TIMEOUT = "timeout"
    ACK_TIMEOUT = "ack_timeout"
    NETWORK_LAYER_READY = "network_layer_ready"

@dataclass
class Event:
    event_type: EventType
    timestamp: float
    machine_id: str
    data: any = None
    
    def __lt__(self, other):
        # Para usar en heapq (priority queue)
        return self.timestamp < other.timestamp
    
    def __str__(self):
        return f"Event({self.event_type.value}, t={self.timestamp:.2f}, machine={self.machine_id})"