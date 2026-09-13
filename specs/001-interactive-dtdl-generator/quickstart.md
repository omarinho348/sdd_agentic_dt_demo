# Quickstart: Interactive DTDL v3 Generator Agent

## Prerequisites

- Python 3.13 or newer
- Project dependencies installed from `pyproject.toml`
- An OpenAI API key available to the OpenAI SDK, typically through `.env`

## Setup

From the repository root:

```powershell
uv sync
$env:OPENAI_API_KEY = "<your-key>"
```

## Complete input validation

```powershell
python src/dtdl_generator.py "Assembly line with station1 cycle time 5s, station2 cycle time 8s, and queue size 3"
```

Expected result: the command exits successfully without missing-parameter prompts and creates `assembly_line.json` containing exactly Queue, Station1, and Station2 interfaces.

## Partial input validation

```powershell
"2.5`n3.0`n3" | python src/dtdl_generator.py "Create a line with assembly and packaging stations."
```

Expected result: the command prompts for the missing station cycle times and queue capacity, then writes a validated schema after the supplied values are accepted.

## Contract validation

Inspect `assembly_line.json` and confirm:

- The root is an array of three interfaces.
- Every interface has DTDL v3 context, a unique ID, `@type` `Interface`, and `contents`.
- Queue contains `capacity` and `occupancy`.
- Both stations contain `cycle_time` and `state`.
- The file exists only after Pydantic validation succeeds.

## Negative-path validation

Provide `0`, a negative value, text, or blank input at a numeric prompt. The command must reject the answer, prompt again, and avoid persisting an invalid contract.
