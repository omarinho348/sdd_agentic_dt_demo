# Tasks: Interactive DTDL v3 Generator Agent

**Input**: Design documents from `/specs/001-interactive-dtdl-generator/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Included because the specification defines acceptance scenarios and the plan requires focused unit, CLI, and contract validation coverage.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently after foundational setup.

**Current delivery target**: The local browser workflow is the primary acceptance surface. The existing CLI remains a compatibility path.

## Phase 7: Browser Workflow Revision

**Purpose**: Replace terminal-only completion with an easy-to-test local webpage while reusing the validated generator contract.

- [X] T041 Update `specs/001-interactive-dtdl-generator/spec.md`, `plan.md`, and `tasks.md` so the browser workflow is the primary acceptance surface.
- [X] T042 Add a JSON API adapter in `src/web_app.py` for extraction, missing-field responses, validated generation, and JSON download.
- [X] T043 Add the browser page in `src/web/index.html` with description input, missing-field form state, generate action, status feedback, contract summary, and download action.
- [X] T044 [P] Add responsive visual styling in `src/web/styles.css` for a clear local evaluation workspace on desktop and mobile.
- [X] T045 [P] Add browser state and API interaction logic in `src/web/app.js`, including field-level validation errors and contract rendering.
- [X] T046 Add `serve` entry point and document `uv run python src/web_app.py` in `README.md` and `specs/001-interactive-dtdl-generator/quickstart.md`.
- [X] T047 [P] Add API tests in `tests/test_web_app.py` using a fake extraction client; cover complete generation, missing fields, invalid completion values, and download output.
- [X] T048 Run browser workflow checks, full regression tests, and mark all Feature 001 tasks complete.

## Phase 1: Setup

**Purpose**: Establish the CLI module and focused test structure described by the implementation plan.

- [X] T001 Create the requested CLI module at `src/dtdl_generator.py` with an importable entry point and no unrelated application changes.
- [X] T002 [P] Create the focused test module at `tests/test_dtdl_generator.py` and fixture directory at `tests/fixtures/`.
- [X] T003 [P] Add or confirm the test runner dependency and test command configuration in `pyproject.toml`.
- [X] T004 [P] Document CLI setup, environment variables, and acceptance commands in `README.md` using `specs/001-interactive-dtdl-generator/quickstart.md` as the source.

## Phase 2: Foundational

**Purpose**: Build the shared validation, OpenAI boundary, and persistence primitives required by every user story.

**Checkpoint**: Foundation is ready when extraction can be stubbed, completed parameters can be validated, DTDL payloads can be validated, and persistence cannot write an invalid payload.

- [X] T005 Define `AssemblyLineParameters` in `src/dtdl_generator.py` with optional extraction fields and positive-value validation for `station1_cycle_time`, `station2_cycle_time`, and `queue_capacity`.
- [X] T006 Define `DTDLContent` and `DTDLInterface` Pydantic models in `src/dtdl_generator.py` for DTDL v3 `Property` and `Telemetry` contents and `Interface` records.
- [X] T007 Implement the `gpt-4o-mini` extraction function in `src/dtdl_generator.py` using the OpenAI SDK, a dense bounded prompt, and `response_format={"type": "json_object"}`.
- [X] T008 Implement parameter validation and missing-field detection in `src/dtdl_generator.py`, including trimmed non-empty station names and positive numeric constraints.
- [X] T009 Implement DTDL payload validation and atomic persistence helpers in `src/dtdl_generator.py`, ensuring Pydantic validation succeeds before replacing `assembly_line.json`.
- [X] T010 [P] Add unit tests for the input and DTDL Pydantic models in `tests/test_dtdl_generator.py`, including null extraction fields and invalid non-positive values.
- [X] T011 [P] Add a stubbed OpenAI response fixture and extraction-boundary tests in `tests/fixtures/extraction_response.json` and `tests/test_dtdl_generator.py`.

## Phase 3: User Story 1 - Generate A Schema From Complete Input (Priority: P1)

**Goal**: A complete plain-English command-line argument produces a validated `assembly_line.json` without missing-parameter prompts.

**Independent Test**: Stub the extraction response for `Assembly line with station1 cycle time 5s, station2 cycle time 8s, and queue size 3`, run the CLI or its entry point, and verify no missing prompt is emitted and the output artifact is valid.

### Tests for User Story 1

- [X] T012 [P] [US1] Add a complete-input acceptance test in `tests/test_dtdl_generator.py` that supplies the required command-line argument and stubs `gpt-4o-mini` extraction.
- [X] T013 [P] [US1] Assert in `tests/test_dtdl_generator.py` that complete input does not call `input()` and writes `assembly_line.json` with the extracted values.

### Implementation for User Story 1

- [X] T014 [US1] Implement required command-line argument parsing in `src/dtdl_generator.py` and return a non-zero usage error without modifying `assembly_line.json` when the argument is absent.
- [X] T015 [US1] Implement the complete-input execution path in `src/dtdl_generator.py` from extraction through validation, DTDL mapping, and persistence without prompting.
- [X] T016 [US1] Preserve custom station names and extracted cycle times and queue capacity in the generated interface display names and contract values in `src/dtdl_generator.py`.
- [X] T017 [US1] Add the complete-input CLI command and expected no-prompt result to `specs/001-interactive-dtdl-generator/quickstart.md`.

**Checkpoint**: User Story 1 is independently demonstrable with a complete command-line description and no interactive parameter prompts.

## Phase 4: User Story 2 - Complete Missing Parameters Interactively (Priority: P1)

**Goal**: A partial description prompts for only unresolved values, rejects invalid answers, and saves after valid completion.

**Independent Test**: Use `Create a line with assembly and packaging stations.`, provide valid answers through mocked `input()` calls, and verify prompts, values, and saved output.

### Tests for User Story 2

- [X] T018 [P] [US2] Add a partial-input acceptance test in `tests/test_dtdl_generator.py` that stubs missing extraction fields and supplies valid `input()` answers.
- [X] T019 [P] [US2] Add invalid-answer tests in `tests/test_dtdl_generator.py` for blank names, non-numeric values, zero, and negative numeric values, asserting retry prompts and no invalid persistence.
- [X] T020 [P] [US2] Add a missing-argument and extraction-failure test in `tests/test_dtdl_generator.py` that asserts a non-zero result and no newly written invalid artifact.

### Implementation for User Story 2

- [X] T021 [US2] Implement stable missing-field prompt order and targeted stdout questions in `src/dtdl_generator.py` for station names, cycle times in seconds, and queue capacity in items.
- [X] T022 [US2] Implement `input()` parsing and retry behavior in `src/dtdl_generator.py`, updating `AssemblyLineParameters` only after each answer passes its field validation.
- [X] T023 [US2] Implement extraction, input, and validation error reporting to stderr and non-zero CLI exits in `src/dtdl_generator.py` without writing partial output.
- [X] T024 [US2] Preserve an existing valid `assembly_line.json` when a subsequent run fails before successful validation in `src/dtdl_generator.py`.
- [X] T025 [US2] Add the partial-input and invalid-answer procedures to `specs/001-interactive-dtdl-generator/quickstart.md`.

**Checkpoint**: User Story 2 is independently demonstrable with partial input, targeted prompts, retries, and safe failure behavior.

## Phase 5: User Story 3 - Inspect A Contract-Ready DTDL Schema (Priority: P1)

**Goal**: Every successful run produces exactly three DTDL v3 interfaces with the required contents and stable IDs.

**Independent Test**: Validate a generated `assembly_line.json` through the Pydantic output models and assert the exact Queue, Station1, and Station2 content contract.

### Tests for User Story 3

- [X] T026 [P] [US3] Add a DTDL contract test in `tests/test_dtdl_generator.py` asserting the root array contains exactly Queue, Station1, and Station2 interfaces.
- [X] T027 [P] [US3] Add content assertions in `tests/test_dtdl_generator.py` for Queue `capacity` Property and `occupancy` Telemetry.
- [X] T028 [P] [US3] Add content assertions in `tests/test_dtdl_generator.py` for each station `cycle_time` Property and `state` Telemetry, including `double` and `string` schemas.
- [X] T029 [P] [US3] Add a persistence-order test in `tests/test_dtdl_generator.py` proving invalid DTDL payloads do not replace an existing artifact.

### Implementation for User Story 3

- [X] T030 [US3] Implement deterministic DTDL v3 mapping in `src/dtdl_generator.py` with `@context`, unique `@id`, `@type: "Interface"`, `displayName`, and interface-local `contents`.
- [X] T031 [US3] Implement the Queue interface contents in `src/dtdl_generator.py` with `capacity` as an integer Property and `occupancy` as integer Telemetry.
- [X] T032 [US3] Implement Station1 and Station2 interface contents in `src/dtdl_generator.py` with `cycle_time` as a double Property and `state` as string Telemetry.
- [X] T033 [US3] Enforce exactly three interfaces and stable Queue, Station1, and Station2 IDs in `src/dtdl_generator.py`.
- [X] T034 [US3] Serialize only the validated DTDL model document to `assembly_line.json` in `src/dtdl_generator.py` and keep the output aligned with `specs/001-interactive-dtdl-generator/contracts/dtdl-schema.md`.

**Checkpoint**: User Story 3 is independently demonstrable by loading and validating the generated DTDL contract.

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finalize constitutional compliance, documentation, and regression coverage across all stories.

- [X] T035 [P] Add regression coverage for the complete, partial, invalid, and failed-run scenarios in `tests/test_dtdl_generator.py`.
- [X] T036 [P] Verify model choice, bounded JSON extraction, standard-library dependency strategy, and absence of heavy agent frameworks in `src/dtdl_generator.py` and `pyproject.toml`.
- [X] T037 [P] Verify the two-station `Queue` -> `Assembly Station` -> `Packaging Station` topology and confirm no simulation/rendering thread integration was added outside the feature scope in `src/dtdl_generator.py`.
- [X] T038 [P] Update `README.md` with the final invocation and output contract after implementation matches the quickstart.
- [X] T039 Run the quickstart validation commands from `specs/001-interactive-dtdl-generator/quickstart.md` and record any environment-dependent limitations in `specs/001-interactive-dtdl-generator/quickstart.md`.
- [X] T040 Run focused tests and repository diagnostics for `src/dtdl_generator.py`, `tests/test_dtdl_generator.py`, and `pyproject.toml` before marking the feature complete.

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; T001-T004 can begin immediately, with T002-T004 parallelizable.
- **Foundational (Phase 2)**: Depends on T001 and T002; T005-T009 establish the shared implementation, while T010-T011 can proceed in parallel once the model/API seams are defined.
- **User Stories (Phases 3-5)**: Depend on Phase 2. US1 and US2 share the extraction and completion primitives; US3 consumes the validated mapping, so the recommended order is US1, US2, then US3, although their tests can be prepared in parallel.
- **Polish (Phase 6)**: Depends on the desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Depends on Foundational; establishes the required CLI argument and successful end-to-end path.
- **US2 (P1)**: Depends on Foundational and reuses US1’s CLI entry point; its completion loop remains independently testable through direct function tests and mocked input.
- **US3 (P1)**: Depends on Foundational and the mapping entry point; its contract tests are independent of OpenAI when they use completed `AssemblyLineParameters` fixtures.

### Parallel Opportunities

- T002, T003, and T004 can run in parallel after the source path is confirmed.
- T010 and T011 can run in parallel after the Pydantic and OpenAI boundaries are named.
- Within each user story, the listed tests marked `[P]` can be authored in parallel because they target separate scenarios in the same test module and do not change production behavior.
- T026-T029 can be authored in parallel as independent contract assertions.
- T035-T038 can be completed in parallel after implementation stabilizes.

## Parallel Example: User Story 1

```text
Task T012: Add complete-input acceptance coverage in tests/test_dtdl_generator.py
Task T013: Assert zero input() calls and persisted extracted values in tests/test_dtdl_generator.py
```

## Parallel Example: User Story 2

```text
Task T018: Add partial-input acceptance coverage in tests/test_dtdl_generator.py
Task T019: Add invalid-answer retry coverage in tests/test_dtdl_generator.py
Task T020: Add missing-argument and extraction-failure coverage in tests/test_dtdl_generator.py
```

## Parallel Example: User Story 3

```text
Task T026: Assert exactly three required interfaces in tests/test_dtdl_generator.py
Task T027: Assert Queue property and telemetry contents in tests/test_dtdl_generator.py
Task T028: Assert station property and telemetry contents in tests/test_dtdl_generator.py
Task T029: Assert persistence ordering in tests/test_dtdl_generator.py
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 setup.
2. Complete Phase 2 foundational models, extraction boundary, validation, and persistence.
3. Complete Phase 3 User Story 1 for complete command-line input.
4. Run the independent US1 acceptance test and stop for MVP validation.

### Incremental Delivery

1. Add User Story 2 to support partial descriptions and robust retries.
2. Add User Story 3 contract assertions and deterministic DTDL contents.
3. Complete Phase 6 regression, documentation, and constitutional checks.

### Definition Of Done

- All tasks are checked off after implementation and focused validation.
- Complete and partial acceptance scenarios pass without network calls in tests through a stubbed extraction boundary.
- `assembly_line.json` is written only after successful Pydantic validation.
- The output contains exactly Queue, Station1, and Station2 with the required properties and telemetry.
- The CLI returns non-zero and preserves any existing valid artifact on failure.
