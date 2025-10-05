"""
Protocolo Go-Back-N (Protocol 5)
- Ventana deslizante de tamaño MAX_SEQ
- Permite múltiples frames pendientes
- Retransmite TODOS los frames desde el primero no confirmado en caso de timeout
- Piggybacking de ACKs
- ACKs acumulativos (ACK n confirma todos hasta n)
"""

from models.frame import Frame
from models.events import Event, EventType
from protocols.protocol_interface import ProtocolInterface


class GoBackNProtocol(ProtocolInterface):
    """Protocolo Go-Back-N con ventana deslizante."""

    MAX_SEQ = 7  # Tamaño de ventana - 1

    def __init__(self, machine_id: str):
        """Inicializa el protocolo Go-Back-N."""
        super().__init__(machine_id)

        # Estado del emisor
        self.next_frame_to_send = 0  # Siguiente frame a enviar
        self.ack_expected = 0  # Frame más antiguo sin confirmar
        self.nbuffered = 0  # Número de frames en ventana

        # Estado del receptor
        self.frame_expected = 0  # Próximo frame esperado

        # Buffers para frames pendientes
        self.buffer = {}  # {seq_num: (packet, destination)}

    def handle_network_layer_ready(self, network_layer, data_link_layer, simulator) -> dict:
        """Maneja cuando Network Layer tiene datos listos para enviar."""

        # Verificar si hay espacio en la ventana
        if self.nbuffered >= self.MAX_SEQ:
            print(f"[GoBackN-{self.machine_id}] Ventana llena ({self.nbuffered}/{self.MAX_SEQ})")
            return {'action': 'no_action'}

        if network_layer.has_data_ready():
            packet, destination = network_layer.get_packet()
            if packet and destination:
                # Guardar en buffer
                self.buffer[self.next_frame_to_send] = (packet, destination)
                self.nbuffered += 1

                # Crear frame con piggybacked ACK
                piggybacked_ack = (self.frame_expected + self.MAX_SEQ) % (self.MAX_SEQ + 1)
                frame = Frame("DATA", self.next_frame_to_send, piggybacked_ack, packet)

                print(f"[GoBackN-{self.machine_id}] Enviando frame seq={self.next_frame_to_send}, ventana={self.nbuffered}/{self.MAX_SEQ}")

                # Avanzar ventana
                seq_to_send = self.next_frame_to_send
                self.next_frame_to_send = self._inc(self.next_frame_to_send)

                # Usar timeout solo si es el primero de la ventana
                if self.nbuffered == 1:
                    return {
                        'action': 'send_frame_with_timeout',
                        'frame': frame,
                        'destination': destination
                    }
                else:
                    return {
                        'action': 'send_frame',
                        'frame': frame,
                        'destination': destination
                    }

        return {'action': 'no_action'}

    def handle_frame_arrival(self, frame) -> dict:
        """Maneja la llegada de un frame válido."""

        if frame.type == "DATA":
            print(f"[GoBackN-{self.machine_id}] Frame DATA recibido seq={frame.seq_num}, ack={frame.ack_num}")

            # Manejar stream de entrada
            packet_to_deliver = None
            if frame.seq_num == self.frame_expected:
                # Frame en orden - entregar
                packet_to_deliver = frame.packet
                self.frame_expected = self._inc(self.frame_expected)
                print(f"[GoBackN-{self.machine_id}] Frame en orden, avanzando frame_expected a {self.frame_expected}")

            # Manejar ACKs acumulativos (stream de salida)
            ack_received = False
            while self._between(self.ack_expected, frame.ack_num, self.next_frame_to_send):
                # ACK recibido - liberar buffer
                if self.ack_expected in self.buffer:
                    del self.buffer[self.ack_expected]
                self.nbuffered -= 1
                print(f"[GoBackN-{self.machine_id}] ACK recibido para seq={self.ack_expected}, ventana={self.nbuffered}/{self.MAX_SEQ}")
                self.ack_expected = self._inc(self.ack_expected)
                ack_received = True

            # Determinar acción basada en ACKs y paquetes
            if packet_to_deliver:
                # Entregar paquete y enviar ACK, luego continuar si hubo ACKs
                action = {
                    'action': 'deliver_packet_and_send_ack',
                    'packet': packet_to_deliver,
                    'ack_seq': frame.seq_num
                }
                # Si se recibieron ACKs y hay espacio, indicar continuar
                if ack_received and self.nbuffered < self.MAX_SEQ:
                    action['continue'] = True
                return action
            else:
                # Frame fuera de orden - enviar ACK del último correcto
                return {
                    'action': 'send_ack_only',
                    'ack_seq': (self.frame_expected + self.MAX_SEQ) % (self.MAX_SEQ + 1)
                }

        elif frame.type == "ACK":
            # ACK puro recibido - procesar ACKs acumulativos
            ack_received = False
            while self._between(self.ack_expected, frame.ack_num, self.next_frame_to_send):
                if self.ack_expected in self.buffer:
                    del self.buffer[self.ack_expected]
                self.nbuffered -= 1
                print(f"[GoBackN-{self.machine_id}] ACK puro recibido para seq={self.ack_expected}")
                self.ack_expected = self._inc(self.ack_expected)
                ack_received = True

            # Si se recibió ACK y hay espacio en ventana, continuar enviando
            if ack_received:
                if self.nbuffered == 0:
                    return {'action': 'stop_timeout_and_continue'}
                else:
                    return {'action': 'continue_sending'}

        return {'action': 'no_action'}

    def handle_frame_corruption(self, frame) -> dict:
        """Maneja un frame corrupto."""
        print(f"[GoBackN-{self.machine_id}] Frame corrupto recibido - ignorando")
        # El timeout manejará el reenvío
        return {'action': 'no_action'}

    def handle_timeout(self, simulator) -> dict:
        """Maneja evento de timeout - retransmite TODOS los frames pendientes."""
        if self.nbuffered > 0:
            print(f"[GoBackN-{self.machine_id}] TIMEOUT - Reenviando TODOS los frames desde seq={self.ack_expected}")

            # Resetear next_frame_to_send al primero no confirmado
            self.next_frame_to_send = self.ack_expected

            # Retransmitir todos los frames en la ventana
            frames_to_send = []
            temp_seq = self.ack_expected

            for i in range(self.nbuffered):
                if temp_seq in self.buffer:
                    packet, destination = self.buffer[temp_seq]
                    piggybacked_ack = (self.frame_expected + self.MAX_SEQ) % (self.MAX_SEQ + 1)
                    frame = Frame("DATA", temp_seq, piggybacked_ack, packet)

                    frames_to_send.append({
                        'frame': frame,
                        'destination': destination,
                        'seq': temp_seq,
                        'use_timeout': (i == 0)  # Solo el primero usa timeout
                    })

                    temp_seq = self._inc(temp_seq)

            # Avanzar next_frame_to_send
            self.next_frame_to_send = temp_seq

            if frames_to_send:
                return {
                    'action': 'send_multiple_frames',
                    'frames': frames_to_send
                }

        return {'action': 'no_action'}

    def _inc(self, k):
        """Incrementa k circularmente."""
        return (k + 1) % (self.MAX_SEQ + 1)

    def _between(self, a, b, c):
        """Retorna True si a <= b < c circularmente."""
        return ((a <= b) and (b < c)) or ((c < a) and (a <= b)) or ((b < c) and (c < a))

    def get_stats(self) -> dict:
        """Retorna estadísticas del protocolo."""
        stats = super().get_stats()
        stats.update({
            'next_frame_to_send': self.next_frame_to_send,
            'ack_expected': self.ack_expected,
            'frame_expected': self.frame_expected,
            'nbuffered': self.nbuffered,
            'max_window': self.MAX_SEQ
        })
        return stats

    def get_protocol_name(self) -> str:
        """Obtiene el nombre del protocolo."""
        return "Go-Back-N"

    def is_bidirectional(self) -> bool:
        """Indica si el protocolo es bidireccional."""
        return True
