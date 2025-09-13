import random
import time
from models.frame import Frame
from models.events import Event, EventType

class PhysicalLayer:
    def __init__(self, error_rate: float = 0.1):
        self.error_rate = error_rate
        self.transmission_delay = 0.5  # segundos
        self.frames_sent = 0
        self.frames_received = 0
        self.corrupted_frames = 0
    
    def send_frame(self, frame: Frame, destination_id: str, simulator):
        """Envía un frame con posibilidad de corrupción"""
        self.frames_sent += 1
        print(f"  [PhysicalLayer] Enviando {frame} hacia {destination_id}")
        
        # Simular corrupción
        if random.random() < self.error_rate:
            frame.corrupt_frame()
            self.corrupted_frames += 1
            print(f"  [PhysicalLayer] ¡Frame corrupto durante transmisión!")
        
        # Programar llegada del frame
        arrival_time = simulator.current_time + self.transmission_delay
        
        if frame.is_valid():
            event = Event(EventType.FRAME_ARRIVAL, arrival_time, destination_id, frame)
        else:
            event = Event(EventType.CKSUM_ERR, arrival_time, destination_id, frame)
        
        simulator.schedule_event(event)
    
    def get_stats(self):
        return {
            'frames_sent': self.frames_sent,
            'frames_received': self.frames_received,
            'corrupted_frames': self.corrupted_frames,
            'error_rate': self.error_rate
        }