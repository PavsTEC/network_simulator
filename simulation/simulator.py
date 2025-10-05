from simulation.event_scheduler import EventScheduler
from simulation.machine import Machine
from models.events import Event, EventType


class Simulator:
    def __init__(self, gui_callback=None, window_size=4):
        self.event_scheduler = EventScheduler()  # Programador de eventos
        self._machines = {}  # Máquinas registradas
        self._current_time = 0.0  # Tiempo actual de simulación
        self._running = False  # Estado de ejecución
        self._paused = False  # Estado de pausa global
        self.gui_callback = gui_callback  # Callback para actualizar GUI
        self.window_size = window_size  # Tamaño de ventana para protocolos GBN y SR


        print("[Simulator] Simulador inicializado")

    def add_machine(self, machine_id: str, protocol_class, error_rate: float = 0.1,
                   transmission_delay: float = 0.5) -> None:
        """Registra una nueva máquina con configuración individual."""
        # Detectar si el protocolo necesita window_size
        protocol_name = protocol_class.__name__
        if protocol_name in ['GoBackNProtocol', 'SelectiveRepeatProtocol']:
            machine = Machine(machine_id, protocol_class, error_rate, transmission_delay, window_size=self.window_size)
        else:
            machine = Machine(machine_id, protocol_class, error_rate, transmission_delay)

        self._machines[machine_id] = machine

        # Asignar referencia al simulador en el protocolo
        machine.protocol.set_simulator(self)

        if protocol_name in ['GoBackNProtocol', 'SelectiveRepeatProtocol']:
            print(f"[Simulator] Máquina {machine_id} agregada (protocolo={protocol_name}, window_size={self.window_size}, error_rate={error_rate}, transmission_delay={transmission_delay}s)")
        else:
            print(f"[Simulator] Máquina {machine_id} agregada (error_rate={error_rate}, transmission_delay={transmission_delay}s)")

    def schedule_event(self, event: Event) -> None:
        """Programa un evento en la cola."""
        # Siempre programar eventos, incluso si está pausado
        # La pausa solo afecta el procesamiento, no la programación
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
        if not self._paused:
            self._paused = True
            print("\n⏸️  [Simulator] Simulación PAUSADA - Los eventos en tránsito se mantendrán")
        else:
            print("\n⚠️  [Simulator] La simulación ya está pausada")

    def resume_simulation(self) -> None:
        """Reanuda la simulación."""
        if self._paused:
            self._paused = False
            print("\n▶️  [Simulator] Simulación REANUDADA - Procesando eventos...")
        else:
            print("\n⚠️  [Simulator] La simulación no está pausada")

    def is_paused(self) -> bool:
        """Retorna si la simulación está pausada."""
        return self._paused

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

        # Si está pausada, no procesar eventos
        if self._paused:
            return

        event_count = 0

        # Procesa todos los eventos pendientes
        while self._running and self.event_scheduler.has_events() and not self._paused:
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

    def run_simulation_step(self, real_time: float) -> None:
        """
        Procesa eventos cuyo tiempo haya llegado según tiempo real.

        Args:
            real_time: Tiempo real transcurrido desde el inicio
        """
        if not self._running or self._paused:
            return

        event_count = 0

        # Procesa eventos cuyo timestamp <= real_time
        while self._running and self.event_scheduler.has_events() and not self._paused:
            event = self.event_scheduler.peek_next_event()
            if not event:
                break

            # Solo procesar si el tiempo del evento ya llegó
            if event.timestamp > real_time:
                break

            # Extraer y procesar el evento
            event = self.event_scheduler.get_next_event()
            self._current_time = real_time  # Usar tiempo real
            event_count += 1

            # Entrega evento a la máquina correspondiente
            if event.machine_id in self._machines:
                machine = self._machines[event.machine_id]
                machine.handle_event(event, self)
            else:
                print(f"[ERROR] Máquina {event.machine_id} no encontrada")

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

    # ===== Métodos llamados por los protocolos =====

    def send_frame_from_protocol(self, machine_id: str, frame, destination: str) -> None:
        """
        Envía un frame desde el protocolo a través de la capa física.

        Args:
            machine_id: ID de la máquina que envía
            frame: Frame a enviar
            destination: ID de la máquina destino
        """
        if machine_id in self._machines:
            machine = self._machines[machine_id]
            machine.physical_layer.send_frame(frame, destination, self)

    def deliver_packet_to_network(self, machine_id: str, packet) -> None:
        """
        Entrega un packet a la capa de red.

        Args:
            machine_id: ID de la máquina receptora
            packet: Packet a entregar
        """
        if machine_id in self._machines:
            machine = self._machines[machine_id]
            event = Event("DELIVER_PACKET",
                         self.get_current_time() + 0.01,
                         machine_id,
                         packet)
            self.schedule_event(event)

    def start_protocol_timer(self, machine_id: str, timeout_duration: float = None, timer_id: int = None) -> None:
        """
        Inicia un timer para el protocolo.

        Args:
            machine_id: ID de la máquina
            timeout_duration: Duración del timeout (si es None, usa valor por defecto)
            timer_id: ID específico del timer (para Selective Repeat con timeouts individuales)
        """
        if machine_id in self._machines:
            machine = self._machines[machine_id]

            # Calcular timeout basado en transmission_delay
            if timeout_duration is None:
                transmission_delay = machine.get_transmission_delay()
                timeout_duration = max(3.0, transmission_delay * 3)

            # Si no se especifica timer_id, usar el sistema de timeout único
            if timer_id is None:
                # Incrementar ID de timeout (invalida timeouts anteriores)
                machine.active_timeout_id += 1
                timeout_id = machine.active_timeout_id
            else:
                # Usar el timer_id proporcionado (para Selective Repeat)
                timeout_id = timer_id

            # Programar evento de timeout
            event = Event(EventType.TIMEOUT,
                         self.get_current_time() + timeout_duration,
                         machine_id,
                         {'timeout_id': timeout_id})
            self.schedule_event(event)

            print(f"[Simulator] Timer iniciado para {machine_id}: {timeout_duration:.2f}s (#{timeout_id})")

    def stop_protocol_timer(self, machine_id: str) -> None:
        """
        Detiene el timer activo del protocolo.

        Args:
            machine_id: ID de la máquina
        """
        if machine_id in self._machines:
            machine = self._machines[machine_id]

            # Incrementar ID para invalidar timeouts pendientes
            machine.active_timeout_id += 1
            print(f"[Simulator] Timer detenido para {machine_id} (nuevo ID: #{machine.active_timeout_id})")