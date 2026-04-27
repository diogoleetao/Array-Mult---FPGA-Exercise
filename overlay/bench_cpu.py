"""CPU-only benchmark for array multiply — runs on any machine."""

import numpy as np
import time
import platform
import sys
import csv
from hw_config import SCALAR, WARMUP, BENCH_ARRAY_SIZES

N_RUNS = 10000  # number of runs for each benchmark

print(f"Platform:    {platform.system()} {platform.machine()}")
print(f"Processor:   {platform.processor()}")
print(f"Python:      {sys.version.split()[0]}, NumPy {np.__version__}")
print(f"Scalar:      {SCALAR}")
print(f"Array sizes: {BENCH_ARRAY_SIZES}")
print(f"Runs:        {N_RUNS}")
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


rows = []

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
    })
    rows.append({
        "array_size": size, "n_runs": N_RUNS, "method": "CPU Python loop",
        "mean_us": np.mean(python_times), "median_us": np.median(python_times),
        "min_us": np.min(python_times), "max_us": np.max(python_times),
        "p1_us": np.percentile(python_times, 1), "p99_us": np.percentile(python_times, 99),
    })

# Print table
print(f"{'Size':>6} {'Method':<16} {'Mean':>8} {'Median':>8} {'Min':>8} {'P99':>8}  (us)")
print("-" * 72)
for r in rows:
    print(f"{r['array_size']:>6} {r['method']:<16} "
          f"{r['mean_us']:>8.2f} {r['median_us']:>8.2f} {r['min_us']:>8.2f} {r['p99_us']:>8.2f}")
print()

# --- Power measurement ---
# Power measured over a fixed time window (not per-run) because each individual run is shorter than the sensor update rate (~1ms).
# Running continuously for POWER_DURATION seconds keeps the CPU active long enough for the sensor to capture real active power.
POWER_IDLE_SAMPLES = 20
POWER_IDLE_INTERVAL = 0.05   # seconds between idle samples
POWER_DURATION = 2.0         # seconds of continuous activity
POWER_SAMPLE_INTERVAL = 0.05 # read sensor every ~50ms

try:
    from pynq import get_rails
    rails = get_rails()

    def read_total_power():
        return sum(r.power.value for r in rails.values() if r.power is not None)

    # Idle power
    time.sleep(1)
    idle_samples = []
    for _ in range(POWER_IDLE_SAMPLES):
        idle_samples.append(read_total_power())
        time.sleep(POWER_IDLE_INTERVAL)
    idle = np.mean(idle_samples)

    # Active power: run NumPy multiply continuously, sample periodically
    a_power = np.arange(1, BENCH_ARRAY_SIZES[-1] + 1, dtype=np.int32)
    power_samples = []
    runs_done = 0
    t_start = time.perf_counter()
    t_next_sample = t_start + POWER_SAMPLE_INTERVAL
    while time.perf_counter() - t_start < POWER_DURATION:
        _ = a_power * SCALAR
        runs_done += 1
        if time.perf_counter() >= t_next_sample:
            power_samples.append(read_total_power())
            t_next_sample += POWER_SAMPLE_INTERVAL
    active = np.mean(power_samples)

    print(f"Power (CPU NumPy, {POWER_DURATION}s window, array={len(a_power)}, {runs_done} runs):")
    print(f"  Idle:   {idle:.3f} W ({POWER_IDLE_SAMPLES} samples)")
    print(f"  Active: {active:.3f} W ({len(power_samples)} samples)")
    print(f"  Delta:  {active - idle:.3f} W")
except ImportError:
    print("Power: not available (pynq not installed, run on Ultra96-V2 board)")
except Exception as e:
    print(f"Power: measurement failed ({e})")
print()

# Save CSV
csv_path = "results/bench_cpu_results.csv"
with open(csv_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
print(f"Results saved to {csv_path}")
