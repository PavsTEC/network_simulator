import random
from models.frame import Frame
from models.events import Event, EventType


class PhysicalLayer:
    """Capa física individual por máquina con configuración propia."""

    def __init__(self, machine_id: str, error_rate: float = 0.1, transmission_delay: float = 0.5):
        """Inicializa la capa física con configuración individual."""
        # Validaciones
        if not (0.0 <= error_rate <= 1.0):
            raise ValueError("Error rate debe estar entre 0.0 y 1.0")
        if transmission_delay < 0:
            raise ValueError("Transmission delay debe ser no negativo")

        self.machine_id = machine_id
        self.error_rate = error_rate
        self.transmission_delay = transmission_delay
        self.is_paused = False  # Para funcionalidad de pausa
        self.frames_sent = 0
        self.frames_received = 0
        self.corrupted_frames = 0

    def send_frame(self, frame: Frame, destination_id: str, simulator) -> None:
        """Envía un frame con posible corrupción y retardo."""
        if self.is_paused:
            print(f"  [PhysicalLayer-{self.machine_id}] Transmisión pausada")
            return

        self.frames_sent += 1
        print(f"  [PhysicalLayer-{self.machine_id}] Enviando {frame} hacia {destination_id}")

        # Simula corrupción según tasa de errores
        is_corrupted = random.random() < self.error_rate
        if is_corrupted:
            print(f"  [PhysicalLayer-{self.machine_id}] ¡Frame corrupto durante transmisión!")

        # Notificar GUI si existe callback
        if hasattr(simulator, 'gui_callback') and simulator.gui_callback:
            # Marcar frame como corrupto para la animación visual
            if is_corrupted:
                frame.corrupted_by_physical = True

            simulator.gui_callback('packet_sent', {
                'frame': frame,
                'from': self.machine_id,
                'to': destination_id,
                'duration': self.transmission_delay
            })

        # Calcula tiempo de llegada con retardo
        arrival_time = simulator.get_current_time() + self.transmission_delay

        # Generar evento según si hay error o no (según especificación)
        if is_corrupted:
            # Frame con errores -> evento CKSUM_ERR
            event = Event(EventType.CKSUM_ERR, arrival_time, destination_id, frame)
        else:
            # Frame sin errores -> evento FRAME_ARRIVAL
            event = Event(EventType.FRAME_ARRIVAL, arrival_time, destination_id, frame)

        simulator.schedule_event(event)

    def set_error_rate(self, error_rate: float) -> None:
        """Configura la tasa de errores para esta máquina."""
        if not (0.0 <= error_rate <= 1.0):
            raise ValueError("Error rate debe estar entre 0.0 y 1.0")
        self.error_rate = error_rate
        print(f"  [PhysicalLayer-{self.machine_id}] Tasa de errores actualizada a: {error_rate}")

    def set_transmission_delay(self, delay: float) -> None:
        """Configura el retardo de transmisión para esta máquina."""
        if delay < 0:
            raise ValueError("Transmission delay debe ser no negativo")
        self.transmission_delay = delay
        print(f"  [PhysicalLayer-{self.machine_id}] Retardo actualizado a: {delay}s")

    def pause(self) -> None:
        """Pausa las transmisiones de esta máquina."""
        self.is_paused = True
        print(f"  [PhysicalLayer-{self.machine_id}] Transmisión pausada")

    def resume(self) -> None:
        """Reanuda las transmisiones de esta máquina."""
        self.is_paused = False
        print(f"  [PhysicalLayer-{self.machine_id}] Transmisión reanudada")

    def get_error_rate(self) -> float:
        """Obtiene la tasa de errores actual."""
        return self.error_rate

    def get_transmission_delay(self) -> float:
        """Obtiene el retardo de transmisión actual."""
        return self.transmission_delay

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