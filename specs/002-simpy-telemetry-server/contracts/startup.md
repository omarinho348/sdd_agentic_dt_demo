# Startup and Failure Contract

## Valid startup

With a valid `assembly_line.json`, `python src/sim_engine.py` starts Uvicorn on port 8000, starts one daemon SimPy thread, and makes `/ws/telemetry` available.

## Invalid startup

If the schema is missing, malformed, or fails Pydantic validation, startup MUST fail clearly and MUST NOT start a simulation thread that emits frames.

If port 8000 is unavailable, startup MUST report the bind failure and MUST NOT terminate or alter the process already using the port.

## Client lifecycle

A disconnected WebSocket client is removed from the active connection set. Other clients continue receiving frames, and simulation continues independently.
