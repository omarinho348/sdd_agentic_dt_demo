# Implementation Plan: SimPy Simulation Engine & Web Telemetry Server

**Branch**: `002-simpy-telemetry-server` | **Date**: 2026-09-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-simpy-telemetry-server/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command; its definition describes the execution workflow.

## Summary

Implement `src/sim_engine.py` as the runtime bridge between the validated Feature 001
DTDL document and live browser telemetry. The module will define `AssemblyLineConfig`
and `TelemetryFrame` Pydantic contracts, ingest and validate `assembly_line.json`, run
the two-station SimPy process in a daemon thread, and expose a FastAPI/Uvicorn
`/ws/telemetry` endpoint. Simulation snapshots cross the thread boundary through a
thread-safe `queue.Queue`; an asyncio task broadcasts them through a connection manager.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.13+

**Primary Dependencies**: `simpy`, `fastapi`, `uvicorn`, `websockets`, `pydantic`, and
standard-library `threading`, `queue`, `asyncio`, `json`, and `pathlib`

**Storage**: Read-only `assembly_line.json` contract; no new persistent store

**Testing**: pytest unit tests, FastAPI TestClient/WebSocket tests, and a two-client
integration test with a bounded runtime

**Target Platform**: Local Windows/Python terminal; Uvicorn on `localhost:8000`

**Project Type**: Local WebSocket telemetry service with a reusable simulation engine

**Performance Goals**: At least 10 valid frames per client within 10 wall-clock seconds;
new WebSocket connections accepted within 1 second while simulation runs

**Constraints**: Exactly two stations; 2.0 simulated-second generator interval;
bounded queue; daemon SimPy thread; `queue.Queue` bridge; no fabricated telemetry after
fatal errors; port 8000 by default

**Scale/Scope**: Local evaluation service supporting multiple simultaneous WebSocket
clients and one simulation run per process

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- LLM and generation: all agent prompts and dynamic code generation use `gpt-4o-mini`,
  with bounded JSON output validated by Pydantic or JSON response format.
- Architecture: the design preserves `Queue` -> `Assembly Station` -> `Packaging Station`,
  uses a daemon SimPy thread, a main-thread PyOpenGL loop, and `queue.Queue` for all
  inter-thread communication.
- Contract: generated DTDL v3 is the source of truth, and validation occurs before
  writing `assembly_line.json`.

**Gate status before Phase 0**: PASS. The plan consumes the validated Feature 001
contract, preserves the required topology, uses only the approved lightweight server
dependencies, and assigns simulation to a daemon thread with queue-based communication.

**Gate status after Phase 1**: PASS. Research and design define explicit Pydantic
contracts, failure behavior, state transitions, WebSocket frames, and multi-client
lifecycle without adding a second configuration source or heavy framework.

## Project Structure

### Documentation (this feature)

```text
specs/002-simpy-telemetry-server/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
src/
├── sim_engine.py          # Config ingestion, SimPy thread, FastAPI app, WebSocket endpoint
├── dtdl_generator.py      # Existing Feature 001 DTDL/Pydantic contract owner
└── web/                   # Existing Feature 001 browser assets; optional telemetry consumer

tests/
├── test_sim_engine.py     # Models, ingestion, simulation, API, WebSocket lifecycle
└── fixtures/
  └── assembly_line.json  # Valid and invalid contract fixtures
```

**Structure Decision**: Add one focused runtime module, `src/sim_engine.py`, rather than
splitting the small service across packages. Reuse Feature 001's `DTDLInterface` model
and mapping conventions, keep the FastAPI app importable for test clients, and isolate
the SimPy environment inside a daemon worker. The existing browser UI can consume the
WebSocket later without changing this service's frame contract.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | The design complies with all constitutional gates. |
