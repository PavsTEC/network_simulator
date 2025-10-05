"""
Protocolo Go-Back-N (GBN)
Implementación base de Manfred, adaptada a la nueva arquitectura.

- Comunicación bidireccional
- Ventana de emisión de tamaño N
- Ventana de recepción de tamaño 1
- Retransmisión en bloque desde send_base al ocurrir timeout
- ACKs acumulativos
"""

from models.frame import Frame
from protocols.protocol_interface import ProtocolInterface


class GoBackNProtocol(ProtocolInterface):
    """Protocolo Go-Back-N con ventana deslizante."""

    def __init__(self, machine_id: str, window_size: int = 4):
        super().__init__(machine_id)

        # Parámetros de ventana
        self.window_size = window_size
        self.max_seq_num = 2 * window_size  # Espacio circular (al menos 2N)

        # Estado del emisor
        self.send_base = 0            # Primer frame no confirmado
        self.next_seq_num = 0         # Próximo número de secuencia a enviar
        self.send_buffer = {}         # {seq_num: {'frame': Frame, 'destination': str}}

        # Estado del receptor
        self.expected_seq_num = 0     # Solo 1 frame válido a la vez (ventana de recepción = 1)

        # Métricas
        self.sent_frames = 0
        self.received_frames = 0
        self.acks_sent = 0
        self.acks_received = 0
        self.retransmissions = 0

    def handle_network_layer_ready(self, network_layer) -> None:
        """Maneja cuando Network Layer tiene datos listos para enviar."""
        # Enviar múltiples frames mientras haya espacio en ventana y datos disponibles
        while not self._window_full():
            packet, destination = self.from_network_layer(network_layer)
            if not packet or not destination:
                break  # No hay más datos disponibles

            # Crear frame con piggybacked ACK (último frame recibido correctamente)
            # Si no hemos recibido ningún frame, usar 0 (sin ACK piggybacked)
            if self.expected_seq_num == 0:
                piggybacked_ack = 0
            else:
                piggybacked_ack = (self.expected_seq_num - 1) % self.max_seq_num

            frame = Frame("DATA", self.next_seq_num, piggybacked_ack, packet)
            self._log(f"[GBN-{self.machine_id}] Enviando DATA seq={self.next_seq_num} -> {destination}")

            # Guardar en buffer
            self.send_buffer[self.next_seq_num] = {
                'frame': frame,
                'destination': destination
            }

            self.sent_frames += 1

            # Si es el primer frame de la ventana, programar timeout global
            if self.send_base == self.next_seq_num:
                self.start_timer()

            # Enviar frame
            self.to_physical_layer(frame, destination)

            # Avanzar secuencia circularmente
            self.next_seq_num = (self.next_seq_num + 1) % self.max_seq_num

    def handle_frame_arrival(self, frame: Frame) -> None:
        """Maneja la llegada de un frame válido."""
        if frame.type == "DATA":
            seq = frame.seq_num
            if seq == self.expected_seq_num:
                self._log(f"[GBN-{self.machine_id}] DATA seq={seq} correcto -> entregar y enviar ACK")
                self.received_frames += 1
                self.acks_sent += 1

                # Entregar paquete
                self.to_network_layer(frame.packet)

                # Avanzar secuencia esperada
                self.expected_seq_num = (self.expected_seq_num + 1) % self.max_seq_num

                # Enviar ACK
                ack_frame = Frame("ACK", 0, seq)
                self.to_physical_layer(ack_frame, "A" if self.machine_id == "B" else "B")

            else:
                self._log(f"[GBN-{self.machine_id}] DATA seq={seq} fuera de orden -> reenviar último ACK {(self.expected_seq_num - 1) % self.max_seq_num}")
                self.acks_sent += 1

                # Reenviar último ACK
                ack_frame = Frame("ACK", 0, (self.expected_seq_num - 1) % self.max_seq_num)
                self.to_physical_layer(ack_frame, "A" if self.machine_id == "B" else "B")

        elif frame.type == "ACK":
            ack = frame.ack_num
            # ACK acumulativo
            if self._in_window(self.send_base, ack):
                self._log(f"[GBN-{self.machine_id}] ACK {ack} acumulativo -> avanzar base")
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
                    # Ventana vacía, detener timeout
                    self.stop_timer()
                else:
                    # Aún hay frames pendientes, reiniciar timeout
                    self.stop_timer()
                    self.start_timer()

                # Intentar enviar más paquetes si hay espacio en ventana
                self.enable_network_layer()
            else:
                self._log(f"[GBN-{self.machine_id}] ACK {ack} duplicado o fuera de ventana -> ignorar")

    def handle_frame_corruption(self, frame: Frame) -> None:
        """Maneja un frame corrupto."""
        self._log(f"[GBN-{self.machine_id}] Frame corrupto -> ignorar (timeout manejará retransmisión)")

    def handle_timeout(self) -> None:
        """Retransmite todos los frames pendientes desde send_base."""
        if not self.send_buffer:
            self._log(f"[GBN-{self.machine_id}] TIMEOUT sin frames pendientes -> ignorar")
            return

        self._log(f"[GBN-{self.machine_id}] TIMEOUT -> retransmitiendo todos los frames desde base {self.send_base}")
        seq = self.send_base
        while seq != self.next_seq_num:
            frame_info = self.send_buffer.get(seq)
            if frame_info:
                frame = frame_info['frame']
                destination = frame_info['destination']
                print(f"   -> Reenviando DATA seq={seq}")
                self.to_physical_layer(frame, destination)
                self.retransmissions += 1
            seq = (seq + 1) % self.max_seq_num

        # Reprogramar timeout global
        self.start_timer()

    def _window_full(self) -> bool:
        """Verifica si la ventana de envío está llena."""
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

    def is_bidirectional(self) -> bool:
        """Indica que este protocolo es bidireccional."""
        return True

    def get_stats(self) -> dict:
        """Retorna estadísticas del protocolo."""
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
        """Obtiene el nombre del protocolo."""
        return "Go-Back-N"
