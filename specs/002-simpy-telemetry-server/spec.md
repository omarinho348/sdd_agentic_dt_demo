# Feature Specification: SimPy Simulation Engine & Web Telemetry Server

**Feature Branch**: `002-simpy-telemetry-server`

**Created**: 2026-09-14

**Status**: Draft

**Input**: User description: "Build an asynchronous SimPy simulation engine and lightweight web server that reads assembly_line.json, executes the two-station assembly line in a background thread, and streams live telemetry over WebSockets."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start a live simulation from the validated model (Priority: P1)

As an operator, I want the simulation service to read the validated `assembly_line.json` contract and start the two-station assembly line so that the runtime behavior reflects the digital-twin model rather than duplicated configuration.

**Why this priority**: Contract ingestion and simulation startup are prerequisites for every telemetry workflow.

**Independent Test**: Provide a valid `assembly_line.json`, start `src/sim_engine.py`, and verify that the service starts on the documented local address and advances a SimPy environment without crashing.

**Acceptance Scenarios**:

1. **Given** a valid schema with Queue, Station1, and Station2 interfaces, **When** the service starts, **Then** it extracts both cycle times and queue capacity from the schema before starting simulation.
2. **Given** the service is running, **When** the item generator advances, **Then** items enter the first station at a two-second interval and progress toward packaging according to the configured cycle times.
3. **Given** a missing, malformed, or contract-invalid schema, **When** the service starts, **Then** it reports a clear startup error and does not run a partial simulation.

### User Story 2 - Observe live station and queue telemetry (Priority: P1)

As a browser client, I want to connect to a WebSocket endpoint and receive live station states and queue occupancy so that I can observe the simulation as it advances.

**Why this priority**: Streaming state is the primary user-visible outcome of this feature.

**Independent Test**: Connect a WebSocket client to `/ws/telemetry`, collect multiple frames, and verify that each frame contains the required timestamp, station states, and queue occupancy.

**Acceptance Scenarios**:

1. **Given** a running service, **When** a client connects to `/ws/telemetry`, **Then** the connection remains open and receives JSON telemetry frames continuously.
2. **Given** a telemetry frame, **When** the client parses it, **Then** it contains `timestamp`, `station1_state`, `station2_state`, and `queue_occupancy`.
3. **Given** station work and queue pressure, **When** simulation state changes, **Then** the stream reports `IDLE`, `BUSY`, or `BLOCKED` for each station and a non-negative queue occupancy.
4. **Given** multiple connected clients, **When** a state update occurs, **Then** each connected client receives the update without one client blocking or terminating another.

### User Story 3 - Keep simulation and web serving responsive (Priority: P1)

As a developer evaluating the digital twin, I want simulation execution isolated from the web server thread so that the server remains responsive while discrete events advance in the background.

**Why this priority**: Thread ownership is a constitutional architecture boundary and prevents a simulation loop from freezing browser clients.

**Independent Test**: Start the service, connect a telemetry client, and make repeated HTTP or WebSocket interactions while simulation events advance; verify responses continue arriving and no direct shared-state mutation is required.

**Acceptance Scenarios**:

1. **Given** a running service, **When** SimPy advances simulated time, **Then** the web server continues accepting and serving client connections.
2. **Given** a telemetry update, **When** the simulation thread communicates with the server, **Then** communication occurs through thread-safe queues rather than direct mutation of server-owned state.
3. **Given** a client disconnects, **When** later telemetry updates occur, **Then** the simulation continues and remaining clients continue receiving frames.

### Edge Cases

- `assembly_line.json` is missing, unreadable, malformed JSON, or contains the wrong number of interfaces.
- A station cycle time or queue capacity is zero, negative, missing, or has an unexpected schema type.
- The generator rate temporarily exceeds station throughput and the inter-station resource reaches capacity; the affected station reports `BLOCKED` rather than silently dropping items.
- The WebSocket client connects before the first simulation update; it receives the next available valid frame without an invalid placeholder.
- A client disconnects during broadcast; the server removes that client and continues broadcasting to others.
- The simulation thread raises an exception; the service reports the failure and does not emit fabricated telemetry.
- The requested port is already in use; startup reports the conflict and leaves the existing process untouched.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The service MUST read `assembly_line.json` at startup and validate it using the project’s Pydantic DTDL models before simulation begins.
- **FR-002**: The service MUST extract Queue capacity, Station1 cycle time, and Station2 cycle time from the validated schema and MUST NOT maintain a second configuration source for those values.
- **FR-003**: The service MUST instantiate a SimPy environment for each service run.
- **FR-004**: The service MUST generate a new item every 2.0 simulated seconds.
- **FR-005**: The service MUST model inter-station storage with a capacity-limited resource derived from the Queue interface.
- **FR-006**: The service MUST execute Station1 and Station2 process loops with `env.timeout()` durations derived from their cycle-time properties.
- **FR-007**: Each station MUST expose exactly one discrete state from `IDLE`, `BUSY`, or `BLOCKED` at every telemetry update.
- **FR-008**: The service MUST expose a WebSocket endpoint at `/ws/telemetry` on the documented local HTTP server.
- **FR-009**: The service MUST broadcast JSON telemetry frames whenever station state or queue occupancy changes.
- **FR-010**: Each telemetry frame MUST include `timestamp`, `station1_state`, `station2_state`, and `queue_occupancy`.
- **FR-011**: `timestamp` MUST represent the current SimPy simulation time, and `queue_occupancy` MUST be a non-negative integer not greater than configured capacity.
- **FR-012**: The service MUST support multiple connected WebSocket clients and isolate client disconnects from simulation execution and other clients.
- **FR-013**: SimPy MUST run on a background daemon thread, while the HTTP/WebSocket server remains responsive on its serving thread.
- **FR-014**: Simulation-to-server communication MUST use thread-safe Python queues and MUST NOT rely on direct shared-variable mutation.
- **FR-015**: The service MUST report startup, schema, simulation, and connection failures clearly and MUST NOT emit invalid or fabricated telemetry after a fatal simulation error.
- **FR-016**: The service MUST be startable with `python src/sim_engine.py` and serve the local application on `http://localhost:8000` unless an explicit supported port override is provided.

### Constitutional Constraints

- **CC-001**: The topology MUST remain `Queue` -> `Assembly Station` -> `Packaging Station`; no additional station may be introduced.
- **CC-002**: Generated DTDL v3 JSON remains the single source of truth; the runtime MUST consume the validated `assembly_line.json` artifact.
- **CC-003**: SimPy MUST run on a background daemon thread, and inter-thread communication MUST use `queue.Queue`.
- **CC-004**: The implementation MUST avoid LangChain, AutoGen, CrewAI, and other heavy agent frameworks.

### Key Entities

- **SimulationConfiguration**: Validated runtime values extracted from the DTDL artifact: queue capacity and two station cycle times.
- **SimulationState**: Current SimPy timestamp, station states, and queue occupancy.
- **TelemetryFrame**: The JSON message sent to WebSocket clients.
- **TelemetryEventQueue**: Thread-safe channel carrying simulation updates from the daemon thread to the web server.
- **WebSocket Client**: A connected consumer that receives broadcast telemetry frames and can disconnect independently.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of starts with a valid `assembly_line.json` expose an HTTP server on the documented local address and begin advancing simulation time.
- **SC-002**: A connected WebSocket client receives at least 10 valid telemetry frames within 10 wall-clock seconds during a normal run.
- **SC-003**: 100% of telemetry frames contain all four required fields with valid state values and queue occupancy within configured bounds.
- **SC-004**: With two simultaneous clients connected, both clients receive the same state-update sequence within one broadcast cycle for at least 20 consecutive frames.
- **SC-005**: Disconnecting one client does not stop simulation or prevent another connected client from receiving the next 10 telemetry frames.
- **SC-006**: A schema validation or simulation startup failure produces no telemetry frames claiming a running simulation state.
- **SC-007**: Under normal local evaluation load, the HTTP/WebSocket service responds to a new connection within 1 second while simulation events continue advancing.

## Assumptions

- Feature 001 has already produced `assembly_line.json` in the repository root before Feature 002 starts.
- The local server is a development/evaluation service and does not require authentication or multi-user persistence.
- The web server may use FastAPI/WebSockets or an equivalent lightweight Python server, provided the required endpoint and threading boundaries remain intact.
- Simulation time is independent of wall-clock time; the service advances events continuously at a rate suitable for live observation.
- `IDLE`, `BUSY`, and `BLOCKED` are the complete station-state vocabulary for this feature.
- The existing browser UI may be extended to display telemetry, but the WebSocket endpoint and frame contract are independently testable.
