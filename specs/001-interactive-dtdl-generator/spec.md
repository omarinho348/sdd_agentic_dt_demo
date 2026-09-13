# Feature Specification: Interactive DTDL v3 Generator Agent

**Feature Branch**: `001-interactive-dtdl-generator`

**Created**: 2026-09-14

**Status**: Draft

**Input**: User description: "Build an interactive CLI tool that uses gpt-4o-mini and Pydantic to parse assembly-line topology inputs, collect missing parameters, and save a validated DTDL v3 schema."

## Clarifications

### Session 2026-09-14

- Q: How should the initial natural-language description enter the CLI? -> A: As a required command-line argument; `input()` is reserved for missing-parameter completion.
- Q: How should users test and evaluate Feature 001? -> A: A local browser application is the primary workflow; the CLI remains available as a compatibility path.

## User Scenarios & Testing *(mandatory)*

### User Story 0 - Generate and inspect a model in the browser (Priority: P1)

As a user, I want a local webpage where I can enter an assembly-line description, complete missing values in a form, and inspect the generated contract so that I can evaluate the feature without terminal prompts or JSON editing.

**Why this priority**: The browser is the primary usability and evaluation surface for Feature 001; it makes the workflow visible and understandable to users who should not need to operate a CLI.

**Independent Test**: Start the local web server, open the displayed URL, submit a complete or partial description, complete any highlighted fields, and verify that the page shows the Queue and two station interfaces plus a downloadable JSON artifact.

**Acceptance Scenarios**:

1. **Given** the local generator page is open, **When** the user enters a complete description and selects Generate model, **Then** the page displays the validated Queue, Station1, and Station2 contract without terminal interaction.
2. **Given** the description omits cycle times or queue capacity, **When** the user selects Generate model, **Then** the page reveals only the missing fields and keeps the workflow on the same page.
3. **Given** the user completes the revealed fields with valid values, **When** the user selects Generate model again, **Then** the page displays the validated contract and offers the generated JSON for download.
4. **Given** an invalid or non-positive value is entered, **When** validation occurs, **Then** the field shows an actionable error and no invalid contract is displayed or persisted.

### User Story 1 - Generate a schema from complete input (Priority: P1)

As a user, I want to describe a complete two-station assembly line in plain English so that the tool produces a validated digital-twin schema without unnecessary interaction.

**Why this priority**: Complete-input generation is the primary fast path and establishes the core value of the feature.

**Independent Test**: Run the CLI with a prompt containing both station names, both positive cycle times, and a positive queue capacity; verify that it exits without parameter prompts and creates a valid `assembly_line.json`.

**Acceptance Scenarios**:

1. **Given** the input `Assembly line with station1 cycle time 5s, station2 cycle time 8s, and queue size 3`, **When** the user runs the generator, **Then** the tool creates `assembly_line.json` without asking for missing parameters.
2. **Given** a complete input with custom station names, **When** the generator finishes, **Then** the resulting schema preserves those names and the supplied cycle times and queue capacity.

### User Story 2 - Complete missing parameters interactively (Priority: P1)

As a user, I want the tool to ask for missing assembly-line values so that a partial natural-language description can still produce a complete schema.

**Why this priority**: Interactive completion is required for the stated partial-input workflow and prevents users from needing to format every parameter in advance.

**Independent Test**: Run the CLI with a partial prompt, provide valid answers at each displayed prompt, and verify that the answers are represented in the saved schema.

**Acceptance Scenarios**:

1. **Given** the input `Create a line with assembly and packaging stations.`, **When** the user runs the generator, **Then** the tool asks for missing cycle times and queue capacity before saving the schema.
2. **Given** a missing station cycle time or queue capacity, **When** the tool prompts for it, **Then** the prompt identifies the parameter and its unit or expected value type.
3. **Given** a user enters an invalid or non-positive numeric value, **When** validation occurs, **Then** the tool reports the value as invalid and requests a replacement without saving an invalid schema.

### User Story 3 - Inspect a contract-ready DTDL schema (Priority: P1)

As a downstream simulation or dashboard consumer, I want a stable DTDL v3 schema containing the queue and both stations so that I can rely on one validated contract for assembly-line properties and telemetry.

**Why this priority**: The schema is the contract used by downstream consumers and must be correct before any generated artifact is accepted.

**Independent Test**: Load the generated JSON and validate its required interface, property, telemetry, names, and numeric values against the feature contract.

**Acceptance Scenarios**:

1. **Given** valid assembly-line parameters, **When** the schema is generated, **Then** it contains DTDL v3 `Interface` definitions for `Queue`, `Station1`, and `Station2`.
2. **Given** the generated interfaces, **When** a consumer inspects `Queue`, **Then** it finds a `capacity` property and an `occupancy` telemetry.
3. **Given** the generated interfaces, **When** a consumer inspects each station, **Then** it finds a `cycle_time` property and a `state` telemetry.
4. **Given** a schema candidate, **When** persistence is attempted, **Then** Pydantic validation completes successfully before the candidate is written to `assembly_line.json`.

### Edge Cases

- The natural-language input omits one or more mandatory values; the tool prompts only for values that remain missing.
- The model returns `null`, an empty station name, malformed structured data, or a value with the wrong type; the tool treats the field as missing or invalid and requests a valid replacement.
- A cycle time or queue capacity is zero, negative, non-numeric, or otherwise outside its required domain; the tool refuses it and does not save an invalid schema.
- The user enters blank input at a required prompt; the tool keeps the parameter unresolved and asks again.
- The model or schema validation service is unavailable or returns an unusable response; the tool reports the failure and does not write a partial contract.
- An existing `assembly_line.json` is present; the tool replaces it only after the new schema has passed validation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The tool MUST accept the initial raw plain-English assembly-line description as a required command-line argument.
- **FR-002**: The tool MUST use `gpt-4o-mini` for initial extraction and request structured output conforming to the `AssemblyLineParameters` model.
- **FR-003**: The extraction model MUST represent `station1_name`, `station1_cycle_time`, `station2_name`, `station2_cycle_time`, and `queue_capacity`, allowing missing values to remain unresolved until interactive completion.
- **FR-004**: The tool MUST inspect extracted values and prompt on standard output for every missing mandatory value before schema generation.
- **FR-005**: The tool MUST read interactive answers using standard console input and associate each answer with the parameter named in the prompt.
- **FR-006**: The tool MUST require non-empty station names, cycle times greater than zero, and queue capacity greater than zero.
- **FR-007**: The tool MUST reject invalid interactive answers, explain the expected value, and continue prompting until a valid value is supplied or the run is terminated.
- **FR-008**: The tool MUST map validated parameters into a DTDL v3 JSON contract containing `Interface` definitions for `Queue`, `Station1`, and `Station2`.
- **FR-009**: The `Queue` interface MUST contain a `capacity` property and an `occupancy` telemetry.
- **FR-010**: Each station interface MUST contain a `cycle_time` property and a `state` telemetry.
- **FR-011**: The tool MUST Pydantic-validate the complete DTDL contract before persistence.
- **FR-012**: The tool MUST save only a successfully validated contract to `assembly_line.json`.
- **FR-013**: The tool MUST avoid writing a partial or invalid output when extraction, interactive validation, or contract validation fails.
- **FR-014**: The tool MUST preserve the two-station topology of `Queue` -> `Assembly Station` -> `Packaging Station` and MUST NOT create additional stations.
- **FR-015**: The project MUST provide a local browser application as the primary user workflow for entering descriptions, completing missing values, and evaluating the generated contract.
- **FR-016**: The browser application MUST expose a JSON API that returns extracted parameters and missing fields without writing an incomplete contract.
- **FR-017**: The browser application MUST validate submitted completion values with the same Pydantic models used by the CLI before generating or persisting the DTDL document.
- **FR-018**: The browser application MUST display the generated interface names, properties, telemetry, and validation status in a readable view and provide a download action for the validated JSON.
- **FR-019**: The CLI MUST remain available for compatibility, but browser acceptance scenarios MUST NOT depend on terminal `input()` prompts.

### Constitutional Constraints

- **CC-001**: All agent prompts and dynamic code generation MUST use `gpt-4o-mini` exclusively and MUST use bounded structured output.
- **CC-002**: The feature MUST use standard Python, the OpenAI SDK, and Pydantic, without heavy agent frameworks.
- **CC-003**: The feature MUST preserve the prescribed two-station topology and use `queue.Queue` for inter-thread communication if simulation or rendering integration is added.
- **CC-004**: DTDL v3 MUST remain the single source of truth, and Pydantic validation MUST precede writing `assembly_line.json`.

### Key Entities

- **AssemblyLineParameters**: The extracted and interactively completed input contract containing two station names, two positive cycle times, and one positive queue capacity.
- **DTDL Interface**: A DTDL v3 interface definition representing the queue or a station and its properties and telemetry.
- **Queue Contract**: The interface describing queue capacity and occupancy telemetry.
- **Station Contract**: The interface describing a station cycle time and state telemetry.
- **Assembly Line Schema**: The validated collection of DTDL interfaces persisted as `assembly_line.json`.
- **Browser Session**: The temporary client-side workflow state containing the original description, extracted values, missing fields, validation errors, and final contract.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a complete valid input, 100% of successful runs generate `assembly_line.json` without displaying a missing-parameter prompt.
- **SC-002**: For the specified partial input, 100% of runs display prompts for each missing cycle time and queue capacity before persistence.
- **SC-003**: 100% of persisted output files pass the defined Pydantic contract validation before being written.
- **SC-004**: 100% of valid generated schemas contain exactly three required interfaces: `Queue`, `Station1`, and `Station2`.
- **SC-005**: At least 95% of users providing valid answers complete schema generation without restarting the CLI after correcting any invalid entry.
- **SC-006**: Invalid, incomplete, or failed runs leave no newly written invalid `assembly_line.json` artifact.
- **SC-007**: A first-time user can start the local web server, open the browser URL, and reach the description form in under 60 seconds using the documented quickstart.
- **SC-008**: 100% of browser submissions with valid completion values show the three-interface contract without requiring terminal input.
- **SC-009**: 100% of browser submissions with invalid completion values show field-level errors and do not persist a new contract.

## Assumptions

- The CLI receives one initial natural-language description as a required command-line argument per run and uses console input only for completion or correction of missing or invalid parameters.
- The initial extraction request may leave any mandatory field unresolved when the source text does not provide it.
- Station names are user-facing labels; the canonical topology still maps the first station to assembly and the second station to packaging.
- Cycle times are measured in seconds, and queue capacity is a count of items.
- `assembly_line.json` is written relative to the current working directory unless the implementation plan establishes an explicit project output location.
- The OpenAI credential and network access required for model extraction are available at runtime.
- Rendering and SimPy execution are downstream consumers of this generator and are not required for this CLI MVP beyond preserving the constitutional topology and contract boundary.
- The local browser server is intended for development and evaluation on the same machine; authentication and multi-user deployment are out of scope.
