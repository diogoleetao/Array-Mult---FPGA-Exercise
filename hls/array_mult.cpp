#include "array_mult_v2.h"

void array_mult_v2(hls::stream<pkt_t> &in_stream,
                   hls::stream<pkt_t> &out_stream,
                   int scalar) {

    #pragma HLS INTERFACE axis port=in_stream
    #pragma HLS INTERFACE axis port=out_stream
    #pragma HLS INTERFACE s_axilite port=scalar
    #pragma HLS INTERFACE ap_ctrl_none port=return

    // Process until TLAST signal (variable array size)
    // The array size is determined at runtime by the transfer length
    for (int i = 0; i < MAX_ARRAY_SIZE; i++) {
        #pragma HLS PIPELINE II=1

        pkt_t pkt = in_stream.read();
        pkt.data = pkt.data * scalar;
        out_stream.write(pkt);

        if (pkt.last)
            break;
    }
}
