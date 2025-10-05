"""
Protocolo Selective Repeat (Repetición Selectiva)
Implementación base de Manfred, adaptada a la nueva arquitectura.

- Comunicación bidireccional
- Ventana deslizante de tamaño N para emisión y recepción
- Reenvío selectivo de frames perdidos/corruptos
- ACKs individuales para cada frame
- Timeouts independientes por frame (característica ESENCIAL de SR)
"""

from models.frame import Frame
from protocols.protocol_interface import ProtocolInterface


class SelectiveRepeatProtocol(ProtocolInterface):
    """Protocolo Selective Repeat con ventanas deslizantes bidireccionales."""

    def __init__(self, machine_id: str, window_size: int = 4):
        super().__init__(machine_id)

        # Configuración de ventanas
        self.window_size = window_size
        self.max_seq_num = 2 * window_size  # Espacio de secuencia debe ser >= 2*N

        # Ventana de envío
        self.send_base = 0  # Primer frame no confirmado
        self.next_seq_num = 0  # Próximo número de secuencia a usar
        self.send_window = {}  # {seq_num: {'frame': Frame, 'destination': str, 'timer_id': int}}

        # Ventana de recepción
        self.rcv_base = 0  # Número de secuencia esperado más bajo
        self.receive_buffer = {}  # {seq_num: Frame} - frames recibidos fuera de orden

        # Control de timeouts individuales (ESENCIAL para Selective Repeat)
        self.next_timer_id = 0
        self.active_timers = {}  # {timer_id: seq_num}

        # Estadísticas
        self.frames_sent = 0
        self.frames_received = 0
        self.acks_sent = 0
        self.acks_received = 0
        self.retransmissions = 0
        self.out_of_order_frames = 0

    def handle_network_layer_ready(self, network_layer) -> None:
        """Maneja cuando Network Layer tiene datos listos para enviar."""

        # Enviar múltiples frames mientras haya espacio en ventana y datos disponibles
        while not self._send_window_full():
            packet, destination = self.from_network_layer(network_layer)
            if not packet or not destination:
                break  # No hay más datos disponibles

            # Crear frame DATA con número de secuencia
            frame = Frame("DATA", self.next_seq_num, 0, packet)

            # Obtener timer_id único para este frame
            timer_id = self._get_next_timer_id()

            # Agregar a ventana de envío
            self.send_window[self.next_seq_num] = {
                'frame': frame,
                'destination': destination,
                'timer_id': timer_id
            }

            # Programar timeout individual para ESTE frame específico
            self._schedule_timeout(self.next_seq_num, timer_id)

            self._log(f"[SR-{self.machine_id}] Enviando frame seq={self.next_seq_num} con timer #{timer_id} (ventana: {self.send_base}-{(self.send_base + self.window_size - 1) % self.max_seq_num})")

            # Enviar frame
            self.to_physical_layer(frame, destination)

            # Avanzar número de secuencia
            self.next_seq_num = (self.next_seq_num + 1) % self.max_seq_num
            self.frames_sent += 1

    def handle_frame_arrival(self, frame) -> None:
        """Maneja la llegada de un frame válido."""

        if frame.type == "DATA":
            self._handle_data_frame(frame)
        elif frame.type == "ACK":
            self._handle_ack_frame(frame)

    def _handle_data_frame(self, frame) -> None:
        """Maneja la llegada de un frame DATA."""
        seq_num = frame.seq_num
        self.frames_received += 1

        self._log(f"[SR-{self.machine_id}] Frame DATA seq={seq_num} recibido (ventana rcv: {self.rcv_base}-{(self.rcv_base + self.window_size - 1) % self.max_seq_num})")

        # Siempre enviar ACK individual para el frame recibido (ESENCIAL en SR)
        ack_frame = Frame("ACK", 0, seq_num)
        self.to_physical_layer(ack_frame, "A" if self.machine_id == "B" else "B")
        self.acks_sent += 1

        # Verificar si está dentro de la ventana de recepción
        if self._in_receive_window(seq_num):
            if seq_num == self.rcv_base:
                # Frame esperado - entregar inmediatamente
                self._log(f"[SR-{self.machine_id}] Frame seq={seq_num} es el esperado -> entregar")
                self.to_network_layer(frame.packet)
                self.rcv_base = (self.rcv_base + 1) % self.max_seq_num

                # Verificar frames buffereados consecutivos
                while self.rcv_base in self.receive_buffer:
                    buffered_frame = self.receive_buffer.pop(self.rcv_base)
                    self._log(f"[SR-{self.machine_id}] Entregando frame buffereado seq={self.rcv_base}")
                    self.to_network_layer(buffered_frame.packet)
                    self.rcv_base = (self.rcv_base + 1) % self.max_seq_num

                self._log(f"[SR-{self.machine_id}] Nueva base rcv: {self.rcv_base}")
            else:
                # Frame fuera de orden - bufferear si no está ya buffereado
                if seq_num not in self.receive_buffer:
                    self.receive_buffer[seq_num] = frame
                    self.out_of_order_frames += 1
                    self._log(f"[SR-{self.machine_id}] Frame seq={seq_num} buffereado (fuera de orden)")
                else:
                    self._log(f"[SR-{self.machine_id}] Frame seq={seq_num} ya estaba buffereado")
        else:
            # Frame fuera de ventana (pero ACK ya fue enviado)
            if self._already_received(seq_num):
                self._log(f"[SR-{self.machine_id}] Frame seq={seq_num} ya recibido anteriormente (ACK reenviado)")
            else:
                self._log(f"[SR-{self.machine_id}] Frame seq={seq_num} fuera de ventana")

    def _handle_ack_frame(self, frame) -> None:
        """Maneja la llegada de un frame ACK."""
        ack_seq = frame.ack_num

        self._log(f"[SR-{self.machine_id}] ACK seq={ack_seq} recibido")

        # Verificar si el ACK corresponde a un frame en la ventana de envío
        if ack_seq in self.send_window:
            # Cancelar timeout individual de ESTE frame
            frame_info = self.send_window.pop(ack_seq)
            self._cancel_timeout(frame_info['timer_id'])

            self.acks_received += 1
            self._log(f"[SR-{self.machine_id}] ACK seq={ack_seq} confirmado, timer #{frame_info['timer_id']} cancelado")

            # Si es el frame base, avanzar ventana
            if ack_seq == self.send_base:
                old_base = self.send_base
                # Avanzar base hasta el próximo frame no confirmado
                while self.send_base not in self.send_window and self.send_base != self.next_seq_num:
                    self.send_base = (self.send_base + 1) % self.max_seq_num

                self._log(f"[SR-{self.machine_id}] Ventana de envío avanzada: {old_base} -> {self.send_base}")

            # Intentar enviar más paquetes si hay espacio en ventana
            self.enable_network_layer()
        else:
            self._log(f"[SR-{self.machine_id}] ACK seq={ack_seq} fuera de ventana o duplicado")

    def handle_frame_corruption(self, frame) -> None:
        """Maneja un frame corrupto."""
        self._log(f"[SR-{self.machine_id}] Frame corrupto recibido - ignorando")
        # En Selective Repeat, frames corruptos se ignoran
        # El timeout individual se encargará del reenvío si era un DATA

    def handle_timeout_with_id(self, timer_id: int) -> None:
        """
        Maneja timeout individual para un frame específico.
        ESTE es el método que diferencia SR de otros protocolos.
        """
        if timer_id in self.active_timers:
            seq_num = self.active_timers.pop(timer_id)

            if seq_num in self.send_window:
                frame_info = self.send_window[seq_num]

                self._log(f"[SR-{self.machine_id}] TIMEOUT timer #{timer_id} - Reenviando SOLO frame seq={seq_num}")
                self.retransmissions += 1

                # Reprogramar timeout individual para ESTE frame
                new_timer_id = self._get_next_timer_id()
                frame_info['timer_id'] = new_timer_id
                self._schedule_timeout(seq_num, new_timer_id)

                # Reenviar SOLO este frame (no todos como Go-Back-N)
                self.to_physical_layer(frame_info['frame'], frame_info['destination'])
            else:
                self._log(f"[SR-{self.machine_id}] TIMEOUT timer #{timer_id} - frame ya fue confirmado")
        else:
            self._log(f"[SR-{self.machine_id}] TIMEOUT timer #{timer_id} - ya fue cancelado")

    def _send_window_full(self) -> bool:
        """Verifica si la ventana de envío está llena."""
        return len(self.send_window) >= self.window_size

    def _in_receive_window(self, seq_num: int) -> bool:
        """Verifica si un número de secuencia está dentro de la ventana de recepción."""
        window_end = (self.rcv_base + self.window_size - 1) % self.max_seq_num

        if self.rcv_base <= window_end:
            return self.rcv_base <= seq_num <= window_end
        else:  # Ventana wrapeada
            return seq_num >= self.rcv_base or seq_num <= window_end

    def _already_received(self, seq_num: int) -> bool:
        """Verifica si un frame ya fue recibido anteriormente."""
        if self.rcv_base == 0:
            return seq_num > (self.max_seq_num - self.window_size)
        else:
            return seq_num < self.rcv_base and seq_num >= (self.rcv_base - self.window_size) % self.max_seq_num

    def _get_next_timer_id(self) -> int:
        """Obtiene el próximo ID de timer único."""
        timer_id = self.next_timer_id
        self.next_timer_id += 1
        return timer_id

    def _schedule_timeout(self, seq_num: int, timer_id: int) -> None:
        """Programa un timeout individual para un frame específico."""
        self.active_timers[timer_id] = seq_num
        # Usar start_timer con timer_id específico
        self.start_timer(timer_id=timer_id)

    def _cancel_timeout(self, timer_id: int) -> None:
        """Cancela un timeout individual (marcándolo como inactivo)."""
        if timer_id in self.active_timers:
            del self.active_timers[timer_id]

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
            'rcv_base': self.rcv_base,
            'send_window_size': len(self.send_window),
            'receive_buffer_size': len(self.receive_buffer),
            'frames_sent': self.frames_sent,
            'frames_received': self.frames_received,
            'retransmissions': self.retransmissions,
            'out_of_order_frames': self.out_of_order_frames,
            'acks_sent': self.acks_sent,
            'acks_received': self.acks_received,
            'active_timers': len(self.active_timers)
        })
        return stats

    def get_protocol_name(self) -> str:
        """Obtiene el nombre del protocolo."""
        return "Selective Repeat"
