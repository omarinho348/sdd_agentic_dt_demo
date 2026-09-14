# Quickstart: SimPy Simulation Engine & Web Telemetry Server

## Prerequisites

- Python 3.13 or newer
- Dependencies installed with `uv sync --group dev`
- A validated `assembly_line.json` in the repository root from Feature 001

## Start the service

From the repository root:

```powershell
uv run python src/sim_engine.py
```

Expected output includes a local server address such as `http://localhost:8000`. Keep this terminal running.

## Check the WebSocket stream

Use a second terminal:

```powershell
uv run python -c "import asyncio, json, websockets; async def main():\n  async with websockets.connect('ws://localhost:8000/ws/telemetry') as socket:\n    for _ in range(10):\n      frame = json.loads(await socket.recv()); print(frame)\nasyncio.run(main())"
```

Each printed frame must contain `timestamp`, `station1_state`, `station2_state`, and `queue_occupancy`. State values must be `IDLE`, `BUSY`, or `BLOCKED`; timestamps should increase or remain ordered; occupancy must remain within Queue capacity.

If the one-line PowerShell command is inconvenient, place the equivalent async client in `tests/manual_telemetry_client.py` and run it with `uv run python tests/manual_telemetry_client.py`.

## Automated validation

```powershell
uv run pytest tests/test_sim_engine.py -q
uv run pytest -q
```

Expected result: schema-ingestion, state-transition, background-thread, WebSocket, multi-client, and disconnect tests pass.

## Failure checks

- Temporarily rename `assembly_line.json`; startup must fail without emitting telemetry.
- Connect two clients, disconnect one, and confirm the other continues receiving frames.
- Restore the schema after checks and stop the server with `Ctrl+C`.

## Browser evaluation

Open `http://127.0.0.1:8000` after starting either `src/sim_engine.py` or
`src/web_app.py` to see the DTDL workbench and live station states, queue occupancy,
and simulation time on the same origin. `src/web_app.py` is now a compatibility entry
point for the unified FastAPI application.
