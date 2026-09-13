# Data Model: Interactive DTDL v3 Generator Agent

## AssemblyLineParameters

Represents the normalized parameters extracted from the initial description and completed through the CLI.

| Field | Type | Required | Validation |
|---|---|---:|---|
| `station1_name` | string or null during extraction | Yes before generation | Non-empty after trimming; maps to the first station interface display name |
| `station1_cycle_time` | float or null during extraction | Yes before generation | Strictly greater than 0; seconds |
| `station2_name` | string or null during extraction | Yes before generation | Non-empty after trimming; maps to the second station interface display name |
| `station2_cycle_time` | float or null during extraction | Yes before generation | Strictly greater than 0; seconds |
| `queue_capacity` | integer or null during extraction | Yes before generation | Strictly greater than 0; item count |

### State transitions

1. **Extracted**: The model contains values from `gpt-4o-mini`; missing fields are allowed only at this stage.
2. **Completing**: Each missing or invalid field is requested through `input()`.
3. **Complete**: All five fields satisfy validation constraints.
4. **Contract-ready**: The complete model is mapped into the DTDL document.

## DTDLInterface

Represents one DTDL v3 interface in the persisted model document.

| Field | Type | Required | Validation |
|---|---|---:|---|
| `@context` | string | Yes | DTDL v3 context URI `dtmi:dtdl:context;3` |
| `@id` | string | Yes | Unique DTMI for the interface |
| `@type` | literal string | Yes | `Interface` |
| `displayName` | string | Yes | Human-readable interface name |
| `contents` | list[DTDLContent] | Yes | At least the required property and telemetry entries |

## DTDLContent

A property or telemetry member inside an interface.

| Field | Type | Required | Validation |
|---|---|---:|---|
| `@type` | literal string | Yes | `Property` or `Telemetry` |
| `name` | string | Yes | Contract name; `capacity`, `occupancy`, `cycle_time`, or `state` |
| `schema` | string | Yes | Primitive DTDL schema such as `integer`, `double`, or `string` |
|

## Assembly Line Schema

The persisted root document is a JSON array of exactly three `DTDLInterface` records:

1. `Queue`: `capacity` property using `integer`; `occupancy` telemetry using `integer`.
2. First station: canonical ID for `Station1`, custom `station1_name` as display name,
   `cycle_time` property using `double`, and `state` telemetry using `string`.
3. Second station: canonical ID for `Station2`, custom `station2_name` as display name,
   `cycle_time` property using `double`, and `state` telemetry using `string`.

The model document order is stable: Queue, Station1, Station2. No additional interfaces are permitted.
