"""Generate a validated DTDL v3 assembly-line model from a natural-language prompt."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


MODEL_NAME = "gpt-4o-mini"
OUTPUT_PATH = Path("assembly_line.json")
PARAMETER_FIELDS = (
    "station1_name",
    "station1_cycle_time",
    "station2_name",
    "station2_cycle_time",
    "queue_capacity",
)


class AssemblyLineParameters(BaseModel):
    """Input parameters, allowing nulls while model extraction is incomplete."""

    station1_name: str | None = None
    station1_cycle_time: float | None = None
    station2_name: str | None = None
    station2_cycle_time: float | None = None
    queue_capacity: int | None = None

    @field_validator("station1_name", "station2_name")
    @classmethod
    def validate_station_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("station name must not be blank")
        return value

    @field_validator("station1_cycle_time", "station2_cycle_time")
    @classmethod
    def validate_cycle_time(cls, value: float | None) -> float | None:
        if value is not None and value <= 0:
            raise ValueError("cycle time must be greater than zero")
        return value

    @field_validator("queue_capacity")
    @classmethod
    def validate_queue_capacity(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("queue capacity must be greater than zero")
        return value


class DTDLContent(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    content_type: Literal["Property", "Telemetry"] = Field(alias="@type")
    name: Literal["capacity", "occupancy", "cycle_time", "state"]
    schema_name: Literal["integer", "double", "string"] = Field(alias="schema")
    description: str | None = None


class DTDLInterface(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    context: Literal["dtmi:dtdl:context;3"] = Field(alias="@context")
    identifier: str = Field(alias="@id", min_length=1)
    interface_type: Literal["Interface"] = Field(alias="@type")
    display_name: str = Field(alias="displayName", min_length=1)
    contents: list[DTDLContent] = Field(min_length=2)


class ExtractionError(RuntimeError):
    """Raised when the model response cannot be interpreted as an object."""


def _extraction_prompt(description: str) -> str:
    return (
        "Extract assembly-line parameters from the user description. Return only a JSON object "
        "with these keys: station1_name, station1_cycle_time, station2_name, "
        "station2_cycle_time, queue_capacity. Use null when a value is absent. "
        f"User description: {description}"
    )


def extract_parameters(description: str, client: OpenAI | None = None) -> AssemblyLineParameters:
    """Extract parameters with bounded JSON, treating invalid fields as missing."""

    load_dotenv()
    client = client or OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": "You extract only assembly-line parameters and return a JSON object.",
            },
            {"role": "user", "content": _extraction_prompt(description)},
        ],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    try:
        raw = json.loads(content or "")
    except (TypeError, json.JSONDecodeError) as error:
        raise ExtractionError("Model response was not valid JSON") from error
    if not isinstance(raw, dict):
        raise ExtractionError("Model response must be a JSON object")

    normalized: dict[str, Any] = {}
    for field_name in PARAMETER_FIELDS:
        value = raw.get(field_name)
        if value is None:
            normalized[field_name] = None
            continue
        try:
            normalized[field_name] = AssemblyLineParameters.model_validate(
                {field_name: value}
            ).model_dump()[field_name]
        except ValidationError:
            normalized[field_name] = None
    return AssemblyLineParameters.model_validate(normalized)


def missing_fields(parameters: AssemblyLineParameters) -> list[str]:
    """Return unresolved fields in the stable CLI prompt order."""

    return [
        field_name
        for field_name in PARAMETER_FIELDS
        if getattr(parameters, field_name) is None
    ]


def complete_parameters(
    parameters: AssemblyLineParameters,
    input_function: Any = input,
) -> AssemblyLineParameters:
    """Prompt until all missing fields have valid values."""

    prompts = {
        "station1_name": "[Missing Parameter] Enter name for Assembly Station: ",
        "station1_cycle_time": "[Missing Parameter] Enter cycle time for Assembly Station (seconds): ",
        "station2_name": "[Missing Parameter] Enter name for Packaging Station: ",
        "station2_cycle_time": "[Missing Parameter] Enter cycle time for Packaging Station (seconds): ",
        "queue_capacity": "[Missing Parameter] Enter queue capacity (items): ",
    }
    for field_name in missing_fields(parameters):
        while getattr(parameters, field_name) is None:
            raw_value = input_function(prompts[field_name]).strip()
            try:
                value: Any = raw_value
                if field_name.endswith("cycle_time"):
                    value = float(raw_value)
                elif field_name == "queue_capacity":
                    value = int(raw_value)
                candidate = parameters.model_copy(update={field_name: value})
                candidate = AssemblyLineParameters.model_validate(candidate.model_dump())
            except (ValueError, ValidationError):
                print(
                    f"[Invalid Parameter] Enter a valid value for {field_name}.",
                    file=sys.stderr,
                )
                continue
            setattr(parameters, field_name, getattr(candidate, field_name))
    return parameters


def build_dtdl_document(parameters: AssemblyLineParameters) -> list[DTDLInterface]:
    """Map complete parameters to the stable three-interface DTDL document."""

    complete = AssemblyLineParameters.model_validate(parameters.model_dump())
    if missing_fields(complete):
        raise ValueError("all assembly-line parameters are required")

    return [
        DTDLInterface(
            **{
                "@context": "dtmi:dtdl:context;3",
                "@id": "dtmi:twinIt:Queue;1",
                "@type": "Interface",
                "displayName": "Queue",
                "contents": [
                    {
                        "@type": "Property",
                        "name": "capacity",
                        "schema": "integer",
                        "description": f"Queue capacity: {complete.queue_capacity} items",
                    },
                    {
                        "@type": "Telemetry",
                        "name": "occupancy",
                        "schema": "integer",
                    },
                ],
            }
        ),
        _station_interface(
            identifier="dtmi:twinIt:Station1;1",
            display_name=complete.station1_name,
            cycle_time=complete.station1_cycle_time,
        ),
        _station_interface(
            identifier="dtmi:twinIt:Station2;1",
            display_name=complete.station2_name,
            cycle_time=complete.station2_cycle_time,
        ),
    ]


def _station_interface(
    identifier: str,
    display_name: str,
    cycle_time: float,
) -> DTDLInterface:
    return DTDLInterface(
        **{
            "@context": "dtmi:dtdl:context;3",
            "@id": identifier,
            "@type": "Interface",
            "displayName": display_name,
            "contents": [
                {
                    "@type": "Property",
                    "name": "cycle_time",
                    "schema": "double",
                    "description": f"Cycle time: {cycle_time} seconds",
                },
                {"@type": "Telemetry", "name": "state", "schema": "string"},
            ],
        }
    )


def validate_document(document: list[DTDLInterface]) -> list[DTDLInterface]:
    """Validate the exact interface count and required stable IDs."""

    if len(document) != 3:
        raise ValueError("assembly-line document must contain exactly three interfaces")
    validated = [DTDLInterface.model_validate(item) for item in document]
    expected_ids = [
        "dtmi:twinIt:Queue;1",
        "dtmi:twinIt:Station1;1",
        "dtmi:twinIt:Station2;1",
    ]
    if [item.identifier for item in validated] != expected_ids:
        raise ValueError("assembly-line interfaces have unexpected IDs or order")
    return validated


def persist_document(document: list[DTDLInterface], output_path: Path = OUTPUT_PATH) -> None:
    """Validate, serialize, and atomically replace the output artifact."""

    validated = validate_document(document)
    payload = [item.model_dump(by_alias=True, exclude_none=True) for item in validated]
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(payload, temporary_file, indent=2)
            temporary_file.write("\n")
        os.replace(temporary_path, output_path)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


def run(description: str, client: OpenAI | None = None, output_path: Path = OUTPUT_PATH) -> None:
    parameters = extract_parameters(description, client=client)
    complete_parameters(parameters)
    persist_document(build_dtdl_document(parameters), output_path=output_path)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or not args[0].strip():
        print(
            'Usage: python src/dtdl_generator.py "<assembly-line description>"',
            file=sys.stderr,
        )
        return 2
    try:
        run(args[0])
    except (ExtractionError, OSError, OpenAIError, ValidationError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(f"Saved validated DTDL schema to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())