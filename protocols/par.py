"""
Protocolo PAR (Positive Acknowledgment with Retransmission)
- Comunicación unidireccional: A envía, B recibe
- Control de flujo con ACK/NAK
- Timeout y reenvío automático
- Números de secuencia alternantes (0,1)
"""

from models.frame import Frame
from models.events import Event, EventType
from protocols.protocol_interface import ProtocolInterface


class PARProtocol(ProtocolInterface):
    """Protocolo PAR con ACK y timeout."""

    def __init__(self, machine_id: str):
        """Inicializa el protocolo PAR."""
        super().__init__(machine_id)
        
        # Estado del protocolo
        self.seq_num = 0  # Número de secuencia actual (0 o 1)
        self.expected_seq = 0  # Secuencia esperada en receptor

        # Control de reenvío
        self.waiting_for_ack = False  # ¿Esperando ACK?
        self.last_packet = None  # Último packet (para reenvío con frame fresco)
        self.last_destination = None  # Destino del último frame

    def handle_network_layer_ready(self, network_layer) -> None:
        """Maneja cuando Network Layer tiene datos listos para enviar."""

        # Solo procesar si no estamos esperando ACK
        if self.waiting_for_ack:
            return

        # Obtener packet de Network Layer
        packet, destination = self.from_network_layer(network_layer)
        if packet and destination:
            # Guardar para posible reenvío
            self.last_packet = packet
            self.last_destination = destination
            self.waiting_for_ack = True

            # Crear frame DATA con número de secuencia
            frame = Frame("DATA", self.seq_num, 0, packet)

            self._log(f"[PAR-{self.machine_id}] Enviando frame seq={self.seq_num}")

            # Enviar frame y activar timeout
            self.to_physical_layer(frame, destination)
            self.start_timer()

    def handle_frame_arrival(self, frame) -> None:
        """Maneja la llegada de un frame válido."""

        if frame.type == "DATA":
            # Frame de datos recibido
            if frame.seq_num == self.expected_seq:
                # Secuencia correcta - entregar paquete y enviar ACK
                self._log(f"[PAR-{self.machine_id}] Frame seq={frame.seq_num} correcto, enviando ACK")

                # Entregar paquete a Network Layer
                self.to_network_layer(frame.packet)

                # Enviar ACK
                ack_frame = Frame("ACK", 0, frame.seq_num)
                self.to_physical_layer(ack_frame, "A")  # Hardcoded por ahora

                # Actualizar secuencia esperada
                self.expected_seq = 1 - self.expected_seq  # Alternar entre 0 y 1

            else:
                # Secuencia duplicada o incorrecta - reenviar ACK anterior
                self._log(f"[PAR-{self.machine_id}] Frame seq={frame.seq_num} duplicado, reenviando ACK anterior")

                # Reenviar ACK del frame anterior
                ack_frame = Frame("ACK", 0, 1 - self.expected_seq)
                self.to_physical_layer(ack_frame, "A")

        elif frame.type == "ACK":
            # ACK recibido
            if self.waiting_for_ack and frame.ack_num == self.seq_num:
                # ACK correcto - avanzar secuencia
                self._log(f"[PAR-{self.machine_id}] ACK seq={frame.ack_num} recibido correctamente")

                # Detener timeout
                self.stop_timer()

                # Actualizar estado
                self.seq_num = 1 - self.seq_num  # Alternar entre 0 y 1
                self.waiting_for_ack = False
                self.last_packet = None
                self.last_destination = None

                # Intentar enviar siguiente paquete inmediatamente
                self.enable_network_layer()

            else:
                # ACK incorrecto o no esperado
                self._log(f"[PAR-{self.machine_id}] ACK seq={frame.ack_num} incorrecto o no esperado")

    def handle_frame_corruption(self, frame) -> None:
        """Maneja un frame corrupto."""
        self._log(f"[PAR-{self.machine_id}] Frame corrupto recibido")

        # En PAR, frame corrupto se trata como no recibido
        # Si esperábamos un DATA, no enviamos nada (timeout se encargará)
        # Si esperábamos un ACK, timeout se encargará del reenvío

    def handle_timeout(self) -> None:
        """Maneja eventos de timeout."""
        if self.waiting_for_ack and self.last_packet:
            self._log(f"[PAR-{self.machine_id}]  TIMEOUT! Retransmitiendo frame seq={self.seq_num}")

            # Crear frame fresco
            fresh_frame = Frame("DATA", self.seq_num, 0, self.last_packet)

            # Reenviar frame con timeout
            self.to_physical_layer(fresh_frame, self.last_destination)
            self.start_timer()

    def get_stats(self) -> dict:
        """Retorna estadísticas del protocolo."""
        stats = super().get_stats()
        stats.update({
            'current_seq': self.seq_num,
            'expected_seq': self.expected_seq,
            'waiting_for_ack': self.waiting_for_ack
        })
        return stats

    def get_protocol_name(self) -> str:
        """Obtiene el nombre del protocolo."""
        return "PAR"