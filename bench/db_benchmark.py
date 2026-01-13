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


def aggregate_iteration_results(iteration_results, metric_key):
    """
    Aggregate a specific metric across multiple benchmark iterations

    Args:
        iteration_results: List of result dicts from multiple iterations
        metric_key: Key to aggregate (e.g., 'throughput', 'total_time')

    Returns:
        dict with median, mean, stddev, min, max
    """
    values = [r[metric_key] for r in iteration_results if metric_key in r]

    if not values:
        return {}

    return {
        'median': statistics.median(values),
        'mean': statistics.mean(values),
        'stddev': statistics.stdev(values) if len(values) > 1 else 0,
        'min': min(values),
        'max': max(values),
        'values': values  # Keep raw values for debugging
    }


def find_median_run(iteration_results, metric_key):
    """
    Find the iteration that has the median value for a given metric
    Returns the full result dict of that iteration
    """
    if not iteration_results:
        return None

    # Extract metric values with their index
    indexed_values = [(i, r[metric_key]) for i, r in enumerate(iteration_results) if metric_key in r]

    if not indexed_values:
        return iteration_results[0]

    # Sort by value and find median
    indexed_values.sort(key=lambda x: x[1])
    median_idx = len(indexed_values) // 2

    return iteration_results[indexed_values[median_idx][0]]


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

# Multi-iteration configuration
BENCHMARK_ITERATIONS = 3  # Number of measured benchmark runs
WARMUP_ITERATIONS = 1     # Number of warmup runs (discarded from results)

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
# MULTI-ITERATION BENCHMARK WRAPPERS
# ============================================================================

def run_benchmark_with_iterations(benchmark_func, *args, metric_key='throughput', **kwargs):
    """
    Run a benchmark function multiple times with warmup

    Args:
        benchmark_func: The benchmark function to run
        *args: Positional arguments to pass to benchmark function
        metric_key: Key to use for finding median run (default: 'throughput')
        **kwargs: Keyword arguments to pass to benchmark function

    Returns:
        dict with:
            - 'iterations': list of all measured iteration results
            - 'aggregated': aggregated metrics across iterations
            - 'median_run': the full result from the median iteration
    """
    print(f"  Running {WARMUP_ITERATIONS} warmup + {BENCHMARK_ITERATIONS} measured iterations...")

    # Warmup iterations (discarded)
    for i in range(WARMUP_ITERATIONS):
        print(f"    Warmup {i+1}/{WARMUP_ITERATIONS}...", end=' ')
        benchmark_func(*args, **kwargs)
        print("✓")

    # Measured iterations
    iteration_results = []
    for i in range(BENCHMARK_ITERATIONS):
        print(f"    Iteration {i+1}/{BENCHMARK_ITERATIONS}...", end=' ')
        result = benchmark_func(*args, **kwargs)
        iteration_results.append(result)
        if metric_key in result:
            print(f"✓ ({result[metric_key]:.2f})")
        else:
            print("✓")

    # Find median run (use its detailed stats like percentiles)
    median_run = find_median_run(iteration_results, metric_key)

    # Aggregate key metrics across iterations
    aggregated = {}
    if iteration_results:
        # Get all keys from first result to know what to aggregate
        sample_result = iteration_results[0]
        for key in sample_result:
            # Skip nested dicts and non-numeric values
            if isinstance(sample_result[key], (int, float)):
                aggregated[key] = aggregate_iteration_results(iteration_results, key)

    return {
        'iterations': iteration_results,
        'aggregated': aggregated,
        'median_run': median_run
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 80)
    print("PostgreSQL Database-Level Benchmark: Binary vs JSON")
    print(f"Bulk operations: {TEST_ROWS:,} rows | Single operations: {SINGLE_OPS:,} iterations")
    print(f"Multi-iteration mode: {WARMUP_ITERATIONS} warmup + {BENCHMARK_ITERATIONS} measured runs")
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

    print(f"\nBulk write ({TEST_ROWS:,} rows)...")
    binary_bulk_write_results = run_benchmark_with_iterations(
        benchmark_write, conn, 'infra_exec_binary', binary_payloads, metric_key='throughput'
    )
    bw_agg = binary_bulk_write_results['aggregated']['throughput']
    print(f"  ✓ Throughput: median={bw_agg['median']:,.0f} rows/s | mean={bw_agg['mean']:,.0f} | stddev={bw_agg['stddev']:,.0f} | [{bw_agg['min']:,.0f}–{bw_agg['max']:,.0f}]")

    print(f"\nBulk read ({TEST_ROWS:,} rows)...")
    binary_bulk_read_results = run_benchmark_with_iterations(
        benchmark_read, conn, 'infra_exec_binary', metric_key='throughput'
    )
    br_agg = binary_bulk_read_results['aggregated']['throughput']
    print(f"  ✓ Throughput: median={br_agg['median']:,.0f} rows/s | mean={br_agg['mean']:,.0f} | stddev={br_agg['stddev']:,.0f} | [{br_agg['min']:,.0f}–{br_agg['max']:,.0f}]")

    clear_table(conn, 'infra_exec_binary')

    print(f"\nSingle writes ({SINGLE_OPS:,} operations)...")
    binary_single_write_results = run_benchmark_with_iterations(
        benchmark_single_writes, conn, 'infra_exec_binary', binary_payloads, SINGLE_OPS, metric_key='throughput'
    )
    bsw = binary_single_write_results['median_run']  # Use median run for percentiles
    bsw_agg = binary_single_write_results['aggregated']['throughput']
    print(f"  ✓ Throughput: median={bsw_agg['median']:,.0f} ops/s | mean={bsw_agg['mean']:,.0f} | stddev={bsw_agg['stddev']:,.0f}")
    print(f"  ✓ Latency (median run): p50={bsw['p50']:.3f}ms | p90={bsw['p90']:.3f}ms | p95={bsw['p95']:.3f}ms | p99={bsw['p99']:.3f}ms")

    print(f"\nSingle reads ({SINGLE_OPS:,} operations)...")
    binary_single_read_results = run_benchmark_with_iterations(
        benchmark_single_reads, conn, 'infra_exec_binary', SINGLE_OPS, metric_key='throughput'
    )
    bsr = binary_single_read_results['median_run']
    bsr_agg = binary_single_read_results['aggregated']['throughput']
    print(f"  ✓ Throughput: median={bsr_agg['median']:,.0f} ops/s | mean={bsr_agg['mean']:,.0f} | stddev={bsr_agg['stddev']:,.0f}")
    print(f"  ✓ Latency (median run): p50={bsr['p50']:.3f}ms | p90={bsr['p90']:.3f}ms | p95={bsr['p95']:.3f}ms | p99={bsr['p99']:.3f}ms")

    # Benchmark JSON
    clear_table(conn, 'infra_exec_json')

    print("\n" + "-" * 80)
    print("JSON FORMAT (JSONB)")
    print("-" * 80)

    print(f"\nBulk write ({TEST_ROWS:,} rows)...")
    json_bulk_write_results = run_benchmark_with_iterations(
        benchmark_write, conn, 'infra_exec_json', json_payloads, metric_key='throughput'
    )
    jw_agg = json_bulk_write_results['aggregated']['throughput']
    print(f"  ✓ Throughput: median={jw_agg['median']:,.0f} rows/s | mean={jw_agg['mean']:,.0f} | stddev={jw_agg['stddev']:,.0f} | [{jw_agg['min']:,.0f}–{jw_agg['max']:,.0f}]")

    print(f"\nBulk read ({TEST_ROWS:,} rows)...")
    json_bulk_read_results = run_benchmark_with_iterations(
        benchmark_read, conn, 'infra_exec_json', metric_key='throughput'
    )
    jr_agg = json_bulk_read_results['aggregated']['throughput']
    print(f"  ✓ Throughput: median={jr_agg['median']:,.0f} rows/s | mean={jr_agg['mean']:,.0f} | stddev={jr_agg['stddev']:,.0f} | [{jr_agg['min']:,.0f}–{jr_agg['max']:,.0f}]")

    clear_table(conn, 'infra_exec_json')

    print(f"\nSingle writes ({SINGLE_OPS:,} operations)...")
    json_single_write_results = run_benchmark_with_iterations(
        benchmark_single_writes, conn, 'infra_exec_json', json_payloads, SINGLE_OPS, metric_key='throughput'
    )
    jsw = json_single_write_results['median_run']
    jsw_agg = json_single_write_results['aggregated']['throughput']
    print(f"  ✓ Throughput: median={jsw_agg['median']:,.0f} ops/s | mean={jsw_agg['mean']:,.0f} | stddev={jsw_agg['stddev']:,.0f}")
    print(f"  ✓ Latency (median run): p50={jsw['p50']:.3f}ms | p90={jsw['p90']:.3f}ms | p95={jsw['p95']:.3f}ms | p99={jsw['p99']:.3f}ms")

    print(f"\nSingle reads ({SINGLE_OPS:,} operations)...")
    json_single_read_results = run_benchmark_with_iterations(
        benchmark_single_reads, conn, 'infra_exec_json', SINGLE_OPS, metric_key='throughput'
    )
    jsr = json_single_read_results['median_run']
    jsr_agg = json_single_read_results['aggregated']['throughput']
    print(f"  ✓ Throughput: median={jsr_agg['median']:,.0f} ops/s | mean={jsr_agg['mean']:,.0f} | stddev={jsr_agg['stddev']:,.0f}")
    print(f"  ✓ Latency (median run): p50={jsr['p50']:.3f}ms | p90={jsr['p90']:.3f}ms | p95={jsr['p95']:.3f}ms | p99={jsr['p99']:.3f}ms")

    # Summary
    print("\n" + "=" * 80)
    print(f"SUMMARY: Binary vs JSON ({BENCHMARK_ITERATIONS} iterations)")
    print("=" * 80)

    print("\nPayload Size:")
    size_diff = ((len(json_payloads[0]) - len(binary_payloads[0])) / len(binary_payloads[0])) * 100
    print(f"  Binary: {len(binary_payloads[0]):,} bytes")
    print(f"  JSON:   {len(json_payloads[0]):,} bytes ({size_diff:+.1f}%)")

    print("\nBulk Write Performance (median):")
    throughput_diff = ((jw_agg['median'] - bw_agg['median']) / bw_agg['median']) * 100
    print(f"  Binary: {bw_agg['median']:,.0f} rows/sec | stability: {(bw_agg['stddev']/bw_agg['mean']*100):.1f}% CV")
    print(f"  JSON:   {jw_agg['median']:,.0f} rows/sec ({throughput_diff:+.1f}%) | stability: {(jw_agg['stddev']/jw_agg['mean']*100):.1f}% CV")

    print("\nSingle Write Performance (median):")
    throughput_diff = ((jsw_agg['median'] - bsw_agg['median']) / bsw_agg['median']) * 100
    latency_diff = ((jsw['p50'] - bsw['p50']) / bsw['p50']) * 100
    print(f"  Binary: {bsw_agg['median']:,.0f} ops/sec | p50={bsw['p50']:.3f}ms | stability: {(bsw_agg['stddev']/bsw_agg['mean']*100):.1f}% CV")
    print(f"  JSON:   {jsw_agg['median']:,.0f} ops/sec ({throughput_diff:+.1f}%) | p50={jsw['p50']:.3f}ms ({latency_diff:+.1f}%) | stability: {(jsw_agg['stddev']/jsw_agg['mean']*100):.1f}% CV")

    print("\nBulk Read Performance (median):")
    throughput_diff = ((jr_agg['median'] - br_agg['median']) / br_agg['median']) * 100
    print(f"  Binary: {br_agg['median']:,.0f} rows/sec | stability: {(br_agg['stddev']/br_agg['mean']*100):.1f}% CV")
    print(f"  JSON:   {jr_agg['median']:,.0f} rows/sec ({throughput_diff:+.1f}%) | stability: {(jr_agg['stddev']/jr_agg['mean']*100):.1f}% CV")

    print("\nSingle Read Performance (median):")
    throughput_diff = ((jsr_agg['median'] - bsr_agg['median']) / bsr_agg['median']) * 100
    latency_diff = ((jsr['p50'] - bsr['p50']) / bsr['p50']) * 100
    print(f"  Binary: {bsr_agg['median']:,.0f} ops/sec | p50={bsr['p50']:.3f}ms | stability: {(bsr_agg['stddev']/bsr_agg['mean']*100):.1f}% CV")
    print(f"  JSON:   {jsr_agg['median']:,.0f} ops/sec ({throughput_diff:+.1f}%) | p50={jsr['p50']:.3f}ms ({latency_diff:+.1f}%) | stability: {(jsr_agg['stddev']/jsr_agg['mean']*100):.1f}% CV")

    print("\nTail Latencies (p99, median run):")
    print(f"  Single Write - Binary: {bsw['p99']:.3f} ms | JSON: {jsw['p99']:.3f} ms")
    print(f"  Single Read  - Binary: {bsr['p99']:.3f} ms | JSON: {jsr['p99']:.3f} ms")

    print("\nStability Assessment:")
    print("  (CV = Coefficient of Variation, lower is more stable)")
    def assess_stability(cv):
        if cv < 5:
            return "Excellent (<5%)"
        elif cv < 10:
            return "Good (<10%)"
        elif cv < 15:
            return "Fair (<15%)"
        else:
            return f"Variable ({cv:.1f}%)"

    print(f"  Binary bulk write:  {assess_stability(bw_agg['stddev']/bw_agg['mean']*100)}")
    print(f"  JSON bulk write:    {assess_stability(jw_agg['stddev']/jw_agg['mean']*100)}")
    print(f"  Binary single read: {assess_stability(bsr_agg['stddev']/bsr_agg['mean']*100)}")
    print(f"  JSON single read:   {assess_stability(jsr_agg['stddev']/jsr_agg['mean']*100)}")

    print()
    conn.close()


if __name__ == '__main__':
    main()
