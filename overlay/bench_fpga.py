"""FPGA vs ARM CPU benchmark for array multiply — runs on Ultra96-V2"""

import numpy as np
import time
import platform
from pynq import Overlay, allocate

ARRAY_SIZE = 1024
SCALAR = 7
WARMUP = 100
N_RUNS = 1000

print("Loading overlay...")
ol = Overlay("/home/xilinx/array_mult/array_mult.bit")
dma = ol.axi_dma_0
ip = ol.array_mult_0

print(f"Platform:    {platform.system()} {platform.machine()}")
print(f"Array:       {ARRAY_SIZE} x int32, scalar = {SCALAR}")
print(f"Interface:   AXI Stream + DMA, 99 MHz")
print(f"Runs:        {N_RUNS} (+ {WARMUP} warmup)")
print()

a = allocate(shape=(ARRAY_SIZE,), dtype=np.int32)
b = allocate(shape=(ARRAY_SIZE,), dtype=np.int32)
for i in range(ARRAY_SIZE):
    a[i] = i + 1
a.sync_to_device()

ip.write(0x10, SCALAR)

NBYTES = ARRAY_SIZE * 4
a_lo = a.physical_address & 0xFFFFFFFF
a_hi = (a.physical_address >> 32) & 0xFFFFFFFF
b_lo = b.physical_address & 0xFFFFFFFF
b_hi = (b.physical_address >> 32) & 0xFFFFFFFF


def run_fpga():
    # Reset both DMA channels control registers 
    dma.mmio.write(0x00, 0b100)
    dma.mmio.write(0x30, 0b100)

    # ap_start
    ip.write(0x00, 0b1)

    # Set up S2MM receive channel
    dma.mmio.write(0x30, 0b1)
    dma.mmio.write(0x48, b_lo)
    dma.mmio.write(0x4C, b_hi)
    dma.mmio.write(0x58, NBYTES)  # triggers S2MM

    # Set up MM2S send channel
    dma.mmio.write(0x00, 0b1)
    dma.mmio.write(0x18, a_lo)
    dma.mmio.write(0x1C, a_hi)
    dma.mmio.write(0x28, NBYTES)  # triggers MM2S

    # Wait for both channels' status registers to go idle (bit 1 = idle)
    while not (dma.mmio.read(0x04) & 0b10 and dma.mmio.read(0x34) & 0b10):
        pass


def bench(func, warmup, n_runs):
    for _ in range(warmup):
        func()
    times = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        func()
        times.append((time.perf_counter() - t0) * 1e6)
    return np.array(times)


# FPGA: reset, send, compute, and receive
fpga_times = bench(run_fpga, WARMUP, N_RUNS)

b.sync_from_device()
errors = sum(1 for i in range(ARRAY_SIZE) if b[i] != (i + 1) * SCALAR)

# CPU vectorized: operates on the whole array at once with vectorized NumPy (uses SIMD on ARM)
a_np = np.arange(1, ARRAY_SIZE + 1, dtype=np.int32)
numpy_times = bench(lambda: a_np * SCALAR, WARMUP, N_RUNS)

# CPU element-by-element: operates element-by-element with interpreter overhead (worst case)
a_list = list(range(1, ARRAY_SIZE + 1))
python_times = bench(lambda: [x * SCALAR for x in a_list], 10, 100)

# Results table
print(f"{'Method':<16} {'Mean':>8} {'Median':>8} {'Min':>8} {'Max':>8} {'P1':>8} {'P99':>8}  (us)")
print("-" * 78)
for label, t in [("FPGA (DMA)", fpga_times), ("CPU NumPy", numpy_times), ("CPU Python loop", python_times)]:
    print(f"{label:<16} {np.mean(t):>8.2f} {np.median(t):>8.2f} {np.min(t):>8.2f} {np.max(t):>8.2f} {np.percentile(t, 1):>8.2f} {np.percentile(t, 99):>8.2f}")
print()

print(f"Correctness: {'PASS' if errors == 0 else f'FAIL ({errors} errors)'}")
print()

# Power measurement
try:
    from pynq import get_rails
    rails = get_rails()

    def read_total_power():
        return sum(r.power.value for r in rails.values() if r.power is not None)

    time.sleep(1)
    idle_samples = []
    for _ in range(20):
        idle_samples.append(read_total_power())
        time.sleep(0.05)
    idle = np.mean(idle_samples)

    power_samples = []
    t_end = time.time() + 2.0
    while time.time() < t_end:
        run_fpga()
        power_samples.append(read_total_power())
    active = np.mean(power_samples)

    print(f"Power:  idle = {idle:.3f} W, active = {active:.3f} W, delta = {active - idle:.3f} W")
    print(f"Energy: {active * np.mean(fpga_times) * 1e-6 * 1e6:.2f} uJ/op")
except Exception:
    print("Power: not available on this board")
print()

print(f"FPGA vs CPU NumPy:      {np.mean(fpga_times) / np.mean(numpy_times):.1f}x {'slower' if np.mean(fpga_times) > np.mean(numpy_times) else 'faster'}")
print(f"FPGA vs CPU Python loop: {np.mean(python_times) / np.mean(fpga_times):.1f}x {'faster' if np.mean(fpga_times) < np.mean(python_times) else 'slower'}")

a.freebuffer()
b.freebuffer()
