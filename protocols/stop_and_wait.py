"""
Protocolo Stop and Wait
- Canal libre de errores (sin corrupción)
- Envía un frame y espera ACK (control de flujo)
- Sin timeout (no hay errores que manejar)
- Sin números de secuencia (no hay duplicados en canal sin errores)
"""

from models.frame import Frame
from protocols.protocol_interface import ProtocolInterface


class StopAndWaitProtocol(ProtocolInterface):
    """Protocolo Stop and Wait simple (canal sin errores)."""

    def __init__(self, machine_id: str):
        """Inicializa el protocolo Stop and Wait."""
        super().__init__(machine_id)

        # Estado del protocolo
        self.waiting_for_ack = False  # ¿Esperando ACK?

    def handle_network_layer_ready(self, network_layer) -> None:
        """Maneja cuando Network Layer tiene datos listos para enviar."""

        # Solo procesar si no estamos esperando ACK
        if self.waiting_for_ack:
            self._log(f"[StopWait-{self.machine_id}] Esperando ACK, no se pueden enviar más datos")
            return

        packet, destination = self.from_network_layer(network_layer)
        if packet and destination:
            self.waiting_for_ack = True

            # Crear frame DATA simple (sin seq num, canal sin errores)
            frame = Frame("DATA", 0, 0, packet)

            self._log(f"[StopWait-{self.machine_id}] Enviando frame")
            self.to_physical_layer(frame, destination)

    def handle_frame_arrival(self, frame) -> None:
        """Maneja la llegada de un frame válido."""

        if frame.type == "DATA":
            # Frame de datos recibido - entregar y enviar ACK
            self._log(f"[StopWait-{self.machine_id}] Frame recibido, enviando ACK")

            # Entregar paquete
            self.to_network_layer(frame.packet)

            # Enviar ACK
            ack_frame = Frame("ACK", 0, 0)
            self.to_physical_layer(ack_frame, "A")  # Hardcoded por ahora

        elif frame.type == "ACK":
            # ACK recibido - continuar enviando
            if self.waiting_for_ack:
                self._log(f"[StopWait-{self.machine_id}] ACK recibido")
                self.waiting_for_ack = False

                # Intentar enviar siguiente paquete inmediatamente
                self.enable_network_layer()
            else:
                self._log(f"[StopWait-{self.machine_id}] ACK no esperado")

    def handle_frame_corruption(self, frame) -> None:
        """Maneja un frame corrupto."""
        # Stop and Wait NO maneja errores (canal sin errores según especificación)
        # Este método no debería llamarse en este protocolo
        self._log(f"[StopWait-{self.machine_id}] Frame corrupto recibido - ERROR: canal debería ser sin errores")

    def get_stats(self) -> dict:
        """Retorna estadísticas del protocolo."""
        stats = super().get_stats()
        stats.update({
            'waiting_for_ack': self.waiting_for_ack
        })
        return stats

    def get_protocol_name(self) -> str:
        """Obtiene el nombre del protocolo."""
        return "Stop and Wait"