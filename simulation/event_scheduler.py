import heapq
from models.events import Event


class EventScheduler:
    def __init__(self):
        self._event_queue = []  # Cola de eventos ordenada por tiempo

    def schedule_event(self, event: Event) -> None:
        # Agrega evento a la cola ordenada
        heapq.heappush(self._event_queue, event)

    def get_next_event(self):
        # Obtiene el próximo evento cronológicamente
        return heapq.heappop(self._event_queue) if self._event_queue else None

    def has_events(self) -> bool:
        # Verifica si hay eventos pendientes
        return bool(self._event_queue)

    def peek_next_event(self):
        # Ve el próximo evento sin removerlo
        return self._event_queue[0] if self._event_queue else None

    def clear_events(self) -> None:
        # Limpia todos los eventos pendientes
        self._event_queue.clear()

    def cancel_events_for_machine(self, machine_id: str) -> int:
        # Cancela todos los eventos de una máquina específica
        original_count = len(self._event_queue)
        self._event_queue = [event for event in self._event_queue
                           if event.machine_id != machine_id]
        heapq.heapify(self._event_queue)  # Reorganiza el heap
        return original_count - len(self._event_queue)