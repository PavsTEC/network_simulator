"""
Capa de enlace simplificada - coordinador de eventos.
Solo timing y comunicación entre capas.
"""

from models.frame import Frame
from models.events import Event, EventType


class DataLinkLayer:
    """Capa de enlace simplificada - coordinador de eventos."""

    def __init__(self, machine_id: str, protocol):
        """Inicializa la capa de enlace."""
        self.machine_id = machine_id
        self.protocol = protocol

    def send_frame(self, frame: Frame, destination_id: str, physical_layer, simulator) -> None:
        """Envía un frame directamente al physical layer (sin delay adicional)."""
        print(f"  [DataLink-{self.machine_id}] Enviando {frame} al physical layer")
        physical_layer.send_frame(frame, destination_id, simulator)


    def handle_frame_arrival(self, frame: Frame, simulator) -> None:
        """Coordina llegada de frame con protocolo."""
        print(f"  [DataLink-{self.machine_id}] Frame recibido: {frame}")

        # DataLinkLayer verifica checksum (como en la realidad)
        if self._verify_frame_checksum(frame):
            # Frame válido - protocolo decide qué hacer
            response = self.protocol.handle_frame_arrival(frame)

            # Ejecutar acción decidida por protocolo
            if response['action'] == 'deliver_packet':
                event = Event("DELIVER_PACKET", simulator.get_current_time(),
                             self.machine_id, response['packet'])
                simulator.schedule_event(event)
        else:
            # Frame corrupto - protocolo decide qué hacer
            response = self.protocol.handle_frame_corruption(frame)
            # En Utopia simplemente se ignora, otros protocolos pueden reenviar ACK/NAK

    def handle_network_layer_ready(self, network_layer, simulator) -> None:
        """Coordina datos de NetworkLayer con protocolo."""
        # Protocolo decide qué hacer
        response = self.protocol.handle_network_layer_ready(network_layer, self, simulator)

        # Ejecutar acción decidida por protocolo
        if response['action'] == 'send_frame':
            # Enviar
            print(f"  [DataLink-{self.machine_id}] Enviando {response['frame']}")

            event = Event("SEND_FRAME", simulator.get_current_time(),
                         self.machine_id, {
                             'frame': response['frame'],
                             'destination': response['destination']
                         })
            simulator.schedule_event(event)

            # El siguiente envío se controlará desde main, no aquí

    def _verify_frame_checksum(self, frame: Frame) -> bool:
        """Verifica si el frame tiene checksum válido (simulación realista)."""
        # En la realidad, DataLinkLayer verifica el FCS/checksum
        # PhysicalLayer solo marca si fue corrompido durante transmisión
        return not frame.corrupted_by_physical

