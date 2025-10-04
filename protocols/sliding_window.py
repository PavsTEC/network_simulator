"""
Protocolo Sliding Window de 1 bit (Alternating Bit) - Bidireccional (CLI)
- Ventana de emisión = 1
- Ventana de recepción = 1
- Números de secuencia alternantes (0,1)
- ACK inmediato (como Stop-and-Wait)
- Timeout y retransmisión automática
"""

from models.frame import Frame
from models.events import Event, EventType
from protocols.protocol_interface import ProtocolInterface


class SlidingWindow1BitProtocol(ProtocolInterface):
    '''Protocolo Alternating Bit bidireccional'''

    def __init__(self, machine_id: str):
        super().__init__(machine_id)
        self.machine_id = machine_id

        # Estado emisor
        self.next_seq_to_send = 0
        self.waiting_for_ack = False
        self.last_frame_sent = None
        self.last_destination = None

        # Estado receptor
        self.frame_expected = 0

        # Control de timeout
        self.timeout_duration = 4.0
        self.timeout_event_scheduled = False

        # Métricas
        self.sent_data = 0
        self.received_data = 0
        self.acks_sent = 0
        self.acks_received = 0
        self.duplicates = 0

    def handle_network_layer_ready(self, network_layer, data_link_layer, simulator) -> dict:
        """Cuando hay datos listos para enviar desde la capa de red."""
        if self.waiting_for_ack:
            print(f"[SW1-{self.machine_id}] Esperando ACK del seq={self.next_seq_to_send}, no se envía nuevo DATA")
            return {'action': 'no_action'}

        if network_layer.has_data_ready():
            packet, destination = network_layer.get_packet()
            if packet and destination:
                frame = Frame("DATA", self.next_seq_to_send, 0, packet)
                print(f"[SW1-{self.machine_id}] Enviando DATA seq={self.next_seq_to_send} → {destination}")

                self.waiting_for_ack = True
                self.last_frame_sent = frame
                self.last_destination = destination
                self.sent_data += 1

                # Programa timeout
                self._schedule_timeout(simulator)

                return {'action': 'send_frame', 'frame': frame, 'destination': destination}

        return {'action': 'no_action'}

    def handle_frame_arrival(self, frame: Frame) -> dict:
        """Procesa llegada de un frame (DATA/ACK)."""
        if frame.type == "DATA":
            # Receptor: aceptar solo el esperado
            if frame.seq_num == self.frame_expected:
                print(f"[SW1-{self.machine_id}] DATA seq={frame.seq_num} correcto → entregar y ACK")
                self.received_data += 1
                self.frame_expected = 1 - self.frame_expected
                self.acks_sent += 1
                return {'action': 'deliver_packet_and_send_ack', 'packet': frame.packet, 'ack_seq': frame.seq_num}
            else:
                print(f"[SW1-{self.machine_id}] DATA seq={frame.seq_num} duplicado/no esperado → solo ACK")
                self.duplicates += 1
                self.acks_sent += 1
                return {'action': 'send_ack_only', 'ack_seq': frame.seq_num}

        elif frame.type == "ACK":
            # Emisor: validar ACK
            if self.waiting_for_ack and frame.ack_num == self.next_seq_to_send:
                print(f"[SW1-{self.machine_id}] ACK seq={frame.ack_num} recibido → listo para siguiente DATA")
                self.waiting_for_ack = False
                self.timeout_event_scheduled = False
                self.next_seq_to_send = 1 - self.next_seq_to_send
                self.acks_received += 1
                return {'action': 'continue_sending'}
            else:
                print(f"[SW1-{self.machine_id}] ACK seq={frame.ack_num} inesperado o duplicado → ignorar")
                return {'action': 'no_action'}

        return {'action': 'no_action'}

    def handle_frame_corruption(self, frame: Frame) -> dict:
        """Frame corrupto detectado por DataLinkLayer."""
        print(f"[SW1-{self.machine_id}] Frame corrupto recibido → ignorar")
        return {'action': 'no_action'}

    def handle_timeout(self, simulator) -> dict:
        """Maneja evento de timeout"""
        if self.waiting_for_ack and self.last_frame_sent:
            print(f"[SW1-{self.machine_id}] TIMEOUT → retransmitir DATA seq={self.last_frame_sent.seq_num}")
            self.timeout_event_scheduled = False
            self._schedule_timeout(simulator)
            return {'action': 'send_frame', 'frame': self.last_frame_sent, 'destination': self.last_destination}

        print(f"[SW1-{self.machine_id}] TIMEOUT ignorado (ACK ya recibido)")
        return {'action': 'no_action'}

    def _schedule_timeout(self, simulator):
        """Programa un evento de timeout para el emisor"""
        if not self.timeout_event_scheduled:
            timeout_event = Event(
                EventType.TIMEOUT,
                simulator.get_current_time() + self.timeout_duration,
                self.machine_id
            )
            simulator.schedule_event(timeout_event)
            self.timeout_event_scheduled = True
            print(f"[SW1-{self.machine_id}] Timeout programado en {self.timeout_duration}s")


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