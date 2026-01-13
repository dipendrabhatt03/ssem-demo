package main

import (
	"fmt"
	"time"

	v1 "github.com/example/protobuf-compat/proto/v1"
	v2 "github.com/example/protobuf-compat/proto/v2"
	"google.golang.org/protobuf/encoding/protojson"
	"google.golang.org/protobuf/proto"
	"google.golang.org/protobuf/types/known/timestamppb"
)

func main() {
	fmt.Println("=== Protobuf Backward Compatibility Demo ===\n")

	// Create timestamps for our test data
	startTime := timestamppb.New(time.Date(2024, 1, 1, 12, 0, 0, 0, time.UTC))
	stopTime := timestamppb.New(time.Date(2024, 1, 1, 13, 0, 0, 0, time.UTC))

	fmt.Println("--- SCENARIO 1: Old Producer (v1) → New Consumer (v2) ---")
	fmt.Println("(Forward Compatibility: new field gets default value)\n")

	// Create v1 message (old producer)
	v1Msg := &v1.InfrastructureExecution{
		ExecutionId:      "exec-123",
		InfrastructureId: "infra-456",
		StartedAt:        startTime,
		StoppedAt:        stopTime,
		InstanceIds:      []string{"i-001", "i-002", "i-003"},
	}

	fmt.Println("V1 Message (old producer):")
	fmt.Printf("  execution_id: %s\n", v1Msg.ExecutionId)
	fmt.Printf("  infrastructure_id: %s\n", v1Msg.InfrastructureId)
	fmt.Printf("  instance_ids: %v\n", v1Msg.InstanceIds)
	fmt.Println()

	// Marshal v1 to binary
	v1Binary, err := proto.Marshal(v1Msg)
	if err != nil {
		panic(err)
	}
	fmt.Printf("V1 Binary size: %d bytes\n", len(v1Binary))

	// Marshal v1 to JSON
	v1JSON, err := protojson.Marshal(v1Msg)
	if err != nil {
		panic(err)
	}
	fmt.Printf("V1 JSON:\n%s\n\n", string(v1JSON))

	// Unmarshal binary into v2 (new consumer)
	v2FromBinary := &v2.InfrastructureExecution{}
	if err := proto.Unmarshal(v1Binary, v2FromBinary); err != nil {
		panic(err)
	}

	fmt.Println("✅ V2 Message from Binary (new consumer reading old data):")
	fmt.Printf("  execution_id: %s\n", v2FromBinary.ExecutionId)
	fmt.Printf("  infrastructure_id: %s\n", v2FromBinary.InfrastructureId)
	fmt.Printf("  instance_ids: %v\n", v2FromBinary.InstanceIds)
	fmt.Printf("  message: \"%s\" (new field gets default/empty value)\n", v2FromBinary.Message)
	fmt.Println()

	// Unmarshal JSON into v2 (new consumer)
	v2FromJSON := &v2.InfrastructureExecution{}
	if err := protojson.Unmarshal(v1JSON, v2FromJSON); err != nil {
		panic(err)
	}

	fmt.Println("✅ V2 Message from JSON (new consumer reading old data):")
	fmt.Printf("  execution_id: %s\n", v2FromJSON.ExecutionId)
	fmt.Printf("  infrastructure_id: %s\n", v2FromJSON.InfrastructureId)
	fmt.Printf("  instance_ids: %v\n", v2FromJSON.InstanceIds)
	fmt.Printf("  message: \"%s\" (new field gets default/empty value)\n", v2FromJSON.Message)
	fmt.Println()

	fmt.Println("--- SCENARIO 2: New Producer (v2) → Old Consumer (v1) ---")
	fmt.Println("(Backward Compatibility: old consumer ignores new field)\n")

	// Create v2 message (new producer) with the new field populated
	v2Msg := &v2.InfrastructureExecution{
		ExecutionId:      "exec-789",
		InfrastructureId: "infra-012",
		StartedAt:        startTime,
		StoppedAt:        stopTime,
		InstanceIds:      []string{"i-004", "i-005"},
		Message:          "Execution completed successfully", // New field with value
	}

	fmt.Println("V2 Message (new producer):")
	fmt.Printf("  execution_id: %s\n", v2Msg.ExecutionId)
	fmt.Printf("  infrastructure_id: %s\n", v2Msg.InfrastructureId)
	fmt.Printf("  instance_ids: %v\n", v2Msg.InstanceIds)
	fmt.Printf("  message: \"%s\" (new field)\n", v2Msg.Message)
	fmt.Println()

	// Marshal v2 to binary
	v2Binary, err := proto.Marshal(v2Msg)
	if err != nil {
		panic(err)
	}
	fmt.Printf("V2 Binary size: %d bytes\n", len(v2Binary))

	// Marshal v2 to JSON
	v2JSON, err := protojson.Marshal(v2Msg)
	if err != nil {
		panic(err)
	}
	fmt.Printf("V2 JSON:\n%s\n\n", string(v2JSON))

	// Unmarshal binary into v1 (old consumer)
	v1FromBinary := &v1.InfrastructureExecution{}
	if err := proto.Unmarshal(v2Binary, v1FromBinary); err != nil {
		panic(err)
	}

	fmt.Println("✅ V1 Message from Binary (old consumer ignores new field):")
	fmt.Printf("  execution_id: %s\n", v1FromBinary.ExecutionId)
	fmt.Printf("  infrastructure_id: %s\n", v1FromBinary.InfrastructureId)
	fmt.Printf("  instance_ids: %v\n", v1FromBinary.InstanceIds)
	fmt.Printf("  (message field not present in v1 schema - safely ignored)\n")
	fmt.Println()

	// Unmarshal JSON into v1 (old consumer)
	// Use DiscardUnknown to ignore the new 'message' field (same behavior as binary)
	v1FromJSON := &v1.InfrastructureExecution{}
	unmarshalOpts := protojson.UnmarshalOptions{`DiscardUnknown`: true}
	if err := unmarshalOpts.Unmarshal(v2JSON, v1FromJSON); err != nil {
		panic(err)
	}

	fmt.Println("✅ V1 Message from JSON (old consumer ignores new field):")
	fmt.Printf("  execution_id: %s\n", v1FromJSON.ExecutionId)
	fmt.Printf("  infrastructure_id: %s\n", v1FromJSON.InfrastructureId)
	fmt.Printf("  instance_ids: %v\n", v1FromJSON.InstanceIds)
	fmt.Printf("  (message field not present in v1 schema - safely ignored)\n")
	fmt.Println()

	fmt.Println("=== Summary ===")
	fmt.Println("✅ Binary and JSON behave identically")
	fmt.Println("✅ New consumers can read old data (new fields get default values)")
	fmt.Println("✅ Old consumers can read new data (unknown fields are ignored)")
	fmt.Println("✅ Schema evolution works seamlessly in both directions")
}
