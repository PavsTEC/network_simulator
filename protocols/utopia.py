from protocols.base_protocol import BaseProtocol
from models.events import Event, EventType
from models.frame import Frame
import time

class UtopiaProtocol(BaseProtocol):
    def __init__(self, machine_id: str):
        super().__init__(machine_id)
        self.is_sender = machine_id == "A"
        
    def start_protocol(self, simulator):
        """Inicia el protocolo Utopia"""
        print(f"\n[Utopia-{self.machine_id}] Iniciando protocolo...")
        
        if self.is_sender:
            # Máquina A: Programar el primer envío
            event = Event(EventType.NETWORK_LAYER_READY, 
                         simulator.current_time + 0.1, 
                         self.machine_id)
            simulator.schedule_event(event)
    
    def handle_event(self, event: Event, simulator):
        """Maneja eventos según el protocolo Utopia"""
        print(f"\n[Utopia-{self.machine_id}] Procesando: {event}")
        
        if self.is_sender:
            # Máquina A (Emisor)
            if event.event_type == EventType.NETWORK_LAYER_READY:
                self._send_next_frame(simulator)
        else:
            # Máquina B (Receptor)
            if event.event_type == EventType.FRAME_ARRIVAL:
                self._receive_frame(event.data, simulator)
    
    def _send_next_frame(self, simulator):
        """Envía el siguiente frame (solo máquina A)"""
        if self.network_layer.has_data_ready():
            packet = self.network_layer.get_packet()
            frame = Frame("DATA", 0, 0, packet)
            
            self.physical_layer.send_frame(frame, "B", simulator)
            self.frames_sent += 1
            
            # Programar siguiente envío
            next_send_time = simulator.current_time + 1.0
            event = Event(EventType.NETWORK_LAYER_READY, next_send_time, self.machine_id)
            simulator.schedule_event(event)
    
    def _receive_frame(self, frame: Frame, simulator):
        """Recibe un frame (solo máquina B)"""
        print(f"  [Utopia-{self.machine_id}] Frame recibido: {frame}")
        
        if frame.is_valid() and frame.packet:
            self.network_layer.deliver_packet(frame.packet)
            self.frames_received += 1
        else:
            print(f"  [Utopia-{self.machine_id}] Frame inválido o sin datos")