"""SimPy assembly-line simulation with a FastAPI telemetry bridge."""

from __future__ import annotations

import asyncio
import json
import math
import queue
import re
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

import simpy
import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from dtdl_generator import DTDLInterface, validate_document


HOST = "127.0.0.1"
PORT = 8000
SCHEMA_PATH = Path("assembly_line.json")
WEB_ROOT = Path(__file__).parent / "web"
State = Literal["IDLE", "BUSY", "BLOCKED"]


class AssemblyLineConfig(BaseModel):
    """Runtime settings derived only from the validated DTDL document."""

    station1_cycle_time: float = Field(gt=0)
    station2_cycle_time: float = Field(gt=0)
    queue_capacity: int = Field(gt=0)
    item_interval: float = 2.0

    @field_validator("station1_cycle_time", "station2_cycle_time", "item_interval")
    @classmethod
    def require_finite_values(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("timing values must be finite")
        return value

    @field_validator("item_interval")
    @classmethod
    def require_fixed_interval(cls, value: float) -> float:
        if value != 2.0:
            raise ValueError("item interval must be exactly 2.0 seconds")
        return value


class TelemetryFrame(BaseModel):
    """The exact JSON payload sent to telemetry clients."""

    model_config = ConfigDict(extra="forbid")

    timestamp: float = Field(ge=0)
    station1_state: State
    station2_state: State
    queue_occupancy: int = Field(ge=0)

    @field_validator("timestamp")
    @classmethod
    def require_finite_timestamp(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("timestamp must be finite")
        return value

    @model_validator(mode="after")
    def validate_capacity_from_context(self) -> TelemetryFrame:
        return self

    @classmethod
    def from_snapshot(
        cls,
        timestamp: float,
        station1_state: State,
        station2_state: State,
        queue_occupancy: int,
        queue_capacity: int,
    ) -> TelemetryFrame:
        frame = cls(
            timestamp=timestamp,
            station1_state=station1_state,
            station2_state=station2_state,
            queue_occupancy=queue_occupancy,
        )
        if queue_occupancy > queue_capacity:
            raise ValueError("queue occupancy exceeds configured capacity")
        return frame


def _description_value(description: str | None, label: str, integer: bool = False) -> float | int:
    if not description:
        raise ValueError(f"missing {label} description")
    pattern = r"([-+]?\d+(?:\.\d+)?)"
    match = re.search(pattern, description)
    if not match:
        raise ValueError(f"invalid {label} description")
    value = float(match.group(1))
    if not math.isfinite(value) or value <= 0 or (integer and not value.is_integer()):
        raise ValueError(f"invalid {label} value")
    return int(value) if integer else value


def load_config(schema_path: Path = SCHEMA_PATH) -> AssemblyLineConfig:
    """Load and validate the Feature 001 artifact before starting simulation."""

    try:
        raw = json.loads(Path(schema_path).read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("DTDl schema must be a JSON array")
        document = validate_document([DTDLInterface.model_validate(item) for item in raw])
    except (OSError, json.JSONDecodeError, TypeError, ValidationError, ValueError) as error:
        raise ValueError(f"invalid assembly-line schema: {error}") from error

    by_id = {interface.identifier: interface for interface in document}
    try:
        queue_interface = by_id["dtmi:twinIt:Queue;1"]
        station1 = by_id["dtmi:twinIt:Station1;1"]
        station2 = by_id["dtmi:twinIt:Station2;1"]
    except KeyError as error:
        raise ValueError("contract is missing a required assembly-line interface") from error

    def content(interface: DTDLInterface, name: str, schema: str) -> Any:
        matches = [item for item in interface.contents if item.name == name and item.schema_name == schema]
        if len(matches) != 1:
            raise ValueError(f"contract must contain exactly one {name} content")
        return matches[0]

    try:
        capacity_content = content(queue_interface, "capacity", "integer")
        station1_content = content(station1, "cycle_time", "double")
        station2_content = content(station2, "cycle_time", "double")
        return AssemblyLineConfig(
            queue_capacity=_description_value(capacity_content.description, "queue capacity", integer=True),
            station1_cycle_time=_description_value(station1_content.description, "station 1 cycle time"),
            station2_cycle_time=_description_value(station2_content.description, "station 2 cycle time"),
        )
    except (ValueError, ValidationError) as error:
        raise ValueError(f"invalid assembly-line schema: {error}") from error


class ConnectionManager:
    """Own the async WebSocket clients and isolate failed connections."""

    def __init__(self) -> None:
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)

    async def broadcast(self, frame: TelemetryFrame) -> None:
        payload = frame.model_dump()
        failed: list[WebSocket] = []
        for websocket in tuple(self.active_connections):
            try:
                await websocket.send_json(payload)
            except Exception:
                failed.append(websocket)
        for websocket in failed:
            self.disconnect(websocket)


class SimulationEngine:
    """Own the SimPy environment and publish immutable frames to a thread-safe queue."""

    def __init__(self, config: AssemblyLineConfig) -> None:
        self.config = config
        self.telemetry_queue: queue.Queue[TelemetryFrame] = queue.Queue()
        self.environment = simpy.Environment()
        self.inter_station_queue = simpy.Store(self.environment, capacity=config.queue_capacity)
        self.source_queue = simpy.Store(self.environment)
        self.station1_state: State = "IDLE"
        self.station2_state: State = "IDLE"
        self.failure: BaseException | None = None
        self.running = False
        self._publish()
        self.environment.process(self._generator())
        self.environment.process(self._assembly_station())
        self.environment.process(self._packaging_station())

    @property
    def latest_frame(self) -> TelemetryFrame:
        return TelemetryFrame.from_snapshot(
            self.environment.now,
            self.station1_state,
            self.station2_state,
            len(self.inter_station_queue.items),
            self.config.queue_capacity,
        )

    def _publish(self) -> None:
        self.telemetry_queue.put(self.latest_frame)

    def _set_state(self, station: int, state: State) -> None:
        if station == 1:
            self.station1_state = state
        else:
            self.station2_state = state
        self._publish()

    def _generator(self):
        item_number = 0
        while True:
            yield self.environment.timeout(self.config.item_interval)
            item_number += 1
            yield self.source_queue.put(item_number)

    def _assembly_station(self):
        while True:
            item = yield self.source_queue.get()
            self._set_state(1, "BUSY")
            yield self.environment.timeout(self.config.station1_cycle_time)
            if len(self.inter_station_queue.items) >= self.config.queue_capacity:
                self._set_state(1, "BLOCKED")
            yield self.inter_station_queue.put(item)
            self._publish()
            self._set_state(1, "IDLE")

    def _packaging_station(self):
        while True:
            item = yield self.inter_station_queue.get()
            self._publish()
            self._set_state(2, "BUSY")
            yield self.environment.timeout(self.config.station2_cycle_time)
            self._set_state(2, "IDLE")

    def run(self, until: float | None = None) -> None:
        self.running = True
        try:
            self.environment.run(until=until)
        except BaseException as error:
            self.failure = error
            self.running = False
            raise
        finally:
            if until is not None:
                self.running = False

    def start(self, on_failure: Any = None) -> threading.Thread:
        def worker_main() -> None:
            try:
                self.run()
            except BaseException as error:
                if on_failure is not None:
                    on_failure(error)

        worker = threading.Thread(target=worker_main, name="simpy-worker", daemon=True)
        worker.start()
        return worker


class AppState:
    def __init__(self, schema_path: Path) -> None:
        self.schema_path = schema_path
        self.config: AssemblyLineConfig | None = None
        self.engine: SimulationEngine | None = None
        self.manager = ConnectionManager()
        self.worker: threading.Thread | None = None
        self.drain_task: asyncio.Task[None] | None = None
        self.latest_frame: TelemetryFrame | None = None
        self.failure: BaseException | None = None
        self.start_lock: asyncio.Lock | None = None



def create_app(schema_path: Path = SCHEMA_PATH, auto_start: bool = True) -> FastAPI:
    state = AppState(Path(schema_path))

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        state.start_lock = asyncio.Lock()
        if auto_start:
            await start_simulation(state)

        async def drain_telemetry() -> None:
            while True:
                if state.engine is None:
                    await asyncio.sleep(0.05)
                    continue
                engine = state.engine
                frame = await asyncio.to_thread(engine.telemetry_queue.get)
                if engine is not state.engine:
                    continue
                state.latest_frame = frame
                await state.manager.broadcast(frame)

        state.drain_task = asyncio.create_task(drain_telemetry())
        try:
            yield
        finally:
            if state.drain_task:
                state.drain_task.cancel()
                await asyncio.gather(state.drain_task, return_exceptions=True)

    application = FastAPI(title="TwinIt Telemetry Server", lifespan=lifespan)
    application.state.runtime = state

    @application.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "failed" if state.failure else "ok",
            "configuration_loaded": state.config is not None,
            "simulation_running": bool(state.engine and state.engine.running),
        }

    @application.post("/api/extract")
    async def extract_model(request: Request) -> JSONResponse:
        from web_app import WebValidationError, extract_request

        try:
            return JSONResponse(await asyncio.to_thread(extract_request, await request.json()))
        except WebValidationError as error:
            return JSONResponse({"errors": error.errors}, status_code=422)
        except Exception as error:
            return JSONResponse({"error": str(error)}, status_code=502)

    @application.post("/api/generate")
    async def generate_model(request: Request) -> JSONResponse:
        from web_app import WebValidationError, generate_request

        try:
            result = await asyncio.to_thread(generate_request, await request.json())
            await start_simulation(state)
            return JSONResponse(result)
        except WebValidationError as error:
            return JSONResponse({"errors": error.errors}, status_code=422)
        except Exception as error:
            return JSONResponse({"error": str(error)}, status_code=502)

    @application.websocket("/ws/telemetry")
    async def telemetry(websocket: WebSocket) -> None:
        await state.manager.connect(websocket)
        try:
            if state.latest_frame is not None:
                await websocket.send_json(state.latest_frame.model_dump())
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            state.manager.disconnect(websocket)
        except Exception:
            state.manager.disconnect(websocket)

    if WEB_ROOT.is_dir():
        application.mount("/", StaticFiles(directory=WEB_ROOT, html=True), name="web")

    return application


async def start_simulation(state: AppState) -> None:
    """Load the current artifact and replace the running simulation."""

    if state.start_lock is None:
        state.start_lock = asyncio.Lock()
    async with state.start_lock:
        config = await asyncio.to_thread(load_config, state.schema_path)
        state.config = config
        state.failure = None
        state.engine = SimulationEngine(config)
        state.latest_frame = state.engine.latest_frame
        state.worker = state.engine.start(lambda error: setattr(state, "failure", error))


app = create_app()


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
