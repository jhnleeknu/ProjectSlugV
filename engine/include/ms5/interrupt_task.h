#ifndef MS5_INTERRUPT_TASK_H
#define MS5_INTERRUPT_TASK_H
#include "ms5/video_port.h"
#include <string>
#include <vector>
namespace ms5 {
struct InterruptRegisters {
    std::uint32_t d[8],a[8];
    InterruptRegisters() { for(unsigned int i=0;i<8;++i) {d[i]=0;a[i]=0;} }
};
struct InterruptTaskResult {
    std::uint32_t next_pc;
    bool restored;
    std::uint32_t stack_address[2],stack_value[2];
    InterruptTaskResult() : next_pc(0),restored(false) {
        for(unsigned int i=0;i<2;++i) {stack_address[i]=0;stack_value[i]=0;}
    }
};
struct InterruptTaskEnqueueResult {
    std::uint32_t next_pc;
    bool queued;
    std::uint32_t stack_address[2],stack_value[2];
    InterruptTaskEnqueueResult() : next_pc(0),queued(false) {
        for(unsigned int i=0;i<2;++i) {stack_address[i]=0;stack_value[i]=0;}
    }
};
// Native c64. Stack words at entry A7 and A7+4 are supplied explicitly.
// Registers except A7 are preserved; final A7 advances by8 even if queue full.
bool queue_interrupt_task(std::vector<std::uint8_t>& ram,InterruptRegisters& registers,
                          std::uint32_t immediate_return,std::uint32_t deferred_return,
                          InterruptTaskEnqueueResult& result,std::string& error);

// Native ce2 through d28 RTS, stopping before task execution or at empty d36.
// Entry A5=108000. Task frame and restored-A5 pointer destination must be RAM.
// External stack writes are returned in execution order; A7 is after RTS.
// Errors preserve RAM/registers/result/ports. Flags are not represented.
bool restore_interrupt_task(std::vector<std::uint8_t>& ram,InterruptRegisters& registers,
                            InterruptTaskResult& result,std::vector<VideoPortWrite>& ports,
                            std::string& error);
}
#endif
