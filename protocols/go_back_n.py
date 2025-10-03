"""
Protocolo Go-Back-N - Bidireccional
- Ventana de emisión configurable (N)
- Ventana de recepción = 1
- Retransmisión en bloque desde send_base cuando ocurre timeout
"""

from models.frame import Frame
from protocols.protocol_interface import ProtocolInterface


class GoBackNProtocol(ProtocolInterface):
    def __init__(self, machine_id: str, window_size: int = 4, max_seq: int = 7):
        self.machine_id = machine_id
        self.window_size = window_size
        self.max_seq = max_seq

        # Estado emisor
        self.next_seq_num = 0
        self.send_base = 0
        self.buffer = {}  # seq_num -> packet

        # Estado receptor
        self.frame_expected = 0

        # Métricas
        self.sent_data = 0
        self.received_data = 0
        self.retransmissions = 0
        self.acks_received = 0

    def handle_network_layer_ready(self, network_layer, data_link_layer, simulator) -> dict:
        # Solo enviar si hay espacio en la ventana
        if (self.next_seq_num - self.send_base + self.max_seq + 1) % (self.max_seq + 1) < self.window_size:
            packet, destination = network_layer.get_packet()
            if packet and destination:
                frame = Frame("DATA", self.next_seq_num, (self.frame_expected - 1) % (self.max_seq + 1), packet)
                print(f"[GBN-{self.machine_id}] Enviando DATA seq={self.next_seq_num} → {destination}")
                self.buffer[self.next_seq_num] = frame
                self.sent_data += 1
                self.next_seq_num = (self.next_seq_num + 1) % (self.max_seq + 1)
                return {
                    'action': 'send_frame',
                    'frame': frame,
                    'destination': destination
                }
        return {'action': 'no_action'}

    def handle_frame_arrival(self, frame: Frame) -> dict:
        if frame.type == "DATA":
            # Receptor: acepta solo frame esperado
            if frame.seq_num == self.frame_expected:
                print(f"[GBN-{self.machine_id}] DATA seq={frame.seq_num} correcto → entregar y ACK")
                self.received_data += 1
                self.frame_expected = (self.frame_expected + 1) % (self.max_seq + 1)
                return {
                    'action': 'deliver_packet_and_send_ack',
                    'packet': frame.packet,
                    'ack_seq': frame.seq_num
                }
            else:
                # Frame fuera de orden → reenviar ACK del último válido
                print(f"[GBN-{self.machine_id}] DATA seq={frame.seq_num} fuera de orden → ACK último válido")
                return {
                    'action': 'send_ack_only',
                    'ack_seq': (self.frame_expected - 1) % (self.max_seq + 1)
                }

        elif frame.type == "ACK":
            # Emisor: avanza base si ACK acumulativo es válido
            if self.send_base <= frame.ack_num < self.next_seq_num:
                print(f"[GBN-{self.machine_id}] ACK acumulativo {frame.ack_num} → avanzar base")
                self.acks_received += 1
                self.send_base = (frame.ack_num + 1) % (self.max_seq + 1)
                return {'action': 'continue_sending'}
            else:
                print(f"[GBN-{self.machine_id}] ACK {frame.ack_num} duplicado o fuera de ventana")
                return {'action': 'no_action'}

        return {'action': 'no_action'}

    def handle_frame_corruption(self, frame: Frame) -> dict:
        print(f"[GBN-{self.machine_id}] Frame corrupto → ignorar")
        return {'action': 'no_action'}

    def handle_timeout(self, timer_id=None) -> dict:
        # Retransmitir todos los frames pendientes desde send_base
        print(f"[GBN-{self.machine_id}] TIMEOUT → retransmitir desde base {self.send_base}")
        actions = []
        seq = self.send_base
        while seq != self.next_seq_num:
            frame = self.buffer[seq]
            actions.append({
                'action': 'send_frame',
                'frame': frame,
                'destination': "B" if self.machine_id == "A" else "A"
            })
            self.retransmissions += 1
            seq = (seq + 1) % (self.max_seq + 1)
        # Devuelve solo el primero, pero podrías adaptarlo para devolver lista
        return actions[0] if actions else {'action': 'no_action'}

    def get_stats(self) -> dict:
        stats = super().get_stats()
        stats.update({
            'send_base': self.send_base,
            'next_seq_num': self.next_seq_num,
            'frame_expected': self.frame_expected,
            'sent_data': self.sent_data,
            'received_data': self.received_data,
            'acks_received': self.acks_received,
            'retransmissions': self.retransmissions,
        })
        return stats

    def get_protocol_name(self) -> str:
        return "Go-Back-N"