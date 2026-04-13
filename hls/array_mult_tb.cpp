#include <iostream>
#include "array_mult.h"

int main() {
    hls::stream<pkt_t> in_stream;
    hls::stream<pkt_t> out_stream;
    int scalar = 7;
    int errors = 0;

    // Write input values into the stream
    for (int i = 0; i < ARRAY_SIZE; i++) {
        pkt_t pkt;
        pkt.data = i + 1;
        pkt.keep = -1;     // all bytes valid
        pkt.strb = -1;
        pkt.last = (i == ARRAY_SIZE - 1) ? 1 : 0;
        in_stream.write(pkt);
    }

    array_mult(in_stream, out_stream, scalar);

    // Read and verify output
    for (int i = 0; i < ARRAY_SIZE; i++) {
        pkt_t pkt = out_stream.read();
        int expected = (i + 1) * scalar;
        if (pkt.data != expected) {
            std::cout << "ERROR at index " << i
                      << ": got " << pkt.data
                      << ", expected " << expected << std::endl;
            errors++;
        }
    }

    if (errors == 0) {
        std::cout << "PASSED — all " << ARRAY_SIZE
                  << " elements correct (scalar=" << scalar << ")" << std::endl;
    } else {
        std::cout << "FAILED — " << errors << " errors" << std::endl;
    }

    return errors;
}
