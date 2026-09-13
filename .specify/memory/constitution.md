<!--
Sync Impact Report
- Version change: template/unversioned -> 1.0.0
- Modified principles: template placeholders replaced with three TwinIt principles
- Added sections: project constraints and development workflow
- Removed sections: none
- Templates requiring updates: .specify/templates/plan-template.md (updated),
	.specify/templates/spec-template.md (updated), .specify/templates/tasks-template.md (updated)
- Follow-up TODOs: none
-->

# TwinIt Constitution

## Core Principles

### I. Token & Execution Guardrails
All agent prompts and dynamic code generation MUST use `gpt-4o-mini` exclusively. The
implementation MUST avoid heavy agent frameworks, including LangChain, AutoGen, and
CrewAI, and use standard Python scripts, the OpenAI SDK, and Pydantic validation.
Prompts MUST be dense and bounded; generated structured data MUST use Pydantic
validation or `response_format={"type": "json_object"}` rather than open-ended text.
This keeps execution predictable, auditable, and economical.

### II. Architectural Boundaries
The model topology MUST remain a two-station linear assembly line: `Queue` ->
`Assembly Station` -> `Packaging Station`. SimPy simulation MUST run on a background
daemon `threading.Thread`, while the PyOpenGL rendering loop MUST run on the main
thread. Inter-thread communication MUST use thread-safe Python `queue.Queue`
instances exclusively; components MUST NOT mutate shared state directly. These
boundaries preserve simulation determinism and keep rendering responsive.

### III. Spec-Driven Contract Primacy
Generated DTDL v3 JSON schemas MUST be the single source of truth for downstream
SimPy code generation and dashboard properties. Every generated DTDL schema MUST
pass Pydantic validation before it is saved to `assembly_line.json`. Code and
dashboard changes MUST follow the validated contract rather than creating parallel
property definitions. This prevents drift between the digital-twin model and its
consumers.

## Additional Constraints

- The implementation MUST target Python 3.13 or newer and use the project’s declared
	OpenAI, Pydantic, SimPy, GLFW, ModernGL, and PyOpenGL dependencies where applicable.
- Features MUST preserve the two-station topology and MUST NOT introduce an additional
	station or an alternative orchestration framework without a constitution amendment.
- Contract-producing workflows MUST retain the generated artifact at
	`assembly_line.json` after validation.

## Development Workflow

- Feature specifications and implementation plans MUST include a Constitution Check
	covering model topology, thread ownership, queue-based communication, model choice,
	prompt output constraints, and DTDL/Pydantic validation.
- Tasks that generate or consume digital-twin contracts MUST identify the contract file
	and validation step explicitly.
- Changes MUST be validated with focused tests or checks for the affected behavior;
	contract changes MUST include schema validation coverage.

## Governance
This constitution supersedes conflicting project practices. Every feature plan and
review MUST verify compliance with the Core Principles and record any justified
exception. Amendments require a documented rationale, an updated Sync Impact Report,
and propagation to affected Spec Kit templates or guidance. Versioning follows
semantic versioning: MAJOR for incompatible principle changes or removals, MINOR for
new or materially expanded requirements, and PATCH for clarifications or wording-only
changes. Compliance MUST be reviewed at planning, implementation, and contract
validation checkpoints.

**Version**: 1.0.0 | **Ratified**: 2026-09-14 | **Last Amended**: 2026-09-14
