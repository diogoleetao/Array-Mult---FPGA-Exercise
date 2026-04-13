"""
Test for the array_mult on Ultra96-V2
Multiplies an array by scalar on the FPGA, reads back
Uses direct DMA register access
"""

import numpy as np
import time
from pynq import Overlay, allocate

ARRAY_SIZE = 1024
SCALAR = 7

print("Loading overlay...")
ol = Overlay("/home/xilinx/array_mult/array_mult.bit")
print(f"IP blocks: {list(ol.ip_dict.keys())}")

dma = ol.axi_dma_0
ip = ol.array_mult_0

# Contiguous buffers for DMA transfers
a = allocate(shape=(ARRAY_SIZE,), dtype=np.int32)
b = allocate(shape=(ARRAY_SIZE,), dtype=np.int32)

for i in range(ARRAY_SIZE):
    a[i] = i + 1
    b[i] = 0

a.sync_to_device()
b.sync_to_device()

# Reset DMA channels
dma.mmio.write(0x00, 0b100)
dma.mmio.write(0x30, 0b100)
time.sleep(0.01)

# Write scalar via AXI-Lite
ip.write(0x10, SCALAR)

# Start the IP. bit 0 = ap_start
ip.write(0x00, 0b1)

# S2MM: set up receive first
dma.mmio.write(0x30, 0b1)
dma.mmio.write(0x48, b.physical_address & 0xFFFFFFFF)
dma.mmio.write(0x4C, (b.physical_address >> 32) & 0xFFFFFFFF)
dma.mmio.write(0x58, ARRAY_SIZE * 4)

# MM2S: send input data
dma.mmio.write(0x00, 0b1)
dma.mmio.write(0x18, a.physical_address & 0xFFFFFFFF)
dma.mmio.write(0x1C, (a.physical_address >> 32) & 0xFFFFFFFF)
dma.mmio.write(0x28, ARRAY_SIZE * 4)

# Wait for both channels to complete
timeout = 5.0
start = time.time()
while time.time() - start < timeout:
    mm2s = dma.mmio.read(0x04)
    s2mm = dma.mmio.read(0x34)
    if (mm2s & 0b10) and (s2mm & 0b10):  # both idle
        break
else:
    print(f"TIMEOUT — MM2S: 0x{mm2s:08x}, S2MM: 0x{s2mm:08x}")
    exit(1)

elapsed = (time.time() - start) * 1000
print(f"DMA completed in {elapsed:.2f} ms")

b.sync_from_device()

# Verify
errors = 0
for i in range(ARRAY_SIZE):
    expected = (i + 1) * SCALAR
    if b[i] != expected:
        print(f"ERROR at index {i}: got {b[i]}, expected {expected}")
        errors += 1
        if errors > 10:
            print("... (stopping after 10 errors)")
            break

if errors == 0:
    print(f"PASS — all {ARRAY_SIZE} elements correct (scalar={SCALAR})")
    print(f"  a[0]={a[0]} * {SCALAR} = {b[0]}")
    print(f"  a[1023]={a[1023]} * {SCALAR} = {b[1023]}")
else:
    print(f"FAIL — {errors} errors")

a.freebuffer()
b.freebuffer()
