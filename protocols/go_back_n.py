"""
Protocolo Go-Back-N (GBN)
- Comunicación bidireccional
- Ventana de emisión de tamaño N
- Ventana de recepción de tamaño 1
- Retransmisión en bloque desde send_base al ocurrir timeout
- ACKs acumulativos
"""

from models.frame import Frame
from models.events import Event, EventType
from protocols.protocol_interface import ProtocolInterface


class GoBackNProtocol(ProtocolInterface):
    """Protocolo Go-Back-N compatible con la arquitectura modular del simulador."""

    def __init__(self, machine_id: str, window_size: int = 4):
        super().__init__(machine_id)
        self.machine_id = machine_id

        # --- Parámetros de ventana ---
        self.window_size = window_size
        self.max_seq_num = 2 * window_size  # Espacio circular (al menos 2N)

        # --- Estado del emisor ---
        self.send_base = 0            # Primer frame no confirmado
        self.next_seq_num = 0         # Próximo número de secuencia a enviar
        self.send_buffer = {}         # {seq_num: {'frame': Frame, 'destination': str}}

        # --- Estado del receptor ---
        self.expected_seq_num = 0     # Solo 1 frame válido a la vez (ventana de recepción = 1)

        # --- Control de timeout (global para la base) ---
        self.timeout_duration = 4.0
        self.timeout_event_scheduled = False

        # --- Métricas ---
        self.sent_frames = 0
        self.received_frames = 0
        self.acks_sent = 0
        self.acks_received = 0
        self.retransmissions = 0

    def handle_network_layer_ready(self, network_layer, data_link_layer, simulator) -> dict:
        """Cuando hay datos listos para enviar desde la capa de red."""
        # Verificar espacio disponible en ventana
        if self._window_full():
            print(f"[GBN-{self.machine_id}] Ventana llena, no se puede enviar nuevo frame")
            return {'action': 'no_action'}

        # Tomar packet y destino de la capa de red
        if network_layer.has_data_ready():
            packet, destination = network_layer.get_packet()
            if packet and destination:
                frame = Frame("DATA", self.next_seq_num, (self.expected_seq_num - 1) % self.max_seq_num, packet)
                print(f"[GBN-{self.machine_id}] Enviando DATA seq={self.next_seq_num} → {destination}")

                # Guardar en buffer
                self.send_buffer[self.next_seq_num] = {
                    'frame': frame,
                    'destination': destination
                }

                self.sent_frames += 1
                # Si es el primer frame de la ventana, programar timeout global
                if not self.timeout_event_scheduled:
                    self._schedule_timeout(simulator)

                # Avanzar secuencia circularmente
                self.next_seq_num = (self.next_seq_num + 1) % self.max_seq_num

                return {'action': 'send_frame', 'frame': frame, 'destination': destination}

        return {'action': 'no_action'}

    def handle_frame_arrival(self, frame: Frame) -> dict:
        """Procesa llegada de un frame (DATA o ACK)."""
        if frame.type == "DATA":
            seq = frame.seq_num
            if seq == self.expected_seq_num:
                print(f"[GBN-{self.machine_id}] DATA seq={seq} correcto → entregar y enviar ACK")
                self.received_frames += 1
                self.acks_sent += 1
                self.expected_seq_num = (self.expected_seq_num + 1) % self.max_seq_num
                return {
                    'action': 'deliver_packet_and_send_ack',
                    'packet': frame.packet,
                    'ack_seq': seq
                }
            else:
                print(f"[GBN-{self.machine_id}] DATA seq={seq} fuera de orden → reenviar último ACK {(self.expected_seq_num - 1) % self.max_seq_num}")
                self.acks_sent += 1
                return {
                    'action': 'send_ack_only',
                    'ack_seq': (self.expected_seq_num - 1) % self.max_seq_num
                }

        elif frame.type == "ACK":
            ack = frame.ack_num
            # ACK acumulativo
            if self._in_window(self.send_base, ack):
                print(f"[GBN-{self.machine_id}] ACK {ack} acumulativo → avanzar base")
                self.acks_received += 1
                old_base = self.send_base
                self.send_base = (ack + 1) % self.max_seq_num

                # Eliminar frames confirmados del buffer
                seq = old_base
                while seq != self.send_base:
                    self.send_buffer.pop(seq, None)
                    seq = (seq + 1) % self.max_seq_num

                # Reprogramar o cancelar timeout
                if self.send_base == self.next_seq_num:
                    self.timeout_event_scheduled = False
                else:
                    self._schedule_timeout(simulator)

                return {'action': 'continue_sending'}
            else:
                print(f"[GBN-{self.machine_id}] ACK {ack} duplicado o fuera de ventana → ignorar")
                return {'action': 'no_action'}

        return {'action': 'no_action'}

    def handle_frame_corruption(self, frame: Frame) -> dict:
        """Frame corrupto detectado por la capa física."""
        print(f"[GBN-{self.machine_id}] Frame corrupto → ignorar (timeout manejará retransmisión)")
        return {'action': 'no_action'}

    def handle_timeout(self, simulator) -> dict:
        """Retransmite todos los frames pendientes desde send_base."""
        if not self.send_buffer:
            print(f"[GBN-{self.machine_id}] TIMEOUT sin frames pendientes → ignorar")
            self.timeout_event_scheduled = False
            return {'action': 'no_action'}

        print(f"[GBN-{self.machine_id}] TIMEOUT → retransmitiendo todos los frames desde base {self.send_base}")
        actions = []
        seq = self.send_base
        while seq != self.next_seq_num:
            frame_info = self.send_buffer.get(seq)
            if frame_info:
                frame = frame_info['frame']
                destination = frame_info['destination']
                print(f"   ↻ Reenviando DATA seq={seq}")
                actions.append({'action': 'send_frame', 'frame': frame, 'destination': destination})
                self.retransmissions += 1
            seq = (seq + 1) % self.max_seq_num

        # Reprogramar timeout global
        self._schedule_timeout(simulator)
        return actions[0] if actions else {'action': 'no_action'}

    def _schedule_timeout(self, simulator):
        """Programa un timeout global para la ventana de envío."""
        timeout_event = Event(
            EventType.TIMEOUT,
            simulator.get_current_time() + self.timeout_duration,
            self.machine_id
        )
        simulator.schedule_event(timeout_event)
        self.timeout_event_scheduled = True
        print(f"[GBN-{self.machine_id}] Timeout programado en {self.timeout_duration}s")

    def _window_full(self) -> bool:
        """True si la ventana de envío está llena."""
        if self.send_base <= self.next_seq_num:
            return (self.next_seq_num - self.send_base) >= self.window_size
        else:
            return (self.next_seq_num + self.max_seq_num - self.send_base) >= self.window_size

    def _in_window(self, base: int, ack: int) -> bool:
        """Verifica si un ACK está dentro del rango de la ventana actual."""
        if base <= ack < (base + self.window_size) % self.max_seq_num:
            return True
        if (base + self.window_size) >= self.max_seq_num:
            return ack < ((base + self.window_size) % self.max_seq_num) or ack >= base
        return False

    def get_stats(self) -> dict:
        stats = super().get_stats()
        stats.update({
            'window_size': self.window_size,
            'send_base': self.send_base,
            'next_seq_num': self.next_seq_num,
            'expected_seq_num': self.expected_seq_num,
            'sent_frames': self.sent_frames,
            'received_frames': self.received_frames,
            'acks_sent': self.acks_sent,
            'acks_received': self.acks_received,
            'retransmissions': self.retransmissions,
        })
        return stats

    def get_protocol_name(self) -> str:
        return f"Go-Back-N"