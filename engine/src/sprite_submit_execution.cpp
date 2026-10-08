#include "ms5/sprite_submit_execution.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t low(std::uint32_t value) { return static_cast<std::uint16_t>(value); }
void word(std::uint32_t& value,std::uint32_t input) { value = (value&0xffff0000U)|low(input); }
void swap(std::uint32_t& value) { value = (value<<16)|(value>>16); }
std::uint32_t indexed(std::uint32_t base,std::uint32_t index) {
    const std::uint32_t value = low(index);
    return base+(value < 0x8000U ? value : value-0x10000U);
}
bool span(std::uint32_t address,unsigned int size,std::string& error) {
    if ((address&1U) || address < 0x100000U || address > 0x110000U-size) {
        error = "sprite submission requires aligned complete CPU RAM span"; return false;
    }
    return true;
}
bool read(const std::vector<std::uint8_t>& ram,std::uint32_t address,unsigned int size,std::uint32_t& value,std::string& error) {
    if (!span(address,size,error)) return false;
    value = 0;
    for (unsigned int i = 0; i < size; ++i) value = (value<<8)|ram[address-0x100000U+i];
    return true;
}
bool write(std::vector<std::uint8_t>& ram,std::uint32_t address,unsigned int size,std::uint32_t value,std::string& error) {
    if (!span(address,size,error)) return false;
    for (unsigned int i = 0; i < size; ++i) ram[address-0x100000U+i] = static_cast<std::uint8_t>(value >> (8*(size-i-1)));
    return true;
}
bool execute(std::vector<std::uint8_t>& ram,SpriteSubmitExecutionState& state,SpriteSubmitStatus& status,std::string& error) {
    SceneMapTransferState& s = state.registers; std::uint32_t value = 0;
    if (!state.waiting) {
        if (!read(ram,0x109152,4,value,error)) return false; s.a[0] = value;
        if (s.a[0] != 0xcd50) { error = "sprite submission supports only default RTS callback cd50"; return false; }
        word(s.d[0],s.d[0]-0x40U);
        if (low(s.d[0]) >= 0x280U) { status = SpriteClipped; return true; }
        word(s.d[0],s.d[0]+0x40U); swap(s.d[0]); word(s.d[0],s.d[0]+0x160U);
        if (low(s.d[0]) >= 0x400U) { status = SpriteClipped; return true; }
        word(s.d[0],s.d[0]-0x160U); swap(s.d[0]);
        s.a[1] = 0x108b34;
        if (!read(ram,0x108d3a,2,value,error)) return false; word(s.d[6],value);
        word(s.d[6],s.d[6]+2U); word(s.d[6],s.d[6]&0x1feU);
        if (!read(ram,0x108d34,2,value,error)) return false;
        if (low(s.d[6]) == value) {
            if (!read(ram,0x108d36,2,value,error)) return false; word(s.d[4],value);
            if (!read(ram,0x108d34,2,value,error)) return false;
            if (low(s.d[4]) == value) { status = SpriteFull; return true; }
            state.waiting = true;
        }
    }
    if (state.waiting) {
        if (!read(ram,0x108d34,2,value,error)) return false;
        if (low(state.registers.d[4]) != value) { status = SpriteWaiting; return true; }
    }
    if (!write(ram,0x108d3a,2,s.d[6],error)) return false;
    const bool deferred = (s.d[1]&64U) != 0; s.d[1] &= ~64U;
    if (!deferred) {
        if (!read(ram,0x108d38,2,value,error)) return false; word(s.d[4],value);
        if (!read(ram,indexed(s.a[1],s.d[6]),2,value,error)) return false; word(s.d[3],value);
        if (!write(ram,indexed(s.a[1],s.d[4]),2,s.d[3],error)) return false;
        word(s.d[4],s.d[4]+2U); word(s.d[4],s.d[4]&0x1feU);
        if (!write(ram,0x108d38,2,s.d[4],error)) return false;
    } else {
        s.a[0] = 0x108f4e;
        if (!read(ram,0x10914e,2,value,error)) return false; word(s.d[4],value);
        if (!write(ram,0x10914e,2,value+2U,error)) return false;
        if (!read(ram,indexed(s.a[1],s.d[6]),2,value,error)) return false; word(s.d[3],value);
        if (!write(ram,indexed(s.a[0],s.d[4]),2,s.d[3],error)) return false;
    }
    s.a[0] = indexed(0x107f34,s.d[3]);
    swap(s.d[7]); word(s.d[0],s.d[0]<<7); word(s.d[7],s.d[7]|s.d[0]); swap(s.d[7]);
    s.d[1] = (s.d[1]&0xffffff00U)|(s.d[1]&7U);
    word(s.d[0],s.d[5]); swap(s.d[0]); word(s.d[0],s.d[0]<<6);
    if (!write(ram,s.a[0],4,s.d[0],error) || !write(ram,s.a[0]+4,4,s.d[1],error) || !write(ram,s.a[0]+8,4,s.d[7],error)) return false;
    state.waiting = false; status = SpriteAccepted; return true;
}
}
bool execute_sprite_submit(std::vector<std::uint8_t>& ram,SpriteSubmitExecutionState& state,
    SpriteSubmitStatus& status,std::string& error) {
    if (ram.size() != 65536) { error = "sprite submission requires exactly64KiB RAM"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram; SpriteSubmitExecutionState next = state; SpriteSubmitStatus result = status;
        if (!execute(candidate,next,result,error)) return false;
        ram.swap(candidate); state = next; status = result; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate sprite submission transaction"; return false; }
}
}
