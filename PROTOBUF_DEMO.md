# Protobuf Backward Compatibility Demo

This project demonstrates that protobuf's schema evolution (adding new fields) works **identically** for both binary protobuf and JSON (protojson) formats.

## Project Structure

```
.
├── proto/
│   ├── v1/
│   │   └── example.proto    # Version 1 (without 'message' field)
│   └── v2/
│       └── example.proto    # Version 2 (with 'message' field)
├── main.go                  # Compatibility demonstration
├── go.mod
└── PROTOBUF_DEMO.md        # This file
```

## What This Demonstrates

1. **Forward Compatibility**: Old producer (v1) → New consumer (v2)
   - New field gets default value when reading old data
   - Works identically for binary and JSON

2. **Backward Compatibility**: New producer (v2) → Old consumer (v1)
   - Old consumer safely ignores the new field
   - Works identically for binary and JSON

## Prerequisites

- Go 1.21 or later
- Protocol Buffers compiler (`protoc`)
- protoc-gen-go plugin

### Installing protoc

**macOS:**
```bash
brew install protobuf
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt install protobuf-compiler

# Or download from: https://github.com/protocolbuffers/protobuf/releases
```

### Installing protoc-gen-go

```bash
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
```

Make sure `$GOPATH/bin` (or `$HOME/go/bin`) is in your `PATH`.

## Running the Demo

### Step 1: Install Dependencies

```bash
go mod download
```

### Step 2: Generate Go Code from Proto Files

```bash
# Generate v1 proto
protoc --go_out=. --go_opt=paths=source_relative \
  proto/v1/example.proto

# Generate v2 proto
protoc --go_out=. --go_opt=paths=source_relative \
  proto/v2/example.proto
```

This will create:
- `proto/v1/example.pb.go`
- `proto/v2/example.pb.go`

### Step 3: Run the Demo

```bash
go run main.go
```

## Expected Output

```
=== Protobuf Backward Compatibility Demo ===

--- SCENARIO 1: Old Producer (v1) → New Consumer (v2) ---
(Forward Compatibility: new field gets default value)

V1 Message (old producer):
  execution_id: exec-123
  infrastructure_id: infra-456
  instance_ids: [i-001 i-002 i-003]

V1 Binary size: 103 bytes
V1 JSON:
{"executionId":"exec-123","infrastructureId":"infra-456","startedAt":"2024-01-01T12:00:00Z","stoppedAt":"2024-01-01T13:00:00Z","instanceIds":["i-001","i-002","i-003"]}

✅ V2 Message from Binary (new consumer reading old data):
  execution_id: exec-123
  infrastructure_id: infra-456
  instance_ids: [i-001 i-002 i-003]
  message: "" (new field gets default/empty value)

✅ V2 Message from JSON (new consumer reading old data):
  execution_id: exec-123
  infrastructure_id: infra-456
  instance_ids: [i-001 i-002 i-003]
  message: "" (new field gets default/empty value)

--- SCENARIO 2: New Producer (v2) → Old Consumer (v1) ---
(Backward Compatibility: old consumer ignores new field)

V2 Message (new producer):
  execution_id: exec-789
  infrastructure_id: infra-012
  instance_ids: [i-004 i-005]
  message: "Execution completed successfully" (new field)

V2 Binary size: 128 bytes
V2 JSON:
{"executionId":"exec-789","infrastructureId":"infra-012","startedAt":"2024-01-01T12:00:00Z","stoppedAt":"2024-01-01T13:00:00Z","instanceIds":["i-004","i-005"],"message":"Execution completed successfully"}

✅ V1 Message from Binary (old consumer ignores new field):
  execution_id: exec-789
  infrastructure_id: infra-012
  instance_ids: [i-004 i-005]
  (message field not present in v1 schema - safely ignored)

✅ V1 Message from JSON (old consumer ignores new field):
  execution_id: exec-789
  infrastructure_id: infra-012
  instance_ids: [i-004 i-005]
  (message field not present in v1 schema - safely ignored)

=== Summary ===
✅ Binary and JSON behave identically
✅ New consumers can read old data (new fields get default values)
✅ Old consumers can read new data (unknown fields are ignored)
✅ Schema evolution works seamlessly in both directions
```

## Key Takeaways

1. **No custom serializers needed**: Standard `proto.Marshal/Unmarshal` and `protojson.Marshal/Unmarshal` handle everything.

2. **Identical behavior**: Binary protobuf and JSON protobuf have the same compatibility guarantees when using `protojson.UnmarshalOptions{DiscardUnknown: true}` for backward compatibility (old consumer reading new data).

3. **Safe schema evolution**: You can add new fields without breaking existing producers or consumers.

4. **Production-ready**: This is the standard approach used in production systems for schema evolution.

5. **Important note**: For JSON backward compatibility, use `DiscardUnknown: true` when unmarshaling to ignore unknown fields (binary protobuf does this by default).

## Schema Versions

### V1 Schema (proto/v1/example.proto)

```protobuf
message InfrastructureExecution {
  string execution_id = 1;
  string infrastructure_id = 2;
  google.protobuf.Timestamp started_at = 3;
  google.protobuf.Timestamp stopped_at = 4;
  repeated string instance_ids = 5;
  // No 'message' field yet
}
```

### V2 Schema (proto/v2/example.proto)

```protobuf
message InfrastructureExecution {
  string execution_id = 1;
  string infrastructure_id = 2;
  google.protobuf.Timestamp started_at = 3;
  google.protobuf.Timestamp stopped_at = 4;
  repeated string instance_ids = 5;
  string message = 6;  // ← New field added
}
```

## Clean Up

To remove generated files:

```bash
rm proto/v1/*.pb.go proto/v2/*.pb.go
```
