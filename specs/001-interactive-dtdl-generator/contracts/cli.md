# CLI Contract

## Invocation

```text
python src/dtdl_generator.py "<plain-English assembly-line description>"
```

The description is required as one command-line argument. A missing argument is a usage error and must not create or modify `assembly_line.json`.

## Extraction

The implementation sends the description to `gpt-4o-mini` with a bounded JSON response request. The JSON object maps to `AssemblyLineParameters` and may contain null values for fields absent from the description.

## Interactive completion

Missing or invalid values are requested with standard `input()` in this order:

1. `station1_name`
2. `station1_cycle_time` in seconds
3. `station2_name`
4. `station2_cycle_time` in seconds
5. `queue_capacity` in items

A prompt must identify the parameter. Invalid or blank answers are rejected and retried. No output is persisted until all values are valid.

## Success

The process writes a validated `assembly_line.json` in the current working directory and exits successfully.

## Failure

Extraction, input, validation, or persistence failures are reported to standard error, return a non-zero exit status, and do not write a new invalid artifact.
