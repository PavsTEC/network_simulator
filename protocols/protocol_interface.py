"""
Interfaz base para todos los protocolos de red.
Todos los protocolos deben heredar de esta clase e implementar sus métodos.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class ProtocolInterface(ABC):
    """Interfaz base que deben implementar todos los protocolos."""
    
    def __init__(self, machine_id: str):
        """
        Inicializa el protocolo con el ID de la máquina.
        
        Args:
            machine_id: Identificador único de la máquina
        """
        self.machine_id = machine_id
    
    @abstractmethod
    def handle_network_layer_ready(self, network_layer, data_link_layer, simulator) -> Dict[str, Any]:
        """
        Maneja cuando Network Layer tiene datos listos para enviar.
        
        Args:
            network_layer: Referencia al Network Layer
            data_link_layer: Referencia al Data Link Layer
            simulator: Referencia al simulador
            
        Returns:
            Dict con la acción a realizar y parámetros necesarios
        """
        pass
    
    @abstractmethod
    def handle_frame_arrival(self, frame) -> Dict[str, Any]:
        """
        Maneja la llegada de un frame válido.
        
        Args:
            frame: Frame recibido
            
        Returns:
            Dict con la acción a realizar y parámetros necesarios
        """
        pass
    
    @abstractmethod
    def handle_frame_corruption(self, frame) -> Dict[str, Any]:
        """
        Maneja un frame corrupto.
        
        Args:
            frame: Frame corrupto recibido
            
        Returns:
            Dict con la acción a realizar y parámetros necesarios
        """
        pass
    
    def handle_timeout(self, simulator) -> Dict[str, Any]:
        """
        Maneja eventos de timeout (opcional para protocolos que no lo necesiten).
        
        Args:
            simulator: Referencia al simulador
            
        Returns:
            Dict con la acción a realizar y parámetros necesarios
        """
        return {'action': 'no_action'}
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del protocolo.
        
        Returns:
            Dict con estadísticas del protocolo
        """
        return {
            'protocol': self.__class__.__name__,
            'machine_id': self.machine_id
        }
    
    @abstractmethod
    def get_protocol_name(self) -> str:
        """
        Obtiene el nombre del protocolo.
        
        Returns:
            Nombre del protocolo
        """
        pass