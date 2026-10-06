#include "ms5/menu_stack.h"
#include "ms5/menu_init.h"
#include <cassert>
#include <iostream>
static void put(std::vector<std::uint8_t>& data, unsigned int at, std::uint32_t value) {
    for (unsigned int i=0; i<4; ++i) data[at+i]=static_cast<std::uint8_t>(value>>(24-i*8));
}
static void failure(std::vector<std::uint8_t>& ram, const ms5::FixedDataResource& data,
                    std::uint32_t address) {
    const std::vector<std::uint8_t> before=ram;
    std::vector<ms5::VideoPortWrite> writes(1);
    writes[0].value=0xabcdef;
    std::string error;
    assert(!ms5::push_menu(ram,data,address,4,8,0x7000,writes,error));
    assert(!error.empty() && ram==before && writes.size()==1 && writes[0].value==0xabcdef);
}
int main() {
    ms5::FixedDataResource data;
    data.source_cpu_address=data.source_rom_offset=0x200;
    data.data.assign(32,0);
    put(data.data,0,0x21e);
    put(data.data,16,0x21e);
    put(data.data,26,0xffffffffU);
    data.data[30]='A';
    std::vector<std::uint8_t> ram(65536,0xa5);
    put(ram,0x7f0e,0x107f0e);
    const std::vector<std::uint8_t> original=ram;
    std::vector<ms5::VideoPortWrite> writes;
    std::string error;
    assert(ms5::push_menu(ram,data,0x200,4,8,0x7000,writes,error));
    assert(writes.empty() && ram[0x7f03]==0xa5 && ram[0x7f1b]==1);
    assert(ram[0x7f05]==0 && ram[0x7f0c]==255 && ram[0x7f04]==1);
    // Only the allocated slot, head and mode may change for an empty stack.
    for (unsigned int i=0;i<65536;++i) {
        if ((i>=0x7efe && i<0x7f0e) || (i>=0x7f0e && i<0x7f12) || i==0x7f1b) continue;
        assert(ram[i]==original[i]);
    }
    ram[0x7f02]=3;
    put(ram,0x7f16,0x3650);
    failure(ram,data,0x400); // Old parent is drawn before new descriptor fails.
    put(data.data,20,0x1234);
    failure(ram,data,0x200); // Unsupported parent callback.
    put(data.data,20,0);
    put(ram,0x7f0e,0x107e0e);
    failure(ram,data,0x200);
    put(ram,0x7f0e,0x107eff);
    failure(ram,data,0x200);
    const std::vector<std::uint8_t> before=ram;
    assert(!ms5::configure_menu_slot(ram,data,0x107eff,0x200,0,0,0,error));
    assert(ram==before);
    ram.resize(5);
    failure(ram,data,0x200);
    std::cout << "Menu stack allocation boundaries and rollback passed\n";
}
