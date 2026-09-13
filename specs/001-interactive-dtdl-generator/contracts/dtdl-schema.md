# DTDL v3 Schema Contract

`assembly_line.json` is a top-level JSON array with exactly three objects. Each object has:

```json
{
  "@context": "dtmi:dtdl:context;3",
  "@id": "dtmi:twinIt:Queue;1",
  "@type": "Interface",
  "displayName": "Queue",
  "contents": []
}
```

Required interfaces:

- Queue: `capacity` Property (`integer`) and `occupancy` Telemetry (`integer`)
- Station1: `cycle_time` Property (`double`) and `state` Telemetry (`string`)
- Station2: `cycle_time` Property (`double`) and `state` Telemetry (`string`)

The exact station display names and cycle-time values come from `AssemblyLineParameters`; interface IDs remain stable. Pydantic validation must complete before serialization and persistence.
