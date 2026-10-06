#include "ms5/object_state.h"

namespace {

void clear_bytes(std::uint8_t* object, std::size_t begin, std::size_t end) {
    for (std::size_t offset = begin; offset < end; ++offset) {
        object[offset] = 0;
    }
}

void write_be_word(std::uint8_t* object, std::size_t offset, std::uint16_t value) {
    object[offset] = static_cast<std::uint8_t>(value >> 8);
    object[offset + 1] = static_cast<std::uint8_t>(value & 0xffU);
}

} // namespace

namespace ms5 {

bool reset_object_fields(std::uint8_t* object, std::size_t size) {
    if (object == NULL || size < 0xc4) {
        return false;
    }
    object[0x1d] = 0;
    clear_bytes(object, 0x2e, 0x54);
    clear_bytes(object, 0x64, 0x68);
    write_be_word(object, 0x6e, 0x0040);
    clear_bytes(object, 0x54, 0x5a);
    object[0x5e] = 0;
    write_be_word(object, 0x5a, 0xffff);
    object[0x60] = 0;
    object[0x17] = 0xff;
    object[0x6d] = 0xff;
    clear_bytes(object, 0x72, 0x76);
    object[0x6a] = 0;
    object[0x6b] = 0xff;
    object[0x6c] = 0xff;
    object[0x15] = 0;
    object[0x61] = 0;
    object[0x62] = 0;
    object[0x63] = 0;
    object[0x12] = 0xff;
    object[0x13] = 0xff;
    write_be_word(object, 0x1e, 0xffff);
    clear_bytes(object, 0x76, 0xc4);
    return true;
}

} // namespace ms5
