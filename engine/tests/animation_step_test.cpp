#include "ms5/animation_step.h"
#include "ms5/sprite_producer.h"
#include <iostream>
#include <cstdlib>
#include <limits>

void check(bool value) { if (!value) { std::cerr << "animation step test failed\n"; std::exit(1); } }
void put(std::vector<std::uint8_t>& ram,std::size_t at,unsigned int value) {
    ram[at]=static_cast<std::uint8_t>(value>>8);ram[at+1]=static_cast<std::uint8_t>(value);
}
int main() {
    std::vector<std::uint8_t> ram(65536,0), script;
    std::string error;bool carry=false;
    // Null state changes only the bank shadow and reports carry.
    put(ram,0x10,3);ram[0xd742]=201;ram[0x2017]=4;
    check(ms5::step_animation(ram,0x2000,script,0,carry,error));
    check(carry && ram[0x10]==0 && ram[0x11]==0 && ram[0xd742]==201 && ram[0x2017]==4);
    check(ms5::initialize_sprite_queue(ram,error));
    ram[0x2026]=0;ram[0x2027]=0x10;ram[0x2028]=0x58;ram[0x2029]=0;
    // Valid draw followed by unsupported opcode must roll back queue mutation.
    const std::uint8_t bytes[]={4,0,0,0,0,0,0x21,0x52,0xff};
    script.assign(bytes,bytes+sizeof(bytes));
    put(ram,0x2042,160);put(ram,0x2046,384);
    const std::vector<std::uint8_t> before=ram;
    carry=true;
    check(!ms5::step_animation(ram,0x2000,script,0x105800,carry,error));
    check(ram==before && carry);
    script.resize(7);
    check(!ms5::step_animation(ram,0x2000,script,0x105800,carry,error) && ram==before && carry);
    script.assign(1,0);
    check(!ms5::step_animation(ram,0x2000,script,0x105800,carry,error) && ram==before);
    script.assign(1,0x28);
    check(!ms5::step_animation(ram,std::numeric_limits<std::size_t>::max(),script,0x105800,carry,error) && ram==before);
    check(!ms5::step_animation(ram,0x2000,script,0x105801,carry,error) && ram==before);
    script.assign(2,0x28);
    check(!ms5::step_animation(ram,0x2000,script,0xffffff,carry,error) && ram==before);
    // A producer wait is an explicit transactional error, not a resumed wait.
    ram=before;
    put(ram,0x8d3a,510);put(ram,0x8d36,2);
    const std::vector<std::uint8_t> waiting=ram;
    script.assign(bytes,bytes+8);script.push_back(0);script.push_back(0);
    check(!ms5::step_animation(ram,0x2000,script,0x105800,carry,error) && ram==waiting);
    // A long stream of skipped draws cannot evade the interpreter budget.
    ram=before;script.clear();
    const std::uint8_t skipped[]={4,0,0,0,0,0x7f,0xf8,0};
    for (unsigned int i=0;i<10001;++i) script.insert(script.end(),skipped,skipped+8);
    script.push_back(0x28);
    check(!ms5::step_animation(ram,0x2000,script,0x105800,carry,error) && ram==before);
    // Absolute jump updates saved pointer before interpreting the target.
    ram=before;
    const std::uint8_t jump[]={8,0x7f,0,0x10,0x58,6,0,0};
    script.assign(jump,jump+8);
    check(ms5::step_animation(ram,0x2000,script,0x105800,carry,error));
    check(ram[0x2029]==6 && !carry);
    ram=before;script[5]=0; // self-loop hits budget; no committed pointer effects
    check(!ms5::step_animation(ram,0x2000,script,0x105800,carry,error) && ram==before);
    std::cout << "animation_step_test: passed\n";
}
