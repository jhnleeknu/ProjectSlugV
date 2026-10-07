#include "ms5/main_frame.h"
#include "ms5/interrupt_service.h"
#include <cassert>
#include <iostream>

namespace {
void word(std::vector<std::uint8_t>& ram, unsigned int at, unsigned int value) {
    ram[at] = static_cast<std::uint8_t>(value >> 8);
    ram[at + 1] = static_cast<std::uint8_t>(value);
}
void longword(std::vector<std::uint8_t>& ram, unsigned int at, unsigned int value) {
    word(ram, at, value >> 16); word(ram, at + 2, value);
}
unsigned int read_word(const std::vector<std::uint8_t>& ram, unsigned int at) {
    return (static_cast<unsigned int>(ram[at]) << 8) | ram[at + 1];
}
bool same_main(const ms5::MainFrameState& a, const ms5::MainFrameState& b) {
    return a.next_pc == b.next_pc && a.object_address == b.object_address && a.d1 == b.d1 && a.d3 == b.d3 &&
           a.sound.kind == b.sound.kind && a.sound.phase == b.sound.phase && a.sound.low == b.sound.low &&
           a.sound.cursor == b.sound.cursor && a.sound.byte.waiting == b.sound.byte.waiting &&
           a.sound.byte.command == b.sound.byte.command && a.sound.byte.tail == b.sound.byte.tail &&
           a.sound.byte.next == b.sound.byte.next && a.sprite.waiting == b.sprite.waiting && a.sprite.cursor == b.sprite.cursor;
}
}
int main() {
    ms5::InterruptRegisters registers;
    registers.a[5] = 0x108000; registers.a[7] = 0x1feffc; registers.d[0] = 0x123456ab;
    ms5::InterruptServiceResult irq;
    std::vector<ms5::VideoPortWrite> writes;
    std::vector<std::uint8_t> bank0(8192, 0x12), bank1(8192, 0x34);
    std::uint8_t display = 0;
    std::string error;
    const std::vector<ms5::CompositionResource> no_compositions;
    const std::vector<ms5::PaletteRecord> palettes;
    std::vector<std::uint8_t> ram(65536, 0);
    word(ram, 0x4d82, 0x422); word(ram, 0x4d8c, 2); word(ram, 0x4d76, 127);
    ram[0x7ded] = 128;
    ms5::MainFrameState main;
    main.next_pc = 0xe74; main.d1 = 0x12345678; main.d3 = 0x98765432;
    assert(ms5::prepare_main_frame(ram, no_compositions, palettes, 0xffff, main, writes, error));
    assert(main.next_pc == 0x3aea && read_word(ram, 0x4d74) == 0);
    const ms5::MainFrameState sound_wait = main;
    assert(ms5::begin_interrupt_service(ram, bank0, bank1, display, no_compositions, registers, 0, 1, irq, writes, error));
    assert(irq.phase == ms5::InterruptServiceComplete && irq.sound_reads == 1 && ram[0x16] == 1);
    assert(read_word(ram, 0x4d74) == 0 && same_main(main, sound_wait));
    assert(ms5::prepare_main_frame(ram, no_compositions, palettes, 0xffff, main, writes, error));
    assert(same_main(main, sound_wait) && writes.empty());
    assert(ms5::begin_interrupt_service(ram, bank0, bank1, display, no_compositions, registers, 0, 0, irq, writes, error));
    // The IRQ consumer skips the repeated zero-byte run; the caller never moves head.
    assert(read_word(ram, 0x4d74) == 127 && ram[0x16] == 2 && same_main(main, sound_wait));
    assert(writes.back().address == 0x320000 && writes.back().value == 0);
    assert(ms5::prepare_main_frame(ram, no_compositions, palettes, 0xffff, main, writes, error));
    assert(main.next_pc == 0xec4 && main.sound.kind == 0 && read_word(ram, 0x4d8a) == 2);
    assert(read_word(ram, 0x4d74) == 127 && read_word(ram, 0x4d76) == 1);

    // Ready old sprites are consumed by IRQ before main can emit the new ring.
    ms5::CompositionResource composition;
    composition.id = 0x2152; composition.source_rom_offset = 0;
    const std::uint8_t data[] = {1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1};
    composition.data.assign(data, data + sizeof(data));
    const std::vector<ms5::CompositionResource> compositions(1, composition);
    ram.assign(65536, 0); ram[0x1b] = 128; ram[0x7ded] = 128;
    ram[0x7dd4] = 2; ram[0x7dcf] = 1;
    longword(ram, 0x81c, 0x10081c);
    word(ram, 0x8d36, 2); word(ram, 0x8d38, 4); word(ram, 0x8d3a, 4);
    ram[0x8d3c] = 128; ram[0x8d3d] = 128;
    word(ram, 0x8d40, 4); word(ram, 0x8d42, 1);
    for (unsigned int offset = 0; offset < 8; offset += 2) word(ram, 0x8d46 + offset, 0xffff);
    word(ram, 0x8b34, 12); word(ram, 0x8b36, 24);
    for (unsigned int index = 0; index < 2; ++index) {
        const unsigned int record = 0x7f34 + 12 * (index + 1);
        word(ram, record, index); word(ram, record + 2, 160 * 64);
        word(ram, record + 4, 0xffff); word(ram, record + 6, 0x1500);
        word(ram, record + 10, 0x2152);
    }
    main = ms5::MainFrameState(); main.next_pc = 0xe74;
    assert(ms5::prepare_main_frame(ram, compositions, palettes, 0xffff, main, writes, error));
    assert(main.next_pc == 0x16bd0 && main.sprite.waiting && main.sprite.cursor == 2);
    assert(read_word(ram, 0x8d34) == 0 && ram[0x7dd4] == 2);
    const ms5::MainFrameState sprite_wait = main;
    // An IRQ palette error is fully transactional and cannot corrupt main pending.
    std::vector<std::uint8_t> bad = ram; word(bad, 0x7dea, 1);
    const std::vector<std::uint8_t> bad_before = bad, before0 = bank0, before1 = bank1;
    const std::uint8_t before_display = display;
    irq.phase = ms5::InterruptServiceReentrant; writes.resize(1); writes[0].value = 789;
    assert(!ms5::begin_interrupt_service(bad, bank0, bank1, display, compositions, registers, 0, 1, irq, writes, error));
    assert(bad == bad_before && bank0 == before0 && bank1 == before1 && display == before_display);
    assert(irq.phase == ms5::InterruptServiceReentrant && writes.size() == 1 && writes[0].value == 789 && same_main(main, sprite_wait));
    assert(ms5::begin_interrupt_service(ram, bank0, bank1, display, compositions, registers, 0, 1, irq, writes, error));
    assert(irq.phase == ms5::InterruptServiceComplete && read_word(ram, 0x8d34) == 2 && ram[0x8d3c] == 0);
    assert(read_word(ram, 0x8d42) == 1 && ram[0x16] == 1 && same_main(main, sprite_wait));
    assert(ms5::prepare_main_frame(ram, compositions, palettes, 0xffff, main, writes, error));
    assert(main.next_pc == 0xec4 && !main.sprite.waiting && read_word(ram, 0x8d36) == 4);
    assert(read_word(ram, 0x8d44) == 3 && ram[0x8d3c] == 0 && ram[0x7dd4] == 1);
    const ms5::MainFrameState completed = main;
    assert(ms5::begin_interrupt_service(ram, bank0, bank1, display, compositions, registers, 0, 0, irq, writes, error));
    assert(read_word(ram, 0x8d34) == 4 && ram[0x8d3c] == 128 && ram[0x16] == 2);
    assert((ram[0x8d3d] & 128) == 0 && same_main(main, completed) && ram[0x7dd4] == 1);

    // Priority reset overrides a busy sound status without advancing the queue.
    ram.assign(65536, 0); word(ram, 0x4d76, 127); ram[0x4d7b] = 128;
    assert(ms5::begin_interrupt_service(ram, bank0, bank1, display, no_compositions, registers, 0, 1, irq, writes, error));
    assert(read_word(ram, 0x4d74) == 0 && writes.back().address == 0x320000 && writes.back().value == 3);
    assert(ram[0x4d7b] == 0 && ram[0x4d7a] == 255);
    std::cout << "Main/IRQ shared sound and sprite handshakes passed\n";
}
