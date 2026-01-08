#!/usr/bin/env python3
"""
PostgreSQL Database-Level Benchmark: Binary vs JSON
Measures ONLY database read/write performance (no serialization overhead)
"""

import time
import random
import statistics
import psycopg2
from datetime import datetime, timezone
from google.protobuf import timestamp_pb2
from google.protobuf import json_format

import infrastructure_pb2

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
# CONFIG
# ============================================================================

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres',
    'password': 'postgres'
}

TEST_ROWS = 10000       # For bulk operations
BATCH_SIZE = 100        # Batch size for bulk writes
SINGLE_OPS = 1000       # Number of single operations to test

# ============================================================================
# DATA GENERATION
# ============================================================================

def create_sample_message(execution_num=1):
    """Create a realistic InfrastructureExecution message"""
    msg = infrastructure_pb2.InfrastructureExecution()

    msg.execution_id = f"exec-{execution_num:06d}"
    msg.infrastructure_id = f"infra-prod-{execution_num % 100:03d}"
    msg.status = infrastructure_pb2.RUNNING
    msg.started_at.CopyFrom(timestamp_pb2.Timestamp())
    msg.stopped_at.CopyFrom(timestamp_pb2.Timestamp())
    msg.auto_approved = execution_num % 3 == 0
    msg.rollback_enabled = execution_num % 2 == 0

    # Instance IDs
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

    # Approvals
    for i in range(2 + (execution_num % 2)):
        approval = msg.approvals.add()
        approval.approval_id = f"approval-{execution_num}-{i}"
        approval.approver.user_id = f"user-{(execution_num + i) % 100}"
        approval.approver.name = f"User Name {(execution_num + i) % 100}"
        approval.approver.email = f"user{(execution_num + i) % 100}@example.com"
        approval.approver.role = "DevOps Engineer" if i == 0 else "Tech Lead"
        approval.approved_at.CopyFrom(timestamp_pb2.Timestamp())
        approval.comments = f"Approved infrastructure changes for execution {execution_num}"
        approval.approval_status = infrastructure_pb2.APPROVED

    # Transformation Plan
    plan = msg.transformation_plan
    plan.plan_id = f"plan-{execution_num}"
    plan.description = f"Infrastructure transformation plan for execution {execution_num}"
    plan.estimated_duration_seconds = 300 + (execution_num % 600)

    # Transformations
    for i in range(5 + (execution_num % 3)):
        trans = plan.transformations.add()
        trans.transformation_id = f"trans-{execution_num}-{i}"
        trans.transformation_type = ["CREATE", "UPDATE", "DELETE", "REPLACE"][i % 4]
        trans.config = f'{{"resource": "aws.ec2.instance", "action": "provision", "count": {i+1}}}'
        trans.order = i
        trans.status = infrastructure_pb2.TRANSFORMATION_COMPLETED if i < 3 else infrastructure_pb2.TRANSFORMATION_RUNNING

    # Transformation outputs
    for i in range(3 + (execution_num % 3)):
        output = plan.outputs[f"output-{i}"]
        output.output_id = f"out-{execution_num}-{i}"
        output.resource_type = ["EC2Instance", "LoadBalancer", "SecurityGroup", "VPC", "Subnet"][i % 5]
        output.resource_id = f"resource-{execution_num}-{i}"
        output.endpoints.extend([
            f"https://endpoint-{execution_num}-{i}-a.example.com",
            f"https://endpoint-{execution_num}-{i}-b.example.com"
        ])

    # Metadata
    msg.metadata["region"] = f"us-east-{execution_num % 3 + 1}"
    msg.metadata["environment"] = "production"
    msg.metadata["cost_center"] = f"cc-{execution_num % 10}"
    msg.metadata["team"] = f"team-{execution_num % 5}"
    msg.metadata["version"] = f"v1.{execution_num % 10}.{execution_num % 100}"
    msg.metadata["build_number"] = str(10000 + execution_num)
    msg.metadata["git_commit"] = f"abc123def456{execution_num:06d}"
    msg.metadata["deployed_by"] = f"user-{execution_num % 50}"

    return msg

# ============================================================================
# DATABASE SETUP
# ============================================================================

def setup_database(conn):
    """Create tables"""
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS infra_exec_binary")
        cur.execute("""
            CREATE TABLE infra_exec_binary (
                id BIGSERIAL PRIMARY KEY,
                payload BYTEA NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        cur.execute("DROP TABLE IF EXISTS infra_exec_json")
        cur.execute("""
            CREATE TABLE infra_exec_json (
                id BIGSERIAL PRIMARY KEY,
                payload JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
    conn.commit()


def clear_table(conn, table_name):
    """Clear all data from specified table"""
    with conn.cursor() as cur:
        cur.execute(f"TRUNCATE TABLE {table_name}")
    conn.commit()

# ============================================================================
# BENCHMARK
# ============================================================================

def benchmark_write(conn, table_name, payloads):
    """Measure ONLY database write time (INSERT)"""
    start = time.perf_counter()

    with conn.cursor() as cur:
        for i in range(0, len(payloads), BATCH_SIZE):
            batch = payloads[i:i + BATCH_SIZE]
            cur.executemany(
                f"INSERT INTO {table_name} (payload) VALUES (%s)",
                [(p,) for p in batch]
            )

    conn.commit()
    elapsed = time.perf_counter() - start

    return {
        'time_sec': elapsed,
        'throughput': len(payloads) / elapsed
    }


def benchmark_read(conn, table_name):
    """Measure ONLY database read time (SELECT)"""
    start = time.perf_counter()

    with conn.cursor() as cur:
        cur.execute(f"SELECT payload FROM {table_name}")
        rows = cur.fetchall()

    elapsed = time.perf_counter() - start

    return {
        'time_sec': elapsed,
        'throughput': len(rows) / elapsed,
        'row_count': len(rows)
    }


def benchmark_single_writes(conn, table_name, payloads, count=SINGLE_OPS):
    """Measure latency for single-row writes (one INSERT + COMMIT at a time)"""
    latencies = []
    total_start = time.perf_counter()

    with conn.cursor() as cur:
        for i in range(count):
            payload = payloads[i]

            start = time.perf_counter()
            cur.execute(f"INSERT INTO {table_name} (payload) VALUES (%s)", (payload,))
            conn.commit()
            elapsed = (time.perf_counter() - start) * 1000  # Convert to milliseconds

            latencies.append(elapsed)

    total_time = time.perf_counter() - total_start
    stats = calculate_statistics(latencies)
    stats['throughput'] = count / total_time
    stats['total_time'] = total_time

    return stats


def benchmark_single_reads(conn, table_name, count=SINGLE_OPS):
    """Measure latency for single-row reads (random IDs, one SELECT at a time)"""
    # Get all row IDs
    with conn.cursor() as cur:
        cur.execute(f"SELECT id FROM {table_name}")
        row_ids = [row[0] for row in cur.fetchall()]

    if len(row_ids) == 0:
        return {}

    latencies = []
    total_start = time.perf_counter()

    with conn.cursor() as cur:
        for i in range(count):
            random_id = random.choice(row_ids)

            start = time.perf_counter()
            cur.execute(f"SELECT payload FROM {table_name} WHERE id = %s", (random_id,))
            cur.fetchone()
            elapsed = (time.perf_counter() - start) * 1000  # Convert to milliseconds

            latencies.append(elapsed)

    total_time = time.perf_counter() - total_start
    stats = calculate_statistics(latencies)
    stats['throughput'] = count / total_time
    stats['total_time'] = total_time

    return stats

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 80)
    print("PostgreSQL Database-Level Benchmark: Binary vs JSON")
    print(f"Bulk operations: {TEST_ROWS:,} rows | Single operations: {SINGLE_OPS:,} iterations")
    print("=" * 80)

    # Connect and setup
    print("\nConnecting to PostgreSQL...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    setup_database(conn)
    print("✓ Connected and tables created")

    # Pre-generate all data (NOT counted in benchmark)
    print(f"\nGenerating {TEST_ROWS:,} messages...")
    binary_payloads = []
    json_payloads = []

    for i in range(TEST_ROWS):
        msg = create_sample_message(i + 1)
        binary_payloads.append(msg.SerializeToString())
        json_payloads.append(json_format.MessageToJson(msg, preserving_proto_field_name=True))

    print(f"✓ Data generated")
    print(f"  Binary payload size: {len(binary_payloads[0]):,} bytes")
    print(f"  JSON payload size:   {len(json_payloads[0]):,} bytes")

    # Benchmark BINARY
    print("\n" + "-" * 80)
    print("BINARY FORMAT (BYTEA)")
    print("-" * 80)

    print(f"Bulk write ({TEST_ROWS:,} rows)...")
    binary_bulk_write = benchmark_write(conn, 'infra_exec_binary', binary_payloads)
    print(f"✓ Bulk Write:   {binary_bulk_write['time_sec']:.3f}s | {binary_bulk_write['throughput']:,.0f} rows/sec")

    print(f"Bulk read ({TEST_ROWS:,} rows)...")
    binary_bulk_read = benchmark_read(conn, 'infra_exec_binary')
    print(f"✓ Bulk Read:    {binary_bulk_read['time_sec']:.3f}s | {binary_bulk_read['throughput']:,.0f} rows/sec")

    clear_table(conn, 'infra_exec_binary')

    print(f"Single writes ({SINGLE_OPS:,} operations)...")
    binary_single_write = benchmark_single_writes(conn, 'infra_exec_binary', binary_payloads, SINGLE_OPS)
    print(f"✓ Single Write: {binary_single_write['throughput']:,.0f} ops/sec | p50={binary_single_write['p50']:.3f}ms p90={binary_single_write['p90']:.3f}ms p95={binary_single_write['p95']:.3f}ms p99={binary_single_write['p99']:.3f}ms")

    print(f"Single reads ({SINGLE_OPS:,} operations)...")
    binary_single_read = benchmark_single_reads(conn, 'infra_exec_binary', SINGLE_OPS)
    print(f"✓ Single Read:  {binary_single_read['throughput']:,.0f} ops/sec | p50={binary_single_read['p50']:.3f}ms p90={binary_single_read['p90']:.3f}ms p95={binary_single_read['p95']:.3f}ms p99={binary_single_read['p99']:.3f}ms")

    # Benchmark JSON
    clear_table(conn, 'infra_exec_json')

    print("\n" + "-" * 80)
    print("JSON FORMAT (JSONB)")
    print("-" * 80)

    print(f"Bulk write ({TEST_ROWS:,} rows)...")
    json_bulk_write = benchmark_write(conn, 'infra_exec_json', json_payloads)
    print(f"✓ Bulk Write:   {json_bulk_write['time_sec']:.3f}s | {json_bulk_write['throughput']:,.0f} rows/sec")

    print(f"Bulk read ({TEST_ROWS:,} rows)...")
    json_bulk_read = benchmark_read(conn, 'infra_exec_json')
    print(f"✓ Bulk Read:    {json_bulk_read['time_sec']:.3f}s | {json_bulk_read['throughput']:,.0f} rows/sec")

    clear_table(conn, 'infra_exec_json')

    print(f"Single writes ({SINGLE_OPS:,} operations)...")
    json_single_write = benchmark_single_writes(conn, 'infra_exec_json', json_payloads, SINGLE_OPS)
    print(f"✓ Single Write: {json_single_write['throughput']:,.0f} ops/sec | p50={json_single_write['p50']:.3f}ms p90={json_single_write['p90']:.3f}ms p95={json_single_write['p95']:.3f}ms p99={json_single_write['p99']:.3f}ms")

    print(f"Single reads ({SINGLE_OPS:,} operations)...")
    json_single_read = benchmark_single_reads(conn, 'infra_exec_json', SINGLE_OPS)
    print(f"✓ Single Read:  {json_single_read['throughput']:,.0f} ops/sec | p50={json_single_read['p50']:.3f}ms p90={json_single_read['p90']:.3f}ms p95={json_single_read['p95']:.3f}ms p99={json_single_read['p99']:.3f}ms")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY: Binary vs JSON")
    print("=" * 80)

    print("\nPayload Size:")
    size_diff = ((len(json_payloads[0]) - len(binary_payloads[0])) / len(binary_payloads[0])) * 100
    print(f"  Binary: {len(binary_payloads[0]):,} bytes")
    print(f"  JSON:   {len(json_payloads[0]):,} bytes ({size_diff:+.1f}%)")

    print("\nBulk Write Performance:")
    throughput_diff = ((json_bulk_write['throughput'] - binary_bulk_write['throughput']) / binary_bulk_write['throughput']) * 100
    print(f"  Binary: {binary_bulk_write['throughput']:,.0f} rows/sec")
    print(f"  JSON:   {json_bulk_write['throughput']:,.0f} rows/sec ({throughput_diff:+.1f}%)")

    print("\nSingle Write Performance:")
    throughput_diff = ((json_single_write['throughput'] - binary_single_write['throughput']) / binary_single_write['throughput']) * 100
    latency_diff = ((json_single_write['p50'] - binary_single_write['p50']) / binary_single_write['p50']) * 100
    print(f"  Binary: {binary_single_write['throughput']:,.0f} ops/sec | p50={binary_single_write['p50']:.3f}ms")
    print(f"  JSON:   {json_single_write['throughput']:,.0f} ops/sec ({throughput_diff:+.1f}%) | p50={json_single_write['p50']:.3f}ms ({latency_diff:+.1f}%)")

    print("\nBulk Read Performance:")
    throughput_diff = ((json_bulk_read['throughput'] - binary_bulk_read['throughput']) / binary_bulk_read['throughput']) * 100
    print(f"  Binary: {binary_bulk_read['throughput']:,.0f} rows/sec")
    print(f"  JSON:   {json_bulk_read['throughput']:,.0f} rows/sec ({throughput_diff:+.1f}%)")

    print("\nSingle Read Performance:")
    throughput_diff = ((json_single_read['throughput'] - binary_single_read['throughput']) / binary_single_read['throughput']) * 100
    latency_diff = ((json_single_read['p50'] - binary_single_read['p50']) / binary_single_read['p50']) * 100
    print(f"  Binary: {binary_single_read['throughput']:,.0f} ops/sec | p50={binary_single_read['p50']:.3f}ms")
    print(f"  JSON:   {json_single_read['throughput']:,.0f} ops/sec ({throughput_diff:+.1f}%) | p50={json_single_read['p50']:.3f}ms ({latency_diff:+.1f}%)")

    print("\nTail Latencies (p99):")
    print(f"  Single Write - Binary: {binary_single_write['p99']:.3f} ms | JSON: {json_single_write['p99']:.3f} ms")
    print(f"  Single Read  - Binary: {binary_single_read['p99']:.3f} ms | JSON: {json_single_read['p99']:.3f} ms")

    print()
    conn.close()


if __name__ == '__main__':
    main()
