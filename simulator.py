import heapq
import time
from models.events import Event, EventType
from protocols.utopia import UtopiaProtocol

class Simulator:
    def __init__(self):
        self.machines = {}
        self.event_queue = []
        self.current_time = 0.0
        self.max_time = 10.0  # Simular por 10 segundos
        self.running = False
        self.event_count = 0
    
    def add_machine(self, machine_id: str, protocol):
        """Agrega una máquina con su protocolo"""
        self.machines[machine_id] = protocol
        print(f"[Simulator] Máquina {machine_id} agregada con protocolo {protocol.__class__.__name__}")
    
    def schedule_event(self, event: Event):
        """Programa un evento en el futuro"""
        heapq.heappush(self.event_queue, event)
        print(f"[Simulator] Evento programado: {event}")
    
    def run_simulation(self):
        """Ejecuta la simulación"""
        print(f"\n{'='*50}")
        print(f"INICIANDO SIMULACIÓN")
        print(f"{'='*50}")
        
        # Inicializar protocolos
        for machine_id, protocol in self.machines.items():
            protocol.start_protocol(self)
        
        self.running = True
        
        # Loop principal de simulación
        while self.running and self.event_queue and self.current_time < self.max_time:
            event = heapq.heappop(self.event_queue)
            self.current_time = event.timestamp
            self.event_count += 1
            
            print(f"\n--- Tiempo: {self.current_time:.2f}s | Evento #{self.event_count} ---")
            
            # Procesar evento
            if event.machine_id in self.machines:
                machine = self.machines[event.machine_id]
                machine.handle_event(event, self)
            else:
                print(f"[ERROR] Máquina {event.machine_id} no encontrada")
        
        self._print_final_stats()
    
    def stop_simulation(self):
        """Detiene la simulación"""
        self.running = False
    
    def _print_final_stats(self):
        """Imprime estadísticas finales"""
        print(f"\n{'='*50}")
        print(f"SIMULACIÓN TERMINADA")
        print(f"{'='*50}")
        print(f"Tiempo total: {self.current_time:.2f}s")
        print(f"Eventos procesados: {self.event_count}")
        
        for machine_id, protocol in self.machines.items():
            print(f"\n--- Estadísticas Máquina {machine_id} ---")
            stats = protocol.get_stats()
            for key, value in stats.items():
                if isinstance(value, dict):
                    print(f"  {key}:")
                    for k, v in value.items():
                        print(f"    {k}: {v}")
                else:
                    print(f"  {key}: {value}")