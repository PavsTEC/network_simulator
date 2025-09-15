from protocols.base_protocol import BaseProtocol
from models.events import Event, EventType
from models.frame import Frame


class UtopiaProtocol(BaseProtocol):
    def __init__(self, machine_id: str):
        super().__init__(machine_id)
        self.is_sender = machine_id == "A"  # A es emisor, B es receptor

    def start_protocol(self, simulator) -> None:
        print(f"[{self.machine_id}] Iniciando protocolo Utopia...")

        if self.is_sender:
            # Programa el primer evento de envío
            event = Event(EventType.NETWORK_LAYER_READY,
                         simulator.get_current_time() + 0.1,
                         self.machine_id)
            simulator.schedule_event(event)

    def handle_event(self, event: Event, simulator) -> None:
        print(f"[{self.machine_id}] Procesando: {event}")

        if self.is_sender:
            if event.event_type == EventType.NETWORK_LAYER_READY:
                self._send_next_frame(simulator)
        else:
            if event.event_type == EventType.FRAME_ARRIVAL:
                self._receive_frame(event.data, simulator)
            elif event.event_type == EventType.CKSUM_ERR:
                print(f"[{self.machine_id}] Frame corrupto recibido")

    def _send_next_frame(self, simulator) -> None:
        # Envía un frame si hay datos disponibles
        if self.network_layer.has_data_ready():
            packet = self.network_layer.get_packet()
            frame = Frame("DATA", 0, 0, packet)

            self.physical_layer.send_frame(frame, "B", simulator)
            self.frames_sent += 1

            # Programa el siguiente envío
            next_send_time = simulator.get_current_time() + 1.0
            event = Event(EventType.NETWORK_LAYER_READY, next_send_time, self.machine_id)
            simulator.schedule_event(event)

    def _receive_frame(self, frame: Frame, simulator) -> None:
        print(f"[{self.machine_id}] Frame recibido: {frame}")

        # Entrega frame válido a la capa de red
        if frame.is_valid() and frame.packet:
            self.network_layer.deliver_packet(frame.packet)
            self.frames_received += 1