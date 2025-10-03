"""
Protocolo Sliding Window de 1 bit (Alternating Bit) - Bidireccional (CLI)
- Ventana de emisión = 1
- Ventana de recepción = 1
- Números de secuencia alternantes (0,1)
- ACK inmediato (como tu Stop-and-Wait)
"""

from models.frame import Frame
from protocols.protocol_interface import ProtocolInterface


class SlidingWindow1BitProtocol(ProtocolInterface):
    """Protocolo Alternating Bit bidireccional sobre la interfaz del proyecto."""

    def __init__(self, machine_id: str):
        self.machine_id = machine_id
        # Estado de emisor
        self.next_seq_to_send = 0      # 0/1
        self.waiting_for_ack = False   # True si hay un DATA en vuelo
        # Estado de receptor
        self.frame_expected = 0        # siguiente seq válido a recibir (0/1)

        # Métricas simples
        self.sent_data = 0
        self.received_data = 0
        self.acks_sent = 0
        self.acks_received = 0
        self.duplicates = 0

    def handle_network_layer_ready(self, network_layer, data_link_layer, simulator) -> dict:
        """Cuando hay datos listos para enviar desde la capa de red."""
        # En Alternating Bit, solo enviamos nuevo DATA si no hay uno pendiente de ACK
        if self.waiting_for_ack:
            print(f"[SW1-{self.machine_id}] Esperando ACK del seq={self.next_seq_to_send}, no se envía nuevo DATA")
            return {'action': 'no_action'}

        if network_layer.has_data_ready():
            packet, destination = network_layer.get_packet()
            if packet and destination:
                frame = Frame("DATA", self.next_seq_to_send, 0, packet)
                print(f"[SW1-{self.machine_id}] Enviando DATA seq={self.next_seq_to_send} → {destination}")
                self.waiting_for_ack = True
                self.sent_data += 1
                return {
                    'action': 'send_frame',
                    'frame': frame,
                    'destination': destination
                }

        return {'action': 'no_action'}

    def handle_frame_arrival(self, frame: Frame) -> dict:
        """Procesa llegada de un frame (DATA/ACK). Checksum ya fue validado por DataLinkLayer."""
        if frame.type == "DATA":
            # Receptor: aceptar solo el esperado, ACKear y alternar
            if frame.seq_num == self.frame_expected:
                print(f"[SW1-{self.machine_id}] DATA seq={frame.seq_num} correcto → entregar y ACK")
                self.received_data += 1
                self.frame_expected = 1 - self.frame_expected  # Alternar esperado
                return {
                    'action': 'deliver_packet_and_send_ack',
                    'packet': frame.packet,
                    'ack_seq': frame.seq_num
                }
            else:
                # Duplicado o fuera de orden: no entregar, solo ACK
                print(f"[SW1-{self.machine_id}] DATA seq={frame.seq_num} duplicado/no esperado → solo ACK")
                self.duplicates += 1
                return {
                    'action': 'send_ack_only',
                    'ack_seq': frame.seq_num
                }

        elif frame.type == "ACK":
            # Emisor: si coincide con el DATA en vuelo, liberar y alternar
            if self.waiting_for_ack and frame.ack_num == self.next_seq_to_send:
                print(f"[SW1-{self.machine_id}] ACK seq={frame.ack_num} recibido → listo para siguiente DATA")
                self.waiting_for_ack = False
                self.next_seq_to_send = 1 - self.next_seq_to_send  # Alternar
                self.acks_received += 1
                return {'action': 'continue_sending'}
            else:
                print(f"[SW1-{self.machine_id}] ACK seq={frame.ack_num} inesperado/duplicado → ignorar")
                return {'action': 'no_action'}

        return {'action': 'no_action'}

    def handle_frame_corruption(self, frame: Frame) -> dict:
        """Frame corrupto detectado por DataLinkLayer."""
        print(f"[SW1-{self.machine_id}] Frame corrupto recibido → ignorar")
        return {'action': 'no_action'}

    def handle_timeout(self, timer_id=None) -> dict:
        # Aquí no implementamos timers; se puede extender si el simulador lo requiere
        return {'action': 'no_action'}

    def get_stats(self) -> dict:
        stats = super().get_stats()
        stats.update({
            'next_seq_to_send': self.next_seq_to_send,
            'frame_expected': self.frame_expected,
            'waiting_for_ack': self.waiting_for_ack,
            'sent_data': self.sent_data,
            'received_data': self.received_data,
            'acks_sent': self.acks_sent,
            'acks_received': self.acks_received,
            'duplicates': self.duplicates,
        })
        return stats

    def get_protocol_name(self) -> str:
        return "Sliding Window"