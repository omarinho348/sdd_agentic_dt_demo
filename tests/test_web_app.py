import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from web_app import WebValidationError, extract_request, generate_request  # noqa: E402


class FakeMessage:
    def __init__(self, content: str):
        self.content = content


class FakeCompletions:
    def __init__(self, completion):
        self.completion = completion

    def create(self, **kwargs):
        return self.completion


class FakeClient:
    def __init__(self, content: str):
        message = FakeMessage(content)
        completion = type("Completion", (), {"choices": [type("Choice", (), {"message": message})()]})()
        self.chat = type("Chat", (), {"completions": FakeCompletions(completion)})()


def complete_client():
    return FakeClient(
        json.dumps(
            {
                "station1_name": "Assembly Station",
                "station1_cycle_time": 5,
                "station2_name": "Packaging Station",
                "station2_cycle_time": 8,
                "queue_capacity": 3,
            }
        )
    )


def test_extract_request_returns_parameters_and_no_missing_fields():
    result = extract_request({"description": "complete line"}, client=complete_client())

    assert result["missing_fields"] == []
    assert result["parameters"]["queue_capacity"] == 3


def test_extract_request_returns_missing_fields_for_partial_model():
    client = FakeClient(
        json.dumps(
            {
                "station1_name": "Assembly Station",
                "station2_name": "Packaging Station",
                "station1_cycle_time": None,
                "station2_cycle_time": None,
                "queue_capacity": None,
            }
        )
    )

    result = extract_request({"description": "partial line"}, client=client)

    assert result["missing_fields"] == [
        "station1_cycle_time",
        "station2_cycle_time",
        "queue_capacity",
    ]


def test_generate_request_persists_valid_contract_for_browser(tmp_path):
    result = generate_request(
        {
            "parameters": {
                "station1_name": "Assembly Station",
                "station1_cycle_time": "5",
                "station2_name": "Packaging Station",
                "station2_cycle_time": "8",
                "queue_capacity": "3",
            }
        },
        output_path=tmp_path / "assembly_line.json",
    )

    assert result["download_name"] == "assembly_line.json"
    assert len(result["document"]) == 3
    assert (tmp_path / "assembly_line.json").exists()


def test_generate_request_returns_field_errors_for_missing_or_invalid_values(tmp_path):
    with pytest.raises(WebValidationError) as error:
        generate_request(
            {
                "parameters": {
                    "station1_name": "Assembly Station",
                    "station1_cycle_time": "0",
                    "station2_name": "Packaging Station",
                    "station2_cycle_time": None,
                    "queue_capacity": 3,
                }
            },
            output_path=tmp_path / "assembly_line.json",
        )

    fields = {item["field"] for item in error.value.errors}
    assert fields == {"station1_cycle_time"}
    assert not (tmp_path / "assembly_line.json").exists()

    with pytest.raises(WebValidationError) as missing_error:
        generate_request(
            {
                "parameters": {
                    "station1_name": "Assembly Station",
                    "station1_cycle_time": 5,
                    "station2_name": "Packaging Station",
                    "station2_cycle_time": None,
                    "queue_capacity": 3,
                }
            },
            output_path=tmp_path / "assembly_line.json",
        )
    assert {item["field"] for item in missing_error.value.errors} == {"station2_cycle_time"}


def test_extract_request_rejects_blank_description():
    with pytest.raises(WebValidationError) as error:
        extract_request({"description": "  "})

    assert error.value.errors == [{"field": "description", "message": "Enter a description."}]
