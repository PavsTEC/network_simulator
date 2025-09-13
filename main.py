from simulator import Simulator
from protocols.utopia import UtopiaProtocol

def main():
    print("🚀 Simulador de Protocolos de Red")
    print("Protocolo: Utopia")
    print("=" * 30)
    
    # Crear simulador
    sim = Simulator()
    
    # Crear máquinas con protocolo Utopia
    machine_a = UtopiaProtocol("A")  # Emisor
    machine_b = UtopiaProtocol("B")  # Receptor
    
    # Agregar máquinas al simulador
    sim.add_machine("A", machine_a)
    sim.add_machine("B", machine_b)
    
    # Ejecutar simulación
    sim.run_simulation()
    
    print("\n✅ Simulación completada!")

if __name__ == "__main__":
    main()