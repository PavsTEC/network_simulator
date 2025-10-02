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
        self.machine_id = machine_id

    def handle_network_layer_ready(self, network_layer, data_link_layer, simulator) -> dict:
        """Decide qué hacer cuando hay datos listos."""
        if network_layer.has_data_ready():
            packet, destination = network_layer.get_packet()
            if packet and destination:
                # Utopia: crear frame y enviar inmediatamente
                frame = Frame("DATA", 0, 0, packet)

                return {
                    'action': 'send_frame',
                    'frame': frame,
                    'destination': destination
                }

        return {'action': 'no_action'}

    def handle_frame_arrival(self, frame: Frame) -> dict:
        """Decide qué hacer con un frame recibido."""
        # Utopia: aceptar todo frame inmediatamente
        if frame.packet:
            return {
                'action': 'deliver_packet',
                'packet': frame.packet
            }

        return {'action': 'no_action'}

    def handle_frame_corruption(self, frame: Frame) -> dict:
        """Decide qué hacer con un frame corrupto."""
        # Utopia: simplemente ignora frames corruptos (no hay errores según requerimientos)
        print(f"[Protocol-{self.machine_id}] Frame corrupto ignorado (Utopia)")
        return {'action': 'no_action'}
    
    def get_protocol_name(self) -> str:
        """Obtiene el nombre del protocolo."""
        return "Utopia"