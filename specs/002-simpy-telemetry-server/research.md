# Research: SimPy Simulation Engine & Web Telemetry Server

## Decision: FastAPI and Uvicorn own the WebSocket server

- **Decision**: Use FastAPI for `/health` and `/ws/telemetry`, served by Uvicorn from `src/sim_engine.py`.
- **Rationale**: FastAPI provides a small, explicit WebSocket lifecycle API and integrates with the existing Python project without a frontend build system. Uvicorn supplies the async serving loop while SimPy remains isolated in its required daemon thread.
- **Alternatives considered**: A raw `websockets` server was rejected because HTTP health/startup handling and connection lifecycle would require more custom code. A second server framework was rejected because it would add unnecessary runtime complexity.

## Decision: Run SimPy in a daemon thread and bridge through a queue

- **Decision**: The server creates a `queue.Queue[TelemetryFrame]`; a daemon thread owns the SimPy environment and places validated frames on that queue. An asyncio task owned by the Uvicorn loop drains the queue and broadcasts frames through `ConnectionManager`.
- **Rationale**: This satisfies the constitution's thread boundary and avoids calling async WebSocket methods directly from the simulation thread. `asyncio.run_coroutine_threadsafe` is reserved for scheduling the queue-drain notification onto the server loop when the implementation needs immediate wakeup; the frame data still crosses through `queue.Queue`.
- **Alternatives considered**: Direct mutation of a shared current-state object was rejected by constitutional constraint. Running SimPy in the Uvicorn event loop was rejected because long-running simulation work could compromise server responsiveness.

## Decision: Use SimPy Store for bounded inter-station storage

- **Decision**: Use a capacity-limited `simpy.Store` as the inter-station queue, with `put()` for Assembly output and `get()` for Packaging input. The configured Queue capacity is the Store capacity.
- **Rationale**: `simpy.Store` directly models item transfer and exposes a bounded `len(items)` occupancy. Assembly can report `BLOCKED` while waiting for storage capacity, while Packaging consumes items independently.
- **Alternatives considered**: `simpy.Resource` was rejected as a service lock rather than an item-storage queue. A Python `queue.Queue` inside SimPy was rejected because it would not participate in SimPy event scheduling.

## Decision: Emit frames on meaningful state and occupancy changes

- **Decision**: The simulation publishes a `TelemetryFrame` whenever a station state changes or the Store occupancy changes, with an initial frame at simulation time zero and a small polling event only for idle periods if needed.
- **Rationale**: Change-driven frames reduce noise while guaranteeing clients observe transitions. The initial frame gives newly connected clients a valid next state without fabricating data.
- **Alternatives considered**: Fixed wall-clock polling was rejected because telemetry timestamps must represent SimPy time and excessive polling adds duplicate frames.

## Decision: Validate schema through Feature 001 models

- **Decision**: Load the JSON array, validate each object with the existing `DTDLInterface`, and derive `AssemblyLineConfig` only from the required stable IDs and contents.
- **Rationale**: This preserves DTDL contract primacy and prevents the simulation from silently using stale or duplicated configuration.
- **Alternatives considered**: Reading arbitrary JSON paths was rejected because it bypasses contract validation. A separate simulation configuration file was rejected because it creates a second source of truth.
