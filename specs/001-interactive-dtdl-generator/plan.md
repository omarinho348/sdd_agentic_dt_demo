# Implementation Plan: Interactive DTDL v3 Generator Agent

**Branch**: `001-interactive-dtdl-generator` | **Date**: 2026-09-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-interactive-dtdl-generator/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command; its definition describes the execution workflow.

## Summary

Implement a single-file Python CLI at `src/dtdl_generator.py` that accepts one required
plain-English assembly-line description, extracts the five assembly-line parameters with
`gpt-4o-mini`, interactively completes missing values, and emits a Pydantic-validated
DTDL v3 model document at `assembly_line.json`. The output contains exactly three
interfaces, Queue, Station1, and Station2, with stable IDs and interface-local
`contents` arrays for properties and telemetry. The module defines the Pydantic
`AssemblyLineParameters` input model and `DTDLInterface` output model, along with the
nested content model needed to validate properties and telemetry.

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

**Project Type**: CLI application with importable validation and serialization helpers

**Performance Goals**: Complete local transformation and validation within 1 second after
the model response; no performance target is imposed on network latency

**Constraints**: Required CLI argument; `gpt-4o-mini` only; bounded JSON extraction;
missing values completed with `input()`; positive numeric domains; no partial output;
exactly three DTDL interfaces; Pydantic validation before persistence

**Scale/Scope**: One assembly-line schema per CLI invocation; one source module and a
focused test suite; no simulation or rendering loop in this feature

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- LLM and generation: all agent prompts and dynamic code generation use `gpt-4o-mini`,
  with bounded JSON output validated by Pydantic or JSON response format.
- Architecture: the design preserves `Queue` -> `Assembly Station` -> `Packaging Station`,
  uses a daemon SimPy thread, a main-thread PyOpenGL loop, and `queue.Queue` for all
  inter-thread communication.
- Contract: generated DTDL v3 is the source of truth, and validation occurs before
  writing `assembly_line.json`.

**Gate status before Phase 0**: PASS. The feature uses the mandated model, bounded
structured extraction, standard Python/OpenAI/Pydantic dependencies, and the required
two-station contract. SimPy and PyOpenGL thread boundaries are not activated by this
CLI-only feature; any future integration must preserve those boundaries.

**Gate status after Phase 1**: PASS. The design has no heavy framework, keeps the
validated DTDL document as the sole output contract, and defines focused checks for
complete input, interactive completion, invalid input, and persistence ordering.

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
└── dtdl_generator.py    # CLI, extraction, completion, DTDL mapping, validation, persistence

tests/
├── test_dtdl_generator.py
└── fixtures/
  └── extraction responses and expected contract samples
```

**Structure Decision**: Keep the implementation in the requested `src/dtdl_generator.py`
module because the feature is a focused CLI rather than a multi-service application.
Expose small importable functions for extraction, completion, DTDL construction, and
persistence so unit tests can stub OpenAI responses and test validation without network
access. Keep end-to-end CLI tests in `tests/test_dtdl_generator.py` and assert the
artifact contract from `assembly_line.json`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | The design complies with all constitutional gates. |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
