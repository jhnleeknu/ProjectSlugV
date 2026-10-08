#include "ms5/object_sprite_wrapper.h"
#include <new>
namespace ms5 {
namespace {
bool read(const std::vector<std::uint8_t>& ram, std::uint32_t base,
    unsigned int offset, unsigned int size, std::uint32_t& value,
    std::string& error) {
    const std::uint64_t address = static_cast<std::uint64_t>(base)+offset;
    if (address < 0x100000U || address+size > 0x110000U ||
        (size > 1 && (address&1U))) {
        error = "object sprite wrapper requires aligned complete object RAM reads";
        return false;
    }
    value = 0;
    for (unsigned int i = 0; i < size; ++i)
        value = (value<<8)|ram[static_cast<std::size_t>(address-0x100000U)+i];
    return true;
}
void word(std::uint32_t& value, std::uint32_t input) {
    value = (value&0xffff0000U)|(input&0xffffU);
}
void swap(std::uint32_t& value) { value = (value<<16)|(value>>16); }
bool execute(std::vector<std::uint8_t>& ram, ObjectSpriteWrapperState& state,
    SpriteSubmitStatus& status, std::string& error) {
    if (state.sprite.waiting) {
        if (state.a5 != 0x108000U) {
            error = "object sprite wrapper captured wait requires A5=108000";
            return false;
        }
    } else {
        SceneMapTransferState& s = state.sprite.registers;
        std::uint32_t value = 0;
        state.a5 = 0x108000; s.d[3] = 0;
        if (!read(ram,state.a6,0x53,1,value,error)) return false;
        s.d[2] = (s.d[2]&0xffffff00U)|value;
        swap(s.d[0]);
        if (!read(ram,state.a6,0x42,2,value,error)) return false;
        word(s.d[0],s.d[0]+value);
        unsigned int extend = s.d[2]&1U;
        s.d[2] = (s.d[2]&0xffffff00U)|((s.d[2]&0xffU)>>1);
        word(s.d[0],s.d[0]-extend);
        swap(s.d[0]);
        if (!read(ram,state.a6,0x46,2,value,error)) return false;
        word(s.d[0],s.d[0]+value);
        extend = s.d[2]&1U;
        s.d[2] = (s.d[2]&0xffffff00U)|((s.d[2]&0xffU)>>1);
        word(s.d[0],s.d[0]-extend);
        if (!read(ram,state.a6,0x12,4,value,error)) return false;
        s.d[1] = value;
        if (!read(ram,state.a6,0x1e,2,value,error)) return false;
        word(s.d[5],value);
    }
    return execute_sprite_submit(ram,state.sprite,status,error);
}
}
bool execute_object_sprite_wrapper(std::vector<std::uint8_t>& ram,
    ObjectSpriteWrapperState& state, SpriteSubmitStatus& status,
    std::string& error) {
    if (ram.size() != 65536) {
        error = "object sprite wrapper requires exactly64KiB RAM"; return false;
    }
    try {
        std::vector<std::uint8_t> candidate = ram;
        ObjectSpriteWrapperState next = state;
        SpriteSubmitStatus result = status;
        if (!execute(candidate,next,result,error)) return false;
        ram.swap(candidate); state = next; status = result; error.clear(); return true;
    } catch (const std::bad_alloc&) {
        error = "cannot allocate object sprite wrapper transaction"; return false;
    }
}
}
