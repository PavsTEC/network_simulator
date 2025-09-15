from simulation.simulator import Simulator
from protocols.utopia import UtopiaProtocol


def main():
    print("Simulador de Protocolos de Red")
    print("=" * 30)

    # Crear simulador principal
    sim = Simulator()

    # Crear máquinas con protocolo Utopia (A=emisor, B=receptor)
    machine_a = UtopiaProtocol("A")
    machine_b = UtopiaProtocol("B")

    # Registrar máquinas en el simulador
    sim.add_machine("A", machine_a)
    sim.add_machine("B", machine_b)

    # Mostrar configuración inicial de errores
    print(f"\nConfiguración inicial de tasas de errores:")
    print(f"Máquina A: {sim.get_error_rate('A')}")
    print(f"Máquina B: {sim.get_error_rate('B')}")

    # Configurar tasas de errores
    print(f"\nConfigurando tasa de errores global a 0.2...")
    sim.set_global_error_rate(0.2)

    print(f"\nConfigurando tasa de errores para máquina A a 0.05...")
    sim.set_error_rate("A", 0.05)

    # Mostrar configuración final
    print(f"\nConfiguración final de tasas de errores:")
    print(f"Máquina A: {sim.get_error_rate('A')}")
    print(f"Máquina B: {sim.get_error_rate('B')}")

    # Ejecutar simulación completa
    sim.run_simulation()

    print("\nSimulación completada!")


if __name__ == "__main__":
    main()