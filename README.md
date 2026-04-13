# Array Multiply on Ultra96-V2

HLS accelerator that multiplies a 1024-element integer array by a scalar, running on the Avnet Ultra96-V2 (Zynq UltraScale+ ZU3EG). Uses AXI Stream interfaces with a DMA block for data transfer between PS and PL.

Done as part of my Master's thesis at IST on onboard cloud detection for satellites.

## Repository structure

- `hls/array_mult.cpp` — HLS kernel (AXI Stream (in/out), AXI-Lite (scalar and return))
- `hls/array_mult.h` — Header with stream type and array size definition
- `hls/array_mult_tb.cpp` — C simulation testbench
- `vivado/create_bd.tcl` — TCL script to recreate the Vivado block design
- `overlay/array_mult.bit` — FPGA bitstream
- `overlay/array_mult.hwh` — Hardware handoff
- `overlay/test_array_mult.py` — Functional test (runs on board)
- `overlay/bench_fpga.py` — FPGA vs ARM CPU benchmark (runs on board)
- `overlay/bench_cpu.py` — CPU-only benchmark

## Notes

- [AXI DMA Register Map (PG021)](https://docs.amd.com/r/en-US/pg021_axi_dma/Direct-Register-Mode-Register-Address-Map) - used to check the addresses of the DMA
