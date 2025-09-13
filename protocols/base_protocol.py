from abc import ABC, abstractmethod
from layers.network_layer import NetworkLayer
from layers.physical_layer import PhysicalLayer
from models.events import Event

class BaseProtocol(ABC):
    def __init__(self, machine_id: str):
        self.machine_id = machine_id
        self.network_layer = NetworkLayer(machine_id)
        self.physical_layer = PhysicalLayer()
        self.state = {}
        self.frames_sent = 0
        self.frames_received = 0
    
    @abstractmethod
    def handle_event(self, event: Event, simulator):
        """Maneja un evento específico"""
        pass
    
    @abstractmethod
    def start_protocol(self, simulator):
        """Inicia el protocolo"""
        pass
    
    def get_stats(self):
        """Retorna estadísticas del protocolo"""
        net_stats = self.network_layer.get_stats()
        phy_stats = self.physical_layer.get_stats()
        
        return {
            'machine_id': self.machine_id,
            'frames_sent': self.frames_sent,
            'frames_received': self.frames_received,
            'network_layer': net_stats,
            'physical_layer': phy_stats
        }
