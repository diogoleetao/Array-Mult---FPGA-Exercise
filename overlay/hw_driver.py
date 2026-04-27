"""
Hardware driver for array_mult on Ultra96-V2

"""

import time
import numpy as np
from pynq import Overlay, allocate

from hw_config import (
    BITSTREAM_PATH, IP_NAME, DMA_NAME, MAX_ARRAY_SIZE,
    SCALAR_REG,
    MM2S_DMACR, MM2S_DMASR, MM2S_SA, MM2S_SA_MSB, MM2S_LENGTH,
    S2MM_DMACR, S2MM_DMASR, S2MM_DA, S2MM_DA_MSB, S2MM_LENGTH,
    DMA_RESET, DMA_RUN, DMA_IDLE,
)


class ArrayMultDriver:
    """Manages the array_mult FPGA overlay, DMA, and IP."""

    def __init__(self, bitstream=BITSTREAM_PATH, timing=False,
                 array_size=MAX_ARRAY_SIZE):
        self.ol = None
        self.dma = None
        self.ip = None
        self.a = None           # input buffer
        self.b = None           # output buffer
        self._a_lo = 0
        self._a_hi = 0
        self._b_lo = 0
        self._b_hi = 0
        self._array_size = array_size
        self._nbytes = array_size * 4
        self._timing = timing
        self._was_cached = False

        self.load_time_s = None
        self.alloc_time_s = None

        self._load_overlay(bitstream)
        self._alloc_buffers()

    # ---- setup ----

    def _load_overlay(self, bitstream):
        """Load bitstream, skipping PL programming if already loaded."""
        if self._timing:
            t0 = time.perf_counter()

        self.ol = Overlay(bitstream, download=False)
        if not self.ol.is_loaded():
            self.ol.download()
            self._was_cached = False
        else:
            self._was_cached = True

        if self._timing:
            self.load_time_s = time.perf_counter() - t0

        self.dma = getattr(self.ol, DMA_NAME)
        self.ip = getattr(self.ol, IP_NAME)

        print(f"Overlay: {bitstream}")
        print(f"  IPs:  {list(self.ol.ip_dict.keys())}")
        print(f"  DMA:  {DMA_NAME}")
        print(f"  IP:   {IP_NAME}")

    def _alloc_buffers(self):
        """Allocate contiguous DMA buffers and cache physical addresses."""
        if self._timing:
            t0 = time.perf_counter()
        self.a = allocate(shape=(self._array_size,), dtype=np.int32)
        self.b = allocate(shape=(self._array_size,), dtype=np.int32)
        if self._timing:
            self.alloc_time_s = time.perf_counter() - t0

        self._a_lo = self.a.physical_address & 0xFFFFFFFF
        self._a_hi = (self.a.physical_address >> 32) & 0xFFFFFFFF
        self._b_lo = self.b.physical_address & 0xFFFFFFFF
        self._b_hi = (self.b.physical_address >> 32) & 0xFFFFFFFF

    # ---- core operations ----

    def set_scalar(self, scalar):
        """Write the scalar value to the HLS IP via AXI-Lite."""
        self.ip.write(SCALAR_REG, scalar)

    def set_array_size(self, size):
        """Change the active array size (must be <= allocated buffer size)."""
        if size > self._array_size:
            raise ValueError(f"size {size} exceeds buffer size {self._array_size}")
        self._nbytes = size * 4

    def setup(self):
        """Reset DMA and configure channel addresses (one-time per size)."""
        mmio = self.dma.mmio

        # Reset both DMA channels
        mmio.write(MM2S_DMACR, DMA_RESET)
        mmio.write(S2MM_DMACR, DMA_RESET)
        while mmio.read(MM2S_DMACR) & DMA_RESET:
            pass
        while mmio.read(S2MM_DMACR) & DMA_RESET:
            pass

        # S2MM: set run mode, configure destination address
        mmio.write(S2MM_DMACR, DMA_RUN)
        mmio.write(S2MM_DA, self._b_lo)
        mmio.write(S2MM_DA_MSB, self._b_hi)

        # MM2S: set run mode, configure source address
        mmio.write(MM2S_DMACR, DMA_RUN)
        mmio.write(MM2S_SA, self._a_lo)
        mmio.write(MM2S_SA_MSB, self._a_hi)

    def run(self):
        """Execute one DMA transfer+compute cycle (call setup() first)."""
        mmio = self.dma.mmio

        # S2MM, writing LENGTH tells it how many bytes to expect
        mmio.write(S2MM_LENGTH, self._nbytes)

        # Trigger MM2S, writing LENGTH starts the send to the HLS kernel
        mmio.write(MM2S_LENGTH, self._nbytes)

        # Wait until receive channel is idle
        while not (mmio.read(S2MM_DMASR) & DMA_IDLE):
            pass

    def run_full(self):
        """Execute one complete DMA round-trip including setup (for single runs)."""
        self.setup()
        self.run()

    def run_timed(self):
        """Execute one DMA round-trip and return elapsed time in microseconds."""
        t0 = time.perf_counter()
        self.run()
        return (time.perf_counter() - t0) * 1e6

    # ---- helpers ----

    def print_setup_times(self):
        """Print overlay load and buffer allocation times (requires timing=True)."""
        if self.load_time_s is None:
            print("Setup times not available (timing=False)")
            return
        cached = " (cached)" if self._was_cached else " (programmed)"
        print(f"Overlay load:      {self.load_time_s * 1000:.1f} ms{cached}")
        print(f"Buffer allocation: {self.alloc_time_s * 1000:.1f} ms")

    def free(self):
        """Release DMA buffers."""
        if self.a is not None:
            self.a.freebuffer()
        if self.b is not None:
            self.b.freebuffer()
