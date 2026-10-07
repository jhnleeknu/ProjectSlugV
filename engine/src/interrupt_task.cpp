#include "ms5/interrupt_task.h"
namespace ms5 {
namespace {
std::uint32_t read_long(const std::vector<std::uint8_t>& ram,std::size_t at) {
    return (static_cast<std::uint32_t>(ram[at])<<24)|(static_cast<std::uint32_t>(ram[at+1])<<16)|
           (static_cast<std::uint32_t>(ram[at+2])<<8)|ram[at+3];
}
void put_long(std::vector<std::uint8_t>& ram,std::size_t at,std::uint32_t value) {
    for(unsigned int i=0;i<4;++i) ram[at+i]=static_cast<std::uint8_t>(value>>(24U-8U*i));
}
void emit(std::vector<VideoPortWrite>& ports,std::uint8_t size,std::uint32_t at,std::uint32_t value) {
    VideoPortWrite write;write.size=size;write.address=at;write.value=value;ports.push_back(write);
}
}
bool queue_interrupt_task(std::vector<std::uint8_t>& ram,InterruptRegisters& registers,
                          std::uint32_t immediate_return,std::uint32_t deferred_return,
                          InterruptTaskEnqueueResult& result,std::string& error) {
    if(ram.size()!=65536U || registers.a[7]<0x110004U || registers.a[7]>0xfffff4U || (registers.a[7]&1U)!=0) {
        error="task enqueue requires 64KiB RAM and a supported external stack";return false;
    }
    const std::uint32_t head=read_long(ram,0x81c);
    const bool enqueue=head>0x10001cU;
    if(enqueue && (head<0x100040U || head>0x10081cU || (head&1U)!=0)) {
        error="task enqueue frame must fit aligned work RAM below queue pointer";return false;
    }
    std::vector<std::uint8_t> candidate=ram;
    if(enqueue) {
        const unsigned int at=head-64U-0x100000U;
        // Predecrement writes PC, A6, then A5..A0/D7..D0.
        put_long(candidate,at+60U,deferred_return);
        put_long(candidate,at+56U,registers.a[6]);
        for(unsigned int i=0;i<6;++i) put_long(candidate,at+52U-4U*i,registers.a[5U-i]);
        for(unsigned int i=0;i<8;++i) put_long(candidate,at+28U-4U*i,registers.d[7U-i]);
        put_long(candidate,0x81c,head-64U);
    }
    InterruptTaskEnqueueResult next;
    next.queued=enqueue;next.next_pc=immediate_return;
    next.stack_address[0]=registers.a[7]-4U;next.stack_value[0]=registers.a[6];
    next.stack_address[1]=registers.a[7]+4U;next.stack_value[1]=immediate_return;
    ram.swap(candidate);registers.a[7]+=8U;result=next;error.clear();return true;
}
bool restore_interrupt_task(std::vector<std::uint8_t>& ram,InterruptRegisters& registers,
                            InterruptTaskResult& result,std::vector<VideoPortWrite>& ports,
                            std::string& error) {
    if(ram.size()!=65536U || registers.a[5]!=0x108000U) {
        error="interrupt task restore requires 64KiB RAM and A5=108000";return false;
    }
    const std::uint32_t frame=read_long(ram,0x81c);
    InterruptRegisters next=registers;InterruptTaskResult outcome;
    std::vector<VideoPortWrite> hardware;
    next.a[6]=frame;
    if(frame>=0x10081cU) {
        outcome.next_pc=0xd36;registers=next;result=outcome;ports.swap(hardware);error.clear();return true;
    }
    if(frame<0x100000U || frame>0x1007dcU || (frame&1U)!=0 ||
       registers.a[7]<0x110008U || registers.a[7]>0xfffffcU || (registers.a[7]&1U)!=0) {
        error="unsupported interrupt task frame or external stack address";return false;
    }
    std::vector<std::uint8_t> candidate=ram;
    emit(hardware,1,0x300001,registers.d[0]&255U);
    candidate[0x10]=0;candidate[0x11]=0;
    emit(hardware,2,0x2ffff2,0x1000);emit(hardware,2,0x2ffff0,0);
    const unsigned int at=frame-0x100000U;
    for(unsigned int i=0;i<8;++i) next.d[i]=read_long(candidate,at+4U*i);
    for(unsigned int i=0;i<6;++i) next.a[i]=read_long(candidate,at+32U+4U*i);
    const std::uint32_t destination=next.a[5]-0x77e4U;
    if(destination<0x100000U || destination>0x10fffcU || (destination&1U)!=0) {
        error="restored A5 queue pointer destination must be aligned work RAM";return false;
    }
    // The restored A5 participates in this write before the final A6/PC reads.
    put_long(candidate,destination-0x100000U,frame+64U);
    outcome.next_pc=read_long(candidate,at+60U);
    next.a[6]=read_long(candidate,at+56U);
    next.a[5]=0x108000U;
    next.a[7]=registers.a[7]-4U;
    outcome.restored=true;
    outcome.stack_address[0]=registers.a[7]-4U;outcome.stack_value[0]=0xd2a;
    outcome.stack_address[1]=registers.a[7]-8U;outcome.stack_value[1]=outcome.next_pc;
    ram.swap(candidate);registers=next;result=outcome;ports.swap(hardware);error.clear();return true;
}
bool resume_interrupt_tasks(std::vector<std::uint8_t>& ram,InterruptRegisters& registers,
                            InterruptTaskResult& result,std::vector<VideoPortWrite>& ports,
                            std::string& error) {
    InterruptRegisters next=registers;
    next.a[5]=0x108000U;
    if(!restore_interrupt_task(ram,next,result,ports,error)) return false;
    registers=next;return true;
}

}
