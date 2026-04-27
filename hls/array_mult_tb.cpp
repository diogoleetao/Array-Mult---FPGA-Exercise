#include <iostream>
#include "array_mult_v2.h"

int test_size(int size, int scalar) {
    hls::stream<pkt_t> in_stream;
    hls::stream<pkt_t> out_stream;
    int errors = 0;

    // Write input values into the stream
    for (int i = 0; i < size; i++) {
        pkt_t pkt;
        pkt.data = i + 1;
        pkt.keep = -1;     // all bytes valid
        pkt.strb = -1;
        pkt.last = (i == size - 1) ? 1 : 0;
        in_stream.write(pkt);
    }

    array_mult_v2(in_stream, out_stream, scalar);

    // Read and verify output
    for (int i = 0; i < size; i++) {
        pkt_t pkt = out_stream.read();
        int expected = (i + 1) * scalar;
        if (pkt.data != expected) {
            std::cout << "  ERROR at index " << i
                      << ": got " << pkt.data
                      << ", expected " << expected << std::endl;
            errors++;
        }
    }

    return errors;
}

int main() {
    int scalar = 7;
    int total_errors = 0;

    // Test multiple array sizes
    int sizes[] = {1, 10, 256, 1024, 4096, 16384};
    int n_sizes = sizeof(sizes) / sizeof(sizes[0]);

    for (int t = 0; t < n_sizes; t++) {
        int size = sizes[t];
        int errors = test_size(size, scalar);

        if (errors == 0) {
            std::cout << "PASSED — size=" << size
                      << ", scalar=" << scalar << std::endl;
        } else {
            std::cout << "FAILED — size=" << size
                      << ", " << errors << " errors" << std::endl;
        }
        total_errors += errors;
    }

    std::cout << std::endl;
    if (total_errors == 0) {
        std::cout << "ALL TESTS PASSED" << std::endl;
    } else {
        std::cout << "TOTAL FAILURES: " << total_errors << std::endl;
    }

    return total_errors;
}
