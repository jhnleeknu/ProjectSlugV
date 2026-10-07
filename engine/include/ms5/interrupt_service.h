#ifndef MS5_INTERRUPT_SERVICE_H
#define MS5_INTERRUPT_SERVICE_H
#include "ms5/interrupt_task.h"
#include "ms5/sound_service.h"
#include "ms5/composition_resource.h"
namespace ms5 {
enum InterruptServicePhase {
    InterruptServiceComplete=0,
    InterruptServiceReentrant=1,
    InterruptServiceTask=2,
    InterruptServiceSoundWait=3
};
struct InterruptServiceResult {
    InterruptServicePhase phase;
    InterruptRegisters task_registers;
    InterruptTaskResult task;
    SoundWordPending sound;
    std::uint8_t sound_reads;
    InterruptServiceResult() : phase(InterruptServiceComplete),sound_reads(0) {}
};
// Native c8c until return, task dispatch or sound producer suspension.
// A5 must be 108000. Only input D0 and A7 are needed by this semantic layer.
// task_registers/task are valid only in phase Task; they describe the exact
// dispatch boundary. This API does not promise CPU scratch registers at return.
// Palette banks/display are changed only when the rendering branch is reached.
// Port writes include all ordered MMIO; transient subroutine stack is excluded.
// All APIs preserve every mutable output on failure. Suspension is success and
// retains the busy byte; normal completion clears the entire busy byte.
bool begin_interrupt_service(std::vector<std::uint8_t>& ram,
                             std::vector<std::uint8_t>& palette0,
                             std::vector<std::uint8_t>& palette1,
                             std::uint8_t& display_bank,
                             const std::vector<CompositionResource>& resources,
                             const InterruptRegisters& registers,
                             std::uint8_t external_status,std::uint8_t sound_status,
                             InterruptServiceResult& result,
                             std::vector<VideoPortWrite>& ports,std::string& error);
// Native d2a after callback RTS. Caller supplies its resulting registers and
// already-popped A7. Does not rerun credit/rendering or increment the counter.
bool continue_interrupt_service(std::vector<std::uint8_t>& ram,
                                const InterruptRegisters& registers,
                                std::uint8_t external_status,std::uint8_t sound_status,
                                InterruptServiceResult& result,
                                std::vector<VideoPortWrite>& ports,std::string& error);
// Resume the same sound producer; no external status resampling or timer tick.
bool resume_interrupt_service_sound(std::vector<std::uint8_t>& ram,
                                    std::uint8_t sound_status,InterruptServiceResult& result,
                                    std::vector<VideoPortWrite>& ports,std::string& error);
}
#endif
