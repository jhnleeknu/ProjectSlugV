#include "ms5/stage_cue_frame.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& ram,unsigned int at,std::uint32_t value,unsigned int size = 2) {
    for (unsigned int i = 0; i < size; ++i) ram[at+i] = static_cast<std::uint8_t>(value >> (8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& ram,unsigned int at,unsigned int size = 4) {
    std::uint32_t value = 0; for (unsigned int i = 0; i < size; ++i) value = (value<<8)|ram[at+i]; return value;
}
ms5::StageCueFrameState initial() {
    ms5::StageCueFrameState s;
    for (unsigned int i = 0; i < 8; ++i) s.registers.d[i] = 0xabcd1200U+i;
    for (unsigned int i = 0; i < 5; ++i) s.registers.a[i] = 0x76540000U+i;
    return s;
}
bool same(const ms5::StageCueFrameState& a,const ms5::StageCueFrameState& b) {
    for (unsigned int i = 0; i < 8; ++i) if (a.registers.d[i] != b.registers.d[i]) return false;
    for (unsigned int i = 0; i < 5; ++i) if (a.registers.a[i] != b.registers.a[i]) return false;
    return a.waiting_for_sprite == b.waiting_for_sprite;
}
void prepare(std::vector<std::uint8_t>& ram,unsigned int tag,bool success) {
    ram.assign(65536,0); put(ram,0xde26,0x101200,4); ram[0xde2e] = 1; ram[0xde2f] = 1;
    put(ram,0x1200,3); put(ram,0x1202,64); ram[0x1207] = tag; ram[0x106a] = 0x5a;
    if (success) { put(ram,0x4c9c,0x102000,4); put(ram,0x4ca0,1); put(ram,0xbfc,0x103000,4); }
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0); std::vector<ms5::FixedDataResource> windows;
    ms5::StageCueFrameState s = initial(); ms5::SpriteSubmitStatus status = ms5::SpriteFull; std::string error;
    // Literal null stream returns A0=0 but publishes A1=4; status is unused.
    assert(ms5::step_stage_cue_frame(ram,windows,s,1,status,error));
    assert(s.registers.a[0] == 0 && s.registers.a[1] == 4 && get(ram,0xde26) == 4 && status == ms5::SpriteFull && !s.waiting_for_sprite && s.registers.d[0] == initial().registers.d[0]);
    // Disabled selection/debug leaves all registers and status alone.
    ram[0xde2e] = 1; s = initial(); const ms5::StageCueFrameState untouched = s;
    assert(ms5::step_stage_cue_frame(ram,windows,s,1,status,error)); assert(same(s,untouched) && status == ms5::SpriteFull);
    ms5::FixedDataResource lookup; lookup.source_cpu_address = lookup.source_rom_offset = 0xe8a0c; lookup.data.resize(128);
    for (unsigned int i = 0; i < 32; ++i) { put(lookup.data,i*4,0x8000+i); put(lookup.data,i*4+2,0x4000+i); }
    windows.push_back(lookup);
    // Boundary tags and allocation success/fallback both continue through node.
    for (unsigned int outcome = 0; outcome < 2; ++outcome) {
        for (unsigned int tag = 0x1b; tag <= 0x3c; tag += (tag == 0x1c ? 0x1f : 1)) {
            prepare(ram,tag,outcome != 0); s = initial(); status = ms5::SpriteClipped;
            assert(ms5::step_stage_cue_frame(ram,windows,s,0x101000,status,error));
            assert(ram[0xde2f] == 0 && status == ms5::SpriteClipped && s.registers.a[3] == initial().registers.a[3]);
            if (tag == 0x1c || tag == 0x3b) {
                const unsigned int object = outcome != 0 ? 0x2000 : 0xe98;
                const unsigned int index = tag-0x1c;
                assert(get(ram,object+0x76,2) == 0x8000+index && get(ram,object+0x78,2) == 0x4000+index);
                assert(get(ram,object+0x2e) == 0x30000 && get(ram,object+0x32) == 0x400000 && ram[object+0x6a] == 0x5a);
                assert(s.registers.a[0] == 0x100000+object+0x7a && s.registers.a[1] == 0xe8a0c+index*4+4);
                assert(s.registers.d[0] == (0x30000U|index*4) && s.registers.d[1] == 0x400000);
                if (outcome != 0) assert(get(ram,0x2000) == 0xd5f16 && get(ram,0x4ca0,2) == 0);
            } else {
                assert(s.registers.a[0] == 0x101200 && s.registers.d[0] == static_cast<unsigned int>((tag-0x1c)&0xffff));
                assert(get(ram,0x4ca0,2) == outcome);
            }
        }
    }
    // A late lookup read error rolls back allocation and coordinate writes.
    prepare(ram,0x1c,true); s = initial(); status = ms5::SpriteWaiting; windows.clear();
    const std::vector<std::uint8_t> before = ram; const ms5::StageCueFrameState saved = s;
    assert(!ms5::step_stage_cue_frame(ram,windows,s,0x101000,status,error)); assert(ram == before && same(s,saved) && status == ms5::SpriteWaiting);
    // Null debug cue returns after setting A1, without touching status.
    ram.assign(65536,0); ram[0xde2e] = 1; ram[0xf001] = 2; s = initial();
    assert(ms5::step_stage_cue_frame(ram,windows,s,1,status,error)); assert(s.registers.a[0] == 0 && s.registers.a[1] == 0x10d38e && status == ms5::SpriteWaiting);
    // Fresh frame publishes the cleared tag before returning a sprite wait.
    prepare(ram,0,false); ram[0xf001] = 2; put(ram,0x1200,0); put(ram,0x9152,0xcd50,4);
    put(ram,0x8d34,2); put(ram,0x8d36,4); put(ram,0x8b36,12); s = initial();
    assert(ms5::step_stage_cue_frame(ram,windows,s,1,status,error)); assert(s.waiting_for_sprite && status == ms5::SpriteWaiting && ram[0xde2f] == 0);
    assert(s.registers.d[4] == 0xabcd0004U && s.registers.d[6] == 0xabcd0002U && s.registers.a[3] == initial().registers.a[3]);
    const ms5::StageCueFrameState pending = s;
    ram[0xde2f] = 1; put(ram,0xde26,0xffffffffU,4); put(ram,0x9152,0,4); put(ram,0x8d36,88); put(ram,0x8d3a,99); put(ram,0x8d34,6);
    const std::vector<std::uint8_t> hold = ram;
    assert(ms5::step_stage_cue_frame(ram,windows,s,1,status,error)); assert(same(s,pending) && ram == hold && status == ms5::SpriteWaiting);
    put(ram,0x8d34,4);
    assert(ms5::step_stage_cue_frame(ram,windows,s,1,status,error)); assert(!s.waiting_for_sprite && status == ms5::SpriteAccepted && ram[0xde2f] == 1 && get(ram,0xde26) == 0xffffffffU && get(ram,0x8d3a,2) == 2);
    // Pending errors preserve pending/status and earlier frame side effects.
    s = pending; put(ram,0x8d38,1); status = ms5::SpriteFull;
    const std::vector<std::uint8_t> bad_resume = ram;
    assert(!ms5::step_stage_cue_frame(ram,windows,s,1,status,error)); assert(same(s,pending) && ram == bad_resume && status == ms5::SpriteFull);
    // Null progression still publishes4 before a debug read fails; outer rollback.
    ram.assign(65536,0); ram[0xf001] = 2; s = initial(); const std::vector<std::uint8_t> null_debug = ram;
    assert(!ms5::step_stage_cue_frame(ram,windows,s,1,status,error)); assert(ram == null_debug && same(s,initial()) && status == ms5::SpriteFull);
    ram.resize(65535); const std::vector<std::uint8_t> short_ram = ram;
    assert(!ms5::step_stage_cue_frame(ram,windows,s,1,status,error)); assert(ram == short_ram && same(s,initial()) && status == ms5::SpriteFull);
    std::cout << "stage_cue_frame_test passed\n";
}
