"""
Protocolo Go-Back-N (Bidireccional)
- Ventana de emisión configurable (N)
- Ventana de recepción = 1
- ACK acumulativos
- Retransmisión secuencial desde send_base cuando ocurre timeout
- Compatible con el simulador actual (sin modificar otros archivos)
"""

from models.frame import Frame
from models.events import Event, EventType
from protocols.protocol_interface import ProtocolInterface


class GoBackNProtocol(ProtocolInterface):
    """Implementación autocontenida de Go-Back-N."""

    def __init__(self, machine_id: str, window_size: int = 4, max_seq: int = 7):
        super().__init__(machine_id)
        self.machine_id = machine_id
        self.window_size = window_size
        self.max_seq = max_seq  # número máximo de secuencia (mod N+1)

        # Estado emisor
        self.send_base = 0
        self.next_seq_to_send = 0
        self.buffer = {}  # seq_num -> Frame
        self.last_destination = None

        # Estado receptor
        self.frame_expected = 0

        # Control de timeout
        self.timeout_duration = 5.0
        self.timeout_event_scheduled = False

        # Métricas
        self.sent_data = 0
        self.received_data = 0
        self.acks_sent = 0
        self.acks_received = 0
        self.retransmissions = 0

    def _in_window(self, seq):
        """Verifica si un número de secuencia está dentro de la ventana."""
        if self.send_base <= self.next_seq_to_send:
            return self.send_base <= seq < self.send_base + self.window_size
        else:
            return seq >= self.send_base or seq < (self.send_base + self.window_size) % (self.max_seq + 1)

    def _ack_in_range(self, ack):
        """Determina si un ACK es válido dentro de la ventana actual."""
        if self.send_base <= ack < self.next_seq_to_send:
            return True
        if self.next_seq_to_send < self.send_base:
            return ack >= self.send_base or ack < self.next_seq_to_send
        return False

    def handle_network_layer_ready(self, network_layer, data_link_layer, simulator) -> dict:
        """Cuando la capa de red tiene datos listos para enviar."""
        if self._in_window(self.next_seq_to_send):
            packet, destination = network_layer.get_packet()
            if packet and destination:
                frame = Frame("DATA", self.next_seq_to_send, 0, packet)
                print(f"[GBN-{self.machine_id}] Enviando DATA seq={self.next_seq_to_send} → {destination}")

                self.buffer[self.next_seq_to_send] = frame
                self.last_destination = destination
                self.sent_data += 1

                # Si es el primer frame pendiente, inicia timeout
                if self.send_base == self.next_seq_to_send and not self.timeout_event_scheduled:
                    self._schedule_timeout(simulator)

                # Avanzar número de secuencia circularmente
                self.next_seq_to_send = (self.next_seq_to_send + 1) % (self.max_seq + 1)

                return {'action': 'send_frame', 'frame': frame, 'destination': destination}
        else:
            print(f"[GBN-{self.machine_id}] Ventana llena → no se puede enviar nuevo DATA")

        return {'action': 'no_action'}

    def handle_frame_arrival(self, frame: Frame) -> dict:
        """Procesa llegada de un frame DATA o ACK."""
        if frame.type == "DATA":
            # Receptor: acepta solo el frame esperado
            if frame.seq_num == self.frame_expected:
                print(f"[GBN-{self.machine_id}] DATA seq={frame.seq_num} correcto → entregar y ACK")
                self.received_data += 1
                self.acks_sent += 1
                self.frame_expected = (self.frame_expected + 1) % (self.max_seq + 1)
                return {'action': 'deliver_packet_and_send_ack', 'packet': frame.packet, 'ack_seq': frame.seq_num}
            else:
                print(f"[GBN-{self.machine_id}] DATA seq={frame.seq_num} fuera de orden → ACK último válido")
                self.acks_sent += 1
                return {'action': 'send_ack_only', 'ack_seq': (self.frame_expected - 1) % (self.max_seq + 1)}

        elif frame.type == "ACK":
            ack = frame.ack_num
            if self._ack_in_range(ack):
                print(f"[GBN-{self.machine_id}] ACK {ack} válido → avanzar base")
                self.acks_received += 1
                old_base = self.send_base
                self.send_base = (ack + 1) % (self.max_seq + 1)

                # Limpiar frames confirmados
                seq = old_base
                while seq != self.send_base:
                    self.buffer.pop(seq, None)
                    seq = (seq + 1) % (self.max_seq + 1)

                # Control de timeout
                if self.send_base == self.next_seq_to_send:
                    print(f"[GBN-{self.machine_id}] Todos los ACK recibidos → detener timer")
                    self.timeout_event_scheduled = False
                else:
                    print(f"[GBN-{self.machine_id}] Aún quedan frames pendientes → reiniciar timer")
                    self.timeout_event_scheduled = False
                    self._schedule_timeout(simulator)

                return {'action': 'continue_sending'}
            else:
                print(f"[GBN-{self.machine_id}] ACK {ack} duplicado o fuera de rango → ignorar")
                return {'action': 'no_action'}

        return {'action': 'no_action'}

    def handle_frame_corruption(self, frame: Frame) -> dict:
        print(f"[GBN-{self.machine_id}] Frame corrupto → ignorar (esperando timeout)")
        return {'action': 'no_action'}


    def handle_timeout(self, simulator) -> dict:
        """Retransmite todos los frames pendientes desde send_base."""
        if self.send_base == self.next_seq_to_send or not self.buffer:
            print(f"[GBN-{self.machine_id}] No hay frames pendientes.")
            self.timeout_event_scheduled = False
            return {'action': 'no_action'}

        print(f"[GBN-{self.machine_id}] TIMEOUT → retransmitiendo desde base {self.send_base}")
        seq = self.send_base
        frame = self.buffer[seq]
        print(f"   ↻ Reenviando DATA seq={frame.seq_num}")
        self.retransmissions += 1

        # Reprogramar timeout
        self.timeout_event_scheduled = False
        self._schedule_timeout(simulator)

        return {'action': 'send_frame', 'frame': frame, 'destination': self.last_destination}


    def _schedule_timeout(self, simulator):
        """Programa un evento de timeout."""
        if not self.timeout_event_scheduled:
            timeout_event = Event(
                EventType.TIMEOUT,
                simulator.get_current_time() + self.timeout_duration,
                self.machine_id
            )
            simulator.schedule_event(timeout_event)
            self.timeout_event_scheduled = True
            print(f"[GBN-{self.machine_id}] Timeout programado en {self.timeout_duration}s")

    def get_stats(self) -> dict:
        stats = super().get_stats()
        stats.update({
            'send_base': self.send_base,
            'next_seq_to_send': self.next_seq_to_send,
            'frame_expected': self.frame_expected,
            'sent_data': self.sent_data,
            'received_data': self.received_data,
            'acks_sent': self.acks_sent,
            'acks_received': self.acks_received,
            'retransmissions': self.retransmissions,
            'window_size': self.window_size,
        })
        return stats

    def get_protocol_name(self) -> str:
        return "Go-Back-N"