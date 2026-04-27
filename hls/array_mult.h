#ifndef ARRAY_MULT_V2_H
#define ARRAY_MULT_V2_H

#include <hls_stream.h>
#include <ap_axi_sdata.h>

// Maximum array size
// The kernel stops when it sees TLAST, so any size up to this works
#define MAX_ARRAY_SIZE 16384

// 32-bit AXI Stream packet
typedef ap_axis<32, 0, 0, 0> pkt_t;

void array_mult_v2(hls::stream<pkt_t> &in_stream,
                   hls::stream<pkt_t> &out_stream,
                   int scalar);

#endif
