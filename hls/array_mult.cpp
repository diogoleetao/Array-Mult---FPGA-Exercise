#include "array_mult.h"

void array_mult(hls::stream<pkt_t> &in_stream,
                hls::stream<pkt_t> &out_stream,
                int scalar) {

    #pragma HLS INTERFACE axis port=in_stream
    #pragma HLS INTERFACE axis port=out_stream
    #pragma HLS INTERFACE s_axilite port=scalar
    #pragma HLS INTERFACE s_axilite port=return

    for (int i = 0; i < ARRAY_SIZE; i++) {
        #pragma HLS PIPELINE II=1

        pkt_t pkt = in_stream.read();
        pkt.data = pkt.data * scalar;
        out_stream.write(pkt);
    }
}
