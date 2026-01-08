package main

import (
	"encoding/hex"
	"fmt"
)

func main() {
	hexData := "0A0866726F6E74656E64120E7373656D6F757470757464656D6F2A0C08C2F080C90610888FC99101320C08C2F080C90610888FC991013A00"

	binaryData, err := hex.DecodeString(hexData)
	if err != nil {
		panic(err)
	}

	fmt.Printf("Total length: %d bytes\n", len(binaryData))
	fmt.Printf("Raw hex: %s\n\n", hexData)

	// Manually parse the protobuf wire format
	fmt.Println("=== Wire Format Analysis ===")

	i := 0
	for i < len(binaryData) {
		// Read field tag
		if i >= len(binaryData) {
			break
		}

		tag := binaryData[i]
		fieldNumber := tag >> 3
		wireType := tag & 0x07

		fmt.Printf("Byte %d: Field %d, Wire Type %d", i, fieldNumber, wireType)
		i++

		switch wireType {
		case 0: // Varint
			fmt.Print(" (varint): ")
			value := uint64(0)
			shift := uint(0)
			for {
				if i >= len(binaryData) {
					break
				}
				b := binaryData[i]
				i++
				value |= uint64(b&0x7F) << shift
				if b < 0x80 {
					break
				}
				shift += 7
			}
			fmt.Printf("%d\n", value)

		case 2: // Length-delimited (string, bytes, embedded messages)
			if i >= len(binaryData) {
				break
			}
			length := int(binaryData[i])
			i++
			fmt.Printf(" (length-delimited, len=%d): ", length)

			if i+length <= len(binaryData) {
				data := binaryData[i : i+length]
				// Try to print as string
				fmt.Printf("%q (hex: %X)\n", string(data), data)
				i += length
			} else {
				fmt.Printf("ERROR: length exceeds remaining data\n")
				break
			}

		default:
			fmt.Printf(" (unknown wire type)\n")
			break
		}
	}

	// Try to decode known string fields
	fmt.Println("\n=== Decoded String Values ===")

	// Field 1 (0A 08 ...) - length 8
	field1 := binaryData[2:10]
	fmt.Printf("Field 1: %q\n", string(field1))

	// Field 2 (12 0E ...) - length 14
	field2 := binaryData[11:25]
	fmt.Printf("Field 2: %q\n", string(field2))
}
