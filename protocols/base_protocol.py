from abc import ABC, abstractmethod
from typing import Dict, Any, TYPE_CHECKING
from layers.network_layer import NetworkLayer
from layers.physical_layer import PhysicalLayer
from models.events import Event

if TYPE_CHECKING:
    from simulation.simulator import Simulator


class BaseProtocol(ABC):
    def __init__(self, machine_id: str):
        self.machine_id = machine_id
        self.network_layer = NetworkLayer(machine_id)  # Capa de red para manejo de paquetes
        self.physical_layer = PhysicalLayer()  # Capa física para transmisión
        self.state: Dict[str, Any] = {}  # Estado interno del protocolo
        self.frames_sent = 0  # Contador de frames enviados
        self.frames_received = 0  # Contador de frames recibidos

    @abstractmethod
    def handle_event(self, event: Event, simulator: 'Simulator') -> None:
        # Procesa eventos específicos del protocolo
        pass

    @abstractmethod
    def start_protocol(self, simulator: 'Simulator') -> None:
        # Inicializa el protocolo y programa eventos iniciales
        pass

    def set_error_rate(self, error_rate: float) -> bool:
        # Configura la tasa de errores de la capa física
        try:
            self.physical_layer.set_error_rate(error_rate)
            return True
        except Exception as e:
            print(f"[{self.machine_id}] Error configurando tasa de errores: {e}")
            return False

    def get_error_rate(self) -> float:
        # Obtiene la tasa de errores actual
        return self.physical_layer.get_error_rate()

    def get_stats(self) -> Dict[str, Any]:
        # Recolecta estadísticas de todas las capas
        net_stats = self.network_layer.get_stats()
        phy_stats = self.physical_layer.get_stats()

        return {
            'machine_id': self.machine_id,
            'frames_sent': self.frames_sent,
            'frames_received': self.frames_received,
            'network_layer': net_stats,
            'physical_layer': phy_stats
        }
