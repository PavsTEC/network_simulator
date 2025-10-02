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
            self._execute_protocol_response(response, simulator)
        else:
            # Frame corrupto - protocolo decide qué hacer
            response = self.protocol.handle_frame_corruption(frame)
            self._execute_protocol_response(response, simulator)

    def handle_network_layer_ready(self, network_layer, simulator) -> None:
        """Coordina datos de NetworkLayer con protocolo."""
        # Protocolo decide qué hacer
        response = self.protocol.handle_network_layer_ready(network_layer, self, simulator)
        self._execute_protocol_response(response, simulator)

    def _execute_protocol_response(self, response: dict, simulator) -> None:
        """Ejecuta la acción decidida por el protocolo."""
        action = response.get('action', 'no_action')
        
        if action == 'send_frame':
            # Enviar frame
            print(f"  [DataLink-{self.machine_id}] Enviando {response['frame']}")
            event = Event("SEND_FRAME", simulator.get_current_time(),
                         self.machine_id, {
                             'frame': response['frame'],
                             'destination': response['destination']
                         })
            simulator.schedule_event(event)
            
        elif action == 'deliver_packet':
            # Entregar paquete a Network Layer
            event = Event("DELIVER_PACKET", simulator.get_current_time(),
                         self.machine_id, response['packet'])
            simulator.schedule_event(event)
            
        elif action == 'deliver_packet_and_send_ack':
            # Entregar paquete Y enviar ACK
            # 1. Entregar paquete
            event = Event("DELIVER_PACKET", simulator.get_current_time(),
                         self.machine_id, response['packet'])
            simulator.schedule_event(event)
            
            # 2. Enviar ACK
            ack_frame = Frame("ACK", 0, response['ack_seq'])
            print(f"  [DataLink-{self.machine_id}] Enviando ACK seq={response['ack_seq']}")
            event = Event("SEND_FRAME", simulator.get_current_time() + 0.1,
                         self.machine_id, {
                             'frame': ack_frame,
                             'destination': 'A'  # PAR: B siempre responde a A
                         })
            simulator.schedule_event(event)
            
        elif action == 'send_nak':
            # Enviar NAK
            nak_frame = Frame("NAK", 0, response['nak_seq'])
            print(f"  [DataLink-{self.machine_id}] Enviando NAK seq={response['nak_seq']}")
            event = Event("SEND_FRAME", simulator.get_current_time() + 0.1,
                         self.machine_id, {
                             'frame': nak_frame,
                             'destination': 'A'  # PAR: B siempre responde a A
                         })
            simulator.schedule_event(event)
            
        elif action == 'send_ack_only':
            # Enviar solo ACK (sin entregar paquete - para frames duplicados)
            ack_frame = Frame("ACK", 0, response['ack_seq'])
            print(f"  [DataLink-{self.machine_id}] Enviando ACK seq={response['ack_seq']} (frame duplicado)")
            event = Event("SEND_FRAME", simulator.get_current_time() + 0.1,
                         self.machine_id, {
                             'frame': ack_frame,
                             'destination': 'A'
                         })
            simulator.schedule_event(event)
            
        elif action == 'continue_sending':
            # Continuar enviando - programar siguiente dato si hay
            event = Event(EventType.NETWORK_LAYER_READY,
                         simulator.get_current_time() + 0.1,
                         self.machine_id)
            simulator.schedule_event(event)
            
        elif action == 'retransmit':
            # El protocolo maneja el reenvío internamente
            pass
            
        # 'no_action' no requiere procesamiento

    def _verify_frame_checksum(self, frame: Frame) -> bool:
        """Verifica si el frame tiene checksum válido (simulación realista)."""
        # En la realidad, DataLinkLayer verifica el FCS/checksum
        # PhysicalLayer solo marca si fue corrompido durante transmisión
        return not frame.corrupted_by_physical

