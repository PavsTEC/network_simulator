from simulation.event_scheduler import EventScheduler
from simulation.machine import Machine
from models.events import Event


class Simulator:
    def __init__(self):
        self.event_scheduler = EventScheduler()  # Programador de eventos
        self._machines = {}  # Máquinas registradas
        self._current_time = 0.0  # Tiempo actual de simulación
        self._running = False  # Estado de ejecución
        self.max_simulation_time = 10.0  # Tiempo máximo de simulación

        print("[Simulator] Simulador inicializado")

    def add_machine(self, machine_id: str, protocol) -> None:
        # Registra una nueva máquina con su protocolo
        machine = Machine(machine_id, protocol)
        self._machines[machine_id] = machine
        print(f"[Simulator] Máquina {machine_id} agregada")

    def schedule_event(self, event: Event) -> None:
        # Programa un evento en la cola
        self.event_scheduler.schedule_event(event)

    def get_current_time(self) -> float:
        # Retorna el tiempo actual de simulación
        return self._current_time

    def set_error_rate(self, machine_id: str, error_rate: float) -> bool:
        # Configura tasa de errores para una máquina específica
        if machine_id in self._machines:
            return self._machines[machine_id].set_error_rate(error_rate)
        return False

    def set_global_error_rate(self, error_rate: float) -> int:
        # Configura tasa de errores para todas las máquinas
        success_count = 0
        for machine in self._machines.values():
            if machine.set_error_rate(error_rate):
                success_count += 1
        print(f"[Simulator] Tasa de errores {error_rate} aplicada a {success_count} máquinas")
        return success_count

    def get_error_rate(self, machine_id: str) -> float:
        # Obtiene la tasa de errores de una máquina
        if machine_id in self._machines:
            return self._machines[machine_id].get_error_rate()
        return None

    def run_simulation(self) -> None:
        # Ejecuta el bucle principal de simulación
        print("\n" + "="*50)
        print("INICIANDO SIMULACIÓN")
        print("="*50)

        # Inicializa todos los protocolos
        for machine in self._machines.values():
            machine.start(self)

        self._running = True
        event_count = 0

        # Bucle principal: procesa eventos hasta cumplir condiciones de parada
        while (self._running and
               self.event_scheduler.has_events() and
               self._current_time < self.max_simulation_time):

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

        self._print_final_stats(event_count)

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