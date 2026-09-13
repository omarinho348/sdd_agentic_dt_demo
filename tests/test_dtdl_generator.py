import json
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from dtdl_generator import (
    AssemblyLineParameters,
    DTDLContent,
    DTDLInterface,
    build_dtdl_document,
    complete_parameters,
    extract_parameters,
    main,
    persist_document,
)


class FakeMessage:
    def __init__(self, content: str):
        self.content = content


class FakeCompletion:
    def __init__(self, content: str):
        self.choices = [type("Choice", (), {"message": FakeMessage(content)})()]


class FakeCompletions:
    def __init__(self, content: str):
        self.content = content
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return FakeCompletion(self.content)


class FakeClient:
    def __init__(self, content: str):
        self.completions = FakeCompletions(content)
        self.chat = type("Chat", (), {"completions": self.completions})()


def test_parameters_allow_missing_extraction_values():
    parameters = AssemblyLineParameters(
        station1_name=None,
        station1_cycle_time=None,
        station2_name=None,
        station2_cycle_time=None,
        queue_capacity=None,
    )

    assert parameters.station1_name is None
    assert parameters.queue_capacity is None


@pytest.mark.parametrize(
    "field, value",
    [
        ("station1_cycle_time", 0),
        ("station1_cycle_time", -1),
        ("station2_cycle_time", 0),
        ("queue_capacity", 0),
    ],
)
def test_parameters_reject_non_positive_values(field, value):
    values = {
        "station1_name": "Assembly",
        "station1_cycle_time": 5.0,
        "station2_name": "Packaging",
        "station2_cycle_time": 8.0,
        "queue_capacity": 3,
        field: value,
    }

    with pytest.raises(ValidationError):
        AssemblyLineParameters(**values)


def test_dtdl_interface_validates_required_shape():
    interface = DTDLInterface(
        **{
            "@context": "dtmi:dtdl:context;3",
            "@id": "dtmi:twinIt:Queue;1",
            "@type": "Interface",
            "displayName": "Queue",
            "contents": [
                DTDLContent(
                    **{
                        "@type": "Property",
                        "name": "capacity",
                        "schema": "integer",
                    }
                ),
                DTDLContent(
                    **{
                        "@type": "Telemetry",
                        "name": "occupancy",
                        "schema": "integer",
                    }
                ),
            ],
        }
    )

    assert interface.model_dump(by_alias=True)["@type"] == "Interface"


def test_extraction_uses_bounded_json_and_fixture_response():
    response = Path(__file__).parent.joinpath("fixtures", "extraction_response.json").read_text()
    client = FakeClient(response)

    parameters = extract_parameters("complete line", client=client)

    assert parameters.station1_cycle_time == 5.0
    assert client.completions.kwargs["model"] == "gpt-4o-mini"
    assert client.completions.kwargs["response_format"] == {"type": "json_object"}


def test_complete_input_builds_three_interfaces_without_prompting(tmp_path, monkeypatch):
    parameters = AssemblyLineParameters(
        station1_name="Assembly Station",
        station1_cycle_time=5.0,
        station2_name="Packaging Station",
        station2_cycle_time=8.0,
        queue_capacity=3,
    )
    document = build_dtdl_document(parameters)
    output_path = tmp_path / "assembly_line.json"
    prompt_calls = []

    monkeypatch.setattr("builtins.input", lambda prompt: prompt_calls.append(prompt))
    persist_document(document, output_path=output_path)
    payload = json.loads(output_path.read_text())

    assert prompt_calls == []
    assert [item["displayName"] for item in payload] == [
        "Queue",
        "Assembly Station",
        "Packaging Station",
    ]
    assert payload[0]["contents"][0]["description"] == "Queue capacity: 3 items"


def test_partial_input_prompts_in_stable_order_and_retries_invalid_values(capsys):
    parameters = AssemblyLineParameters()
    answers = iter(["Assembly Station", "0", "5", "Packaging Station", "-1", "8", "3"])

    complete_parameters(parameters, input_function=lambda prompt: next(answers))

    assert parameters.model_dump() == {
        "station1_name": "Assembly Station",
        "station1_cycle_time": 5.0,
        "station2_name": "Packaging Station",
        "station2_cycle_time": 8.0,
        "queue_capacity": 3,
    }
    error_output = capsys.readouterr().err
    assert "station1_cycle_time" in error_output
    assert "station2_cycle_time" in error_output


def test_missing_argument_returns_usage_error_without_writing(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    result = main([])

    assert result == 2
    assert not (tmp_path / "assembly_line.json").exists()
    assert "Usage:" in capsys.readouterr().err


def test_persist_rejects_invalid_document_without_replacing_existing_artifact(tmp_path):
    output_path = tmp_path / "assembly_line.json"
    output_path.write_text('{"existing": true}\n')

    with pytest.raises(ValueError):
        persist_document([], output_path=output_path)

    assert output_path.read_text() == '{"existing": true}\n'


def test_contract_contains_required_queue_and_station_contents():
    parameters = AssemblyLineParameters(
        station1_name="Assembly",
        station1_cycle_time=5,
        station2_name="Packaging",
        station2_cycle_time=8,
        queue_capacity=3,
    )

    payload = [item.model_dump(by_alias=True, exclude_none=True) for item in build_dtdl_document(parameters)]

    assert len(payload) == 3
    assert {(content["@type"], content["name"]) for content in payload[0]["contents"]} == {
        ("Property", "capacity"),
        ("Telemetry", "occupancy"),
    }
    for station in payload[1:]:
        assert {(content["@type"], content["name"]) for content in station["contents"]} == {
            ("Property", "cycle_time"),
            ("Telemetry", "state"),
        }