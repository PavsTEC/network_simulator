"""
Clase Machine - coordinador principal que maneja todas las capas de red.
"""

from layers.network_layer import NetworkLayer
from layers.physical_layer import PhysicalLayer
from models.events import Event, EventType


class Machine:
    """Máquina coordinadora que maneja todas las capas de red."""

    def __init__(self, machine_id: str, protocol_class, error_rate: float = 0.1,
                 transmission_delay: float = 0.5, **protocol_kwargs):
        """Inicializa la máquina con todas sus capas."""
        self.machine_id = machine_id

        # Crear capas independientes
        self.network_layer = NetworkLayer(machine_id)
        self.physical_layer = PhysicalLayer(machine_id, error_rate, transmission_delay)

        # Crear protocolo independiente con parámetros adicionales
        self.protocol = protocol_class(machine_id, **protocol_kwargs)

        # Control de timeout (necesario para start_protocol_timer en Simulator)
        self.active_timeout_id = 0

    def handle_event(self, event: Event, simulator) -> None:
        """Enruta eventos a la capa apropiada."""
        print(f"[Machine-{self.machine_id}] Procesando evento: {event.event_type}")

        if event.event_type == EventType.FRAME_ARRIVAL:
            # Frame válido (SIN ERRORES) -> Protocolo maneja directamente
            self.protocol.handle_frame_arrival(event.data)

        elif event.event_type == EventType.CKSUM_ERR:
            # Frame CON ERRORES -> Protocolo maneja corrupción
            self.protocol.handle_frame_corruption(event.data)

        elif event.event_type == EventType.NETWORK_LAYER_READY:
            # NetworkLayer tiene datos -> Protocolo decide qué hacer
            self.protocol.handle_network_layer_ready(self.network_layer)

        elif event.event_type == "DELIVER_PACKET":
            # Entregar paquete a NetworkLayer
            self.network_layer.deliver_packet(event.data, simulator)

        elif event.event_type == EventType.TIMEOUT:
            # Timeout del protocolo -> verificar si es válido
            timeout_id = event.data.get('timeout_id') if event.data else None

            # Verificar si el protocolo maneja timeouts individuales (Selective Repeat)
            if hasattr(self.protocol, 'handle_timeout_with_id') and hasattr(self.protocol, 'active_timers'):
                # Protocolo con timeouts individuales (Selective Repeat)
                if timeout_id in self.protocol.active_timers:
                    self.protocol.handle_timeout_with_id(timeout_id)
            else:
                # Protocolo con timeout único (PAR, Go-Back-N, etc.)
                if timeout_id == self.active_timeout_id:
                    self.protocol.handle_timeout()

        else:
            print(f"[Machine-{self.machine_id}] Evento no reconocido: {event.event_type}")

    def start(self, simulator) -> None:
        """Inicia la máquina."""
        print(f"[Machine-{self.machine_id}] Iniciando máquina...")

        # Si NetworkLayer tiene datos iniciales, programar evento
        if self.network_layer.has_data_ready():
            event = Event(EventType.NETWORK_LAYER_READY,
                         simulator.get_current_time() + 0.1,
                         self.machine_id)
            simulator.schedule_event(event)

    # Configuración individual por máquina
    def set_error_rate(self, error_rate: float) -> None:
        """Configura la tasa de errores de esta máquina."""
        self.physical_layer.set_error_rate(error_rate)

    def set_transmission_delay(self, delay: float) -> None:
        """Configura el retardo de transmisión de esta máquina."""
        self.physical_layer.set_transmission_delay(delay)

    def get_error_rate(self) -> float:
        """Obtiene la tasa de errores de esta máquina."""
        return self.physical_layer.get_error_rate()

    def get_transmission_delay(self) -> float:
        """Obtiene el retardo de transmisión de esta máquina."""
        return self.physical_layer.get_transmission_delay()

    # Funcionalidad de pausa por máquina
    def pause(self) -> None:
        """Pausa las transmisiones de esta máquina."""
        self.physical_layer.pause()

    def resume(self) -> None:
        """Reanuda las transmisiones de esta máquina."""
        self.physical_layer.resume()

    def get_stats(self) -> dict:
        """Obtiene estadísticas de la máquina."""
        return {
            'machine_id': self.machine_id,
            'frames_sent': getattr(self.physical_layer, 'frames_sent', 0),
            'frames_received': getattr(self.physical_layer, 'frames_received', 0),
            'error_rate': self.physical_layer.get_error_rate(),
            'transmission_delay': self.physical_layer.get_transmission_delay()
        }

