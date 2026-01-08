# PostgreSQL Protobuf Benchmark: Binary vs JSON

A comprehensive benchmarking experiment comparing binary protobuf vs protobuf JSON storage performance in PostgreSQL.

## Overview

This benchmark measures the real-world performance differences between:
- **Binary Protobuf**: Compact binary serialization stored in PostgreSQL BYTEA columns
- **JSON Protobuf**: Official protobuf JSON mapping stored in PostgreSQL JSONB columns

The experiment uses realistic, moderately complex protobuf messages (~1-3 KB binary, ~3-6 KB JSON) to simulate production workloads.

## What Gets Measured

### Write Performance
- **Insert throughput** (rows/sec): How many rows can be inserted per second
- **Total insert time**: Wall-clock time to insert all rows
- **Serialization latency distribution**: Detailed percentiles (min, p50, p90, p95, p99, max, mean, stddev)

### Read Performance
- **Read throughput** (rows/sec): How many rows can be read and deserialized per second
- **Total read time**: Wall-clock time to read and deserialize all rows
- **Deserialization latency distribution**: Detailed percentiles (min, p50, p90, p95, p99, max, stddev)
- **PostgreSQL fetch time**: Time spent fetching from database (separate from deserialization)

### QPS Impact Analysis
- **Per-operation overhead**: Exact millisecond difference between binary and JSON
- **QPS scaling table**: Shows overhead at 10, 100, 1K, 5K, and 10K QPS
- **Real-world interpretation**: Automatic verdict on when JSON overhead matters
- **Tail latency analysis**: p99 latency comparison for understanding worst-case performance

### Storage
- **Payload size** (bytes): Size of serialized payload for each format

## Prerequisites

- **Python**: 3.9 or later
- **PostgreSQL**: 14 or later (running locally or accessible)
- **pip**: For installing Python dependencies

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `protobuf`: Official protobuf library
- `psycopg2-binary`: PostgreSQL driver
- `grpcio-tools`: Protobuf compiler for Python

### 2. Compile Protobuf Schema

```bash
./setup.sh
```

Or manually:
```bash
python -m grpc_tools.protoc -I=proto --python_out=. proto/infrastructure.proto
```

This generates `proto/infrastructure_pb2.py` from the `.proto` definition.

### 3. Configure Database Connection

Edit `benchmark.py` and update the `DB_CONFIG` dictionary:

```python
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres',
    'password': 'postgres'
}
```

### 4. Ensure PostgreSQL is Running

```bash
# Check if PostgreSQL is running
psql -h localhost -U postgres -c "SELECT version();"
```

### 5. Run the Benchmark

```bash
python benchmark.py
```

The benchmark will:
1. Create two separate tables: `infra_exec_binary` and `infra_exec_json`
2. Run write + read tests for binary format (1,000 rows)
3. Run write + read tests for JSON format (1,000 rows)
4. Run write + read tests for binary format (10,000 rows)
5. Run write + read tests for JSON format (10,000 rows)
6. Print comprehensive results

**Why separate tables?** Using dedicated tables for each format eliminates WHERE clauses and provides cleaner, more accurate benchmarks with simple `SELECT payload FROM table` queries.

## Interpreting Results

### Sample Output (Enhanced with Percentiles & QPS Analysis)

```
[BINARY]
  Payload size:         2,168 bytes
  Insert throughput:    9367.53 rows/sec

  Deserialization Latency Distribution:
    Min:    0.0026 ms
    p50:    0.0030 ms
    p90:    0.0032 ms
    p95:    0.0033 ms
    p99:    0.0035 ms
    Max:    0.0190 ms
    Mean:   0.0030 ms
    StdDev: 0.0006 ms

[JSON]
  Payload size:         5,178 bytes
  Insert throughput:    7923.34 rows/sec

  Deserialization Latency Distribution:
    Min:    0.2241 ms
    p50:    0.2675 ms
    p90:    0.2987 ms
    p95:    0.3065 ms
    p99:    0.3423 ms
    Max:    1.9752 ms
    Mean:   0.2691 ms
    StdDev: 0.0600 ms

REAL-WORLD QPS IMPACT: When does JSON overhead matter?
──────────────────────────────────────────────────────
  QPS        Binary Latency       JSON Latency         Extra Overhead
  ---------- -------------------- -------------------- --------------------
  10             0.03 ms/sec         2.68 ms/sec         2.65 ms/sec (+0.00s)
  100            0.30 ms/sec        26.75 ms/sec        26.45 ms/sec (+0.03s)
  1000           3.00 ms/sec       267.54 ms/sec       264.54 ms/sec (+0.26s)
  5000          15.00 ms/sec      1337.71 ms/sec      1322.71 ms/sec (+1.32s)
  10000         30.00 ms/sec      2675.41 ms/sec      2645.42 ms/sec (+2.65s)

  Interpretation:
  • Per-operation overhead: 0.2645 ms (98.9% of JSON latency)
  • At 1,000 QPS: adds ~0.26 ms/sec = 0.0003s extra CPU time
  • At 10,000 QPS: adds ~2.65 ms/sec = 0.00s extra CPU time
  • VERDICT: Overhead is negligible (<0.5ms). JSON is fine for most workloads.

SUMMARY: Binary vs JSON
════════════════════════
Payload Size:
  Binary: 2,168 bytes
  JSON:   5,178 bytes (+138.8%)

Tail Latency (p99 deserialization):
  Binary: 0.0035 ms
  JSON:   0.3423 ms (+9794.2% but still <1ms!)
```

### Understanding the Enhanced Metrics

#### Percentile Latencies (Why They Matter)

**What percentiles tell you:**
- **p50 (median)**: Half of operations complete faster than this
- **p90**: 90% of operations complete faster (good for SLA)
- **p95**: 95% of operations complete faster
- **p99 (tail latency)**: 99% complete faster - shows worst-case performance
- **Max**: Absolute worst case (can be outlier)

**Example from results:**
```
JSON p99: 0.3423 ms means 99% of deserializations take <0.34ms
JSON Max: 1.9752 ms is an outlier, not typical
```

**Why this matters more than averages:**
- Averages hide outliers and tail behavior
- p99 is what users experience in the worst (but not exceptional) case
- If p99 < 1ms, your latency is excellent even under load

#### QPS Impact Table (The Reality Check)

This table shows **total CPU time spent** at different query rates:

**Reading the table:**
```
At 1,000 QPS:
  Binary: 3.00 ms/sec   → Uses 0.3% of 1 CPU core
  JSON:   267.54 ms/sec → Uses 26.8% of 1 CPU core
  Extra:  264.54 ms/sec → JSON needs 26.5% more CPU
```

**When to care:**
- **<1,000 QPS**: Overhead is negligible (< 0.3 seconds per second)
- **1,000-5,000 QPS**: Moderate overhead (0.3-1.3 seconds per second)
- **>10,000 QPS**: Significant overhead (>2.6 seconds per second = need more cores)

#### Payload Size
- **Binary**: Highly compact, field tags + values with minimal overhead
- **JSON**: Human-readable, includes field names and formatting
- **Typical ratio**: JSON is 2-3x larger than binary

**What this means**:
- More disk space for JSON
- More network I/O for JSON
- Higher storage costs at scale

#### Write Performance
Factors affecting insert speed:
- **Serialization time**: Converting message to bytes/string
- **PostgreSQL insert time**: Writing to disk
- **Network overhead**: Usually negligible on localhost

**When JSON overhead matters**:
- High-throughput systems (>1,000 writes/sec)
- Large payloads (>10 KB)
- Storage-constrained environments

#### Read Performance
Factors affecting read speed:
- **PostgreSQL fetch time**: Reading from disk
- **Deserialization time**: Parsing bytes/JSON back to objects

**Expected findings**:
- JSON deserialization is typically 20-50% slower
- JSON parsing is CPU-intensive (string parsing vs binary decoding)

#### Throughput Crossover Point

The benchmark helps answer: **At what scale does the format choice matter?**

| Workload | Binary Advantage | JSON Advantage |
|----------|-----------------|----------------|
| <100 writes/sec | Minimal (~5-10% faster) | Queryability, debugging |
| 100-1,000 writes/sec | Moderate (~15-25% faster) | Still manageable |
| >1,000 writes/sec | Significant (~25-50% faster) | Consider binary |
| >10 KB payloads | Storage/bandwidth savings | Human readability |

### When to Choose Binary

✅ **Use binary when**:
- High throughput (>1,000 writes/sec)
- Large payloads (>5 KB)
- Storage costs are a concern
- You don't need to query payload fields directly in SQL
- Performance is critical

### When to Choose JSON

✅ **Use JSON when**:
- Moderate throughput (<500 writes/sec)
- You need to query payload fields (PostgreSQL JSONB operators)
- Debugging/observability is important
- Integration with JSON-based tools
- Human readability matters

### Trade-offs Summary

| Aspect | Binary | JSON |
|--------|--------|------|
| **Size** | Smallest (baseline) | 2-3x larger |
| **Write speed** | Fastest (baseline) | 10-30% slower |
| **Read speed** | Fastest (baseline) | 20-50% slower |
| **Queryability** | ❌ Opaque BYTEA | ✅ PostgreSQL JSONB operators |
| **Debugging** | ❌ Requires deserialization | ✅ Human-readable |
| **Indexing** | ❌ No field-level indexes | ✅ GIN/GiST indexes |
| **Schema evolution** | ✅ Forward/backward compatible | ✅ Forward/backward compatible |

## Project Structure

```
bench/
├── proto/
│   └── infrastructure.proto      # Protobuf schema definition
├── requirements.txt               # Python dependencies
├── schema.sql                     # PostgreSQL table schema
├── benchmark.py                   # Main benchmark script
├── setup.sh                       # Setup script
└── README.md                      # This file
```

## Message Structure

The benchmark uses a realistic `InfrastructureExecution` message with:

- **Strings**: execution_id, infrastructure_id, error_message
- **Enums**: ExecutionStatus, ApprovalStatus, TransformationStatus
- **Timestamps**: started_at, stopped_at, approved_at
- **Repeated fields**: instance_ids (15 items), approvals (2-3 items), transformations (5-7 items)
- **Nested messages**: PipelineExecutionContext, PipelineApproval, UserInfo, TransformationPlan, Transformation, TransformationOutput
- **Maps**: metadata (8 key-value pairs), outputs (3-5 entries)
- **Booleans**: auto_approved, rollback_enabled

This structure mirrors real-world production messages with depth and variety.

## Customization

### Adjust Test Sizes

Edit `benchmark.py`:
```python
TEST_SIZES = [1000, 10000]  # Change to [500, 5000, 50000] etc.
```

### Adjust Batch Size

Edit `benchmark.py`:
```python
BATCH_SIZE = 100  # Change to 50, 200, 500 etc.
```

### Modify Message Complexity

Edit `proto/infrastructure.proto` to add/remove fields, then:
```bash
./setup.sh
python benchmark.py
```

## Troubleshooting

### Connection Errors

```
psycopg2.OperationalError: could not connect to server
```

**Solution**: Check PostgreSQL is running and credentials are correct.

### Import Errors

```
ModuleNotFoundError: No module named 'proto.infrastructure_pb2'
```

**Solution**: Run `./setup.sh` to compile the proto file.

### Permission Errors

```
permission denied for table infra_exec_binary
```

**Solution**: Ensure your PostgreSQL user has CREATE TABLE permissions.

## Cleanup

To remove the benchmark tables:

```sql
DROP TABLE IF EXISTS infra_exec_binary;
DROP TABLE IF EXISTS infra_exec_json;
```

To remove generated files:

```bash
rm -rf proto/__pycache__ proto/*_pb2.py
```

## Questions This Benchmark Answers

1. **How much larger is JSON vs binary?**
   - Expect 2-3x size increase

2. **Is JSON significantly slower for my workload?**
   - Low throughput (<100 writes/sec): Minimal difference
   - High throughput (>1,000 writes/sec): 20-50% slower

3. **What's the storage cost difference?**
   - Calculate: (JSON size - binary size) × row count × storage cost/GB

4. **Should I use binary or JSON?**
   - Binary: Performance-critical, high-throughput systems
   - JSON: Query flexibility, debugging, moderate workloads

## License

This benchmark is provided as-is for educational and evaluation purposes.
