# Research: Interactive DTDL v3 Generator Agent

## Decision: Use a top-level DTDL model-document array

- **Decision**: Persist `assembly_line.json` as a JSON array containing exactly three DTDL v3 `Interface` objects: `Queue`, `Station1`, and `Station2`. Each interface contains its own `contents` array for properties and telemetry.
- **Rationale**: DTDL model documents conventionally contain one or more interface definitions at the document root. `contents` belongs to each interface and is the correct location for its property and telemetry definitions. This keeps the artifact validator-friendly while satisfying the requested contents-based contract.
- **Alternatives considered**: A wrapper object with an `interfaces` field was rejected because it adds a non-DTDL envelope. A single root interface containing other interfaces as contents was rejected because interface definitions are not nested that way in the required contract.

## Decision: Keep extraction and contract models separate

- **Decision**: Define `AssemblyLineParameters` for user-supplied/extracted values and `DTDLInterface` plus nested content models for the output document.
- **Rationale**: Input validation has domain constraints such as positive cycle times and queue capacity, while DTDL output validation has schema constraints such as `@type`, `schema`, and `contents`. Separate models prevent input concerns from leaking into the serialized contract and make validation failures actionable.
- **Alternatives considered**: A single permissive dictionary was rejected because it would weaken validation and make invalid output possible. A single model for both concerns was rejected because the shapes and lifecycle states differ.

## Decision: Use a bounded JSON extraction request with `gpt-4o-mini`

- **Decision**: Send the command-line description to the OpenAI SDK using model `gpt-4o-mini` and request a JSON object matching the extraction fields; parse the response into `AssemblyLineParameters`.
- **Rationale**: This satisfies the project constitution, keeps the prompt deterministic, and lets Pydantic enforce field types and positivity after model output is received.
- **Alternatives considered**: Free-form text parsing was rejected because it is less deterministic. Heavy agent frameworks were rejected by constitutional constraint and because this single-step extraction does not need orchestration.

## Decision: Complete missing values through a single reusable prompt loop

- **Decision**: Validate each required field in a stable order and use `input()` only for missing or invalid values. Retry invalid numeric values without writing output.
- **Rationale**: A stable order makes the CLI testable and makes partial-input behavior predictable. Keeping prompting separate from extraction also supports unit tests without network calls.
- **Alternatives considered**: Re-querying the model for missing values was rejected because it adds cost and can reintroduce ambiguity. Prompting for every field was rejected because complete inputs must run with zero missing-parameter prompts.

## Decision: Validate before atomic replacement of the output file

- **Decision**: Build and validate the complete DTDL payload with Pydantic, serialize only after validation, and replace `assembly_line.json` only after successful validation.
- **Rationale**: This preserves the existing valid artifact when a new run fails and ensures no invalid or partial contract is persisted.
- **Alternatives considered**: Writing incrementally was rejected because a failure could leave a partial artifact. Writing first and validating afterward violates the constitution.
