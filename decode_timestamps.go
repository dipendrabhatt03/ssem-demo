package main

import (
	"encoding/hex"
	"fmt"
	"time"

	"google.golang.org/protobuf/proto"
	"google.golang.org/protobuf/types/known/timestamppb"
)

func main() {
	hexData := "0A0866726F6E74656E64120E7373656D6F757470757464656D6F2A0C08C2F080C90610888FC99101320C08C2F080C90610888FC991013A00"

	binaryData, _ := hex.DecodeString(hexData)

	fmt.Println("=== Decoding the Protobuf Message ===\n")

	// Field 1: execution_id
	fmt.Printf("Field 1 (execution_id): \"frontend\"\n")

	// Field 2: infrastructure_id
	fmt.Printf("Field 2 (infrastructure_id): \"ssemoutputdemo\"\n")

	// Field 5: Timestamp at bytes 28-40 (embedded message)
	timestampBytes5 := binaryData[28:40]
	ts5 := &timestamppb.Timestamp{}
	if err := proto.Unmarshal(timestampBytes5, ts5); err == nil {
		fmt.Printf("Field 5 (embedded timestamp): %s\n", ts5.AsTime().Format(time.RFC3339))
		fmt.Printf("  Seconds: %d, Nanos: %d\n", ts5.Seconds, ts5.Nanos)
	}

	// Field 6: Timestamp at bytes 42-54 (embedded message)
	timestampBytes6 := binaryData[42:54]
	ts6 := &timestamppb.Timestamp{}
	if err := proto.Unmarshal(timestampBytes6, ts6); err == nil {
		fmt.Printf("Field 6 (embedded timestamp): %s\n", ts6.AsTime().Format(time.RFC3339))
		fmt.Printf("  Seconds: %d, Nanos: %d\n", ts6.Seconds, ts6.Nanos)
	}

	// Field 7: Empty string
	fmt.Printf("Field 7: \"\" (empty string)\n")

	fmt.Println("\n=== Summary ===")
	fmt.Println("This data appears to be from a different protobuf schema where:")
	fmt.Println("  - Field 1 = execution_id (string)")
	fmt.Println("  - Field 2 = infrastructure_id (string)")
	fmt.Println("  - Field 5 = started_at or similar (Timestamp)")
	fmt.Println("  - Field 6 = stopped_at or similar (Timestamp)")
	fmt.Println("  - Field 7 = message or similar (string)")
	fmt.Println("\nThis doesn't match our schema where field 5 is 'repeated string instance_ids'")
	fmt.Println("and fields 3 & 4 are the Timestamp fields.")
}
