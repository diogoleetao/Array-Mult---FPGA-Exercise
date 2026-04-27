"""FPGA vs ARM CPU benchmark for array multiply — runs on Ultra96-V2"""

import numpy as np
import time
import platform
import csv
from hw_config import MAX_ARRAY_SIZE, SCALAR, WARMUP, BENCH_ARRAY_SIZES
from hw_driver import ArrayMultDriver

N_RUNS = 10000  # number of runs for each benchmark

# --- Setup hardware ---
print("Loading overlay...")
hw = ArrayMultDriver(timing=True)
hw.set_scalar(SCALAR)

print(f"Platform:    {platform.system()} {platform.machine()}")
print(f"Scalar:      {SCALAR}")
print(f"Interface:   AXI Stream + DMA (v2, TLAST), 99 MHz")
print(f"Array sizes: {BENCH_ARRAY_SIZES}")
print(f"Runs:        {N_RUNS}")
print()
hw.print_setup_times()
print()


def bench(func, warmup, n_runs):
    for _ in range(warmup):
        func()
    times = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        func()
        times.append((time.perf_counter() - t0) * 1e6)
    return np.array(times)


# Prepare FPGA input
for i in range(MAX_ARRAY_SIZE):
    hw.a[i] = i + 1
hw.a.sync_to_device()

rows = []

# --- FPGA benchmark ---
for size in BENCH_ARRAY_SIZES:
    hw.set_array_size(size)
    print(f"FPGA size={size}...")

    # Setup once (timed separately) — DMA reset + address config
    t0 = time.perf_counter()
    hw.setup()
    setup_us = (time.perf_counter() - t0) * 1e6
    print(f"  Setup: {setup_us:.1f} us")

    # Benchmark only transfer+compute (run)
    fpga_times = bench(hw.run, WARMUP, N_RUNS)
    rows.append({
        "array_size": size, "n_runs": N_RUNS, "method": "FPGA (DMA)",
        "mean_us": np.mean(fpga_times), "median_us": np.median(fpga_times),
        "min_us": np.min(fpga_times), "max_us": np.max(fpga_times),
        "p1_us": np.percentile(fpga_times, 1), "p99_us": np.percentile(fpga_times, 99),
        "setup_us": setup_us,
    })

    # Verify correctness at this size
    hw.b.sync_from_device()
    errors = sum(1 for i in range(size) if hw.b[i] != (i + 1) * SCALAR)
    print(f"  Correctness: {'PASS' if errors == 0 else f'FAIL ({errors} errors)'}")
print()

# --- CPU benchmarks ---
for size in BENCH_ARRAY_SIZES:
    a_np = np.arange(1, size + 1, dtype=np.int32)
    numpy_times = bench(lambda: a_np * SCALAR, WARMUP, N_RUNS)

    a_list = list(range(1, size + 1))
    python_times = bench(lambda: [x * SCALAR for x in a_list], WARMUP, N_RUNS)

    rows.append({
        "array_size": size, "n_runs": N_RUNS, "method": "CPU NumPy",
        "mean_us": np.mean(numpy_times), "median_us": np.median(numpy_times),
        "min_us": np.min(numpy_times), "max_us": np.max(numpy_times),
        "p1_us": np.percentile(numpy_times, 1), "p99_us": np.percentile(numpy_times, 99),
        "setup_us": 0,
    })
    rows.append({
        "array_size": size, "n_runs": N_RUNS, "method": "CPU Python loop",
        "mean_us": np.mean(python_times), "median_us": np.median(python_times),
        "min_us": np.min(python_times), "max_us": np.max(python_times),
        "p1_us": np.percentile(python_times, 1), "p99_us": np.percentile(python_times, 99),
        "setup_us": 0,
    })

# --- Print table ---
print(f"{'Size':>6} {'Method':<16} {'Mean':>8} {'Median':>8} {'Min':>8} {'P99':>8} {'Setup':>8}  (us)")
print("-" * 78)
for r in rows:
    setup_str = f"{r['setup_us']:>8.1f}" if r['setup_us'] > 0 else f"{'—':>8}"
    print(f"{r['array_size']:>6} {r['method']:<16} "
          f"{r['mean_us']:>8.2f} {r['median_us']:>8.2f} {r['min_us']:>8.2f} {r['p99_us']:>8.2f} {setup_str}")
print()

# --- Power measurement ---
# Power measured over a fixed time window (not per-run) because each individual run is shorter than the sensor update rate (~1ms).
# Running continuously for POWER_DURATION seconds keeps the CPU active long enough for the sensor to capture real active power.
POWER_IDLE_SAMPLES = 20
POWER_IDLE_INTERVAL = 0.05   # seconds between idle samples
POWER_DURATION = 2.0         # seconds of continuous activity
POWER_SAMPLE_INTERVAL = 0.05 # read sensor every ~50ms (no sleep, just a check)

power_rows = []

try:
    from pynq import get_rails
    rails = get_rails()

    def read_total_power():
        return sum(r.power.value for r in rails.values() if r.power is not None)

    def measure_power(run_func, method_name):
        """Run func continuously for POWER_DURATION, sample power periodically."""
        samples = []
        runs_done = 0
        t_start = time.perf_counter()
        t_next = t_start + POWER_SAMPLE_INTERVAL
        while time.perf_counter() - t_start < POWER_DURATION:
            run_func()
            runs_done += 1
            if time.perf_counter() >= t_next:
                samples.append(read_total_power())
                t_next += POWER_SAMPLE_INTERVAL
        active = np.mean(samples)
        print(f"  {method_name}: {active:.3f} W ({len(samples)} samples, {runs_done} runs)")
        return active, len(samples), runs_done

    # Idle power
    time.sleep(1)
    idle_samples = []
    for _ in range(POWER_IDLE_SAMPLES):
        idle_samples.append(read_total_power())
        time.sleep(POWER_IDLE_INTERVAL)
    idle = np.mean(idle_samples)

    print(f"Power ({POWER_DURATION}s window per method):")
    print(f"  Idle: {idle:.3f} W ({POWER_IDLE_SAMPLES} samples)")

    # FPGA power — setup once, then run repeatedly
    hw.set_array_size(MAX_ARRAY_SIZE)
    hw.setup()
    fpga_active, fpga_n, fpga_runs = measure_power(hw.run, "FPGA (DMA)")
    power_rows.append({"method": "FPGA (DMA)", "idle_w": idle, "active_w": fpga_active,
                        "delta_w": fpga_active - idle, "samples": fpga_n, "runs": fpga_runs})

    # CPU NumPy power
    a_pwr = np.arange(1, MAX_ARRAY_SIZE + 1, dtype=np.int32)
    numpy_active, numpy_n, numpy_runs = measure_power(lambda: a_pwr * SCALAR, "CPU NumPy")
    power_rows.append({"method": "CPU NumPy", "idle_w": idle, "active_w": numpy_active,
                        "delta_w": numpy_active - idle, "samples": numpy_n, "runs": numpy_runs})

    # CPU Python loop power
    a_list = list(range(1, MAX_ARRAY_SIZE + 1))
    python_active, python_n, python_runs = measure_power(
        lambda: [x * SCALAR for x in a_list], "CPU Python loop")
    power_rows.append({"method": "CPU Python loop", "idle_w": idle, "active_w": python_active,
                        "delta_w": python_active - idle, "samples": python_n, "runs": python_runs})

    print()
    for r in power_rows:
        print(f"  {r['method']:<16} delta = {r['delta_w']:.3f} W")

except Exception as e:
    print(f"Power: not available on this board ({e})")
print()

# --- Save CSVs ---
csv_path = "results/bench_fpga_results.csv"
with open(csv_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
print(f"Results saved to {csv_path}")

if power_rows:
    power_csv = "results/bench_power_results.csv"
    with open(power_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=power_rows[0].keys())
        writer.writeheader()
        writer.writerows(power_rows)
    print(f"Power results saved to {power_csv}")

hw.free()
