#!/bin/bash
# Setup script for PostgreSQL Protobuf Benchmark

set -e

echo "=========================================="
echo "Protobuf Benchmark Setup"
echo "=========================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Compile proto file
echo ""
echo "Compiling protobuf schema..."
python3 -m grpc_tools.protoc -I=proto --python_out=. proto/infrastructure.proto

if [ -f "infrastructure_pb2.py" ]; then
    echo "✓ Generated proto/infrastructure_pb2.py"
else
    echo "❌ Error: Failed to generate proto/infrastructure_pb2.py"
    exit 1
fi

echo ""
echo "=========================================="
echo "✓ Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Ensure PostgreSQL is running"
echo "2. Update DB_CONFIG in benchmark.py if needed"
echo "3. Run: python3 benchmark.py"
echo ""
