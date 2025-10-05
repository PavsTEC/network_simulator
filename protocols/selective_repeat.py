"""
Protocolo Selective Repeat (Protocol 6)
- Ventana deslizante bidireccional
- Acepta frames fuera de orden
- Retransmite SOLO el frame que dio timeout (no todos)
- Usa NAK para frames perdidos
- Buffer de recepción para reordenar
- Piggybacking de ACKs
"""

from models.frame import Frame
from models.events import Event, EventType
from protocols.protocol_interface import ProtocolInterface


class SelectiveRepeatProtocol(ProtocolInterface):
    """Protocolo Selective Repeat con retransmisión selectiva."""

    MAX_SEQ = 7  # Debe ser 2^n - 1
    NR_BUFS = (MAX_SEQ + 1) // 2  # Tamaño de ventana

    def __init__(self, machine_id: str):
        """Inicializa el protocolo Selective Repeat."""
        super().__init__(machine_id)

        # Estado del emisor
        self.next_frame_to_send = 0
        self.ack_expected = 0
        self.nbuffered = 0

        # Estado del receptor
        self.frame_expected = 0
        self.too_far = self.NR_BUFS  # Límite superior de ventana receptor

        # Buffers
        self.out_buf = {}  # {seq_num % NR_BUFS: (packet, destination)}
        self.in_buf = {}  # {seq_num % NR_BUFS: packet}
        self.arrived = {}  # {seq_num % NR_BUFS: bool}

        # Control NAK
        self.no_nak = True  # Solo un NAK por frame

        # Timeouts individuales por buffer (uno por cada frame en ventana)
        self.timeout_duration = 3.0
        self.active_timers = {}  # {buf_index: timeout_event_data}

        # Inicializar buffers de recepción
        for i in range(self.NR_BUFS):
            self.arrived[i] = False

    def handle_network_layer_ready(self, network_layer, data_link_layer, simulator) -> dict:
        """Maneja cuando Network Layer tiene datos listos para enviar."""

        # Verificar si hay espacio en la ventana
        if self.nbuffered >= self.NR_BUFS:
            print(f"[SelectiveRepeat-{self.machine_id}] Ventana llena ({self.nbuffered}/{self.NR_BUFS})")
            return {'action': 'no_action'}

        if network_layer.has_data_ready():
            packet, destination = network_layer.get_packet()
            if packet and destination:
                # Guardar en buffer de salida
                buf_index = self.next_frame_to_send % self.NR_BUFS
                self.out_buf[buf_index] = (packet, destination)
                self.nbuffered += 1

                # Crear frame con piggybacked ACK
                piggybacked_ack = (self.frame_expected + self.MAX_SEQ) % (self.MAX_SEQ + 1)
                frame = Frame("DATA", self.next_frame_to_send, piggybacked_ack, packet)

                # Programar timeout
                self._schedule_timeout(self.next_frame_to_send, simulator)

                print(f"[SelectiveRepeat-{self.machine_id}] Enviando frame seq={self.next_frame_to_send}, ventana={self.nbuffered}/{self.NR_BUFS}")

                # Avanzar ventana
                self.next_frame_to_send = self._inc(self.next_frame_to_send)

                return {
                    'action': 'send_frame',
                    'frame': frame,
                    'destination': destination
                }

        return {'action': 'no_action'}

    def handle_frame_arrival(self, frame) -> dict:
        """Maneja la llegada de un frame válido."""

        if frame.type == "DATA":
            print(f"[SelectiveRepeat-{self.machine_id}] Frame DATA recibido seq={frame.seq_num}, ack={frame.ack_num}")

            # Enviar NAK si frame no es el esperado (ANTES de procesar)
            if frame.seq_num != self.frame_expected and self.no_nak:
                print(f"[SelectiveRepeat-{self.machine_id}] Enviando NAK para seq={self.frame_expected}")
                self.no_nak = False
                # Aún así procesamos el frame si está en ventana
                result = {
                    'action': 'send_nak',
                    'nak_seq': self.frame_expected
                }
            else:
                result = None

            # Verificar si frame está en ventana de recepción
            if self._between(self.frame_expected, frame.seq_num, self.too_far):
                buf_index = frame.seq_num % self.NR_BUFS

                if not self.arrived[buf_index]:
                    # Frame nuevo dentro de ventana
                    self.arrived[buf_index] = True
                    self.in_buf[buf_index] = frame.packet

                    print(f"[SelectiveRepeat-{self.machine_id}] Frame seq={frame.seq_num} aceptado y buffereado")

                    # Intentar entregar frames en orden
                    packets_to_deliver = []
                    while self.arrived[self.frame_expected % self.NR_BUFS]:
                        buf_index = self.frame_expected % self.NR_BUFS
                        packets_to_deliver.append(self.in_buf[buf_index])
                        self.arrived[buf_index] = False

                        self.frame_expected = self._inc(self.frame_expected)
                        self.too_far = self._inc(self.too_far)
                        self.no_nak = True  # Resetear NAK cuando avanzamos

                    # Manejar ACKs acumulativos
                    ack_processed = self._process_ack(frame.ack_num)

                    if packets_to_deliver:
                        action = {
                            'action': 'deliver_multiple_packets_and_ack',
                            'packets': packets_to_deliver,
                            'ack_seq': frame.seq_num
                        }
                        # Si se procesaron ACKs y hay espacio, continuar
                        if ack_processed and self.nbuffered < self.NR_BUFS:
                            action['continue'] = True
                        return action
                    elif result:
                        # Ya enviamos NAK
                        return result
                    else:
                        return {
                            'action': 'send_ack_only',
                            'ack_seq': frame.seq_num
                        }
            else:
                # Frame fuera de ventana
                print(f"[SelectiveRepeat-{self.machine_id}] Frame seq={frame.seq_num} fuera de ventana")

            # Procesar ACKs
            ack_processed = self._process_ack(frame.ack_num)

            # Si ya determinamos enviar NAK, retornarlo
            if result:
                return result

            return {'action': 'send_ack_only', 'ack_seq': (self.frame_expected + self.MAX_SEQ) % (self.MAX_SEQ + 1)}

        elif frame.type == "ACK":
            # ACK puro recibido
            print(f"[SelectiveRepeat-{self.machine_id}] ACK puro recibido ack={frame.ack_num}")
            ack_processed = self._process_ack(frame.ack_num)
            # Si se liberó espacio, continuar enviando
            if ack_processed and self.nbuffered < self.NR_BUFS:
                return {'action': 'continue_sending'}
            return {'action': 'no_action'}

        elif frame.type == "NAK":
            # NAK recibido - reenviar frame específico
            nak_seq = (frame.ack_num + 1) % (self.MAX_SEQ + 1)

            if self._between(self.ack_expected, nak_seq, self.next_frame_to_send):
                buf_index = nak_seq % self.NR_BUFS
                if buf_index in self.out_buf:
                    packet, destination = self.out_buf[buf_index]
                    piggybacked_ack = (self.frame_expected + self.MAX_SEQ) % (self.MAX_SEQ + 1)
                    retrans_frame = Frame("DATA", nak_seq, piggybacked_ack, packet)

                    print(f"[SelectiveRepeat-{self.machine_id}] NAK recibido, reenviando frame seq={nak_seq}")

                    return {
                        'action': 'send_frame',
                        'frame': retrans_frame,
                        'destination': destination
                    }

        return {'action': 'no_action'}

    def handle_frame_corruption(self, frame) -> dict:
        """Maneja un frame corrupto."""
        print(f"[SelectiveRepeat-{self.machine_id}] Frame corrupto recibido")

        # Enviar NAK si no se ha enviado uno
        if self.no_nak:
            print(f"[SelectiveRepeat-{self.machine_id}] Enviando NAK por frame corrupto")
            return {
                'action': 'send_nak',
                'nak_seq': self.frame_expected
            }

        return {'action': 'no_action'}

    def handle_timeout(self, simulator) -> dict:
        """Maneja evento de timeout - retransmite SOLO el frame específico que dio timeout."""
        # Timeout podría venir sin datos si es de protocolos más simples
        # Para Selective Repeat, buscamos el frame más antiguo sin confirmar
        if self.nbuffered > 0:
            # Reenviar el frame más antiguo (ack_expected)
            oldest_seq = self.ack_expected
            buf_index = oldest_seq % self.NR_BUFS

            if buf_index in self.out_buf:
                packet, destination = self.out_buf[buf_index]
                piggybacked_ack = (self.frame_expected + self.MAX_SEQ) % (self.MAX_SEQ + 1)
                frame = Frame("DATA", oldest_seq, piggybacked_ack, packet)

                print(f"[SelectiveRepeat-{self.machine_id}] TIMEOUT - Reenviando frame seq={oldest_seq}")

                # Reprogramar timeout para este frame
                if buf_index in self.active_timers:
                    del self.active_timers[buf_index]
                self._schedule_timeout(oldest_seq, simulator)

                return {
                    'action': 'send_frame',
                    'frame': frame,
                    'destination': destination
                }

        return {'action': 'no_action'}

    def _process_ack(self, ack_num):
        """Procesa ACKs acumulativos. Retorna True si se liberó espacio."""
        ack_processed = False
        while self._between(self.ack_expected, ack_num, self.next_frame_to_send):
            buf_index = self.ack_expected % self.NR_BUFS
            if buf_index in self.out_buf:
                del self.out_buf[buf_index]
            self.nbuffered -= 1
            if buf_index in self.active_timers:
                del self.active_timers[buf_index]
            print(f"[SelectiveRepeat-{self.machine_id}] ACK procesado para seq={self.ack_expected}")
            self.ack_expected = self._inc(self.ack_expected)
            ack_processed = True
        return ack_processed

    def _inc(self, k):
        """Incrementa k circularmente."""
        return (k + 1) % (self.MAX_SEQ + 1)

    def _between(self, a, b, c):
        """Retorna True si a <= b < c circularmente."""
        return ((a <= b) and (b < c)) or ((c < a) and (a <= b)) or ((b < c) and (c < a))

    def _schedule_timeout(self, seq_num, simulator):
        """Programa un evento de timeout para un frame específico."""
        buf_index = seq_num % self.NR_BUFS
        if buf_index not in self.active_timers:
            timeout_event = Event(
                EventType.TIMEOUT,
                simulator.get_current_time() + self.timeout_duration,
                self.machine_id,
                {'seq_num': seq_num, 'buf_index': buf_index}
            )
            simulator.schedule_event(timeout_event)
            self.active_timers[buf_index] = seq_num

    def get_stats(self) -> dict:
        """Retorna estadísticas del protocolo."""
        stats = super().get_stats()
        stats.update({
            'next_frame_to_send': self.next_frame_to_send,
            'ack_expected': self.ack_expected,
            'frame_expected': self.frame_expected,
            'too_far': self.too_far,
            'nbuffered': self.nbuffered,
            'max_window': self.NR_BUFS,
            'timeout_duration': self.timeout_duration
        })
        return stats

    def get_protocol_name(self) -> str:
        """Obtiene el nombre del protocolo."""
        return "Selective Repeat"

    def is_bidirectional(self) -> bool:
        """Indica si el protocolo es bidireccional."""
        return True
