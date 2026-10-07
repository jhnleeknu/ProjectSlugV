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
    ram[0xfd80]=0x80;put(ram,6,4,0x3dcc);put(ram,0x10,2,0xffff);put(ram,0x4d8e,2,0x4567);
    assert(ms5::begin_irq_envelope(ram,stack,0x110000,regs,result,ports,error));
    assert(!result.bios_handoff && result.next_pc==0x3dcc && result.stack_writes.size()==18);
    assert(regs.a[0]==0x3dcc && regs.a[5]==0x108000 && regs.a[7]==0x11003c);
    assert(result.stack_writes[0].value==original.a[6] && result.stack_writes[17].value==0x23c);
    // Execute the default callback, then supply explicit host BIOS scratch state.
    assert(ms5::return_default_irq_callback(stack,0x110000,regs,result,ports,error));
    assert(result.next_pc==0x23c && result.stack_writes.empty() && ports.empty());
    regs.a[5]=0;regs.d[0]=0xaabbccdd;regs.d[7]=0x11223344;
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
    regs.a[7]=0x110080;
    assert(!ms5::return_default_irq_callback(stack,0x110000,regs,result,ports,error));
    assert(regs.a[7]==0x110080 && result.next_pc==0x29a && ports.size()==4);
    // Raster IRQ preserves only A5, so callback changes to other registers survive.
    regs=original;put(ram,0xa,4,0x3dcc);put(ram,0x4d8e,2,0x3344);
    assert(ms5::begin_raster_irq(ram,stack,0x110000,regs,result,ports,error));
    assert(result.next_pc==0x3dcc && result.stack_writes.size()==3 && ports.empty());
    assert(regs.a[7]==0x110076 && regs.a[5]==0x3dcc);
    assert(ms5::return_default_irq_callback(stack,0x110000,regs,result,ports,error));
    assert(result.next_pc==0x2b6 && regs.a[7]==0x11007a);
    regs.d[0]=0xaabbccdd;regs.a[0]=0xbbbb;regs.a[5]=0xdeadbeef;put(ram,0x4d8e,2,0);
    assert(ms5::finish_raster_irq(ram,stack,0x110000,regs,result,ports,error));
    assert(regs.a[5]==original.a[5] && regs.a[7]==original.a[7]);
    assert(regs.d[0]==0xaabbccdd && regs.a[0]==0xbbbb && result.next_pc==0x2cc);
    assert(ports.size()==2 && ports[0].value==2 && ports[1].value==0x3344 && result.stack_writes.empty());
    ram[0xfd80]=0;regs.a[7]=0;
    assert(ms5::begin_raster_irq(ram,stack,1,regs,result,ports,error));
    assert(result.next_pc==0x2d6 && !result.bios_handoff && ports.size()==1 && regs.a[7]==0);
    // Main callback uses already-loaded A0, and restores the actual saved A6.
    regs=original;regs.a[0]=0x3dcc;regs.a[6]=0x100100;
    put(ram,0x176,4,0xdeadbeef);put(ram,0x17a,4,0x12345678);
    assert(ms5::enter_main_callback(ram,stack,0x110000,regs,result,ports,error));
    assert(result.next_pc==0x3dcc && regs.a[6]==0x12345678 && regs.a[7]==0x110078);
    assert(result.stack_writes.size()==2 && ports.empty());
    regs.d[1]=0x99887766;regs.a[6]=0xdeadbeef;
    assert(ms5::return_default_irq_callback(stack,0x110000,regs,result,ports,error));
    assert(result.next_pc==0xf44 && regs.a[7]==0x11007c);
    // Use current bytes, even when a callback has modified the saved object.
    put(stack,0x7c,4,0xfedcba98);
    assert(ms5::restore_main_callback(stack,0x110000,regs,result,ports,error));
    assert(result.next_pc==0xf46 && regs.a[6]==0xfedcba98 && regs.a[7]==0x110080);
    assert(regs.d[1]==0x99887766 && result.stack_writes.empty() && ports.empty());
    const std::vector<std::uint8_t> main_ram=ram,main_stack=stack;
    result.next_pc=0x1234;result.bios_handoff=true;
    ms5::VideoPortWrite sentinel;sentinel.size=2;sentinel.address=0x3c0000;sentinel.value=77;
    result.stack_writes.push_back(sentinel);ports.push_back(sentinel);
    assert(!ms5::restore_main_callback(stack,0x110000,regs,result,ports,error));
    assert(!ms5::enter_main_callback(ram,stack,0x110000,regs,result,ports,error));
    assert(ram==main_ram && stack==main_stack && regs.a[6]==0xfedcba98 && regs.a[7]==0x110080);
    assert(result.next_pc==0x1234 && result.bios_handoff && result.stack_writes.size()==1);
    assert(result.stack_writes[0].value==77 && ports.size()==1 && ports[0].value==77);
    regs.a[6]=0x100100;
    assert(!ms5::enter_main_callback(ram,ram,0x110000,regs,result,ports,error));
    assert(ram==main_ram && regs.a[6]==0x100100 && result.next_pc==0x1234);
    std::cout<<"IRQ and main callback saved frames, explicit stack writes and rollback passed\n";
}
