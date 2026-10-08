#include "ms5/sprite_submit_execution.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& ram,unsigned int at,std::uint32_t value,unsigned int size = 2) {
    for (unsigned int i = 0; i < size; ++i) ram[at+i] = static_cast<std::uint8_t>(value >> (8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& ram,unsigned int at,unsigned int size = 4) {
    std::uint32_t value = 0; for (unsigned int i = 0; i < size; ++i) value = (value<<8)|ram[at+i]; return value;
}
ms5::SpriteSubmitExecutionState initial() {
    ms5::SpriteSubmitExecutionState s;
    for (unsigned int i = 0; i < 8; ++i) s.registers.d[i] = 0xabcd1200U+i;
    for (unsigned int i = 0; i < 5; ++i) s.registers.a[i] = 0x76540000U+i;
    s.registers.d[0] = 0x00030040; s.registers.d[1] = 0xabcd12bf; s.registers.d[7] = 0x00110022; return s;
}
bool same(const ms5::SpriteSubmitExecutionState& a,const ms5::SpriteSubmitExecutionState& b) {
    for (unsigned int i = 0; i < 8; ++i) if (a.registers.d[i] != b.registers.d[i]) return false;
    for (unsigned int i = 0; i < 5; ++i) if (a.registers.a[i] != b.registers.a[i]) return false;
    return a.waiting == b.waiting;
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0); put(ram,0x9152,0xcd50,4);
    ms5::SpriteSubmitExecutionState s = initial(); ms5::SpriteSubmitStatus status = ms5::SpriteAccepted; std::string error;
    // First clip returns the subtracted low WORD and only changes A0.
    s.registers.d[0] = 0xbeef003f; const std::vector<std::uint8_t> base = ram;
    assert(ms5::execute_sprite_submit(ram,s,status,error)); assert(status == ms5::SpriteClipped && !s.waiting && s.registers.d[0] == 0xbeefffffU && s.registers.a[0] == 0xcd50 && ram == base);
    // Second clip returns swapped D0 with the X bias still applied.
    s = initial(); s.registers.d[0] = 0x02a00040;
    assert(ms5::execute_sprite_submit(ram,s,status,error)); assert(status == ms5::SpriteClipped && s.registers.d[0] == 0x00400400);
    // Normal accepted register widths and MOVEM layout.
    s = initial(); put(ram,0x8b36,12);
    assert(ms5::execute_sprite_submit(ram,s,status,error));
    assert(status == ms5::SpriteAccepted && !s.waiting && s.registers.a[0] == 0x107f40 && s.registers.a[1] == 0x108b34);
    assert(s.registers.d[0] == 0x120500c0 && s.registers.d[1] == 0xabcd1207U && s.registers.d[3] == 0xabcd000cU);
    assert(s.registers.d[4] == 0xabcd0002U && s.registers.d[6] == 0xabcd0002U && s.registers.d[7] == 0x20110022);
    assert(get(ram,0x7f40) == s.registers.d[0] && get(ram,0x7f44) == s.registers.d[1] && get(ram,0x7f48) == s.registers.d[7]);
    assert(s.registers.d[2] == initial().registers.d[2] && s.registers.d[5] == initial().registers.d[5] && s.registers.a[4] == initial().registers.a[4]);
    // Full observes equal consumer/prepared after D6 calculation; no writes.
    put(ram,0x8d3a,0); put(ram,0x8d34,2); put(ram,0x8d36,2); s = initial();
    const std::vector<std::uint8_t> full_ram = ram;
    assert(ms5::execute_sprite_submit(ram,s,status,error)); assert(status == ms5::SpriteFull && !s.waiting && s.registers.d[4] == 0xabcd0002U && ram == full_ram);
    // Wait keeps captured D4/D6 and resumes without callback or cursor reload.
    put(ram,0x8d36,4); s = initial(); const std::vector<std::uint8_t> waiting_ram = ram;
    assert(ms5::execute_sprite_submit(ram,s,status,error)); assert(status == ms5::SpriteWaiting && s.waiting && ram == waiting_ram);
    const ms5::SpriteSubmitExecutionState waiting = s;
    put(ram,0x9152,0xdeadbeef,4); put(ram,0x8d36,0x2468); put(ram,0x8d3a,0x1357); put(ram,0x8d34,6);
    const std::vector<std::uint8_t> changed = ram;
    assert(ms5::execute_sprite_submit(ram,s,status,error)); assert(status == ms5::SpriteWaiting && same(s,waiting) && ram == changed);
    put(ram,0x8d34,4); put(ram,0x8d38,0); put(ram,0x8b36,24);
    assert(ms5::execute_sprite_submit(ram,s,status,error)); assert(status == ms5::SpriteAccepted && !s.waiting && get(ram,0x8d3a,2) == 2 && s.registers.a[0] == 0x107f4c);
    // Normal signed cursor and record offsets can address wider valid RAM.
    put(ram,0x9152,0xcd50,4); put(ram,0x8d3a,0); put(ram,0x8d34,0); put(ram,0x8d38,0x8000); put(ram,0x8b36,0xfff4); s = initial();
    assert(ms5::execute_sprite_submit(ram,s,status,error)); assert(status == ms5::SpriteAccepted && get(ram,0xb34,2) == 0xfff4 && s.registers.a[0] == 0x107f28 && s.registers.d[4] == 0xabcd0002U);
    // Synthetic direct-resume state (D6=061a is not reachable through cd58).
    // This probes source-order support, not a natural queue execution path.
    // Deferred queue count is incremented before an aliased source is read.
    s = initial(); s.waiting = true; s.registers.a[1] = 0x108b34; s.registers.d[4] = 4; s.registers.d[6] = 0xabcd061a; s.registers.d[1] = 0xfedcba45;
    put(ram,0x8d34,4); put(ram,0x914e,0x200);
    assert(ms5::execute_sprite_submit(ram,s,status,error)); assert(status == ms5::SpriteAccepted && !s.waiting);
    assert(get(ram,0x914e,2) == 0x202 && s.registers.d[3] == 0xabcd0202U && s.registers.d[4] == 0x200 && s.registers.d[1] == 0xfedcba05U && s.registers.a[0] == 0x108136);
    // Late odd record error restores earlier producer/count/list mutations.
    s = initial(); put(ram,0x8d3a,0); put(ram,0x8d34,0); put(ram,0x8d38,0); put(ram,0x8b36,1); status = ms5::SpriteWaiting;
    const std::vector<std::uint8_t> before = ram; const ms5::SpriteSubmitExecutionState saved = s;
    assert(!ms5::execute_sprite_submit(ram,s,status,error)); assert(ram == before && same(s,saved) && status == ms5::SpriteWaiting);
    // Failed pending resume keeps pending and caller's status intact.
    s = waiting; put(ram,0x8d34,4); put(ram,0x8d38,1); const std::vector<std::uint8_t> pending_ram = ram;
    assert(!ms5::execute_sprite_submit(ram,s,status,error)); assert(ram == pending_ram && same(s,waiting) && status == ms5::SpriteWaiting);
    put(ram,0x9152,0,4); s = initial(); const std::vector<std::uint8_t> bad_callback = ram;
    assert(!ms5::execute_sprite_submit(ram,s,status,error)); assert(ram == bad_callback && same(s,initial()));
    ram.resize(65535); const std::vector<std::uint8_t> short_ram = ram;
    assert(!ms5::execute_sprite_submit(ram,s,status,error)); assert(ram == short_ram && same(s,initial()));
    std::cout << "sprite_submit_execution_test passed\n";
}
