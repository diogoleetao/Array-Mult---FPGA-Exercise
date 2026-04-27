"""
Functional test for the array_mult v2 IP on Ultra96-V2
Tests multiple array sizes (TLAST-based variable length)
"""

import numpy as np
from hw_config import MAX_ARRAY_SIZE, SCALAR
from hw_driver import ArrayMultDriver

TEST_SIZES = [1, 10, 256, 1024, 4096, 16384]

# --- Setup hardware ---
print("Loading overlay...")
hw = ArrayMultDriver()
print()

# Fill input buffer once (max size)
for i in range(MAX_ARRAY_SIZE):
    hw.a[i] = i + 1
hw.a.sync_to_device()

hw.set_scalar(SCALAR)

# --- Test each size ---
total_errors = 0

for size in TEST_SIZES:
    hw.set_array_size(size)

    # Clear output
    for i in range(size):
        hw.b[i] = 0
    hw.b.sync_to_device()

    hw.setup()
    hw.run()
    hw.b.sync_from_device()

    errors = 0
    for i in range(size):
        expected = (i + 1) * SCALAR
        if hw.b[i] != expected:
            print(f"  ERROR at index {i}: got {hw.b[i]}, expected {expected}")
            errors += 1
            if errors > 5:
                print("  ... (stopping after 5 errors)")
                break

    if errors == 0:
        print(f"PASS — size={size}, scalar={SCALAR}  "
              f"(a[0]={hw.a[0]}*{SCALAR}={hw.b[0]}, "
              f"a[{size-1}]={hw.a[size-1]}*{SCALAR}={hw.b[size-1]})")
    else:
        print(f"FAIL — size={size}, {errors} errors")
    total_errors += errors

print()
if total_errors == 0:
    print(f"ALL TESTS PASSED ({len(TEST_SIZES)} sizes)")
else:
    print(f"TOTAL FAILURES: {total_errors}")

hw.free()
