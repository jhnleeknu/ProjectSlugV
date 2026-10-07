#include "ms5/irq_envelope.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& bytes,unsigned int at,unsigned int size,std::uint32_t value) {
    for(unsigned int i=0;i<size;++i) bytes[at+i]=static_cast<std::uint8_t>(value>>(8U*(size-i-1U)));
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0),stack(128,0xaa);
    ms5::InterruptRegisters regs;
    for(unsigned int i=0;i<8;++i) {regs.d[i]=0x12345670+i;regs.a[i]=0x87654320+i;}
    regs.a[7]=0x110080;const ms5::InterruptRegisters original=regs;
    ms5::IrqEnvelopeResult result;std::vector<ms5::VideoPortWrite> ports;std::string error;
    // BIOS handoff bypasses unused stack validation and preserves all registers.
    assert(ms5::begin_irq_envelope(ram,stack,1,regs,result,ports,error));
    assert(result.bios_handoff && result.next_pc==0xc00438 && result.stack_writes.empty());
    assert(regs.a[5]==original.a[5] && ports.size()==1 && ports[0].value==6);
    ram[0xfd80]=0x80;put(ram,6,4,0x3456);put(ram,0x10,2,0xffff);put(ram,0x4d8e,2,0x4567);
    assert(ms5::begin_irq_envelope(ram,stack,0x110000,regs,result,ports,error));
    assert(!result.bios_handoff && result.next_pc==0x3456 && result.stack_writes.size()==18);
    assert(regs.a[0]==0x3456 && regs.a[5]==0x108000 && regs.a[7]==0x11003c);
    assert(result.stack_writes[0].value==original.a[6] && result.stack_writes[17].value==0x23c);
    // Host callback and BIOS have returned: their scratch registers differ.
    regs.a[7]+=4;regs.a[5]=0;regs.d[0]=0xaabbccdd;regs.d[7]=0x11223344;
    assert(ms5::finish_irq_envelope(ram,stack,0x110000,regs,8,result,ports,error));
    assert(result.next_pc==0x29a && !result.bios_handoff && result.stack_writes.size()==2);
    assert(result.stack_writes[0].address==0x110040 && result.stack_writes[0].value==0x3344);
    assert(result.stack_writes[1].address==0x11003e && result.stack_writes[1].value==0xccdd);
    for(unsigned int i=0;i<8;++i) {assert(regs.d[i]==original.d[i]);assert(regs.a[i]==original.a[i]);}
    assert(ports.size()==4 && ports[1].value==0 && ports[3].value==0x4567 && ram[2]==255);
    const std::vector<std::uint8_t> before_ram=ram,before_stack=stack;
    assert(!ms5::finish_irq_envelope(ram,stack,0x110000,regs,0,result,ports,error));
    assert(ram==before_ram && stack==before_stack && result.next_pc==0x29a && ports.size()==4);
    assert(!ms5::begin_irq_envelope(ram,ram,0x110000,regs,result,ports,error));
    assert(ram==before_ram && result.next_pc==0x29a);
    std::cout<<"IRQ envelope saved frame, explicit stack writes and rollback passed\n";
}
