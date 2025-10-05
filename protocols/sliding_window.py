"""
Protocolo Sliding Window (Protocol 4) - Versión bidireccional
- Comunicación full-duplex bidireccional
- Piggybacking de ACKs en frames de datos
- Números de secuencia alternantes (0,1)
- Timeout y reenvío automático
"""

from models.frame import Frame
from models.events import Event, EventType
from protocols.protocol_interface import ProtocolInterface


class SlidingWindowProtocol(ProtocolInterface):
    """Protocolo Sliding Window bidireccional con piggybacking."""

    def __init__(self, machine_id: str):
        """Inicializa el protocolo Sliding Window."""
        super().__init__(machine_id)

        # Estado del emisor
        self.next_frame_to_send = 0  # Próximo frame a enviar (0 o 1)

        # Estado del receptor
        self.frame_expected = 0  # Frame esperado (0 o 1)

        # Control de reenvío
        self.waiting_for_ack = False
        self.last_packet_sent = None  # Buffer del último paquete enviado
        self.last_destination = None

    def handle_network_layer_ready(self, network_layer, data_link_layer, simulator) -> dict:
        """Maneja cuando Network Layer tiene datos listos para enviar."""

        # Solo enviar si no estamos esperando ACK
        if self.waiting_for_ack:
            print(f"[SlidingWindow-{self.machine_id}] Esperando ACK, no se pueden enviar más datos")
            return {'action': 'no_action'}

        if network_layer.has_data_ready():
            packet, destination = network_layer.get_packet()
            if packet and destination:
                # Crear frame con piggybacked ACK
                # El ACK es para frame_expected - 1 (el último que recibimos correctamente)
                piggybacked_ack = 1 - self.frame_expected

                frame = Frame("DATA", self.next_frame_to_send, piggybacked_ack, packet)

                # Guardar para posible reenvío
                self.last_packet_sent = packet
                self.last_destination = destination
                self.waiting_for_ack = True

                print(f"[SlidingWindow-{self.machine_id}] Enviando frame seq={self.next_frame_to_send}, ack={piggybacked_ack}")

                return {
                    'action': 'send_frame_with_timeout',
                    'frame': frame,
                    'destination': destination
                }

        return {'action': 'no_action'}

    def handle_frame_arrival(self, frame) -> dict:
        """Maneja la llegada de un frame válido."""

        if frame.type == "DATA":
            # Frame de datos recibido
            print(f"[SlidingWindow-{self.machine_id}] Frame DATA recibido seq={frame.seq_num}, ack={frame.ack_num}")

            # Manejar stream de entrada
            packet_to_deliver = None
            if frame.seq_num == self.frame_expected:
                # Secuencia correcta - entregar paquete
                packet_to_deliver = frame.packet
                self.frame_expected = 1 - self.frame_expected  # Alternar
                print(f"[SlidingWindow-{self.machine_id}] Secuencia correcta, avanzando frame_expected a {self.frame_expected}")

            # Manejar stream de salida (piggybacked ACK)
            if self.waiting_for_ack and frame.ack_num == self.next_frame_to_send:
                # ACK recibido para nuestro frame enviado
                print(f"[SlidingWindow-{self.machine_id}] ACK recibido para seq={frame.ack_num}")
                self.waiting_for_ack = False
                self.next_frame_to_send = 1 - self.next_frame_to_send  # Alternar

            # Siempre enviar un frame de respuesta (con datos si hay, o ACK puro)
            if packet_to_deliver:
                return {
                    'action': 'deliver_packet_and_send_ack',
                    'packet': packet_to_deliver,
                    'ack_seq': frame.seq_num
                }
            else:
                # Frame duplicado o fuera de orden - solo ACK
                return {
                    'action': 'send_ack_only',
                    'ack_seq': 1 - self.frame_expected  # ACK del último correcto
                }

        elif frame.type == "ACK":
            # ACK puro recibido
            if self.waiting_for_ack and frame.ack_num == self.next_frame_to_send:
                print(f"[SlidingWindow-{self.machine_id}] ACK puro recibido para seq={frame.ack_num}")
                self.waiting_for_ack = False
                self.next_frame_to_send = 1 - self.next_frame_to_send

                return {'action': 'stop_timeout_and_continue'}
            else:
                print(f"[SlidingWindow-{self.machine_id}] ACK incorrecto o no esperado")
                return {'action': 'no_action'}

        return {'action': 'no_action'}

    def handle_frame_corruption(self, frame) -> dict:
        """Maneja un frame corrupto."""
        print(f"[SlidingWindow-{self.machine_id}] Frame corrupto recibido - ignorando")
        # El timeout manejará el reenvío si es necesario
        return {'action': 'no_action'}

    def handle_timeout(self, simulator) -> dict:
        """Maneja evento de timeout."""
        if self.waiting_for_ack and self.last_packet_sent:
            print(f"[SlidingWindow-{self.machine_id}] TIMEOUT - Reenviando frame seq={self.next_frame_to_send}")

            # Recrear frame con piggybacked ACK actualizado
            piggybacked_ack = 1 - self.frame_expected
            frame = Frame("DATA", self.next_frame_to_send, piggybacked_ack, self.last_packet_sent)

            return {
                'action': 'send_frame_with_timeout',
                'frame': frame,
                'destination': self.last_destination
            }

        return {'action': 'no_action'}

    def get_stats(self) -> dict:
        """Retorna estadísticas del protocolo."""
        stats = super().get_stats()
        stats.update({
            'next_frame_to_send': self.next_frame_to_send,
            'frame_expected': self.frame_expected,
            'waiting_for_ack': self.waiting_for_ack
        })
        return stats

    def get_protocol_name(self) -> str:
        """Obtiene el nombre del protocolo."""
        return "Sliding Window"

    def is_bidirectional(self) -> bool:
        """Indica si el protocolo es bidireccional."""
        return True
