#include "ms5/interrupt_service.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& ram,unsigned int at,std::uint32_t value) {
    for(unsigned int i=0;i<4;++i) ram[at+i]=static_cast<std::uint8_t>(value>>(24U-8U*i));
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0),p0(8192,0x12),p1(8192,0x34);
    std::vector<ms5::CompositionResource> resources;
    ms5::InterruptRegisters regs;regs.a[5]=0x108000;regs.a[7]=0x1feffc;regs.d[0]=0x123456ab;
    ms5::InterruptServiceResult result;std::vector<ms5::VideoPortWrite> ports;
    std::string error;std::uint8_t bank=0;
    ram[0x19]=0x81;ram[0x16]=255;ram[0x1b]=128; // busy bypasses invalid palette counter.
    ram[0x7deb]=1;
    assert(ms5::begin_interrupt_service(ram,p0,p1,bank,resources,regs,0,2,result,ports,error));
    assert(result.phase==ms5::InterruptServiceReentrant && ram[0x19]==0x81 && ports.empty());
    ram[0x19]=0x7f;ram[0x1b]=0;ram[0xf001]=16;ram[0xfd82]=1;
    assert(ms5::begin_interrupt_service(ram,p0,p1,bank,resources,regs,0,2,result,ports,error));
    assert(result.phase==ms5::InterruptServiceComplete && ram[0x19]==0 && ram[0x16]==255);
    assert(ports.size()==1 && ports[0].address==0x3a0001 && ports[0].value==0xab && result.sound_reads==1);
    // Render succeeds, then a bad sound queue rejects the whole transaction.
    ram[0x1b]=128;ram[0x7deb]=0;ram[0x7ded]=128;ram[0x5da2]=128;
    put(ram,0x81c,0x10081c);ram[0x4d74]=1;
    const std::vector<std::uint8_t> before=ram,before0=p0,before1=p1;
    assert(!ms5::begin_interrupt_service(ram,p0,p1,bank,resources,regs,0,2,result,ports,error));
    assert(ram==before && p0==before0 && p1==before1 && result.phase==ms5::InterruptServiceComplete && ports.size()==1);
    ram[0x4d74]=0;
    // A saved task interrupts the service before sound; callback return finishes it.
    put(ram,0x81c,0x1007dc);put(ram,0x7dc+52,0x108000);put(ram,0x7dc+60,0xff100);
    assert(ms5::begin_interrupt_service(ram,p0,p1,bank,resources,regs,0,2,result,ports,error));
    assert(result.phase==ms5::InterruptServiceTask && result.sound_reads==0 && ram[0x19]==128);
    assert(result.task.next_pc==0xff100 && result.task_registers.a[7]==regs.a[7]-4);
    regs=result.task_registers;regs.a[7]+=4;regs.a[5]=0;regs.d[0]=0xcafebabe;
    assert(ms5::continue_interrupt_service(ram,regs,0,2,result,ports,error));
    assert(result.phase==ms5::InterruptServiceComplete && ram[0x19]==0 && result.sound_reads==1);
    assert(ports.size()==1 && ports[0].address==0x3a0001 && ports[0].value==0xbe);
    assert(!ms5::resume_interrupt_service_sound(ram,0,result,ports,error));
    std::cout<<"Interrupt service guard, transaction rollback and task continuation passed\n";
}
