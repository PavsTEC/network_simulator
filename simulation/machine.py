"""
Clase Machine simplificada que representa una máquina en la simulación.
"""

from protocols.base_protocol import BaseProtocol
from models.events import Event


class Machine:
    """Representa una máquina en la red que ejecuta un protocolo específico."""

    def __init__(self, machine_id: str, protocol: BaseProtocol):
        """Inicializa una nueva máquina."""
        self.machine_id = machine_id
        self.protocol = protocol

    def handle_event(self, event: Event, simulator) -> None:
        """Maneja un evento dirigido a esta máquina."""
        print(f"[Machine-{self.machine_id}] Iniciando máquina...")
        self.protocol.handle_event(event, simulator)

    def start(self, simulator) -> None:
        """Inicia la máquina y su protocolo."""
        print(f"[Machine-{self.machine_id}] Iniciando máquina...")
        self.protocol.start_protocol(simulator)

    def set_error_rate(self, error_rate: float) -> bool:
        """Configura la tasa de errores de la capa física."""
        return self.protocol.set_error_rate(error_rate)

    def get_error_rate(self):
        """Obtiene la tasa de errores actual de la capa física."""
        return self.protocol.get_error_rate()

    def get_stats(self):
        """Obtiene las estadísticas de la máquina."""
        return self.protocol.get_stats()