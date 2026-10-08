#ifndef MS5_ANIMATION_MACHINE_H
#define MS5_ANIMATION_MACHINE_H
#include "ms5/program_bus.h"
#include "ms5/video_port.h"
namespace ms5 {
struct AnimationMachineState {
    std::uint32_t d[8], a[8], pc;
    AnimationMachineState() : pc(0x49fc6) {
        for (unsigned int i=0;i<8;++i) {d[i]=0;a[i]=0;}
    }
};
struct AnimationMachineDevice {
    std::vector<std::uint8_t> pvc;
    std::uint32_t bank_base;
    AnimationMachineDevice() : pvc(8192,0), bank_base(0x200000) {}
};
enum AnimationMachineStatus { AnimationMachineReturned, AnimationMachineWaiting };
// Explicit original-PC entry/resume. Caller supplies the return LONG already
// in shared RAM at A7, and a separate stop PC. No stack/sentinel fabrication.
// resources supplies borrowed ROM/vector views; its bank_base/pvc are replaced
// by the mutable device candidate during execution. Exact64KiB RAM/8192B PVC.
// Successful wait/return commits effects. Failure preserves every output.
// Unsupported code/device paths are checked errors, not fabricated execution.
// General CCR/timing/interrupt execution is not represented by this state.
bool run_animation_machine(std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows, const ProgramBusState& resources,
    AnimationMachineState& state, AnimationMachineDevice& device,
    std::uint32_t stop_pc, std::uint8_t external_status,
    std::uint32_t& external_reads, AnimationMachineStatus& status,
    std::vector<VideoPortWrite>& ports, std::string& error);
}
#endif
