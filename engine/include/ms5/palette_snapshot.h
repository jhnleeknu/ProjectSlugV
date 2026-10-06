#ifndef MS5_PALETTE_SNAPSHOT_H
#define MS5_PALETTE_SNAPSHOT_H

#include <cstdint>
#include <string>
#include <vector>

namespace ms5 {

// Save at 68000 CPU address 0x008bc8 and restore at 0x008be0. RAM is a
// caller-owned 65536-byte image based at CPU 0x100000. Save copies the 20
// bytes at RAM offsets 0x7dc2..0x7dd5 into 0x7dd6..0x7de9. Restore copies
// them back. When the restored timer byte at 0x7dd4 is zero, restore sets
// it to one and preserves the pre-restore bytes at 0x7dc2, 0x7dc4 and
// 0x7dc6. All other bytes are preserved. Failure preserves every RAM byte
// and sets error; success clears it.
bool save_palette_effect(std::vector<std::uint8_t>& ram, std::string& error);
bool restore_palette_effect(std::vector<std::uint8_t>& ram, std::string& error);

} // namespace ms5

#endif
