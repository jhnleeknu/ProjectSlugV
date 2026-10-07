#ifndef MS5_PALETTE_FRAME_H
#define MS5_PALETTE_FRAME_H

#include "ms5/palette_resource.h"
#include "ms5/video_port.h"

namespace ms5 {

// Normal frame path from 68000 CPU 0x005728 through the pending gate at
// 0x00718c and normal preparation at 0x007196. RAM is a caller-owned
// 65536-byte image based at CPU 0x100000; offsets below are RAM offsets.
// A nonzero byte timer at 0x7dd4 is decremented. Its final tick copies the
// three big-endian target words at 0x7dc8..0x7dcc to 0x7dc2..0x7dc6;
// earlier ticks add the step words at 0x7dce..0x7dd2 modulo 65536.
// Changes to any current high byte dirty all 256 nodes except those with
// flag mask 2. Low-byte changes alone do not dirty nodes. When pending
// byte 0x7ded has bit 7 set, preparation is deferred and frame updates
// still commit. Otherwise prepare_palettes supplies normal preparation.
// Optional writes receive ordered watchdog and PVC bank word writes. Device
// timing and alternate entries are excluded. Optional d1 supplies/receives
// native D1 through timer arithmetic and preparation. Failure preserves
// RAM/writes/d1. Other scratch registers and CPU flags are not returned.
bool step_palette_frame(std::vector<std::uint8_t>& ram,
                        const std::vector<PaletteRecord>& records,
                        std::string& error,
                        std::vector<VideoPortWrite>* writes = NULL,
                        std::uint32_t* d1 = NULL);

} // namespace ms5

#endif
