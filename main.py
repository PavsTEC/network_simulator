import time
from simulation.simulator import Simulator
from protocols.utopia import UtopiaProtocol


def main():
    print("Simulador de Protocolos de Red")
    print("=" * 30)

    # Crear simulador principal
    sim = Simulator()

    # Registrar máquinas para protocolo Utopia
    sim.add_machine("A", UtopiaProtocol, error_rate=0.0, transmission_delay=3.0)
    sim.add_machine("B", UtopiaProtocol, error_rate=0.0, transmission_delay=2.0)

    # Mostrar configuración
    print(f"\nConfiguración:")
    print(f"  Máquina A: error_rate={sim.get_machine_error_rate('A')}, delay={sim.get_machine_transmission_delay('A')}s")
    print(f"  Máquina B: error_rate={sim.get_machine_error_rate('B')}, delay={sim.get_machine_transmission_delay('B')}s")

    print(f"\nIniciando envío del abecedario: A -> B (delay=1.5s entre letras)")
    print("Presiona Ctrl+C para detener...")

    # Inicializar el simulador una sola vez
    sim.start_simulation()

    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    index = 0

    try:
        while True:
            letter = alphabet[index % len(alphabet)]

            # Enviar la letra
            success = sim.send_data("A", "B", letter)

            if success:
                print(f"\n[Main] Enviando letra '{letter}' ({index + 1})")

                # Procesar eventos generados por este envío
                sim.run_simulation()

                index += 1
            else:
                print(f"[Main] Error enviando letra '{letter}'")

            time.sleep(1.5)  # 1.5 segundos entre letras

    except KeyboardInterrupt:
        print(f"\n[Main] Envío del abecedario detenido por usuario")
    finally:
        sim.stop_simulation()
        print("\nSimulación completada!")


if __name__ == "__main__":
    main()