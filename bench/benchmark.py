#!/usr/bin/env python3
"""
PostgreSQL Protobuf Benchmark: Binary vs JSON
Compares performance of binary protobuf vs protobuf JSON in PostgreSQL
"""

import time
import json
import psycopg2
import statistics
from datetime import datetime, timezone
from google.protobuf import timestamp_pb2
from google.protobuf import json_format

import infrastructure_pb2

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres',
    'password': 'postgres'
}

BATCH_SIZE = 100  # Insert rows in batches
TEST_SIZES = [1000, 10000]  # Number of rows to test

# ============================================================================
# STATISTICS UTILITIES
# ============================================================================

def calculate_percentile(data, percentile):
    """Calculate percentile from a list of numbers"""
    if not data:
        return 0
    sorted_data = sorted(data)
    index = (len(sorted_data) - 1) * percentile / 100
    floor = int(index)
    ceil = floor + 1
    if ceil >= len(sorted_data):
        return sorted_data[floor]
    return sorted_data[floor] + (sorted_data[ceil] - sorted_data[floor]) * (index - floor)


def calculate_statistics(data):
    """Calculate comprehensive statistics from timing data"""
    if not data:
        return {}

    sorted_data = sorted(data)
    return {
        'min': min(data),
        'max': max(data),
        'mean': statistics.mean(data),
        'median': statistics.median(data),
        'stdev': statistics.stdev(data) if len(data) > 1 else 0,
        'p50': calculate_percentile(data, 50),
        'p90': calculate_percentile(data, 90),
        'p95': calculate_percentile(data, 95),
        'p99': calculate_percentile(data, 99)
    }


# ============================================================================
# PROTOBUF UTILITIES
# ============================================================================

def create_timestamp(dt=None):
    """Create a protobuf Timestamp from datetime"""
    if dt is None:
        dt = datetime.now(timezone.utc)
    ts = timestamp_pb2.Timestamp()
    ts.FromDatetime(dt)
    return ts


def create_sample_message(execution_num=1):
    """
    Create a realistic InfrastructureExecution message
    Target size: 1-3 KB binary, 3-6 KB JSON
    """
    msg = infrastructure_pb2.InfrastructureExecution()

    # Basic fields
    msg.execution_id = f"exec-{execution_num:06d}"
    msg.infrastructure_id = f"infra-prod-{execution_num % 100:03d}"
    msg.status = infrastructure_pb2.RUNNING
    msg.started_at.CopyFrom(create_timestamp())
    msg.stopped_at.CopyFrom(create_timestamp())
    msg.auto_approved = execution_num % 3 == 0
    msg.rollback_enabled = execution_num % 2 == 0
    msg.error_message = ""

    # Instance IDs (15-20 instances)
    for i in range(15):
        msg.instance_ids.append(f"i-{execution_num:06d}-{i:03d}")

    # Pipeline Context
    ctx = msg.context
    ctx.pipeline_id = f"pipeline-{execution_num % 50}"
    ctx.pipeline_name = f"Production Deployment Pipeline {execution_num % 50}"
    ctx.stage_id = f"stage-deploy-{execution_num % 10}"
    ctx.stage_name = f"Deploy Stage {execution_num % 10}"
    ctx.step_id = f"step-infra-{execution_num}"
    ctx.step_name = "Infrastructure Provisioning"
    ctx.tags.extend(["production", "automated", "critical", f"region-us-east-{execution_num % 3 + 1}"])
    ctx.organization_id = f"org-{execution_num % 10}"
    ctx.project_id = f"proj-{execution_num % 25}"
    ctx.account_id = f"acc-{execution_num % 5}"

    # Approvals (2-3 approvals)
    for i in range(2 + (execution_num % 2)):
        approval = msg.approvals.add()
        approval.approval_id = f"approval-{execution_num}-{i}"
        approval.approver.user_id = f"user-{(execution_num + i) % 100}"
        approval.approver.name = f"User Name {(execution_num + i) % 100}"
        approval.approver.email = f"user{(execution_num + i) % 100}@example.com"
        approval.approver.role = "DevOps Engineer" if i == 0 else "Tech Lead"
        approval.approved_at.CopyFrom(create_timestamp())
        approval.comments = f"Approved infrastructure changes for execution {execution_num}"
        approval.approval_status = infrastructure_pb2.APPROVED

    # Transformation Plan
    plan = msg.transformation_plan
    plan.plan_id = f"plan-{execution_num}"
    plan.description = f"Infrastructure transformation plan for execution {execution_num}"
    plan.estimated_duration_seconds = 300 + (execution_num % 600)

    # Transformations (5-7 transformations)
    for i in range(5 + (execution_num % 3)):
        trans = plan.transformations.add()
        trans.transformation_id = f"trans-{execution_num}-{i}"
        trans.transformation_type = ["CREATE", "UPDATE", "DELETE", "REPLACE"][i % 4]
        trans.config = f'{{"resource": "aws.ec2.instance", "action": "provision", "count": {i+1}}}'
        trans.order = i
        trans.status = infrastructure_pb2.TRANSFORMATION_COMPLETED if i < 3 else infrastructure_pb2.TRANSFORMATION_RUNNING

    # Transformation outputs (3-5 outputs)
    for i in range(3 + (execution_num % 3)):
        output = plan.outputs[f"output-{i}"]
        output.output_id = f"out-{execution_num}-{i}"
        output.resource_type = ["EC2Instance", "LoadBalancer", "SecurityGroup", "VPC", "Subnet"][i % 5]
        output.resource_id = f"resource-{execution_num}-{i}"
        output.endpoints.extend([
            f"https://endpoint-{execution_num}-{i}-a.example.com",
            f"https://endpoint-{execution_num}-{i}-b.example.com"
        ])

    # Metadata (8-10 key-value pairs)
    msg.metadata["region"] = f"us-east-{execution_num % 3 + 1}"
    msg.metadata["environment"] = "production"
    msg.metadata["cost_center"] = f"cc-{execution_num % 10}"
    msg.metadata["team"] = f"team-{execution_num % 5}"
    msg.metadata["version"] = f"v1.{execution_num % 10}.{execution_num % 100}"
    msg.metadata["build_number"] = str(10000 + execution_num)
    msg.metadata["git_commit"] = f"abc123def456{execution_num:06d}"
    msg.metadata["deployed_by"] = f"user-{execution_num % 50}"

    return msg


def serialize_binary(msg):
    """Serialize message to binary protobuf"""
    return msg.SerializeToString()


def serialize_json(msg):
    """Serialize message to JSON using protobuf's official JSON mapping"""
    return json_format.MessageToJson(msg, preserving_proto_field_name=True)


def deserialize_binary(data):
    """Deserialize binary protobuf to message"""
    msg = infrastructure_pb2.InfrastructureExecution()
    msg.ParseFromString(data)
    return msg


def deserialize_json(data):
    """
    Deserialize JSON to protobuf message

    Note: PostgreSQL JSONB returns data as a Python dict,
    but json_format.Parse() expects a JSON string.
    """
    msg = infrastructure_pb2.InfrastructureExecution()

    # If data is a dict (from PostgreSQL JSONB), convert to JSON string
    if isinstance(data, dict):
        data = json.dumps(data)

    json_format.Parse(data, msg)
    return msg


# ============================================================================
# DATABASE UTILITIES
# ============================================================================

def get_connection():
    """Create database connection"""
    return psycopg2.connect(**DB_CONFIG)


def setup_database(conn):
    """Setup database schema - creates separate tables for binary and JSON"""
    with conn.cursor() as cur:
        # Drop and recreate binary table
        cur.execute("DROP TABLE IF EXISTS infra_exec_binary")
        cur.execute("""
            CREATE TABLE infra_exec_binary (
                id BIGSERIAL PRIMARY KEY,
                payload BYTEA NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Drop and recreate JSON table
        cur.execute("DROP TABLE IF EXISTS infra_exec_json")
        cur.execute("""
            CREATE TABLE infra_exec_json (
                id BIGSERIAL PRIMARY KEY,
                payload JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
    conn.commit()
    print("✓ Database tables created (infra_exec_binary, infra_exec_json)")


def clear_table(conn, table_name):
    """Clear all data from specified table"""
    with conn.cursor() as cur:
        cur.execute(f"TRUNCATE TABLE {table_name}")
    conn.commit()


# ============================================================================
# BENCHMARK FUNCTIONS
# ============================================================================

def benchmark_writes(conn, format_type, row_count):
    """
    Benchmark write performance

    Args:
        conn: Database connection
        format_type: 'binary' or 'json'
        row_count: Number of rows to insert

    Returns:
        dict with metrics
    """
    print(f"\n--- Write Benchmark: {format_type.upper()} ({row_count:,} rows) ---")

    # Generate sample message and measure serialization
    sample_msg = create_sample_message(1)

    serialize_times = []
    payloads = []

    # Pre-generate and serialize all messages
    print("Generating and serializing messages...")
    for i in range(row_count):
        msg = create_sample_message(i + 1)

        start = time.perf_counter()
        if format_type == 'binary':
            payload = serialize_binary(msg)
        else:  # json
            payload = serialize_json(msg)
        serialize_time = (time.perf_counter() - start) * 1000  # ms

        serialize_times.append(serialize_time)
        payloads.append(payload)

    # Calculate serialization statistics
    serialize_stats = calculate_statistics(serialize_times)
    payload_size = len(payloads[0])

    # Insert in batches
    print(f"Inserting {row_count:,} rows in batches of {BATCH_SIZE}...")
    start_time = time.perf_counter()

    # Determine table name based on format
    table_name = 'infra_exec_binary' if format_type == 'binary' else 'infra_exec_json'

    with conn.cursor() as cur:
        for i in range(0, row_count, BATCH_SIZE):
            batch = payloads[i:i + BATCH_SIZE]

            cur.executemany(
                f"INSERT INTO {table_name} (payload) VALUES (%s)",
                [(p,) for p in batch]
            )

            if (i + BATCH_SIZE) % 1000 == 0:
                print(f"  Inserted {i + BATCH_SIZE:,} rows...")

    conn.commit()

    total_time = time.perf_counter() - start_time
    throughput = row_count / total_time

    print(f"✓ Completed in {total_time:.2f}s")

    return {
        'format': format_type,
        'row_count': row_count,
        'payload_size': payload_size,
        'total_write_time': total_time,
        'write_throughput': throughput,
        'serialize_stats': serialize_stats
    }


def benchmark_reads(conn, format_type, row_count):
    """
    Benchmark read performance

    Args:
        conn: Database connection
        format_type: 'binary' or 'json'
        row_count: Number of rows to read

    Returns:
        dict with metrics
    """
    print(f"\n--- Read Benchmark: {format_type.upper()} ({row_count:,} rows) ---")

    # Read all rows
    print(f"Reading {row_count:,} rows...")
    start_time = time.perf_counter()

    # Determine table name based on format
    table_name = 'infra_exec_binary' if format_type == 'binary' else 'infra_exec_json'

    with conn.cursor() as cur:
        cur.execute(f"SELECT payload FROM {table_name}")
        rows = cur.fetchall()

    fetch_time = time.perf_counter() - start_time
    print(f"✓ Fetched {len(rows):,} rows in {fetch_time:.2f}s")

    # Deserialize all payloads
    print("Deserializing payloads...")
    deserialize_times = []

    for row in rows:
        payload = row[0]

        start = time.perf_counter()
        if format_type == 'binary':
            msg = deserialize_binary(payload)
        else:  # json
            msg = deserialize_json(payload)
        deserialize_time = (time.perf_counter() - start) * 1000  # ms

        deserialize_times.append(deserialize_time)

    # Calculate deserialization statistics
    deserialize_stats = calculate_statistics(deserialize_times)

    total_time = fetch_time + (sum(deserialize_times) / 1000)
    throughput = len(rows) / total_time

    print(f"✓ Completed in {total_time:.2f}s")

    return {
        'format': format_type,
        'row_count': row_count,
        'total_read_time': total_time,
        'read_throughput': throughput,
        'fetch_time': fetch_time,
        'deserialize_stats': deserialize_stats
    }


# ============================================================================
# RESULTS REPORTING
# ============================================================================

def print_latency_percentiles(stats, label):
    """Print detailed latency percentile table"""
    print(f"\n  {label} Latency Distribution:")
    print(f"    Min:    {stats['min']:.4f} ms")
    print(f"    p50:    {stats['p50']:.4f} ms")
    print(f"    p90:    {stats['p90']:.4f} ms")
    print(f"    p95:    {stats['p95']:.4f} ms")
    print(f"    p99:    {stats['p99']:.4f} ms")
    print(f"    Max:    {stats['max']:.4f} ms")
    print(f"    Mean:   {stats['mean']:.4f} ms")
    print(f"    StdDev: {stats['stdev']:.4f} ms")


def print_qps_impact(binary_latency_ms, json_latency_ms, operation="read"):
    """Print QPS impact analysis showing when JSON overhead matters"""
    print(f"\n  QPS Impact Analysis ({operation.title()} Operations):")
    print(f"  {'QPS':<10} {'Binary Latency':<20} {'JSON Latency':<20} {'Extra Overhead':<20}")
    print(f"  {'-'*10} {'-'*20} {'-'*20} {'-'*20}")

    test_qps = [10, 100, 1000, 5000, 10000]
    overhead_per_op = json_latency_ms - binary_latency_ms

    for qps in test_qps:
        binary_total = binary_latency_ms * qps
        json_total = json_latency_ms * qps
        overhead_total = overhead_per_op * qps

        print(f"  {qps:<10} {binary_total:>8.2f} ms/sec     {json_total:>8.2f} ms/sec     {overhead_total:>8.2f} ms/sec (+{(overhead_total/1000):.2f}s)")


def print_results(results):
    """Print comprehensive benchmark results with percentiles and QPS analysis"""
    print("\n" + "=" * 100)
    print("BENCHMARK RESULTS - DETAILED ANALYSIS")
    print("=" * 100)

    for size in TEST_SIZES:
        print(f"\n{'='*100}")
        print(f"TEST SIZE: {size:,} ROWS")
        print(f"{'='*100}")

        size_results = [r for r in results if r.get('row_count') == size]

        # Write benchmarks
        print(f"\n{'─'*100}")
        print("WRITE PERFORMANCE")
        print(f"{'─'*100}")

        for r in size_results:
            if 'total_write_time' in r:
                print(f"\n[{r['format'].upper()}]")
                print(f"  Payload size:         {r['payload_size']:,} bytes")
                print(f"  Insert throughput:    {r['write_throughput']:.2f} rows/sec")
                print(f"  Total insert time:    {r['total_write_time']:.2f} sec")

                if 'serialize_stats' in r:
                    print_latency_percentiles(r['serialize_stats'], "Serialization")

        # Read benchmarks
        print(f"\n{'─'*100}")
        print("READ PERFORMANCE")
        print(f"{'─'*100}")

        binary_read = None
        json_read = None

        for r in size_results:
            if 'total_read_time' in r:
                print(f"\n[{r['format'].upper()}]")
                print(f"  Read throughput:      {r['read_throughput']:.2f} rows/sec")
                print(f"  Total read time:      {r['total_read_time']:.2f} sec")
                print(f"  PostgreSQL fetch:     {r['fetch_time']:.4f} sec")

                if 'deserialize_stats' in r:
                    print_latency_percentiles(r['deserialize_stats'], "Deserialization")

                if r['format'] == 'binary':
                    binary_read = r
                else:
                    json_read = r

        # QPS Impact Analysis
        if binary_read and json_read:
            print(f"\n{'─'*100}")
            print("REAL-WORLD QPS IMPACT: When does JSON overhead matter?")
            print(f"{'─'*100}")

            binary_p50 = binary_read['deserialize_stats']['p50']
            json_p50 = json_read['deserialize_stats']['p50']

            print_qps_impact(binary_p50, json_p50, "read")

            print(f"\n  Interpretation:")
            overhead_ms = json_p50 - binary_p50
            print(f"  • Per-operation overhead: {overhead_ms:.4f} ms ({(overhead_ms/json_p50*100):.1f}% of JSON latency)")
            print(f"  • At 1,000 QPS: adds ~{overhead_ms:.2f} ms/sec = {(overhead_ms/1000):.4f}s extra CPU time")
            print(f"  • At 10,000 QPS: adds ~{overhead_ms*10:.2f} ms/sec = {(overhead_ms*10/1000):.2f}s extra CPU time")

            if overhead_ms < 0.5:
                print(f"  • VERDICT: Overhead is negligible (<0.5ms). JSON is fine for most workloads.")
            elif overhead_ms < 2:
                print(f"  • VERDICT: Overhead is low (<2ms). JSON acceptable unless you're doing >10K QPS.")
            else:
                print(f"  • VERDICT: Overhead is significant (>{overhead_ms:.1f}ms). Consider binary for high-throughput systems.")

    # Summary comparison
    print(f"\n{'='*100}")
    print("SUMMARY: Binary vs JSON")
    print(f"{'='*100}")

    binary_write = [r for r in results if r['format'] == 'binary' and 'total_write_time' in r]
    json_write = [r for r in results if r['format'] == 'json' and 'total_write_time' in r]

    if binary_write and json_write:
        b = binary_write[0]
        j = json_write[0]

        size_diff = ((j['payload_size'] - b['payload_size']) / b['payload_size']) * 100
        write_diff = ((j['total_write_time'] - b['total_write_time']) / b['total_write_time']) * 100

        print(f"\nPayload Size:")
        print(f"  Binary: {b['payload_size']:,} bytes")
        print(f"  JSON:   {j['payload_size']:,} bytes ({size_diff:+.1f}%)")

        print(f"\nWrite Performance:")
        print(f"  Binary throughput: {b['write_throughput']:.2f} rows/sec")
        print(f"  JSON throughput:   {j['write_throughput']:.2f} rows/sec ({write_diff:+.1f}%)")

        binary_read = [r for r in results if r['format'] == 'binary' and 'total_read_time' in r]
        json_read = [r for r in results if r['format'] == 'json' and 'total_read_time' in r]

        if binary_read and json_read:
            br = binary_read[0]
            jr = json_read[0]

            read_diff = ((jr['total_read_time'] - br['total_read_time']) / br['total_read_time']) * 100

            print(f"\nRead Performance:")
            print(f"  Binary throughput: {br['read_throughput']:.2f} rows/sec")
            print(f"  JSON throughput:   {jr['read_throughput']:.2f} rows/sec ({read_diff:+.1f}%)")

            binary_p99 = br['deserialize_stats']['p99']
            json_p99 = jr['deserialize_stats']['p99']

            print(f"\nTail Latency (p99 deserialization):")
            print(f"  Binary: {binary_p99:.4f} ms")
            print(f"  JSON:   {json_p99:.4f} ms ({((json_p99-binary_p99)/binary_p99*100):+.1f}%)")

    print("\n")


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 80)
    print("PostgreSQL Protobuf Benchmark: Binary vs JSON")
    print("=" * 80)

    # Connect to database
    print("\nConnecting to PostgreSQL...")
    conn = get_connection()
    conn.autocommit = False
    print(f"✓ Connected to {DB_CONFIG['database']}@{DB_CONFIG['host']}")

    # Setup database
    setup_database(conn)

    results = []

    # Run benchmarks for each test size
    for row_count in TEST_SIZES:
        print(f"\n{'=' * 80}")
        print(f"TESTING WITH {row_count:,} ROWS")
        print(f"{'=' * 80}")

        # Binary benchmarks
        clear_table(conn, 'infra_exec_binary')
        results.append(benchmark_writes(conn, 'binary', row_count))
        results.append(benchmark_reads(conn, 'binary', row_count))

        # JSON benchmarks
        clear_table(conn, 'infra_exec_json')
        results.append(benchmark_writes(conn, 'json', row_count))
        results.append(benchmark_reads(conn, 'json', row_count))

    # Print final results
    print_results(results)

    # Cleanup
    conn.close()
    print("✓ Connection closed")


if __name__ == '__main__':
    main()
