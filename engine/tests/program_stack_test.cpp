#include "ms5/program_stack.h"
#include <cassert>
#include <iostream>
namespace {
typedef std::vector<std::uint8_t> Bytes;
typedef std::vector<ms5::FixedDataResource> Windows;
void push(Bytes& ram,std::uint32_t& sp,unsigned int size,std::uint32_t value) {
    std::string error="dirty";
    assert(ms5::push_program_stack(ram,sp,size,value,error));assert(error.empty());
}
std::uint32_t pop(const Bytes& ram,const Windows& windows,const ms5::ProgramBusState& bus,std::uint32_t& sp,unsigned int size) {
    std::uint32_t value=0xdeadbeef;std::string error="dirty";
    assert(ms5::pop_program_stack(ram,windows,bus,sp,size,value,error));assert(error.empty());return value;
}
void push_error(Bytes& ram,std::uint32_t sp,unsigned int size) {
    const Bytes before=ram;const std::uint32_t old=sp;std::string error;
    assert(!ms5::push_program_stack(ram,sp,size,0x12345678,error));
    assert(ram==before&&sp==old&&!error.empty());
}
void pop_error(const Bytes& ram,const Windows& windows,const ms5::ProgramBusState& bus,std::uint32_t sp,unsigned int size) {
    const Bytes before=ram;const std::uint32_t old=sp;std::uint32_t value=0xdeadbeef;std::string error;
    assert(!ms5::pop_program_stack(ram,windows,bus,sp,size,value,error));
    assert(ram==before&&sp==old&&value==0xdeadbeef&&!error.empty());
}
ms5::FixedDataResource window(std::uint32_t cpu,std::uint32_t physical,unsigned int size) {
    ms5::FixedDataResource w;w.source_cpu_address=cpu;w.source_rom_offset=physical;w.data.resize(size);return w;
}
void mirrors_and_padding() {
    Bytes ram(65536,0xa5);Windows windows;ms5::ProgramBusState bus;
    for(unsigned int mirror=0;mirror<16;++mirror) {
        const std::uint32_t top=0x100104+mirror*0x10000;
        std::uint32_t sp=top;push(ram,sp,4,0x12345678);assert(sp==top-4);
        assert(ram[0x100]==0x12&&ram[0x103]==0x78);
        assert(pop(ram,windows,bus,sp,4)==0x12345678&&sp==top);
    }
    std::uint32_t sp=0x1feffd;push(ram,sp,1,0x1234);assert(sp==0x1feffb);
    assert(ram[0xeffb]==0x34&&ram[0xeffc]==0xa5); // odd BYTE and untouched padding
    ram[0xeffb]=0x77;assert(pop(ram,windows,bus,sp,1)==0x77&&sp==0x1feffd);
    sp=0x11100102;push(ram,sp,2,0xabcd);assert(sp==0x11100100);
    assert(pop(ram,windows,bus,sp,2)==0xabcd&&sp==0x11100102);
    sp=0x110002;push(ram,sp,4,0x89abcdef);assert(sp==0x10fffe);
    assert(ram[0xfffe]==0x89&&ram[0xffff]==0xab&&ram[0]==0xcd&&ram[1]==0xef);
    assert(pop(ram,windows,bus,sp,4)==0x89abcdef&&sp==0x110002);
    // Pop consumes current memory, not a previous push's host value.
    sp=0x108004;push(ram,sp,4,0x11223344);ram[0x8001]=0x99;
    assert(pop(ram,windows,bus,sp,4)==0x11993344);
}
void rom_and_device_reads() {
    Bytes ram(65536);Windows windows;ms5::ProgramBusState bus;
    windows.push_back(window(0x200004,0x300004,4));
    windows[0].data[0]=0x12;windows[0].data[1]=0x34;windows[0].data[2]=0xab;windows[0].data[3]=0xcd;
    bus.bank_base=0x300000;std::uint32_t sp=0x1200004;
    assert(pop(ram,windows,bus,sp,4)==0x1234abcd&&sp==0x1200008);
    windows.push_back(windows[0]);pop_error(ram,windows,bus,0x200004,4);windows.pop_back();
    pop_error(ram,windows,bus,0x2fe000,2);pop_error(ram,windows,bus,0,4);
    Bytes vectors(128,0x56);bus.vectors=&vectors;sp=0;
    assert(pop(ram,windows,bus,sp,2)==0x5656&&sp==2);
    Bytes pvc(8192,0x9a);bus.pvc=&pvc;sp=0x2fffff;
    assert(pop(ram,windows,bus,sp,1)==0x9a&&sp==0x300001);
}
void rollback() {
    Bytes ram(65536,0x7e);Windows windows;ms5::ProgramBusState bus;
    push_error(ram,0x200002,4); // first WORD RAM1ffffe, second WORD bank: preflight no partial write
    push_error(ram,0x100003,2);pop_error(ram,windows,bus,0x100001,4);
    push_error(ram,0,4); // explicit32-bit subtraction wraps tofffffffc, unsupported bus
    push_error(ram,1,1); // wraps toffffffff, BYTE still unsupported region
    pop_error(ram,windows,bus,0xfffffffe,4); // no accidental host overflow / value publication
    for(unsigned int size=0;size<=5;++size)if(size!=1&&size!=2&&size!=4) {
        push_error(ram,0x108000,size);pop_error(ram,windows,bus,0x108000,size);
    }
    Bytes short_ram(65535);push_error(short_ram,0x108000,1);pop_error(short_ram,windows,bus,0x108000,1);
    // A LONG read whose first WORD exists but second does not preserves SP/value.
    windows.push_back(window(0x100,0x100,2));pop_error(ram,windows,bus,0x100,4);
}
}
int main() {mirrors_and_padding();rom_and_device_reads();rollback();std::cout<<"program_stack_test PASS\n";}
