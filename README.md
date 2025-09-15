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

```mermaid
sequenceDiagram
    participant A as Máquina A<br/>(Emisor)
    participant PA as Protocol<br/>(Utopia/Stop&Wait/etc)
    participant NLA as NetworkLayer A
    participant PLA as PhysicalLayer A
    participant NET as Canal de Red<br/>(con errores)
    participant PLB as PhysicalLayer B
    participant PB as Protocol B
    participant NLB as NetworkLayer B
    participant B as Máquina B<br/>(Receptor)

    Note over A,B: Simulación por Eventos Discretos

    A->>PA: start_protocol()
    PA->>PA: programa event "network_layer_ready"

    loop Cada segundo
        PA->>NLA: has_data_ready()
        NLA->>PA: True
        PA->>NLA: get_packet()
        NLA->>PA: Packet("Data_A_1")
        PA->>PA: crear Frame con packet
        PA->>PLA: send_frame(frame, "B")

        PLA->>NET: transmitir frame
        Note over NET: Posible corrupción<br/>(según tasa de errores)
        NET->>PLB: frame + retardo

        alt Frame válido
            PLB->>PB: event "frame_arrival"
            PB->>NLB: deliver_packet()
            NLB->>B: entregar a aplicación
        else Frame corrupto
            PLB->>PB: event "cksum_err"
            PB->>PB: descartar frame
        end

        PA->>PA: programar próximo envío
    end
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

```mermaid
graph TD
    %% Subgrafos principales
    subgraph Simulador
        SIM[Simulator]
        ES[EventScheduler]
        MA[Machine A]
        MB[Machine B]
    end

    subgraph Protocolos
        BP[BaseProtocol]
        UP[UtopiaProtocol]
        SW[Stop&Wait]
        GBN[GoBackN]
        SR[SelectiveRepeat]
        OTHER[... otros]
    end

    subgraph Capas
        NL[NetworkLayer]
        PL[PhysicalLayer]
    end

    subgraph Modelos
        EV[Event]
        PKT[Packet]
        FR[Frame]
    end

    %% Relaciones principales
    SIM --> ES
    SIM --> MA
    SIM --> MB

    MA --> UP
    MB --> UP

    UP --> BP
    SW --> BP
    GBN --> BP
    SR --> BP
    OTHER --> BP

    UP --> NL
    UP --> PL

    UP --> EV
    NL --> PKT
    PL --> FR

    %% Nota importante
    BP -.-> NOTE["Cualquiera de los 6<br/>protocolos puede<br/>sustituir a Utopia"]
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
