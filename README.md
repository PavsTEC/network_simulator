# Simulador de Protocolos de Red

Simulador educativo que muestra cómo las máquinas se comunican enviando datos a través de una red con errores.

## ¿Cómo Funciona?

### 1. Configuración Inicial
```python
python main.py
```

El programa crea:
- **Máquina A**: Emisor que envía datos
- **Máquina B**: Receptor que recibe datos
- **Simulador**: Coordina toda la comunicación

### 2. Flujo del Programa

```plantuml
@startuml
!define RECTANGLE class

participant "Máquina A\n(Emisor)" as A
participant "Protocol\n(Utopia/Stop&Wait/etc)" as PA
participant "NetworkLayer A" as NLA
participant "PhysicalLayer A" as PLA
participant "Canal de Red\n(con errores)" as NET
participant "PhysicalLayer B" as PLB
participant "Protocol B" as PB
participant "NetworkLayer B" as NLB
participant "Máquina B\n(Receptor)" as B

note over A, B: Simulación por Eventos Discretos

A -> PA: start_protocol()
PA -> PA: programa event "network_layer_ready"

loop Cada segundo
    PA -> NLA: has_data_ready()
    NLA -> PA: True
    PA -> NLA: get_packet()
    NLA -> PA: Packet("Data_A_1")
    PA -> PA: crear Frame con packet
    PA -> PLA: send_frame(frame, "B")

    PLA -> NET: transmitir frame
    note over NET: Posible corrupción\n(según tasa de errores)
    NET -> PLB: frame + retardo

    alt Frame válido
        PLB -> PB: event "frame_arrival"
        PB -> NLB: deliver_packet()
        NLB -> B: entregar a aplicación
    else Frame corrupto
        PLB -> PB: event "cksum_err"
        PB -> PB: descartar frame
    end

    PA -> PA: programar próximo envío
end

@enduml
```

#### Paso a paso:
1. **Máquina A** pide datos a su NetworkLayer
2. **NetworkLayer** crea un paquete con texto único
3. **Máquina A** mete el paquete en un Frame
4. **PhysicalLayer** envía el frame (puede corromperse)
5. **Máquina B** recibe el frame después de un retardo
6. Si llegó bien → entrega a aplicación
7. Si llegó corrupto → lo descarta
8. **Máquina A** programa enviar otro frame en 1 segundo

### 3. Sistema de Eventos

El simulador funciona con **eventos programados**:
- `network_layer_ready`: "Tengo datos para enviar"
- `frame_arrival`: "Llegó un frame válido"
- `cksum_err`: "Llegó un frame corrupto"

### 4. Lo Que Ves en Pantalla

```
--- Tiempo: 0.10s | Evento #1 ---
[A] Procesando: Event(network_layer_ready, t=0.10, machine=A)
  [NetworkLayer-A] Generado: Packet(Data_A_1)
  [PhysicalLayer] Enviando Frame(DATA, packet=Data_A_1) hacia B
  [PhysicalLayer] ¡Frame corrupto durante transmisión!

--- Tiempo: 0.60s | Evento #2 ---
[B] Procesando: Event(cksum_err, t=0.60, machine=B)
[B] Frame corrupto recibido
```

## Configuración de Errores

```python
sim.set_global_error_rate(0.2)    # 20% de frames se corrompen
sim.set_error_rate("A", 0.05)     # Máquina A: solo 5% errores
```

## Arquitectura del Sistema

```plantuml
@startuml
!theme plain

package "Simulador" {
  [Simulator] as SIM
  [EventScheduler] as ES
  [Machine A] as MA
  [Machine B] as MB
}

package "Protocolo" {
  [BaseProtocol] as BP
  [UtopiaProtocol] as UP
  [Stop&Wait] as SW
  [GoBackN] as GBN
  [SelectiveRepeat] as SR
  [... otros] as OTHER
}

package "Capas de Red" {
  [NetworkLayer] as NL
  [PhysicalLayer] as PL
}

package "Modelos de Datos" {
  [Event] as EV
  [Packet] as PKT
  [Frame] as FR
}

' Relaciones principales
SIM --> ES : programa eventos
SIM --> MA : controla
SIM --> MB : controla

MA --> UP : implementa
MB --> UP : implementa

UP --> BP : hereda de
SW --> BP : hereda de
GBN --> BP : hereda de
SR --> BP : hereda de
OTHER --> BP : hereda de

UP --> NL : usa
UP --> PL : usa

UP --> EV : genera
NL --> PKT : crea
PL --> FR : maneja

note right of BP : Cualquiera de los 6\nprotocolos puede\nsustituir a Utopia

@enduml
```

## Estructura de Archivos

```
main.py           # Punto de entrada - configura y ejecuta
├── simulation/
│   ├── simulator.py      # Coordinador principal
│   └── event_scheduler.py # Cola de eventos ordenada por tiempo
├── protocols/
│   └── utopia.py         # Protocolo simple: A envía, B recibe
├── layers/
│   ├── network_layer.py  # Crea y entrega paquetes
│   └── physical_layer.py # Envía frames, simula errores
└── models/
    ├── packet.py         # Datos a enviar
    ├── frame.py          # Envoltorio del packet
    └── events.py         # Eventos del simulador
```

## ¿Para Qué Sirve?

Este simulador te ayuda a entender:
- Cómo los datos viajan por una red
- Por qué los protocolos necesitan manejar errores
- Cómo funciona la simulación por eventos discretos
- La diferencia entre paquetes y frames

## Ejecutar

```bash
python main.py
```

Verás la configuración de errores, luego el intercambio de frames en tiempo real, y finalmente las estadísticas de cuántos frames se enviaron y recibieron.
