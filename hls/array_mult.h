#ifndef ARRAY_MULT_H
#define ARRAY_MULT_H

#include <hls_stream.h>
#include <ap_axi_sdata.h>

#define ARRAY_SIZE 1024

// 32-bit AXI Stream packet
typedef ap_axis<32, 0, 0, 0> pkt_t;

void array_mult(hls::stream<pkt_t> &in_stream,
                hls::stream<pkt_t> &out_stream,
                int scalar);

#endif
