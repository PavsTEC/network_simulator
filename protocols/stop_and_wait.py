"""
Protocolo Stop and Wait
- Canal libre de errores (sin corrupción)
- Envía un frame y espera ACK (control de flujo)
- Sin timeout (no hay errores que manejar)
- Sin números de secuencia (no hay duplicados en canal sin errores)
"""

from models.frame import Frame
from protocols.protocol_interface import ProtocolInterface


class StopAndWaitProtocol(ProtocolInterface):
    """Protocolo Stop and Wait simple (canal sin errores)."""

    def __init__(self, machine_id: str):
        """Inicializa el protocolo Stop and Wait."""
        super().__init__(machine_id)

        # Estado del protocolo
        self.waiting_for_ack = False  # ¿Esperando ACK?

    def handle_network_layer_ready(self, network_layer, data_link_layer, simulator) -> dict:
        """Decide qué hacer cuando hay datos listos en Network Layer."""

        # Solo procesar si no estamos esperando ACK
        if self.waiting_for_ack:
            print(f"[StopWait-{self.machine_id}] Esperando ACK, no se pueden enviar más datos")
            return {'action': 'no_action'}

        if network_layer.has_data_ready():
            packet, destination = network_layer.get_packet()
            if packet and destination:
                self.waiting_for_ack = True

                # Crear frame DATA simple (sin seq num, canal sin errores)
                frame = Frame("DATA", 0, 0, packet)

                print(f"[StopWait-{self.machine_id}] Enviando frame")

                return {
                    'action': 'send_frame',
                    'frame': frame,
                    'destination': destination
                }

        return {'action': 'no_action'}

    def handle_frame_arrival(self, frame) -> dict:
        """Decide qué hacer con un frame recibido."""

        if frame.type == "DATA":
            # Frame de datos recibido - entregar y enviar ACK dummy
            print(f"[StopWait-{self.machine_id}] Frame recibido, enviando ACK")

            return {
                'action': 'deliver_packet_and_send_ack',
                'packet': frame.packet,
                'ack_seq': 0  # ACK dummy (sin secuencia en canal sin errores)
            }

        elif frame.type == "ACK":
            # ACK recibido - continuar enviando
            if self.waiting_for_ack:
                print(f"[StopWait-{self.machine_id}] ACK recibido")
                self.waiting_for_ack = False

                return {'action': 'continue_sending'}
            else:
                print(f"[StopWait-{self.machine_id}] ACK no esperado")
                return {'action': 'no_action'}

        return {'action': 'no_action'}

    def handle_frame_corruption(self, frame) -> dict:
        """Decide qué hacer con un frame corrupto."""
        # Stop and Wait NO maneja errores (canal sin errores según especificación)
        # Este método no debería llamarse en este protocolo
        print(f"[StopWait-{self.machine_id}] Frame corrupto recibido - ERROR: canal debería ser sin errores")
        return {'action': 'no_action'}

    def get_stats(self) -> dict:
        """Retorna estadísticas del protocolo."""
        stats = super().get_stats()
        stats.update({
            'waiting_for_ack': self.waiting_for_ack
        })
        return stats

    def get_protocol_name(self) -> str:
        """Obtiene el nombre del protocolo."""
        return "Stop and Wait"