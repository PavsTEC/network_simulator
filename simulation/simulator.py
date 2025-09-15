from simulation.event_scheduler import EventScheduler
from simulation.machine import Machine
from models.events import Event, EventType


class Simulator:
    def __init__(self):
        self.event_scheduler = EventScheduler()  # Programador de eventos
        self._machines = {}  # Máquinas registradas
        self._current_time = 0.0  # Tiempo actual de simulación
        self._running = False  # Estado de ejecución
        self._paused = False  # Estado de pausa global


        print("[Simulator] Simulador inicializado")

    def add_machine(self, machine_id: str, protocol_class, error_rate: float = 0.1,
                   transmission_delay: float = 0.5) -> None:
        """Registra una nueva máquina con configuración individual."""
        machine = Machine(machine_id, protocol_class, error_rate, transmission_delay)
        self._machines[machine_id] = machine
        print(f"[Simulator] Máquina {machine_id} agregada (error_rate={error_rate}, transmission_delay={transmission_delay}s)")

    def schedule_event(self, event: Event) -> None:
        """Programa un evento en la cola."""
        if not self._paused:
            self.event_scheduler.schedule_event(event)

    def get_current_time(self) -> float:
        """Retorna el tiempo actual de simulación."""
        return self._current_time


    # Configuración individual por máquina
    def set_machine_error_rate(self, machine_id: str, error_rate: float) -> bool:
        """Configura la tasa de errores de una máquina específica."""
        if machine_id in self._machines:
            try:
                self._machines[machine_id].set_error_rate(error_rate)
                return True
            except Exception as e:
                print(f"[Simulator] Error configurando tasa de errores para {machine_id}: {e}")
                return False
        return False

    def set_machine_transmission_delay(self, machine_id: str, delay: float) -> bool:
        """Configura el retardo de transmisión de una máquina específica."""
        if machine_id in self._machines:
            try:
                self._machines[machine_id].set_transmission_delay(delay)
                return True
            except Exception as e:
                print(f"[Simulator] Error configurando retardo para {machine_id}: {e}")
                return False
        return False

    def get_machine_error_rate(self, machine_id: str) -> float:
        """Obtiene la tasa de errores de una máquina específica."""
        if machine_id in self._machines:
            return self._machines[machine_id].get_error_rate()
        return None

    def get_machine_transmission_delay(self, machine_id: str) -> float:
        """Obtiene el retardo de transmisión de una máquina específica."""
        if machine_id in self._machines:
            return self._machines[machine_id].get_transmission_delay()
        return None

    # Funcionalidad de pausa
    def pause_simulation(self) -> None:
        """Pausa toda la simulación."""
        self._paused = True
        print("[Simulator] Simulación pausada")

    def resume_simulation(self) -> None:
        """Reanuda la simulación."""
        self._paused = False
        print("[Simulator] Simulación reanudada")

    def pause_machine(self, machine_id: str) -> bool:
        """Pausa una máquina específica."""
        if machine_id in self._machines:
            self._machines[machine_id].pause()
            return True
        return False

    def resume_machine(self, machine_id: str) -> bool:
        """Reanuda una máquina específica."""
        if machine_id in self._machines:
            self._machines[machine_id].resume()
            return True
        return False

    def send_data(self, from_machine: str, to_machine: str, data: str) -> bool:
        """Envía datos específicos desde una máquina hacia otra."""
        if from_machine in self._machines and to_machine in self._machines:
            machine = self._machines[from_machine]
            machine.network_layer.add_data_to_send(data, to_machine)

            # Programa evento de envío
            event = Event(EventType.NETWORK_LAYER_READY,
                         self.get_current_time() + 0.1,
                         from_machine)
            self.schedule_event(event)
            return True
        return False

    def start_simulation(self) -> None:
        """Inicializa el simulador y las máquinas una sola vez."""
        print("\n" + "="*50)
        print("INICIANDO SIMULACIÓN")
        print("="*50)

        # Inicializa todas las máquinas una sola vez
        for machine in self._machines.values():
            machine.start(self)

        self._running = True
        print("[Simulator] Simulador iniciado y listo para procesar eventos")

    def run_simulation(self) -> None:
        """Procesa todos los eventos pendientes en la cola."""
        if not self._running:
            print("[Simulator] Simulación no iniciada. Llama start_simulation() primero.")
            return

        event_count = 0

        # Procesa todos los eventos pendientes
        while self._running and self.event_scheduler.has_events():
            if self._paused:
                print("[Simulator] Simulación pausada - esperando...")
                continue

            event = self.event_scheduler.get_next_event()
            if not event:
                break

            self._current_time = event.timestamp  # Avanza el tiempo de simulación
            event_count += 1

            print(f"\n--- Tiempo: {self._current_time:.2f}s | Evento #{event_count} ---")

            # Entrega evento a la máquina correspondiente
            if event.machine_id in self._machines:
                machine = self._machines[event.machine_id]
                machine.handle_event(event, self)
            else:
                print(f"[ERROR] Máquina {event.machine_id} no encontrada")

        if event_count > 0:
            print(f"[Simulator] Procesados {event_count} eventos")

    def stop_simulation(self) -> None:
        """Detiene la simulación."""
        self._running = False
        print("[Simulator] Simulación detenida por usuario")

    def _print_final_stats(self, event_count: int) -> None:
        # Imprime estadísticas finales de la simulación
        print(f"\n{'='*50}")
        print(f"SIMULACIÓN TERMINADA")
        print(f"{'='*50}")
        print(f"Tiempo total: {self._current_time:.2f}s")
        print(f"Eventos procesados: {event_count}")

        # Muestra estadísticas de cada máquina
        for machine_id, machine in self._machines.items():
            print(f"\n--- Estadísticas Máquina {machine_id} ---")
            stats = machine.get_stats()
            for key, value in stats.items():
                if isinstance(value, dict):
                    print(f"  {key}:")
                    for k, v in value.items():
                        print(f"    {k}: {v}")
                else:
                    print(f"  {key}: {value}")