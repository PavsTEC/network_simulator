"""
Interfaz base para todos los protocolos de red.

Los protocolos implementan la lógica de control de enlace y pueden
llamar directamente a métodos del simulador para enviar frames,
programar timeouts, etc.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from simulation.simulator import Simulator


class ProtocolInterface(ABC):
    """Interfaz base que deben implementar todos los protocolos."""

    def __init__(self, machine_id: str):
        """
        Inicializa el protocolo.

        Args:
            machine_id: Identificador único de la máquina
        """
        self.machine_id = machine_id
        self.simulator = None  # Referencia al simulador

    def set_simulator(self, simulator: 'Simulator') -> None:
        """Asigna la referencia al simulador."""
        self.simulator = simulator

    def _log(self, message: str) -> None:
        """Imprime un mensaje con timestamp del simulador."""
        if self.simulator:
            timestamp = self.simulator.get_current_time()
            print(f"[t={timestamp:.2f}s] {message}")
        else:
            print(message)
    
    @abstractmethod
    def handle_network_layer_ready(self, network_layer) -> None:
        """
        Maneja cuando Network Layer tiene datos listos para enviar.

        Args:
            network_layer: Referencia al Network Layer
        """
        pass

    @abstractmethod
    def handle_frame_arrival(self, frame) -> None:
        """
        Maneja la llegada de un frame válido.

        Args:
            frame: Frame recibido sin errores
        """
        pass

    @abstractmethod
    def handle_frame_corruption(self, frame) -> None:
        """
        Maneja un frame corrupto.

        Args:
            frame: Frame recibido con errores de checksum
        """
        pass

    def handle_timeout(self) -> None:
        """Maneja eventos de timeout."""
        pass  # Los protocolos sin timeout no necesitan implementar esto
    
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

    def is_bidirectional(self) -> bool:
        """
        Indica si el protocolo soporta comunicación bidireccional.

        Returns:
            True si el protocolo es bidireccional, False si es unidireccional
        """
        return False

    # Métodos helper para que los protocolos interactúen con el simulador
    def to_physical_layer(self, frame, destination: str) -> None:
        """Envía un frame a la capa física."""
        if self.simulator:
            self.simulator.send_frame_from_protocol(self.machine_id, frame, destination)

    def to_network_layer(self, packet) -> None:
        """Entrega un packet a la capa de red."""
        if self.simulator:
            self.simulator.deliver_packet_to_network(self.machine_id, packet)

    def start_timer(self, timeout_duration: float = None, timer_id: int = None) -> None:
        """Inicia un timer que generará un evento de timeout."""
        if self.simulator:
            self.simulator.start_protocol_timer(self.machine_id, timeout_duration, timer_id)

    def stop_timer(self) -> None:
        """Detiene el timer activo."""
        if self.simulator:
            self.simulator.stop_protocol_timer(self.machine_id)

    def from_network_layer(self, network_layer):
        """Obtiene el siguiente packet de la capa de red."""
        if network_layer.has_data_ready():
            return network_layer.get_packet()
        return None, None

    def enable_network_layer(self) -> None:
        """Programa un evento para intentar enviar más datos inmediatamente."""
        if self.simulator:
            from models.events import Event, EventType
            event = Event(EventType.NETWORK_LAYER_READY,
                         self.simulator.get_current_time(),
                         self.machine_id)
            self.simulator.schedule_event(event)