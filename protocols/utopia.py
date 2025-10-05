"""
Protocolo Utopia - versión simplificada.
Solo lógica esencial: envío inmediato sin control.
"""

from models.frame import Frame
from protocols.protocol_interface import ProtocolInterface


class UtopiaProtocol(ProtocolInterface):
    """Protocolo Utopia - el más simple posible."""

    def __init__(self, machine_id: str):
        """Inicializa el protocolo Utopia."""
        super().__init__(machine_id)

    def handle_network_layer_ready(self, network_layer) -> None:
        """Maneja cuando Network Layer tiene datos listos para enviar."""
        packet, destination = self.from_network_layer(network_layer)
        if packet and destination:
            # Utopia: crear frame y enviar inmediatamente
            frame = Frame("DATA", 0, 0, packet)
            self.to_physical_layer(frame, destination)

    def handle_frame_arrival(self, frame: Frame) -> None:
        """Maneja la llegada de un frame válido."""
        # Utopia: aceptar todo frame inmediatamente
        if frame.packet:
            self.to_network_layer(frame.packet)

    def handle_frame_corruption(self, frame: Frame) -> None:
        """Maneja un frame corrupto."""
        # Utopia: simplemente ignora frames corruptos (no hay errores según requerimientos)
        self._log(f"[Utopia-{self.machine_id}] Frame corrupto ignorado")
    
    def get_protocol_name(self) -> str:
        """Obtiene el nombre del protocolo."""
        return "Utopia"