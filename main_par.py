import time
from simulation.simulator import Simulator
from protocols.par import PARProtocol


def main():
    print("Simulador de Protocolos de Red - Protocolo PAR")
    print("=" * 50)

    # Crear simulador principal
    sim = Simulator()

    # Registrar máquinas para protocolo PAR
    # A = emisor, B = receptor
    sim.add_machine("A", PARProtocol, error_rate=0.2, transmission_delay=2.0)  # 20% error rate para probar reenvíos
    sim.add_machine("B", PARProtocol, error_rate=0.1, transmission_delay=1.5)

    # Mostrar configuración
    print(f"\nConfiguración del Protocolo PAR:")
    print(f"  Máquina A (emisor): error_rate={sim.get_machine_error_rate('A')}, delay={sim.get_machine_transmission_delay('A')}s")
    print(f"  Máquina B (receptor): error_rate={sim.get_machine_error_rate('B')}, delay={sim.get_machine_transmission_delay('B')}s")
    print(f"  Comunicación unidireccional: A -> B")

    print(f"\nIniciando envío con protocolo PAR (delay=2s entre letras)")
    print("Presiona Ctrl+C para detener...")

    # Inicializar el simulador una sola vez
    sim.start_simulation()

    # Datos a enviar (paquetes ilimitados según especificación)
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    numbers = "0123456789"
    data_sources = [alphabet, numbers]
    current_source = 0
    index = 0

    try:
        while True:
            # Alternar entre letras y números para variedad
            data_set = data_sources[current_source]
            char = data_set[index % len(data_set)]

            # Enviar el carácter
            success = sim.send_data("A", "B", char)

            if success:
                source_name = "letra" if current_source == 0 else "número"
                print(f"\n[Main] Enviando {source_name} '{char}' (#{index + 1})")

                # Procesar eventos generados por este envío
                sim.run_simulation()

                index += 1
                
                # Cambiar entre letras y números cada 10 caracteres
                if index % 10 == 0:
                    current_source = 1 - current_source
                    print(f"[Main] Cambiando a {'números' if current_source == 1 else 'letras'}")

            else:
                print(f"[Main] Error enviando carácter '{char}'")

            time.sleep(2.0)  # 2 segundos entre envíos para observar el protocolo

    except KeyboardInterrupt:
        print(f"\n[Main] Envío detenido por usuario")
    finally:
        sim.stop_simulation()
        print("\nSimulación completada!")
        
        # Mostrar estadísticas finales
        print("\n" + "="*50)
        print("ESTADÍSTICAS FINALES")
        print("="*50)
        for machine_id in ["A", "B"]:
            machine = sim._machines[machine_id]
            print(f"\nMáquina {machine_id}:")
            
            # Estadísticas de Physical Layer
            phys_stats = machine.physical_layer.get_stats()
            print(f"  Physical Layer:")
            print(f"    Frames enviados: {phys_stats['frames_sent']}")
            print(f"    Frames recibidos: {phys_stats['frames_received']}")
            print(f"    Frames corruptos: {phys_stats['corrupted_frames']}")
            print(f"    Tasa de corrupción observada: {phys_stats.get('corruption_rate_observed', 0):.1f}%")
            
            # Estadísticas del protocolo
            protocol_stats = machine.protocol.get_stats()
            print(f"  Protocolo PAR:")
            print(f"    Secuencia actual: {protocol_stats['current_seq']}")
            print(f"    Esperando ACK: {protocol_stats['waiting_for_ack']}")
            print(f"    Timeout configurado: {protocol_stats['timeout_duration']}s")
            
            # Estadísticas de Network Layer
            net_stats = machine.network_layer.get_stats()
            print(f"  Network Layer:")
            print(f"    Paquetes recibidos: {net_stats['packets_received']}")
            print(f"    Paquetes pendientes: {net_stats['pending_packets']}")


if __name__ == "__main__":
    main()