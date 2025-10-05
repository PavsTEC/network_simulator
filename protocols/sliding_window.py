"""
Protocolo Sliding Window de 1 bit (Alternating Bit) - Bidireccional
Implementación base de Manfred, adaptada a la nueva arquitectura.

- Ventana de emisión = 1
- Ventana de recepción = 1
- Números de secuencia alternantes (0,1)
- ACK inmediato (como Stop-and-Wait)
- Timeout y retransmisión automática
- Comunicación bidireccional
"""

from models.frame import Frame
from protocols.protocol_interface import ProtocolInterface


class SlidingWindowProtocol(ProtocolInterface):
    """Protocolo Alternating Bit bidireccional."""

    def __init__(self, machine_id: str):
        super().__init__(machine_id)

        # Estado emisor
        self.next_seq_to_send = 0
        self.waiting_for_ack = False
        self.last_frame_sent = None
        self.last_destination = None

        # Estado receptor
        self.frame_expected = 0

        # Métricas
        self.sent_data = 0
        self.received_data = 0
        self.acks_sent = 0
        self.acks_received = 0
        self.duplicates = 0

    def handle_network_layer_ready(self, network_layer) -> None:
        """Maneja cuando Network Layer tiene datos listos para enviar."""
        if self.waiting_for_ack:
            self._log(f"[SW1-{self.machine_id}] Esperando ACK del seq={self.next_seq_to_send}, no se envía nuevo DATA")
            return

        packet, destination = self.from_network_layer(network_layer)
        if packet and destination:
            frame = Frame("DATA", self.next_seq_to_send, 0, packet)
            self._log(f"[SW1-{self.machine_id}] Enviando DATA seq={self.next_seq_to_send} -> {destination}")

            self.waiting_for_ack = True
            self.last_frame_sent = frame
            self.last_destination = destination
            self.sent_data += 1

            # Enviar frame con timeout
            self.to_physical_layer(frame, destination)
            self.start_timer()

    def handle_frame_arrival(self, frame: Frame) -> None:
        """Maneja la llegada de un frame válido."""
        if frame.type == "DATA":
            # Receptor: aceptar solo el esperado
            if frame.seq_num == self.frame_expected:
                self._log(f"[SW1-{self.machine_id}] DATA seq={frame.seq_num} correcto -> entregar y ACK")
                self.received_data += 1
                self.frame_expected = 1 - self.frame_expected
                self.acks_sent += 1

                # Entregar paquete
                self.to_network_layer(frame.packet)

                # Enviar ACK
                ack_frame = Frame("ACK", 0, frame.seq_num)
                self.to_physical_layer(ack_frame, "A" if self.machine_id == "B" else "B")

            else:
                self._log(f"[SW1-{self.machine_id}] DATA seq={frame.seq_num} duplicado/no esperado -> solo ACK")
                self.duplicates += 1
                self.acks_sent += 1

                # Reenviar ACK del frame duplicado
                ack_frame = Frame("ACK", 0, frame.seq_num)
                self.to_physical_layer(ack_frame, "A" if self.machine_id == "B" else "B")

        elif frame.type == "ACK":
            # Emisor: validar ACK
            if self.waiting_for_ack and frame.ack_num == self.next_seq_to_send:
                self._log(f"[SW1-{self.machine_id}] ACK seq={frame.ack_num} recibido -> listo para siguiente DATA")
                self.waiting_for_ack = False
                self.next_seq_to_send = 1 - self.next_seq_to_send
                self.acks_received += 1

                # Detener timeout
                self.stop_timer()

                # Intentar enviar siguiente paquete inmediatamente
                self.enable_network_layer()
            else:
                self._log(f"[SW1-{self.machine_id}] ACK seq={frame.ack_num} inesperado o duplicado -> ignorar")

    def handle_frame_corruption(self, frame: Frame) -> None:
        """Maneja un frame corrupto."""
        self._log(f"[SW1-{self.machine_id}] Frame corrupto recibido -> ignorar")

    def handle_timeout(self) -> None:
        """Maneja eventos de timeout."""
        if self.waiting_for_ack and self.last_frame_sent:
            self._log(f"[SW1-{self.machine_id}] TIMEOUT -> retransmitir DATA seq={self.last_frame_sent.seq_num}")

            # Reenviar frame
            self.to_physical_layer(self.last_frame_sent, self.last_destination)
            self.start_timer()
        else:
            self._log(f"[SW1-{self.machine_id}] TIMEOUT ignorado (ACK ya recibido)")

    def is_bidirectional(self) -> bool:
        """Indica que este protocolo es bidireccional."""
        return True

    def get_stats(self) -> dict:
        """Retorna estadísticas del protocolo."""
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
        """Obtiene el nombre del protocolo."""
        return "Sliding Window"
