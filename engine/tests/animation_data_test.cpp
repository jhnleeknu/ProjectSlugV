#include "ms5/animation_step.h"
#include <iostream>
#include <cstdlib>
void check(bool value) { if(!value) { std::cerr<<"animation data test failed\n";std::exit(1); } }
int main() {
    std::vector<std::uint8_t> ram(65536,0), script;
    ram[0x2027]=0x10;ram[0x2028]=0x58;ram[0x20a0]=1;
    ms5::FixedDataResource fields;fields.source_cpu_address=fields.source_rom_offset=0x4a76c;
    fields.data.push_back(0);fields.data.push_back(0xa0);
    std::vector<ms5::FixedDataResource> regions(1,fields);
    const std::uint8_t branch[]={12,1,0x80,0,0,0x10,0x58,12,0,0,0,0,0x28};
    script.assign(branch,branch+sizeof(branch));
    const std::vector<std::uint8_t> before=ram;bool carry=false;std::string error;
    check(ms5::step_animation_with_data(ram,0x2000,script,0x105800,regions,carry,error));
    check(carry && ram[0x2029]==12); // selector8000 wraps onto selector0
    ram=before;regions.push_back(fields);
    check(!ms5::step_animation_with_data(ram,0x2000,script,0x105800,regions,carry,error) && ram==before && carry);
    regions.clear();
    check(!ms5::step_animation_with_data(ram,0x2000,script,0x105800,regions,carry,error) && ram==before);
    fields.data[0]=0x80;fields.data[1]=0;regions.push_back(fields);
    check(!ms5::step_animation_with_data(ram,0x2000,script,0x105800,regions,carry,error) && ram==before);
    // Successful callback before invalid opcode must not leave a partial copy.
    ms5::FixedDataResource table;table.source_cpu_address=table.source_rom_offset=0x60000;
    table.data.assign(4,0xab);regions.assign(1,table);
    const std::uint8_t call[]={20,30,0,6,0,0,0xff};script.assign(call,call+7);
    check(!ms5::step_animation_with_data(ram,0x2000,script,0x105800,regions,carry,error) && ram==before);
    script[6]=0;script.push_back(0);
    check(ms5::step_animation_with_data(ram,0x2000,script,0x105800,regions,carry,error));
    check(ram[0x2078]==0xab && ram[0x207b]==0xab && ram[0x2029]==6);
    ram=before;ram[0x207d]=1;const std::vector<std::uint8_t> outside=ram;
    check(!ms5::step_animation_with_data(ram,0x2000,script,0x105800,regions,carry,error) && ram==outside);
    // Indexed draw skips out-of-range entries without decoding their bytes.
    ram=before;fields.data[0]=0;fields.data[1]=0xa0;regions.assign(1,fields);
    const std::uint8_t indexed[]={0x10,0,0,8,0xff,0,0,0,0,0,0,0,0x28};
    script.assign(indexed,indexed+sizeof(indexed));
    check(ms5::step_animation_with_data(ram,0x2000,script,0x105800,regions,carry,error));
    check(carry && ram[0x2029]==0);
    ram=before;ram[0x20a0]=0;const std::vector<std::uint8_t> selected=ram;
    check(!ms5::step_animation_with_data(ram,0x2000,script,0x105800,regions,carry,error) && ram==selected && carry);
    script[4]=4;script[9]=0x7f;script[10]=0xf8; // suppressed draw ID 007ff800
    check(ms5::step_animation_with_data(ram,0x2000,script,0x105800,regions,carry,error));
    check(carry && ram[0x2029]==0);
    ram=selected;script.resize(11);
    check(!ms5::step_animation_with_data(ram,0x2000,script,0x105800,regions,carry,error) && ram==selected);
    // MOVE.B keeps the offset word's high byte: 0100 becomes index word0100.
    script.assign(indexed,indexed+sizeof(indexed));fields.data[0]=1;fields.data[1]=0;
    regions.assign(1,fields);ram=selected;
    check(ms5::step_animation_with_data(ram,0x2000,script,0x105800,regions,carry,error));
    check(carry && ram[0x2029]==0);
    std::cout<<"animation_data_test: passed\n";
}
