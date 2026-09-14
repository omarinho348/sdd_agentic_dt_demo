# WebSocket Telemetry Contract

## Server

Start from the repository root:

```powershell
python src/sim_engine.py
```

The service listens on `http://localhost:8000` by default. A health endpoint may be exposed at `/health` for readiness checks.

## WebSocket endpoint

```text
ws://localhost:8000/ws/telemetry
```

The connection remains open while simulation is running. The server sends JSON text frames; clients do not need to send messages.

## Frame schema

Every frame MUST have this shape:

```json
{
  "timestamp": 14.2,
  "station1_state": "BUSY",
  "station2_state": "IDLE",
  "queue_occupancy": 1
}
```

Rules:

- `timestamp` is SimPy simulation time, not wall-clock time.
- `station1_state` and `station2_state` are one of `IDLE`, `BUSY`, or `BLOCKED`.
- `queue_occupancy` is an integer from 0 through configured Queue capacity.
- A frame is emitted initially and whenever state or occupancy changes.
- All connected clients receive the same frame sequence for a broadcast event.
