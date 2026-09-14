import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from sim_engine import (  # noqa: E402
    AssemblyLineConfig,
    ConnectionManager,
    SimulationEngine,
    TelemetryFrame,
    create_app,
    load_config,
)


FIXTURES = Path(__file__).parent / "fixtures"


def test_config_and_frame_contracts_validate_values():
    config = AssemblyLineConfig(
        station1_cycle_time=1,
        station2_cycle_time=2,
        queue_capacity=2,
    )
    assert config.item_interval == 2.0
    frame = TelemetryFrame.from_snapshot(0, "IDLE", "IDLE", 2, config.queue_capacity)
    assert set(frame.model_dump()) == {
        "timestamp",
        "station1_state",
        "station2_state",
        "queue_occupancy",
    }
    with pytest.raises(ValidationError):
        AssemblyLineConfig(station1_cycle_time=0, station2_cycle_time=2, queue_capacity=2)
    with pytest.raises(ValueError):
        TelemetryFrame.from_snapshot(0, "IDLE", "IDLE", 3, config.queue_capacity)


@pytest.mark.parametrize(
    "fixture_name",
    ["missing_schema.json", "malformed_schema.json", "wrong_count_schema.json", "invalid_value_schema.json"],
)
def test_invalid_schema_fails_before_simulation(fixture_name):
    with pytest.raises(ValueError, match="invalid assembly-line schema"):
        load_config(FIXTURES / fixture_name)


def test_valid_schema_is_the_runtime_configuration_source():
    config = load_config(FIXTURES / "assembly_line.json")
    assert config.model_dump() == {
        "station1_cycle_time": 1.0,
        "station2_cycle_time": 2.0,
        "queue_capacity": 2,
        "item_interval": 2.0,
    }


def test_simulation_publishes_cadence_station_flow_and_bounded_queue():
    engine = SimulationEngine(load_config(FIXTURES / "assembly_line.json"))
    engine.run(until=12)
    frames = []
    while not engine.telemetry_queue.empty():
        frames.append(engine.telemetry_queue.get_nowait())

    assert frames[0].timestamp == 0
    assert any(frame.timestamp == 2 for frame in frames)
    assert any(frame.station1_state == "BUSY" for frame in frames)
    assert any(frame.station2_state == "BUSY" for frame in frames)
    assert all(0 <= frame.queue_occupancy <= 2 for frame in frames)
    assert [frame.timestamp for frame in frames] == sorted(frame.timestamp for frame in frames)


def test_worker_is_a_daemon_thread():
    engine = SimulationEngine(load_config(FIXTURES / "assembly_line.json"))
    worker = engine.start()
    assert worker.daemon
    assert worker.name == "simpy-worker"


def test_connection_manager_broadcast_and_disconnect_isolation():
    async def scenario():
        manager = ConnectionManager()
        first = AsyncMock()
        second = AsyncMock()
        failed = AsyncMock()
        failed.send_json.side_effect = RuntimeError("gone")
        manager.active_connections.update({first, second, failed})
        frame = TelemetryFrame(timestamp=1, station1_state="BUSY", station2_state="IDLE", queue_occupancy=0)

        await manager.broadcast(frame)
        assert manager.active_connections == {first, second}
        assert first.send_json.await_count == 1
        assert second.send_json.await_count == 1
        manager.disconnect(first)
        assert manager.active_connections == {second}

    asyncio.run(scenario())


def test_health_and_websocket_frames_are_live():
    app = create_app(FIXTURES / "assembly_line.json")
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["configuration_loaded"] is True
        with client.websocket_connect("/ws/telemetry") as websocket:
            frames = [websocket.receive_json() for _ in range(10)]

    assert all(set(frame) == {"timestamp", "station1_state", "station2_state", "queue_occupancy"} for frame in frames)
    assert all(frame["station1_state"] in {"IDLE", "BUSY", "BLOCKED"} for frame in frames)
    assert all(frame["station2_state"] in {"IDLE", "BUSY", "BLOCKED"} for frame in frames)
    assert all(0 <= frame["queue_occupancy"] <= 2 for frame in frames)
    assert [frame["timestamp"] for frame in frames] == sorted(frame["timestamp"] for frame in frames)


def test_two_clients_receive_broadcasts_and_one_can_disconnect():
    app = create_app(FIXTURES / "assembly_line.json")
    with TestClient(app) as client:
        with client.websocket_connect("/ws/telemetry") as first:
            initial_first = first.receive_json()
            with client.websocket_connect("/ws/telemetry") as second:
                initial_second = second.receive_json()
                assert initial_first.keys() == initial_second.keys()
                assert first.receive_json().keys() == second.receive_json().keys()
            assert first.receive_json().keys() == initial_first.keys()


def test_app_fails_startup_for_missing_schema():
    with pytest.raises(Exception, match="invalid assembly-line schema"):
        with TestClient(create_app(FIXTURES / "missing_schema.json")):
            pass


def test_browser_app_waits_for_generation_then_starts_that_model(tmp_path):
    schema_path = tmp_path / "assembly_line.json"
    app = create_app(schema_path, auto_start=False)
    payload = {
        "parameters": {
            "station1_name": "Assembly Station",
            "station1_cycle_time": 1,
            "station2_name": "Packaging Station",
            "station2_cycle_time": 2,
            "queue_capacity": 2,
        }
    }

    with TestClient(app) as client:
        assert client.get("/health").json()["simulation_running"] is False
        response = client.post("/api/generate", json=payload)
        assert response.status_code == 200
        with client.websocket_connect("/ws/telemetry") as websocket:
            frame = websocket.receive_json()

    assert frame["timestamp"] >= 0
    assert frame["queue_occupancy"] <= 2
