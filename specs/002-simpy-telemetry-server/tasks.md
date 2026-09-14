# Tasks: SimPy Simulation Engine & Web Telemetry Server

**Input**: Design documents from `/specs/002-simpy-telemetry-server/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Included because the specification defines schema-ingestion, simulation, WebSocket, multi-client, failure, and responsiveness acceptance scenarios.

**Organization**: Tasks are grouped by user story, with shared infrastructure in Setup and Foundational phases.

## Phase 1: Setup

**Purpose**: Add the approved server dependencies and test surface without changing Feature 001 behavior.

- [X] T001 Add `fastapi`, `uvicorn`, and `websockets` runtime dependencies in `pyproject.toml` and refresh `uv.lock`.
- [X] T002 [P] Create `tests/test_sim_engine.py` and `tests/fixtures/` for Feature 002 coverage.
- [X] T003 [P] Add a valid Feature 001-compatible schema fixture at `tests/fixtures/assembly_line.json` for deterministic simulation tests.
- [X] T004 [P] Add invalid, missing, and malformed schema fixtures under `tests/fixtures/` for startup failure tests.
- [X] T005 [P] Add Feature 002 startup and WebSocket commands to `specs/002-simpy-telemetry-server/quickstart.md` and the repository `README.md`.

## Phase 2: Foundational

**Purpose**: Establish contract ingestion, telemetry validation, queue bridging, and connection lifecycle before story-specific behavior.

**Checkpoint**: Foundation is ready when a valid DTDL artifact yields an `AssemblyLineConfig`, every telemetry snapshot validates as a `TelemetryFrame`, and simulation events can cross from the worker thread through `queue.Queue`.

- [X] T006 Define `AssemblyLineConfig` in `src/sim_engine.py` with positive cycle times, positive queue capacity, and fixed `item_interval=2.0` validation.
- [X] T007 Define `TelemetryFrame` in `src/sim_engine.py` with non-negative timestamp, `IDLE`/`BUSY`/`BLOCKED` states, and bounded queue occupancy validation.
- [X] T008 Implement DTDL schema loading and Pydantic validation in `src/sim_engine.py` by reusing `src/dtdl_generator.py` and rejecting missing, malformed, or contract-invalid artifacts.
- [X] T009 Implement extraction of Queue capacity and Station1/Station2 cycle times from validated `assembly_line.json` contents in `src/sim_engine.py` without introducing a second configuration file.
- [X] T010 Implement `ConnectionManager` in `src/sim_engine.py` with connect, disconnect, broadcast, and failed-client removal behavior.
- [X] T011 Create the FastAPI app and Uvicorn startup entry point in `src/sim_engine.py`, defaulting to `localhost:8000` and exposing `/health`.
- [X] T012 [P] Add unit tests for `AssemblyLineConfig`, `TelemetryFrame`, schema ingestion, and malformed-contract rejection in `tests/test_sim_engine.py`.
- [X] T013 [P] Add connection-manager tests in `tests/test_sim_engine.py` for registration, broadcast fan-out, and disconnect isolation.

## Phase 3: User Story 1 - Start A Live Simulation From The Validated Model (Priority: P1)

**Goal**: A valid `assembly_line.json` starts a two-station SimPy process using only contract-derived timing and capacity values.

**Independent Test**: Start the engine with the fixture contract, run the simulation for bounded simulated time, and assert generator cadence, station processing, queue bounds, and startup failure behavior.

### Tests for User Story 1

- [X] T014 [P] [US1] Add a simulation startup test in `tests/test_sim_engine.py` that builds a SimPy environment from the valid fixture and advances it without errors.
- [X] T015 [P] [US1] Add generator cadence coverage in `tests/test_sim_engine.py` proving new items are scheduled every 2.0 simulated seconds.
- [X] T016 [P] [US1] Add station processing coverage in `tests/test_sim_engine.py` proving `env.timeout()` uses both configured cycle times and items reach packaging.
- [X] T017 [P] [US1] Add invalid-schema startup tests in `tests/test_sim_engine.py` for missing, malformed, wrong-count, and invalid-value contracts.

### Implementation for User Story 1

- [X] T018 [US1] Implement the SimPy environment and bounded `simpy.Store` inter-station queue in `src/sim_engine.py` using `AssemblyLineConfig.queue_capacity`.
- [X] T019 [US1] Implement the item generator process in `src/sim_engine.py` with a 2.0 simulated-second `env.timeout()` interval.
- [X] T020 [US1] Implement Station1 and Station2 SimPy process loops in `src/sim_engine.py` using configured cycle times and Store `put()`/`get()` events.
- [X] T021 [US1] Implement `IDLE`, `BUSY`, and `BLOCKED` state transitions in `src/sim_engine.py`, including full-queue backpressure without dropping items.
- [X] T022 [US1] Implement startup configuration loading and clear failure reporting in `src/sim_engine.py` before launching any simulation worker.

**Checkpoint**: User Story 1 is independently demonstrable with a valid contract, advancing SimPy environment, bounded queue, and safe startup failures.

## Phase 4: User Story 2 - Observe Live Station And Queue Telemetry (Priority: P1)

**Goal**: Connected WebSocket clients receive validated JSON frames whenever simulation state or queue occupancy changes.

**Independent Test**: Connect a WebSocket test client to `/ws/telemetry`, collect at least 10 frames, and assert required fields, allowed states, increasing timestamps, and occupancy bounds.

### Tests for User Story 2

- [X] T023 [P] [US2] Add FastAPI WebSocket endpoint tests in `tests/test_sim_engine.py` for `/ws/telemetry` connection and initial valid frame delivery.
- [X] T024 [P] [US2] Add telemetry frame assertions in `tests/test_sim_engine.py` for exact keys, allowed state values, SimPy timestamps, and queue occupancy bounds.
- [X] T025 [P] [US2] Add a live bounded-time integration test in `tests/test_sim_engine.py` that receives at least 10 frames from a running simulation.
- [X] T026 [P] [US2] Add two-client broadcast tests in `tests/test_sim_engine.py` proving both clients receive the same state-update sequence.

### Implementation for User Story 2

- [X] T027 [US2] Implement the thread-safe telemetry event queue and simulation snapshot publishing in `src/sim_engine.py`.
- [X] T028 [US2] Implement the asyncio queue-drain task in `src/sim_engine.py` and schedule broadcast work onto the server event loop with `asyncio.run_coroutine_threadsafe` where required.
- [X] T029 [US2] Implement `/ws/telemetry` in `src/sim_engine.py` to accept clients, keep connections open, and send serialized `TelemetryFrame` JSON frames.
- [X] T030 [US2] Emit an initial valid telemetry frame and subsequent frames on station-state or queue-occupancy changes in `src/sim_engine.py`.
- [X] T031 [US2] Ensure broadcast failures remove only disconnected clients and do not stop the SimPy worker in `src/sim_engine.py`.

**Checkpoint**: User Story 2 is independently demonstrable with a live WebSocket client receiving at least 10 valid frames and multiple clients receiving the same updates.

## Phase 5: User Story 3 - Keep Simulation And Web Serving Responsive (Priority: P1)

**Goal**: Simulation runs in a daemon thread while the async web server remains responsive and all cross-thread communication uses `queue.Queue`.

**Independent Test**: Start the FastAPI app, verify the simulation worker is daemonized, make repeated HTTP/WebSocket interactions during simulation, and disconnect one client while another continues receiving frames.

### Tests for User Story 3

- [X] T032 [P] [US3] Add a worker-thread test in `tests/test_sim_engine.py` asserting SimPy runs in a daemon `threading.Thread` separate from the web server.
- [X] T033 [P] [US3] Add responsiveness coverage in `tests/test_sim_engine.py` asserting `/health` and a new WebSocket connection respond while simulation advances.
- [X] T034 [P] [US3] Add disconnect-isolation coverage in `tests/test_sim_engine.py` proving one client disconnect does not stop the worker or another client’s frames.
- [X] T035 [P] [US3] Add source-level or dependency-injection coverage in `tests/test_sim_engine.py` proving telemetry crosses via a thread-safe queue and no direct WebSocket send occurs from SimPy code.

### Implementation for User Story 3

- [X] T036 [US3] Implement the daemon simulation worker lifecycle in `src/sim_engine.py` and start it from FastAPI startup without blocking Uvicorn.
- [X] T037 [US3] Implement queue-to-asyncio notification and cancellation cleanup in `src/sim_engine.py` so shutdown does not leak worker or broadcast tasks.
- [X] T038 [US3] Add `/health` status reporting in `src/sim_engine.py` for configuration-loaded and simulation-running state without exposing mutable shared state directly.
- [X] T039 [US3] Handle simulation exceptions in `src/sim_engine.py` by recording a failure signal, stopping fabricated telemetry, and keeping failure reporting clear.

**Checkpoint**: User Story 3 is independently demonstrable through responsiveness, daemon-thread, queue-bridge, and disconnect tests.

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finish documentation, contract traceability, integration checks, and regression validation.

- [X] T040 [P] Extend `src/web/app.js` and `src/web/index.html` to show live telemetry frames from `/ws/telemetry` without changing the DTDL contract renderer.
- [X] T041 [P] Add a browser-facing telemetry status and latest-frame panel in `src/web/styles.css` and `src/web/index.html` for local evaluation.
- [X] T042 [P] Add end-to-end browser/API documentation to `README.md` and `specs/002-simpy-telemetry-server/quickstart.md`.
- [X] T043 [P] Verify the runtime imports only `simpy`, `fastapi`, `uvicorn`, `pydantic`, and standard-library concurrency primitives; no heavy agent framework is introduced.
- [X] T044 [P] Verify DTDL contract primacy and the fixed `Queue` -> `Assembly Station` -> `Packaging Station` topology in `src/sim_engine.py` and tests.
- [X] T045 Run the complete Feature 001 and Feature 002 test suites and repository diagnostics.
- [X] T046 Run the manual WebSocket quickstart with two clients, record observed frames, and document any environment-dependent limitations in `specs/002-simpy-telemetry-server/quickstart.md`.

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies. T001-T005 establish dependencies, fixtures, and test surface.
- **Foundational (Phase 2)**: Depends on Setup. T006-T011 establish contracts, ingestion, connection management, and app lifecycle; T012-T013 can run in parallel once those seams are defined.
- **User Story 1 (Phase 3)**: Depends on Foundational. It establishes valid SimPy startup and state transitions.
- **User Story 2 (Phase 4)**: Depends on Foundational and the simulation event publisher from US1; it can begin test authoring while US1 implementation stabilizes.
- **User Story 3 (Phase 5)**: Depends on the worker and WebSocket seams from US1/US2; its tests validate the constitutional boundary.
- **Polish (Phase 6)**: Depends on all desired stories being complete.

### User Story Dependencies

- **US1 (P1)**: Foundational only; independently validates contract ingestion and simulation execution.
- **US2 (P1)**: Foundational plus the simulation event source from US1; independently validates WebSocket frames with deterministic fixtures.
- **US3 (P1)**: Foundational plus the worker/broadcast lifecycle from US1 and US2; independently validates responsiveness and client isolation.

### Parallel Opportunities

- T002-T005 can run in parallel after dependencies are declared.
- T012-T013 can run in parallel after the shared models and manager names exist.
- T014-T017 can run in parallel because they cover independent startup and simulation behaviors.
- T023-T026 can run in parallel as independent WebSocket and frame assertions.
- T032-T035 can run in parallel as independent architecture and lifecycle checks.
- T040-T044 can run in parallel after the runtime contract stabilizes.

## Parallel Example: User Story 1

```text
Task T014: Add simulation startup coverage in tests/test_sim_engine.py
Task T015: Add generator cadence coverage in tests/test_sim_engine.py
Task T016: Add station processing coverage in tests/test_sim_engine.py
Task T017: Add invalid-schema startup coverage in tests/test_sim_engine.py
```

## Parallel Example: User Story 2

```text
Task T023: Add WebSocket endpoint coverage in tests/test_sim_engine.py
Task T024: Add telemetry frame contract assertions in tests/test_sim_engine.py
Task T025: Add bounded live frame integration coverage in tests/test_sim_engine.py
Task T026: Add two-client broadcast coverage in tests/test_sim_engine.py
```

## Parallel Example: User Story 3

```text
Task T032: Add daemon worker coverage in tests/test_sim_engine.py
Task T033: Add responsiveness coverage in tests/test_sim_engine.py
Task T034: Add disconnect isolation coverage in tests/test_sim_engine.py
Task T035: Add queue-bridge architecture coverage in tests/test_sim_engine.py
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 setup.
2. Complete Phase 2 contract ingestion, Pydantic models, connection manager, and FastAPI app foundation.
3. Complete Phase 3 User Story 1 to run a validated two-station SimPy simulation.
4. Complete the minimum Phase 4 WebSocket endpoint and frame stream.
5. **STOP and VALIDATE**: connect one client and confirm at least 10 valid frames.

### Incremental Delivery

1. Add multi-client broadcast and disconnect isolation from User Story 2.
2. Add daemon-thread responsiveness and failure lifecycle from User Story 3.
3. Add the existing browser telemetry panel and final documentation in Phase 6.
4. Run Feature 001 regression tests alongside Feature 002 tests.

### Definition Of Done

- Every task is checked off after implementation and focused validation.
- The engine reads only validated `assembly_line.json` configuration.
- SimPy runs in a daemon thread and communicates through `queue.Queue`.
- WebSocket frames validate against `TelemetryFrame` and contain the exact required fields.
- Multiple clients and disconnects do not interrupt simulation or remaining clients.
- Invalid startup and fatal simulation errors do not emit fabricated telemetry.
- Feature 001 and Feature 002 test suites and repository diagnostics pass.
