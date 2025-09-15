import random
from models.frame import Frame
from models.events import Event, EventType


class PhysicalLayer:
    def __init__(self, error_rate: float = 0.1, transmission_delay: float = 0.5):
        # Validaciones de parámetros
        if not (0.0 <= error_rate <= 1.0):
            raise ValueError("Error rate debe estar entre 0.0 y 1.0")
        if transmission_delay < 0:
            raise ValueError("Transmission delay debe ser no negativo")

        self.error_rate = error_rate  # Probabilidad de corrupción
        self.transmission_delay = transmission_delay  # Retardo de transmisión
        self.frames_sent = 0  # Contador de frames enviados
        self.frames_received = 0  # Contador de frames recibidos
        self.corrupted_frames = 0  # Contador de frames corruptos

    def send_frame(self, frame: Frame, destination_id: str, simulator) -> None:
        # Validaciones de entrada
        if not frame:
            raise ValueError("Frame no puede ser None")
        if not destination_id.strip():
            raise ValueError("Destination ID no puede estar vacío")

        self.frames_sent += 1
        print(f"  [PhysicalLayer] Enviando {frame} hacia {destination_id}")

        # Simula corrupción según tasa de errores
        if random.random() < self.error_rate:
            frame.corrupt_frame()
            self.corrupted_frames += 1
            print(f"  [PhysicalLayer] ¡Frame corrupto durante transmisión!")

        # Calcula tiempo de llegada con retardo
        arrival_time = simulator.get_current_time() + self.transmission_delay

        # Crea evento según estado del frame
        if frame.is_valid():
            event = Event(EventType.FRAME_ARRIVAL, arrival_time, destination_id, frame)
        else:
            event = Event(EventType.CKSUM_ERR, arrival_time, destination_id, frame)

        simulator.schedule_event(event)

    def set_error_rate(self, new_error_rate: float) -> None:
        # Actualiza la tasa de errores con validación
        if not (0.0 <= new_error_rate <= 1.0):
            raise ValueError("La tasa de errores debe estar entre 0.0 y 1.0")

        self.error_rate = new_error_rate
        print(f"  [PhysicalLayer] Tasa de errores actualizada a: {self.error_rate}")

    def get_error_rate(self) -> float:
        # Retorna la tasa de errores actual
        return self.error_rate

    def get_stats(self):
        # Calcula estadísticas de transmisión
        corruption_rate = (self.corrupted_frames / self.frames_sent * 100) if self.frames_sent > 0 else 0.0

        return {
            'frames_sent': self.frames_sent,
            'frames_received': self.frames_received,
            'corrupted_frames': self.corrupted_frames,
            'error_rate': self.error_rate,
            'transmission_delay': self.transmission_delay,
            'corruption_rate_observed': corruption_rate,
            'total_transmission_time': self.frames_sent * self.transmission_delay
        }