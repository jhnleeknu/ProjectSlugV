#ifndef MS5_ANIMATION_MACHINE_FRAME_H
#define MS5_ANIMATION_MACHINE_FRAME_H
#include "ms5/animation_machine.h"
namespace ms5 {
// Frame driver over run_animation_machine only (F5 decision D1). One frame = H + declared controller skip + N:
//   H: the frame head from PC = LONG (100820) (e4a on the first frame, e74 later) through its RTS to 2ac2; the dispatcher
//      (2ac2..2ac6 / 2ab8, A6 = 1008e4, JSR (A0)) is where the controller LONG (1008e4), e.g. c52a, would be entered. H stops there.
//   skip: the declared controller skip (PC := 2ac2, A7 += 4 = the RTS the controller would run, C Unknown). The controller is not run.
//   N: the existing F2 node pass from 2ac2 until the dispatcher enters LONG (100820).
// BIOS, IRQ and the controller are not executed. Each segment starts with C Unknown. Only the head callbacks e4a / e74 are supported.
// Declared wait releases (one per Waiting block, recorded in AnimationFrameWait; at most 64 waits per segment):
//   ef2   BYTE (A5-7fea) := BYTE (A5-7fe9)   (vblank)          16bd0  WORD (A5+d34) := D0.W   (sprite flush)
//   3aea  WORD 104d74 := ffff                (sound ring)      cda4   WORD 108d34 := D4.W     (sprite queue)
//   47af0 / 478de  BYTE 107ded &= 7f only if WORD 107dea == 0, else a checked error (gate).
// Any other wait PC is a checked error. Addresses are 24-bit, RAM index = address & ffff.
enum AnimationFrameSegment { AnimationFrameHead=0, AnimationFrameNodes=1 };
struct AnimationFrameWait {
    AnimationFrameSegment segment;
    std::uint32_t pc;       // the Waiting block
    std::uint32_t address;  // released address (24-bit)
    std::uint8_t size;      // BYTEs
    std::uint32_t before, released;
};
struct AnimationFrameResult {
    std::uint32_t head_pc;        // LONG (100820) at the H start; 0 for run_animation_machine_pass
    std::uint32_t controller_pc;  // LONG (1008e4) at the H start (= H stop PC); 0 for run_animation_machine_pass
    std::uint32_t pass_stop_pc;   // LONG (100820) at the N start (= N stop PC)
    std::vector<VideoPortWrite> head_ports, node_ports;  // execution order
    std::vector<AnimationFrameWait> waits;               // in order, both segments
    std::uint32_t head_external_reads, node_external_reads;
    AnimationFrameResult() : head_pc(0), controller_pc(0), pass_stop_pc(0), head_external_reads(0), node_external_reads(0) {}
};
// N only (frame 0 from a seed): PC 2ac2, A6 1008e4, A7 1ff000; stop = LONG (100820), which must be e4a / e74.
// Ends at PC = stop, A6 = 100820, A7 = 1feffc, LONG (1feffc) = 2ac2 (a valid H start).
// Both functions work on copies: any failure returns false with ram, state, device and result unchanged and error set.
bool run_animation_machine_pass(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    const ProgramBusState& resources, AnimationMachineState& state, AnimationMachineDevice& device,
    std::uint8_t external_status, AnimationFrameResult& result, std::string& error);
// H + skip + N from a valid H start (PC = LONG (100820), A6 100820, A7 1feffc, LONG (1feffc) = 2ac2).
bool step_animation_machine_frame(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    const ProgramBusState& resources, AnimationMachineState& state, AnimationMachineDevice& device,
    std::uint8_t external_status, AnimationFrameResult& result, std::string& error);
}
#endif
