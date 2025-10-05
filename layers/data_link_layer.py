"""
Capa de enlace simplificada - coordinador de eventos.
Solo timing y comunicación entre capas.
"""

from models.frame import Frame
from models.events import Event, EventType


class DataLinkLayer:
    """Capa de enlace simplificada - coordinador de eventos."""

    def __init__(self, machine_id: str, protocol, transmission_delay: float = 1.0):
        """Inicializa la capa de enlace."""
        self.machine_id = machine_id
        self.protocol = protocol
        self.active_timeout_id = 0  # ID del timeout activo (incrementa con cada nuevo timeout)
        # Timeout debe ser al menos 3x el round-trip time (ida + vuelta + margen)
        self.timeout_duration = max(3.0, transmission_delay * 3)

    def send_frame(self, frame: Frame, destination_id: str, physical_layer, simulator) -> None:
        """Envía un frame directamente al physical layer (sin delay adicional)."""
        print(f"  [DataLink-{self.machine_id}] Enviando {frame} al physical layer")
        physical_layer.send_frame(frame, destination_id, simulator)


    def handle_frame_arrival(self, frame: Frame, simulator) -> None:
        """Coordina llegada de frame SIN ERRORES con protocolo."""
        print(f"  [DataLink-{self.machine_id}] Frame recibido: {frame}")

        # Frame válido (sin errores) - protocolo decide qué hacer
        response = self.protocol.handle_frame_arrival(frame)
        self._execute_protocol_response(response, simulator)

    def handle_frame_corruption(self, frame: Frame, simulator) -> None:
        """Coordina llegada de frame CON ERRORES con protocolo."""
        print(f"  [DataLink-{self.machine_id}] Frame recibido: {frame} [CORRUPTED]")

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
            # Enviar frame sin timeout
            print(f"  [DataLink-{self.machine_id}] Enviando {response['frame']}")
            event = Event("SEND_FRAME", simulator.get_current_time(),
                         self.machine_id, {
                             'frame': response['frame'],
                             'destination': response['destination']
                         })
            simulator.schedule_event(event)

        elif action == 'send_frame_with_timeout':
            # Enviar frame CON timeout
            print(f"  [DataLink-{self.machine_id}] Enviando {response['frame']}")
            event = Event("SEND_FRAME", simulator.get_current_time(),
                         self.machine_id, {
                             'frame': response['frame'],
                             'destination': response['destination']
                         })
            simulator.schedule_event(event)

            # Incrementar ID y programar timeout
            self.active_timeout_id += 1
            current_timeout_id = self.active_timeout_id

            timeout_event = Event(EventType.TIMEOUT,
                                simulator.get_current_time() + self.timeout_duration,
                                self.machine_id,
                                {'timeout_id': current_timeout_id})
            simulator.schedule_event(timeout_event)
            print(f"  [DataLink-{self.machine_id}] Timeout #{current_timeout_id} programado para {self.timeout_duration}s")
            
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

            # 2. Enviar ACK inmediatamente (sin delay artificial)
            ack_frame = Frame("ACK", 0, response['ack_seq'])
            print(f"  [DataLink-{self.machine_id}] Enviando ACK seq={response['ack_seq']}")
            event = Event("SEND_FRAME", simulator.get_current_time(),
                         self.machine_id, {
                             'frame': ack_frame,
                             'destination': 'A'
                         })
            simulator.schedule_event(event)

            # 3. Si hay flag continue, programar envío inmediato
            if response.get('continue', False):
                event = Event(EventType.NETWORK_LAYER_READY,
                             simulator.get_current_time(),
                             self.machine_id)
                simulator.schedule_event(event)
            
        elif action == 'send_nak':
            # Enviar NAK inmediatamente (sin delay artificial)
            nak_frame = Frame("NAK", 0, response['nak_seq'])
            print(f"  [DataLink-{self.machine_id}] Enviando NAK seq={response['nak_seq']}")
            event = Event("SEND_FRAME", simulator.get_current_time(),
                         self.machine_id, {
                             'frame': nak_frame,
                             'destination': 'A'
                         })
            simulator.schedule_event(event)
            
        elif action == 'send_ack_only':
            # Enviar solo ACK inmediatamente (sin entregar paquete - para frames duplicados)
            ack_frame = Frame("ACK", 0, response['ack_seq'])
            print(f"  [DataLink-{self.machine_id}] Enviando ACK seq={response['ack_seq']} (frame duplicado)")
            event = Event("SEND_FRAME", simulator.get_current_time(),
                         self.machine_id, {
                             'frame': ack_frame,
                             'destination': 'A'
                         })
            simulator.schedule_event(event)
            
        elif action == 'continue_sending':
            # Continuar enviando inmediatamente - sin delay
            event = Event(EventType.NETWORK_LAYER_READY,
                         simulator.get_current_time(),
                         self.machine_id)
            simulator.schedule_event(event)

        elif action == 'stop_timeout_and_continue':
            # Detener timeout incrementando el ID (invalida timeouts viejos)
            self.active_timeout_id += 1
            print(f"  [DataLink-{self.machine_id}] Timeout cancelado (nuevo ID: #{self.active_timeout_id})")

            # Continuar enviando inmediatamente
            event = Event(EventType.NETWORK_LAYER_READY,
                         simulator.get_current_time(),
                         self.machine_id)
            simulator.schedule_event(event)
            
        elif action == 'retransmit':
            # El protocolo maneja el reenvío internamente
            pass

        elif action == 'send_multiple_frames':
            # Enviar múltiples frames (Go-Back-N retransmisión)
            for frame_data in response['frames']:
                print(f"  [DataLink-{self.machine_id}] Reenviando frame seq={frame_data['seq']}")
                event = Event("SEND_FRAME", simulator.get_current_time(),
                             self.machine_id, {
                                 'frame': frame_data['frame'],
                                 'destination': frame_data['destination']
                             })
                simulator.schedule_event(event)

                # Programar timeout solo para el primero (si use_timeout está presente)
                if frame_data.get('use_timeout', False):
                    self.active_timeout_id += 1
                    current_timeout_id = self.active_timeout_id

                    timeout_event = Event(EventType.TIMEOUT,
                                        simulator.get_current_time() + self.timeout_duration,
                                        self.machine_id,
                                        {'timeout_id': current_timeout_id})
                    simulator.schedule_event(timeout_event)
                    print(f"  [DataLink-{self.machine_id}] Timeout #{current_timeout_id} programado para {self.timeout_duration}s")

        elif action == 'deliver_multiple_packets_and_ack':
            # Entregar múltiples paquetes (Selective Repeat) y enviar ACK
            for packet in response['packets']:
                event = Event("DELIVER_PACKET", simulator.get_current_time(),
                             self.machine_id, packet)
                simulator.schedule_event(event)

            # Enviar ACK
            ack_frame = Frame("ACK", 0, response['ack_seq'])
            print(f"  [DataLink-{self.machine_id}] Enviando ACK seq={response['ack_seq']}")
            event = Event("SEND_FRAME", simulator.get_current_time(),
                         self.machine_id, {
                             'frame': ack_frame,
                             'destination': 'A'
                         })
            simulator.schedule_event(event)

            # Si hay flag continue, programar envío inmediato
            if response.get('continue', False):
                event = Event(EventType.NETWORK_LAYER_READY,
                             simulator.get_current_time(),
                             self.machine_id)
                simulator.schedule_event(event)

        # 'no_action' no requiere procesamiento

