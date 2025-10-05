from models.packet import Packet

class NetworkLayer:
    def __init__(self, machine_id: str):
        self.machine_id = machine_id
        self.received_packets = []  # Lista de paquetes recibidos
        self.pending_data = []  # Cola de datos pendientes por enviar

    def has_data_ready(self) -> bool:
        # Solo tiene datos si hay algo en la cola pendiente
        return len(self.pending_data) > 0

    def add_data_to_send(self, data: str, destination: str) -> None:
        """Agrega datos específicos a la cola de envío con destino"""
        message = {'data': data, 'destination': destination}
        self.pending_data.append(message)
        print(f"  [NetworkLayer-{self.machine_id}] Datos agregados a cola: '{data}' -> {destination}")

    def get_packet(self) -> tuple:
        # Toma el siguiente dato de la cola y retorna (packet, destination)
        if self.pending_data:
            message = self.pending_data.pop(0)
            packet = Packet(message['data'])
            destination = message['destination']
            print(f"  [NetworkLayer-{self.machine_id}] Generado: {packet} -> {destination}")
            return packet, destination
        return None, None

    def deliver_packet(self, packet: Packet, simulator=None):
        # Entrega el paquete recibido a la aplicación
        self.received_packets.append(packet)
        print(f"  [NetworkLayer-{self.machine_id}] Entregado a aplicación: {packet}")

        # Notificar GUI si existe callback
        if simulator and hasattr(simulator, 'gui_callback') and simulator.gui_callback:
            simulator.gui_callback('packet_delivered', {
                'packet': packet,
                'machine_id': self.machine_id
            })

    def get_stats(self):
        # Retorna estadísticas de envío y recepción
        return {
            'packets_received': len(self.received_packets),
            'pending_packets': len(self.pending_data)
        }