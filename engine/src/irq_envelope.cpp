#include "ms5/irq_envelope.h"
namespace ms5 {
namespace {
bool valid_span(const std::vector<std::uint8_t>& stack,std::uint32_t base,
                std::uint32_t first,std::uint32_t end) {
    if(base<0x110000U || base>0xfffffeU || (base&1U)!=0 || (stack.size()&1U)!=0 ||
       stack.size()>0x1000000U-base) return false;
    return first>=base && end>=first && end-base<=stack.size();
}
std::uint32_t read(const std::vector<std::uint8_t>& bytes,std::size_t at,unsigned int size) {
    std::uint32_t value=0;
    for(unsigned int i=0;i<size;++i) value=(value<<8)|bytes[at+i];
    return value;
}
void put(std::vector<std::uint8_t>& bytes,std::size_t at,unsigned int size,std::uint32_t value) {
    for(unsigned int i=0;i<size;++i) bytes[at+i]=static_cast<std::uint8_t>(value>>(8U*(size-i-1U)));
}
void emit(std::vector<VideoPortWrite>& writes,std::uint8_t size,std::uint32_t address,std::uint32_t value) {
    VideoPortWrite write;write.size=size;write.address=address;write.value=value;
    writes.push_back(write);
}
void push(std::vector<std::uint8_t>& stack,std::uint32_t base,std::uint32_t& sp,
          std::uint8_t size,std::uint32_t value,std::vector<VideoPortWrite>& writes) {
    sp-=size;put(stack,sp-base,size,value);emit(writes,size,sp,value);
}
}
bool begin_irq_envelope(std::vector<std::uint8_t>& ram,
                        std::vector<std::uint8_t>& stack,std::uint32_t stack_base,
                        InterruptRegisters& registers,IrqEnvelopeResult& result,
                        std::vector<VideoPortWrite>& ports,std::string& error) {
    if(ram.size()!=65536U) {error="IRQ entry requires 64KiB RAM";return false;}
    IrqEnvelopeResult next;std::vector<VideoPortWrite> hardware;
    emit(hardware,2,0x3c000c,6);
    if((ram[0xfd80]&128U)==0) {
        next.next_pc=0xc00438;next.bios_handoff=true;
        result=next;ports.swap(hardware);error.clear();return true;
    }
    const std::uint32_t sp=registers.a[7];
    if(&ram==&stack || sp<0x110044U || sp>0xfffffeU || (sp&1U)!=0 ||
       !valid_span(stack,stack_base,sp-68U,sp)) {
        error="IRQ entry stack span does not cover the external save frame";return false;
    }
    std::vector<std::uint8_t> candidate=stack;InterruptRegisters saved=registers;
    for(unsigned int i=0;i<7;++i) push(candidate,stack_base,saved.a[7],4,registers.a[6U-i],next.stack_writes);
    for(unsigned int i=0;i<8;++i) push(candidate,stack_base,saved.a[7],4,registers.d[7U-i],next.stack_writes);
    saved.a[5]=0x108000;
    push(candidate,stack_base,saved.a[7],2,read(ram,0x4d8e,2),next.stack_writes);
    push(candidate,stack_base,saved.a[7],2,read(ram,0x10,2),next.stack_writes);
    saved.a[0]=read(ram,6,4);
    push(candidate,stack_base,saved.a[7],4,0x23c,next.stack_writes);
    next.next_pc=saved.a[0];
    stack.swap(candidate);registers=saved;result=next;ports.swap(hardware);error.clear();return true;
}
bool finish_irq_envelope(std::vector<std::uint8_t>& ram,
                         std::vector<std::uint8_t>& stack,std::uint32_t stack_base,
                         InterruptRegisters& registers,std::uint16_t video_status,
                         IrqEnvelopeResult& result,std::vector<VideoPortWrite>& ports,
                         std::string& error) {
    const std::uint32_t sp=registers.a[7];
    if(ram.size()!=65536U || &ram==&stack || sp<0x110002U || sp>0xffffbeU ||
       (sp&1U)!=0 || !valid_span(stack,stack_base,sp-2U,sp+64U)) {
        error="IRQ finish requires RAM and a complete external restore frame";return false;
    }
    std::vector<std::uint8_t> next_ram=ram,next_stack=stack;
    InterruptRegisters restored=registers;IrqEnvelopeResult next;
    std::vector<VideoPortWrite> hardware;
    emit(hardware,2,0x3c0004,0);
    const std::uint32_t bank=read(next_stack,sp-stack_base,2);
    put(next_ram,0x10,2,bank);
    std::uint32_t temporary_sp=sp+2U;
    push(next_stack,stack_base,temporary_sp,2,registers.d[7]&65535U,next.stack_writes);
    push(next_stack,stack_base,temporary_sp,2,registers.d[0]&65535U,next.stack_writes);
    emit(hardware,2,0x2ffff2,((bank+1U)<<12)&65535U);
    emit(hardware,2,0x2ffff0,0);
    const std::uint32_t vram=read(next_stack,sp+2U-stack_base,2);
    put(next_ram,0x4d8e,2,vram);emit(hardware,2,0x3c0000,vram);
    next_ram[2]=(video_status&8U)!=0 ? 255U : 0U;
    for(unsigned int i=0;i<8;++i) restored.d[i]=read(next_stack,sp+4U+4U*i-stack_base,4);
    for(unsigned int i=0;i<7;++i) restored.a[i]=read(next_stack,sp+36U+4U*i-stack_base,4);
    restored.a[7]=sp+64U;next.next_pc=0x29a;
    ram.swap(next_ram);stack.swap(next_stack);registers=restored;result=next;ports.swap(hardware);error.clear();return true;
}
bool return_default_irq_callback(const std::vector<std::uint8_t>& stack,
                                 std::uint32_t stack_base,InterruptRegisters& registers,
                                 IrqEnvelopeResult& result,
                                 std::vector<VideoPortWrite>& ports,std::string& error) {
    const std::uint32_t sp=registers.a[7];
    if(sp<0x110000U || sp>0xfffffaU || (sp&1U)!=0 ||
       !valid_span(stack,stack_base,sp,sp+4U)) {
        error="default IRQ callback requires an external return long";return false;
    }
    IrqEnvelopeResult next;next.next_pc=read(stack,sp-stack_base,4);
    registers.a[7]+=4U;result=next;ports.clear();error.clear();return true;
}

bool begin_raster_irq(std::vector<std::uint8_t>& ram,
                      std::vector<std::uint8_t>& stack,std::uint32_t stack_base,
                      InterruptRegisters& registers,IrqEnvelopeResult& result,
                      std::vector<VideoPortWrite>& ports,std::string& error) {
    if(ram.size()!=65536U) {error="raster IRQ entry requires 64KiB RAM";return false;}
    IrqEnvelopeResult next;std::vector<VideoPortWrite> hardware;
    if((ram[0xfd80]&128U)==0) {
        emit(hardware,2,0x3c000c,2);next.next_pc=0x2d6;
        result=next;ports.swap(hardware);error.clear();return true;
    }
    const std::uint32_t sp=registers.a[7];
    if(&ram==&stack || sp<0x11000aU || sp>0xfffffeU || (sp&1U)!=0 ||
       !valid_span(stack,stack_base,sp-10U,sp)) {
        error="raster IRQ entry stack span does not cover the save frame";return false;
    }
    std::vector<std::uint8_t> candidate=stack;InterruptRegisters saved=registers;
    push(candidate,stack_base,saved.a[7],4,registers.a[5],next.stack_writes);
    push(candidate,stack_base,saved.a[7],2,read(ram,0x4d8e,2),next.stack_writes);
    saved.a[5]=read(ram,0xa,4);
    push(candidate,stack_base,saved.a[7],4,0x2b6,next.stack_writes);
    next.next_pc=saved.a[5];
    stack.swap(candidate);registers=saved;result=next;ports.swap(hardware);error.clear();return true;
}
bool finish_raster_irq(std::vector<std::uint8_t>& ram,
                       std::vector<std::uint8_t>& stack,std::uint32_t stack_base,
                       InterruptRegisters& registers,IrqEnvelopeResult& result,
                       std::vector<VideoPortWrite>& ports,std::string& error) {
    const std::uint32_t sp=registers.a[7];
    if(ram.size()!=65536U || &ram==&stack || sp<0x110000U || sp>0xfffff8U ||
       (sp&1U)!=0 || !valid_span(stack,stack_base,sp,sp+6U)) {
        error="raster IRQ finish requires a complete external restore frame";return false;
    }
    IrqEnvelopeResult next;std::vector<VideoPortWrite> hardware;
    emit(hardware,2,0x3c000c,2);
    const std::uint32_t vram=read(stack,sp-stack_base,2);
    emit(hardware,2,0x3c0000,vram);
    const std::uint32_t a5=read(stack,sp+2U-stack_base,4);
    put(ram,0x4d8e,2,vram);registers.a[5]=a5;registers.a[7]+=6U;
    next.next_pc=0x2cc;result=next;ports.swap(hardware);error.clear();return true;
}

}
