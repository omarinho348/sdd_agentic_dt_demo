# TwinIt Interactive DTDL Generator

Generate a validated DTDL v3 assembly-line model from a browser page. TwinIt uses
`gpt-4o-mini` for bounded JSON extraction, asks for missing values in a form, and writes
`assembly_line.json` only after Pydantic validation succeeds. The original CLI remains
available for compatibility.

## Setup

```powershell
uv sync --group dev
```

Create a file named `.env` in the repository root, next to `pyproject.toml`:

```text
C:\Users\ok\sdd_agentic_dt_demo\
├── .env                  # your local secret, never commit this file
├── .env.example          # safe template
├── pyproject.toml
├── src\
│   └── dtdl_generator.py
└── assembly_line.json    # generated output, ignored by Git
```

Copy [.env.example](.env.example) to `.env`, then replace the placeholder value:

```text
OPENAI_API_KEY=replace-with-your-real-key
```

Do not add quotes, commit the file, or paste the key into Python source. The generator
loads this variable automatically through `python-dotenv`.

## Generate a schema

Start the local browser app from the repository root:

```powershell
uv run python src/web_app.py
```

Open <http://127.0.0.1:8000> in your browser. Enter a complete description, or click
**Use a sample** to try the missing-field flow. The page shows the validated Queue and
station interfaces and lets you download the JSON result. Press `Ctrl+C` in the
terminal to stop the server.

### Compatibility CLI

Complete input runs without missing-parameter prompts:

```powershell
python src/dtdl_generator.py "Assembly line with station1 cycle time 5s, station2 cycle time 8s, and queue size 3"
```

Partial descriptions prompt for missing station names, cycle times in seconds, and
queue capacity in items. Invalid or non-positive answers are rejected and retried.

The output contains exactly three DTDL v3 interfaces: `Queue`, `Station1`, and
`Station2`. Queue defines `capacity` and `occupancy`; each station defines `cycle_time`
and `state`.

## Test

```powershell
uv run pytest -q
```

See [the feature quickstart](specs/001-interactive-dtdl-generator/quickstart.md) for
complete, partial, and negative-path examples.
