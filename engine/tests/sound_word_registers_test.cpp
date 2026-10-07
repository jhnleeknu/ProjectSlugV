#include "ms5/sound_word.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& ram, unsigned int at, unsigned int value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8); ram[at + 1] = static_cast<std::uint8_t>(value);
}
bool same(const ms5::SoundWordPending& a, const ms5::SoundWordPending& b) {
    return a.kind == b.kind && a.phase == b.phase && a.low == b.low && a.cursor == b.cursor &&
        a.byte.waiting == b.byte.waiting && a.byte.command == b.byte.command && a.byte.tail == b.byte.tail && a.byte.next == b.byte.next;
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0); ms5::SoundWordPending pending; std::string error;
    std::uint32_t d0 = 0x12342000, d1 = 0xabcdef01; std::uint8_t reads = 99;
    put(ram,0x4d8a,3);
    assert(ms5::enqueue_sound_word_registers(ram,d0,d1,0,pending,reads,error));
    assert(d0 == 0x12342000 && d1 == 0xabcdef01 && reads == 0);
    d0 = 0x12340120;
    assert(ms5::enqueue_sound_word_registers(ram,d0,d1,0,pending,reads,error));
    assert(d0 == 0x12340120 && d1 == 0xabcd0100 && reads == 0);
    ram.assign(65536,0); ram[0x12] = 1; ram[0xfd82] = 1; ram[0xfd8d] = 1;
    d0 = 0x12340720; d1 = 0xabcdef01;
    assert(ms5::enqueue_sound_word_registers(ram,d0,d1,255,pending,reads,error));
    assert(d0 == 0x12340720 && d1 == 0xabcd0700 && reads == 1);
    ram.assign(65536,0); put(ram,0x4d82,0x0422); put(ram,0x4d84,0x0523); put(ram,0x4d86,0x0624); put(ram,0x4d8c,6);
    d0 = 0x12340422; d1 = 0xabcdef01;
    assert(ms5::enqueue_sound_word_registers(ram,d0,d1,0,pending,reads,error));
    assert(d0 == 0x12340422 && d1 == 0xabcd0002 && ram[0x4d83] == 0x23 && ram[0x4d85] == 0x22);
    // Overflow high/low waits keep upper bits and do not reread changed word slots.
    d0 = 0x12340725; put(ram,0x4d74,1);
    assert(ms5::enqueue_sound_word_registers(ram,d0,d1,0,pending,reads,error));
    assert(pending.phase == 1 && d0 == 0x12340705 && d1 == 0xabcd0001);
    const ms5::SoundWordPending waiting = pending; const std::vector<std::uint8_t> waiting_ram = ram;
    assert(ms5::resume_sound_word_registers(ram,d0,d1,pending,error));
    assert(ram == waiting_ram && same(pending,waiting) && d0 == 0x12340705);
    put(ram,0x4d82,0xffff); put(ram,0x4d76,73); put(ram,0x4d74,2);
    assert(ms5::resume_sound_word_registers(ram,d0,d1,pending,error));
    assert(pending.phase == 2 && pending.byte.command == 0x23 && d0 == 0x12340723 && d1 == 0xabcd0002 && ram[0x4cf4] == 5);
    const std::vector<std::uint8_t> before = ram; const ms5::SoundWordPending low_wait = pending;
    d1 ^= 1;
    assert(!ms5::resume_sound_word_registers(ram,d0,d1,pending,error));
    assert(ram == before && same(pending,low_wait) && d1 == 0xabcd0003); d1 ^= 1;
    put(ram,0x4d74,3);
    assert(ms5::resume_sound_word_registers(ram,d0,d1,pending,error));
    assert(pending.kind == 0 && d0 == 0x12340723 && d1 == 0xabcd0002 && ram[0x4cf5] == 0x23);
    // Special high byte3 preserves D1 until the low byte producer; low3 does too.
    ram.assign(65536,0); put(ram,0x4d82,0x0303); put(ram,0x4d8c,6);
    d0 = 0x12340725; d1 = 0xabcdef01;
    assert(ms5::enqueue_sound_word_registers(ram,d0,d1,0,pending,reads,error));
    assert(d0 == 0x12340703 && d1 == 0xabcd0002 && pending.kind == 0 && ram[0x4d7b] == 255);
    ram.assign(65536,0); put(ram,0x4d8c,6);
    d0 = 0x12340725; d1 = 0xabcdef01;
    assert(ms5::enqueue_sound_word_registers(ram,d0,d1,0,pending,reads,error));
    assert(d0 == 0x12340725 && d1 == 0xabcd0002 && pending.kind == 0);
    ram.assign(65536,0); put(ram,0x4d8c,6); put(ram,0x4d82,0x0422); put(ram,0x4d74,128);
    d0 = 0x12340725; d1 = 0xabcdef01; reads = 77;
    const std::vector<std::uint8_t> bad = ram; const ms5::SoundWordPending old = pending;
    assert(!ms5::enqueue_sound_word_registers(ram,d0,d1,0,pending,reads,error));
    assert(ram == bad && same(pending,old) && d0 == 0x12340725 && d1 == 0xabcdef01 && reads == 77);
    std::cout << "sound_word_registers_test: passed\n";
}
