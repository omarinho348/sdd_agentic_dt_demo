# Implementation Plan: Interactive DTDL v3 Generator Agent

**Branch**: `001-interactive-dtdl-generator` | **Date**: 2026-09-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-interactive-dtdl-generator/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command; its definition describes the execution workflow.

## Summary

Implement a local browser application as the primary Feature 001 workflow. A small
standard-library HTTP server serves a responsive page and JSON endpoints, while the
existing `src/dtdl_generator.py` remains the contract owner for extraction, Pydantic
validation, DTDL v3 mapping, and persistence. Users enter a description in the browser,
receive missing fields as form controls rather than terminal prompts, and inspect or
download the validated three-interface model document at `assembly_line.json`.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.13+

**Primary Dependencies**: Standard library (`json`, `os`, `sys`, `pathlib`),
`python-dotenv`, `openai`, and `pydantic`; no agent framework

**Storage**: `assembly_line.json` in the current working directory, replaced only after
successful validation

**Testing**: `pytest`-style unit and CLI subprocess tests; focused Pydantic contract
validation and acceptance-path tests

**Target Platform**: Windows and other Python 3.13-compatible desktop terminals

**Project Type**: Local browser application with a Python HTTP server and compatibility CLI

**Performance Goals**: Complete local transformation and validation within 1 second after
the model response; no performance target is imposed on network latency

**Constraints**: Required CLI argument; `gpt-4o-mini` only; bounded JSON extraction;
missing values completed with `input()`; positive numeric domains; no partial output;
exactly three DTDL interfaces; Pydantic validation before persistence

**Scale/Scope**: One local browser session and one assembly-line schema per generation;
one server module, one static frontend, and a focused test suite; no simulation or
rendering loop in this feature

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- LLM and generation: all agent prompts and dynamic code generation use `gpt-4o-mini`,
  with bounded JSON output validated by Pydantic or JSON response format.
- Architecture: the design preserves `Queue` -> `Assembly Station` -> `Packaging Station`,
  uses a daemon SimPy thread, a main-thread PyOpenGL loop, and `queue.Queue` for all
  inter-thread communication.
- Contract: generated DTDL v3 is the source of truth, and validation occurs before
  writing `assembly_line.json`.
- Browser workflow: the local page owns user interaction; the server exposes only the
  extraction and validated-generation operations needed by that page.

**Gate status before Phase 0**: PASS. The feature uses the mandated model, bounded
structured extraction, standard Python/OpenAI/Pydantic dependencies, and the required
two-station contract. SimPy and PyOpenGL thread boundaries are not activated by this
CLI-only feature; any future integration must preserve those boundaries.

**Gate status after Phase 1**: PASS. The design has no heavy framework, keeps the
validated DTDL document as the sole output contract, and defines focused checks for
browser complete input, browser completion, invalid input, and persistence ordering.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
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
├── dtdl_generator.py     # CLI, extraction, completion, DTDL mapping, validation, persistence
├── web_app.py            # Local HTTP server and JSON API
└── web/
  ├── index.html        # Browser workflow
  ├── app.js            # Form state, API calls, contract rendering, download
  └── styles.css        # Responsive visual system

tests/
├── test_dtdl_generator.py
├── test_web_app.py
└── fixtures/
    └── extraction responses and expected contract samples
```

**Structure Decision**: Keep `src/dtdl_generator.py` as the domain and contract module.
Add `src/web_app.py` as a thin standard-library HTTP adapter and keep the frontend in
`src/web/` so the application can be run locally without a frontend build system or
heavy framework. Test the API with fake extraction clients and test the page as a static
asset; retain CLI regression coverage for compatibility.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | The design complies with all constitutional gates. |
