package main

import (
	"encoding/hex"
	"fmt"

	v1 "github.com/example/protobuf-compat/proto/v1"
	v2 "github.com/example/protobuf-compat/proto/v2"
	"google.golang.org/protobuf/encoding/protojson"
	"google.golang.org/protobuf/proto"
)

func main() {
	// The hex string provided (without 0x prefix)
	hexData := "0A0866726F6E74656E64120E7373656D6F757470757464656D6F2A0C08C2F080C90610888FC99101320C08C2F080C90610888FC991013A00"

	// Decode hex to binary
	binaryData, err := hex.DecodeString(hexData)
	if err != nil {
		panic(fmt.Sprintf("Failed to decode hex: %v", err))
	}

	fmt.Printf("Binary data length: %d bytes\n", len(binaryData))
	fmt.Printf("Binary data (hex): %X\n\n", binaryData)

	// Try unmarshaling with v1 schema
	fmt.Println("=== Attempting to unmarshal with V1 schema ===")
	v1Msg := &v1.InfrastructureExecution{}
	if err := proto.Unmarshal(binaryData, v1Msg); err != nil {
		fmt.Printf("❌ V1 unmarshal failed: %v\n\n", err)
	} else {
		fmt.Println("✅ V1 unmarshal successful!")
		fmt.Printf("  execution_id: %s\n", v1Msg.ExecutionId)
		fmt.Printf("  infrastructure_id: %s\n", v1Msg.InfrastructureId)
		if v1Msg.StartedAt != nil {
			fmt.Printf("  started_at: %v\n", v1Msg.StartedAt.AsTime())
		}
		if v1Msg.StoppedAt != nil {
			fmt.Printf("  stopped_at: %v\n", v1Msg.StoppedAt.AsTime())
		}
		fmt.Printf("  instance_ids: %v\n", v1Msg.InstanceIds)

		// Convert to JSON for readability
		jsonData, _ := protojson.MarshalOptions{Indent: "  "}.Marshal(v1Msg)
		fmt.Printf("\nV1 JSON representation:\n%s\n\n", string(jsonData))
	}

	// Try unmarshaling with v2 schema
	fmt.Println("=== Attempting to unmarshal with V2 schema ===")
	v2Msg := &v2.InfrastructureExecution{}
	if err := proto.Unmarshal(binaryData, v2Msg); err != nil {
		fmt.Printf("❌ V2 unmarshal failed: %v\n\n", err)
	} else {
		fmt.Println("✅ V2 unmarshal successful!")
		fmt.Printf("  execution_id: %s\n", v2Msg.ExecutionId)
		fmt.Printf("  infrastructure_id: %s\n", v2Msg.InfrastructureId)
		if v2Msg.StartedAt != nil {
			fmt.Printf("  started_at: %v\n", v2Msg.StartedAt.AsTime())
		}
		if v2Msg.StoppedAt != nil {
			fmt.Printf("  stopped_at: %v\n", v2Msg.StoppedAt.AsTime())
		}
		fmt.Printf("  instance_ids: %v\n", v2Msg.InstanceIds)
		fmt.Printf("  message: \"%s\"\n", v2Msg.Message)

		// Convert to JSON for readability
		jsonData, _ := protojson.MarshalOptions{Indent: "  "}.Marshal(v2Msg)
		fmt.Printf("\nV2 JSON representation:\n%s\n\n", string(jsonData))
	}
}
