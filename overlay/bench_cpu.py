"""CPU-only benchmark for array multiply"""

import numpy as np
import time
import platform
import sys

SCALAR = 7
WARMUP = 100
N_RUNS = 1000

print(f"Platform:    {platform.system()} {platform.machine()}")
print(f"Processor:   {platform.processor()}")
print(f"Python:      {sys.version.split()[0]}, NumPy {np.__version__}")
print(f"Scalar:      {SCALAR}")
print(f"Runs:        {N_RUNS} (+ {WARMUP} warmup)")
print()

SIZE = 1024

# CPU Vectorized
a_np = np.arange(1, SIZE + 1, dtype=np.int32)
for _ in range(WARMUP):
    b_np = a_np * SCALAR
numpy_times = []
for _ in range(N_RUNS):
    t0 = time.perf_counter()
    b_np = a_np * SCALAR
    numpy_times.append((time.perf_counter() - t0) * 1e6)
numpy_times = np.array(numpy_times)

# CPU Element-by-element
a_list = list(range(1, SIZE + 1))
for _ in range(WARMUP):
    b_list = [x * SCALAR for x in a_list]
python_times = []
for _ in range(N_RUNS):
    t0 = time.perf_counter()
    b_list = [x * SCALAR for x in a_list]
    python_times.append((time.perf_counter() - t0) * 1e6)
python_times = np.array(python_times)

print(f"Array size: {SIZE} x int32")
print()
print(f"{'Method':<16} {'Mean':>8} {'Median':>8} {'Min':>8} {'Max':>8} {'P1':>8} {'P99':>8}  (us)")
print("-" * 78)
for label, t in [("CPU NumPy", numpy_times), ("CPU Python loop", python_times)]:
    print(f"{label:<16} {np.mean(t):>8.2f} {np.median(t):>8.2f} {np.min(t):>8.2f} {np.max(t):>8.2f} {np.percentile(t, 1):>8.2f} {np.percentile(t, 99):>8.2f}")
print()
print("Note: CPU power not measurable from software.")
