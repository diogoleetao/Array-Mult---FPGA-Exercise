# Array Multiply on Ultra96-V2

HLS accelerator that multiplies an integer array by a scalar, running on the Avnet Ultra96-V2 (Zynq UltraScale+ ZU3EG). Uses AXI Stream interfaces with a DMA block for data transfer between PS and PL. Two versions are included.

Done as part of my Master's thesis at IST.

## v1 vs v2

Both versions use the same architecture: AXI Stream for data (through AXI DMA) and AXI-Lite for the scalar register. Both versions use the same block design structure: Zynq PS, AXI DMA, HLS IP, SmartConnect. The only difference between versions is the control interface and how the kernel handles array size:

| | v1 (`array_mult`) | v2 (`array_mult_v2`) |
|---|---|---|
| **Control** | `ap_ctrl_hs` — requires `ap_start` from software | `ap_ctrl_none` — free-running, processes data as it arrives |
| **Array size** | Fixed at 1024 (hardcoded in HLS loop bound) | Variable, up to 16384 (set at runtime) |
| **HLS loop** | `for (i = 0; i < ARRAY_SIZE; i++)` — always 1024 iterations | `for (i = 0; i < MAX_ARRAY_SIZE; i++)` with `if (pkt.last) break;` |
| **Size control** | Changing the size requires resynthesizing the HLS IP and regenerating the bitstream | The DMA transfer length determines the array size, the kernel stops when it sees the TLAST signal from the DMA on the AXI Stream |


## Repository structure

```
array_mult_repo/
├── hls/
│   ├── array_mult.cpp          ← v2 HLS kernel
│   ├── array_mult.h            ← header: define packet type and MAX_ARRAY_SIZE
│   ├── array_mult_tb.cpp       ← C simulation testbench
│   └── v1_fixed_size/          ← v1 HLS kernel: fixed 1024 iterations
├── overlay/
│   ├── hw_config.py            ← register addresses, DMA offsets, design constants
│   ├── hw_driver.py            ← ArrayMultDriver class (setup/run timing separation)
│   ├── test_array_mult.py      ← functional test
│   ├── bench_fpga.py           ← FPGA + ARM CPU benchmark (runs on board)
│   ├── bench_cpu.py            ← CPU-only benchmark (runs on any machine)
│   ├── plot_results.py         ← generates plots from CSV results
│   ├── array_mult.bit/.hwh    ← v1 bitstream + hardware handoff
│   ├── array_mult_v2.bit/.hwh ← v2 bitstream + hardware handoff
│   ├── results/                ← CSV benchmark outputs
│   │   ├── bench_fpga_results.csv
│   │   ├── bench_cpu_results.csv
│   │   └── bench_power_results.csv
│   └── plots/                  ← PNG plot outputs
│       ├── plot_board_latency.png
│       ├── plot_laptop_latency.png
│       ├── plot_all_platforms.png
│       └── plot_power.png
├── vivado/
│   └── create_bd.tcl           ← TCL script to recreate Vivado block design
└── README.md
```

## Switching between v1 and v2

All Python scripts import their configuration from `hw_config.py`. This file defines both versions:

```python
BITSTREAM_V1 = "/home/xilinx/array_mult/array_mult.bit"
BITSTREAM_V2 = "/home/xilinx/array_mult/array_mult_v2.bit"
BITSTREAM_PATH = BITSTREAM_V2   # ← change this to BITSTREAM_V1 for v1

IP_NAME_V1 = "array_mult_0"
IP_NAME_V2 = "array_mult_v2_0"
IP_NAME = IP_NAME_V2            # ← change this to IP_NAME_V1 for v1
```

To run v1 instead of v2, change `BITSTREAM_PATH` and `IP_NAME` to point to the v1 values. Adjust the file paths if storing the bitstreams in a different directory.

## Benchmark results

Latency measured with `time.perf_counter()`, 10000 runs per method per size, 100 warmup runs. Three methods are compared:

- **FPGA DMA**: data is sent from DDR to the PL kernel via AXI DMA and results are written back to DDR
- **NumPy**: uses SIMD vector instructions to multiply the entire array in one call
- **Python loop**: iterates over each element in Python, adding a per-element overhead

### Board (Ultra96-V2, Cortex-A53, PL 99 MHz)

| Size | FPGA DMA (median) | ARM NumPy (median) | ARM Python loop (median) |
|---|---|---|---|
| 256 | 24.9 us | 13.9 us | 129.4 us |
| 1024 | 33.0 us | 17.8 us | 493.1 us |
| 4096 | 47.7 us | 24.7 us | 1922.7 us |
| 16384 | 113.4 us | 49.1 us | 8687.2 us |

### Laptop (Intel i7)

| Size | NumPy (median) | Python loop (median) |
|---|---|---|
| 256 | 2.7 us | 21.6 us |
| 1024 | 4.4 us | 81.8 us |
| 4096 | 10.7 us | 303.3 us |
| 16384 | 24.9 us | 1186.2 us |

ARM NumPy is faster than the FPGA at all sizes because this workload is memory-bound (one multiply per element is trivial computation). NumPy performs the multiply directly in CPU cache using SIMD instructions with no data movement overhead, while the FPGA path must transfer every element from DDR through the AXI Stream to the PL and back. Both scale at similar rates with array size, but the FPGA has a fixed DMA round-trip overhead (~25 us baseline even for a single element).

## Power measurement

Power is measured using the INA226 sensors on the Ultra96-V2 board, accessed via `pynq.get_rails()`.

I use a **time-based** rather than a per-run benchmark: the hardware runs the operation continuously in a tight loop for a fixed duration (2 seconds), while power is sampled every 50ms. This is necessary because each individual execution completes in short time intervals (between 10 us and 100 us), which is faster than the INA226 sensor update rate (~1 ms). Sampling power after a single run would always read idle power so, by keeping the hardware continuously active for 2 seconds, the sensor captures real active power.

The same method is used for both FPGA and CPU measurements, making the results directly comparable.

**Why the power delta is small**: Our measured idle power is 1.366W. During active workloads (array size 16384):

| Method | Active power | Delta from idle |
|---|---|---|
| FPGA (DMA) | 1.359 W | -0.007 W |
| CPU NumPy | 1.375 W | +0.009 W |
| CPU Python loop | 1.395 W | +0.029 W |

The three methods barely change the power usage of the board. This is because the board's 1.37 W idle power is dominated by always-on PS tasks (ARM cores running Linux, DDR controller, I/O transceivers). The Vivado power report confirms this: the PS accounts for 1.496 W (80% of estimated total), while the PL accelerator uses only 0.028 W for CLB logic and 0.027 W for signals.

For a simple operation like scalar multiplication, the kernel does one multiply per element per clock cycle so the PL barely switches compared to idle. The workload is memory-bound (moving data PS DDR → PL → PS DDR), not compute-bound, so there is very little power draw from the accelerator.

The FPGA power advantage becomes observable for compute-heavy workloads (for example in neural network inference), where the PL performs many operations per byte transferred in parallel, without the instruction overhead of a CPU.

## Notes

- The HLS kernel uses `ap_ctrl_none` (free-running): no ap_start/ap_done handshake. The kernel is always ready to process stream data.
- DMA register addresses in `hw_config.py` are derived from the [AXI DMA register map (PG021)](https://docs.amd.com/r/en-US/pg021_axi_dma/Direct-Register-Mode-Register-Address-Map)
- All benchmark timing uses `time.perf_counter()` (highest resolution and monotonic)
- Tools: Vitis HLS 2025.1 (synthesis), Vivado 2025.1 (block design + bitstream), PYNQ (board runtime)
