"""
Hardware configuration for array_mult on Ultra96-V2

All register addresses, DMA offsets, and design parameters
Derived from HLS synthesis (xarray_mult_hw.h) and AXI DMA register map

Change BITSTREAM_PATH if deploying to a different directory on the board
"""

# --- Design parameters ---
ARRAY_SIZE = 1024       # v1 fixed size (must match HLS: array_mult.h)
MAX_ARRAY_SIZE = 16384  # v2 max size (must match HLS: array_mult_v2.h)
SCALAR = 7

# --- Bitstream paths ---
BITSTREAM_V1 = "/home/xilinx/array_mult/array_mult.bit"      # fixed 1024
BITSTREAM_V2 = "/home/xilinx/array_mult/array_mult_v2.bit"    # variable size (TLAST)
BITSTREAM_PATH = BITSTREAM_V2  # default

# --- IP names in the block design ---
IP_NAME_V1 = "array_mult_0"
IP_NAME_V2 = "array_mult_v2_0"
IP_NAME = IP_NAME_V2  # default
DMA_NAME = "axi_dma_0"

# --- HLS IP: AXI-Lite register map (from xarray_mult_v2_hw.h) ---
# ap_ctrl_none: no control register (kernel is free-running)
# 0x00 : reserved
SCALAR_REG = 0x10       # scalar argument

# --- AXI DMA register map (Xilinx PG021) ---
# MM2S (Memory-Map to Stream — send channel)
MM2S_DMACR = 0x00       # control: bit 0 run/stop; bit 2 reset
MM2S_DMASR = 0x04       # status:  bit 0 halted (0=run, 1=halted), bit 1 idle (1=idle)
MM2S_SA = 0x18           # source address low 32 bits
MM2S_SA_MSB = 0x1C       # source address high 32 bits
MM2S_LENGTH = 0x28       # transfer length in bytes (writing a value triggers transfer)

# S2MM (Stream to Memory-Map — receive channel)
S2MM_DMACR = 0x30       # control: bit 0 run/stop; bit 2 reset
S2MM_DMASR = 0x34       # status:  bit 0 halted (0=run, 1=halted), bit 1 idle (1=idle)
S2MM_DA = 0x48           # destination address low 32 bits
S2MM_DA_MSB = 0x4C       # destination address high 32 bits
S2MM_LENGTH = 0x58       # transfer length in bytes (writing a value triggers transfer)

# DMA control bits
DMA_RESET = 0b100       
DMA_RUN = 0b1            
DMA_IDLE = 0b10          

# --- Benchmark defaults ---
WARMUP = 100
BENCH_ARRAY_SIZES = [256, 1024, 4096, 16384]
