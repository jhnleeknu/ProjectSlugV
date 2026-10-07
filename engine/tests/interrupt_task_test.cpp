#include "ms5/interrupt_task.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& ram,unsigned int at,std::uint32_t value) {
    for(unsigned int i=0;i<4;++i) ram[at+i]=static_cast<std::uint8_t>(value>>(24U-8U*i));
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0);ms5::InterruptRegisters r;
    ms5::InterruptTaskResult result;std::vector<ms5::VideoPortWrite> ports;std::string error;
    r.a[5]=0x108000;r.a[7]=0x1feffc;r.d[0]=0xabcdef42;
    put(ram,0x81c,0xffffffff);
    assert(ms5::restore_interrupt_task(ram,r,result,ports,error));
    assert(!result.restored && result.next_pc==0xd36 && r.a[6]==0xffffffff && ports.empty() && r.d[0]==0xabcdef42);
    put(ram,0x81c,0x1007dc);
    for(unsigned int i=0;i<16;++i) put(ram,0x7dc+4*i,0x1000+i);
    // Restored A5 makes the cursor write alias the saved PC.
    put(ram,0x7dc+52,0x100818+0x77e4);
    assert(ms5::restore_interrupt_task(ram,r,result,ports,error));
    assert(result.restored && result.next_pc==0x10081c && r.a[6]==0x100e && r.a[5]==0x108000);
    assert(r.a[7]==0x1feff8 && r.d[0]==0x1000 && ports.size()==3 && ports[0].value==0x42);
    assert(result.stack_value[0]==0xd2a && result.stack_value[1]==0x10081c);
    assert(result.stack_address[0]==0x1feff8 && result.stack_address[1]==0x1feff4);
    put(ram,0x81c,0x1007dc);put(ram,0x7dc+52,0);
    const std::vector<std::uint8_t> before=ram;const std::uint32_t d0=r.d[0];
    assert(!ms5::restore_interrupt_task(ram,r,result,ports,error));
    assert(ram==before && r.d[0]==d0 && result.restored && ports.size()==3);
    std::cout<<"Interrupt task unsigned empty check, restored A5 alias and rollback passed\n";
}
